"""
Dashboard Routes

PHASE 40 — Real-Time Control Dashboard

API endpoints for dashboard.

Dashboard State:
- GET  /api/v1/dashboard/state/{symbol}  - Get dashboard state
- GET  /api/v1/dashboard/multi           - Get multi-symbol dashboard
- GET  /api/v1/dashboard/portfolio       - Get portfolio summary
- GET  /api/v1/dashboard/risk            - Get risk summary

Approval Queue:
- GET  /api/v1/approval/pending          - Get pending executions
- POST /api/v1/approval/approve          - Approve execution
- POST /api/v1/approval/reject           - Reject execution
- POST /api/v1/approval/reduce           - Reduce execution size
- POST /api/v1/approval/override         - Override execution params

Alerts:
- GET  /api/v1/dashboard/alerts          - Get active alerts
- POST /api/v1/dashboard/alerts/ack      - Acknowledge alert

Audit:
- GET  /api/v1/dashboard/audit           - Get audit logs
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .dashboard_engine import get_dashboard_engine
from .approval_engine import get_approval_engine
from .alerts_engine import get_alerts_engine
from .audit_engine import get_audit_engine


router = APIRouter(tags=["Control Dashboard"])


# ══════════════════════════════════════════════════════════════
# Request Models
# ══════════════════════════════════════════════════════════════

class CreatePendingRequest(BaseModel):
    """Request to create pending execution."""
    symbol: str
    side: str
    size_usd: float = Field(gt=0)
    strategy: str = "MANUAL"
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    hypothesis_id: Optional[str] = None
    expected_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.8
    reliability: float = 0.8


class ApproveRequest(BaseModel):
    """Request to approve execution."""
    pending_id: str
    user: str = "operator"
    note: Optional[str] = None


class RejectRequest(BaseModel):
    """Request to reject execution."""
    pending_id: str
    user: str = "operator"
    reason: str = ""


class ReduceRequest(BaseModel):
    """Request to reduce execution size."""
    pending_id: str
    new_size_usd: float = Field(gt=0)
    user: str = "operator"
    note: Optional[str] = None


class OverrideRequest(BaseModel):
    """Request to override execution params."""
    pending_id: str
    size_override: Optional[float] = None
    order_type_override: Optional[str] = None
    limit_price_override: Optional[float] = None
    user: str = "operator"
    note: Optional[str] = None


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge alert."""
    alert_id: str
    user: str = "operator"


