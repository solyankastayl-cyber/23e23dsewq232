"""
Execution Routes for Trading Terminal
======================================

FastAPI routes for execution lifecycle management.

Endpoints:
- GET /api/terminal/execution/{symbol} - Execution status
- GET /api/terminal/orders - List orders
- GET /api/terminal/orders/open - Open orders only
- GET /api/terminal/orders/history - Order history
- GET /api/terminal/orders/{order_id} - Get specific order
- GET /api/terminal/intents - List intents
- GET /api/terminal/intents/{intent_id} - Get specific intent

Simulation endpoints (dev/testing):
- POST /api/terminal/intents/simulate-upsert - Create/update intent
- POST /api/terminal/orders/simulate-place - Place order
- POST /api/terminal/orders/{order_id}/simulate-fill - Fill order
- POST /api/terminal/orders/{order_id}/simulate-cancel - Cancel order
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from .execution_state_engine import get_execution_engine
from .execution_repository import get_execution_repository

router = APIRouter(prefix="/api/terminal", tags=["Execution & Orders"])


# ---- Pydantic Models ----

class SimulateUpsertRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "4H"
    decision: dict = {}
    execution: dict = {}
    validation: dict = {"is_valid": True}
    position: dict = {"has_position": False}


class SimulatePlaceRequest(BaseModel):
    intent_id: str
    side: str = "BUY"
    order_type: str = "LIMIT"


class SimulateFillRequest(BaseModel):
    fill_size: float
    fill_price: Optional[float] = None


class SimulateCancelRequest(BaseModel):
    reason: str = "manual_cancel"


# ---- Read Endpoints ----

@router.get("/execution/health")
async def execution_health():
    """Health check for execution module"""
    return {
        "ok": True,
        "module": "execution_state_engine",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/execution/{symbol}")
async def get_execution_status(
    symbol: str,
    timeframe: str = Query(default="4H", description="Timeframe: 1H, 4H, or 1D")
):
    """
    Get current execution status for symbol.
    
    Returns execution intent state, order status, and filled percentage.
    """
    engine = get_execution_engine()
    repo = get_execution_repository()
    
    summary = engine.build_status_summary(symbol.upper(), timeframe.upper())
    intent = repo.get_latest_intent(symbol.upper(), timeframe.upper())
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "execution_status": summary,
        "intent": intent.to_dict() if intent else None
    }


@router.get("/orders")
async def list_orders(
    symbol: Optional[str] = None,
    open_only: bool = Query(default=False, description="Show only open orders"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """List all orders"""
    repo = get_execution_repository()
    orders = repo.list_orders(
        symbol=symbol.upper() if symbol else None,
        open_only=open_only,
        limit=limit
    )
    return {
        "ok": True,
        "count": len(orders),
        "orders": [o.to_dict() for o in orders]
    }


@router.get("/orders/open")
async def list_open_orders():
    """List only open orders"""
    repo = get_execution_repository()
    orders = repo.list_orders(open_only=True)
    return {
        "ok": True,
        "count": len(orders),
        "orders": [o.to_dict() for o in orders]
    }


@router.get("/orders/history")
async def list_order_history(
    symbol: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500)
):
    """Get order history"""
    repo = get_execution_repository()
    orders = repo.list_orders(
        symbol=symbol.upper() if symbol else None,
        open_only=False,
        limit=limit
    )
    return {
        "ok": True,
        "count": len(orders),
        "orders": [o.to_dict() for o in orders]
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order by ID"""
    repo = get_execution_repository()
    order = repo.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "ok": True,
        "order": order.to_dict()
    }


@router.get("/intents")
async def list_intents(
    symbol: Optional[str] = None
):
    """List all execution intents"""
    repo = get_execution_repository()
    intents = repo.list_intents(symbol=symbol.upper() if symbol else None)
    return {
        "ok": True,
        "count": len(intents),
        "intents": [i.to_dict() for i in intents]
    }


@router.get("/intents/{intent_id}")
async def get_intent(intent_id: str):
    """Get specific intent by ID"""
    repo = get_execution_repository()
    intent = repo.get_intent(intent_id)
    
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    return {
        "ok": True,
        "intent": intent.to_dict()
    }


# ---- Simulation Endpoints (Dev/Testing) ----

@router.post("/intents/simulate-upsert")
async def simulate_upsert_intent(request: SimulateUpsertRequest):
    """
    Create or update execution intent from decision/execution data.
    For development and testing.
    """
    engine = get_execution_engine()
    
    intent = engine.build_or_update_intent(
        symbol=request.symbol.upper(),
        timeframe=request.timeframe.upper(),
        decision=request.decision,
        execution=request.execution,
        validation=request.validation,
        position=request.position,
    )
    
    return {
        "ok": True,
        "intent": intent.to_dict()
    }


@router.post("/orders/simulate-place")
async def simulate_place_order(request: SimulatePlaceRequest):
    """
    Simulate placing an order from intent.
    For development and testing.
    """
    engine = get_execution_engine()
    
    try:
        order = engine.create_simulated_order(
            intent_id=request.intent_id,
            side=request.side,
            order_type=request.order_type
        )
        return {
            "ok": True,
            "order": order.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/simulate-fill")
async def simulate_fill_order(order_id: str, request: SimulateFillRequest):
    """
    Simulate filling an order (partial or full).
    For development and testing.
    """
    engine = get_execution_engine()
    
    try:
        order = engine.simulate_fill(
            order_id=order_id,
            fill_size=request.fill_size,
            fill_price=request.fill_price
        )
        return {
            "ok": True,
            "order": order.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/simulate-cancel")
async def simulate_cancel_order(order_id: str, request: SimulateCancelRequest):
    """
    Simulate cancelling an order.
    For development and testing.
    """
    engine = get_execution_engine()
    
    try:
        order = engine.simulate_cancel(
            order_id=order_id,
            reason=request.reason
        )
        return {
            "ok": True,
            "order": order.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
