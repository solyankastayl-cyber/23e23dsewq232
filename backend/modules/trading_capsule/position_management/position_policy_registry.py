"""
Position Policy Registry
========================

Registry of complete position policies (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any

from .position_policy_types import (
    PositionPolicy,
    StopLossConfig,
    TakeProfitConfig,
    TrailingStopConfig,
    PartialCloseConfig,
    TimeStopConfig,
    ForcedExitConfig,
    StopLossType,
    StopPlacement,
    TakeProfitType,
    TPPlacement,
    TrailingStopType,
    TrailingActivation,
    PartialCloseType,
    TimeStopType,
    ForcedExitTrigger
)


class PositionPolicyRegistry:
    """
    Registry of complete position management policies per strategy.
    """
    
    def __init__(self):
        self._policies: Dict[str, PositionPolicy] = {}
        self._build_policies()
    
    def _build_policies(self):
        """Build policies for each strategy"""
        
        # ============================================
        # TREND_CONFIRMATION Policy
        # ============================================
        self._policies["TREND_CONFIRMATION"] = PositionPolicy(
            policy_id="TREND_CONFIRMATION_POLICY",
            name="Trend Confirmation Position Policy",
            description="Structure-based stops, trailing TP, structure trailing, multi-partial close",
            
            stop_loss=StopLossConfig(
                stop_type=StopLossType.STRUCTURE_STOP,
                placement=StopPlacement.SWING_LOW,
                structure_buffer_pct=0.1,
                lookback_bars=20,
                max_stop_distance_pct=2.5,
                min_stop_distance_pct=0.3
            ),
            
            take_profit=TakeProfitConfig(
                tp_type=TakeProfitType.TRAILING_TP,
                placement=TPPlacement.TRAILING,
                rr_ratio=2.0,
                trailing_activation_pct=0.5,
                trailing_distance_pct=0.3,
                use_multiple_targets=True,
                targets=[
                    {"rr": 1.0, "sizePct": 0.3},
                    {"rr": 2.0, "sizePct": 0.3},
                    {"rr": 0, "sizePct": 0.4, "trailing": True}
                ]
            ),
            
            trailing_stop=TrailingStopConfig(
                trailing_type=TrailingStopType.STRUCTURE_TRAILING,
                activation=TrailingActivation.AT_FIRST_TP,
                structure_lookback=5,
                activation_profit_pct=0.5
            ),
            
            partial_close=PartialCloseConfig(
                partial_type=PartialCloseType.FIXED_LEVELS,
                levels=[
                    {"targetPct": 0.5, "closePct": 0.3},
                    {"targetPct": 1.0, "closePct": 0.3},
                    {"targetPct": 2.0, "closePct": 0.4}
                ],
                move_to_breakeven=True,
                breakeven_buffer_pct=0.1
            ),
            
            time_stop=TimeStopConfig(
                time_stop_type=TimeStopType.BAR_BASED,
                max_bars=50,
                exit_at_loss=False,
                reduce_only=True,
                partial_exit_pct=0.5
            ),
            
            forced_exit=ForcedExitConfig(
                triggers=[
                    ForcedExitTrigger.REGIME_SWITCH,
                    ForcedExitTrigger.STRUCTURE_BREAK,
                    ForcedExitTrigger.RISK_LIMIT_BREACH
                ],
                exit_on_regime_switch=True,
                allowed_regime_transitions=["TRENDING->LOW_VOLATILITY"],
                volatility_exit_threshold=2.5,
                structure_break_exit=True,
                max_position_loss_pct=2.0,
                max_daily_loss_pct=5.0
            ),
            
            compatible_strategies=["TREND_CONFIRMATION"],
            primary_strategy="TREND_CONFIRMATION"
        )
        
        # ============================================
        # MOMENTUM_BREAKOUT Policy
        # ============================================
        self._policies["MOMENTUM_BREAKOUT"] = PositionPolicy(
            policy_id="MOMENTUM_BREAKOUT_POLICY",
            name="Momentum Breakout Position Policy",
            description="Hard stops, fixed RR, ATR trailing, required time stop",
            
            stop_loss=StopLossConfig(
                stop_type=StopLossType.HARD_STOP,
                placement=StopPlacement.FIXED_DISTANCE,
                risk_distance_pct=1.0,
                max_stop_distance_pct=2.0,
                min_stop_distance_pct=0.5
            ),
            
            take_profit=TakeProfitConfig(
                tp_type=TakeProfitType.FIXED_RR,
                placement=TPPlacement.RR_RATIO,
                rr_ratio=2.0,
                use_multiple_targets=True,
                targets=[
                    {"rr": 1.5, "sizePct": 0.5},
                    {"rr": 2.5, "sizePct": 0.5}
                ]
            ),
            
            trailing_stop=TrailingStopConfig(
                trailing_type=TrailingStopType.ATR_TRAILING,
                activation=TrailingActivation.AT_BREAKEVEN,
                atr_multiplier=1.5,
                atr_period=14,
                activation_profit_pct=0.3
            ),
            
            partial_close=PartialCloseConfig(
                partial_type=PartialCloseType.FIXED_LEVELS,
                levels=[
                    {"targetPct": 0.5, "closePct": 0.5},
                    {"targetPct": 1.0, "closePct": 0.5}
                ],
                move_to_breakeven=True,
                breakeven_buffer_pct=0.1
            ),
            
            time_stop=TimeStopConfig(
                time_stop_type=TimeStopType.BAR_BASED,
                max_bars=10,
                exit_at_loss=True,
                reduce_only=False,
                partial_exit_pct=1.0
            ),
            
            forced_exit=ForcedExitConfig(
                triggers=[
                    ForcedExitTrigger.REGIME_SWITCH,
                    ForcedExitTrigger.VOLATILITY_SPIKE,
                    ForcedExitTrigger.STRUCTURE_BREAK,
                    ForcedExitTrigger.RISK_LIMIT_BREACH
                ],
                exit_on_regime_switch=True,
                allowed_regime_transitions=[],
                volatility_exit_threshold=2.0,
                structure_break_exit=True,
                max_position_loss_pct=1.5,
                max_daily_loss_pct=4.0
            ),
            
            compatible_strategies=["MOMENTUM_BREAKOUT"],
            primary_strategy="MOMENTUM_BREAKOUT"
        )
        
        # ============================================
        # MEAN_REVERSION Policy
        # ============================================
        self._policies["MEAN_REVERSION"] = PositionPolicy(
            policy_id="MEAN_REVERSION_POLICY",
            name="Mean Reversion Position Policy",
            description="Structure stops, structure TP, no trailing, required time stop",
            
            stop_loss=StopLossConfig(
                stop_type=StopLossType.STRUCTURE_STOP,
                placement=StopPlacement.SUPPORT_LEVEL,
                structure_buffer_pct=0.15,
                lookback_bars=30,
                max_stop_distance_pct=3.0,
                min_stop_distance_pct=0.4
            ),
            
            take_profit=TakeProfitConfig(
                tp_type=TakeProfitType.STRUCTURE_TP,
                placement=TPPlacement.RESISTANCE,
                structure_levels=["resistance", "vwap", "liquidity"],
                rr_ratio=1.5,
                use_multiple_targets=True,
                targets=[
                    {"rr": 1.0, "sizePct": 0.5},
                    {"rr": 1.5, "sizePct": 0.5}
                ]
            ),
            
            trailing_stop=TrailingStopConfig(
                trailing_type=TrailingStopType.NONE,
                activation=TrailingActivation.AT_FIRST_TP
            ),
            
            partial_close=PartialCloseConfig(
                partial_type=PartialCloseType.FIXED_LEVELS,
                levels=[
                    {"targetPct": 0.7, "closePct": 0.5},
                    {"targetPct": 1.0, "closePct": 0.5}
                ],
                move_to_breakeven=True,
                breakeven_buffer_pct=0.15
            ),
            
            time_stop=TimeStopConfig(
                time_stop_type=TimeStopType.BAR_BASED,
                max_bars=30,
                exit_at_loss=True,
                reduce_only=False,
                partial_exit_pct=1.0
            ),
            
            forced_exit=ForcedExitConfig(
                triggers=[
                    ForcedExitTrigger.REGIME_SWITCH,
                    ForcedExitTrigger.VOLATILITY_SPIKE,
                    ForcedExitTrigger.RISK_LIMIT_BREACH,
                    ForcedExitTrigger.DRAWDOWN_LIMIT
                ],
                exit_on_regime_switch=True,
                allowed_regime_transitions=["RANGE->LOW_VOLATILITY"],
                volatility_exit_threshold=1.8,
                structure_break_exit=False,
                max_position_loss_pct=2.5,
                max_daily_loss_pct=5.0
            ),
            
            compatible_strategies=["MEAN_REVERSION"],
            primary_strategy="MEAN_REVERSION"
        )
    
    def get_policy(self, strategy: str) -> Optional[PositionPolicy]:
        """Get policy for strategy"""
        return self._policies.get(strategy.upper())
    
    def get_all_policies(self) -> List[PositionPolicy]:
        """Get all policies"""
        return list(self._policies.values())
    
    def get_policy_summary(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get policy summary for strategy"""
        policy = self.get_policy(strategy)
        if not policy:
            return None
        
        return {
            "policyId": policy.policy_id,
            "name": policy.name,
            "strategy": policy.primary_strategy,
            "summary": {
                "stopType": policy.stop_loss.stop_type.value,
                "tpType": policy.take_profit.tp_type.value,
                "trailingType": policy.trailing_stop.trailing_type.value,
                "partialClose": policy.partial_close.partial_type.value,
                "timeStop": policy.time_stop.time_stop_type.value,
                "forcedExitTriggers": len(policy.forced_exit.triggers)
            }
        }
    
    def get_strategy_policy_matrix(self) -> Dict[str, Dict[str, str]]:
        """Get matrix of strategies to policy components"""
        return {
            strategy: {
                "stop": policy.stop_loss.stop_type.value,
                "tp": policy.take_profit.tp_type.value,
                "trailing": policy.trailing_stop.trailing_type.value,
                "partialClose": "YES" if policy.partial_close.partial_type != PartialCloseType.NONE else "NO",
                "timeStop": "REQUIRED" if policy.time_stop.time_stop_type != TimeStopType.NONE else "OPTIONAL"
            }
            for strategy, policy in self._policies.items()
        }


# Global singleton
position_policy_registry = PositionPolicyRegistry()
