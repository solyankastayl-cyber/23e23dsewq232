"""
Alignment engine — checks whether the primary scenario direction is
structurally supported by the interaction layer and the temporal pressures.

Since the canonical `interaction` object does NOT expose a `direction` field,
we infer it from the interaction.type heuristically. This mapping is the
single source of truth for "is this interaction pro or anti the current bias".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# direction relative to the prevailing bias the engines already inferred:
#   "aligned"   → reinforces whatever the aggregated bias says
#   "opposed"   → contradicts the aggregated bias
#   "neutral"   → no directional opinion
INTERACTION_DIRECTION_MAP: Dict[str, str] = {
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _infer_interaction_direction(
    interaction: Optional[Dict[str, Any]],
    aggregated_bias: str,
) -> str:
    """
    Returns one of {"bullish", "bearish", "neutral"}.

    Uses interaction.direction if present (future-proof), otherwise falls
    back to INTERACTION_DIRECTION_MAP against the aggregated bias.
    """
    if not interaction:
        return "neutral"
    # explicit direction wins (future-proof)
    explicit = str(interaction.get("direction") or "").lower()
    if explicit in ("bullish", "bearish", "neutral"):
        return explicit
    itype = str(interaction.get("type") or "").lower()
    stance = INTERACTION_DIRECTION_MAP.get(itype, "neutral")
    if stance == "neutral":
        return "neutral"
    if stance == "aligned":
        return aggregated_bias if aggregated_bias in ("bullish", "bearish") else "neutral"
    # opposed
    if aggregated_bias == "bullish":
        return "bearish"
    if aggregated_bias == "bearish":
        return "bullish"
    return "neutral"


def compute_alignment(
    primary_bias: str,
    context: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    """
    Returns (alignment_score 0..1, drivers[], risks[]).
    Base 0.5 (neutral). Nudges are bounded so a single layer cannot
    monopolise the score.
    """
    score = 0.5
    drivers: List[str] = []
    risks: List[str] = []

    interaction = context.get("interaction") or {}
    temporal = context.get("temporal_intelligence") or {}
    aggregated_bias = str(context.get("bias") or "neutral").lower()

    interaction_dir = _infer_interaction_direction(interaction, aggregated_bias)

    # --- interaction ↔ primary scenario alignment
    if interaction_dir == primary_bias and primary_bias in ("bullish", "bearish"):
        score += 0.20
        drivers.append("interaction_aligned_with_primary_scenario")
    elif interaction_dir != "neutral" and interaction_dir != primary_bias:
        score -= 0.20
        risks.append("interaction_conflicts_with_primary_scenario")

    # --- temporal pressure support
    continuation = _safe_float(temporal.get("continuation_pressure"))
    reversal = _safe_float(temporal.get("reversal_pressure"))
    if primary_bias in ("bullish", "bearish"):
        if continuation > reversal and continuation > 0.0:
            score += 0.15
            drivers.append("temporal_continuation_support")
        elif reversal > continuation and reversal > 0.0:
            score -= 0.15
            risks.append("temporal_reversal_pressure_against_primary")

    # --- neutral primary handled by instability
    if primary_bias == "neutral":
        instability = _safe_float(temporal.get("instability_pressure"))
        if instability > 0.5:
            score += 0.10
            drivers.append("neutral_primary_supported_by_instability")

    score = max(0.0, min(score, 1.0))
    return score, drivers, risks
