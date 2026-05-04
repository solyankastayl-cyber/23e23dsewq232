"""
Stale Order Guard (SEC1)
========================

Detects and handles:
- Stuck orders
- Unsynced orders
- Old pending orders
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyGuardType,
    SafetyEvent,
    SafetyEventType,
    StaleOrderConfig
)


class StaleOrderGuard:
    """
    Stale Order Detection Guard.
    
    Monitors pending orders and flags those that:
    - Are older than threshold
    - Haven't been filled/cancelled
    """
    
    def __init__(self, config: Optional[StaleOrderConfig] = None):
        self.config = config or StaleOrderConfig()
        self._pending_orders: Dict[str, Dict] = {}  # order_id -> order info
        self._stale_orders: Dict[str, Dict] = {}    # order_id -> stale info
        self._lock = threading.Lock()
    
    def track_order(self, order_id: str, symbol: str, side: str, exchange: str):
        """Track new pending order"""
        with self._lock:
            self._pending_orders[order_id] = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "exchange": exchange,
                "created_at": datetime.now(timezone.utc),
                "status": "PENDING"
            }
    
    def update_order(self, order_id: str, status: str):
        """Update order status"""
        with self._lock:
            if order_id in self._pending_orders:
                if status in ["FILLED", "CANCELLED", "REJECTED"]:
                    self._pending_orders.pop(order_id, None)
                    self._stale_orders.pop(order_id, None)
                else:
                    self._pending_orders[order_id]["status"] = status
    
    def check_stale_orders(self) -> List[SafetyEvent]:
        """Check for stale orders and return events"""
        if not self.config.enabled:
            return []
        
        events = []
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(minutes=self.config.stale_threshold_minutes)
        
        with self._lock:
            for order_id, order in list(self._pending_orders.items()):
                if order["created_at"] < stale_threshold:
                    if order_id not in self._stale_orders:
                        # New stale order detected
                        self._stale_orders[order_id] = {
                            **order,
                            "detected_at": now,
                            "age_minutes": (now - order["created_at"]).total_seconds() / 60
                        }
                        
                        events.append(SafetyEvent(
                            event_type=SafetyEventType.STALE_ORDER_DETECTED,
                            order_id=order_id,
                            symbol=order["symbol"],
                            exchange=order["exchange"],
                            guard=SafetyGuardType.STALE,
                            message=f"Stale order detected: {order_id} on {order['symbol']}",
                            details={
                                "ageMinutes": self._stale_orders[order_id]["age_minutes"],
                                "threshold": self.config.stale_threshold_minutes,
                                "side": order["side"],
                                "autoCancelEnabled": self.config.auto_cancel_stale
                            }
                        ))
        
        return events
    
    def get_stale_orders(self) -> List[Dict]:
        """Get list of current stale orders"""
        with self._lock:
            return list(self._stale_orders.values())
    
    def get_pending_orders(self) -> List[Dict]:
        """Get list of pending orders"""
        with self._lock:
            return list(self._pending_orders.values())
    
    def get_orders_to_cancel(self) -> List[str]:
        """Get order IDs that should be cancelled (if auto-cancel enabled)"""
        if not self.config.auto_cancel_stale:
            return []
        
        with self._lock:
            return list(self._stale_orders.keys())
    
    def clear_order(self, order_id: str):
        """Manually clear an order from tracking"""
        with self._lock:
            self._pending_orders.pop(order_id, None)
            self._stale_orders.pop(order_id, None)
    
    def get_stats(self) -> Dict:
        """Get guard statistics"""
        with self._lock:
            return {
                "pendingOrders": len(self._pending_orders),
                "staleOrders": len(self._stale_orders),
                "staleThresholdMinutes": self.config.stale_threshold_minutes,
                "autoCancelEnabled": self.config.auto_cancel_stale,
                "enabled": self.config.enabled
            }


# Global instance
stale_order_guard = StaleOrderGuard()
