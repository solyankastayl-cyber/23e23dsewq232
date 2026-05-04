"""
Order Repository
================

PHASE 4.1 - Data persistence for orders and events.
"""

import time
from typing import Dict, List, Optional, Any

from .order_types import Order, ExecutionEvent, OrderState, OrderSummary


class OrderRepository:
    """
    Repository for order data:
    - Order storage
    - Event storage
    - Query interfaces
    """
    
    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._events: List[ExecutionEvent] = []
        self._snapshots: List[Dict[str, Any]] = []
        
        print("[OrderRepository] Initialized (PHASE 4.1)")
    
    # Order methods
    def save_order(self, order: Order):
        """Save order"""
        self._orders[order.order_id] = order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_orders(self, state: Optional[OrderState] = None, limit: int = 100) -> List[Order]:
        """Get orders, optionally filtered by state"""
        orders = list(self._orders.values())
        if state:
            orders = [o for o in orders if o.state == state]
        return orders[-limit:]
    
    def delete_order(self, order_id: str):
        """Delete order"""
        self._orders.pop(order_id, None)
    
    # Event methods
    def save_event(self, event: ExecutionEvent):
        """Save event"""
        self._events.append(event)
        if len(self._events) > 5000:
            self._events = self._events[-5000:]
    
    def get_events(self, order_id: Optional[str] = None, limit: int = 100) -> List[ExecutionEvent]:
        """Get events, optionally filtered by order"""
        events = self._events
        if order_id:
            events = [e for e in events if e.order_id == order_id]
        return events[-limit:]
    
    # Snapshot methods
    def save_snapshot(self, summary: OrderSummary):
        """Save summary snapshot"""
        self._snapshots.append({
            "summary": summary.to_dict(),
            "timestamp": int(time.time() * 1000)
        })
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
    
    def get_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get snapshots"""
        return self._snapshots[-limit:]
    
    # Clear
    def clear(self):
        """Clear all data"""
        self._orders.clear()
        self._events.clear()
        self._snapshots.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        return {
            "orders": len(self._orders),
            "events": len(self._events),
            "snapshots": len(self._snapshots),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
order_repository = OrderRepository()
