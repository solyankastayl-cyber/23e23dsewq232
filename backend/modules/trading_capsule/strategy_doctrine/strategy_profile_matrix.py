"""
Strategy-Profile Compatibility Matrix
=====================================

Определяет совместимость стратегий с risk профилями.
"""

from typing import Dict
from .doctrine_types import (
    StrategyType,
    ProfileType,
    CompatibilityLevel
)


class StrategyProfileMatrix:
    """
    Matrix of strategy-profile compatibility.
    
    Risk profiles affect which strategies are available.
    """
    
    def __init__(self):
        self._matrix: Dict[StrategyType, Dict[ProfileType, CompatibilityLevel]] = {
            
            # TREND_CONFIRMATION
            # Допустима для всех профилей
            StrategyType.TREND_CONFIRMATION: {
                ProfileType.CONSERVATIVE: CompatibilityLevel.OPTIMAL,
                ProfileType.BALANCED: CompatibilityLevel.OPTIMAL,
                ProfileType.AGGRESSIVE: CompatibilityLevel.ALLOWED
            },
            
            # MOMENTUM_BREAKOUT
            # Требует более высокого риск-аппетита
            StrategyType.MOMENTUM_BREAKOUT: {
                ProfileType.CONSERVATIVE: CompatibilityLevel.FORBIDDEN,
                ProfileType.BALANCED: CompatibilityLevel.ALLOWED,
                ProfileType.AGGRESSIVE: CompatibilityLevel.OPTIMAL
            },
            
            # MEAN_REVERSION
            # Хорошо для консервативных и сбалансированных
            StrategyType.MEAN_REVERSION: {
                ProfileType.CONSERVATIVE: CompatibilityLevel.OPTIMAL,
                ProfileType.BALANCED: CompatibilityLevel.OPTIMAL,
                ProfileType.AGGRESSIVE: CompatibilityLevel.CONDITIONAL
            }
        }
    
    def get_compatibility(
        self,
        strategy: StrategyType,
        profile: ProfileType
    ) -> CompatibilityLevel:
        """
        Get compatibility level for strategy-profile pair.
        """
        if strategy not in self._matrix:
            return CompatibilityLevel.FORBIDDEN
        
        return self._matrix[strategy].get(profile, CompatibilityLevel.FORBIDDEN)
    
    def is_allowed(
        self,
        strategy: StrategyType,
        profile: ProfileType
    ) -> bool:
        """
        Check if strategy is allowed for profile.
        """
        compat = self.get_compatibility(strategy, profile)
        return compat != CompatibilityLevel.FORBIDDEN
    
    def get_confidence_modifier(
        self,
        strategy: StrategyType,
        profile: ProfileType
    ) -> float:
        """
        Get confidence modifier based on profile compatibility.
        """
        compat = self.get_compatibility(strategy, profile)
        
        modifiers = {
            CompatibilityLevel.OPTIMAL: 1.0,
            CompatibilityLevel.ALLOWED: 0.9,
            CompatibilityLevel.CONDITIONAL: 0.7,
            CompatibilityLevel.FORBIDDEN: 0.0
        }
        
        return modifiers.get(compat, 0.0)
    
    def get_allowed_strategies(self, profile: ProfileType) -> list:
        """
        Get list of allowed strategies for a profile.
        """
        allowed = []
        for strategy in StrategyType:
            if self.is_allowed(strategy, profile):
                allowed.append(strategy)
        return allowed
    
    def get_matrix_dict(self) -> dict:
        """
        Get full matrix as dictionary.
        """
        result = {}
        for strategy, profiles in self._matrix.items():
            result[strategy.value] = {
                p.value: c.value for p, c in profiles.items()
            }
        return result


# Global singleton
strategy_profile_matrix = StrategyProfileMatrix()
