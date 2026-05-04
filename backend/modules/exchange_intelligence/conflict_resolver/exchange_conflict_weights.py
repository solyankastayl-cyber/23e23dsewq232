"""
Exchange Conflict Weights
==========================
Phase 14.1 — Weight configuration for conflict resolution.

Weights based on signal reliability and market impact analysis:
- Liquidations: Highest weight (1.30) - cascade events are price-moving
- Derivatives: High weight (1.15) - L/S ratio and leverage are leading
- Flow: Base weight (1.00) - order flow is reliable baseline
- Funding: Lower weight (0.85) - can be lagging/crowded
- Volume: Lowest weight (0.75) - often noisy
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class WeightConfig:
    """Weight configuration for engines."""
    base_weights: Dict[str, float]
    
    # Regime modifiers
    trend_modifiers: Dict[str, float]
    squeeze_modifiers: Dict[str, float]
    cascade_modifiers: Dict[str, float]


# Default base weights
BASE_WEIGHTS: Dict[str, float] = {
    "liquidations": 1.30,
    "derivatives": 1.15,
    "flow": 1.00,
    "funding": 0.85,
    "volume": 0.75,
}

# Trend regime: flow and funding matter more
TREND_MODIFIERS: Dict[str, float] = {
    "liquidations": 1.0,
    "derivatives": 1.1,
    "flow": 1.3,
    "funding": 1.2,
    "volume": 0.9,
}

# Squeeze regime: liquidations and derivatives dominate
SQUEEZE_MODIFIERS: Dict[str, float] = {
    "liquidations": 1.5,
    "derivatives": 1.4,
    "flow": 0.8,
    "funding": 0.7,
    "volume": 0.6,
}

# Cascade regime: liquidations absolutely dominate
CASCADE_MODIFIERS: Dict[str, float] = {
    "liquidations": 2.0,
    "derivatives": 1.2,
    "flow": 0.7,
    "funding": 0.5,
    "volume": 0.5,
}


def get_weights(regime: str = "normal") -> Dict[str, float]:
    """
    Get weights based on market regime.
    
    Args:
        regime: "normal", "trend", "squeeze", "cascade"
    
    Returns:
        Dict of engine weights
    """
    if regime == "trend":
        return {k: BASE_WEIGHTS[k] * TREND_MODIFIERS[k] for k in BASE_WEIGHTS}
    elif regime == "squeeze":
        return {k: BASE_WEIGHTS[k] * SQUEEZE_MODIFIERS[k] for k in BASE_WEIGHTS}
    elif regime == "cascade":
        return {k: BASE_WEIGHTS[k] * CASCADE_MODIFIERS[k] for k in BASE_WEIGHTS}
    else:
        return BASE_WEIGHTS.copy()


# Thresholds for bias determination
BIAS_THRESHOLD = 0.25  # Score > this = LONG, Score < -this = SHORT
HIGH_CONFLICT_THRESHOLD = 0.5  # Above this = high conflict
LOW_CONFIDENCE_THRESHOLD = 0.4  # Below this = low confidence signal

# Dominance threshold: signal must be this much stronger than 2nd place
DOMINANCE_THRESHOLD = 1.2
