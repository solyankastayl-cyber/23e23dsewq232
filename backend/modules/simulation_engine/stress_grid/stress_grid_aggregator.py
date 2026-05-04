"""
PHASE 23.2 — Stress Grid Aggregator
===================================
Main entry point for stress grid analysis.

Combines:
- Stress Grid Runner
- Stress Grid Engine

Produces unified StressGridState.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ..simulation_aggregator import SimulationAggregator
from ..simulation_types import SimulationResult

from .stress_grid_types import (
    StressGridState,
    ResilienceState,
    ResilienceAction,
    ScenarioResultSummary,
)
from .stress_grid_runner import StressGridRunner
from .stress_grid_engine import StressGridEngine


class StressGridAggregator:
    """
    Main aggregator for stress grid analysis.
    
    Runs all scenarios and produces unified resilience assessment.
    """
    
    def __init__(self, simulation_aggregator: Optional[SimulationAggregator] = None):
        self.runner = StressGridRunner(simulation_aggregator)
        self.engine = StressGridEngine()
    
    def run_grid(
        self,
        net_exposure: float = 0.5,
        gross_exposure: float = 0.8,
        deployable_capital: float = 1.0,
        capital_efficiency: float = 0.7,
        current_var: float = 0.10,
        current_tail_risk: float = 0.15,
        current_volatility: float = 0.20,
        current_correlation: float = 0.40,
        current_liquidity: float = 1.0,
        portfolio_beta: float = 1.0,
        crisis_state: str = "NORMAL",
    ) -> StressGridState:
        """
        Run complete stress grid analysis.
        
        Args:
            Portfolio and risk parameters
            
        Returns:
            StressGridState with full analysis
        """
        # Run all scenarios
        results = self.runner.run_all_scenarios(
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            deployable_capital=deployable_capital,
            capital_efficiency=capital_efficiency,
            current_var=current_var,
            current_tail_risk=current_tail_risk,
            current_volatility=current_volatility,
            current_correlation=current_correlation,
            current_liquidity=current_liquidity,
            portfolio_beta=portfolio_beta,
            crisis_state=crisis_state,
        )
        
        # Classify results
        counts = self.runner.classify_results(results)
        
        # Extract summaries
        summaries = self.runner.extract_summaries(results)
        
        # Get by-type breakdown
        by_type = self.runner.get_by_type_breakdown(results)
        
        # Find worst scenario
        worst = self.runner.find_worst_scenario(results)
        worst_scenario = worst.scenario_name if worst else "none"
        worst_drawdown = worst.estimated_drawdown if worst else 0.0
        
        # Calculate average drawdown
        avg_drawdown = self.runner.calculate_average_drawdown(results)
        
        # Calculate fragility index
        fragility_index = self.engine.calculate_fragility_index(
            stable_count=counts["stable"],
            stressed_count=counts["stressed"],
            fragile_count=counts["fragile"],
            broken_count=counts["broken"],
        )
        
        # Get resilience state
        resilience_state = self.engine.get_resilience_state(fragility_index)
        
        # Get recommended action
        recommended_action = self.engine.get_recommended_action(resilience_state)
        
        # Get modifiers
        modifiers = self.engine.get_modifiers(resilience_state)
        
        # Build reason
        reason = self.engine.build_reason(
            state=resilience_state,
            fragility_index=fragility_index,
            stable_count=counts["stable"],
            stressed_count=counts["stressed"],
            fragile_count=counts["fragile"],
            broken_count=counts["broken"],
            worst_scenario=worst_scenario,
            by_type_breakdown=by_type,
        )
        
        return StressGridState(
            scenarios_run=len(results),
            stable_count=counts["stable"],
            stressed_count=counts["stressed"],
            fragile_count=counts["fragile"],
            broken_count=counts["broken"],
            worst_scenario=worst_scenario,
            worst_drawdown=worst_drawdown,
            average_drawdown=avg_drawdown,
            fragility_index=fragility_index,
            system_resilience_state=resilience_state,
            recommended_action=recommended_action,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            reason=reason,
            scenario_results=summaries,
            by_type_breakdown=by_type,
        )
    
    def get_worst_scenarios(
        self,
        grid_state: StressGridState,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get top N worst scenarios by drawdown.
        """
        sorted_scenarios = sorted(
            grid_state.scenario_results,
            key=lambda s: s.estimated_drawdown,
            reverse=True
        )
        
        return [s.to_dict() for s in sorted_scenarios[:top_n]]
    
    def get_vulnerability_analysis(
        self,
        grid_state: StressGridState,
    ) -> Dict[str, Any]:
        """
        Get detailed vulnerability analysis by scenario type.
        """
        vulnerabilities = self.engine.analyze_type_vulnerabilities(
            grid_state.by_type_breakdown
        )
        
        # Rank by fragility
        ranked = sorted(
            vulnerabilities.items(),
            key=lambda x: x[1]["fragility"],
            reverse=True
        )
        
        return {
            "vulnerabilities": dict(ranked),
            "most_vulnerable": ranked[0][0] if ranked else None,
            "least_vulnerable": ranked[-1][0] if ranked else None,
            "fragility_index": grid_state.fragility_index,
        }
    
    def compare_exposures(
        self,
        exposures: List[Dict[str, float]],
        base_params: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compare stress grid results across different exposure levels.
        
        Args:
            exposures: List of exposure configs (net_exposure, gross_exposure, portfolio_beta)
            base_params: Base parameters for other settings
            
        Returns:
            Comparison results for each exposure level
        """
        base = base_params or {}
        results = []
        
        for exposure in exposures:
            params = {**base, **exposure}
            grid = self.run_grid(**params)
            
            results.append({
                "exposure_config": exposure,
                "fragility_index": grid.fragility_index,
                "system_resilience_state": grid.system_resilience_state.value,
                "worst_drawdown": grid.worst_drawdown,
                "broken_count": grid.broken_count,
            })
        
        return results
