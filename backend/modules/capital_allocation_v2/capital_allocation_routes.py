"""
PHASE 21.1 — Capital Allocation Routes
=====================================
API endpoints for Capital Allocation Engine v2.

Endpoints:
- GET  /api/v1/capital-allocation/state
- GET  /api/v1/capital-allocation/strategies
- GET  /api/v1/capital-allocation/factors
- GET  /api/v1/capital-allocation/assets
- GET  /api/v1/capital-allocation/clusters
- GET  /api/v1/capital-allocation/summary
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional

from modules.capital_allocation_v2.capital_router_engine import (
    get_capital_router_engine,
)
from modules.capital_allocation_v2.strategy_capital_engine import (
    get_strategy_capital_engine,
)
from modules.capital_allocation_v2.factor_capital_engine import (
    get_factor_capital_engine,
)
from modules.capital_allocation_v2.asset_capital_engine import (
    get_asset_capital_engine,
)
from modules.capital_allocation_v2.cluster_capital_engine import (
    get_cluster_capital_engine,
)

router = APIRouter(
    prefix="/api/v1/capital-allocation",
    tags=["PHASE 21.1 - Capital Allocation v2"],
)


@router.get("/state")
async def get_allocation_state(
    total_capital: float = Query(1.0, description="Total capital to allocate"),
    market_regime: Optional[str] = Query(None, description="Market regime override"),
    btc_dominance: Optional[float] = Query(None, description="BTC dominance (0-1)"),
    regime_confidence: float = Query(0.7, description="Regime confidence (0-1)"),
):
    """
    Get full capital allocation state.
    
    Returns system-wide capital distribution across all dimensions.
    """
    try:
        engine = get_capital_router_engine()
        state = engine.compute_allocation(
            total_capital=total_capital,
            market_regime=market_regime,
            btc_dominance=btc_dominance,
            regime_confidence=regime_confidence,
        )
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_allocation_summary():
    """
    Get capital allocation summary.
    
    Returns compact summary of allocation state.
    """
    try:
        engine = get_capital_router_engine()
        summary = engine.get_summary()
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategy_allocations(
    regime_confidence: float = Query(0.7, description="Regime confidence"),
    portfolio_modifier: float = Query(1.0, description="Portfolio modifier"),
):
    """
    Get strategy-level capital allocations.
    """
    try:
        engine = get_strategy_capital_engine()
        result = engine.compute_allocations(
            regime_confidence=regime_confidence,
            portfolio_modifier=portfolio_modifier,
        )
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": {
                "allocations": {k: round(v, 4) for k, v in result["allocations"].items()},
                "slices": [s.to_dict() for s in result["slices"]],
                "concentration": round(result["concentration"], 4),
                "dominant_strategy": engine.get_dominant_strategy(result["allocations"]),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors")
async def get_factor_allocations(
    research_modifier: float = Query(1.0, description="Research loop modifier"),
):
    """
    Get factor-level capital allocations.
    """
    try:
        engine = get_factor_capital_engine()
        result = engine.compute_allocations(research_modifier=research_modifier)
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": {
                "allocations": {k: round(v, 4) for k, v in result["allocations"].items()},
                "slices": [s.to_dict() for s in result["slices"]],
                "concentration": round(result["concentration"], 4),
                "factor_health": round(engine.get_factor_health(result["allocations"]), 4),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets")
async def get_asset_allocations(
    btc_dominance: float = Query(0.55, description="BTC dominance (0-1)"),
    market_breadth: float = Query(0.5, description="Market breadth (0-1)"),
    risk_off: bool = Query(False, description="Risk-off mode"),
):
    """
    Get asset-level capital allocations.
    """
    try:
        engine = get_asset_capital_engine()
        result = engine.compute_allocations(
            btc_dominance=btc_dominance,
            market_breadth=market_breadth,
            risk_off_mode=risk_off,
        )
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": {
                "allocations": {k: round(v, 4) for k, v in result["allocations"].items()},
                "concentration": round(result["concentration"], 4),
                "dominant_asset": engine.get_dominant_asset(result["allocations"]),
                "btc_dominance_input": btc_dominance,
                "market_breadth_input": market_breadth,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters")
async def get_cluster_allocations(
    regime: str = Query("MIXED", description="Market regime"),
):
    """
    Get cluster-level capital allocations.
    """
    try:
        router_engine = get_capital_router_engine()
        strategy_alloc = router_engine.get_strategy_allocations()
        asset_alloc = router_engine.get_asset_allocations()
        
        cluster_engine = get_cluster_capital_engine()
        result = cluster_engine.compute_allocations(
            strategy_allocations=strategy_alloc,
            asset_allocations=asset_alloc,
            regime=regime,
        )
        
        overloaded = cluster_engine.detect_cluster_overload(result["allocations"])
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": {
                "allocations": {k: round(v, 4) for k, v in result["allocations"].items()},
                "concentration": round(result["concentration"], 4),
                "dominant_cluster": cluster_engine.get_dominant_cluster(result["allocations"]),
                "overloaded_clusters": overloaded,
                "regime": regime,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing")
async def get_routing_info():
    """
    Get current routing information.
    """
    try:
        engine = get_capital_router_engine()
        state = engine.compute_allocation()
        
        return {
            "status": "ok",
            "phase": "21.1",
            "data": {
                "dominant_route": state.dominant_route.value,
                "routing_regime": state.routing_regime.value,
                "allocation_confidence": round(state.allocation_confidence, 4),
                "concentration_score": round(state.concentration_score, 4),
                "confidence_modifier": round(state.confidence_modifier, 4),
                "capital_modifier": round(state.capital_modifier, 4),
                "reason": state.reason,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
