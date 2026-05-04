"""
SEC3 Connection Safety Routes
=============================

API endpoints for connection safety monitoring.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .connection_service import connection_safety_service


router = APIRouter(prefix="/api/connection-safety", tags=["sec3-connection-safety"])


# ===========================================
# Request/Response Models
# ===========================================

class ActionRequest(BaseModel):
    """Request for safety action"""
    reason: str = Field(..., description="Reason for action")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for SEC3 Connection Safety"""
    return connection_safety_service.get_health()


# ===========================================
# Connection Health
# ===========================================

@router.get("/status")
async def get_all_health():
    """
    Get health status for all exchanges.
    
    Returns connection health for each monitored exchange including:
    - API status and latency
    - WebSocket health
    - Error rates
    - Rate limit pressure
    - Degraded/quarantined flags
    """
    healths = connection_safety_service.get_all_health()
    return {
        "exchanges": [h.to_dict() for h in healths],
        "count": len(healths),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/status/{exchange}")
async def get_exchange_health(exchange: str):
    """
    Get health status for specific exchange.
    """
    health = connection_safety_service.get_exchange_health(exchange)
    
    if not health:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
    
    return health.to_dict()


@router.get("/summary")
async def get_summary():
    """
    Get summary of all connections.
    
    Shows:
    - Total exchanges monitored
    - Healthy/degraded/quarantined counts
    - Active incidents
    - Overall health status
    """
    summary = connection_safety_service.get_summary()
    return summary.to_dict()


@router.post("/check/{exchange}")
async def check_exchange_health(exchange: str):
    """
    Force health check for exchange.
    """
    health = connection_safety_service.check_health(exchange)
    return health.to_dict()


# ===========================================
# Incidents
# ===========================================

@router.get("/incidents")
async def get_incidents(
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    limit: int = Query(50, description="Maximum records")
):
    """
    Get connection incidents.
    
    Returns history of connection problems:
    - Outages
    - Latency spikes
    - Rate limit hits
    - WebSocket desyncs
    """
    incidents = connection_safety_service.get_incidents(
        exchange=exchange,
        resolved=resolved,
        limit=limit
    )
    return {
        "incidents": [i.to_dict() for i in incidents],
        "count": len(incidents),
        "timestamp": int(time.time() * 1000)
    }


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    request: ActionRequest
):
    """
    Resolve an incident.
    """
    success = connection_safety_service.resolve_incident(incident_id, request.reason)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    
    return {
        "incidentId": incident_id,
        "resolved": True,
        "note": request.reason,
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Actions
# ===========================================

@router.get("/actions")
async def get_actions(
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    limit: int = Query(50, description="Maximum records")
):
    """
    Get safety actions history.
    
    Shows actions taken:
    - Degrade mode activations
    - Order freezes
    - Quarantines
    - Restorations
    """
    actions = connection_safety_service.get_actions(
        exchange=exchange,
        limit=limit
    )
    return {
        "actions": [a.to_dict() for a in actions],
        "count": len(actions),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Safety Controls
# ===========================================

@router.post("/{exchange}/degrade")
async def degrade_exchange(
    exchange: str,
    request: ActionRequest
):
    """
    Put exchange in degraded mode.
    
    In degraded mode:
    - Reads allowed
    - Reduce-only orders allowed
    - No new position entries
    """
    action = connection_safety_service.degrade_exchange(exchange, request.reason)
    return {
        "exchange": exchange.upper(),
        "action": "DEGRADE_MODE",
        "actionId": action.action_id,
        "reason": request.reason,
        "timestamp": int(time.time() * 1000)
    }


@router.post("/{exchange}/quarantine")
async def quarantine_exchange(
    exchange: str,
    request: ActionRequest
):
    """
    Quarantine exchange - exclude from all trading.
    
    Quarantine means:
    - No orders allowed
    - No position updates
    - Exchange excluded from trading
    """
    action = connection_safety_service.quarantine_exchange(exchange, request.reason)
    return {
        "exchange": exchange.upper(),
        "action": "QUARANTINE",
        "actionId": action.action_id,
        "reason": request.reason,
        "timestamp": int(time.time() * 1000)
    }


@router.post("/{exchange}/restore")
async def restore_exchange(
    exchange: str,
    request: ActionRequest
):
    """
    Restore exchange from degraded/quarantine state.
    
    Returns exchange to normal operation.
    """
    action = connection_safety_service.restore_exchange(exchange, request.reason)
    return {
        "exchange": exchange.upper(),
        "action": "RESTORE",
        "actionId": action.action_id,
        "reason": request.reason,
        "timestamp": int(time.time() * 1000)
    }


@router.post("/{exchange}/freeze")
async def freeze_orders(
    exchange: str,
    request: ActionRequest
):
    """
    Freeze all new orders on exchange.
    """
    action = connection_safety_service.freeze_orders(exchange, request.reason)
    return {
        "exchange": exchange.upper(),
        "action": "FREEZE_ORDERS",
        "actionId": action.action_id,
        "reason": request.reason,
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Checks
# ===========================================

@router.get("/{exchange}/tradeable")
async def check_tradeable(exchange: str):
    """
    Check if exchange is available for trading.
    """
    health = connection_safety_service.get_exchange_health(exchange)
    
    if not health:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
    
    tradeable = connection_safety_service.is_exchange_tradeable(exchange)
    degraded = connection_safety_service.is_exchange_degraded(exchange)
    can_open = connection_safety_service.can_open_positions(exchange)
    
    return {
        "exchange": exchange.upper(),
        "tradeable": tradeable,
        "degraded": degraded,
        "canOpenPositions": can_open,
        "timestamp": int(time.time() * 1000)
    }
