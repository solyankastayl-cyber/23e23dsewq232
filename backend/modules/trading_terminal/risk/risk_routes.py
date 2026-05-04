"""
Risk Routes (TR4)
=================

API endpoints for Risk Dashboard.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from .risk_service import risk_service


router = APIRouter(prefix="/api/risk", tags=["TR4 - Risk Dashboard"])


class TailRiskUpdate(BaseModel):
    var_95: float
    cvar_95: float
    var_99: float = 0.0
    cvar_99: float = 0.0


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = "admin"


@router.get("/health")
async def get_service_health():
    """Get TR4 module health."""
    return risk_service.get_health()


@router.get("/state")
async def get_risk_state():
    """Get complete risk state."""
    state = risk_service.get_risk_state()
    return state.to_dict()


@router.get("/metrics")
async def get_risk_metrics():
    """Get risk metrics (drawdown, daily loss)."""
    metrics = risk_service.get_metrics()
    return metrics.to_dict()


@router.get("/exposure")
async def get_exposure():
    """Get exposure metrics."""
    exposure = risk_service.get_exposure()
    return exposure.to_dict()


@router.get("/concentration")
async def get_concentration():
    """Get concentration metrics."""
    concentration = risk_service.get_concentration()
    return concentration.to_dict()


@router.get("/tail")
async def get_tail_risk():
    """Get VaR/CVaR tail risk metrics."""
    tail = risk_service.get_tail_risk()
    return tail.to_dict()


@router.post("/tail")
async def update_tail_risk(request: TailRiskUpdate):
    """Update tail risk from Monte Carlo."""
    risk_service.update_tail_risk(
        var_95=request.var_95, cvar_95=request.cvar_95,
        var_99=request.var_99, cvar_99=request.cvar_99
    )
    return {"success": True, "message": "Tail risk updated"}


@router.get("/alerts")
async def get_alerts(active_only: bool = True):
    """Get risk alerts."""
    alerts = risk_service.get_alerts(active_only=active_only)
    return {"alerts": [a.to_dict() for a in alerts], "count": len(alerts), "active_only": active_only}


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(alert_id: str, request: AcknowledgeRequest):
    """Acknowledge a risk alert."""
    success = risk_service.acknowledge_alert(alert_id, request.acknowledged_by)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": f"Alert {alert_id} acknowledged"}


@router.get("/guardrails")
async def get_guardrails():
    """Get guardrail rules."""
    return {"rules": risk_service.get_guardrail_rules()}


@router.get("/guardrails/events")
async def get_guardrail_events(limit: int = 50):
    """Get guardrail events."""
    events = risk_service.get_guardrail_events(limit)
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@router.post("/guardrails/{rule_name}/enable")
async def enable_guardrail(rule_name: str):
    """Enable a guardrail rule."""
    success = risk_service.enable_guardrail(rule_name)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True, "message": f"Rule {rule_name} enabled"}


@router.post("/guardrails/{rule_name}/disable")
async def disable_guardrail(rule_name: str):
    """Disable a guardrail rule."""
    success = risk_service.disable_guardrail(rule_name)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True, "message": f"Rule {rule_name} disabled"}


@router.get("/dashboard")
async def get_dashboard():
    """Get risk dashboard data."""
    return risk_service.get_dashboard()


@router.get("/snapshots")
async def get_snapshots(limit: int = 100):
    """Get risk snapshots history."""
    snapshots = risk_service.get_snapshots(limit)
    return {"snapshots": [s.to_dict() for s in snapshots], "count": len(snapshots)}