# ══════════════════════════════════════════════════════════════
# Dashboard State Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/api/v1/dashboard/state/{symbol}")
async def get_dashboard_state(symbol: str):
    """
    Get aggregated dashboard state for symbol.
    
    Combines data from:
    - Market state
    - Hypothesis engine
    - Portfolio manager
    - Risk budget engine
    - Execution gateway
    """
    try:
        engine = get_dashboard_engine()
        state = engine.build_dashboard_state(symbol.upper())
        
        return {
            "status": "ok",
            "phase": "40",
            "symbol": state.symbol,
            "execution_mode": state.execution_mode,
            "market": {
                "regime": state.market.regime,
                "regime_confidence": state.market.regime_confidence,
                "fractal_bias": state.market.fractal_bias,
                "reflexivity_state": state.market.reflexivity_state,
                "volatility_regime": state.market.volatility_regime,
                "trend_strength": state.market.trend_strength,
            },
            "hypothesis": {
                "top_hypothesis": state.hypothesis.top_hypothesis,
                "confidence": state.hypothesis.confidence,
                "reliability": state.hypothesis.reliability,
                "competing_count": state.hypothesis.competing_count,
                "conflict_state": state.hypothesis.conflict_state,
                "top_scenario": state.hypothesis.top_scenario,
            },
            "portfolio": {
                "total_capital": state.portfolio.total_capital,
                "deployed_capital": state.portfolio.deployed_capital,
                "available_capital": state.portfolio.available_capital,
                "long_exposure": state.portfolio.long_exposure,
                "short_exposure": state.portfolio.short_exposure,
                "net_exposure": state.portfolio.net_exposure,
                "position_count": state.portfolio.position_count,
            },
            "risk": {
                "portfolio_risk": state.risk.portfolio_risk,
                "risk_utilization": state.risk.risk_utilization,
                "var_95": state.risk.var_95,
                "var_99": state.risk.var_99,
                "risk_state": state.risk.risk_state,
                "vol_scale_factor": state.risk.vol_scale_factor,
            },
            "pnl": {
                "realized_pnl": state.pnl.realized_pnl,
                "unrealized_pnl": state.pnl.unrealized_pnl,
                "total_pnl": state.pnl.total_pnl,
                "daily_pnl": state.pnl.daily_pnl,
                "avg_slippage_bps": state.pnl.avg_slippage_bps,
            },
            "execution": {
                "mode": state.execution.mode,
                "pending_count": state.execution.pending_count,
                "fill_count_today": state.execution.fill_count_today,
                "daily_volume": state.execution.daily_volume,
                "connected_exchanges": state.execution.connected_exchanges,
            },
            "alerts": {
                "count": state.alert_count,
                "critical_count": state.critical_alert_count,
                "items": [
                    {
                        "alert_id": a.alert_id,
                        "severity": a.severity,
                        "title": a.title,
                        "message": a.message,
                        "category": a.category,
                    }
                    for a in state.alerts[:5]
                ],
            },
            "last_updated": state.last_updated.isoformat(),
            "data_freshness_ms": state.data_freshness_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dashboard/multi")
async def get_multi_dashboard(
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols"),
):
    """Get dashboard for multiple symbols."""
    try:
        engine = get_dashboard_engine()
        
        symbol_list = symbols.split(",") if symbols else None
        dashboard = engine.build_multi_dashboard(symbol_list)
        
        return {
            "status": "ok",
            "phase": "40",
            "symbols": dashboard.symbols,
            "symbol_count": len(dashboard.symbols),
            "portfolio": {
                "total_capital": dashboard.portfolio.total_capital,
                "deployed_capital": dashboard.portfolio.deployed_capital,
                "position_count": dashboard.portfolio.position_count,
            },
            "risk": {
                "portfolio_risk": dashboard.risk.portfolio_risk,
                "risk_state": dashboard.risk.risk_state,
            },
            "execution": {
                "mode": dashboard.execution.mode,
                "pending_count": dashboard.execution.pending_count,
            },
            "alert_count": len(dashboard.alerts),
            "timestamp": dashboard.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dashboard/portfolio")
async def get_portfolio_summary():
    """Get portfolio summary."""
    try:
        engine = get_dashboard_engine()
        summary = engine.get_portfolio_summary()
        
        return {
            "status": "ok",
            "phase": "40",
            "portfolio": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dashboard/risk")
async def get_risk_summary():
    """Get risk summary."""
    try:
        engine = get_dashboard_engine()
        summary = engine.get_risk_summary()
        
        return {
            "status": "ok",
            "phase": "40",
            "risk": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Approval Queue Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/api/v1/approval/pending")
async def get_pending_executions(
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
):
    """Get pending executions awaiting approval."""
    try:
        engine = get_approval_engine()
        pending = engine.get_pending_executions(symbol=symbol, strategy=strategy)
        
        return {
            "status": "ok",
            "phase": "40",
            "count": len(pending),
            "pending": [
                {
                    "pending_id": p.pending_id,
                    "symbol": p.symbol,
                    "side": p.side,
                    "size_usd": p.size_usd,
                    "size_base": p.size_base,
                    "order_type": p.order_type,
                    "strategy": p.strategy,
                    "expected_entry": p.expected_entry,
                    "stop_loss": p.stop_loss,
                    "take_profit": p.take_profit,
                    "confidence": p.confidence,
                    "reliability": p.reliability,
                    "position_risk": p.position_risk,
                    "portfolio_risk_after": p.portfolio_risk_after,
                    "impact_state": p.impact_state,
                    "system_recommendation": p.system_recommendation,
                    "recommendation_reason": p.recommendation_reason,
                    "status": p.status,
                    "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                    "created_at": p.created_at.isoformat(),
                }
                for p in pending
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/approval/create")
async def create_pending_execution(request: CreatePendingRequest):
    """Create new pending execution."""
    try:
        engine = get_approval_engine()
        audit = get_audit_engine()
        
        pending = engine.add_pending_execution(
            symbol=request.symbol,
            side=request.side,
            size_usd=request.size_usd,
            strategy=request.strategy,
            order_type=request.order_type,
            limit_price=request.limit_price,
            hypothesis_id=request.hypothesis_id,
            expected_entry=request.expected_entry or 0.0,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            confidence=request.confidence,
            reliability=request.reliability,
        )
        
        # Log
        audit.log_action(
            action="PENDING_CREATED",
            action_type="QUEUE",
            symbol=request.symbol,
            pending_id=pending.pending_id,
            new_value={"size_usd": request.size_usd, "side": request.side},
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "pending_id": pending.pending_id,
            "symbol": pending.symbol,
            "system_recommendation": pending.system_recommendation,
            "recommendation_reason": pending.recommendation_reason,
            "expires_at": pending.expires_at.isoformat() if pending.expires_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/approval/approve")
async def approve_execution(request: ApproveRequest):
    """Approve pending execution."""
    try:
        engine = get_approval_engine()
        audit = get_audit_engine()
        
        result = engine.approve_execution(
            pending_id=request.pending_id,
            user=request.user,
            note=request.note,
        )
        
        # Log
        audit.log_approval(
            action="APPROVE",
            pending_id=request.pending_id,
            symbol=result.pending_id,  # Will be updated
            user=request.user,
            order_id=result.order_id,
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "result": {
                "success": result.success,
                "action": result.action,
                "pending_id": result.pending_id,
                "order_id": result.order_id,
                "execution_status": result.execution_status,
                "message": result.message,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/approval/reject")
async def reject_execution(request: RejectRequest):
    """Reject pending execution."""
    try:
        engine = get_approval_engine()
        audit = get_audit_engine()
        
        result = engine.reject_execution(
            pending_id=request.pending_id,
            user=request.user,
            reason=request.reason,
        )
        
        # Log
        audit.log_approval(
            action="REJECT",
            pending_id=request.pending_id,
            symbol="",
            user=request.user,
            note=request.reason,
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "result": {
                "success": result.success,
                "action": result.action,
                "pending_id": result.pending_id,
                "message": result.message,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/approval/reduce")
async def reduce_execution(request: ReduceRequest):
    """Reduce pending execution size."""
    try:
        engine = get_approval_engine()
        audit = get_audit_engine()
        
        # Get original size
        pending = engine.get_pending_execution(request.pending_id)
        original_size = pending.size_usd if pending else 0
        
        result = engine.reduce_execution(
            pending_id=request.pending_id,
            new_size_usd=request.new_size_usd,
            user=request.user,
            note=request.note,
        )
        
        # Log
        audit.log_approval(
            action="REDUCE",
            pending_id=request.pending_id,
            symbol=pending.symbol if pending else "",
            user=request.user,
            previous_size=original_size,
            new_size=request.new_size_usd,
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "result": {
                "success": result.success,
                "action": result.action,
                "pending_id": result.pending_id,
                "message": result.message,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/approval/override")
async def override_execution(request: OverrideRequest):
    """Override pending execution params."""
    try:
        engine = get_approval_engine()
        audit = get_audit_engine()
        
        result = engine.override_execution(
            pending_id=request.pending_id,
            size_override=request.size_override,
            order_type_override=request.order_type_override,
            limit_price_override=request.limit_price_override,
            user=request.user,
            note=request.note,
        )
        
        # Log
        audit.log_action(
            action="OVERRIDE",
            action_type="APPROVAL",
            pending_id=request.pending_id,
            user=request.user,
            new_value={
                "size": request.size_override,
                "order_type": request.order_type_override,
                "limit_price": request.limit_price_override,
            },
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "result": {
                "success": result.success,
                "action": result.action,
                "pending_id": result.pending_id,
                "message": result.message,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Alerts Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/api/v1/dashboard/alerts")
async def get_alerts(
    symbol: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Get active alerts."""
    try:
        engine = get_alerts_engine()
        
        # Run checks to generate new alerts
        engine.run_all_checks()
        
        alerts = engine.get_active_alerts(
            symbol=symbol,
            category=category,
            severity=severity,
            limit=limit,
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "count": len(alerts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "symbol": a.symbol,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "source": a.source,
                    "category": a.category,
                    "value": a.value,
                    "threshold": a.threshold,
                    "acknowledged": a.acknowledged,
                    "created_at": a.created_at.isoformat(),
                }
                for a in alerts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dashboard/alerts/{symbol}")
async def get_alerts_for_symbol(symbol: str):
    """Get alerts for specific symbol."""
    try:
        engine = get_alerts_engine()
        alerts = engine.get_active_alerts(symbol=symbol.upper())
        
        return {
            "status": "ok",
            "phase": "40",
            "symbol": symbol.upper(),
            "count": len(alerts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "category": a.category,
                }
                for a in alerts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dashboard/alerts/ack")
async def acknowledge_alert(request: AcknowledgeAlertRequest):
    """Acknowledge alert."""
    try:
        engine = get_alerts_engine()
        audit = get_audit_engine()
        
        success = engine.acknowledge_alert(request.alert_id, request.user)
        
        if success:
            audit.log_alert_acknowledgement(request.alert_id, request.user)
        
        return {
            "status": "ok",
            "phase": "40",
            "acknowledged": success,
            "alert_id": request.alert_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Audit Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/api/v1/dashboard/audit")
async def get_audit_logs(
    action_type: Optional[str] = None,
    user: Optional[str] = None,
    symbol: Optional[str] = None,
    hours_back: Optional[int] = Query(default=24, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get audit logs."""
    try:
        engine = get_audit_engine()
        logs = engine.get_logs(
            action_type=action_type,
            user=user,
            symbol=symbol,
            hours_back=hours_back,
            limit=limit,
        )
        
        return {
            "status": "ok",
            "phase": "40",
            "count": len(logs),
            "logs": [
                {
                    "audit_id": l.audit_id,
                    "action": l.action,
                    "action_type": l.action_type,
                    "user": l.user,
                    "symbol": l.symbol,
                    "order_id": l.order_id,
                    "pending_id": l.pending_id,
                    "previous_size": l.previous_size,
                    "new_size": l.new_size,
                    "success": l.success,
                    "timestamp": l.timestamp.isoformat(),
                }
                for l in logs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dashboard/audit/{symbol}")
async def get_audit_logs_for_symbol(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get audit logs for specific symbol."""
    try:
        engine = get_audit_engine()
        logs = engine.get_logs(symbol=symbol.upper(), limit=limit)
        
        return {
            "status": "ok",
            "phase": "40",
            "symbol": symbol.upper(),
            "count": len(logs),
            "logs": [
                {
                    "audit_id": l.audit_id,
                    "action": l.action,
                    "user": l.user,
                    "timestamp": l.timestamp.isoformat(),
                }
                for l in logs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dashboard/audit/stats")
async def get_audit_statistics(
    hours_back: int = Query(default=24, ge=1, le=168),
):
    """Get audit statistics."""
    try:
        engine = get_audit_engine()
        stats = engine.get_statistics(hours_back=hours_back)
        
        return {
            "status": "ok",
            "phase": "40",
            "statistics": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Health Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/api/v1/dashboard/health")
async def dashboard_health():
    """Dashboard health check."""
    try:
        approval = get_approval_engine()
        alerts = get_alerts_engine()
        
        return {
            "status": "ok",
            "phase": "40",
            "module": "Control Dashboard",
            "components": {
                "dashboard_state": "ok",
                "approval_queue": "ok",
                "alerts_engine": "ok",
                "audit_engine": "ok",
            },
            "pending_count": approval.get_pending_count(),
            "alert_count": alerts.get_alert_count(),
            "critical_alerts": alerts.get_alert_count(severity="CRITICAL"),
            "endpoints": [
                "GET  /api/v1/dashboard/state/{symbol}",
                "GET  /api/v1/dashboard/multi",
                "GET  /api/v1/dashboard/portfolio",
                "GET  /api/v1/dashboard/risk",
                "GET  /api/v1/approval/pending",
                "POST /api/v1/approval/approve",
                "POST /api/v1/approval/reject",
                "POST /api/v1/approval/reduce",
                "POST /api/v1/approval/override",
                "GET  /api/v1/dashboard/alerts",
                "GET  /api/v1/dashboard/audit",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
