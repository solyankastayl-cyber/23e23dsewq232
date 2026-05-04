"""
PHASE 22.3 — Cluster Contagion Routes
=====================================
API endpoints for Cluster Contagion Engine.

Endpoints:
- GET  /api/v1/institutional-risk/cluster-contagion
- GET  /api/v1/institutional-risk/cluster-contagion/summary
- GET  /api/v1/institutional-risk/cluster-contagion/paths
- GET  /api/v1/institutional-risk/cluster-contagion/stress
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

from modules.institutional_risk.cluster_contagion.cluster_contagion_aggregator import (
    get_cluster_contagion_aggregator,
)

router = APIRouter(
    prefix="/api/v1/institutional-risk/cluster-contagion",
    tags=["PHASE 22.3 - Cluster Contagion Engine"],
)


@router.get("")
async def get_contagion_state(
    btc_exposure: float = Query(0.30, description="BTC cluster exposure"),
    majors_exposure: float = Query(0.25, description="Majors cluster exposure"),
    alts_exposure: float = Query(0.20, description="Alts cluster exposure"),
    trend_exposure: float = Query(0.15, description="Trend cluster exposure"),
    reversal_exposure: float = Query(0.10, description="Reversal cluster exposure"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    market_risk_state: str = Query("NORMAL", description="Market risk state"),
    concentration_score: float = Query(0.3, description="Concentration score"),
):
    """Get full cluster contagion state."""
    try:
        aggregator = get_cluster_contagion_aggregator()
        cluster_exposures = {
            "btc_cluster": btc_exposure,
            "majors_cluster": majors_exposure,
            "alts_cluster": alts_exposure,
            "trend_cluster": trend_exposure,
            "reversal_cluster": reversal_exposure,
        }
        state = aggregator.compute_contagion_state(
            cluster_exposures=cluster_exposures,
            volatility_state=volatility_state,
            market_risk_state=market_risk_state,
            concentration_score=concentration_score,
        )
        return {
            "status": "ok",
            "phase": "22.3",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_contagion_summary():
    """Get cluster contagion summary."""
    try:
        aggregator = get_cluster_contagion_aggregator()
        summary = aggregator.get_summary()
        return {
            "status": "ok",
            "phase": "22.3",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paths")
async def get_contagion_paths(
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    market_risk_state: str = Query("NORMAL", description="Market risk state"),
):
    """Get contagion paths and probabilities."""
    try:
        aggregator = get_cluster_contagion_aggregator()
        state = aggregator.compute_contagion_state(
            volatility_state=volatility_state,
            market_risk_state=market_risk_state,
        )
        return {
            "status": "ok",
            "phase": "22.3",
            "data": {
                "contagion_paths": state.contagion_paths,
                "contagion_probabilities": {
                    k: round(v, 4) for k, v in state.contagion_probabilities.items()
                },
                "systemic_risk_score": round(state.systemic_risk_score, 4),
                "contagion_state": state.contagion_state.value,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stress")
async def get_cluster_stress(
    volatility_state: str = Query("NORMAL", description="Volatility state"),
    market_risk_state: str = Query("NORMAL", description="Market risk state"),
):
    """Get per-cluster stress scores."""
    try:
        aggregator = get_cluster_contagion_aggregator()
        state = aggregator.compute_contagion_state(
            volatility_state=volatility_state,
            market_risk_state=market_risk_state,
        )
        return {
            "status": "ok",
            "phase": "22.3",
            "data": {
                "cluster_stress": {k: round(v, 4) for k, v in state.cluster_stress.items()},
                "dominant_cluster": state.dominant_cluster,
                "weakest_cluster": state.weakest_cluster,
                "contagion_state": state.contagion_state.value,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_contagion_history(limit: int = Query(20, description="History limit")):
    """Get contagion state history."""
    try:
        aggregator = get_cluster_contagion_aggregator()
        history = aggregator.get_history(limit=limit)
        return {
            "status": "ok",
            "phase": "22.3",
            "history": [h.to_dict() for h in history],
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_contagion():
    """Recompute contagion state and record to history."""
    try:
        aggregator = get_cluster_contagion_aggregator()
        state = aggregator.recompute()
        return {
            "status": "ok",
            "phase": "22.3",
            "message": "Cluster contagion state recomputed and recorded",
            "data": state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
