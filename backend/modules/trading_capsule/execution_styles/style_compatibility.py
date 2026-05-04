"""
Style Compatibility Matrix
==========================

Матрицы совместимости стилей со стратегиями и профилями.
"""

from typing import Dict, List, Optional
from .execution_style_types import (
    ExecutionStyleType,
    StyleCompatibilityLevel
)

# Import strategy types from doctrine
try:
    from modules.trading_capsule.strategy_doctrine.doctrine_types import (
        StrategyType,
        ProfileType,
        RegimeType
    )
except ImportError:
    # Fallback if doctrine not available
    from enum import Enum
    class StrategyType(str, Enum):
        TREND_CONFIRMATION = "TREND_CONFIRMATION"
        MOMENTUM_BREAKOUT = "MOMENTUM_BREAKOUT"
        MEAN_REVERSION = "MEAN_REVERSION"
    
    class ProfileType(str, Enum):
        CONSERVATIVE = "CONSERVATIVE"
        BALANCED = "BALANCED"
        AGGRESSIVE = "AGGRESSIVE"
    
    class RegimeType(str, Enum):
        TRENDING = "TRENDING"
        RANGE = "RANGE"
        HIGH_VOLATILITY = "HIGH_VOLATILITY"
        LOW_VOLATILITY = "LOW_VOLATILITY"
        TRANSITION = "TRANSITION"


