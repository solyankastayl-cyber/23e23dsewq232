"""
Transition Pressure — three orthogonal 0..1 scores derived from the latest
feature snapshot, with aux drivers/risks strings for UX.

The scores are interpreted as:
  * reversal_pressure   : probability-like weight that the current trend is
                          about to flip (divergences, exhaustion, wick
                          rejections, waning alignment).
  * continuation_pressure: weight favouring trend continuation (strong
                          engine alignment, persistent momentum, freshness).
  * instability_pressure: weight of regime instability (expansion, high
                          conflict, chaotic volatility).

All rules are conservative additive increments on the most recent snapshot.
No ML, no random.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .types import MIN_HISTORY


def _feat(snap: Any, key: str, default: float = 0.0) -> float:
    if not isinstance(snap, dict):
        return default
    feats = snap.get("features") or {}
    v = feats.get(key, default)
    try:
        v = float(v)
        if v != v:
            return default
        return v
    except (TypeError, ValueError):
        return default


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, round(float(x), 4)))


def compute_transition_pressure(history: List[Any]) -> Dict[str, Any]:
    if not history or len(history) < MIN_HISTORY:
        return {
            "reversal_pressure": 0.0,
            "continuation_pressure": 0.0,
            "instability_pressure": 0.0,
            "drivers": [],
            "risks": [],
        }

    latest = history[-1]
    reversal = 0.0
    continuation = 0.0
    instability = 0.0
    drivers: List[str] = []
    risks: List[str] = []

    # Momentum divergences.
    if _feat(latest, "rsi_div_bear") >= 0.5:
        reversal += 0.25
        risks.append("bearish_divergence")
    if _feat(latest, "rsi_div_bull") >= 0.5:
        reversal += 0.25
        drivers.append("bullish_divergence")

    # Exhaustion of momentum.
    if _feat(latest, "exhaustion_flag") >= 0.5:
        reversal += 0.20
        risks.append("momentum_exhaustion")

    # Volatility expansion → instability.
    if _feat(latest, "expansion_flag") >= 0.5:
        instability += 0.20
        drivers.append("volatility_expansion")
    if _feat(latest, "explosive_bar_flag") >= 0.5:
        instability += 0.20
        risks.append("explosive_bar")

    # Strong alignment drives continuation.
    sm_align = _feat(latest, "structure_momentum_alignment")
    sl_align = _feat(latest, "structure_level_alignment")
    if sm_align > 0.6:
        continuation += 0.25
        drivers.append("structure_momentum_alignment")
    if sl_align > 0.6:
        continuation += 0.20
        drivers.append("structure_level_alignment")
    # Strong mis-alignment hints at reversal.
    if sm_align < -0.6:
        reversal += 0.15
        risks.append("structure_momentum_misalignment")

    # High engine conflict → instability.
    if _feat(latest, "conflict_ratio") > 0.4:
        instability += 0.25
        risks.append("high_engine_conflict")

    # Pattern conflict → instability.
    if _feat(latest, "pattern_conflict_flag") >= 0.5:
        instability += 0.10
        risks.append("pattern_conflict")

    # Structure break event recent → reversal pressure.
    if _feat(latest, "structure_break_flag") >= 0.5:
        reversal += 0.15
        drivers.append("recent_structure_break")

    return {
        "reversal_pressure": _clip01(reversal),
        "continuation_pressure": _clip01(continuation),
        "instability_pressure": _clip01(instability),
        "drivers": drivers,
        "risks": risks,
    }
