"""
Recovery Registry
=================

Central registry for Recovery Engine (PHASE 1.4)
"""

from typing import Dict, List, Optional, Any

from .recovery_types import RecoveryType, RecoveryConfig
from .recovery_policy_engine import recovery_policy_engine
from .recovery_regime_filter import recovery_regime_filter
from .recovery_structure_filter import recovery_structure_filter
from .recovery_risk_limits import recovery_risk_limits


class RecoveryRegistry:
    """
    Central registry for recovery configurations.
    
    Provides unified access to all recovery rules and matrices.
    """
    
    def __init__(self):
        pass
    
    def get_recovery_types(self) -> List[Dict[str, Any]]:
        """Get all recovery types with descriptions"""
        return [
            {
                "type": RecoveryType.CONTROLLED_AVERAGING.value,
                "name": "Controlled Averaging",
                "description": "Add to losing position with strict limits",
                "maxAdds": 2,
                "sizePattern": "Decreasing (50%, 25%)",
                "allowedStrategies": ["MEAN_REVERSION"],
                "risk": "MODERATE"
            },
            {
                "type": RecoveryType.RE_ENTRY.value,
                "name": "Re-Entry",
                "description": "Re-enter after partial exit at better price",
                "maxAdds": 1,
                "sizePattern": "Fixed",
                "allowedStrategies": ["MEAN_REVERSION"],
                "risk": "LOW"
            },
            {
                "type": RecoveryType.NONE.value,
                "name": "No Recovery",
                "description": "Cut losses, no averaging",
                "maxAdds": 0,
                "sizePattern": "N/A",
                "allowedStrategies": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
                "risk": "LOWEST"
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Any]:
        """Get strategy-recovery compatibility matrix"""
        return {
            "matrix": recovery_policy_engine.get_strategy_matrix(),
            "allowedStrategies": recovery_policy_engine.get_allowed_strategies(),
            "forbiddenStrategies": recovery_policy_engine.get_forbidden_strategies(),
            "description": "Only MEAN_REVERSION allows controlled averaging"
        }
    
    def get_regime_matrix(self) -> Dict[str, Any]:
        """Get regime-recovery compatibility matrix"""
        return {
            "matrix": recovery_regime_filter.get_regime_matrix(),
            "allowedRegimes": recovery_regime_filter.get_allowed_regimes(),
            "forbiddenRegimes": recovery_regime_filter.get_forbidden_regimes(),
            "description": "Recovery only in RANGE/LOW_VOL, forbidden in TRENDING/HIGH_VOL"
        }
    
    def get_structure_requirements(self) -> Dict[str, Any]:
        """Get structure requirements for recovery"""
        return recovery_structure_filter.get_structure_requirements()
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Get risk limits for recovery"""
        return recovery_risk_limits.get_risk_limits_summary()
    
    def get_complete_recovery_rules(self) -> Dict[str, Any]:
        """Get all recovery rules in one response"""
        return {
            "recoveryTypes": self.get_recovery_types(),
            "strategyMatrix": self.get_strategy_matrix(),
            "regimeMatrix": self.get_regime_matrix(),
            "structureRequirements": self.get_structure_requirements(),
            "riskLimits": self.get_risk_limits(),
            "summary": {
                "allowedStrategies": 1,
                "allowedRegimes": 3,  # RANGE, LOW_VOL, TRANSITION(conditional)
                "maxAdds": 2,
                "maxExposure": "1.5x base",
                "keyPrinciple": "Never increase risk beyond policy limits"
            }
        }
    
    def get_blocking_rules(self) -> List[Dict[str, Any]]:
        """Get all blocking rules for recovery"""
        return [
            {
                "ruleId": "BLOCK_TREND_RECOVERY",
                "condition": "strategy = TREND_CONFIRMATION",
                "action": "DENY",
                "reason": "Trend strategies must not average"
            },
            {
                "ruleId": "BLOCK_MOMENTUM_RECOVERY",
                "condition": "strategy = MOMENTUM_BREAKOUT",
                "action": "DENY",
                "reason": "Momentum failures must be cut immediately"
            },
            {
                "ruleId": "BLOCK_TRENDING_REGIME",
                "condition": "regime = TRENDING",
                "action": "DENY",
                "reason": "Trending market will compound losses"
            },
            {
                "ruleId": "BLOCK_HIGH_VOL_REGIME",
                "condition": "regime = HIGH_VOLATILITY",
                "action": "DENY",
                "reason": "High volatility makes recovery too risky"
            },
            {
                "ruleId": "BLOCK_STRUCTURE_BREAK",
                "condition": "structure_broken = true",
                "action": "DENY",
                "reason": "Broken structure invalidates mean reversion thesis"
            },
            {
                "ruleId": "BLOCK_MAX_ADDS",
                "condition": "current_adds >= 2",
                "action": "DENY",
                "reason": "Maximum adds reached"
            },
            {
                "ruleId": "BLOCK_EXPOSURE_LIMIT",
                "condition": "exposure >= 1.5x",
                "action": "DENY",
                "reason": "Position exposure limit reached"
            },
            {
                "ruleId": "BLOCK_UNHEALTHY_POSITION",
                "condition": "position_loss > 1.5R",
                "action": "FORCE_EXIT",
                "reason": "Position too unhealthy for recovery"
            }
        ]


# Global singleton
recovery_registry = RecoveryRegistry()
