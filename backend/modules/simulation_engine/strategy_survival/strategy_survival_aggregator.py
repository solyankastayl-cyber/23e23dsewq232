"""
PHASE 23.3 — Strategy Survival Aggregator
=========================================
Main entry point for strategy survival analysis.

Combines:
- Strategy Scenario Runner
- Strategy Survival Engine

Produces unified StrategySurvivalMatrix.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ..simulation_aggregator import SimulationAggregator

from .strategy_survival_types import (
    StrategySurvivalState,
    StrategySurvivalMatrix,
    StrategySurvivalStateEnum,
    StrategyAction,
    DEFAULT_STRATEGIES,
)
from .strategy_scenario_runner import StrategyScenarioRunner
from .strategy_survival_engine import StrategySurvivalEngine


class StrategySurvivalAggregator:
    """
    Main aggregator for strategy survival analysis.
    
    Runs all scenarios for each strategy and builds survival matrix.
    """
    
    def __init__(self, simulation_aggregator: Optional[SimulationAggregator] = None):
        self.runner = StrategyScenarioRunner(simulation_aggregator)
        self.engine = StrategySurvivalEngine()
    
    def analyze_strategy(
        self,
        strategy_name: str,
        net_exposure: float = 0.5,
        gross_exposure: float = 0.8,
        deployable_capital: float = 1.0,
        current_var: float = 0.10,
        current_tail_risk: float = 0.15,
        current_volatility: float = 0.20,
        current_correlation: float = 0.40,
        portfolio_beta: float = 1.0,
        crisis_state: str = "NORMAL",
    ) -> StrategySurvivalState:
        """
        Analyze single strategy survival across all scenarios.
        
        Args:
            strategy_name: Name of strategy to analyze
            Portfolio and risk parameters
            
        Returns:
            StrategySurvivalState for the strategy
        """
        # Run all scenarios for this strategy
        results = self.runner.run_scenarios_for_strategy(
            strategy_name=strategy_name,
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
        
        # Classify results
        classified = self.runner.classify_scenario_results(results)
        counts = self.runner.get_counts(classified)
        
        # Get breakdown by scenario type
        by_type = self.runner.get_by_scenario_type(results)
        
        # Find worst scenario
        worst_scenario, worst_drawdown = self.runner.find_worst_scenario(results)
        
        # Calculate average drawdown
        avg_drawdown = self.runner.calculate_average_drawdown(results)
        
        # Calculate robustness score
        robustness_score = self.engine.calculate_robustness_score(
            stable_count=counts["stable"],
            stressed_count=counts["stressed"],
            fragile_count=counts["fragile"],
            broken_count=counts["broken"],
        )
        
        # Get survival state
        survival_state = self.engine.get_survival_state(robustness_score)
        
        # Get recommended action
        recommended_action = self.engine.get_recommended_action(survival_state)
        
        # Get modifiers
        modifiers = self.engine.get_modifiers(survival_state)
        
        # Build reason
        reason = self.engine.build_reason(
            strategy_name=strategy_name,
            state=survival_state,
            stable_count=counts["stable"],
            broken_count=counts["broken"],
            worst_scenario=worst_scenario,
            by_scenario_type=by_type,
        )
        
        return StrategySurvivalState(
            strategy_name=strategy_name,
            scenarios_run=len(results),
            stable_count=counts["stable"],
            stressed_count=counts["stressed"],
            fragile_count=counts["fragile"],
            broken_count=counts["broken"],
            average_drawdown=avg_drawdown,
            worst_drawdown=worst_drawdown,
            robustness_score=robustness_score,
            survival_state=survival_state,
            recommended_action=recommended_action,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            worst_scenario=worst_scenario,
            reason=reason,
            by_scenario_type=by_type,
        )
    
    def build_matrix(
        self,
        strategies: Optional[List[str]] = None,
        net_exposure: float = 0.5,
        gross_exposure: float = 0.8,
        deployable_capital: float = 1.0,
        current_var: float = 0.10,
        current_tail_risk: float = 0.15,
        current_volatility: float = 0.20,
        current_correlation: float = 0.40,
        portfolio_beta: float = 1.0,
        crisis_state: str = "NORMAL",
    ) -> StrategySurvivalMatrix:
        """
        Build complete strategy survival matrix.
        
        Args:
            strategies: List of strategies to analyze (defaults to DEFAULT_STRATEGIES)
            Portfolio and risk parameters
            
        Returns:
            StrategySurvivalMatrix with all strategies
        """
        if strategies is None:
            strategies = DEFAULT_STRATEGIES
        
        # Analyze each strategy
        strategy_states = {}
        for strategy_name in strategies:
            state = self.analyze_strategy(
                strategy_name=strategy_name,
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
            strategy_states[strategy_name] = state
        
        # Find most robust and most fragile
        sorted_by_robustness = sorted(
            strategy_states.items(),
            key=lambda x: x[1].robustness_score,
            reverse=True
        )
        
        most_robust = sorted_by_robustness[0][0] if sorted_by_robustness else "none"
        most_fragile = sorted_by_robustness[-1][0] if sorted_by_robustness else "none"
        
        # Calculate average robustness
        avg_robustness = sum(s.robustness_score for s in strategy_states.values()) / max(len(strategy_states), 1)
        
        # Count by state
        robust_count = sum(1 for s in strategy_states.values() if s.survival_state == StrategySurvivalStateEnum.ROBUST)
        stable_count = sum(1 for s in strategy_states.values() if s.survival_state == StrategySurvivalStateEnum.STABLE)
        fragile_count = sum(1 for s in strategy_states.values() if s.survival_state == StrategySurvivalStateEnum.FRAGILE)
        broken_count = sum(1 for s in strategy_states.values() if s.survival_state == StrategySurvivalStateEnum.BROKEN)
        
        return StrategySurvivalMatrix(
            strategies=strategy_states,
            most_robust=most_robust,
            most_fragile=most_fragile,
            average_system_strategy_robustness=avg_robustness,
            robust_count=robust_count,
            stable_count=stable_count,
            fragile_count=fragile_count,
            broken_count=broken_count,
        )
    
    def get_strategy_ranking(
        self,
        matrix: StrategySurvivalMatrix,
    ) -> List[Dict[str, Any]]:
        """
        Get strategies ranked by robustness.
        """
        sorted_strategies = sorted(
            matrix.strategies.items(),
            key=lambda x: x[1].robustness_score,
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                "strategy_name": name,
                "robustness_score": round(state.robustness_score, 4),
                "survival_state": state.survival_state.value,
                "recommended_action": state.recommended_action.value,
                "worst_scenario": state.worst_scenario,
            }
            for i, (name, state) in enumerate(sorted_strategies)
        ]
    
    def get_action_summary(
        self,
        matrix: StrategySurvivalMatrix,
    ) -> Dict[str, List[str]]:
        """
        Get summary of recommended actions per strategy.
        """
        actions = {
            "KEEP_ACTIVE": [],
            "REDUCE": [],
            "SHADOW": [],
            "DISABLE": [],
        }
        
        for name, state in matrix.strategies.items():
            actions[state.recommended_action.value].append(name)
        
        return actions
