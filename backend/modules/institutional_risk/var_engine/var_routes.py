"""
PHASE 22.1 — VaR Routes
=======================
API endpoints for VaR Engine.

Endpoints:
- GET  /api/v1/institutional-risk/var
- GET  /api/v1/institutional-risk/var/summary
- GET  /api/v1/institutional-risk/var/state
- GET  /api/v1/institutional-risk/var/tail
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional

from modules.institutional_risk.var_engine.var_aggregator import (
    get_var_aggregator,
)

router = APIRouter(
    prefix="/api/v1/institutional-risk/var",
    tags=["PHASE 22.1 - VaR Engine"],
)


@router.get("")
async def get_var_state(
    gross_exposure: float = Query(0.5, description="Gross portfolio exposure"),
    net_exposure: float = Query(0.4, description="Net portfolio exposure"),
    deployable_capital: float = Query(0.57, description="Deployable capital"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    regime: str = Query("MIXED", description="Market regime"),
    position_concentration: float = Query(0.3, description="Position concentration"),
):
    """
    Get full VaR state.
    
    Returns Portfolio VaR, Expected Shortfall, and risk state.
    """
    try:
        aggregator = get_var_aggregator()
        state = aggregator.compute_var_state(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            deployable_capital=deployable_capital,
            volatility_state=volatility_state,
            regime=regime,
            position_concentration=position_concentration,
        )
        
        return {
            "status": "ok",
            "phase": "22.1",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_var_summary():
    """
    Get VaR summary.
    
    Returns compact summary of VaR state.
    """
    try:
        aggregator = get_var_aggregator()
        summary = aggregator.get_summary()
        
        return {
            "status": "ok",
            "phase": "22.1",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_risk_state(
    gross_exposure: float = Query(0.5, description="Gross exposure"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    regime: str = Query("MIXED", description="Market regime"),
):
    """
    Get risk state information.
    
    Returns risk state and recommended action.
    """
    try:
        aggregator = get_var_aggregator()
        state = aggregator.compute_var_state(
            gross_exposure=gross_exposure,
            volatility_state=volatility_state,
            regime=regime,
        )
        
        state_info = {
            "risk_state": state.risk_state.value,
            "recommended_action": state.recommended_action.value,
            "var_ratio": round(state.var_ratio, 4),
            "is_action_required": aggregator.state_engine.is_action_required(state.risk_state),
            "is_emergency": aggregator.state_engine.is_emergency(state.risk_state),
            "confidence_modifier": round(state.confidence_modifier, 4),
            "capital_modifier": round(state.capital_modifier, 4),
        }
        
        return {
            "status": "ok",
            "phase": "22.1",
            "data": state_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tail")
async def get_tail_risk(
    gross_exposure: float = Query(0.5, description="Gross exposure"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
):
    """
    Get tail risk information.
    
    Returns Expected Shortfall and tail risk metrics.
    """
    try:
        aggregator = get_var_aggregator()
        state = aggregator.compute_var_state(
            gross_exposure=gross_exposure,
            volatility_state=volatility_state,
        )
        
        tail_info = {
            "expected_shortfall_95": round(state.expected_shortfall_95, 4),
            "expected_shortfall_99": round(state.expected_shortfall_99, 4),
            "portfolio_var_95": round(state.portfolio_var_95, 4),
            "portfolio_var_99": round(state.portfolio_var_99, 4),
            "tail_risk_ratio": round(state.tail_risk_ratio, 4),
            "tail_severity": aggregator.es_engine.get_tail_severity(state.tail_risk_ratio),
            "is_elevated": aggregator.es_engine.is_tail_risk_elevated(state.tail_risk_ratio),
        }
        
        return {
            "status": "ok",
            "phase": "22.1",
            "data": tail_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_var_history(limit: int = Query(20, description="History limit")):
    """
    Get VaR state history.
    """
    try:
        aggregator = get_var_aggregator()
        history = aggregator.get_history(limit=limit)
        
        return {
            "status": "ok",
            "phase": "22.1",
            "history": [h.to_dict() for h in history],
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_var():
    """
    Recompute VaR and record to history.
    """
    try:
        aggregator = get_var_aggregator()
        state = aggregator.recompute()
        
        return {
            "status": "ok",
            "phase": "22.1",
            "message": "VaR state recomputed and recorded",
            "data": state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
