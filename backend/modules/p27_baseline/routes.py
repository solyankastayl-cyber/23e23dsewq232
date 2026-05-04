"""
P2.7 Baseline Validation Routes

Read-only monitoring endpoints.
NO trading logic modifications.
"""
from fastapi import APIRouter, HTTPException
from .monitor import get_p27_monitor

router = APIRouter(prefix="/api/p27", tags=["P2.7 Baseline"])


@router.get("/status")
async def get_baseline_status(experiment_id: str = None):
    """
    Get P2.7 baseline validation status
    
    Query params:
    - experiment_id: Filter by experiment (optional, default: all)
    
    Returns:
    - experiment_id: Which experiment this status is for
    - total_trades (current / target 50)
    - win_rate (overall + last 10)
    - long_vs_short split
    - equity curve
    - flow_integrity
    - slippage stats
    
    READ ONLY - no modifications to trading system
    """
    try:
        monitor = get_p27_monitor()
        status = await monitor.get_status(experiment_id=experiment_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitor error: {str(e)}")


@router.get("/equity-curve")
async def get_equity_curve():
    """
    Get full equity curve (all trades)
    
    Returns cumulative PnL progression.
    READ ONLY.
    """
    try:
        monitor = get_p27_monitor()
        curve = await monitor.get_equity_curve_full()
        return {
            "ok": True,
            "total_trades": len(curve),
            "equity_curve": curve
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Equity curve error: {str(e)}")


@router.get("/health")
async def p27_health():
    """P2.7 module health check"""
    return {
        "ok": True,
        "module": "P2.7 Baseline Validation",
        "mode": "READ_ONLY",
        "note": "No modifications to trading logic"
    }
