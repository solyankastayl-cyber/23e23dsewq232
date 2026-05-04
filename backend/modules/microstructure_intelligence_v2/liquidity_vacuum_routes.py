"""
Liquidity Vacuum Detector — Routes

PHASE 28.2 — API endpoints for liquidity vacuum detection.

Endpoints:
- GET /api/v1/microstructure/vacuum/{symbol}
- GET /api/v1/microstructure/vacuum/history/{symbol}
- GET /api/v1/microstructure/vacuum/summary/{symbol}
- POST /api/v1/microstructure/vacuum/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .liquidity_vacuum_engine import (
    LiquidityVacuumEngine,
    get_liquidity_vacuum_engine,
)
from .liquidity_vacuum_registry import (
    LiquidityVacuumRegistry,
    get_liquidity_vacuum_registry,
)


router = APIRouter(prefix="/api/v1/microstructure/vacuum", tags=["liquidity-vacuum"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_vacuum_state(symbol: str):
    """
    Get current liquidity vacuum state for symbol.
    
    Returns vacuum direction, probability, gap analysis and state classification.
    """
    engine = get_liquidity_vacuum_engine()
    registry = get_liquidity_vacuum_registry()
    
    # Build vacuum state
    state = engine.build_vacuum_state_simulated(symbol.upper())
    
    # Store in history
    await registry.store_vacuum_state(state)
    
    return {
        "symbol": state.symbol,
        "vacuum_direction": state.vacuum_direction,
        "vacuum_probability": state.vacuum_probability,
        "vacuum_size_bps": state.vacuum_size_bps,
        "nearest_liquidity_wall_distance": state.nearest_liquidity_wall_distance,
        "orderbook_gap_score": state.orderbook_gap_score,
        "liquidity_state": state.liquidity_state,
        "confidence": state.confidence,
        "reason": state.reason,
        "computed_at": state.computed_at.isoformat(),
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_vacuum_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get liquidity vacuum history for symbol.
    """
    registry = get_liquidity_vacuum_registry()
    history = await registry.get_history(symbol.upper(), limit)
    
    return {
        "symbol": symbol.upper(),
        "history": [
            {
                "vacuum_direction": r.vacuum_direction,
                "vacuum_probability": r.vacuum_probability,
                "vacuum_size_bps": r.vacuum_size_bps,
                "nearest_liquidity_wall_distance": r.nearest_liquidity_wall_distance,
                "orderbook_gap_score": r.orderbook_gap_score,
                "liquidity_state": r.liquidity_state,
                "confidence": r.confidence,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in history
        ],
        "count": len(history),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_vacuum_summary(symbol: str):
    """
    Get liquidity vacuum summary statistics for symbol.
    """
    registry = get_liquidity_vacuum_registry()
    summary = await registry.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_records": summary.total_records,
        "directions": {
            "up": summary.up_count,
            "down": summary.down_count,
            "none": summary.none_count,
        },
        "states": {
            "normal": summary.normal_count,
            "thin_zone": summary.thin_zone_count,
            "vacuum": summary.vacuum_count,
        },
        "averages": {
            "vacuum_probability": summary.average_vacuum_probability,
            "vacuum_size_bps": summary.average_vacuum_size_bps,
            "wall_distance": summary.average_wall_distance,
            "gap_score": summary.average_gap_score,
            "confidence": summary.average_confidence,
        },
        "current": {
            "state": summary.current_state,
            "direction": summary.current_direction,
        },
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_vacuum_state(symbol: str):
    """
    Force recompute of liquidity vacuum state.
    
    Stores result in history.
    """
    try:
        engine = get_liquidity_vacuum_engine()
        registry = get_liquidity_vacuum_registry()
        
        # Recompute
        state = engine.build_vacuum_state_simulated(symbol.upper())
        
        # Store in history
        await registry.store_vacuum_state(state)
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "vacuum_direction": state.vacuum_direction,
            "vacuum_probability": state.vacuum_probability,
            "vacuum_size_bps": state.vacuum_size_bps,
            "nearest_liquidity_wall_distance": state.nearest_liquidity_wall_distance,
            "orderbook_gap_score": state.orderbook_gap_score,
            "liquidity_state": state.liquidity_state,
            "confidence": state.confidence,
            "reason": state.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
