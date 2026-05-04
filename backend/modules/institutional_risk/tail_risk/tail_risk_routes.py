"""
PHASE 22.2 — Tail Risk Routes
=============================
API endpoints for Tail Risk Engine.

Endpoints:
- GET  /api/v1/institutional-risk/tail
- GET  /api/v1/institutional-risk/tail/summary
- GET  /api/v1/institutional-risk/tail/state
- GET  /api/v1/institutional-risk/tail/asymmetry
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

from modules.institutional_risk.tail_risk.tail_risk_aggregator import (
    get_tail_risk_aggregator,
)

router = APIRouter(
    prefix="/api/v1/institutional-risk/tail-risk",
    tags=["PHASE 22.2 - Tail Risk Engine"],
)


@router.get("")
async def get_tail_risk_state(
    portfolio_var_95: float = Query(0.048, description="Portfolio VaR 95"),
    portfolio_var_99: float = Query(0.065, description="Portfolio VaR 99"),
    expected_shortfall_95: float = Query(0.058, description="Expected Shortfall 95"),
    expected_shortfall_99: float = Query(0.081, description="Expected Shortfall 99"),
    var_risk_state: str = Query("NORMAL", description="VaR risk state"),
    gross_exposure: float = Query(0.5, description="Gross portfolio exposure"),
    concentration_score: float = Query(0.3, description="Position concentration score"),
    deployable_capital: float = Query(0.57, description="Deployable capital"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    asset_exposure: float = Query(0.35, description="Asset exposure"),
    cluster_exposure: float = Query(0.30, description="Cluster exposure"),
    factor_exposure: float = Query(0.25, description="Factor exposure"),
):
    """
    Get full tail risk state.
    
    Returns tail losses, crash sensitivity, concentration, asymmetry, and risk state.
    """
    try:
        aggregator = get_tail_risk_aggregator()
        state = aggregator.compute_tail_risk_state(
            portfolio_var_95=portfolio_var_95,
            portfolio_var_99=portfolio_var_99,
            expected_shortfall_95=expected_shortfall_95,
            expected_shortfall_99=expected_shortfall_99,
            var_risk_state=var_risk_state,
            gross_exposure=gross_exposure,
            concentration_score=concentration_score,
            deployable_capital=deployable_capital,
            volatility_state=volatility_state,
            asset_exposure=asset_exposure,
            cluster_exposure=cluster_exposure,
            factor_exposure=factor_exposure,
        )

        return {
            "status": "ok",
            "phase": "22.2",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_tail_risk_summary():
    """
    Get tail risk summary.
    
    Returns compact summary of tail risk state.
    """
    try:
        aggregator = get_tail_risk_aggregator()
        summary = aggregator.get_summary()

        return {
            "status": "ok",
            "phase": "22.2",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_tail_risk_state_info(
    gross_exposure: float = Query(0.5, description="Gross exposure"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    concentration_score: float = Query(0.3, description="Concentration score"),
):
    """
    Get tail risk state information.
    
    Returns risk level and recommended action.
    """
    try:
        aggregator = get_tail_risk_aggregator()
        state = aggregator.compute_tail_risk_state(
            gross_exposure=gross_exposure,
            volatility_state=volatility_state,
            concentration_score=concentration_score,
        )

        state_info = {
            "tail_risk_state": state.tail_risk_state.value,
            "tail_risk_score": round(state.tail_risk_score, 4),
            "recommended_action": state.recommended_action.value,
            "confidence_modifier": round(state.confidence_modifier, 4),
            "capital_modifier": round(state.capital_modifier, 4),
        }

        return {
            "status": "ok",
            "phase": "22.2",
            "data": state_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/asymmetry")
async def get_asymmetry_info(
    portfolio_var_95: float = Query(0.048, description="Portfolio VaR 95"),
    expected_shortfall_95: float = Query(0.058, description="Expected Shortfall 95"),
    expected_shortfall_99: float = Query(0.081, description="Expected Shortfall 99"),
):
    """
    Get asymmetry analysis.
    
    Shows how much worse the tail is compared to normal VaR.
    """
    try:
        aggregator = get_tail_risk_aggregator()
        state = aggregator.compute_tail_risk_state(
            portfolio_var_95=portfolio_var_95,
            expected_shortfall_95=expected_shortfall_95,
            expected_shortfall_99=expected_shortfall_99,
        )

        asymmetry_info = {
            "asymmetry_score": round(state.asymmetry_score, 4),
            "asymmetry_normalized": round(
                aggregator.severity_engine.normalize_asymmetry(state.asymmetry_score), 4
            ),
            "tail_loss_95": round(state.tail_loss_95, 4),
            "tail_loss_99": round(state.tail_loss_99, 4),
            "crash_sensitivity": round(state.crash_sensitivity, 4),
            "tail_concentration": round(state.tail_concentration, 4),
        }

        return {
            "status": "ok",
            "phase": "22.2",
            "data": asymmetry_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_tail_risk_history(limit: int = Query(20, description="History limit")):
    """Get tail risk state history."""
    try:
        aggregator = get_tail_risk_aggregator()
        history = aggregator.get_history(limit=limit)

        return {
            "status": "ok",
            "phase": "22.2",
            "history": [h.to_dict() for h in history],
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_tail_risk():
    """Recompute tail risk and record to history."""
    try:
        aggregator = get_tail_risk_aggregator()
        state = aggregator.recompute()

        return {
            "status": "ok",
            "phase": "22.2",
            "message": "Tail risk state recomputed and recorded",
            "data": state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
