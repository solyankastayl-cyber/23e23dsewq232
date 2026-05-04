"""
Duplicate Order Guard (SEC1)
============================

Protects against:
- Double signals
- Repeated API calls  
- Retry execution
- Race conditions
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import deque

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyGuardType,
    DuplicateGuardConfig,
    OrderValidationRequest
)


class DuplicateGuard:
    """
    Duplicate Order Detection Guard.
    
    Maintains sliding window of recent orders and blocks
    potential duplicates based on:
    - Same symbol
    - Same side
    - Similar price (within tolerance)
    - Similar size (within tolerance)
    - Within time window
    """
    
    def __init__(self, config: Optional[DuplicateGuardConfig] = None):
        self.config = config or DuplicateGuardConfig()
        self._recent_orders: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def validate(self, order: OrderValidationRequest) -> SafetyDecisionResult:
        """Validate order for duplicates"""
        if not self.config.enabled:
            return SafetyDecisionResult(
                decision=SafetyDecision.ALLOW,
                order_id=order.order_id,
                reason="Duplicate guard disabled"
            )
        
        with self._lock:
            # Check for duplicate
            duplicate = self._find_duplicate(order)
            
            if duplicate:
                return SafetyDecisionResult(
                    decision=SafetyDecision.BLOCK,
                    guard=SafetyGuardType.DUPLICATE,
                    order_id=order.order_id,
                    reason=f"Duplicate order detected (matches {duplicate['order_id']})",
                    details={
                        "originalOrderId": duplicate["order_id"],
                        "timeDiffSeconds": duplicate["time_diff"],
                        "priceDiff": duplicate["price_diff"],
                        "sizeDiff": duplicate["size_diff"]
                    }
                )
            
            # Add to recent orders
            self._add_order(order)
            
            return SafetyDecisionResult(
                decision=SafetyDecision.ALLOW,
                order_id=order.order_id,
                reason="No duplicate detected"
            )
    
    def _find_duplicate(self, order: OrderValidationRequest) -> Optional[Dict]:
        """Find potential duplicate in recent orders"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.config.window_seconds)
        
        for recent in self._recent_orders:
            # Skip if outside window
            if recent["timestamp"] < window_start:
                continue
            
            # Check symbol and side
            if recent["symbol"] != order.symbol or recent["side"] != order.side:
                continue
            
            # Check price tolerance (for limit orders)
            price_diff = 0.0
            if order.price and recent.get("price"):
                price_diff = abs(order.price - recent["price"]) / order.price
                if price_diff > self.config.check_price_tolerance_pct / 100:
                    continue
            
            # Check size tolerance
            size_diff = abs(order.size - recent["size"]) / max(order.size, 0.0001)
            if size_diff > self.config.check_size_tolerance_pct / 100:
                continue
            
            # Found duplicate
            time_diff = (now - recent["timestamp"]).total_seconds()
            return {
                "order_id": recent["order_id"],
                "time_diff": time_diff,
                "price_diff": price_diff,
                "size_diff": size_diff
            }
        
        return None
    
    def _add_order(self, order: OrderValidationRequest):
        """Add order to recent orders"""
        self._recent_orders.append({
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "size": order.size,
            "price": order.price,
            "timestamp": order.timestamp or datetime.now(timezone.utc)
        })
    
    def clear_history(self):
        """Clear order history"""
        with self._lock:
            self._recent_orders.clear()
    
    def get_stats(self) -> Dict:
        """Get guard statistics"""
        with self._lock:
            return {
                "recentOrdersCount": len(self._recent_orders),
                "windowSeconds": self.config.window_seconds,
                "enabled": self.config.enabled
            }


# Global instance
duplicate_guard = DuplicateGuard()
