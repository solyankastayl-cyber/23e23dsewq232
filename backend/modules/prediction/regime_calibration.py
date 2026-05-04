"""
Regime Calibration

Applies regime-specific weights to confidence.
Trend regimes are more predictable than range.
"""

from typing import Dict


# Regime confidence multipliers
# trend = most predictable, high_vol = least
REGIME_WEIGHTS: Dict[str, float] = {
    "trend": 1.10,         # Trends are easier to ride
    "compression": 1.05,   # Breakouts are clear signals
    "range": 0.90,         # Range is harder to time
    "high_volatility": 0.85,  # High vol = unpredictable
}


def apply_regime_weight(confidence: float, regime: str) -> float:
    """
    Apply regime-specific confidence adjustment.
    
    Args:
        confidence: Base confidence value
        regime: Detected regime
    
    Returns:
        Adjusted confidence (capped at 0.90)
    """
    weight = REGIME_WEIGHTS.get(regime, 1.0)
    adjusted = confidence * weight
    return min(adjusted, 0.90)


def get_regime_weight(regime: str) -> float:
    """Get weight for a regime."""
    return REGIME_WEIGHTS.get(regime, 1.0)
