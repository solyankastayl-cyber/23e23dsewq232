"""
Strategy-Regime Compatibility Matrix
====================================

Определяет совместимость стратегий с режимами рынка.
"""

from typing import Dict, Optional
from .doctrine_types import (
    StrategyType,
    RegimeType,
    CompatibilityLevel
)


class StrategyRegimeMatrix:
    """
    Matrix of strategy-regime compatibility.
    
    Defines where each strategy is:
    - OPTIMAL (best fit)
    - ALLOWED (can be used)
    - CONDITIONAL (reduced confidence)
    - FORBIDDEN (blocked)
    """
    
    def __init__(self):
        self._matrix: Dict[StrategyType, Dict[RegimeType, CompatibilityLevel]] = {
            
            # TREND_CONFIRMATION
            # Основная стратегия трендовых рынков
            StrategyType.TREND_CONFIRMATION: {
                RegimeType.TRENDING: CompatibilityLevel.OPTIMAL,
                RegimeType.LOW_VOLATILITY: CompatibilityLevel.ALLOWED,
                RegimeType.TRANSITION: CompatibilityLevel.CONDITIONAL,
                RegimeType.RANGE: CompatibilityLevel.FORBIDDEN,
                RegimeType.HIGH_VOLATILITY: CompatibilityLevel.FORBIDDEN
            },
            
            # MOMENTUM_BREAKOUT
            # Стратегия импульса и пробоев
            StrategyType.MOMENTUM_BREAKOUT: {
                RegimeType.TRENDING: CompatibilityLevel.OPTIMAL,
                RegimeType.HIGH_VOLATILITY: CompatibilityLevel.ALLOWED,
                RegimeType.TRANSITION: CompatibilityLevel.CONDITIONAL,
                RegimeType.RANGE: CompatibilityLevel.FORBIDDEN,
                RegimeType.LOW_VOLATILITY: CompatibilityLevel.FORBIDDEN
            },
            
            # MEAN_REVERSION
            # Стратегия возврата к среднему
            StrategyType.MEAN_REVERSION: {
                RegimeType.RANGE: CompatibilityLevel.OPTIMAL,
                RegimeType.LOW_VOLATILITY: CompatibilityLevel.OPTIMAL,
                RegimeType.TRANSITION: CompatibilityLevel.CONDITIONAL,
                RegimeType.TRENDING: CompatibilityLevel.FORBIDDEN,
                RegimeType.HIGH_VOLATILITY: CompatibilityLevel.FORBIDDEN
            }
        }
    
    def get_compatibility(
        self,
        strategy: StrategyType,
        regime: RegimeType
    ) -> CompatibilityLevel:
        """
        Get compatibility level for strategy-regime pair.
        """
        if strategy not in self._matrix:
            return CompatibilityLevel.FORBIDDEN
        
        return self._matrix[strategy].get(regime, CompatibilityLevel.FORBIDDEN)
    
    def is_allowed(
        self,
        strategy: StrategyType,
        regime: RegimeType
    ) -> bool:
        """
        Check if strategy is allowed in regime.
        """
        compat = self.get_compatibility(strategy, regime)
        return compat in [
            CompatibilityLevel.OPTIMAL,
            CompatibilityLevel.ALLOWED,
            CompatibilityLevel.CONDITIONAL
        ]
    
    def is_optimal(
        self,
        strategy: StrategyType,
        regime: RegimeType
    ) -> bool:
        """
        Check if strategy is optimal for regime.
        """
        return self.get_compatibility(strategy, regime) == CompatibilityLevel.OPTIMAL
    
    def is_forbidden(
        self,
        strategy: StrategyType,
        regime: RegimeType
    ) -> bool:
        """
        Check if strategy is forbidden in regime.
        """
        return self.get_compatibility(strategy, regime) == CompatibilityLevel.FORBIDDEN
    
    def get_confidence_modifier(
        self,
        strategy: StrategyType,
        regime: RegimeType
    ) -> float:
        """
        Get confidence modifier based on compatibility.
        """
        compat = self.get_compatibility(strategy, regime)
        
        modifiers = {
            CompatibilityLevel.OPTIMAL: 1.0,
            CompatibilityLevel.ALLOWED: 0.85,
            CompatibilityLevel.CONDITIONAL: 0.6,
            CompatibilityLevel.FORBIDDEN: 0.0
        }
        
        return modifiers.get(compat, 0.0)
    
    def get_allowed_strategies(self, regime: RegimeType) -> list:
        """
        Get list of allowed strategies for a regime.
        """
        allowed = []
        for strategy in StrategyType:
            if self.is_allowed(strategy, regime):
                allowed.append(strategy)
        return allowed
    
    def get_optimal_strategies(self, regime: RegimeType) -> list:
        """
        Get list of optimal strategies for a regime.
        """
        optimal = []
        for strategy in StrategyType:
            if self.is_optimal(strategy, regime):
                optimal.append(strategy)
        return optimal
    
    def get_matrix_dict(self) -> dict:
        """
        Get full matrix as dictionary.
        """
        result = {}
        for strategy, regimes in self._matrix.items():
            result[strategy.value] = {
                r.value: c.value for r, c in regimes.items()
            }
        return result


# Global singleton
strategy_regime_matrix = StrategyRegimeMatrix()
