"""
Kill Switch Routes

PHASE 41.3 — Kill Switch Engine

API endpoints:
- POST /api/v1/safety/kill-switch/activate      - Activate kill switch
- POST /api/v1/safety/kill-switch/deactivate    - Deactivate kill switch
- POST /api/v1/safety/kill-switch/safe-mode     - Enter safe mode
- GET  /api/v1/safety/kill-switch/state         - Get state
- GET  /api/v1/safety/kill-switch/status        - Get full status
- GET  /api/v1/safety/kill-switch/events        - Get event history
- GET  /api/v1/safety/kill-switch/config        - Get configuration
- POST /api/v1/safety/kill-switch/check         - Check if order allowed
- GET  /api/v1/safety/kill-switch/health        - Health check
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .kill_switch_engine import get_kill_switch
from .kill_switch_types import (
    KillSwitchTrigger,
    ActivateKillSwitchRequest,
    DeactivateKillSwitchRequest,
)


router = APIRouter(prefix="/api/v1/safety/kill-switch", tags=["Safety Kill Switch"])


# ══════════════════════════════════════════════════════════════
# Request Models
# ══════════════════════════════════════════════════════════════

class ActivateRequest(BaseModel):
    trigger: str = "MANUAL"
    reason: str = ""
    user: str = "operator"
    cancel_pending: bool = True
    close_positions: bool = False
    reduce_exposure: bool = True
    emergency: bool = False


class DeactivateRequest(BaseModel):
    user: str = "operator"
    reason: str = ""
    confirm_safe: bool = False


class SafeModeRequest(BaseModel):
    reason: str = ""
    user: str = "operator"


class CheckOrderRequest(BaseModel):
    symbol: str
    size_usd: float = Field(gt=0)
    side: str = "BUY"


# ══════════════════════════════════════════════════════════════
# Activate / Deactivate
# ══════════════════════════════════════════════════════════════

@router.post("/activate")
async def activate_kill_switch(request: ActivateRequest):
    """Activate kill switch — emergency stop."""
    try:
        ks = get_kill_switch()
        event = ks.activate(ActivateKillSwitchRequest(
            trigger=KillSwitchTrigger(request.trigger),
            reason=request.reason,
            user=request.user,
            cancel_pending=request.cancel_pending,
            close_positions=request.close_positions,
            reduce_exposure=request.reduce_exposure,
            emergency=request.emergency,
        ))

        return {
            "status": "ok",
            "phase": "41",
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "previous_state": event.previous_state.value,
                "new_state": event.new_state.value,
                "trigger": event.trigger.value if event.trigger else None,
                "trigger_reason": event.trigger_reason,
                "actions_taken": [a.value for a in event.actions_taken],
                "triggered_by": event.triggered_by,
                "timestamp": event.timestamp.isoformat(),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deactivate")
async def deactivate_kill_switch(request: DeactivateRequest):
    """Deactivate kill switch — return to normal."""
    try:
        ks = get_kill_switch()
        event = ks.deactivate(DeactivateKillSwitchRequest(
            user=request.user,
            reason=request.reason,
            confirm_safe=request.confirm_safe,
        ))

        return {
            "status": "ok",
            "phase": "41",
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "previous_state": event.previous_state.value,
                "new_state": event.new_state.value,
                "triggered_by": event.triggered_by,
                "timestamp": event.timestamp.isoformat(),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/safe-mode")
async def enter_safe_mode(request: SafeModeRequest):
    """Enter safe mode — reduced operations."""
    try:
        ks = get_kill_switch()
        event = ks.enter_safe_mode(reason=request.reason, user=request.user)

        return {
            "status": "ok",
            "phase": "41",
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "previous_state": event.previous_state.value,
                "new_state": event.new_state.value,
                "actions_taken": [a.value for a in event.actions_taken],
                "timestamp": event.timestamp.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# State / Status
# ══════════════════════════════════════════════════════════════

@router.get("/state")
async def get_kill_switch_state():
    """Get current kill switch state."""
    try:
        ks = get_kill_switch()
        state = ks.get_state()

        return {
            "status": "ok",
            "phase": "41",
            "state": state.value,
            "is_active": ks.is_active(),
            "is_safe_mode": ks.is_safe_mode(),
            "is_disabled": ks.is_disabled(),
            "size_modifier": ks.get_size_modifier(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_kill_switch_status():
    """Get full kill switch status."""
    try:
        ks = get_kill_switch()
        s = ks.get_status()

        return {
            "status": "ok",
            "phase": "41",
            "kill_switch": {
                "state": s.state.value,
                "is_active": s.is_active,
                "is_safe_mode": s.is_safe_mode,
                "last_trigger": s.last_trigger.value if s.last_trigger else None,
                "last_trigger_reason": s.last_trigger_reason,
                "last_triggered_at": s.last_triggered_at.isoformat() if s.last_triggered_at else None,
                "triggered_by": s.triggered_by,
                "actions_taken": [a.value for a in s.actions_taken],
                "blocked_orders_count": s.blocked_orders_count,
                "cancelled_orders_count": s.cancelled_orders_count,
                "closed_positions_count": s.closed_positions_count,
                "uptime_since": s.uptime_since.isoformat(),
                "last_check": s.last_check.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Events
# ══════════════════════════════════════════════════════════════

@router.get("/events")
async def get_kill_switch_events(
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get kill switch event history."""
    try:
        ks = get_kill_switch()
        events = ks.get_events(limit=limit)

        return {
            "status": "ok",
            "phase": "41",
            "count": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "previous_state": e.previous_state.value,
                    "new_state": e.new_state.value,
                    "trigger": e.trigger.value if e.trigger else None,
                    "trigger_reason": e.trigger_reason,
                    "actions_taken": [a.value for a in e.actions_taken],
                    "triggered_by": e.triggered_by,
                    "portfolio_risk": e.portfolio_risk,
                    "drawdown": e.drawdown,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in events
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Check Order
# ══════════════════════════════════════════════════════════════

@router.post("/check")
async def check_order(request: CheckOrderRequest):
    """Check if order is allowed through kill switch."""
    try:
        ks = get_kill_switch()
        result = ks.check_order_allowed(
            symbol=request.symbol,
            size_usd=request.size_usd,
            side=request.side,
        )

        return {
            "status": "ok",
            "phase": "41",
            "check": {
                "allowed": result.allowed,
                "state": result.state.value,
                "blocked_reason": result.blocked_reason,
                "size_modified": result.size_modified,
                "size_modifier": result.size_modifier,
                "warnings": result.warnings,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════

@router.get("/config")
async def get_kill_switch_config():
    """Get kill switch configuration."""
    try:
        ks = get_kill_switch()
        c = ks.get_config()

        return {
            "status": "ok",
            "phase": "41",
            "config": c.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def kill_switch_health():
    """Kill switch health check."""
    try:
        ks = get_kill_switch()
        state = ks.get_state()

        return {
            "status": "ok",
            "phase": "41",
            "module": "Safety Kill Switch",
            "state": state.value,
            "is_active": ks.is_active(),
            "endpoints": [
                "POST /api/v1/safety/kill-switch/activate",
                "POST /api/v1/safety/kill-switch/deactivate",
                "POST /api/v1/safety/kill-switch/safe-mode",
                "GET  /api/v1/safety/kill-switch/state",
                "GET  /api/v1/safety/kill-switch/status",
                "GET  /api/v1/safety/kill-switch/events",
                "POST /api/v1/safety/kill-switch/check",
                "GET  /api/v1/safety/kill-switch/config",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
