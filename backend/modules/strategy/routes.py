"""Strategy API Routes — Week 4

Endpoints for strategy statistics and allocator state.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/api/strategy", tags=["strategy"])

# Will be initialized in server.py
_strategy_stats_service = None
_trading_runtime = None


def init_strategy_routes(strategy_stats_service, trading_runtime):
    """Initialize strategy routes with services."""
    global _strategy_stats_service, _trading_runtime
    _strategy_stats_service = strategy_stats_service
    _trading_runtime = trading_runtime


@router.get("/stats")
async def get_strategy_stats() -> Dict[str, Any]:
    """Get performance statistics for all strategies.
    
    Returns:
        {
            "ok": true,
            "strategies": {
                "trend_v1": {"win_rate": 0.6, ...},
                ...
            }
        }
    """
    if not _strategy_stats_service:
        return {"ok": False, "error": "Service not initialized", "strategies": {}}
    
    try:
        stats_map = await _strategy_stats_service.get_stats_map()
        return {"ok": True, "strategies": stats_map}
    except Exception as e:
        return {"ok": False, "error": str(e), "strategies": {}}


@router.get("/allocator-preview")
async def allocator_preview() -> Dict[str, Any]:
    """Get last allocator decisions and metadata.
    
    Returns:
        {
            "ok": true,
            "decisions": [...],
            "allocator_meta": {...}
        }
    """
    if not _trading_runtime:
        # Fallback: get from trading_core module directly
        from modules.trading_core.trading_runtime import get_last_allocation_preview
        preview = get_last_allocation_preview()
        return {
            "ok": True,
            "decisions": preview.get("decisions", []),
            "allocator_meta": preview.get("allocator_meta", {}),
        }
    
    # Get cached last allocation from runtime
    last_allocation = getattr(_trading_runtime, "last_allocation_preview", None)
    
    if not last_allocation:
        return {
            "ok": True,
            "decisions": [],
            "allocator_meta": {"reason": "No allocations yet"}
        }
    
    return {
        "ok": True,
        "decisions": last_allocation.get("decisions", []),
        "allocator_meta": last_allocation.get("allocator_meta", {}),
    }


@router.get("/allocator-v3")
async def allocator_v3_preview() -> Dict[str, Any]:
    """Get AllocatorV3 preview (same as allocator-preview for now)."""
    return await allocator_preview()


@router.get("/ranked-signals")
async def get_ranked_signals() -> Dict[str, Any]:
    """Get ranked signals with acceptance/rejection status.
    
    Returns:
        {
            "ok": true,
            "data": {
                "regime": "trend",
                "signals_total": 10,
                "signals_ranked": 10,
                "signals_accepted": 3,
                "signals_rejected": 7,
                "top_ranked": [...],
                "rejected": [...]
            }
        }
    """
    try:
        from modules.trading_core.trading_runtime import get_last_allocation_preview
        preview = get_last_allocation_preview()
        return {"ok": True, "data": preview}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": None}
