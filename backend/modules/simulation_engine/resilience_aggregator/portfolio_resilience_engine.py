"""
PHASE 23.4 — Portfolio Resilience Engine
========================================
Core engine that combines Stress Grid and Strategy Survival into unified resilience.

Formula:
resilience_score = 0.55 * stress_grid_score + 0.45 * strategy_survival_score
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..stress_grid.stress_grid_aggregator import StressGridAggregator
from ..stress_grid.stress_grid_types import StressGridState, ResilienceState as GridResilienceState

from ..strategy_survival.strategy_survival_aggregator import StrategySurvivalAggregator
from ..strategy_survival.strategy_survival_types import (
    StrategySurvivalMatrix,
    StrategySurvivalStateEnum,
)

from .resilience_types import (
    PortfolioResilienceState,
    ResilienceStateEnum,
    ResilienceAction,
    RESILIENCE_THRESHOLDS,
    RESILIENCE_MODIFIERS,
    RESILIENCE_WEIGHTS,
    STRESS_GRID_SCORES,
    STRATEGY_SURVIVAL_SCORES,
)


class PortfolioResilienceEngine:
    """
    Combines Stress Grid and Strategy Survival into unified resilience state.
    
    This is the final resilience overlay for the simulation engine.
    """
    
    def __init__(self):
        self.stress_grid_aggregator = StressGridAggregator()
        self.strategy_survival_aggregator = StrategySurvivalAggregator()
        self.weights = RESILIENCE_WEIGHTS
        self.thresholds = RESILIENCE_THRESHOLDS
    
    def calculate(
        self,
        # Portfolio parameters
        net_exposure: float = 0.5,
        gross_exposure: float = 0.8,
        deployable_capital: float = 1.0,
        
        # Risk metrics
        current_var: float = 0.10,
        current_tail_risk: float = 0.15,
        current_volatility: float = 0.20,
        current_correlation: float = 0.40,
        
        # Portfolio characteristics
        portfolio_beta: float = 1.0,
        crisis_state: str = "NORMAL",
        
        # Strategy list
        strategies: Optional[list] = None,
    ) -> PortfolioResilienceState:
        """
        Calculate unified portfolio resilience state.
        
        Args:
            Portfolio, risk, and strategy parameters
            
        Returns:
            PortfolioResilienceState with combined analysis
        """
        # Run Stress Grid
        stress_grid = self.stress_grid_aggregator.run_grid(
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            deployable_capital=deployable_capital,
            current_var=current_var,
            current_tail_risk=current_tail_risk,
            current_volatility=current_volatility,
            current_correlation=current_correlation,
            portfolio_beta=portfolio_beta,
            crisis_state=crisis_state,
        )
        
        # Run Strategy Survival Matrix
        strategy_matrix = self.strategy_survival_aggregator.build_matrix(
            strategies=strategies,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            deployable_capital=deployable_capital,
            current_var=current_var,
            current_tail_risk=current_tail_risk,
            current_volatility=current_volatility,
            current_correlation=current_correlation,
            portfolio_beta=portfolio_beta,
            crisis_state=crisis_state,
        )
        
        # Get component states
        stress_grid_state = stress_grid.system_resilience_state.value
        
        # Derive strategy survival state from average robustness
        strategy_survival_state = self._derive_strategy_state(
            strategy_matrix.average_system_strategy_robustness
        )
        
        # Calculate component scores
        stress_grid_score = STRESS_GRID_SCORES.get(stress_grid_state, 0.50)
        strategy_survival_score = STRATEGY_SURVIVAL_SCORES.get(strategy_survival_state, 0.50)
        
        # Calculate weighted resilience score
        resilience_score = (
            self.weights["stress_grid"] * stress_grid_score +
            self.weights["strategy_survival"] * strategy_survival_score
        )
        
        # Get resilience state
        resilience_state = self._get_resilience_state(resilience_score)
        
        # Get recommended action
        recommended_action = self._get_recommended_action(resilience_state)
        
        # Get modifiers
        modifiers = RESILIENCE_MODIFIERS.get(resilience_state, RESILIENCE_MODIFIERS[ResilienceStateEnum.STABLE])
        
        # Determine strongest and weakest components
        strongest_component = "stress_grid" if stress_grid_score >= strategy_survival_score else "strategy_survival"
        weakest_component = "strategy_survival" if stress_grid_score >= strategy_survival_score else "stress_grid"
        
        # Build reason
        reason = self._build_reason(
            resilience_state=resilience_state,
            stress_grid_state=stress_grid_state,
            strategy_survival_state=strategy_survival_state,
            strongest_component=strongest_component,
            weakest_component=weakest_component,
        )
        
        return PortfolioResilienceState(
            stress_grid_state=stress_grid_state,
            strategy_survival_state=strategy_survival_state,
            resilience_score=resilience_score,
            resilience_state=resilience_state,
            average_drawdown=stress_grid.average_drawdown,
            worst_drawdown=stress_grid.worst_drawdown,
            fragility_index=stress_grid.fragility_index,
            average_strategy_robustness=strategy_matrix.average_system_strategy_robustness,
            most_robust_strategy=strategy_matrix.most_robust,
            most_fragile_strategy=strategy_matrix.most_fragile,
            recommended_action=recommended_action,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            strongest_component=strongest_component,
            weakest_component=weakest_component,
            reason=reason,
            stress_grid_score=stress_grid_score,
            strategy_survival_score=strategy_survival_score,
        )
    
    def _derive_strategy_state(self, avg_robustness: float) -> str:
        """Derive strategy survival state from average robustness."""
        if avg_robustness >= 0.70:
            return "ROBUST"
        elif avg_robustness >= 0.50:
            return "STABLE"
        elif avg_robustness >= 0.30:
            return "FRAGILE"
        else:
            return "BROKEN"
    
    def _get_resilience_state(self, resilience_score: float) -> ResilienceStateEnum:
        """Determine resilience state from score."""
        if resilience_score >= self.thresholds[ResilienceStateEnum.ROBUST]:
            return ResilienceStateEnum.ROBUST
        elif resilience_score >= self.thresholds[ResilienceStateEnum.STABLE]:
            return ResilienceStateEnum.STABLE
        elif resilience_score >= self.thresholds[ResilienceStateEnum.FRAGILE]:
            return ResilienceStateEnum.FRAGILE
        else:
            return ResilienceStateEnum.CRITICAL
    
    def _get_recommended_action(self, state: ResilienceStateEnum) -> ResilienceAction:
        """Get recommended action from resilience state."""
        action_map = {
            ResilienceStateEnum.ROBUST: ResilienceAction.HOLD,
            ResilienceStateEnum.STABLE: ResilienceAction.HEDGE,
            ResilienceStateEnum.FRAGILE: ResilienceAction.DELEVER,
            ResilienceStateEnum.CRITICAL: ResilienceAction.KILL_SWITCH,
        }
        return action_map.get(state, ResilienceAction.HEDGE)
    
    def _build_reason(
        self,
        resilience_state: ResilienceStateEnum,
        stress_grid_state: str,
        strategy_survival_state: str,
        strongest_component: str,
        weakest_component: str,
    ) -> str:
        """Build explanation reason."""
        component_labels = {
            "stress_grid": "system stress profile",
            "strategy_survival": "strategy set",
        }
        
        strongest_label = component_labels.get(strongest_component, strongest_component)
        weakest_label = component_labels.get(weakest_component, weakest_component)
        
        if resilience_state == ResilienceStateEnum.ROBUST:
            return f"strong resilience across both {strongest_label} and {weakest_label}"
        
        elif resilience_state == ResilienceStateEnum.STABLE:
            return f"acceptable resilience with {strongest_label} supporting overall stability"
        
        elif resilience_state == ResilienceStateEnum.FRAGILE:
            if weakest_component == "strategy_survival":
                return f"portfolio resilience weakened by fragile {weakest_label} despite acceptable {strongest_label}"
            return f"portfolio resilience weakened by {weakest_label}, {strongest_label} providing some support"
        
        else:  # CRITICAL
            return f"critical resilience failure in both {strongest_label} ({stress_grid_state}) and {weakest_label} ({strategy_survival_state})"
    
    def get_drivers(self, state: PortfolioResilienceState) -> Dict[str, Any]:
        """Get detailed breakdown of resilience drivers."""
        return {
            "components": {
                "stress_grid": {
                    "state": state.stress_grid_state,
                    "score": round(state.stress_grid_score, 4),
                    "weight": self.weights["stress_grid"],
                    "contribution": round(state.stress_grid_score * self.weights["stress_grid"], 4),
                    "metrics": {
                        "fragility_index": round(state.fragility_index, 4),
                        "average_drawdown": round(state.average_drawdown, 4),
                        "worst_drawdown": round(state.worst_drawdown, 4),
                    },
                },
                "strategy_survival": {
                    "state": state.strategy_survival_state,
                    "score": round(state.strategy_survival_score, 4),
                    "weight": self.weights["strategy_survival"],
                    "contribution": round(state.strategy_survival_score * self.weights["strategy_survival"], 4),
                    "metrics": {
                        "average_robustness": round(state.average_strategy_robustness, 4),
                        "most_robust": state.most_robust_strategy,
                        "most_fragile": state.most_fragile_strategy,
                    },
                },
            },
            "strongest_component": state.strongest_component,
            "weakest_component": state.weakest_component,
            "total_resilience_score": round(state.resilience_score, 4),
            "resilience_state": state.resilience_state.value,
        }
    
    def calculate_from_states(
        self,
        stress_grid_state: StressGridState,
        strategy_matrix: StrategySurvivalMatrix,
    ) -> PortfolioResilienceState:
        """
        Calculate resilience from pre-computed states.
        
        Convenience method when stress grid and strategy matrix are already available.
        """
        # Get component states
        grid_state_str = stress_grid_state.system_resilience_state.value
        
        # Derive strategy state
        strategy_state_str = self._derive_strategy_state(
            strategy_matrix.average_system_strategy_robustness
        )
        
        # Calculate scores
        stress_grid_score = STRESS_GRID_SCORES.get(grid_state_str, 0.50)
        strategy_survival_score = STRATEGY_SURVIVAL_SCORES.get(strategy_state_str, 0.50)
        
        # Calculate weighted resilience score
        resilience_score = (
            self.weights["stress_grid"] * stress_grid_score +
            self.weights["strategy_survival"] * strategy_survival_score
        )
        
        # Get states and actions
        resilience_state = self._get_resilience_state(resilience_score)
        recommended_action = self._get_recommended_action(resilience_state)
        modifiers = RESILIENCE_MODIFIERS.get(resilience_state, RESILIENCE_MODIFIERS[ResilienceStateEnum.STABLE])
        
        # Determine components
        strongest_component = "stress_grid" if stress_grid_score >= strategy_survival_score else "strategy_survival"
        weakest_component = "strategy_survival" if stress_grid_score >= strategy_survival_score else "stress_grid"
        
        # Build reason
        reason = self._build_reason(
            resilience_state=resilience_state,
            stress_grid_state=grid_state_str,
            strategy_survival_state=strategy_state_str,
            strongest_component=strongest_component,
            weakest_component=weakest_component,
        )
        
        return PortfolioResilienceState(
            stress_grid_state=grid_state_str,
            strategy_survival_state=strategy_state_str,
            resilience_score=resilience_score,
            resilience_state=resilience_state,
            average_drawdown=stress_grid_state.average_drawdown,
            worst_drawdown=stress_grid_state.worst_drawdown,
            fragility_index=stress_grid_state.fragility_index,
            average_strategy_robustness=strategy_matrix.average_system_strategy_robustness,
            most_robust_strategy=strategy_matrix.most_robust,
            most_fragile_strategy=strategy_matrix.most_fragile,
            recommended_action=recommended_action,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            strongest_component=strongest_component,
            weakest_component=weakest_component,
            reason=reason,
            stress_grid_score=stress_grid_score,
            strategy_survival_score=strategy_survival_score,
        )
