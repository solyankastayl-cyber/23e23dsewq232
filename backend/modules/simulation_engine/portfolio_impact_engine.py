"""
PHASE 23.1 — Portfolio Impact Engine
====================================
Estimates PnL and drawdown impact from shock scenarios.

Uses portfolio state and risk metrics to calculate:
- Estimated PnL impact
- Estimated drawdown
- Post-shock VaR
- Post-shock tail risk
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .simulation_types import (
    SimulationScenario,
    SurvivalState,
    SurvivalAction,
    SURVIVAL_THRESHOLDS,
    SURVIVAL_MODIFIERS,
)
from .shock_simulator import ShockState


class PortfolioImpactEngine:
    """
    Estimates portfolio impact from shock scenarios.
    
    Uses rule-based approach to estimate PnL, drawdown, and risk metrics.
    """
    
    def __init__(self):
        self.survival_thresholds = SURVIVAL_THRESHOLDS
        self.survival_modifiers = SURVIVAL_MODIFIERS
        
        # Beta assumptions for different asset types
        self.beta_assumptions = {
            "crypto": 1.2,      # Higher beta to market
            "btc": 1.0,         # BTC is the market
            "eth": 1.15,        # Slightly higher
            "alts": 1.4,        # Much higher beta
            "defi": 1.5,        # DeFi highest beta
            "default": 1.0,
        }
    
    def calculate_impact(
        self,
        scenario: SimulationScenario,
        shock_state: ShockState,
        net_exposure: float = 0.5,
        gross_exposure: float = 0.8,
        deployable_capital: float = 1.0,
        capital_efficiency: float = 0.7,
        current_var: float = 0.10,
        current_tail_risk: float = 0.15,
        portfolio_beta: float = 1.0,
        crisis_state: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Calculate portfolio impact from scenario.
        
        Args:
            scenario: Simulation scenario
            shock_state: Post-shock state
            net_exposure: Net portfolio exposure (0-1)
            gross_exposure: Gross portfolio exposure (0-1)
            deployable_capital: Available capital
            capital_efficiency: Capital utilization
            current_var: Current VaR estimate
            current_tail_risk: Current tail risk
            portfolio_beta: Portfolio beta to market
            crisis_state: Current crisis state
            
        Returns:
            Impact estimates
        """
        # Calculate PnL impact
        # Base impact = price shock * net exposure * beta
        base_pnl_impact = shock_state.adjusted_price_change * net_exposure * portfolio_beta
        
        # Adjust for correlation (higher correlation = more impact)
        correlation_amplifier = 1.0 + (shock_state.adjusted_correlation - 0.4) * 0.5
        
        # Adjust for liquidity (lower liquidity = more slippage impact)
        liquidity_penalty = (1.0 - shock_state.adjusted_liquidity) * 0.02
        
        estimated_pnl_impact = base_pnl_impact * correlation_amplifier - liquidity_penalty
        
        # Calculate drawdown
        # Drawdown considers gross exposure and volatility amplification
        vol_amplifier = 1.0 + shock_state.adjusted_volatility * 0.3
        estimated_drawdown = abs(estimated_pnl_impact) * vol_amplifier * (gross_exposure / max(net_exposure, 0.1))
        estimated_drawdown = min(0.50, max(0.0, estimated_drawdown))  # Cap at 50%
        
        # Calculate post-shock VaR
        var_multiplier = 1.0 + shock_state.adjusted_volatility + (shock_state.adjusted_correlation * 0.3)
        estimated_var_post_shock = min(1.0, current_var * var_multiplier)
        
        # Calculate post-shock tail risk
        tail_multiplier = 1.0 + shock_state.adjusted_volatility * 1.2 + shock_state.adjusted_correlation * 0.4
        estimated_tail_risk = min(1.0, current_tail_risk * tail_multiplier)
        
        # Determine survival state
        survival_state = self._get_survival_state(estimated_drawdown)
        
        # Get recommended action
        recommended_action = self._get_recommended_action(survival_state)
        
        # Get modifiers
        modifiers = self.survival_modifiers.get(survival_state, self.survival_modifiers[SurvivalState.STABLE])
        
        # Build reason
        reason = self._build_reason(
            scenario=scenario,
            survival_state=survival_state,
            estimated_drawdown=estimated_drawdown,
            shock_state=shock_state,
        )
        
        return {
            "estimated_pnl_impact": round(estimated_pnl_impact, 4),
            "estimated_drawdown": round(estimated_drawdown, 4),
            "estimated_var_post_shock": round(estimated_var_post_shock, 4),
            "estimated_tail_risk_post_shock": round(estimated_tail_risk, 4),
            "survival_state": survival_state,
            "recommended_action": recommended_action,
            "confidence_modifier": modifiers["confidence_modifier"],
            "capital_modifier": modifiers["capital_modifier"],
            "reason": reason,
            "breakdown": {
                "base_pnl_impact": round(base_pnl_impact, 4),
                "correlation_amplifier": round(correlation_amplifier, 4),
                "liquidity_penalty": round(liquidity_penalty, 4),
                "vol_amplifier": round(vol_amplifier, 4),
            },
        }
    
    def _get_survival_state(self, drawdown: float) -> SurvivalState:
        """Determine survival state from drawdown."""
        if drawdown < self.survival_thresholds[SurvivalState.STABLE]:
            return SurvivalState.STABLE
        elif drawdown < self.survival_thresholds[SurvivalState.STRESSED]:
            return SurvivalState.STRESSED
        elif drawdown < self.survival_thresholds[SurvivalState.FRAGILE]:
            return SurvivalState.FRAGILE
        else:
            return SurvivalState.BROKEN
    
    def _get_recommended_action(self, state: SurvivalState) -> SurvivalAction:
        """Get recommended action from survival state."""
        action_map = {
            SurvivalState.STABLE: SurvivalAction.HOLD,
            SurvivalState.STRESSED: SurvivalAction.HEDGE,
            SurvivalState.FRAGILE: SurvivalAction.DELEVER,
            SurvivalState.BROKEN: SurvivalAction.KILL_SWITCH,
        }
        return action_map.get(state, SurvivalAction.HOLD)
    
    def _build_reason(
        self,
        scenario: SimulationScenario,
        survival_state: SurvivalState,
        estimated_drawdown: float,
        shock_state: ShockState,
    ) -> str:
        """Build explanation reason."""
        scenario_type = scenario.scenario_type.value.lower().replace("_", " ")
        severity = scenario.severity.value.lower()
        
        if survival_state == SurvivalState.STABLE:
            return f"portfolio resilient under {severity} {scenario_type} scenario"
        elif survival_state == SurvivalState.STRESSED:
            return f"{severity} {scenario_type} causes moderate stress, hedging recommended"
        elif survival_state == SurvivalState.FRAGILE:
            return f"high exposure under {scenario_type} scenario ({estimated_drawdown:.1%} drawdown)"
        else:  # BROKEN
            return f"critical exposure under {severity} {scenario_type}, emergency action required"
