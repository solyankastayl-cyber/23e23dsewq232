"""
Strategy Visibility Routes
===========================
Sprint A3: Operator visibility endpoints
"""

from fastapi import APIRouter, Query

from .service_locator import get_strategy_visibility_service

router = APIRouter(prefix="/api/strategy", tags=["strategy-visibility"])


@router.get("/signals/live")
async def get_live_signals(limit: int = Query(default=50, ge=1, le=200)):
    """
    Get current live signals snapshot.
    
    Returns one signal per symbol with latest TA evaluation.
    """
    service = get_strategy_visibility_service()
    return await service.get_live_signals(limit=limit)


@router.get("/decisions/recent")
async def get_recent_decisions(limit: int = Query(default=100, ge=1, le=300)):
    """
    Get recent runtime decisions (append-only log).
    
    Shows approved, rejected, pending decisions with reasons.
    """
    service = get_strategy_visibility_service()
    return await service.get_recent_decisions(limit=limit)


@router.get("/summary")
async def get_strategy_summary(window_minutes: int = Query(default=60, ge=5, le=1440)):
    """
    Get strategy summary stats for time window.
    
    Returns counts: live_signals, approved, rejected, pending, executed.
    """
    service = get_strategy_visibility_service()
    return await service.get_summary(window_minutes=window_minutes)
