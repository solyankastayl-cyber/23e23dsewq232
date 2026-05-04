"""
TT5 - Control Routes
====================
FastAPI router for operator control endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from .control_repository import ControlRepository
from .control_engine import ControlEngine
from .control_query_service import ControlQueryService


router = APIRouter(tags=["Operator Control"])

# Singleton instances
_repo = ControlRepository()
_engine = ControlEngine(_repo)
_query = ControlQueryService(_repo)


# === Request Models ===

class AlphaModeRequest(BaseModel):
    mode: str  # AUTO / MANUAL / OFF


class OverrideRequest(BaseModel):
    override_type: str
    scope_key: str
    reason: Optional[str] = ""


class IngestActionsRequest(BaseModel):
    actions: List[dict]


# === State Endpoints ===

@router.get("/api/control/state")
async def get_control_state():
    """Get current control state"""
    try:
        return {
            "ok": True,
            "data": _engine.get_state(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/control/summary")
async def get_control_summary():
    """Get control summary for UI"""
    try:
        return {
            "ok": True,
            "data": _engine.get_summary(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === System Control Endpoints ===

@router.post("/api/control/pause")
async def pause_system():
    """Pause system - stop new trades"""
    try:
        return {
            "ok": True,
            "data": _engine.pause(),
            "message": "System paused",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/resume")
async def resume_system():
    """Resume normal operation"""
    try:
        return {
            "ok": True,
            "data": _engine.resume(),
            "message": "System resumed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/kill/soft")
async def soft_kill():
    """Soft kill - no new entries, manage existing"""
    try:
        return {
            "ok": True,
            "data": _engine.soft_kill(),
            "message": "Soft kill activated",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/kill/hard")
async def hard_kill():
    """Hard kill - stop all trading"""
    try:
        return {
            "ok": True,
            "data": _engine.hard_kill(),
            "message": "Hard kill activated - ALL TRADING STOPPED",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/emergency")
async def emergency_stop():
    """Emergency stop - halt everything"""
    try:
        return {
            "ok": True,
            "data": _engine.emergency_stop(),
            "message": "EMERGENCY STOP ACTIVATED",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Alpha Mode Endpoints ===

@router.post("/api/control/alpha/mode")
async def set_alpha_mode(request: AlphaModeRequest):
    """Set alpha factory mode: AUTO / MANUAL / OFF"""
    try:
        if request.mode not in {"AUTO", "MANUAL", "OFF"}:
            raise HTTPException(status_code=400, detail="Invalid mode. Must be AUTO, MANUAL, or OFF")
        
        return {
            "ok": True,
            "data": _engine.set_alpha_mode(request.mode),
            "message": f"Alpha mode set to {request.mode}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Pending Actions Endpoints ===

@router.get("/api/control/alpha/pending")
async def get_pending_actions():
    """Get all pending alpha actions"""
    try:
        return {
            "ok": True,
            "data": _engine.pending_actions(),
            "count": len(_engine.pending_actions()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/alpha/approve/{pending_id}")
async def approve_action(pending_id: str):
    """Approve a pending action"""
    try:
        result = _engine.approve_action(pending_id)
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/alpha/reject/{pending_id}")
async def reject_action(pending_id: str):
    """Reject a pending action"""
    try:
        result = _engine.reject_action(pending_id)
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/alpha/approve-all")
async def approve_all_actions():
    """Approve all pending actions"""
    try:
        return {
            "ok": True,
            "data": _engine.approve_all(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/alpha/reject-all")
async def reject_all_actions():
    """Reject all pending actions"""
    try:
        return {
            "ok": True,
            "data": _engine.reject_all(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/alpha/ingest")
async def ingest_alpha_actions(request: IngestActionsRequest):
    """Ingest actions from Alpha Factory"""
    try:
        result = _engine.ingest_alpha_actions(request.actions)
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Overrides Endpoints ===

@router.get("/api/control/overrides")
async def list_overrides():
    """List active overrides"""
    try:
        return {
            "ok": True,
            "data": _engine.list_overrides(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/control/override")
async def add_override(request: OverrideRequest):
    """Add operator override rule"""
    try:
        result = _engine.add_override(
            request.override_type,
            request.scope_key,
            request.reason
        )
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/control/override/{rule_id}")
async def remove_override(rule_id: str):
    """Remove override rule"""
    try:
        result = _engine.remove_override(rule_id)
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Permission Checks ===

@router.get("/api/control/can-trade")
async def check_can_trade():
    """Check if trading is allowed"""
    try:
        return {
            "ok": True,
            "data": {
                "can_trade": _engine.can_trade(),
                "can_open_entry": _engine.can_open_entry(),
                "can_manage_positions": _engine.can_manage_positions(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === History ===

@router.get("/api/control/history")
async def get_action_history(limit: int = Query(50)):
    """Get resolved actions history"""
    try:
        return {
            "ok": True,
            "data": _engine.get_action_history(limit),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Terminal State Integration ===

@router.get("/api/control/for-terminal-state")
async def get_for_terminal_state():
    """Get control data for terminal state"""
    try:
        return {
            "ok": True,
            "data": _query.format_for_terminal_state(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Reset (Dev/Test) ===

@router.post("/api/control/reset")
async def reset_control():
    """Reset control to defaults"""
    try:
        _repo.reset()
        return {
            "ok": True,
            "message": "Control layer reset",
            "data": _engine.get_state(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Export service ===

def get_control_service():
    """Get control service for integration"""
    return {
        "repo": _repo,
        "engine": _engine,
        "query": _query,
    }
