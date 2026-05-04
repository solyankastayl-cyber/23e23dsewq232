"""
Strategy Engine Routes — Control Plane
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from .kill_switch import get_kill_switch

logger = logging.getLogger(__name__)

router = APIRouter()


class KillSwitchRequest(BaseModel):
    reason: Optional[str] = "Manual stop"


@router.post("/api/strategy/kill-switch/activate")
async def activate_kill_switch(request: KillSwitchRequest):
    """
    Activate kill switch (STOP ALL TRADING).
    
    CRITICAL: This stops all automated trading immediately.
    """
    try:
        kill_switch = get_kill_switch()
        result = await kill_switch.activate(request.reason)
        
        return result
    
    except Exception as e:
        logger.error(f"[StrategyRoutes] Kill switch activation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/strategy/kill-switch/deactivate")
async def deactivate_kill_switch():
    """
    Deactivate kill switch (RESUME TRADING).
    """
    try:
        kill_switch = get_kill_switch()
        result = await kill_switch.deactivate()
        
        return result
    
    except Exception as e:
        logger.error(f"[StrategyRoutes] Kill switch deactivation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/strategy/kill-switch/status")
async def get_kill_switch_status():
    """
    Get kill switch status.
    """
    try:
        kill_switch = get_kill_switch()
        status = await kill_switch.get_status()
        
        return {
            "ok": True,
            **status
        }
    
    except Exception as e:
        logger.error(f"[StrategyRoutes] Kill switch status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/strategy/risk/limits")
async def get_risk_limits():
    """
    Get current risk limits.
    """
    from .risk_manager import get_risk_manager
    
    try:
        risk_manager = get_risk_manager()
        
        return {
            "ok": True,
            "limits": {
                "max_positions": risk_manager.MAX_POSITIONS,
                "max_trades_per_hour": risk_manager.MAX_TRADES_PER_HOUR,
                "daily_loss_limit": risk_manager.DAILY_LOSS_LIMIT,
                "cooldown_seconds": risk_manager.COOLDOWN_SECONDS,
                "max_slippage_pct": risk_manager.MAX_SLIPPAGE_PCT,
            }
        }
    
    except Exception as e:
        logger.error(f"[StrategyRoutes] Risk limits failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/strategy/state")
async def get_strategy_state():
    """
    Get strategy state for all symbols.
    """
    try:
        from modules.core.database import get_database
        
        db = get_database()
        states = await db.strategy_state.find({}, {"_id": 0}).to_list(length=100)
        
        return {
            "ok": True,
            "states": states
        }
    
    except Exception as e:
        logger.error(f"[StrategyRoutes] Strategy state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/api/strategy/risk/health")
async def get_risk_health():
    """Get risk manager health metrics."""
    try:
        from modules.strategy_engine.risk_manager import get_risk_manager
        from modules.portfolio.service import get_portfolio_service
        import time
        
        risk_manager = get_risk_manager()
        portfolio_service = get_portfolio_service()
        
        summary = await portfolio_service.get_summary()
        
        # Convert Pydantic model to dict
        summary_dict = summary.dict() if hasattr(summary, 'dict') else summary
        
        # Determine risk state
        total_pnl = summary_dict.get("total_pnl", 0)
        deployment_pct = summary_dict.get("deployment_pct", 0)
        
        if total_pnl < risk_manager.DAILY_LOSS_LIMIT * 0.8:
            risk_state = "CRITICAL"
        elif deployment_pct > 70:
            risk_state = "WARNING"
        else:
            risk_state = "NORMAL"
        
        active_positions_count = summary_dict.get("active_positions_count", 0)
        if not active_positions_count:
            # Fallback: count from list
            active_positions = summary_dict.get("active_positions", [])
            active_positions_count = len(active_positions) if isinstance(active_positions, list) else 0
        
        return {
            "ok": True,
            "state": risk_state,
            "exposure_pct": deployment_pct,
            "active_positions": active_positions_count,
            "max_positions": risk_manager.MAX_POSITIONS,
            "daily_pnl": total_pnl,
            "loss_limit": risk_manager.DAILY_LOSS_LIMIT,
            "rejects_last_hour": 0,
            "last_reject_reason": None
        }
    except Exception as e:
        logger.error(f"[StrategyRoutes] Risk health failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/strategy/rejections")
async def get_strategy_rejections(limit: int = 50):
    """Get recent rejected signals (shows why RiskManager blocked)."""
    try:
        from modules.portfolio.service import get_portfolio_service
        
        portfolio = get_portfolio_service()
        db = portfolio.db
        
        # Get rejections from execution logger
        rejections = await db.strategy_rejections.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        # Format for frontend
        formatted = []
        for r in rejections:
            formatted.append({
                "symbol": r.get("symbol"),
                "reason": r.get("reason"),
                "confidence": r.get("confidence"),
                "strategy": r.get("strategy"),
                "timestamp": int(r["timestamp"].timestamp()) if r.get("timestamp") else None
            })
        
        return {"ok": True, "rejections": formatted}
    except Exception as e:
        logger.error(f"[StrategyRoutes] Rejections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
