"""
PHASE 19.2 — Strategy Weight Engine
===================================
Computes adjusted weights based on strategy state.

Process:
1. Get base weight
2. Apply state multiplier
3. Return adjusted weight
"""

from typing import Dict, Optional

from modules.strategy_brain.allocation.strategy_allocation_types import (
    BASE_WEIGHTS,
    STATE_MULTIPLIERS,
)


class StrategyWeightEngine:
    """
    Strategy Weight Engine.
    
    Adjusts base weights based on strategy state.
    """
    
    def __init__(self, base_weights: Optional[Dict[str, float]] = None):
        """Initialize with optional custom base weights."""
        self.base_weights = base_weights or BASE_WEIGHTS.copy()
    
    def get_base_weight(self, strategy_name: str) -> float:
        """
        Get base weight for strategy.
        
        Returns 0.0 if strategy not found.
        """
        return self.base_weights.get(strategy_name, 0.0)
    
    def get_state_multiplier(self, strategy_state: str) -> float:
        """
        Get multiplier for strategy state.
        
        ACTIVE: 1.0
        REDUCED: 0.6
        DISABLED: 0.0
        """
        return STATE_MULTIPLIERS.get(strategy_state, 0.0)
    
    def compute_adjusted_weight(
        self,
        strategy_name: str,
        strategy_state: str,
    ) -> float:
        """
        Compute adjusted weight for strategy.
        
        Formula:
            adjusted_weight = base_weight × state_multiplier
        """
        base_weight = self.get_base_weight(strategy_name)
        state_multiplier = self.get_state_multiplier(strategy_state)
        
        return base_weight * state_multiplier
    
    def compute_all_adjusted_weights(
        self,
        strategy_states: Dict[str, str],
    ) -> Dict[str, float]:
        """
        Compute adjusted weights for all strategies.
        
        Args:
            strategy_states: Dict of {strategy_name: strategy_state}
        
        Returns:
            Dict of {strategy_name: adjusted_weight}
        """
        adjusted = {}
        
        for strategy_name in self.base_weights:
            state = strategy_states.get(strategy_name, "DISABLED")
            adjusted[strategy_name] = self.compute_adjusted_weight(
                strategy_name, state
            )
        
        return adjusted
    
    def validate_base_weights(self) -> bool:
        """
        Validate that base weights sum to 1.0.
        """
        total = sum(self.base_weights.values())
        return abs(total - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyWeightEngine] = None


def get_weight_engine() -> StrategyWeightEngine:
    """Get singleton weight engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyWeightEngine()
    return _engine