class StyleCompatibilityMatrix:
    """
    Matrix of style compatibility with strategies, profiles, and regimes.
    """
    
    def __init__(self):
        self._build_strategy_matrix()
        self._build_profile_matrix()
        self._build_regime_matrix()
    
    def _build_strategy_matrix(self):
        """Build strategy-style compatibility matrix"""
        
        self._strategy_matrix: Dict[str, Dict[ExecutionStyleType, StyleCompatibilityLevel]] = {
            
            # TREND_CONFIRMATION
            "TREND_CONFIRMATION": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            },
            
            # MOMENTUM_BREAKOUT
            "MOMENTUM_BREAKOUT": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.FORBIDDEN,  # No scaling in momentum
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.OPTIMAL,       # Important for momentum
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            },
            
            # MEAN_REVERSION
            "MEAN_REVERSION": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.OPTIMAL,    # Best for mean reversion
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            }
        }
    
    def _build_profile_matrix(self):
        """Build profile-style compatibility matrix"""
        
        self._profile_matrix: Dict[str, Dict[ExecutionStyleType, StyleCompatibilityLevel]] = {
            
            # CONSERVATIVE
            "CONSERVATIVE": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.FORBIDDEN,  # Too risky
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            },
            
            # BALANCED
            "BALANCED": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            },
            
            # AGGRESSIVE
            "AGGRESSIVE": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.CONDITIONAL,  # Only where doctrine allows
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.ALLOWED
            }
        }
    
    def _build_regime_matrix(self):
        """Build regime-style compatibility matrix"""
        
        self._regime_matrix: Dict[str, Dict[ExecutionStyleType, StyleCompatibilityLevel]] = {
            
            # TRENDING
            "TRENDING": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.CONDITIONAL,
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.ALLOWED
            },
            
            # RANGE
            "RANGE": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.OPTIMAL,    # Best in range
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            },
            
            # HIGH_VOLATILITY
            "HIGH_VOLATILITY": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.FORBIDDEN,  # Too risky
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            },
            
            # LOW_VOLATILITY
            "LOW_VOLATILITY": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.ALLOWED,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.ALLOWED
            },
            
            # TRANSITION
            "TRANSITION": {
                ExecutionStyleType.CLEAN_ENTRY: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.SCALED_ENTRY: StyleCompatibilityLevel.FORBIDDEN,
                ExecutionStyleType.PARTIAL_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.TIME_EXIT: StyleCompatibilityLevel.OPTIMAL,
                ExecutionStyleType.DEFENSIVE_EXIT: StyleCompatibilityLevel.OPTIMAL
            }
        }
    
    # ===========================================
    # Strategy Compatibility
    # ===========================================
    
    def get_strategy_compatibility(
        self,
        strategy: str,
        style: ExecutionStyleType
    ) -> StyleCompatibilityLevel:
        """Get compatibility level for strategy-style pair"""
        strategy_upper = strategy.upper()
        if strategy_upper not in self._strategy_matrix:
            return StyleCompatibilityLevel.FORBIDDEN
        return self._strategy_matrix[strategy_upper].get(style, StyleCompatibilityLevel.FORBIDDEN)
    
    def is_style_allowed_for_strategy(
        self,
        strategy: str,
        style: ExecutionStyleType
    ) -> bool:
        """Check if style is allowed for strategy"""
        compat = self.get_strategy_compatibility(strategy, style)
        return compat != StyleCompatibilityLevel.FORBIDDEN
    
    def get_allowed_styles_for_strategy(self, strategy: str) -> List[ExecutionStyleType]:
        """Get list of allowed styles for a strategy"""
        return [
            style for style in ExecutionStyleType
            if self.is_style_allowed_for_strategy(strategy, style)
        ]
    
    # ===========================================
    # Profile Compatibility
    # ===========================================
    
    def get_profile_compatibility(
        self,
        profile: str,
        style: ExecutionStyleType
    ) -> StyleCompatibilityLevel:
        """Get compatibility level for profile-style pair"""
        profile_upper = profile.upper()
        if profile_upper not in self._profile_matrix:
            return StyleCompatibilityLevel.FORBIDDEN
        return self._profile_matrix[profile_upper].get(style, StyleCompatibilityLevel.FORBIDDEN)
    
    def is_style_allowed_for_profile(
        self,
        profile: str,
        style: ExecutionStyleType
    ) -> bool:
        """Check if style is allowed for profile"""
        compat = self.get_profile_compatibility(profile, style)
        return compat != StyleCompatibilityLevel.FORBIDDEN
    
    def get_allowed_styles_for_profile(self, profile: str) -> List[ExecutionStyleType]:
        """Get list of allowed styles for a profile"""
        return [
            style for style in ExecutionStyleType
            if self.is_style_allowed_for_profile(profile, style)
        ]
    
    # ===========================================
    # Regime Compatibility
    # ===========================================
    
    def get_regime_compatibility(
        self,
        regime: str,
        style: ExecutionStyleType
    ) -> StyleCompatibilityLevel:
        """Get compatibility level for regime-style pair"""
        regime_upper = regime.upper()
        if regime_upper not in self._regime_matrix:
            return StyleCompatibilityLevel.ALLOWED  # Default to allowed if regime unknown
        return self._regime_matrix[regime_upper].get(style, StyleCompatibilityLevel.ALLOWED)
    
    def is_style_allowed_in_regime(
        self,
        regime: str,
        style: ExecutionStyleType
    ) -> bool:
        """Check if style is allowed in regime"""
        compat = self.get_regime_compatibility(regime, style)
        return compat != StyleCompatibilityLevel.FORBIDDEN
    
    # ===========================================
    # Combined Compatibility
    # ===========================================
    
    def check_full_compatibility(
        self,
        style: ExecutionStyleType,
        strategy: Optional[str] = None,
        profile: Optional[str] = None,
        regime: Optional[str] = None
    ) -> Dict[str, any]:
        """Check style compatibility across all dimensions"""
        
        result = {
            "style": style.value,
            "allowed": True,
            "compatibility": {},
            "blocked_by": None,
            "warnings": []
        }
        
        # Check strategy
        if strategy:
            strat_compat = self.get_strategy_compatibility(strategy, style)
            result["compatibility"]["strategy"] = {
                "strategy": strategy,
                "level": strat_compat.value
            }
            if strat_compat == StyleCompatibilityLevel.FORBIDDEN:
                result["allowed"] = False
                result["blocked_by"] = f"strategy:{strategy}"
            elif strat_compat == StyleCompatibilityLevel.CONDITIONAL:
                result["warnings"].append(f"Conditional for {strategy}")
        
        # Check profile
        if profile and result["allowed"]:
            prof_compat = self.get_profile_compatibility(profile, style)
            result["compatibility"]["profile"] = {
                "profile": profile,
                "level": prof_compat.value
            }
            if prof_compat == StyleCompatibilityLevel.FORBIDDEN:
                result["allowed"] = False
                result["blocked_by"] = f"profile:{profile}"
            elif prof_compat == StyleCompatibilityLevel.CONDITIONAL:
                result["warnings"].append(f"Conditional for {profile}")
        
        # Check regime
        if regime and result["allowed"]:
            reg_compat = self.get_regime_compatibility(regime, style)
            result["compatibility"]["regime"] = {
                "regime": regime,
                "level": reg_compat.value
            }
            if reg_compat == StyleCompatibilityLevel.FORBIDDEN:
                result["allowed"] = False
                result["blocked_by"] = f"regime:{regime}"
            elif reg_compat == StyleCompatibilityLevel.CONDITIONAL:
                result["warnings"].append(f"Conditional in {regime}")
        
        return result
    
    # ===========================================
    # Export Matrices
    # ===========================================
    
    def get_strategy_matrix_dict(self) -> dict:
        """Get strategy matrix as dictionary"""
        return {
            strat: {style.value: level.value for style, level in styles.items()}
            for strat, styles in self._strategy_matrix.items()
        }
    
    def get_profile_matrix_dict(self) -> dict:
        """Get profile matrix as dictionary"""
        return {
            prof: {style.value: level.value for style, level in styles.items()}
            for prof, styles in self._profile_matrix.items()
        }
    
    def get_regime_matrix_dict(self) -> dict:
        """Get regime matrix as dictionary"""
        return {
            reg: {style.value: level.value for style, level in styles.items()}
            for reg, styles in self._regime_matrix.items()
        }


# Global singleton
style_compatibility_matrix = StyleCompatibilityMatrix()
