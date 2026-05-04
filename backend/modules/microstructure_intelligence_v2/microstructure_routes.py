"""
Microstructure Intelligence v2 — Routes

API endpoints for microstructure snapshots.

Endpoints:
- GET /api/v1/microstructure/current/{symbol}
- GET /api/v1/microstructure/summary/{symbol}
- GET /api/v1/microstructure/history/{symbol}
- POST /api/v1/microstructure/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .microstructure_snapshot_engine import (
    MicrostructureSnapshotEngine,
    get_microstructure_snapshot_engine,
)
from .microstructure_registry import (
    MicrostructureRegistry,
    get_microstructure_registry,
)


router = APIRouter(prefix="/api/v1/microstructure", tags=["microstructure"])


@router.get("/current/{symbol}", response_model=Dict[str, Any])
async def get_current_microstructure(symbol: str):
    """
    Get current microstructure snapshot for symbol.
    
    Returns spread, depth, imbalance, pressure metrics and state classifications.
    """
    engine = get_microstructure_snapshot_engine()
    registry = get_microstructure_registry()
    
    # Build snapshot
    snapshot = engine.build_snapshot_simulated(symbol.upper())
    
    # Store in history
    await registry.store_snapshot(snapshot)
    
    return {
        "symbol": snapshot.symbol,
        "spread_bps": snapshot.spread_bps,
        "depth_score": snapshot.depth_score,
        "imbalance_score": snapshot.imbalance_score,
        "liquidation_pressure": snapshot.liquidation_pressure,
        "funding_pressure": snapshot.funding_pressure,
        "oi_pressure": snapshot.oi_pressure,
        "liquidity_state": snapshot.liquidity_state,
        "pressure_state": snapshot.pressure_state,
        "microstructure_state": snapshot.microstructure_state,
        "confidence": snapshot.confidence,
        "reason": snapshot.reason,
        "computed_at": snapshot.computed_at.isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_microstructure_summary(symbol: str):
    """
    Get microstructure summary statistics for symbol.
    
    Returns counts by state and averages.
    """
    registry = get_microstructure_registry()
    summary = await registry.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_records": summary.total_records,
        "liquidity_states": {
            "deep": summary.deep_count,
            "normal": summary.normal_count,
            "thin": summary.thin_count,
        },
        "pressure_states": {
            "buy_pressure": summary.buy_pressure_count,
            "sell_pressure": summary.sell_pressure_count,
            "balanced": summary.balanced_count,
        },
        "microstructure_states": {
            "supportive": summary.supportive_count,
            "neutral": summary.neutral_count,
            "fragile": summary.fragile_count,
            "stressed": summary.stressed_count,
        },
        "averages": {
            "spread_bps": summary.average_spread_bps,
            "depth_score": summary.average_depth_score,
            "confidence": summary.average_confidence,
        },
        "current_state": summary.current_state,
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_microstructure_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get microstructure snapshot history for symbol.
    """
    registry = get_microstructure_registry()
    history = await registry.get_history(symbol.upper(), limit)
    
    return {
        "symbol": symbol.upper(),
        "history": [
            {
                "spread_bps": r.spread_bps,
                "depth_score": r.depth_score,
                "imbalance_score": r.imbalance_score,
                "liquidation_pressure": r.liquidation_pressure,
                "funding_pressure": r.funding_pressure,
                "oi_pressure": r.oi_pressure,
                "liquidity_state": r.liquidity_state,
                "pressure_state": r.pressure_state,
                "microstructure_state": r.microstructure_state,
                "confidence": r.confidence,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in history
        ],
        "count": len(history),
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_microstructure(symbol: str):
    """
    Force recompute of microstructure snapshot.
    
    Stores result in history.
    """
    try:
        engine = get_microstructure_snapshot_engine()
        registry = get_microstructure_registry()
        
        # Recompute
        snapshot = engine.build_snapshot_simulated(symbol.upper())
        
        # Store in history
        await registry.store_snapshot(snapshot)
        
        return {
            "status": "ok",
            "symbol": snapshot.symbol,
            "spread_bps": snapshot.spread_bps,
            "depth_score": snapshot.depth_score,
            "imbalance_score": snapshot.imbalance_score,
            "liquidation_pressure": snapshot.liquidation_pressure,
            "funding_pressure": snapshot.funding_pressure,
            "oi_pressure": snapshot.oi_pressure,
            "liquidity_state": snapshot.liquidity_state,
            "pressure_state": snapshot.pressure_state,
            "microstructure_state": snapshot.microstructure_state,
            "confidence": snapshot.confidence,
            "reason": snapshot.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
