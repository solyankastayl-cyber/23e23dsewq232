"""
Decision classifier — compresses (confidence, dominance, risk_level) into a
single coarse signal_strength label. Conservative by design: extreme risk
or ambiguous dominance collapse to "no_edge" regardless of confidence.
"""
from __future__ import annotations


def classify_decision(
    confidence: float,
    dominance: float,
    risk_level: str,
) -> str:
    try:
        c = float(confidence)
        d = float(dominance)
    except (TypeError, ValueError):
        return "no_edge"
    rl = str(risk_level or "").lower()

    # Hard kills first
    if d < 0.07:
        return "no_edge"
    if rl == "extreme":
        return "no_edge"

    # Strong: confident AND dominant AND low risk
    if c >= 0.70 and d >= 0.20 and rl == "low":
        return "strong"

    # Moderate: enough confidence / dominance, bounded risk
    if c >= 0.50 and d >= 0.12 and rl in ("low", "elevated"):
        return "moderate"

    # Weak: barely enough to report a directional bias
    if c >= 0.35 and d >= 0.07:
        return "weak"

    return "no_edge"
