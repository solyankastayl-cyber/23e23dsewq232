"""
Order Routes
============

PHASE 4.1 - API endpoints for Order State Engine.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .order_types import OrderType, OrderSide, TimeInForce, OrderState
from .order_state_machine import order_state_machine
from .order_tracker import order_tracker
from .order_events import order_event_emitter
from .order_repository import order_repository


router = APIRouter(prefix="/api/orders", tags=["phase4.1-order-state"])


# ===========================================
# Request Models
# ===========================================

class CreateOrderRequest(BaseModel):
    """Request to create an order"""
    symbol: str = Field("BTCUSDT", description="Trading symbol")
    side: str = Field("BUY", description="BUY or SELL")
    order_type: str = Field("MARKET", description="MARKET, LIMIT, etc")
    quantity: float = Field(0.1, description="Order quantity")
    price: float = Field(0.0, description="Limit price")
    stop_price: float = Field(0.0, description="Stop trigger price")
    time_in_force: str = Field("GTC", description="GTC, IOC, FOK")
    strategy_id: str = Field("", description="Strategy ID")
    position_id: str = Field("", description="Position ID")
    exchange: str = Field("BINANCE", description="Exchange name")
    expected_price: float = Field(0.0, description="Expected fill price")
    client_order_id: str = Field("", description="Client order ID")
    expires_at: int = Field(0, description="Expiration timestamp")
    tags: Optional[Dict[str, str]] = Field(None, description="Custom tags")


class SubmitOrderRequest(BaseModel):
    """Request to submit an order"""
    order_id: str = Field(..., description="Order ID")
    exchange_order_id: str = Field("", description="Exchange order ID")


class FillOrderRequest(BaseModel):
    """Request to record a fill"""
    order_id: str = Field(..., description="Order ID")
    filled_qty: float = Field(..., description="Filled quantity")
    fill_price: float = Field(..., description="Fill price")
    commission: float = Field(0.0, description="Commission")
    commission_asset: str = Field("USDT", description="Commission asset")
    exchange_fill_id: str = Field("", description="Exchange fill ID")


class CancelOrderRequest(BaseModel):
    """Request to cancel an order"""
    order_id: str = Field(..., description="Order ID")
    reason: str = Field("", description="Cancellation reason")


class RejectOrderRequest(BaseModel):
    """Request to reject an order"""
    order_id: str = Field(..., description="Order ID")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Order State module"""
    return {
        "module": "PHASE 4.1 Order State Engine",
        "status": "healthy",
        "version": "1.0.0",
        "engines": {
            "stateMachine": order_state_machine.get_health(),
            "tracker": order_tracker.get_health(),
            "events": order_event_emitter.get_health()
        },
        "repository": order_repository.get_stats(),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Order CRUD
# ===========================================

@router.post("/create")
async def create_order(request: CreateOrderRequest):
    """Create a new order"""
    
    try:
        side = OrderSide(request.side.upper())
        order_type = OrderType(request.order_type.upper())
        tif = TimeInForce(request.time_in_force.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
    
    order = order_tracker.create_order(
        symbol=request.symbol,
        side=side,
        order_type=order_type,
        quantity=request.quantity,
        price=request.price,
        stop_price=request.stop_price,
        time_in_force=tif,
        strategy_id=request.strategy_id,
        position_id=request.position_id,
        exchange=request.exchange,
        expected_price=request.expected_price,
        client_order_id=request.client_order_id,
        expires_at=request.expires_at,
        tags=request.tags
    )
    
    order_repository.save_order(order)
    
    return order.to_dict()


@router.post("/submit")
async def submit_order(request: SubmitOrderRequest):
    """Submit order to exchange"""
    
    success, error = order_tracker.submit_order(
        order_id=request.order_id,
        exchange_order_id=request.exchange_order_id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    order = order_tracker.get_order(request.order_id)
    return order.to_dict()


@router.post("/accept/{order_id}")
async def accept_order(order_id: str):
    """Mark order as accepted by exchange"""
    
    success, error = order_tracker.accept_order(order_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    order = order_tracker.get_order(order_id)
    return order.to_dict()


@router.post("/fill")
async def fill_order(request: FillOrderRequest):
    """Record a fill for order"""
    
    success, error = order_tracker.fill_order(
        order_id=request.order_id,
        filled_qty=request.filled_qty,
        fill_price=request.fill_price,
        commission=request.commission,
        commission_asset=request.commission_asset,
        exchange_fill_id=request.exchange_fill_id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    order = order_tracker.get_order(request.order_id)
    if not order:
        # Order moved to history
        history = order_tracker.get_history(1)
        if history and history[0].order_id == request.order_id:
            order = history[0]
    
    return order.to_dict() if order else {"success": True, "orderId": request.order_id}


@router.post("/cancel")
async def cancel_order(request: CancelOrderRequest):
    """Cancel an order"""
    
    success, error = order_tracker.cancel_order(
        order_id=request.order_id,
        reason=request.reason
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {"success": True, "orderId": request.order_id, "action": "cancelled"}


@router.post("/reject")
async def reject_order(request: RejectOrderRequest):
    """Mark order as rejected"""
    
    success, error = order_tracker.reject_order(
        order_id=request.order_id,
        error_code=request.error_code,
        error_message=request.error_message
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {"success": True, "orderId": request.order_id, "action": "rejected"}


# ===========================================
# Query Endpoints
# ===========================================

@router.get("/status/{order_id}")
async def get_order_status(order_id: str):
    """Get order status"""
    
    order = order_tracker.get_order(order_id)
    if not order:
        # Check history
        for o in order_tracker.get_history():
            if o.order_id == order_id:
                return o.to_dict()
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    
    return order.to_dict()


@router.get("/active")
async def get_active_orders():
    """Get all active orders"""
    
    orders = order_tracker.get_active_orders()
    return {
        "orders": [o.to_dict() for o in orders],
        "count": len(orders)
    }


@router.get("/history")
async def get_order_history(limit: int = Query(50, le=200)):
    """Get order history"""
    
    history = order_tracker.get_history(limit)
    return {
        "orders": [o.to_dict() for o in history],
        "count": len(history)
    }


@router.get("/by-symbol/{symbol}")
async def get_orders_by_symbol(symbol: str):
    """Get orders by symbol"""
    
    orders = order_tracker.get_orders_by_symbol(symbol)
    return {
        "symbol": symbol,
        "orders": [o.to_dict() for o in orders],
        "count": len(orders)
    }


@router.get("/by-strategy/{strategy_id}")
async def get_orders_by_strategy(strategy_id: str):
    """Get orders by strategy"""
    
    orders = order_tracker.get_orders_by_strategy(strategy_id)
    return {
        "strategyId": strategy_id,
        "orders": [o.to_dict() for o in orders],
        "count": len(orders)
    }


# ===========================================
# Events Endpoints
# ===========================================

@router.get("/events")
async def get_events(limit: int = Query(50, le=200)):
    """Get recent execution events"""
    
    events = order_event_emitter.get_events(limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/{order_id}")
async def get_events_for_order(order_id: str):
    """Get events for specific order"""
    
    events = order_event_emitter.get_events_for_order(order_id)
    return {
        "orderId": order_id,
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/fills")
async def get_fill_events(limit: int = Query(50, le=200)):
    """Get fill-related events"""
    
    events = order_event_emitter.get_fill_events(limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/errors")
async def get_error_events(limit: int = Query(50, le=200)):
    """Get error events"""
    
    events = order_event_emitter.get_error_events(limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


# ===========================================
# State Machine Endpoints
# ===========================================

@router.get("/state-machine/transitions")
async def get_transitions():
    """Get all valid state transitions"""
    
    transitions = order_state_machine.get_all_transitions()
    return {
        "transitions": [t.to_dict() for t in transitions],
        "count": len(transitions)
    }


@router.get("/state-machine/valid-transitions/{state}")
async def get_valid_transitions(state: str):
    """Get valid transitions from state"""
    
    try:
        order_state = OrderState(state.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
    
    valid = order_state_machine.get_valid_transitions(order_state)
    return {
        "fromState": state,
        "validTransitions": [s.value for s in valid],
        "isTerminal": order_state_machine.is_terminal(order_state)
    }


# ===========================================
# Summary
# ===========================================

@router.get("/summary")
async def get_summary():
    """Get order summary"""
    
    summary = order_tracker.get_summary()
    return summary.to_dict()


# ===========================================
# Demo & Testing
# ===========================================

@router.post("/demo")
async def run_demo():
    """
    Run demo to test order lifecycle.
    Creates orders with various states including partial fills.
    """
    
    results = []
    
    # Demo 1: Full order lifecycle (Market order - immediate fill)
    order1 = order_tracker.create_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.5,
        expected_price=42000.0,
        strategy_id="TREND_CONFIRMATION",
        position_id=f"pos_{uuid.uuid4().hex[:8]}"
    )
    
    order_tracker.submit_order(order1.order_id, f"exch_{uuid.uuid4().hex[:8]}")
    order_tracker.accept_order(order1.order_id)
    order_tracker.fill_order(
        order1.order_id,
        filled_qty=0.5,
        fill_price=42010.0,
        commission=0.005
    )
    
    results.append({
        "demo": "Full lifecycle (Market)",
        "orderId": order1.order_id,
        "finalState": "FILLED",
        "slippage": "0.024%"
    })
    
    # Demo 2: Partial fills (Limit order)
    order2 = order_tracker.create_order(
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10.0,
        price=2500.0,
        expected_price=2500.0,
        strategy_id="MEAN_REVERSION"
    )
    
    order_tracker.submit_order(order2.order_id, f"exch_{uuid.uuid4().hex[:8]}")
    order_tracker.accept_order(order2.order_id)
    
    # Partial fill 1
    order_tracker.fill_order(order2.order_id, filled_qty=3.0, fill_price=2498.0, commission=0.003)
    # Partial fill 2
    order_tracker.fill_order(order2.order_id, filled_qty=4.0, fill_price=2499.0, commission=0.004)
    # Final fill
    order_tracker.fill_order(order2.order_id, filled_qty=3.0, fill_price=2500.0, commission=0.003)
    
    results.append({
        "demo": "Partial fills (Limit)",
        "orderId": order2.order_id,
        "fillCount": 3,
        "avgPrice": order_tracker.get_order(order2.order_id) is None,  # Moved to history
        "finalState": "FILLED"
    })
    
    # Demo 3: Cancelled order
    order3 = order_tracker.create_order(
        symbol="SOLUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=100.0,
        price=95.0,
        strategy_id="BREAKOUT"
    )
    
    order_tracker.submit_order(order3.order_id, f"exch_{uuid.uuid4().hex[:8]}")
    order_tracker.accept_order(order3.order_id)
    order_tracker.cancel_order(order3.order_id, "User requested cancellation")
    
    results.append({
        "demo": "Cancelled order",
        "orderId": order3.order_id,
        "finalState": "CANCELLED"
    })
    
    # Demo 4: Rejected order
    order4 = order_tracker.create_order(
        symbol="DOGEUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100000.0,
        strategy_id="MOMENTUM"
    )
    
    order_tracker.submit_order(order4.order_id, "")
    order_tracker.reject_order(order4.order_id, "INSUFFICIENT_FUNDS", "Not enough balance")
    
    results.append({
        "demo": "Rejected order",
        "orderId": order4.order_id,
        "finalState": "REJECTED",
        "errorCode": "INSUFFICIENT_FUNDS"
    })
    
    # Demo 5: Active order (partial fill, still open)
    order5 = order_tracker.create_order(
        symbol="AVAXUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=50.0,
        price=35.0,
        strategy_id="SWING"
    )
    
    order_tracker.submit_order(order5.order_id, f"exch_{uuid.uuid4().hex[:8]}")
    order_tracker.accept_order(order5.order_id)
    order_tracker.fill_order(order5.order_id, filled_qty=20.0, fill_price=34.98, commission=0.002)
    
    results.append({
        "demo": "Active order (partial fill)",
        "orderId": order5.order_id,
        "currentState": "PARTIAL_FILL",
        "filledQty": 20.0,
        "remainingQty": 30.0
    })
    
    return {
        "demo": "complete",
        "results": results,
        "summary": order_tracker.get_summary().to_dict(),
        "eventCount": len(order_event_emitter.get_events())
    }


@router.delete("/clear")
async def clear_all():
    """Clear all orders and events"""
    
    order_tracker.clear()
    order_event_emitter.clear_events()
    order_repository.clear()
    
    return {"success": True, "action": "cleared", "timestamp": int(time.time() * 1000)}


@router.get("/stats")
async def get_stats():
    """Get module statistics"""
    
    return {
        "tracker": order_tracker.get_health(),
        "events": order_event_emitter.get_health(),
        "repository": order_repository.get_stats()
    }
