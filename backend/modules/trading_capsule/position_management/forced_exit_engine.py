"""
Forced Exit Engine
==================

Engine for forced exit rules (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .position_policy_types import (
    ForcedExitTrigger,
    ForcedExitConfig
)


@dataclass
class ForcedExitDecision:
    """Decision for forced exit"""
    force_exit: bool
    triggers_fired: List[ForcedExitTrigger]
    exit_urgency: str  # "immediate", "next_bar", "reduce_only"
    exit_size_pct: float
    reasons: List[str]
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "forceExit": self.force_exit,
            "triggersFired": [t.value for t in self.triggers_fired],
            "exitUrgency": self.exit_urgency,
            "exitSizePct": round(self.exit_size_pct, 4),
            "reasons": self.reasons,
            "notes": self.notes
        }


class ForcedExitEngine:
    """
    Engine for evaluating forced exit conditions.
    """
    
    def __init__(self):
        self._configs = self._build_default_configs()
    
    def _build_default_configs(self) -> Dict[str, ForcedExitConfig]:
        """Build default forced exit configs per strategy"""
        
        return {
            # TREND_CONFIRMATION
            "TREND_CONFIRMATION": ForcedExitConfig(
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
            
            # MOMENTUM_BREAKOUT
            "MOMENTUM_BREAKOUT": ForcedExitConfig(
                triggers=[
                    ForcedExitTrigger.REGIME_SWITCH,
                    ForcedExitTrigger.VOLATILITY_SPIKE,
                    ForcedExitTrigger.STRUCTURE_BREAK,
                    ForcedExitTrigger.RISK_LIMIT_BREACH
                ],
                exit_on_regime_switch=True,
                allowed_regime_transitions=[],  # Exit on any regime change
                volatility_exit_threshold=2.0,
                structure_break_exit=True,
                max_position_loss_pct=1.5,
                max_daily_loss_pct=4.0
            ),
            
            # MEAN_REVERSION
            "MEAN_REVERSION": ForcedExitConfig(
                triggers=[
                    ForcedExitTrigger.REGIME_SWITCH,
                    ForcedExitTrigger.VOLATILITY_SPIKE,
                    ForcedExitTrigger.RISK_LIMIT_BREACH,
                    ForcedExitTrigger.DRAWDOWN_LIMIT
                ],
                exit_on_regime_switch=True,
                allowed_regime_transitions=["RANGE->LOW_VOLATILITY"],
                volatility_exit_threshold=1.8,  # Lower threshold
                structure_break_exit=False,  # Mean reversion expects some structure break
                max_position_loss_pct=2.5,  # Higher for averaging
                max_daily_loss_pct=5.0
            )
        }
    
    def evaluate_forced_exit(
        self,
        strategy: str,
        current_regime: str,
        previous_regime: Optional[str] = None,
        current_volatility: float = 1.0,  # Normalized (1.0 = normal)
        normal_volatility: float = 1.0,
        structure_broken: bool = False,
        position_pnl_pct: float = 0.0,
        daily_pnl_pct: float = 0.0,
        correlation_spike: bool = False
    ) -> ForcedExitDecision:
        """
        Evaluate forced exit conditions.
        """
        
        strategy_upper = strategy.upper()
        config = self._configs.get(strategy_upper, self._configs["MOMENTUM_BREAKOUT"])
        
        triggers_fired = []
        reasons = []
        notes = []
        force_exit = False
        exit_urgency = "none"
        exit_size_pct = 0.0
        
        # Check regime switch
        if ForcedExitTrigger.REGIME_SWITCH in config.triggers:
            if previous_regime and current_regime != previous_regime:
                transition = f"{previous_regime}->{current_regime}"
                if config.exit_on_regime_switch:
                    if transition not in config.allowed_regime_transitions:
                        triggers_fired.append(ForcedExitTrigger.REGIME_SWITCH)
                        reasons.append(f"Regime switched: {transition}")
                        force_exit = True
                        exit_urgency = "next_bar"
                        exit_size_pct = 1.0
                    else:
                        notes.append(f"Regime transition {transition} allowed")
        
        # Check volatility spike
        if ForcedExitTrigger.VOLATILITY_SPIKE in config.triggers:
            vol_ratio = current_volatility / normal_volatility if normal_volatility > 0 else 1.0
            if vol_ratio > config.volatility_exit_threshold:
                triggers_fired.append(ForcedExitTrigger.VOLATILITY_SPIKE)
                reasons.append(f"Volatility spike: {vol_ratio:.1f}x normal (threshold: {config.volatility_exit_threshold}x)")
                force_exit = True
                exit_urgency = "immediate"
                exit_size_pct = 1.0
        
        # Check structure break
        if ForcedExitTrigger.STRUCTURE_BREAK in config.triggers:
            if structure_broken and config.structure_break_exit:
                triggers_fired.append(ForcedExitTrigger.STRUCTURE_BREAK)
                reasons.append("Market structure broken")
                force_exit = True
                exit_urgency = "immediate"
                exit_size_pct = 1.0
        
        # Check risk limits
        if ForcedExitTrigger.RISK_LIMIT_BREACH in config.triggers:
            if abs(position_pnl_pct) > config.max_position_loss_pct and position_pnl_pct < 0:
                triggers_fired.append(ForcedExitTrigger.RISK_LIMIT_BREACH)
                reasons.append(f"Position loss {position_pnl_pct:.2f}% > max {config.max_position_loss_pct}%")
                force_exit = True
                exit_urgency = "immediate"
                exit_size_pct = 1.0
            
            if abs(daily_pnl_pct) > config.max_daily_loss_pct and daily_pnl_pct < 0:
                triggers_fired.append(ForcedExitTrigger.RISK_LIMIT_BREACH)
                reasons.append(f"Daily loss {daily_pnl_pct:.2f}% > max {config.max_daily_loss_pct}%")
                force_exit = True
                exit_urgency = "immediate"
                exit_size_pct = 1.0
        
        # Check drawdown
        if ForcedExitTrigger.DRAWDOWN_LIMIT in config.triggers:
            if position_pnl_pct < -config.max_position_loss_pct:
                triggers_fired.append(ForcedExitTrigger.DRAWDOWN_LIMIT)
                reasons.append(f"Drawdown limit reached: {position_pnl_pct:.2f}%")
                force_exit = True
                exit_urgency = "immediate"
                exit_size_pct = 1.0
        
        # Check correlation spike
        if ForcedExitTrigger.CORRELATION_SPIKE in config.triggers:
            if correlation_spike:
                triggers_fired.append(ForcedExitTrigger.CORRELATION_SPIKE)
                reasons.append("Correlation spike detected (portfolio risk)")
                force_exit = True
                exit_urgency = "reduce_only"
                exit_size_pct = 0.5  # Reduce 50%
        
        if not triggers_fired:
            notes.append("No forced exit triggers fired")
        
        return ForcedExitDecision(
            force_exit=force_exit,
            triggers_fired=triggers_fired,
            exit_urgency=exit_urgency,
            exit_size_pct=exit_size_pct,
            reasons=reasons,
            notes=notes
        )
    
    def get_config_for_strategy(self, strategy: str) -> ForcedExitConfig:
        """Get forced exit config for strategy"""
        return self._configs.get(strategy.upper(), self._configs["MOMENTUM_BREAKOUT"])
    
    def get_all_exit_triggers(self) -> List[Dict[str, Any]]:
        """Get all exit triggers with descriptions"""
        return [
            {
                "trigger": ForcedExitTrigger.REGIME_SWITCH.value,
                "name": "Regime Switch",
                "description": "Exit when market regime changes",
                "severity": "HIGH",
                "defaultAction": "Exit next bar"
            },
            {
                "trigger": ForcedExitTrigger.VOLATILITY_SPIKE.value,
                "name": "Volatility Spike",
                "description": "Exit on abnormal volatility increase",
                "severity": "HIGH",
                "defaultAction": "Exit immediately"
            },
            {
                "trigger": ForcedExitTrigger.STRUCTURE_BREAK.value,
                "name": "Structure Break",
                "description": "Exit when market structure invalidated",
                "severity": "HIGH",
                "defaultAction": "Exit immediately"
            },
            {
                "trigger": ForcedExitTrigger.RISK_LIMIT_BREACH.value,
                "name": "Risk Limit Breach",
                "description": "Exit when position or daily loss exceeds limits",
                "severity": "CRITICAL",
                "defaultAction": "Exit immediately"
            },
            {
                "trigger": ForcedExitTrigger.CORRELATION_SPIKE.value,
                "name": "Correlation Spike",
                "description": "Reduce when portfolio correlation increases",
                "severity": "MEDIUM",
                "defaultAction": "Reduce position"
            },
            {
                "trigger": ForcedExitTrigger.DRAWDOWN_LIMIT.value,
                "name": "Drawdown Limit",
                "description": "Exit when max drawdown reached",
                "severity": "CRITICAL",
                "defaultAction": "Exit immediately"
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-forced exit matrix"""
        return {
            strategy: {
                "triggers": [t.value for t in config.triggers],
                "exitOnRegimeSwitch": config.exit_on_regime_switch,
                "volatilityThreshold": config.volatility_exit_threshold,
                "maxPositionLossPct": config.max_position_loss_pct,
                "maxDailyLossPct": config.max_daily_loss_pct
            }
            for strategy, config in self._configs.items()
        }


# Global singleton
forced_exit_engine = ForcedExitEngine()
