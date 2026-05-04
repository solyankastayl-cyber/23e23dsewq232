"""
Orderbook Pressure Map — Routes

PHASE 28.3 — API endpoints for orderbook pressure detection.

Endpoints:
- GET /api/v1/microstructure/pressure/{symbol}
- GET /api/v1/microstructure/pressure/summary/{symbol}
- GET /api/v1/microstructure/pressure/history/{symbol}
- POST /api/v1/microstructure/pressure/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .orderbook_pressure_engine import (
    OrderbookPressureEngine,
    get_orderbook_pressure_engine,
)
from .orderbook_pressure_registry import (
    OrderbookPressureRegistry,
    get_orderbook_pressure_registry,
)


router = APIRouter(prefix="/api/v1/microstructure/pressure", tags=["orderbook-pressure"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_pressure_map(symbol: str):
    """
    Get current orderbook pressure map for symbol.
    
    Returns bid/ask pressure, absorption zones, and sweep risk.
    """
    engine = get_orderbook_pressure_engine()
    registry = get_orderbook_pressure_registry()
    
    # Build pressure map
    pressure_map = engine.build_pressure_map_simulated(symbol.upper())
    
    # Store in history
    await registry.store_pressure_map(pressure_map)
    
    return {
        "symbol": pressure_map.symbol,
        "bid_pressure": pressure_map.bid_pressure,
        "ask_pressure": pressure_map.ask_pressure,
        "net_pressure": pressure_map.net_pressure,
        "pressure_bias": pressure_map.pressure_bias,
        "absorption_zone": pressure_map.absorption_zone,
        "sweep_risk": pressure_map.sweep_risk,
        "sweep_probability": pressure_map.sweep_probability,
        "pressure_state": pressure_map.pressure_state,
        "confidence": pressure_map.confidence,
        "reason": pressure_map.reason,
        "computed_at": pressure_map.computed_at.isoformat(),
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_pressure_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get orderbook pressure history for symbol.
    """
    registry = get_orderbook_pressure_registry()
    history = await registry.get_history(symbol.upper(), limit)
    
    return {
        "symbol": symbol.upper(),
        "history": [
            {
                "bid_pressure": r.bid_pressure,
                "ask_pressure": r.ask_pressure,
                "net_pressure": r.net_pressure,
                "pressure_bias": r.pressure_bias,
                "absorption_zone": r.absorption_zone,
                "sweep_risk": r.sweep_risk,
                "sweep_probability": r.sweep_probability,
                "pressure_state": r.pressure_state,
                "confidence": r.confidence,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in history
        ],
        "count": len(history),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_pressure_summary(symbol: str):
    """
    Get orderbook pressure summary statistics for symbol.
    """
    registry = get_orderbook_pressure_registry()
    summary = await registry.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_records": summary.total_records,
        "bias": {
            "bid_dominant": summary.bid_dominant_count,
            "ask_dominant": summary.ask_dominant_count,
            "balanced": summary.balanced_count,
        },
        "absorption": {
            "bid": summary.bid_absorption_count,
            "ask": summary.ask_absorption_count,
            "none": summary.no_absorption_count,
        },
        "sweep_risk": {
            "up": summary.sweep_up_count,
            "down": summary.sweep_down_count,
            "none": summary.sweep_none_count,
        },
        "states": {
            "supportive": summary.supportive_count,
            "neutral": summary.neutral_count,
            "fragile": summary.fragile_count,
            "stressed": summary.stressed_count,
        },
        "averages": {
            "bid_pressure": summary.average_bid_pressure,
            "ask_pressure": summary.average_ask_pressure,
            "net_pressure": summary.average_net_pressure,
            "sweep_probability": summary.average_sweep_probability,
            "confidence": summary.average_confidence,
        },
        "current": {
            "state": summary.current_state,
            "bias": summary.current_bias,
        },
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_pressure_map(symbol: str):
    """
    Force recompute of orderbook pressure map.
    
    Stores result in history.
    """
    try:
        engine = get_orderbook_pressure_engine()
        registry = get_orderbook_pressure_registry()
        
        # Recompute
        pressure_map = engine.build_pressure_map_simulated(symbol.upper())
        
        # Store in history
        await registry.store_pressure_map(pressure_map)
        
        return {
            "status": "ok",
            "symbol": pressure_map.symbol,
            "bid_pressure": pressure_map.bid_pressure,
            "ask_pressure": pressure_map.ask_pressure,
            "net_pressure": pressure_map.net_pressure,
            "pressure_bias": pressure_map.pressure_bias,
            "absorption_zone": pressure_map.absorption_zone,
            "sweep_risk": pressure_map.sweep_risk,
            "sweep_probability": pressure_map.sweep_probability,
            "pressure_state": pressure_map.pressure_state,
            "confidence": pressure_map.confidence,
            "reason": pressure_map.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
