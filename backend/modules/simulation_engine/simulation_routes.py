"""
PHASE 23.1 — Simulation Routes
==============================
API endpoints for Simulation / Crisis Engine.

Endpoints:
- GET  /api/v1/simulation/scenarios
- GET  /api/v1/simulation/run/{scenario}
- POST /api/v1/simulation/run
- GET  /api/v1/simulation/summary
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List
from datetime import datetime, timezone

from .simulation_aggregator import SimulationAggregator
from .scenario_registry import list_scenarios, get_scenario, SCENARIO_REGISTRY
from .simulation_types import ScenarioType, SeverityLevel, SimulationScenario


router = APIRouter(
    prefix="/api/v1/simulation",
    tags=["simulation-engine"]
)

# Singleton aggregator
_aggregator = SimulationAggregator()


def get_aggregator() -> SimulationAggregator:
    """Get simulation aggregator instance."""
    return _aggregator


@router.get("/scenarios")
async def get_scenarios(
    scenario_type: Optional[str] = Query(None, description="Filter by scenario type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
):
    """
    List all available simulation scenarios.
    
    Returns list of scenario names, types, severities, and descriptions.
    """
    scenarios = list_scenarios()
    
    # Apply filters
    if scenario_type:
        scenarios = [s for s in scenarios if s["type"] == scenario_type.upper()]
    
    if severity:
        scenarios = [s for s in scenarios if s["severity"] == severity.upper()]
    
    return {
        "count": len(scenarios),
        "scenarios": scenarios,
        "types": [t.value for t in ScenarioType],
        "severities": [s.value for s in SeverityLevel],
    }


@router.get("/run/{scenario_name}")
async def run_scenario(
    scenario_name: str,
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
    Run a specific scenario simulation.
    
    Returns simulation result with estimated impacts and recommendations.
    """
    aggregator = get_aggregator()
    
    result = aggregator.run_scenario(
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
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. Use GET /scenarios to list available scenarios."
        )
    
    return result.to_full_dict()


@router.post("/run")
async def run_custom_scenario(
    # Scenario parameters
    scenario_type: str = Query("FLASH_CRASH", description="Scenario type"),
    severity: str = Query("HIGH", description="Severity level"),
    price_shock: float = Query(-0.15, description="Price shock"),
    volatility_shock: float = Query(0.50, description="Volatility shock"),
    liquidity_shock: float = Query(-0.40, description="Liquidity shock"),
    correlation_shock: float = Query(0.30, description="Correlation shock"),
    regime_shift: Optional[str] = Query(None, description="Regime shift"),
    
    # Portfolio state
    net_exposure: float = Query(0.5, description="Net exposure"),
    gross_exposure: float = Query(0.8, description="Gross exposure"),
    deployable_capital: float = Query(1.0, description="Deployable capital"),
    
    # Current risk
    current_var: float = Query(0.10, description="Current VaR"),
    current_tail_risk: float = Query(0.15, description="Current tail risk"),
    current_volatility: float = Query(0.20, description="Current volatility"),
    current_correlation: float = Query(0.40, description="Current correlation"),
    
    # Portfolio characteristics
    portfolio_beta: float = Query(1.0, description="Portfolio beta"),
    crisis_state: str = Query("NORMAL", description="Crisis state"),
):
    """
    Run a custom scenario simulation.
    
    Allows defining custom shock parameters.
    """
    aggregator = get_aggregator()
    
    # Validate scenario type
    try:
        s_type = ScenarioType(scenario_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario type. Must be one of: {[t.value for t in ScenarioType]}"
        )
    
    # Validate severity
    try:
        s_severity = SeverityLevel(severity.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Must be one of: {[s.value for s in SeverityLevel]}"
        )
    
    # Create custom scenario
    custom_scenario = SimulationScenario(
        scenario_name=f"custom_{scenario_type.lower()}_{severity.lower()}",
        scenario_type=s_type,
        severity=s_severity,
        price_shock=price_shock,
        volatility_shock=volatility_shock,
        liquidity_shock=liquidity_shock,
        correlation_shock=correlation_shock,
        regime_shift=regime_shift,
        description="Custom scenario",
    )
    
    result = aggregator.run_custom_scenario(
        scenario=custom_scenario,
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
    
    return result.to_full_dict()


@router.get("/summary")
async def get_simulation_summary(
    # Portfolio state
    net_exposure: float = Query(0.5, description="Net exposure"),
    gross_exposure: float = Query(0.8, description="Gross exposure"),
    deployable_capital: float = Query(1.0, description="Deployable capital"),
    
    # Current risk
    current_var: float = Query(0.10, description="Current VaR"),
    current_tail_risk: float = Query(0.15, description="Current tail risk"),
    current_volatility: float = Query(0.20, description="Current volatility"),
    current_correlation: float = Query(0.40, description="Current correlation"),
    
    # Portfolio
    portfolio_beta: float = Query(1.0, description="Portfolio beta"),
    crisis_state: str = Query("NORMAL", description="Crisis state"),
):
    """
    Run all scenarios and return summary.
    
    Provides worst-case analysis and state distribution.
    """
    aggregator = get_aggregator()
    
    results = aggregator.run_all_scenarios(
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
    
    return aggregator.get_summary(results)


@router.get("/run-type/{scenario_type}")
async def run_scenarios_by_type(
    scenario_type: str,
    # Portfolio state
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    current_var: float = Query(0.10),
    current_volatility: float = Query(0.20),
    portfolio_beta: float = Query(1.0),
):
    """
    Run all scenarios of a specific type.
    """
    aggregator = get_aggregator()
    
    try:
        s_type = ScenarioType(scenario_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario type. Must be one of: {[t.value for t in ScenarioType]}"
        )
    
    results = aggregator.run_scenarios_by_type(
        scenario_type=s_type,
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        current_var=current_var,
        current_volatility=current_volatility,
        portfolio_beta=portfolio_beta,
    )
    
    return {
        "scenario_type": s_type.value,
        "count": len(results),
        "results": [r.to_summary() for r in results],
        "worst_case": results[-1].to_dict() if results else None,  # Highest severity
    }
