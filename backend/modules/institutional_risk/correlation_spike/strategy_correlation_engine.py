"""
PHASE 22.4 — Strategy Correlation Engine
========================================
Calculates correlation between active strategies.

When similar strategies are active, effective correlation increases.
"""

from typing import Dict, Any, Optional, List
from .correlation_types import STRATEGY_TYPE_CORRELATION


class StrategyCorrelationEngine:
    """
    Calculates strategy-level correlation.
    
    Similar strategy types (trend + breakout) have high correlation.
    Diverse strategies (trend + mean_reversion) have low correlation.
    """
    
    def __init__(self):
        self.type_correlation = STRATEGY_TYPE_CORRELATION
        
        # Strategy to type mapping
        self.strategy_types = {
            "MTF_BREAKOUT": "breakout",
            "CHANNEL_BREAKOUT": "breakout",
            "MOMENTUM_CONTINUATION": "momentum",
            "DOUBLE_BOTTOM": "reversal",
            "DOUBLE_TOP": "reversal",
            "HEAD_SHOULDERS": "reversal",
            "HARMONIC_ABCD": "mean_reversion",
            "WEDGE_RISING": "trend",
            "WEDGE_FALLING": "trend",
            "TREND_FOLLOWING": "trend",
            "MEAN_REVERSION": "mean_reversion",
            "ARB_SPOT_PERP": "arb",
            "ARB_CROSS_EXCHANGE": "arb",
        }
    
    def calculate(
        self,
        active_strategies: Optional[List[str]] = None,
        strategy_allocations: Optional[Dict[str, float]] = None,
        volatility_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Calculate strategy correlation.
        
        Args:
            active_strategies: List of active strategy IDs
            strategy_allocations: Dict of strategy -> allocation weight
            volatility_state: Current volatility regime
            
        Returns:
            Strategy correlation metrics
        """
        if not active_strategies:
            active_strategies = []
        
        if not strategy_allocations:
            strategy_allocations = {s: 1.0 / max(len(active_strategies), 1) for s in active_strategies}
        
        if len(active_strategies) <= 1:
            return {
                "strategy_correlation": 0.0,
                "strategy_count": len(active_strategies),
                "type_breakdown": {},
                "pair_correlations": {},
                "reason": "single_strategy_or_none",
            }
        
        # Group by type
        type_weights = {}
        for strategy in active_strategies:
            s_type = self.strategy_types.get(strategy, "unknown")
            weight = strategy_allocations.get(strategy, 0)
            type_weights[s_type] = type_weights.get(s_type, 0) + weight
        
        # Calculate weighted correlation
        total_correlation = 0.0
        pair_correlations = {}
        weight_sum = 0.0
        
        types = list(type_weights.keys())
        for i, type1 in enumerate(types):
            for type2 in types[i:]:
                w1 = type_weights.get(type1, 0)
                w2 = type_weights.get(type2, 0)
                
                if type1 == type2:
                    # Same type = perfect correlation
                    corr = 0.85
                else:
                    # Look up pair correlation
                    key = (type1, type2) if (type1, type2) in self.type_correlation else (type2, type1)
                    corr = self.type_correlation.get(key, 0.35)
                
                pair_weight = w1 * w2
                total_correlation += corr * pair_weight
                weight_sum += pair_weight
                pair_correlations[f"{type1}_{type2}"] = round(corr, 4)
        
        strategy_correlation = total_correlation / max(weight_sum, 0.001)
        
        # Volatility adjustment
        if volatility_state.upper() in ["HIGH", "EXPANDING", "EXTREME", "CRISIS"]:
            strategy_correlation = min(1.0, strategy_correlation * 1.2)
        
        return {
            "strategy_correlation": round(min(1.0, max(0, strategy_correlation)), 4),
            "strategy_count": len(active_strategies),
            "type_breakdown": {k: round(v, 4) for k, v in type_weights.items()},
            "pair_correlations": pair_correlations,
            "volatility_state": volatility_state,
        }
    
    def get_type_diversity(self, active_strategies: List[str]) -> float:
        """
        Calculate type diversity score.
        
        Higher = more diverse strategy types.
        """
        types = set()
        for strategy in active_strategies:
            types.add(self.strategy_types.get(strategy, "unknown"))
        
        if len(active_strategies) == 0:
            return 1.0
        
        return min(1.0, len(types) / max(len(active_strategies), 1))
