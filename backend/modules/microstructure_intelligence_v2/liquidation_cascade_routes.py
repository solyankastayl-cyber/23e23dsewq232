"""
Liquidation Cascade Probability — Routes

PHASE 28.4 — API endpoints for liquidation cascade detection.

Endpoints:
- GET /api/v1/microstructure/cascade/{symbol}
- GET /api/v1/microstructure/cascade/summary/{symbol}
- GET /api/v1/microstructure/cascade/history/{symbol}
- POST /api/v1/microstructure/cascade/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .liquidation_cascade_engine import (
    LiquidationCascadeEngine,
    get_liquidation_cascade_engine,
)
from .liquidation_cascade_registry import (
    LiquidationCascadeRegistry,
    get_liquidation_cascade_registry,
)


router = APIRouter(prefix="/api/v1/microstructure/cascade", tags=["liquidation-cascade"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_cascade_state(symbol: str):
    """
    Get current liquidation cascade state for symbol.
    
    Aggregates liquidation pressure, vacuum probability, and sweep probability
    to assess cascade risk.
    """
    engine = get_liquidation_cascade_engine()
    registry = get_liquidation_cascade_registry()
    
    # Build cascade state
    state = engine.build_cascade_state_simulated(symbol.upper())
    
    # Store in history
    await registry.store_cascade_state(state)
    
    return {
        "symbol": state.symbol,
        "cascade_direction": state.cascade_direction,
        "cascade_probability": state.cascade_probability,
        "liquidation_pressure": state.liquidation_pressure,
        "vacuum_probability": state.vacuum_probability,
        "sweep_probability": state.sweep_probability,
        "cascade_severity": state.cascade_severity,
        "cascade_state": state.cascade_state,
        "confidence": state.confidence,
        "reason": state.reason,
        "computed_at": state.computed_at.isoformat(),
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_cascade_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get liquidation cascade history for symbol.
    """
    registry = get_liquidation_cascade_registry()
    history = await registry.get_history(symbol.upper(), limit)
    
    return {
        "symbol": symbol.upper(),
        "history": [
            {
                "cascade_direction": r.cascade_direction,
                "cascade_probability": r.cascade_probability,
                "liquidation_pressure": r.liquidation_pressure,
                "vacuum_probability": r.vacuum_probability,
                "sweep_probability": r.sweep_probability,
                "cascade_severity": r.cascade_severity,
                "cascade_state": r.cascade_state,
                "confidence": r.confidence,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in history
        ],
        "count": len(history),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_cascade_summary(symbol: str):
    """
    Get liquidation cascade summary statistics for symbol.
    """
    registry = get_liquidation_cascade_registry()
    summary = await registry.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_records": summary.total_records,
        "directions": {
            "up": summary.up_count,
            "down": summary.down_count,
            "none": summary.none_count,
        },
        "severity": {
            "low": summary.low_count,
            "medium": summary.medium_count,
            "high": summary.high_count,
            "extreme": summary.extreme_count,
        },
        "states": {
            "stable": summary.stable_count,
            "building": summary.building_count,
            "active": summary.active_count,
            "critical": summary.critical_count,
        },
        "averages": {
            "cascade_probability": summary.average_cascade_probability,
            "liquidation_pressure": summary.average_liquidation_pressure,
            "vacuum_probability": summary.average_vacuum_probability,
            "sweep_probability": summary.average_sweep_probability,
            "confidence": summary.average_confidence,
        },
        "current": {
            "state": summary.current_state,
            "direction": summary.current_direction,
            "severity": summary.current_severity,
        },
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_cascade_state(symbol: str):
    """
    Force recompute of liquidation cascade state.
    
    Stores result in history.
    """
    try:
        engine = get_liquidation_cascade_engine()
        registry = get_liquidation_cascade_registry()
        
        # Recompute
        state = engine.build_cascade_state_simulated(symbol.upper())
        
        # Store in history
        await registry.store_cascade_state(state)
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "cascade_direction": state.cascade_direction,
            "cascade_probability": state.cascade_probability,
            "liquidation_pressure": state.liquidation_pressure,
            "vacuum_probability": state.vacuum_probability,
            "sweep_probability": state.sweep_probability,
            "cascade_severity": state.cascade_severity,
            "cascade_state": state.cascade_state,
            "confidence": state.confidence,
            "reason": state.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
