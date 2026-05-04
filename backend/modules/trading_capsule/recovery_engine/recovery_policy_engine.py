"""
Recovery Policy Engine
======================

Strategy compatibility for Recovery Engine (PHASE 1.4)
"""

from typing import Dict, List, Optional, Any

from .recovery_types import RecoveryType, RecoveryConfig


class RecoveryPolicyEngine:
    """
    Manages strategy-specific recovery policies.
    
    Recovery is ONLY allowed for specific strategies
    that have statistical edge with averaging.
    """
    
    def __init__(self):
        self._build_strategy_policies()
    
    def _build_strategy_policies(self):
        """Build strategy-specific recovery policies"""
        
        # Strategy -> (allowed, config, reason)
        self._policies: Dict[str, Dict[str, Any]] = {
            # TREND_CONFIRMATION - NO RECOVERY
            "TREND_CONFIRMATION": {
                "allowed": False,
                "recovery_type": RecoveryType.NONE,
                "config": None,
                "reason": "Trend strategies should not average - cut losses quickly",
                "notes": [
                    "Adding to trend trade against direction compounds losses",
                    "Trend may continue further than expected",
                    "Use tight stops instead of averaging"
                ]
            },
            
            # MOMENTUM_BREAKOUT - NO RECOVERY
            "MOMENTUM_BREAKOUT": {
                "allowed": False,
                "recovery_type": RecoveryType.NONE,
                "config": None,
                "reason": "Breakout failures should be cut immediately",
                "notes": [
                    "Failed breakouts often lead to sharp reversals",
                    "Momentum loss indicates trade thesis is wrong",
                    "Never average into failed momentum"
                ]
            },
            
            # MEAN_REVERSION - RECOVERY ALLOWED
            "MEAN_REVERSION": {
                "allowed": True,
                "recovery_type": RecoveryType.CONTROLLED_AVERAGING,
                "config": RecoveryConfig(
                    recovery_type=RecoveryType.CONTROLLED_AVERAGING,
                    max_adds=2,
                    add_size_multiplier=0.5,
                    min_add_size_pct=0.25,
                    max_total_exposure=1.5,
                    max_portfolio_exposure_pct=5.0,
                    min_price_move_pct=0.5,
                    max_loss_before_add_r=0.5,
                    max_position_loss_r=1.5,
                    require_structure_intact=True
                ),
                "reason": "Mean reversion has statistical edge with controlled averaging",
                "notes": [
                    "Price deviation from mean creates better entry",
                    "Averaging improves average price in range-bound market",
                    "Strict limits prevent catastrophic loss",
                    "Only allowed in RANGE/LOW_VOL regimes"
                ]
            }
        }
    
    def is_recovery_allowed(self, strategy: str) -> bool:
        """Check if recovery is allowed for strategy"""
        strategy_upper = strategy.upper()
        if strategy_upper not in self._policies:
            return False
        return self._policies[strategy_upper]["allowed"]
    
    def get_recovery_type(self, strategy: str) -> RecoveryType:
        """Get recovery type for strategy"""
        strategy_upper = strategy.upper()
        if strategy_upper not in self._policies:
            return RecoveryType.NONE
        return self._policies[strategy_upper]["recovery_type"]
    
    def get_config(self, strategy: str) -> Optional[RecoveryConfig]:
        """Get recovery config for strategy"""
        strategy_upper = strategy.upper()
        if strategy_upper not in self._policies:
            return None
        return self._policies[strategy_upper]["config"]
    
    def get_policy(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get full policy for strategy"""
        strategy_upper = strategy.upper()
        if strategy_upper not in self._policies:
            return None
        
        policy = self._policies[strategy_upper]
        return {
            "strategy": strategy_upper,
            "allowed": policy["allowed"],
            "recoveryType": policy["recovery_type"].value,
            "config": policy["config"].to_dict() if policy["config"] else None,
            "reason": policy["reason"],
            "notes": policy["notes"]
        }
    
    def get_all_policies(self) -> List[Dict[str, Any]]:
        """Get all recovery policies"""
        return [self.get_policy(s) for s in self._policies.keys()]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-recovery compatibility matrix"""
        return {
            strategy: {
                "allowed": policy["allowed"],
                "recoveryType": policy["recovery_type"].value,
                "maxAdds": policy["config"].max_adds if policy["config"] else 0,
                "maxExposure": policy["config"].max_total_exposure if policy["config"] else 0
            }
            for strategy, policy in self._policies.items()
        }
    
    def get_allowed_strategies(self) -> List[str]:
        """Get list of strategies that allow recovery"""
        return [
            strategy for strategy, policy in self._policies.items()
            if policy["allowed"]
        ]
    
    def get_forbidden_strategies(self) -> List[str]:
        """Get list of strategies that forbid recovery"""
        return [
            strategy for strategy, policy in self._policies.items()
            if not policy["allowed"]
        ]


# Global singleton
recovery_policy_engine = RecoveryPolicyEngine()
