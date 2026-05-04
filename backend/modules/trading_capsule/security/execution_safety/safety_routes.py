"""
Safety Routes (SEC1)
====================

API endpoints for Execution Safety Layer.

Endpoints:
- GET  /api/security/execution/health     - Service health
- GET  /api/security/execution/config     - Get config
- POST /api/security/execution/config     - Update config
- POST /api/security/execution/validate   - Validate order
- GET  /api/security/execution/events     - Get events
- GET  /api/security/execution/stats      - Get statistics
- GET  /api/security/execution/rates      - Get rate limits status

Quarantine:
- GET  /api/security/execution/quarantines            - List quarantines
- POST /api/security/execution/quarantine/exchange    - Quarantine exchange
- POST /api/security/execution/quarantine/symbol      - Quarantine symbol
- POST /api/security/execution/quarantine/lift        - Lift quarantine

Stale Orders:
- GET  /api/security/execution/stale          - Get stale orders
- POST /api/security/execution/stale/check    - Check for stale orders
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel

from .safety_service import safety_service
from .safety_types import OrderValidationRequest


router = APIRouter(prefix="/api/security/execution", tags=["SEC1 - Execution Safety"])


# ===========================================
# Request Models
# ===========================================

class OrderValidationInput(BaseModel):
    symbol: str
    side: str
    order_type: str = "MARKET"
    size: float
    price: Optional[float] = None
    strategy_id: Optional[str] = None
    exchange: str = "binance"


class ConfigUpdateInput(BaseModel):
    duplicate: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None
    rate: Optional[Dict[str, Any]] = None
    stale: Optional[Dict[str, Any]] = None
    exchangeSync: Optional[Dict[str, Any]] = None


class QuarantineExchangeInput(BaseModel):
    exchange: str
    reason: str
    duration_minutes: Optional[int] = None


class QuarantineSymbolInput(BaseModel):
    exchange: str
    symbol: str
    reason: str
    duration_minutes: Optional[int] = None


class LiftQuarantineInput(BaseModel):
    key: str


# ===========================================
# Health & Status
# ===========================================

@router.get("/health")
async def get_health():
    """Get SEC1 module health."""
    return safety_service.get_health()


@router.get("/stats")
async def get_stats():
    """Get safety statistics."""
    return safety_service.get_stats()


@router.get("/rates")
async def get_rate_status():
    """Get current rate limit status."""
    return safety_service.get_rate_status()


# ===========================================
# Configuration
# ===========================================

@router.get("/config")
async def get_config():
    """Get current safety configuration."""
    return safety_service.get_config()


@router.post("/config")
async def update_config(config: ConfigUpdateInput):
    """Update safety configuration."""
    return safety_service.update_config(config.dict(exclude_none=True))


# ===========================================
# Order Validation
# ===========================================

@router.post("/validate")
async def validate_order(order: OrderValidationInput):
    """
    Validate order through all safety guards.
    
    Checks:
    - Duplicate detection
    - Rate limiting
    - Position limits
    - Quarantine status
    
    Returns decision: ALLOW, BLOCK, WARN, or QUARANTINE
    """
    req = OrderValidationRequest(
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        size=order.size,
        price=order.price,
        strategy_id=order.strategy_id,
        exchange=order.exchange
    )
    
    result = safety_service.validate_order(req)
    return result.to_dict()


# ===========================================
# Events
# ===========================================

@router.get("/events")
async def get_events(
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent safety events."""
    return {
        "events": safety_service.get_events(limit=limit),
        "count": min(limit, len(safety_service._events))
    }


# ===========================================
# Quarantine Management
# ===========================================

@router.get("/quarantines")
async def get_quarantines(
    active_only: bool = Query(True, description="Only return active quarantines")
):
    """Get all quarantines."""
    return {
        "quarantines": safety_service.get_quarantines(active_only=active_only)
    }


@router.post("/quarantine/exchange")
async def quarantine_exchange(input: QuarantineExchangeInput):
    """Quarantine an exchange."""
    safety_service.quarantine_exchange(
        exchange=input.exchange,
        reason=input.reason,
        duration_minutes=input.duration_minutes
    )
    return {
        "success": True,
        "message": f"Exchange {input.exchange} quarantined",
        "reason": input.reason
    }


@router.post("/quarantine/symbol")
async def quarantine_symbol(input: QuarantineSymbolInput):
    """Quarantine a symbol."""
    safety_service.quarantine_symbol(
        exchange=input.exchange,
        symbol=input.symbol,
        reason=input.reason,
        duration_minutes=input.duration_minutes
    )
    return {
        "success": True,
        "message": f"Symbol {input.symbol} on {input.exchange} quarantined",
        "reason": input.reason
    }


@router.post("/quarantine/lift")
async def lift_quarantine(input: LiftQuarantineInput):
    """Lift a quarantine by key."""
    success = safety_service.lift_quarantine(input.key)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Quarantine not found: {input.key}")
    
    return {
        "success": True,
        "message": f"Quarantine lifted: {input.key}"
    }


# ===========================================
# Stale Orders
# ===========================================

@router.get("/stale")
async def get_stale_orders():
    """Get current stale orders."""
    return {
        "staleOrders": safety_service.get_stale_orders()
    }


@router.post("/stale/check")
async def check_stale_orders():
    """Check for new stale orders."""
    events = safety_service.check_stale_orders()
    return {
        "newStaleOrders": events,
        "count": len(events)
    }


@router.post("/order/status")
async def update_order_status(order_id: str, status: str):
    """Update order status for tracking."""
    safety_service.update_order_status(order_id, status)
    return {"success": True}


# ===========================================
# Exchange Sync
# ===========================================

class SyncValidationInput(BaseModel):
    exchange_positions: Dict[str, Dict] = {}
    exchange_orders: Dict[str, Dict] = {}
    exchange_balances: Dict[str, float] = {}


@router.post("/sync/validate")
async def validate_sync(input: SyncValidationInput):
    """Validate exchange sync state."""
    result = safety_service.validate_exchange_sync(
        exchange_positions=input.exchange_positions,
        exchange_orders=input.exchange_orders,
        exchange_balances=input.exchange_balances
    )
    return result.to_dict()
