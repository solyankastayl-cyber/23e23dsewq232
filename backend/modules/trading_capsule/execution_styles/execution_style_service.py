"""
Execution Style Service
=======================

Main service for Execution Styles (PHASE 1.2)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .execution_style_types import (
    ExecutionStyleType,
    ExecutionStyleDefinition,
    StyleCompatibilityLevel
)
from .execution_style_registry import style_registry
from .style_compatibility import style_compatibility_matrix
from .style_policy import style_policy_engine, StylePolicyDecision


class ExecutionStyleService:
    """
    Main service for Execution Styles.
    
    Provides:
    - Style definitions
    - Compatibility checks
    - Style selection
    - Policy evaluation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        print("[ExecutionStyleService] Initialized (PHASE 1.2)")
    
    # ===========================================
    # Style Definitions
    # ===========================================
    
    def get_all_styles(self) -> List[ExecutionStyleDefinition]:
        """Get all execution style definitions"""
        return style_registry.get_all_styles()
    
    def get_style(self, style_type: ExecutionStyleType) -> Optional[ExecutionStyleDefinition]:
        """Get specific style definition"""
        return style_registry.get_style(style_type)
    
    def get_entry_styles(self) -> List[ExecutionStyleDefinition]:
        """Get entry-focused styles"""
        return style_registry.get_entry_styles()
    
    def get_exit_styles(self) -> List[ExecutionStyleDefinition]:
        """Get exit-focused styles"""
        return style_registry.get_exit_styles()
    
    # ===========================================
    # Compatibility
    # ===========================================
    
    def check_style_compatibility(
        self,
        style: ExecutionStyleType,
        strategy: Optional[str] = None,
        profile: Optional[str] = None,
        regime: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check style compatibility with conditions.
        """
        return style_compatibility_matrix.check_full_compatibility(
            style=style,
            strategy=strategy,
            profile=profile,
            regime=regime
        )
    
    def get_compatible_styles_for_strategy(self, strategy: str) -> Dict[str, Any]:
        """
        Get all styles with compatibility levels for a strategy.
        """
        styles = {}
        for style_type in ExecutionStyleType:
            compat = style_compatibility_matrix.get_strategy_compatibility(strategy, style_type)
            styles[style_type.value] = {
                "level": compat.value,
                "allowed": compat != StyleCompatibilityLevel.FORBIDDEN
            }
        
        return {
            "strategy": strategy.upper(),
            "styles": styles,
            "allowedStyles": [s for s, v in styles.items() if v["allowed"]]
        }
    
    def get_compatible_styles_for_profile(self, profile: str) -> Dict[str, Any]:
        """
        Get all styles with compatibility levels for a profile.
        """
        styles = {}
        for style_type in ExecutionStyleType:
            compat = style_compatibility_matrix.get_profile_compatibility(profile, style_type)
            styles[style_type.value] = {
                "level": compat.value,
                "allowed": compat != StyleCompatibilityLevel.FORBIDDEN
            }
        
        return {
            "profile": profile.upper(),
            "styles": styles,
            "allowedStyles": [s for s, v in styles.items() if v["allowed"]]
        }
    
    # ===========================================
    # Style Selection
    # ===========================================
    
    def select_styles(
        self,
        strategy: str,
        profile: str,
        regime: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select allowed execution styles for given conditions.
        """
        
        styles_evaluation = style_policy_engine.select_allowed_styles(
            strategy=strategy,
            profile=profile,
            regime=regime
        )
        
        allowed = [s for s in styles_evaluation if s["allowed"]]
        blocked = [s for s in styles_evaluation if s["blocked"]]
        
        # Recommend best entry and exit style
        recommended_entry = None
        recommended_exit = None
        
        for s in allowed:
            style_type = ExecutionStyleType(s["style"])
            if style_type in [ExecutionStyleType.CLEAN_ENTRY, ExecutionStyleType.SCALED_ENTRY]:
                if recommended_entry is None:
                    recommended_entry = s["style"]
            elif style_type in [ExecutionStyleType.PARTIAL_EXIT, ExecutionStyleType.TIME_EXIT, ExecutionStyleType.DEFENSIVE_EXIT]:
                if recommended_exit is None:
                    recommended_exit = s["style"]
        
        return {
            "strategy": strategy.upper(),
            "profile": profile.upper(),
            "regime": regime.upper() if regime else None,
            "styles": styles_evaluation,
            "allowedCount": len(allowed),
            "blockedCount": len(blocked),
            "recommended": {
                "entryStyle": recommended_entry,
                "exitStyle": recommended_exit
            },
            "timestamp": int(time.time() * 1000)
        }
    
    def get_recommended_style_combination(
        self,
        strategy: str,
        profile: str,
        regime: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recommended entry + exit style combination.
        """
        
        selection = self.select_styles(strategy, profile, regime)
        allowed_styles = [s["style"] for s in selection["styles"] if s["allowed"]]
        
        # Default recommendations
        entry_style = ExecutionStyleType.CLEAN_ENTRY
        exit_style = ExecutionStyleType.PARTIAL_EXIT
        
        # Strategy-specific recommendations
        strategy_upper = strategy.upper()
        
        if strategy_upper == "MEAN_REVERSION":
            # Mean reversion prefers scaled entry if allowed
            if ExecutionStyleType.SCALED_ENTRY.value in allowed_styles:
                entry_style = ExecutionStyleType.SCALED_ENTRY
        
        elif strategy_upper == "MOMENTUM_BREAKOUT":
            # Momentum prefers time exit
            exit_style = ExecutionStyleType.TIME_EXIT
        
        elif strategy_upper == "TREND_CONFIRMATION":
            # Trend prefers partial exit for runners
            exit_style = ExecutionStyleType.PARTIAL_EXIT
        
        # Verify recommendations are allowed
        if entry_style.value not in allowed_styles:
            entry_style = ExecutionStyleType.CLEAN_ENTRY
        
        if exit_style.value not in allowed_styles:
            for fallback in [ExecutionStyleType.PARTIAL_EXIT, ExecutionStyleType.DEFENSIVE_EXIT]:
                if fallback.value in allowed_styles:
                    exit_style = fallback
                    break
        
        return {
            "strategy": strategy_upper,
            "profile": profile.upper(),
            "regime": regime.upper() if regime else None,
            "recommendation": {
                "entryStyle": entry_style.value,
                "exitStyle": exit_style.value,
                "defensiveStyle": ExecutionStyleType.DEFENSIVE_EXIT.value  # Always available
            },
            "entryDetails": style_registry.get_style(entry_style).to_dict() if style_registry.get_style(entry_style) else None,
            "exitDetails": style_registry.get_style(exit_style).to_dict() if style_registry.get_style(exit_style) else None
        }
    
    # ===========================================
    # Policy Evaluation
    # ===========================================
    
    def evaluate_style_policy(
        self,
        style: ExecutionStyleType,
        strategy: Optional[str] = None,
        profile: Optional[str] = None,
        regime: Optional[str] = None
    ) -> StylePolicyDecision:
        """
        Evaluate style against policy rules.
        """
        return style_policy_engine.evaluate(
            style=style,
            strategy=strategy,
            profile=profile,
            regime=regime
        )
    
    def get_policy_rules(self) -> Dict[str, Any]:
        """
        Get all policy rules.
        """
        rules = style_policy_engine.get_all_rules()
        return {
            "rules": [r.to_dict() for r in rules],
            "count": len(rules)
        }
    
    # ===========================================
    # Matrices
    # ===========================================
    
    def get_strategy_matrix(self) -> Dict[str, Any]:
        """
        Get style-strategy compatibility matrix.
        """
        return {
            "matrix": style_compatibility_matrix.get_strategy_matrix_dict(),
            "description": "Style-Strategy compatibility matrix"
        }
    
    def get_profile_matrix(self) -> Dict[str, Any]:
        """
        Get style-profile compatibility matrix.
        """
        return {
            "matrix": style_compatibility_matrix.get_profile_matrix_dict(),
            "description": "Style-Profile compatibility matrix"
        }
    
    def get_regime_matrix(self) -> Dict[str, Any]:
        """
        Get style-regime compatibility matrix.
        """
        return {
            "matrix": style_compatibility_matrix.get_regime_matrix_dict(),
            "description": "Style-Regime compatibility matrix"
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "PHASE 1.2 Execution Styles",
            "status": "healthy",
            "version": "1.0.0",
            "stylesLoaded": len(style_registry.get_all_styles()),
            "policyRules": len(style_policy_engine.get_all_rules()),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
execution_style_service = ExecutionStyleService()
