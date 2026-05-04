"""
PHASE 22.5 — Crisis Exposure Routes
===================================
API endpoints for Crisis Exposure Aggregator.

Endpoints:
- GET  /api/v1/institutional-risk/crisis
- GET  /api/v1/institutional-risk/crisis/summary
- GET  /api/v1/institutional-risk/crisis/state
- GET  /api/v1/institutional-risk/crisis/drivers
- POST /api/v1/institutional-risk/crisis/recompute
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone

from .crisis_exposure_engine import CrisisExposureEngine
from .crisis_registry import get_crisis_registry


router = APIRouter(
    prefix="/api/v1/institutional-risk/crisis",
    tags=["institutional-risk", "crisis-aggregator"]
)

# Singleton engine
_engine = CrisisExposureEngine()


def get_engine() -> CrisisExposureEngine:
    """Get crisis exposure engine instance."""
    return _engine


@router.get("")
async def get_crisis_exposure(
    # VaR inputs
    var_state: str = Query("NORMAL", description="VaR risk state"),
    var_ratio: float = Query(0.0, description="VaR ratio"),
    var_confidence: float = Query(1.0, description="VaR confidence modifier"),
    var_capital: float = Query(1.0, description="VaR capital modifier"),
    
    # Tail Risk inputs
    tail_state: str = Query("LOW", description="Tail risk state"),
    tail_score: float = Query(0.0, description="Tail risk score"),
    tail_confidence: float = Query(1.0, description="Tail confidence modifier"),
    tail_capital: float = Query(1.0, description="Tail capital modifier"),
    
    # Contagion inputs
    contagion_state: str = Query("LOW", description="Contagion state"),
    systemic_score: float = Query(0.0, description="Systemic risk score"),
    contagion_confidence: float = Query(1.0, description="Contagion confidence modifier"),
    contagion_capital: float = Query(1.0, description="Contagion capital modifier"),
    
    # Correlation inputs
    correlation_state: str = Query("NORMAL", description="Correlation state"),
    correlation_intensity: float = Query(0.0, description="Correlation spike intensity"),
    correlation_confidence: float = Query(1.0, description="Correlation confidence modifier"),
    correlation_capital: float = Query(1.0, description="Correlation capital modifier"),
):
    """
    Get full crisis exposure state.
    
    Aggregates VaR, Tail Risk, Contagion, and Correlation into unified state.
    """
    engine = get_engine()
    registry = get_crisis_registry()
    
    state = engine.calculate(
        var_state=var_state,
        var_ratio=var_ratio,
        var_confidence_modifier=var_confidence,
        var_capital_modifier=var_capital,
        
        tail_state=tail_state,
        tail_risk_score=tail_score,
        tail_confidence_modifier=tail_confidence,
        tail_capital_modifier=tail_capital,
        
        contagion_state=contagion_state,
        systemic_risk_score=systemic_score,
        contagion_confidence_modifier=contagion_confidence,
        contagion_capital_modifier=contagion_capital,
        
        correlation_state=correlation_state,
        correlation_spike_intensity=correlation_intensity,
        correlation_confidence_modifier=correlation_confidence,
        correlation_capital_modifier=correlation_capital,
    )
    
    # Update registry
    registry.update(state)
    
    return state.to_full_dict()


@router.get("/summary")
async def get_crisis_summary(
    var_state: str = Query("NORMAL"),
    tail_state: str = Query("LOW"),
    contagion_state: str = Query("LOW"),
    correlation_state: str = Query("NORMAL"),
):
    """
    Get compact crisis summary.
    """
    engine = get_engine()
    
    state = engine.calculate(
        var_state=var_state,
        tail_state=tail_state,
        contagion_state=contagion_state,
        correlation_state=correlation_state,
    )
    
    return state.to_summary()


@router.get("/state")
async def get_current_crisis_state(
    var_state: str = Query("NORMAL"),
    tail_state: str = Query("LOW"),
    contagion_state: str = Query("LOW"),
    correlation_state: str = Query("NORMAL"),
):
    """
    Get current crisis state classification.
    """
    engine = get_engine()
    
    state = engine.calculate(
        var_state=var_state,
        tail_state=tail_state,
        contagion_state=contagion_state,
        correlation_state=correlation_state,
    )
    
    return {
        "crisis_state": state.crisis_state.value,
        "crisis_score": round(state.crisis_score, 4),
        "recommended_action": state.recommended_action.value,
        "modifiers": {
            "confidence_modifier": round(state.confidence_modifier, 4),
            "capital_modifier": round(state.capital_modifier, 4),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/drivers")
async def get_crisis_drivers(
    var_state: str = Query("NORMAL"),
    tail_state: str = Query("LOW"),
    contagion_state: str = Query("LOW"),
    correlation_state: str = Query("NORMAL"),
    var_confidence: float = Query(1.0),
    var_capital: float = Query(1.0),
    tail_confidence: float = Query(1.0),
    tail_capital: float = Query(1.0),
    contagion_confidence: float = Query(1.0),
    contagion_capital: float = Query(1.0),
    correlation_confidence: float = Query(1.0),
    correlation_capital: float = Query(1.0),
):
    """
    Get detailed breakdown of crisis risk drivers.
    """
    engine = get_engine()
    
    state = engine.calculate(
        var_state=var_state,
        tail_state=tail_state,
        contagion_state=contagion_state,
        correlation_state=correlation_state,
        var_confidence_modifier=var_confidence,
        var_capital_modifier=var_capital,
        tail_confidence_modifier=tail_confidence,
        tail_capital_modifier=tail_capital,
        contagion_confidence_modifier=contagion_confidence,
        contagion_capital_modifier=contagion_capital,
        correlation_confidence_modifier=correlation_confidence,
        correlation_capital_modifier=correlation_capital,
    )
    
    drivers = engine.get_drivers(state)
    drivers["crisis_state"] = state.crisis_state.value
    drivers["recommended_action"] = state.recommended_action.value
    
    return drivers


@router.post("/recompute")
async def recompute_crisis_state(
    var_state: str = Query("NORMAL"),
    tail_state: str = Query("LOW"),
    contagion_state: str = Query("LOW"),
    correlation_state: str = Query("NORMAL"),
    var_confidence: float = Query(1.0),
    var_capital: float = Query(1.0),
    tail_confidence: float = Query(1.0),
    tail_capital: float = Query(1.0),
    contagion_confidence: float = Query(1.0),
    contagion_capital: float = Query(1.0),
    correlation_confidence: float = Query(1.0),
    correlation_capital: float = Query(1.0),
):
    """
    Force recompute crisis state and update registry.
    """
    engine = get_engine()
    registry = get_crisis_registry()
    
    state = engine.calculate(
        var_state=var_state,
        tail_state=tail_state,
        contagion_state=contagion_state,
        correlation_state=correlation_state,
        var_confidence_modifier=var_confidence,
        var_capital_modifier=var_capital,
        tail_confidence_modifier=tail_confidence,
        tail_capital_modifier=tail_capital,
        contagion_confidence_modifier=contagion_confidence,
        contagion_capital_modifier=contagion_capital,
        correlation_confidence_modifier=correlation_confidence,
        correlation_capital_modifier=correlation_capital,
    )
    
    # Update registry
    registry.update(state)
    
    return {
        "status": "recomputed",
        "crisis_state": state.crisis_state.value,
        "crisis_score": round(state.crisis_score, 4),
        "recommended_action": state.recommended_action.value,
        "registry_stats": registry.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
