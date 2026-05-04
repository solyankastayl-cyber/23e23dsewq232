"""
Risk engine — aggregates structural / temporal / interaction risk signals
into a single 0..1 risk score and a coarse label.

Reads read-only from the result dict. Never mutates inputs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Interaction types considered structurally risky.
RISKY_INTERACTION_TYPES = frozenset({
    "fake_breakout",
    "expansion_chaos",
    "whipsaw",
})


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def compute_risk(context: Dict[str, Any]) -> Tuple[float, str, List[str]]:
    """
    Inputs (all optional / defensive):
      - context["conflict_ratio"]: float
      - context["temporal_intelligence"]: {
            instability_pressure, reversal_pressure,
            regime_flip_frequency, detected_sequence
        }
      - context["interaction"]: { type }

    Returns (risk_score in [0,1], risk_level label, risks[]).
    """
    risk = 0.0
    risks: List[str] = []

    conflict = _safe_float(context.get("conflict_ratio"))
    temporal = context.get("temporal_intelligence") or {}
    interaction = context.get("interaction") or {}

    # 1. Engine conflict
    if conflict > 0.40:
        risk += 0.25
        risks.append("high_engine_conflict")

    # 2. Temporal instability
    if _safe_float(temporal.get("instability_pressure")) > 0.60:
        risk += 0.25
        risks.append("temporal_instability")

    # 3. Reversal pressure
    if _safe_float(temporal.get("reversal_pressure")) > 0.60:
        risk += 0.20
        risks.append("reversal_pressure_high")

    # 4. Unstable regime (frequent flips)
    if _safe_float(temporal.get("regime_flip_frequency")) > 0.30:
        risk += 0.15
        risks.append("unstable_regime")

    # 5. Structurally risky interaction type
    itype = str(interaction.get("type") or "").lower()
    if itype in RISKY_INTERACTION_TYPES:
        risk += 0.20
        risks.append(f"interaction_{itype}")

    # 6. Chaotic sequence heuristic
    seq = str((temporal.get("detected_sequence") or "")).lower()
    if seq and "chaos" in seq:
        risk += 0.10
        risks.append("chaotic_sequence")

    risk = min(risk, 1.0)

    if risk >= 0.75:
        level = "extreme"
    elif risk >= 0.50:
        level = "high"
    elif risk >= 0.25:
        level = "elevated"
    else:
        level = "low"
    return risk, level, risks
