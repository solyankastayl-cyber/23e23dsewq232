"""
PHASE 23.1 — Simulation Aggregator
==================================
Main entry point for simulation engine.

Combines:
- Scenario Registry
- Shock Simulator
- Portfolio Impact Engine

Provides unified interface for running crisis simulations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .simulation_types import (
    SimulationScenario,
    SimulationResult,
    ScenarioType,
    SeverityLevel,
    SurvivalState,
    SurvivalAction,
)
from .scenario_registry import (
    SCENARIO_REGISTRY,
    get_scenario,
    list_scenarios,
    get_scenarios_by_type,
)
from .shock_simulator import ShockSimulator
from .portfolio_impact_engine import PortfolioImpactEngine


class SimulationAggregator:
    """
    Main aggregator for simulation engine.
    
    Runs crisis scenarios and produces simulation results.
    """
    
    def __init__(self):
        self.shock_simulator = ShockSimulator()
        self.impact_engine = PortfolioImpactEngine()
    
    def run_scenario(
        self,
        scenario_name: str,
        # Portfolio state
        net_exposure: float = 0.5,
        gross_exposure: float = 0.8,
        deployable_capital: float = 1.0,
        capital_efficiency: float = 0.7,
        
        # Current risk metrics
        current_var: float = 0.10,
        current_tail_risk: float = 0.15,
        current_volatility: float = 0.20,
        current_correlation: float = 0.40,
        current_liquidity: float = 1.0,
        
        # Portfolio characteristics
        portfolio_beta: float = 1.0,
        crisis_state: str = "NORMAL",
        current_regime: str = "NORMAL",
    ) -> Optional[SimulationResult]:
        """
        Run a named scenario simulation.
        
        Args:
            scenario_name: Name of scenario from registry
            net_exposure: Net portfolio exposure
            gross_exposure: Gross portfolio exposure
            deployable_capital: Available capital
            capital_efficiency: Capital utilization
            current_var: Current VaR
            current_tail_risk: Current tail risk
            current_volatility: Current volatility
            current_correlation: Current correlation
            current_liquidity: Current liquidity
            portfolio_beta: Portfolio beta
            crisis_state: Current crisis state
            current_regime: Current market regime
            
        Returns:
            SimulationResult or None if scenario not found
        """
        scenario = get_scenario(scenario_name)
        if not scenario:
            return None
        
        return self.run_custom_scenario(
            scenario=scenario,
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
            current_regime=current_regime,
        )
    
    def run_custom_scenario(
        self,
        scenario: SimulationScenario,
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
        current_regime: str = "NORMAL",
    ) -> SimulationResult:
        """
        Run a custom scenario simulation.
        """
        # Apply shock to get post-shock state
        shock_state = self.shock_simulator.apply_shock(
            scenario=scenario,
            current_volatility=current_volatility,
            current_correlation=current_correlation,
            current_liquidity=current_liquidity,
            current_regime=current_regime,
        )
        
        # Calculate portfolio impact
        impact = self.impact_engine.calculate_impact(
            scenario=scenario,
            shock_state=shock_state,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            deployable_capital=deployable_capital,
            capital_efficiency=capital_efficiency,
            current_var=current_var,
            current_tail_risk=current_tail_risk,
            portfolio_beta=portfolio_beta,
            crisis_state=crisis_state,
        )
        
        # Build result
        return SimulationResult(
            scenario_name=scenario.scenario_name,
            severity=scenario.severity,
            estimated_pnl_impact=impact["estimated_pnl_impact"],
            estimated_drawdown=impact["estimated_drawdown"],
            estimated_var_post_shock=impact["estimated_var_post_shock"],
            estimated_tail_risk_post_shock=impact["estimated_tail_risk_post_shock"],
            survival_state=impact["survival_state"],
            recommended_action=impact["recommended_action"],
            confidence_modifier=impact["confidence_modifier"],
            capital_modifier=impact["capital_modifier"],
            reason=impact["reason"],
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            deployable_capital=deployable_capital,
            current_crisis_state=crisis_state,
        )
    
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
        """Run all scenarios in registry."""
        results = []
        
        for scenario_name in SCENARIO_REGISTRY.keys():
            result = self.run_scenario(
                scenario_name=scenario_name,
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
            if result:
                results.append(result)
        
        return results
    
    def run_scenarios_by_type(
        self,
        scenario_type: ScenarioType,
        **kwargs,
    ) -> List[SimulationResult]:
        """Run all scenarios of a specific type."""
        scenarios = get_scenarios_by_type(scenario_type)
        results = []
        
        for scenario in scenarios:
            result = self.run_custom_scenario(scenario=scenario, **kwargs)
            results.append(result)
        
        return results
    
    def get_worst_case(
        self,
        results: List[SimulationResult],
    ) -> Optional[SimulationResult]:
        """Get worst case result from multiple simulations."""
        if not results:
            return None
        
        return max(results, key=lambda r: r.estimated_drawdown)
    
    def get_summary(
        self,
        results: List[SimulationResult],
    ) -> Dict[str, Any]:
        """Get summary of multiple simulation results."""
        if not results:
            return {"count": 0, "scenarios": []}
        
        # Group by survival state
        state_counts = {}
        for result in results:
            state = result.survival_state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Find worst case
        worst = self.get_worst_case(results)
        
        # Average metrics
        avg_drawdown = sum(r.estimated_drawdown for r in results) / len(results)
        avg_var = sum(r.estimated_var_post_shock for r in results) / len(results)
        
        return {
            "count": len(results),
            "state_distribution": state_counts,
            "worst_case": {
                "scenario": worst.scenario_name,
                "drawdown": round(worst.estimated_drawdown, 4),
                "survival_state": worst.survival_state.value,
                "recommended_action": worst.recommended_action.value,
            } if worst else None,
            "averages": {
                "avg_drawdown": round(avg_drawdown, 4),
                "avg_var_post_shock": round(avg_var, 4),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
