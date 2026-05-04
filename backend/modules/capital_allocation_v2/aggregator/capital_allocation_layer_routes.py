"""
PHASE 21.3 — Capital Allocation Layer Routes
============================================
API endpoints for Capital Allocation Aggregator.

Endpoints:
- GET  /api/v1/capital-allocation/layer
- GET  /api/v1/capital-allocation/layer/summary
- GET  /api/v1/capital-allocation/layer/state
- GET  /api/v1/capital-allocation/layer/registry
- POST /api/v1/capital-allocation/layer/recompute
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional

from modules.capital_allocation_v2.aggregator.capital_allocation_aggregator import (
    get_capital_allocation_aggregator,
)
from modules.capital_allocation_v2.aggregator.capital_allocation_registry import (
    get_capital_allocation_registry,
)

router = APIRouter(
    prefix="/api/v1/capital-allocation/layer",
    tags=["PHASE 21.3 - Capital Allocation Layer"],
)


@router.get("")
async def get_layer_state(
    total_capital: float = Query(1.0, description="Total capital"),
    market_regime: Optional[str] = Query(None, description="Market regime"),
    btc_dominance: Optional[float] = Query(None, description="BTC dominance (0-1)"),
    regime_confidence: float = Query(0.7, description="Regime confidence"),
    portfolio_state: str = Query("NORMAL", description="Portfolio state"),
    risk_state: str = Query("NORMAL", description="Risk state"),
    loop_state: str = Query("HEALTHY", description="Research loop state"),
    volatility_state: str = Query("NORMAL", description="Volatility state"),
):
    """
    Get full Capital Allocation Layer state.
    
    Returns unified state combining allocator and budget constraints.
    """
    try:
        aggregator = get_capital_allocation_aggregator()
        state = aggregator.compute_layer_state(
            total_capital=total_capital,
            market_regime=market_regime,
            btc_dominance=btc_dominance,
            regime_confidence=regime_confidence,
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            loop_state=loop_state,
            volatility_state=volatility_state,
        )
        
        return {
            "status": "ok",
            "phase": "21.3",
            "data": state.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_layer_summary():
    """
    Get Capital Allocation Layer summary.
    
    Returns compact summary of layer state.
    """
    try:
        aggregator = get_capital_allocation_aggregator()
        summary = aggregator.get_summary()
        
        return {
            "status": "ok",
            "phase": "21.3",
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_allocation_state_info():
    """
    Get allocation state information.
    
    Returns detailed state with reason.
    """
    try:
        aggregator = get_capital_allocation_aggregator()
        state_info = aggregator.get_state_info()
        
        return {
            "status": "ok",
            "phase": "21.3",
            "data": state_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_layer_registry():
    """
    Get layer registry statistics.
    
    Returns history and state distribution.
    """
    try:
        registry = get_capital_allocation_registry()
        stats = registry.get_stats()
        
        return {
            "status": "ok",
            "phase": "21.3",
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_layer_history(limit: int = Query(20, description="History limit")):
    """
    Get layer state history.
    """
    try:
        registry = get_capital_allocation_registry()
        history = registry.get_history(limit=limit)
        
        return {
            "status": "ok",
            "phase": "21.3",
            "history": [h.to_dict() for h in history],
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute")
async def recompute_layer():
    """
    Recompute layer state and record to registry.
    
    Returns new state after recomputation.
    """
    try:
        aggregator = get_capital_allocation_aggregator()
        state = aggregator.recompute()
        
        return {
            "status": "ok",
            "phase": "21.3",
            "message": "Layer state recomputed and recorded",
            "data": state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/efficiency")
async def get_capital_efficiency(
    market_regime: Optional[str] = Query(None, description="Market regime"),
    regime_confidence: float = Query(0.7, description="Regime confidence"),
):
    """
    Get capital efficiency analysis.
    """
    try:
        aggregator = get_capital_allocation_aggregator()
        state = aggregator.compute_layer_state(
            market_regime=market_regime,
            regime_confidence=regime_confidence,
        )
        
        return {
            "status": "ok",
            "phase": "21.3",
            "data": {
                "capital_efficiency": round(state.capital_efficiency, 4),
                "deployable_capital": round(state.deployable_capital, 4),
                "allocation_confidence": round(state.allocation_confidence, 4),
                "concentration_score": round(state.concentration_score, 4),
                "allocation_state": state.allocation_state.value,
                "efficiency_formula": "deployable × confidence × (1 - concentration)",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modifiers")
async def get_layer_modifiers():
    """
    Get combined layer modifiers.
    """
    try:
        aggregator = get_capital_allocation_aggregator()
        state = aggregator.compute_layer_state()
        
        return {
            "status": "ok",
            "phase": "21.3",
            "data": {
                "confidence_modifier": round(state.confidence_modifier, 4),
                "capital_modifier": round(state.capital_modifier, 4),
                "allocation_state": state.allocation_state.value,
                "budget_state": state.budget_state,
                "bounds": {
                    "confidence": "[0.75, 1.20]",
                    "capital": "[0.70, 1.15]",
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
