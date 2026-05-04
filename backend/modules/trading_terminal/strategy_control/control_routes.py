"""
Strategy Control Routes (TR5)
=============================

API endpoints for Strategy Control module.

Endpoints:
- GET  /api/control/health          - Service health
- GET  /api/control/state           - Get control state
- GET  /api/control/dashboard       - Get dashboard data

Profile:
- GET  /api/control/profile         - Get profile info
- POST /api/control/profile/switch  - Switch profile

Config:
- GET  /api/control/config          - Get config info
- POST /api/control/config/switch   - Switch config

Trading:
- POST /api/control/trading/pause   - Pause trading
- POST /api/control/trading/resume  - Resume trading

Kill Switch:
- GET  /api/control/kill-switch     - Get kill switch state
- POST /api/control/kill-switch/soft     - Trigger soft kill
- POST /api/control/kill-switch/hard     - Trigger hard kill
- POST /api/control/kill-switch/reset    - Reset kill switch

Override:
- GET  /api/control/override        - Get override state
- POST /api/control/override        - Enable override
- POST /api/control/override/disable - Disable override

Events:
- GET  /api/control/events          - Get control events
- GET  /api/control/events/kill-switch - Get kill switch events
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .control_service import strategy_control_service


router = APIRouter(prefix="/api/control", tags=["TR5 - Strategy Control"])


# ===========================================
# Request Models
# ===========================================

class ProfileSwitchRequest(BaseModel):
    profile: str = Field(..., description="Target profile: CONSERVATIVE, BALANCED, AGGRESSIVE")
    reason: str = Field("", description="Reason for switch")
    actor: str = Field("admin", description="Who initiated the switch")


class ConfigSwitchRequest(BaseModel):
    config_id: str = Field(..., description="Target config ID")
    reason: str = Field("", description="Reason for switch")
    actor: str = Field("admin", description="Who initiated the switch")


class PauseRequest(BaseModel):
    reason: str = Field("", description="Reason for pause")
    actor: str = Field("admin", description="Who initiated")


class ResumeRequest(BaseModel):
    reason: str = Field("", description="Reason for resume")
    actor: str = Field("admin", description="Who initiated")


class KillSwitchRequest(BaseModel):
    reason: str = Field("", description="Reason for kill switch")
    actor: str = Field("admin", description="Who initiated")
    close_method: str = Field("market", description="Position close method (for HARD kill)")


class KillSwitchResetRequest(BaseModel):
    reason: str = Field("", description="Reason for reset")
    actor: str = Field("admin", description="Who initiated")


class OverrideEnableRequest(BaseModel):
    reason: str = Field("", description="Reason for enabling override")
    actor: str = Field("admin", description="Who initiated")
    manual_order_routing: bool = Field(True, description="Enable manual order routing")
    disable_auto_switching: bool = Field(True, description="Disable auto profile switching")
    disable_strategy_runtime: bool = Field(True, description="Disable strategy runtime")


class OverrideDisableRequest(BaseModel):
    reason: str = Field("", description="Reason for disabling override")
    actor: str = Field("admin", description="Who initiated")


# ===========================================
# Health & State
# ===========================================

@router.get("/health")
async def get_service_health():
    """Get TR5 module health."""
    return strategy_control_service.get_health()


@router.get("/state")
async def get_control_state():
    """Get current control state."""
    state = strategy_control_service.get_state()
    return state.to_dict()


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard data with all control information."""
    return strategy_control_service.get_dashboard()


# ===========================================
# Profile Control
# ===========================================

@router.get("/profile")
async def get_profile():
    """Get current profile information."""
    return strategy_control_service.get_profile()


