"""
PHASE 23.2 — Stress Grid Routes
===============================
API endpoints for Multi-Scenario Stress Grid.

Endpoints:
- GET  /api/v1/simulation/stress-grid
- GET  /api/v1/simulation/stress-grid/summary
- GET  /api/v1/simulation/stress-grid/worst
- GET  /api/v1/simulation/stress-grid/scenarios
- POST /api/v1/simulation/stress-grid/recompute
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone

from .stress_grid_aggregator import StressGridAggregator


router = APIRouter(
    prefix="/api/v1/simulation/stress-grid",
    tags=["simulation-engine", "stress-grid"]
)

# Singleton aggregator
_aggregator = StressGridAggregator()


def get_aggregator() -> StressGridAggregator:
    """Get stress grid aggregator instance."""
    return _aggregator


@router.get("")
async def get_stress_grid(
    # Portfolio state
    net_exposure: float = Query(0.5, description="Net portfolio exposure"),
    gross_exposure: float = Query(0.8, description="Gross portfolio exposure"),
    deployable_capital: float = Query(1.0, description="Deployable capital"),
    
    # Current risk metrics
    current_var: float = Query(0.10, description="Current VaR"),
    current_tail_risk: float = Query(0.15, description="Current tail risk"),
    current_volatility: float = Query(0.20, description="Current volatility"),
    current_correlation: float = Query(0.40, description="Current correlation"),
    
    # Portfolio characteristics
    portfolio_beta: float = Query(1.0, description="Portfolio beta"),
    crisis_state: str = Query("NORMAL", description="Current crisis state"),
):
    """
    Run complete stress grid analysis.
    
    Executes all scenarios and returns full resilience assessment.
    """
    aggregator = get_aggregator()
    
    grid_state = aggregator.run_grid(
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
    
    return grid_state.to_full_dict()


@router.get("/summary")
async def get_stress_grid_summary(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
    current_volatility: float = Query(0.20),
):
    """
    Get compact stress grid summary.
    """
    aggregator = get_aggregator()
    
    grid_state = aggregator.run_grid(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
        current_volatility=current_volatility,
    )
    
    return grid_state.to_summary()


@router.get("/worst")
async def get_worst_scenarios(
    top_n: int = Query(5, description="Number of worst scenarios to return"),
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get top N worst scenarios by drawdown.
    """
    aggregator = get_aggregator()
    
    grid_state = aggregator.run_grid(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    worst = aggregator.get_worst_scenarios(grid_state, top_n=top_n)
    
    return {
        "count": len(worst),
        "worst_scenarios": worst,
        "overall_fragility": round(grid_state.fragility_index, 4),
        "system_resilience_state": grid_state.system_resilience_state.value,
    }


@router.get("/scenarios")
async def get_all_scenario_results(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get all scenario results from stress grid.
    """
    aggregator = get_aggregator()
    
    grid_state = aggregator.run_grid(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    return {
        "scenarios_run": grid_state.scenarios_run,
        "distribution": {
            "stable": grid_state.stable_count,
            "stressed": grid_state.stressed_count,
            "fragile": grid_state.fragile_count,
            "broken": grid_state.broken_count,
        },
        "by_type": grid_state.by_type_breakdown,
        "scenario_results": [s.to_dict() for s in grid_state.scenario_results],
    }


@router.post("/recompute")
async def recompute_stress_grid(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    deployable_capital: float = Query(1.0),
    current_var: float = Query(0.10),
    current_tail_risk: float = Query(0.15),
    current_volatility: float = Query(0.20),
    current_correlation: float = Query(0.40),
    portfolio_beta: float = Query(1.0),
    crisis_state: str = Query("NORMAL"),
):
    """
    Force recompute stress grid.
    """
    aggregator = get_aggregator()
    
    grid_state = aggregator.run_grid(
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
    
    vulnerability = aggregator.get_vulnerability_analysis(grid_state)
    
    return {
        "status": "recomputed",
        "scenarios_run": grid_state.scenarios_run,
        "fragility_index": round(grid_state.fragility_index, 4),
        "system_resilience_state": grid_state.system_resilience_state.value,
        "recommended_action": grid_state.recommended_action.value,
        "vulnerability_analysis": vulnerability,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/vulnerability")
async def get_vulnerability_analysis(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get detailed vulnerability analysis by scenario type.
    """
    aggregator = get_aggregator()
    
    grid_state = aggregator.run_grid(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    return aggregator.get_vulnerability_analysis(grid_state)
