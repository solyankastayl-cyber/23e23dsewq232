"""
Circuit Breaker Routes

PHASE 41.4 — Circuit Breaker Engine

API endpoints:
- GET  /api/v1/safety/circuit-breaker/status    - Get status
- GET  /api/v1/safety/circuit-breaker/rules     - Get all rules
- GET  /api/v1/safety/circuit-breaker/rules/{id} - Get rule by ID
- POST /api/v1/safety/circuit-breaker/check     - Check if order allowed
- POST /api/v1/safety/circuit-breaker/reset     - Reset all breakers
- POST /api/v1/safety/circuit-breaker/reset/{id} - Reset specific rule
- POST /api/v1/safety/circuit-breaker/enable/{id} - Enable rule
- POST /api/v1/safety/circuit-breaker/disable/{id} - Disable rule
- POST /api/v1/safety/circuit-breaker/record-fill - Record fill for tracking
- POST /api/v1/safety/circuit-breaker/record-error - Record execution error
- GET  /api/v1/safety/circuit-breaker/events    - Get events
- GET  /api/v1/safety/circuit-breaker/config    - Get config
- GET  /api/v1/safety/circuit-breaker/health    - Health check
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .breaker_engine import get_circuit_breaker


router = APIRouter(prefix="/api/v1/safety/circuit-breaker", tags=["Circuit Breaker"])


# ══════════════════════════════════════════════════════════════
# Request Models
# ══════════════════════════════════════════════════════════════

class CheckOrderRequest(BaseModel):
    symbol: str = ""
    size_usd: float = 0.0
    side: str = "BUY"


class RecordFillRequest(BaseModel):
    pnl: float


class RecordErrorRequest(BaseModel):
    error: str = ""


class RecordSlippageRequest(BaseModel):
    slippage_bps: float


# ══════════════════════════════════════════════════════════════
# Status
# ══════════════════════════════════════════════════════════════

@router.get("/status")
async def get_breaker_status():
    """Get overall circuit breaker status."""
    try:
        cb = get_circuit_breaker()
        s = cb.get_status()

        return {
            "status": "ok",
            "phase": "41",
            "circuit_breaker": {
                "state": s.state.value,
                "active_rules": s.active_rules,
                "tripped_rules": s.tripped_rules,
                "total_rules": s.total_rules,
                "size_modifier": s.size_modifier,
                "new_entries_blocked": s.new_entries_blocked,
                "limit_only": s.limit_only,
                "kill_switch_triggered": s.kill_switch_triggered,
                "tripped_rule_ids": s.tripped_rule_ids,
                "tripped_details": s.tripped_details,
                "total_trips": s.total_trips,
                "trips_last_24h": s.trips_last_24h,
                "last_trip_at": s.last_trip_at.isoformat() if s.last_trip_at else None,
                "last_check": s.last_check.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Rules
# ══════════════════════════════════════════════════════════════

@router.get("/rules")
async def get_rules():
    """Get all circuit breaker rules."""
    try:
        cb = get_circuit_breaker()
        rules = cb.get_rules()

        return {
            "status": "ok",
            "phase": "41",
            "count": len(rules),
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "rule_type": r.rule_type.value,
                    "name": r.name,
                    "description": r.description,
                    "enabled": r.enabled,
                    "state": r.state.value,
                    "current_value": r.current_value,
                    "warning_threshold": r.warning_threshold,
                    "trigger_threshold": r.trigger_threshold,
                    "critical_threshold": r.critical_threshold,
                    "size_modifier_warning": r.size_modifier_warning,
                    "size_modifier_trigger": r.size_modifier_trigger,
                    "size_modifier_critical": r.size_modifier_critical,
                    "trip_count": r.trip_count,
                    "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                }
                for r in rules
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get specific rule."""
    try:
        cb = get_circuit_breaker()
        rule = cb.get_rule(rule_id.upper())

        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return {
            "status": "ok",
            "phase": "41",
            "rule": {
                "rule_id": rule.rule_id,
                "rule_type": rule.rule_type.value,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "state": rule.state.value,
                "current_value": rule.current_value,
                "warning_threshold": rule.warning_threshold,
                "trigger_threshold": rule.trigger_threshold,
                "critical_threshold": rule.critical_threshold,
                "warning_actions": [a.value for a in rule.warning_actions],
                "trigger_actions": [a.value for a in rule.trigger_actions],
                "critical_actions": [a.value for a in rule.critical_actions],
                "size_modifier_warning": rule.size_modifier_warning,
                "size_modifier_trigger": rule.size_modifier_trigger,
                "size_modifier_critical": rule.size_modifier_critical,
                "recovery_threshold": rule.recovery_threshold,
                "cooldown_seconds": rule.cooldown_seconds,
                "trip_count": rule.trip_count,
                "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Check Order
# ══════════════════════════════════════════════════════════════

@router.post("/check")
async def check_order(request: CheckOrderRequest):
    """Check if order passes circuit breaker rules."""
    try:
        cb = get_circuit_breaker()
        result = cb.check_order_allowed(
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
                "size_modifier": result.size_modifier,
                "new_entries_blocked": result.new_entries_blocked,
                "limit_only": result.limit_only,
                "tripped_rules": result.tripped_rules,
                "warnings": result.warnings,
                "blocked_reason": result.blocked_reason,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Reset
# ══════════════════════════════════════════════════════════════

@router.post("/reset")
async def reset_all_breakers():
    """Reset all circuit breakers to CLOSED."""
    try:
        cb = get_circuit_breaker()
        cb.reset_all()

        return {
            "status": "ok",
            "phase": "41",
            "message": "All circuit breakers reset to CLOSED",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{rule_id}")
async def reset_rule(rule_id: str):
    """Reset specific circuit breaker rule."""
    try:
        cb = get_circuit_breaker()
        success = cb.reset_rule(rule_id.upper())

        if not success:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return {
            "status": "ok",
            "phase": "41",
            "rule_id": rule_id.upper(),
            "message": f"Rule {rule_id} reset to CLOSED",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Enable / Disable
# ══════════════════════════════════════════════════════════════

@router.post("/enable/{rule_id}")
async def enable_rule(rule_id: str):
    """Enable a circuit breaker rule."""
    try:
        cb = get_circuit_breaker()
        success = cb.enable_rule(rule_id.upper())

        if not success:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return {"status": "ok", "phase": "41", "rule_id": rule_id.upper(), "enabled": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable/{rule_id}")
async def disable_rule(rule_id: str):
    """Disable a circuit breaker rule."""
    try:
        cb = get_circuit_breaker()
        success = cb.disable_rule(rule_id.upper())

        if not success:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return {"status": "ok", "phase": "41", "rule_id": rule_id.upper(), "enabled": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Record Events
# ══════════════════════════════════════════════════════════════

@router.post("/record-fill")
async def record_fill(request: RecordFillRequest):
    """Record a trade fill for loss streak tracking."""
    try:
        cb = get_circuit_breaker()
        cb.record_fill(request.pnl)

        return {"status": "ok", "phase": "41", "pnl_recorded": request.pnl}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-error")
async def record_error(request: RecordErrorRequest):
    """Record an execution error."""
    try:
        cb = get_circuit_breaker()
        cb.record_execution_error(request.error)

        return {"status": "ok", "phase": "41", "error_recorded": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-slippage")
async def record_slippage(request: RecordSlippageRequest):
    """Record slippage measurement."""
    try:
        cb = get_circuit_breaker()
        cb.record_slippage(request.slippage_bps)

        return {"status": "ok", "phase": "41", "slippage_recorded": request.slippage_bps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Events
# ══════════════════════════════════════════════════════════════

@router.get("/events")
async def get_events(
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get circuit breaker events."""
    try:
        cb = get_circuit_breaker()
        events = cb.get_events(limit=limit)

        return {
            "status": "ok",
            "phase": "41",
            "count": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "rule_id": e.rule_id,
                    "rule_type": e.rule_type.value,
                    "severity": e.severity.value,
                    "previous_state": e.previous_state.value,
                    "new_state": e.new_state.value,
                    "current_value": e.current_value,
                    "threshold": e.threshold,
                    "actions_taken": [a.value for a in e.actions_taken],
                    "size_modifier": e.size_modifier,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in events
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Config & Health
# ══════════════════════════════════════════════════════════════

@router.get("/config")
async def get_config():
    """Get circuit breaker configuration."""
    try:
        cb = get_circuit_breaker()
        return {"status": "ok", "phase": "41", "config": cb.get_config().model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def breaker_health():
    """Circuit breaker health check."""
    try:
        cb = get_circuit_breaker()
        s = cb.get_status()

        return {
            "status": "ok",
            "phase": "41",
            "module": "Circuit Breaker",
            "state": s.state.value,
            "active_rules": s.active_rules,
            "tripped_rules": s.tripped_rules,
            "endpoints": [
                "GET  /api/v1/safety/circuit-breaker/status",
                "GET  /api/v1/safety/circuit-breaker/rules",
                "POST /api/v1/safety/circuit-breaker/check",
                "POST /api/v1/safety/circuit-breaker/reset",
                "GET  /api/v1/safety/circuit-breaker/events",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
