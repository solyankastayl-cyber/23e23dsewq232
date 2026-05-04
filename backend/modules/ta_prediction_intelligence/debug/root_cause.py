"""
Root Cause Engine — read-only attribution of which layer of the system
produced the wrong signal. Strict priority order per spec:

    1. interaction layer
    2. engine disagreement
    3. conflict mismanagement
    4. temporal layer
    5. risk misread
    6. scenario logic failure

Returns:
    {
        "primary_cause":     <str|None>,
        "secondary_causes":  [<str>, ...],
        "engine_attribution": [
            {"engine": ..., "weight": float, "sign": int}, ...
        ],
    }

Pure functions only. No mutation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .taxonomy import (
    ErrorType,
    HIGH_CONFLICT_THRESHOLD,
    HIGH_VOLATILITY_THRESHOLD,
    TIMING_ADVERSE_THRESHOLD,
)

# Map interaction.type → directional stance vs aggregated bias.
_INTERACTION_DIRECTION_MAP: Dict[str, str] = {
    "trend_continuation": "aligned",
    "breakout": "aligned",
    "breakout_confirmed": "aligned",
    "pullback_continuation": "aligned",
    "early_reversal": "opposed",
    "rejection": "opposed",
    "fake_breakout": "opposed",
    "whipsaw": "opposed",
    "compression": "neutral",
    "expansion_chaos": "neutral",
    "range_bound": "neutral",
}


def _bias_to_sign(value: Optional[str]) -> int:
    if not value:
        return 0
    v = str(value).lower()
    if v in ("bullish", "bull"):
        return +1
    if v in ("bearish", "bear"):
        return -1
    return 0


def _interaction_inferred_direction(
    interaction: Optional[Dict[str, Any]], aggregated_bias: str
) -> int:
    """Returns -1/0/+1."""
    if not interaction:
        return 0
    explicit = str(interaction.get("direction") or "").lower()
    if explicit in ("bullish", "bull"):
        return +1
    if explicit in ("bearish", "bear"):
        return -1
    if explicit in ("neutral",):
        return 0
    itype = str(interaction.get("type") or "").lower()
    stance = _INTERACTION_DIRECTION_MAP.get(itype, "neutral")
    agg_sign = _bias_to_sign(aggregated_bias)
    if stance == "aligned":
        return agg_sign
    if stance == "opposed":
        return -agg_sign
    return 0


def _engine_attribution(
    contributions: List[Dict[str, Any]], real_dir: int
) -> List[Dict[str, Any]]:
    """
    Returns engine-level wrong-attribution sorted by weight desc.

    weight = max(0, confidence) × max(0, quality)
    sign   = engine bias sign (+1/-1/0)
    Only engines whose sign disagrees with real_dir AND have weight>0 are returned.
    """
    if real_dir == 0:
        return []
    out: List[Dict[str, Any]] = []
    for c in contributions or []:
        try:
            conf = float(c.get("confidence") or 0.0)
            qual = float(c.get("quality") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
            qual = 0.0
        if conf <= 0 or qual <= 0:
            continue
        sign = _bias_to_sign(c.get("bias"))
        if sign == 0:
            continue
        if sign == real_dir:
            continue
        weight = round(conf * qual, 6)
        out.append({
            "engine": str(c.get("engine") or ""),
            "sign": sign,
            "confidence": round(conf, 6),
            "quality": round(qual, 6),
            "weight": weight,
        })
    out.sort(key=lambda d: (-d["weight"], d["engine"]))
    return out


def attribute_root_causes(
    record: Dict[str, Any],
    error_type: ErrorType,
    classification_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Pure: produces a deterministic root-cause attribution.

    For CORRECT predictions the result is empty (no causes to attribute).
    For LOW_SIGNAL_NOISE / UNDERCONFIDENT we still return any structural
    over-/under-confidence findings so the architect can see why the
    decision layer produced a weak signal in those cases too.
    """
    causes: List[str] = []
    decision = record.get("decision_intelligence") or {}
    interaction = record.get("interaction") or {}
    contributions = record.get("contributions") or []
    temporal = record.get("temporal_intelligence") or {}
    bias_aggregated = str(record.get("bias") or "neutral").lower()

    real_dir = int(classification_meta.get("real_dir") or 0)
    pred_dir = int(classification_meta.get("pred_dir") or 0)
    decision_confidence = float(classification_meta.get("decision_confidence") or 0.0)
    conflict_ratio = float(classification_meta.get("conflict_ratio") or 0.0)
    mae_pct = classification_meta.get("max_adverse_move_pct")

    # CORRECT and UNDERCONFIDENT: only structural notes, no errors to blame.
    if error_type == ErrorType.CORRECT:
        return {
            "primary_cause": None,
            "secondary_causes": [],
            "engine_attribution": [],
            "notes": ["prediction_correct"],
        }

    # ── 1. Interaction failure (priority 1)
    inter_dir = _interaction_inferred_direction(interaction, bias_aggregated)
    if real_dir != 0 and inter_dir != 0 and inter_dir != real_dir:
        causes.append("interaction_misread")

    # ── 2. Engine disagreement (priority 2)
    attribution = _engine_attribution(contributions, real_dir)
    if attribution:
        # Top 1-2 culprits become discrete causes; we tag both
        # "<engine>_misread" and the structural "<engine>_overweight"
        # depending on whether the dominant_engine matches.
        dominant = str(record.get("dominant_engine") or "").lower()
        for entry in attribution[:2]:
            eng = entry["engine"].lower()
            causes.append(f"{eng}_misread")
            if eng == dominant:
                causes.append(f"{eng}_overweight")

    # ── 3. Conflict mismanagement (priority 3)
    if conflict_ratio > 0.30 and decision_confidence > 0.60:
        causes.append("conflict_underestimated")

    # ── 4. Temporal failure (priority 4)
    temp_ready = bool(temporal.get("ready"))
    if temp_ready and real_dir != 0:
        try:
            cont = float(temporal.get("continuation_pressure") or 0.0)
            rev = float(temporal.get("reversal_pressure") or 0.0)
        except (TypeError, ValueError):
            cont, rev = 0.0, 0.0
        agg_sign = _bias_to_sign(bias_aggregated)
        # continuation said "keep going with bias" but real_dir disagreed
        if cont > 0.60 and agg_sign != 0 and agg_sign != real_dir:
            causes.append("temporal_trend_failure")
        # reversal said "flip is coming" but real_dir kept going with bias
        if rev > 0.60 and agg_sign != 0 and agg_sign == real_dir:
            causes.append("false_reversal_signal")

    # ── 5. Risk misread (priority 5)
    risk_level = str(decision.get("risk_level") or "").lower()
    if (
        risk_level == "low"
        and mae_pct is not None
    ):
        try:
            if abs(float(mae_pct)) >= TIMING_ADVERSE_THRESHOLD:
                causes.append("risk_underestimated")
        except (TypeError, ValueError):
            pass

    # ── 6. Scenario selection failure (priority 6)
    if not classification_meta.get("scenario_correct") and pred_dir != 0:
        causes.append("scenario_selection_error")

    # Deduplicate while preserving order.
    seen = set()
    ordered: List[str] = []
    for c in causes:
        if c in seen:
            continue
        seen.add(c)
        ordered.append(c)

    primary = ordered[0] if ordered else None
    secondaries = ordered[1:]

    notes: List[str] = []
    if classification_meta.get("no_edge_ignored"):
        notes.append("no_edge_ignored")

    return {
        "primary_cause": primary,
        "secondary_causes": secondaries,
        "engine_attribution": attribution,
        "notes": notes,
    }
