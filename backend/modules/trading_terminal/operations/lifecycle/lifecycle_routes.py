"""
OPS2 Lifecycle Routes
=====================

API endpoints for position lifecycle.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from .lifecycle_service import lifecycle_service


router = APIRouter(prefix="/api/ops/lifecycle", tags=["ops-lifecycle"])


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for OPS2"""
    return lifecycle_service.get_health()


# ===========================================
# Summary
# ===========================================

@router.get("/summary")
async def get_summary():
    """Get lifecycle summary"""
    return lifecycle_service.get_lifecycle_summary()


# ===========================================
# Single Position
# ===========================================

@router.get("/{position_id}")
async def get_lifecycle(position_id: str):
    """
    Get complete lifecycle for a position.
    
    Includes all events, phases, and statistics.
    """
    lifecycle = lifecycle_service.get_lifecycle(position_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle not found")
    
    return lifecycle.to_dict()


@router.get("/{position_id}/timeline")
async def get_timeline(position_id: str):
    """
    Get simplified timeline for position.
    """
    timeline = lifecycle_service.get_timeline(position_id)
    
    if not timeline:
        raise HTTPException(status_code=404, detail="Lifecycle not found")
    
    return {
        "positionId": position_id,
        "timeline": timeline,
        "eventCount": len(timeline)
    }


@router.get("/{position_id}/stats")
async def get_stats(position_id: str):
    """
    Get lifecycle statistics.
    
    Includes duration, MAE/MFE, capture efficiency.
    """
    stats = lifecycle_service.get_stats(position_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Lifecycle not found")
    
    return stats.to_dict()


@router.get("/{position_id}/mae-mfe")
async def get_mae_mfe(position_id: str):
    """
    Get MAE/MFE metrics for position.
    
    - MAE: Maximum Adverse Excursion (worst loss during position)
    - MFE: Maximum Favorable Excursion (best profit during position)
    """
    result = lifecycle_service.get_mae_mfe(position_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Lifecycle not found")
    
    return {
        "positionId": position_id,
        **result
    }


@router.post("/{position_id}/rebuild")
async def rebuild_lifecycle(position_id: str):
    """
    Force rebuild lifecycle from Event Ledger.
    """
    lifecycle = lifecycle_service.rebuild_lifecycle(position_id)
    
    if not lifecycle:
        raise HTTPException(status_code=404, detail="No events found for position")
    
    return {
        "success": True,
        "lifecycle": lifecycle.to_dict()
    }


# ===========================================
# Filter Queries
# ===========================================

@router.get("/symbol/{symbol}")
async def get_by_symbol(
    symbol: str,
    limit: int = Query(20, le=100)
):
    """Get lifecycles by symbol"""
    lifecycles = lifecycle_service.get_lifecycles_by_symbol(symbol, limit)
    
    return {
        "symbol": symbol.upper(),
        "lifecycles": [lc.to_dict() for lc in lifecycles],
        "count": len(lifecycles)
    }


@router.get("/strategy/{strategy_id}")
async def get_by_strategy(
    strategy_id: str,
    limit: int = Query(20, le=100)
):
    """Get lifecycles by strategy"""
    lifecycles = lifecycle_service.get_lifecycles_by_strategy(strategy_id, limit)
    
    return {
        "strategyId": strategy_id,
        "lifecycles": [lc.to_dict() for lc in lifecycles],
        "count": len(lifecycles)
    }


@router.get("/recent")
async def get_recent(limit: int = Query(20, le=100)):
    """Get most recent lifecycles"""
    lifecycles = lifecycle_service.get_recent_lifecycles(limit)
    
    return {
        "lifecycles": [lc.to_dict() for lc in lifecycles],
        "count": len(lifecycles)
    }
