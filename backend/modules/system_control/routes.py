"""
System Control Routes — Operator Console API

CRITICAL ENDPOINTS:
- System state
- Mode switching (MANUAL/SEMI-AUTO/AUTO)
- System restart
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter()


class SetModeRequest(BaseModel):
    mode: str  # MANUAL | SEMI_AUTO | AUTO


# Global system state
_system_state = {
    "mode": "MANUAL",
    "running": True,
    "last_decision_ts": None,
    "last_trade_ts": None,
    "loop_active": False
}


@router.get("/api/system/state")
async def get_system_state():
    """
    Get current system state.
    
    Returns:
        System state dict
    """
    from modules.strategy_engine.kill_switch import get_kill_switch
    
    try:
        kill_switch = get_kill_switch()
        kill_switch_status = await kill_switch.get_status()
        
        return {
            "ok": True,
            "mode": _system_state["mode"],
            "running": _system_state["running"],
            "kill_switch": kill_switch_status["active"],
            "last_decision_ts": _system_state.get("last_decision_ts"),
            "last_trade_ts": _system_state.get("last_trade_ts"),
            "loop_active": _system_state.get("loop_active", False)
        }
    
    except Exception as e:
        logger.error(f"[SystemRoutes] Get state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system/mode")
async def set_system_mode(request: SetModeRequest):
    """
    Set system trading mode.
    
    Args:
        mode: MANUAL | SEMI_AUTO | AUTO
    
    Returns:
        Updated state
    """
    if request.mode not in ["MANUAL", "SEMI_AUTO", "AUTO"]:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    
    _system_state["mode"] = request.mode
    
    logger.info(f"[SystemRoutes] Mode changed to {request.mode}")
    
    return {
        "ok": True,
        "mode": request.mode,
        "message": f"Mode set to {request.mode}"
    }


@router.post("/api/system/restart")
async def restart_system():
    """
    Restart system (placeholder for now).
    
    NOTE: Actual restart would require supervisor control.
    """
    logger.warning("[SystemRoutes] Restart requested (not implemented)")
    
    return {
        "ok": True,
        "message": "Restart not implemented (requires supervisor integration)"
    }


def update_last_decision_ts():
    """Update last decision timestamp (called by strategy engine)."""
    _system_state["last_decision_ts"] = int(time.time())


def update_last_trade_ts():
    """Update last trade timestamp (called by order manager)."""
    _system_state["last_trade_ts"] = int(time.time())


def set_loop_active(active: bool):
    """Set loop active status."""
    _system_state["loop_active"] = active
