"""
Strategy Hierarchy
==================

Определяет приоритет стратегий для каждого режима рынка.
"""

from typing import Dict, List, Optional, Tuple
from .doctrine_types import (
    StrategyType,
    RegimeType,
    StrategyHierarchyEntry
)


class StrategyHierarchy:
    """
    Defines strategy priority hierarchy per regime.
    
    When multiple strategies are allowed, this determines
    which one takes precedence.
    """
    
    def __init__(self):
        self._hierarchy: Dict[RegimeType, StrategyHierarchyEntry] = {
            
            # TRENDING regime
            # Trend strategies dominate
            RegimeType.TRENDING: StrategyHierarchyEntry(
                regime=RegimeType.TRENDING,
                ranked_strategies=[
                    StrategyType.TREND_CONFIRMATION,
                    StrategyType.MOMENTUM_BREAKOUT
                ],
                disabled_strategies=[
                    StrategyType.MEAN_REVERSION
                ],
                confidence_modifiers={
                    StrategyType.TREND_CONFIRMATION: 1.0,
                    StrategyType.MOMENTUM_BREAKOUT: 0.85
                }
            ),
            
            # RANGE regime
            # Mean reversion dominates
            RegimeType.RANGE: StrategyHierarchyEntry(
                regime=RegimeType.RANGE,
                ranked_strategies=[
                    StrategyType.MEAN_REVERSION,
                    StrategyType.TREND_CONFIRMATION
                ],
                disabled_strategies=[
                    StrategyType.MOMENTUM_BREAKOUT
                ],
                confidence_modifiers={
                    StrategyType.MEAN_REVERSION: 1.0,
                    StrategyType.TREND_CONFIRMATION: 0.6
                }
            ),
            
            # HIGH_VOLATILITY regime
            # Momentum strategies for fast moves
            RegimeType.HIGH_VOLATILITY: StrategyHierarchyEntry(
                regime=RegimeType.HIGH_VOLATILITY,
                ranked_strategies=[
                    StrategyType.MOMENTUM_BREAKOUT,
                    StrategyType.TREND_CONFIRMATION
                ],
                disabled_strategies=[
                    StrategyType.MEAN_REVERSION
                ],
                confidence_modifiers={
                    StrategyType.MOMENTUM_BREAKOUT: 1.0,
                    StrategyType.TREND_CONFIRMATION: 0.75
                }
            ),
            
            # LOW_VOLATILITY regime
            # Mean reversion and trend confirmation work
            RegimeType.LOW_VOLATILITY: StrategyHierarchyEntry(
                regime=RegimeType.LOW_VOLATILITY,
                ranked_strategies=[
                    StrategyType.MEAN_REVERSION,
                    StrategyType.TREND_CONFIRMATION
                ],
                disabled_strategies=[
                    StrategyType.MOMENTUM_BREAKOUT
                ],
                confidence_modifiers={
                    StrategyType.MEAN_REVERSION: 1.0,
                    StrategyType.TREND_CONFIRMATION: 0.85
                }
            ),
            
            # TRANSITION regime
            # Cautious approach, reduced confidence
            RegimeType.TRANSITION: StrategyHierarchyEntry(
                regime=RegimeType.TRANSITION,
                ranked_strategies=[
                    StrategyType.TREND_CONFIRMATION,
                    StrategyType.MEAN_REVERSION,
                    StrategyType.MOMENTUM_BREAKOUT
                ],
                disabled_strategies=[],
                confidence_modifiers={
                    StrategyType.TREND_CONFIRMATION: 0.7,
                    StrategyType.MEAN_REVERSION: 0.65,
                    StrategyType.MOMENTUM_BREAKOUT: 0.5
                }
            )
        }
    
    def get_hierarchy(self, regime: RegimeType) -> Optional[StrategyHierarchyEntry]:
        """
        Get hierarchy for a regime.
        """
        return self._hierarchy.get(regime)
    
    def get_primary_strategy(self, regime: RegimeType) -> Optional[StrategyType]:
        """
        Get primary (top-ranked) strategy for regime.
        """
        hierarchy = self.get_hierarchy(regime)
        if hierarchy and hierarchy.ranked_strategies:
            return hierarchy.ranked_strategies[0]
        return None
    
    def get_ranked_strategies(self, regime: RegimeType) -> List[StrategyType]:
        """
        Get strategies ranked by priority for regime.
        """
        hierarchy = self.get_hierarchy(regime)
        if hierarchy:
            return hierarchy.ranked_strategies
        return []
    
    def get_disabled_strategies(self, regime: RegimeType) -> List[StrategyType]:
        """
        Get strategies disabled for regime.
        """
        hierarchy = self.get_hierarchy(regime)
        if hierarchy:
            return hierarchy.disabled_strategies
        return []
    
    def is_strategy_disabled(self, strategy: StrategyType, regime: RegimeType) -> bool:
        """
        Check if strategy is disabled for regime.
        """
        return strategy in self.get_disabled_strategies(regime)
    
    def get_strategy_rank(self, strategy: StrategyType, regime: RegimeType) -> int:
        """
        Get strategy rank in regime (1 = highest).
        Returns 0 if not ranked.
        """
        ranked = self.get_ranked_strategies(regime)
        if strategy in ranked:
            return ranked.index(strategy) + 1
        return 0
    
    def get_confidence_modifier(
        self,
        strategy: StrategyType,
        regime: RegimeType
    ) -> float:
        """
        Get confidence modifier for strategy in regime.
        """
        hierarchy = self.get_hierarchy(regime)
        if hierarchy and strategy in hierarchy.confidence_modifiers:
            return hierarchy.confidence_modifiers[strategy]
        return 0.0
    
    def compare_strategies(
        self,
        strategy_a: StrategyType,
        strategy_b: StrategyType,
        regime: RegimeType
    ) -> int:
        """
        Compare two strategies in a regime.
        Returns:
        - positive if A > B
        - negative if A < B
        - 0 if equal
        """
        rank_a = self.get_strategy_rank(strategy_a, regime)
        rank_b = self.get_strategy_rank(strategy_b, regime)
        
        # Lower rank number = higher priority
        if rank_a == 0 and rank_b == 0:
            return 0
        if rank_a == 0:
            return -1  # B is ranked, A is not
        if rank_b == 0:
            return 1   # A is ranked, B is not
        
        return rank_b - rank_a  # Reversed because lower rank = better
    
    def select_best_strategy(
        self,
        candidates: List[StrategyType],
        regime: RegimeType
    ) -> Optional[Tuple[StrategyType, float]]:
        """
        Select best strategy from candidates for regime.
        Returns (strategy, confidence_modifier).
        """
        ranked = self.get_ranked_strategies(regime)
        disabled = self.get_disabled_strategies(regime)
        
        # Filter out disabled
        valid = [s for s in candidates if s not in disabled]
        
        if not valid:
            return None
        
        # Sort by rank
        valid_ranked = sorted(
            valid,
            key=lambda s: ranked.index(s) if s in ranked else 999
        )
        
        best = valid_ranked[0]
        modifier = self.get_confidence_modifier(best, regime)
        
        return (best, modifier)
    
    def get_all_hierarchies_dict(self) -> dict:
        """
        Get all hierarchies as dictionary.
        """
        return {
            regime.value: entry.to_dict()
            for regime, entry in self._hierarchy.items()
        }


# Global singleton
strategy_hierarchy = StrategyHierarchy()
