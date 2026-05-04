"""
Doctrine Service
================

Main service for Strategy Doctrine.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple

from .doctrine_types import (
    StrategyType,
    RegimeType,
    ProfileType,
    TimeframeType,
    AssetClass,
    CompatibilityLevel,
    StrategyDefinition,
    DoctrineRule
)
from .strategy_regime_matrix import strategy_regime_matrix
from .strategy_profile_matrix import strategy_profile_matrix
from .strategy_hierarchy import strategy_hierarchy
from .strategy_blocking_rules import blocking_rules_engine, BlockingDecision


class DoctrineService:
    """
    Main service for Strategy Doctrine.
    
    Provides:
    - Strategy definitions
    - Compatibility checks
    - Strategy selection guidance
    - Blocking decisions
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
        
        # Build strategy definitions
        self._strategies = self._build_strategy_definitions()
        
        self._initialized = True
        print("[DoctrineService] Initialized (PHASE 1.1)")
    
    def _build_strategy_definitions(self) -> Dict[StrategyType, StrategyDefinition]:
        """Build complete strategy definitions"""
        
        definitions = {}
        
        # ===========================================
        # TREND_CONFIRMATION
        # ===========================================
        definitions[StrategyType.TREND_CONFIRMATION] = StrategyDefinition(
            strategy_type=StrategyType.TREND_CONFIRMATION,
            name="Trend Confirmation",
            description="Follow established trends with confirmation signals. Primary strategy for trending markets with strong directional momentum.",
            
            regime_compatibility={
                RegimeType.TRENDING: CompatibilityLevel.OPTIMAL,
                RegimeType.LOW_VOLATILITY: CompatibilityLevel.ALLOWED,
                RegimeType.TRANSITION: CompatibilityLevel.CONDITIONAL,
                RegimeType.RANGE: CompatibilityLevel.FORBIDDEN,
                RegimeType.HIGH_VOLATILITY: CompatibilityLevel.FORBIDDEN
            },
            
            profile_compatibility={
                ProfileType.CONSERVATIVE: CompatibilityLevel.OPTIMAL,
                ProfileType.BALANCED: CompatibilityLevel.OPTIMAL,
                ProfileType.AGGRESSIVE: CompatibilityLevel.ALLOWED
            },
            
            timeframe_best=[TimeframeType.H4, TimeframeType.D1],
            timeframe_allowed=[TimeframeType.H1],
            timeframe_forbidden=[TimeframeType.M5, TimeframeType.M15],
            
            asset_best=[AssetClass.BTC, AssetClass.ETH, AssetClass.LARGE_CAP],
            asset_allowed=[AssetClass.MID_CAP],
            
            strengths=[
                "Strong performance in long trends",
                "Works well on macro cycles",
                "Low noise sensitivity",
                "Good win rate in favorable conditions",
                "Clear invalidation levels"
            ],
            weaknesses=[
                "Poor performance in range markets",
                "Susceptible to fake breakouts",
                "Late entries in fast moves",
                "Can miss early trend reversals"
            ],
            
            recovery_allowed=False,
            recovery_conditions=[],
            max_recovery_adds=0
        )
        
        # ===========================================
        # MOMENTUM_BREAKOUT
        # ===========================================
        definitions[StrategyType.MOMENTUM_BREAKOUT] = StrategyDefinition(
            strategy_type=StrategyType.MOMENTUM_BREAKOUT,
            name="Momentum Breakout",
            description="Capture explosive moves on volatility expansion. Aggressive strategy for fast directional moves.",
            
            regime_compatibility={
                RegimeType.TRENDING: CompatibilityLevel.OPTIMAL,
                RegimeType.HIGH_VOLATILITY: CompatibilityLevel.ALLOWED,
                RegimeType.TRANSITION: CompatibilityLevel.CONDITIONAL,
                RegimeType.RANGE: CompatibilityLevel.FORBIDDEN,
                RegimeType.LOW_VOLATILITY: CompatibilityLevel.FORBIDDEN
            },
            
            profile_compatibility={
                ProfileType.CONSERVATIVE: CompatibilityLevel.FORBIDDEN,
                ProfileType.BALANCED: CompatibilityLevel.ALLOWED,
                ProfileType.AGGRESSIVE: CompatibilityLevel.OPTIMAL
            },
            
            timeframe_best=[TimeframeType.H1, TimeframeType.H4],
            timeframe_allowed=[TimeframeType.M15],
            timeframe_forbidden=[TimeframeType.D1],
            
            asset_best=[AssetClass.ALTCOIN, AssetClass.MID_CAP],
            asset_allowed=[AssetClass.BTC, AssetClass.ETH],
            
            strengths=[
                "Captures volatility expansion",
                "Good for news-driven moves",
                "Works on liquidity sweeps",
                "High reward potential",
                "Clear entry signals"
            ],
            weaknesses=[
                "High false breakout rate",
                "Poor in low volatility",
                "Requires fast execution",
                "Higher risk per trade"
            ],
            
            recovery_allowed=False,
            recovery_conditions=[],
            max_recovery_adds=0
        )
        
        # ===========================================
        # MEAN_REVERSION
        # ===========================================
        definitions[StrategyType.MEAN_REVERSION] = StrategyDefinition(
            strategy_type=StrategyType.MEAN_REVERSION,
            name="Mean Reversion",
            description="Trade returns to equilibrium levels. Best in ranging markets with clear support/resistance.",
            
            regime_compatibility={
                RegimeType.RANGE: CompatibilityLevel.OPTIMAL,
                RegimeType.LOW_VOLATILITY: CompatibilityLevel.OPTIMAL,
                RegimeType.TRANSITION: CompatibilityLevel.CONDITIONAL,
                RegimeType.TRENDING: CompatibilityLevel.FORBIDDEN,
                RegimeType.HIGH_VOLATILITY: CompatibilityLevel.FORBIDDEN
            },
            
            profile_compatibility={
                ProfileType.CONSERVATIVE: CompatibilityLevel.OPTIMAL,
                ProfileType.BALANCED: CompatibilityLevel.OPTIMAL,
                ProfileType.AGGRESSIVE: CompatibilityLevel.CONDITIONAL
            },
            
            timeframe_best=[TimeframeType.M15, TimeframeType.H1],
            timeframe_allowed=[TimeframeType.H4],
            timeframe_forbidden=[TimeframeType.D1],
            
            asset_best=[AssetClass.BTC, AssetClass.ETH],
            asset_allowed=[AssetClass.LARGE_CAP],
            
            strengths=[
                "Good in sideways markets",
                "Works with liquidity zones",
                "VWAP reversion setups",
                "Higher win rate",
                "Clear risk levels"
            ],
            weaknesses=[
                "Dangerous in strong trends",
                "Fails in volatility spikes",
                "Requires precise levels",
                "Can extend losses if wrong"
            ],
            
            recovery_allowed=True,
            recovery_conditions=[
                "RANGE regime confirmed",
                "LOW_VOLATILITY regime",
                "Structure intact",
                "Within support zone",
                "Max 2 adds",
                "Total exposure < 5% capital"
            ],
            max_recovery_adds=2
        )
        
        return definitions
    
    # ===========================================
    # Strategy Definitions
    # ===========================================
    
    def get_strategy_definition(self, strategy: StrategyType) -> Optional[StrategyDefinition]:
        """
        Get complete definition for a strategy.
        """
        return self._strategies.get(strategy)
    
    def get_all_strategies(self) -> List[StrategyDefinition]:
        """
        Get all strategy definitions.
        """
        return list(self._strategies.values())
    
    # ===========================================
    # Compatibility Checks
    # ===========================================
    
    def check_strategy_compatibility(
        self,
        strategy: StrategyType,
        regime: Optional[RegimeType] = None,
        profile: Optional[ProfileType] = None,
        timeframe: Optional[TimeframeType] = None
    ) -> Dict[str, Any]:
        """
        Check strategy compatibility with given conditions.
        """
        
        result = {
            "strategy": strategy.value,
            "compatible": True,
            "compatibility": {},
            "warnings": [],
            "blocked": False,
            "blockReason": None
        }
        
        # Check regime compatibility
        if regime:
            regime_compat = strategy_regime_matrix.get_compatibility(strategy, regime)
            result["compatibility"]["regime"] = {
                "regime": regime.value,
                "level": regime_compat.value,
                "allowed": regime_compat != CompatibilityLevel.FORBIDDEN
            }
            if regime_compat == CompatibilityLevel.FORBIDDEN:
                result["compatible"] = False
                result["blocked"] = True
                result["blockReason"] = f"{strategy.value} forbidden in {regime.value}"
            elif regime_compat == CompatibilityLevel.CONDITIONAL:
                result["warnings"].append(f"Reduced confidence in {regime.value}")
        
        # Check profile compatibility
        if profile:
            profile_compat = strategy_profile_matrix.get_compatibility(strategy, profile)
            result["compatibility"]["profile"] = {
                "profile": profile.value,
                "level": profile_compat.value,
                "allowed": profile_compat != CompatibilityLevel.FORBIDDEN
            }
            if profile_compat == CompatibilityLevel.FORBIDDEN:
                result["compatible"] = False
                result["blocked"] = True
                result["blockReason"] = f"{strategy.value} forbidden for {profile.value}"
            elif profile_compat == CompatibilityLevel.CONDITIONAL:
                result["warnings"].append(f"Reduced confidence for {profile.value}")
        
        # Check timeframe
        if timeframe:
            definition = self._strategies.get(strategy)
            if definition:
                if timeframe in definition.timeframe_forbidden:
                    result["compatibility"]["timeframe"] = {
                        "timeframe": timeframe.value,
                        "level": "FORBIDDEN",
                        "allowed": False
                    }
                    result["compatible"] = False
                    result["warnings"].append(f"{timeframe.value} not recommended")
                elif timeframe in definition.timeframe_best:
                    result["compatibility"]["timeframe"] = {
                        "timeframe": timeframe.value,
                        "level": "OPTIMAL",
                        "allowed": True
                    }
                else:
                    result["compatibility"]["timeframe"] = {
                        "timeframe": timeframe.value,
                        "level": "ALLOWED",
                        "allowed": True
                    }
        
        return result
    
    def get_blocking_decision(
        self,
        strategy: StrategyType,
        regime: Optional[RegimeType] = None,
        profile: Optional[ProfileType] = None
    ) -> BlockingDecision:
        """
        Get blocking decision from rules engine.
        """
        return blocking_rules_engine.evaluate(
            strategy=strategy,
            regime=regime,
            profile=profile
        )
    
    # ===========================================
    # Strategy Selection
    # ===========================================
    
    def get_strategy_hierarchy(self, regime: RegimeType) -> Dict[str, Any]:
        """
        Get strategy hierarchy for a regime.
        """
        hierarchy = strategy_hierarchy.get_hierarchy(regime)
        
        if not hierarchy:
            return {
                "regime": regime.value,
                "hierarchy": None
            }
        
        return {
            "regime": regime.value,
            "primaryStrategy": strategy_hierarchy.get_primary_strategy(regime).value if strategy_hierarchy.get_primary_strategy(regime) else None,
            "rankedStrategies": [s.value for s in hierarchy.ranked_strategies],
            "disabledStrategies": [s.value for s in hierarchy.disabled_strategies],
            "confidenceModifiers": {
                s.value: m for s, m in hierarchy.confidence_modifiers.items()
            }
        }
    
    def select_best_strategy(
        self,
        regime: RegimeType,
        profile: ProfileType,
        candidates: Optional[List[StrategyType]] = None
    ) -> Dict[str, Any]:
        """
        Select best strategy for given conditions.
        """
        
        # Default to all strategies if no candidates
        if candidates is None:
            candidates = list(StrategyType)
        
        # Filter by regime
        regime_allowed = [
            s for s in candidates
            if strategy_regime_matrix.is_allowed(s, regime)
        ]
        
        # Filter by profile
        profile_allowed = [
            s for s in regime_allowed
            if strategy_profile_matrix.is_allowed(s, profile)
        ]
        
        if not profile_allowed:
            return {
                "selected": None,
                "reason": "No compatible strategies",
                "candidates": [s.value for s in candidates],
                "regimeFiltered": [s.value for s in regime_allowed],
                "profileFiltered": []
            }
        
        # Select using hierarchy
        result = strategy_hierarchy.select_best_strategy(profile_allowed, regime)
        
        if not result:
            return {
                "selected": None,
                "reason": "Hierarchy selection failed",
                "candidates": [s.value for s in candidates]
            }
        
        selected, base_modifier = result
        
        # Get blocking decision for final modifier
        blocking = blocking_rules_engine.evaluate(selected, regime, profile)
        final_modifier = base_modifier * blocking.final_confidence_modifier
        
        return {
            "selected": selected.value,
            "confidenceModifier": round(final_modifier, 4),
            "regime": regime.value,
            "profile": profile.value,
            "candidates": [s.value for s in candidates],
            "regimeFiltered": [s.value for s in regime_allowed],
            "profileFiltered": [s.value for s in profile_allowed],
            "warnings": blocking.warnings
        }
    
    # ===========================================
    # Matrices
    # ===========================================
    
    def get_regime_matrix(self) -> Dict[str, Any]:
        """
        Get full regime compatibility matrix.
        """
        return {
            "matrix": strategy_regime_matrix.get_matrix_dict(),
            "description": "Strategy-Regime compatibility matrix"
        }
    
    def get_profile_matrix(self) -> Dict[str, Any]:
        """
        Get full profile compatibility matrix.
        """
        return {
            "matrix": strategy_profile_matrix.get_matrix_dict(),
            "description": "Strategy-Profile compatibility matrix"
        }
    
    def get_all_hierarchies(self) -> Dict[str, Any]:
        """
        Get all strategy hierarchies.
        """
        return {
            "hierarchies": strategy_hierarchy.get_all_hierarchies_dict(),
            "description": "Strategy priority hierarchy per regime"
        }
    
    def get_blocking_rules(self) -> Dict[str, Any]:
        """
        Get all blocking rules.
        """
        rules = blocking_rules_engine.get_all_rules()
        return {
            "rules": [r.to_dict() for r in rules],
            "count": len(rules)
        }
    
    # ===========================================
    # Recovery Policy
    # ===========================================
    
    def get_recovery_policy(self, strategy: StrategyType) -> Dict[str, Any]:
        """
        Get recovery policy for a strategy.
        """
        definition = self._strategies.get(strategy)
        
        if not definition:
            return {
                "strategy": strategy.value,
                "recoveryAllowed": False,
                "reason": "Strategy not found"
            }
        
        return {
            "strategy": strategy.value,
            "recoveryAllowed": definition.recovery_allowed,
            "conditions": definition.recovery_conditions,
            "maxAdds": definition.max_recovery_adds
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "PHASE 1.1 Strategy Doctrine",
            "status": "healthy",
            "version": "1.0.0",
            "strategiesLoaded": len(self._strategies),
            "blockingRules": len(blocking_rules_engine.get_all_rules()),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
doctrine_service = DoctrineService()
