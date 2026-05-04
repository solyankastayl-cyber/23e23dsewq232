"""
PHASE 19.2 — Strategy Capital Engine
====================================
Computes capital shares via renormalization.

Process:
1. Get adjusted weights from Weight Engine
2. Sum all adjusted weights
3. Normalize to get capital_share
4. Compute confidence modifier (bounded)
"""

from typing import Dict, Optional, Tuple

from modules.strategy_brain.allocation.strategy_allocation_types import (
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
)
from modules.strategy_brain.allocation.strategy_weight_engine import (
    get_weight_engine,
    StrategyWeightEngine,
)


class StrategyCapitalEngine:
    """
    Strategy Capital Engine.
    
    Normalizes adjusted weights to get capital shares.
    """
    
    def __init__(self):
        """Initialize with weight engine."""
        self.weight_engine = get_weight_engine()
    
    def compute_capital_shares(
        self,
        adjusted_weights: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute capital shares via renormalization.
        
        Formula:
            capital_share = adjusted_weight / sum(all_adjusted_weights)
        
        Ensures sum = 1.0
        """
        total = sum(adjusted_weights.values())
        
        if total == 0:
            # All strategies disabled - equal zero distribution
            return {k: 0.0 for k in adjusted_weights}
        
        return {
            strategy: weight / total
            for strategy, weight in adjusted_weights.items()
        }
    
    def compute_confidence_modifier(self, capital_share: float) -> float:
        """
        Compute confidence modifier from capital share.
        
        Bounded to [0.75, 1.25]
        
        Logic:
        - Base modifier starts at 1.0
        - Scale by capital_share relative to average
        - Apply bounds
        """
        # Average share would be 1.0 / num_strategies ≈ 0.125
        # We scale relative to this
        average_share = 0.125  # 1/8 strategies
        
        if capital_share == 0:
            return CONFIDENCE_MODIFIER_MIN
        
        # Ratio to average
        ratio = capital_share / average_share
        
        # Scale modifier (centered at 1.0)
        modifier = 0.75 + (ratio * 0.25)
        
        # Bound
        return max(
            CONFIDENCE_MODIFIER_MIN,
            min(CONFIDENCE_MODIFIER_MAX, modifier)
        )
    
    def compute_full_allocation(
        self,
        strategy_states: Dict[str, str],
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """
        Compute full allocation data.
        
        Args:
            strategy_states: Dict of {strategy_name: strategy_state}
        
        Returns:
            Tuple of:
            - adjusted_weights
            - capital_shares
            - confidence_modifiers
        """
        # Get adjusted weights
        adjusted_weights = self.weight_engine.compute_all_adjusted_weights(
            strategy_states
        )
        
        # Normalize to capital shares
        capital_shares = self.compute_capital_shares(adjusted_weights)
        
        # Compute confidence modifiers
        confidence_modifiers = {
            strategy: self.compute_confidence_modifier(share)
            for strategy, share in capital_shares.items()
        }
        
        return adjusted_weights, capital_shares, confidence_modifiers


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyCapitalEngine] = None


def get_capital_engine() -> StrategyCapitalEngine:
    """Get singleton capital engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyCapitalEngine()
    return _engine
