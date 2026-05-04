"""
Order Event Emitter
===================

PHASE 4.1 - Emits and tracks execution events.
"""

import time
import uuid
from typing import Dict, List, Optional, Any, Callable

from .order_types import (
    ExecutionEvent,
    ExecutionEventType,
    Order,
    OrderState,
    OrderFill
)


class OrderEventEmitter:
    """
    Emits execution events:
    - Order lifecycle events
    - Fill events
    - Error events
    - Event subscribers
    """
    
    def __init__(self):
        # Event storage
        self._events: List[ExecutionEvent] = []
        self._events_by_order: Dict[str, List[ExecutionEvent]] = {}
        
        # Subscribers
        self._subscribers: Dict[ExecutionEventType, List[Callable]] = {}
        
        # Event limits
        self._max_events = 10000
        self._max_events_per_order = 100
        
        print("[OrderEventEmitter] Initialized (PHASE 4.1)")
    
    def emit(
        self,
        event_type: ExecutionEventType,
        order: Order,
        from_state: OrderState,
        to_state: OrderState,
        fill: Optional[OrderFill] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ExecutionEvent:
        """Emit an execution event"""
        
        event = ExecutionEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            order_id=order.order_id,
            client_order_id=order.client_order_id,
            from_state=from_state,
            to_state=to_state,
            details=details or {},
            fill=fill,
            timestamp=int(time.time() * 1000)
        )
        
        # Store event
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        
        # Store by order
        if order.order_id not in self._events_by_order:
            self._events_by_order[order.order_id] = []
        self._events_by_order[order.order_id].append(event)
        if len(self._events_by_order[order.order_id]) > self._max_events_per_order:
            self._events_by_order[order.order_id] = self._events_by_order[order.order_id][-self._max_events_per_order:]
        
        # Notify subscribers
        self._notify_subscribers(event)
        
        return event
    
    def emit_created(self, order: Order, details: Optional[Dict] = None) -> ExecutionEvent:
        """Emit order created event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_CREATED,
            order=order,
            from_state=OrderState.NEW,
            to_state=OrderState.NEW,
            details=details or {
                "symbol": order.symbol,
                "side": order.side.value,
                "type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.price
            }
        )
    
    def emit_submitted(self, order: Order, exchange_order_id: str = "") -> ExecutionEvent:
        """Emit order submitted event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_SUBMITTED,
            order=order,
            from_state=OrderState.NEW,
            to_state=OrderState.SUBMITTED,
            details={
                "exchangeOrderId": exchange_order_id,
                "exchange": order.exchange
            }
        )
    
    def emit_accepted(self, order: Order) -> ExecutionEvent:
        """Emit order accepted event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_ACCEPTED,
            order=order,
            from_state=OrderState.SUBMITTED,
            to_state=OrderState.ACCEPTED,
            details={
                "acceptedAt": order.accepted_at
            }
        )
    
    def emit_partial_fill(self, order: Order, fill: OrderFill) -> ExecutionEvent:
        """Emit partial fill event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_PARTIAL_FILL,
            order=order,
            from_state=order.previous_state,
            to_state=OrderState.PARTIAL_FILL,
            fill=fill,
            details={
                "filledQty": fill.filled_qty,
                "fillPrice": fill.fill_price,
                "totalFilled": order.filled_quantity,
                "remaining": order.remaining_quantity,
                "fillPct": round(order.filled_quantity / order.quantity * 100, 1)
            }
        )
    
    def emit_filled(self, order: Order, fill: Optional[OrderFill] = None) -> ExecutionEvent:
        """Emit order filled event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_FILLED,
            order=order,
            from_state=order.previous_state,
            to_state=OrderState.FILLED,
            fill=fill,
            details={
                "totalFilled": order.filled_quantity,
                "avgPrice": order.avg_fill_price,
                "totalCommission": order.total_commission,
                "slippagePct": order.slippage_pct,
                "fillCount": order.fill_count,
                "fillTimeMs": order.filled_at - order.submitted_at if order.submitted_at else 0
            }
        )
    
    def emit_cancelled(self, order: Order, reason: str = "") -> ExecutionEvent:
        """Emit order cancelled event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_CANCELLED,
            order=order,
            from_state=order.previous_state,
            to_state=OrderState.CANCELLED,
            details={
                "reason": reason,
                "filledQty": order.filled_quantity,
                "remainingQty": order.remaining_quantity
            }
        )
    
    def emit_rejected(self, order: Order, error_code: str, error_message: str) -> ExecutionEvent:
        """Emit order rejected event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_REJECTED,
            order=order,
            from_state=order.previous_state,
            to_state=OrderState.REJECTED,
            details={
                "errorCode": error_code,
                "errorMessage": error_message
            }
        )
    
    def emit_failed(self, order: Order, error_code: str, error_message: str) -> ExecutionEvent:
        """Emit order failed event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_FAILED,
            order=order,
            from_state=order.previous_state,
            to_state=OrderState.FAILED,
            details={
                "errorCode": error_code,
                "errorMessage": error_message,
                "retryCount": order.retry_count
            }
        )
    
    def emit_expired(self, order: Order) -> ExecutionEvent:
        """Emit order expired event"""
        return self.emit(
            event_type=ExecutionEventType.ORDER_EXPIRED,
            order=order,
            from_state=order.previous_state,
            to_state=OrderState.EXPIRED,
            details={
                "expiresAt": order.expires_at,
                "filledQty": order.filled_quantity
            }
        )
    
    def subscribe(self, event_type: ExecutionEventType, callback: Callable):
        """Subscribe to event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: ExecutionEventType, callback: Callable):
        """Unsubscribe from event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                c for c in self._subscribers[event_type] if c != callback
            ]
    
    def _notify_subscribers(self, event: ExecutionEvent):
        """Notify all subscribers of event"""
        callbacks = self._subscribers.get(event.event_type, [])
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"[OrderEventEmitter] Subscriber error: {e}")
    
    def get_events(self, limit: int = 50) -> List[ExecutionEvent]:
        """Get recent events"""
        return self._events[-limit:]
    
    def get_events_for_order(self, order_id: str) -> List[ExecutionEvent]:
        """Get events for specific order"""
        return self._events_by_order.get(order_id, [])
    
    def get_events_by_type(self, event_type: ExecutionEventType, limit: int = 50) -> List[ExecutionEvent]:
        """Get events by type"""
        filtered = [e for e in self._events if e.event_type == event_type]
        return filtered[-limit:]
    
    def get_fill_events(self, limit: int = 50) -> List[ExecutionEvent]:
        """Get fill-related events"""
        fill_types = {ExecutionEventType.ORDER_PARTIAL_FILL, ExecutionEventType.ORDER_FILLED}
        filtered = [e for e in self._events if e.event_type in fill_types]
        return filtered[-limit:]
    
    def get_error_events(self, limit: int = 50) -> List[ExecutionEvent]:
        """Get error events"""
        error_types = {ExecutionEventType.ORDER_REJECTED, ExecutionEventType.ORDER_FAILED}
        filtered = [e for e in self._events if e.event_type in error_types]
        return filtered[-limit:]
    
    def clear_events(self, order_id: Optional[str] = None):
        """Clear events"""
        if order_id:
            self._events_by_order.pop(order_id, None)
            self._events = [e for e in self._events if e.order_id != order_id]
        else:
            self._events.clear()
            self._events_by_order.clear()
    
    def get_event_summary(self) -> Dict[str, int]:
        """Get summary of events by type"""
        summary = {et.value: 0 for et in ExecutionEventType}
        for event in self._events:
            summary[event.event_type.value] += 1
        return summary
    
    def get_health(self) -> Dict:
        """Get emitter health"""
        return {
            "engine": "OrderEventEmitter",
            "version": "1.0.0",
            "phase": "4.1",
            "status": "active",
            "totalEvents": len(self._events),
            "ordersTracked": len(self._events_by_order),
            "subscribers": {et.value: len(cbs) for et, cbs in self._subscribers.items()},
            "eventSummary": self.get_event_summary(),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
order_event_emitter = OrderEventEmitter()
