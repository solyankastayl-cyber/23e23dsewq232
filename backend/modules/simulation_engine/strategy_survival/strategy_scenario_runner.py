"""
PHASE 23.3 — Strategy Scenario Runner
=====================================
Runs all scenarios for a specific strategy with sensitivity adjustments.

Uses strategy-specific sensitivity multipliers for different scenario types.
"""

from typing import Dict, Any, Optional, List, Tuple

from ..simulation_aggregator import SimulationAggregator
from ..simulation_types import SimulationResult, SurvivalState
from ..scenario_registry import SCENARIO_REGISTRY, get_scenario

from .strategy_survival_types import STRATEGY_SENSITIVITY


class StrategyScenarioRunner:
    """
    Runs scenarios for a specific strategy.
    
    Adjusts impact based on strategy-specific sensitivity.
    """
    
    def __init__(self, simulation_aggregator: Optional[SimulationAggregator] = None):
        self.aggregator = simulation_aggregator or SimulationAggregator()
        self.sensitivity = STRATEGY_SENSITIVITY
    
    def run_scenarios_for_strategy(
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
    ) -> List[Tuple[str, SimulationResult, float]]:
        """
        Run all scenarios for a strategy with sensitivity adjustments.
        
        Args:
            strategy_name: Name of the strategy
            Portfolio and risk parameters
            
        Returns:
            List of (scenario_name, result, adjusted_drawdown) tuples
        """
        strategy_key = strategy_name.upper()
        sensitivities = self.sensitivity.get(strategy_key, self.sensitivity["DEFAULT"])
        
        results = []
        
        for scenario_name, scenario in SCENARIO_REGISTRY.items():
            # Get base scenario result
            result = self.aggregator.run_scenario(
                scenario_name=scenario_name,
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
            
            if not result:
                continue
            
            # Apply sensitivity multiplier
            scenario_type = scenario.scenario_type.value
            sensitivity_mult = sensitivities.get(scenario_type, 1.0)
            
            # Adjust drawdown based on sensitivity
            adjusted_drawdown = min(0.50, result.estimated_drawdown * sensitivity_mult)
            
            results.append((scenario_name, result, adjusted_drawdown))
        
        return results
    
    def classify_scenario_results(
        self,
        results: List[Tuple[str, SimulationResult, float]],
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Classify scenario results by survival state using adjusted drawdown.
        
        Returns:
            Dict mapping survival state to list of (scenario_name, drawdown) tuples
        """
        classified = {
            "stable": [],
            "stressed": [],
            "fragile": [],
            "broken": [],
        }
        
        for scenario_name, result, adjusted_drawdown in results:
            # Reclassify based on adjusted drawdown
            if adjusted_drawdown < 0.05:
                state = "stable"
            elif adjusted_drawdown < 0.10:
                state = "stressed"
            elif adjusted_drawdown < 0.18:
                state = "fragile"
            else:
                state = "broken"
            
            classified[state].append((scenario_name, adjusted_drawdown))
        
        return classified
    
    def get_counts(
        self,
        classified: Dict[str, List[Tuple[str, float]]],
    ) -> Dict[str, int]:
        """Get count for each survival state."""
        return {
            "stable": len(classified["stable"]),
            "stressed": len(classified["stressed"]),
            "fragile": len(classified["fragile"]),
            "broken": len(classified["broken"]),
        }
    
    def get_by_scenario_type(
        self,
        results: List[Tuple[str, SimulationResult, float]],
    ) -> Dict[str, Dict[str, int]]:
        """
        Get survival state breakdown by scenario type.
        """
        breakdown = {}
        
        for scenario_name, result, adjusted_drawdown in results:
            scenario = SCENARIO_REGISTRY.get(scenario_name)
            if not scenario:
                continue
            
            s_type = scenario.scenario_type.value
            if s_type not in breakdown:
                breakdown[s_type] = {"stable": 0, "stressed": 0, "fragile": 0, "broken": 0}
            
            # Classify by adjusted drawdown
            if adjusted_drawdown < 0.05:
                breakdown[s_type]["stable"] += 1
            elif adjusted_drawdown < 0.10:
                breakdown[s_type]["stressed"] += 1
            elif adjusted_drawdown < 0.18:
                breakdown[s_type]["fragile"] += 1
            else:
                breakdown[s_type]["broken"] += 1
        
        return breakdown
    
    def find_worst_scenario(
        self,
        results: List[Tuple[str, SimulationResult, float]],
    ) -> Tuple[str, float]:
        """
        Find scenario with worst adjusted drawdown.
        """
        if not results:
            return ("none", 0.0)
        
        worst = max(results, key=lambda x: x[2])
        return (worst[0], worst[2])
    
    def calculate_average_drawdown(
        self,
        results: List[Tuple[str, SimulationResult, float]],
    ) -> float:
        """
        Calculate average adjusted drawdown.
        """
        if not results:
            return 0.0
        
        return sum(r[2] for r in results) / len(results)