@router.post("/profile/switch")
async def switch_profile(request: ProfileSwitchRequest):
    """
    Switch to target profile.
    
    Valid profiles: CONSERVATIVE, BALANCED, AGGRESSIVE
    """
    result = strategy_control_service.switch_profile(
        profile=request.profile,
        reason=request.reason,
        actor=request.actor
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ===========================================
# Config Control
# ===========================================

@router.get("/config")
async def get_config():
    """Get current config information."""
    return strategy_control_service.get_config()


@router.post("/config/switch")
async def switch_config(request: ConfigSwitchRequest):
    """Switch to target config."""
    result = strategy_control_service.switch_config(
        config_id=request.config_id,
        reason=request.reason,
        actor=request.actor
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ===========================================
# Trading Pause/Resume
# ===========================================

@router.post("/trading/pause")
async def pause_trading(request: PauseRequest):
    """
    Pause trading.
    
    Effect:
    - Blocks new signal processing
    - Existing orders can complete
    - No orders cancelled
    - No positions closed
    """
    result = strategy_control_service.pause_trading(
        reason=request.reason,
        actor=request.actor
    )
    
    return result


@router.post("/trading/resume")
async def resume_trading(request: ResumeRequest):
    """Resume trading after pause."""
    result = strategy_control_service.resume_trading(
        reason=request.reason,
        actor=request.actor
    )
    
    return result


# ===========================================
# Kill Switch
# ===========================================

@router.get("/kill-switch")
async def get_kill_switch_state():
    """Get kill switch state."""
    return strategy_control_service.get_kill_switch_state()


@router.post("/kill-switch/soft")
async def trigger_soft_kill(request: KillSwitchRequest):
    """
    Trigger SOFT kill switch.
    
    Actions:
    - Block new entries
    - Cancel open orders
    - Allow position reductions
    - Does NOT force close positions
    
    Use for: bugs, strange behavior, high volatility
    """
    result = strategy_control_service.trigger_soft_kill(
        reason=request.reason,
        actor=request.actor
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/kill-switch/hard")
async def trigger_hard_kill(request: KillSwitchRequest):
    """
    Trigger HARD kill switch (EMERGENCY).
    
    Actions:
    - All SOFT actions
    - Force close all positions
    
    Use for: key compromise, runaway execution, extreme drawdown
    """
    result = strategy_control_service.trigger_hard_kill(
        reason=request.reason,
        actor=request.actor,
        close_method=request.close_method
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/kill-switch/reset")
async def reset_kill_switch(request: KillSwitchResetRequest):
    """Reset kill switch and return to normal mode."""
    result = strategy_control_service.reset_kill_switch(
        reason=request.reason,
        actor=request.actor
    )
    
    return result


# Alias endpoint for legacy support
@router.post("/kill-switch")
async def trigger_kill_switch_legacy(request: KillSwitchRequest):
    """
    Trigger kill switch (defaults to SOFT).
    
    Use /kill-switch/soft or /kill-switch/hard for explicit control.
    """
    return await trigger_soft_kill(request)


# ===========================================
# Override Mode
# ===========================================

@router.get("/override")
async def get_override_state():
    """Get override mode state."""
    return strategy_control_service.get_override_state()


@router.post("/override")
async def enable_override(request: OverrideEnableRequest):
    """
    Enable override mode.
    
    Override mode allows:
    - Manual order routing
    - Disable auto profile switching
    - Disable strategy runtime
    """
    settings = {
        "manual_order_routing": request.manual_order_routing,
        "disable_auto_switching": request.disable_auto_switching,
        "disable_strategy_runtime": request.disable_strategy_runtime
    }
    
    result = strategy_control_service.enable_override(
        reason=request.reason,
        actor=request.actor,
        settings=settings
    )
    
    return result


@router.post("/override/disable")
async def disable_override(request: OverrideDisableRequest):
    """Disable override mode."""
    result = strategy_control_service.disable_override(
        reason=request.reason,
        actor=request.actor
    )
    
    return result


# ===========================================
# Events
# ===========================================

@router.get("/events")
async def get_events(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None, description="Filter by action type")
):
    """Get control events."""
    events = strategy_control_service.get_events(limit=limit, action=action)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/kill-switch")
async def get_kill_switch_events(
    limit: int = Query(20, ge=1, le=100)
):
    """Get recent kill switch events."""
    events = strategy_control_service.get_kill_switch_events(limit=limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


# ===========================================
# Validation Helpers
# ===========================================

@router.get("/can-trade")
async def check_can_trade():
    """Check if trading is currently allowed."""
    can_trade, reason = strategy_control_service.can_trade()
    return {
        "can_trade": can_trade,
        "reason": reason,
        "trading_enabled": strategy_control_service.get_state().trading_enabled
    }


@router.get("/can-enter")
async def check_can_enter():
    """Check if new position entries are allowed."""
    can_enter, reason = strategy_control_service.can_enter_position()
    return {
        "can_enter": can_enter,
        "reason": reason
    }


# ===========================================
# State History
# ===========================================

@router.get("/history")
async def get_state_history(
    limit: int = Query(50, ge=1, le=200)
):
    """Get control state history."""
    history = strategy_control_service.get_state_history(limit=limit)
    return {
        "history": history,
        "count": len(history)
    }
