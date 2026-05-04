"""
PHASE 23.4 — Resilience Routes
==============================
API endpoints for Portfolio Resilience Aggregator.

Endpoints:
- GET  /api/v1/simulation/resilience
- GET  /api/v1/simulation/resilience/summary
- GET  /api/v1/simulation/resilience/state
- GET  /api/v1/simulation/resilience/drivers
- POST /api/v1/simulation/resilience/recompute
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone

from .portfolio_resilience_engine import PortfolioResilienceEngine
from .resilience_registry import get_resilience_registry


router = APIRouter(
    prefix="/api/v1/simulation/resilience",
    tags=["simulation-engine", "resilience"]
)

# Singleton engine
_engine = PortfolioResilienceEngine()


def get_engine() -> PortfolioResilienceEngine:
    """Get portfolio resilience engine instance."""
    return _engine


@router.get("")
async def get_portfolio_resilience(
    # Portfolio parameters
    net_exposure: float = Query(0.5, description="Net portfolio exposure"),
    gross_exposure: float = Query(0.8, description="Gross portfolio exposure"),
    deployable_capital: float = Query(1.0, description="Deployable capital"),
    
    # Risk metrics
    current_var: float = Query(0.10, description="Current VaR"),
    current_tail_risk: float = Query(0.15, description="Current tail risk"),
    current_volatility: float = Query(0.20, description="Current volatility"),
    current_correlation: float = Query(0.40, description="Current correlation"),
    
    # Portfolio characteristics
    portfolio_beta: float = Query(1.0, description="Portfolio beta"),
    crisis_state: str = Query("NORMAL", description="Current crisis state"),
):
    """
    Get full portfolio resilience state.
    
    Combines Stress Grid and Strategy Survival into unified resilience assessment.
    """
    engine = get_engine()
    registry = get_resilience_registry()
    
    state = engine.calculate(
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
    
    # Update registry
    registry.update(state)
    
    return state.to_full_dict()


@router.get("/summary")
async def get_resilience_summary(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get compact resilience summary.
    """
    engine = get_engine()
    
    state = engine.calculate(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    return state.to_summary()


@router.get("/state")
async def get_current_resilience_state(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    portfolio_beta: float = Query(1.0),
):
    """
    Get current resilience state classification.
    """
    engine = get_engine()
    
    state = engine.calculate(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        portfolio_beta=portfolio_beta,
    )
    
    return {
        "resilience_state": state.resilience_state.value,
        "resilience_score": round(state.resilience_score, 4),
        "recommended_action": state.recommended_action.value,
        "modifiers": {
            "confidence_modifier": round(state.confidence_modifier, 4),
            "capital_modifier": round(state.capital_modifier, 4),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/drivers")
async def get_resilience_drivers(
    net_exposure: float = Query(0.5),
    gross_exposure: float = Query(0.8),
    current_var: float = Query(0.10),
    current_volatility: float = Query(0.20),
    portfolio_beta: float = Query(1.0),
):
    """
    Get detailed breakdown of resilience drivers.
    """
    engine = get_engine()
    
    state = engine.calculate(
        net_exposure=net_exposure,
        gross_exposure=gross_exposure,
        current_var=current_var,
        current_volatility=current_volatility,
        portfolio_beta=portfolio_beta,
    )
    
    drivers = engine.get_drivers(state)
    drivers["recommended_action"] = state.recommended_action.value
    drivers["reason"] = state.reason
    
    return drivers


@router.post("/recompute")
async def recompute_resilience(
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
    Force recompute portfolio resilience.
    """
    engine = get_engine()
    registry = get_resilience_registry()
    
    state = engine.calculate(
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
    
    # Update registry
    registry.update(state)
    
    return {
        "status": "recomputed",
        "resilience_state": state.resilience_state.value,
        "resilience_score": round(state.resilience_score, 4),
        "recommended_action": state.recommended_action.value,
        "components": {
            "stress_grid": {
                "state": state.stress_grid_state,
                "score": round(state.stress_grid_score, 4),
            },
            "strategy_survival": {
                "state": state.strategy_survival_state,
                "score": round(state.strategy_survival_score, 4),
            },
        },
        "strongest_component": state.strongest_component,
        "weakest_component": state.weakest_component,
        "registry_stats": registry.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
