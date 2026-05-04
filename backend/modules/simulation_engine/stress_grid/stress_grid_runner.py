"""
PHASE 23.2 — Stress Grid Runner
===============================
Executes all scenarios from the registry through the simulation engine.

Collects results and prepares data for aggregation.
"""

from typing import Dict, Any, Optional, List

from ..simulation_aggregator import SimulationAggregator
from ..simulation_types import SimulationResult, SurvivalState
from ..scenario_registry import SCENARIO_REGISTRY, list_scenarios

from .stress_grid_types import ScenarioResultSummary


class StressGridRunner:
    """
    Runs all scenarios through the simulation engine.
    
    Collects results for stress grid analysis.
    """
    
    def __init__(self, simulation_aggregator: Optional[SimulationAggregator] = None):
        self.aggregator = simulation_aggregator or SimulationAggregator()
    
    def run_all_scenarios(
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
    ) -> List[SimulationResult]:
        """
        Run all registered scenarios.
        
        Args:
            Portfolio and risk parameters
            
        Returns:
            List of SimulationResult for all scenarios
        """
        results = self.aggregator.run_all_scenarios(
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
        
        return results
    
    def classify_results(
        self,
        results: List[SimulationResult],
    ) -> Dict[str, int]:
        """
        Classify results by survival state.
        
        Returns:
            Dict with counts for each survival state
        """
        counts = {
            "stable": 0,
            "stressed": 0,
            "fragile": 0,
            "broken": 0,
        }
        
        for result in results:
            state = result.survival_state.value.lower()
            if state in counts:
                counts[state] += 1
        
        return counts
    
    def extract_summaries(
        self,
        results: List[SimulationResult],
    ) -> List[ScenarioResultSummary]:
        """
        Extract summary for each scenario result.
        """
        summaries = []
        
        for result in results:
            # Get scenario type from registry
            scenario = SCENARIO_REGISTRY.get(result.scenario_name)
            scenario_type = scenario.scenario_type.value if scenario else "UNKNOWN"
            
            summary = ScenarioResultSummary(
                scenario_name=result.scenario_name,
                scenario_type=scenario_type,
                severity=result.severity.value,
                estimated_drawdown=result.estimated_drawdown,
                survival_state=result.survival_state.value,
                recommended_action=result.recommended_action.value,
            )
            summaries.append(summary)
        
        return summaries
    
    def get_by_type_breakdown(
        self,
        results: List[SimulationResult],
    ) -> Dict[str, Dict[str, int]]:
        """
        Get survival state breakdown by scenario type.
        """
        breakdown = {}
        
        for result in results:
            scenario = SCENARIO_REGISTRY.get(result.scenario_name)
            if not scenario:
                continue
            
            s_type = scenario.scenario_type.value
            if s_type not in breakdown:
                breakdown[s_type] = {"stable": 0, "stressed": 0, "fragile": 0, "broken": 0}
            
            state = result.survival_state.value.lower()
            if state in breakdown[s_type]:
                breakdown[s_type][state] += 1
        
        return breakdown
    
    def find_worst_scenario(
        self,
        results: List[SimulationResult],
    ) -> Optional[SimulationResult]:
        """
        Find scenario with worst drawdown.
        """
        if not results:
            return None
        
        return max(results, key=lambda r: r.estimated_drawdown)
    
    def calculate_average_drawdown(
        self,
        results: List[SimulationResult],
    ) -> float:
        """
        Calculate average drawdown across all scenarios.
        """
        if not results:
            return 0.0
        
        return sum(r.estimated_drawdown for r in results) / len(results)
