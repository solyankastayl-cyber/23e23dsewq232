"""
Execution Rate Guard (SEC1)
===========================

Protects against:
- Runaway execution
- Infinite strategy loops
- Rate bombing
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from collections import defaultdict

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyGuardType,
    RateGuardConfig,
    OrderValidationRequest
)


class ExecutionRateGuard:
    """
    Execution Rate Limiting Guard.
    
    Tracks and limits:
    - Total orders per minute
    - Orders per symbol per minute
    - Orders per strategy per minute
    """
    
    def __init__(self, config: Optional[RateGuardConfig] = None):
        self.config = config or RateGuardConfig()
        
        # Sliding window counters
        self._global_orders: list = []
        self._symbol_orders: Dict[str, list] = defaultdict(list)
        self._strategy_orders: Dict[str, list] = defaultdict(list)
        
        self._lock = threading.Lock()
    
    def validate(self, order: OrderValidationRequest) -> SafetyDecisionResult:
        """Validate order against rate limits"""
        if not self.config.enabled:
            return SafetyDecisionResult(
                decision=SafetyDecision.ALLOW,
                order_id=order.order_id,
                reason="Rate guard disabled"
            )
        
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        
        with self._lock:
            # Clean old entries
            self._cleanup_old_entries(window_start)
            
            # Check 1: Global rate limit
            global_count = len(self._global_orders)
            if global_count >= self.config.max_orders_per_minute:
                return SafetyDecisionResult(
                    decision=SafetyDecision.BLOCK,
                    guard=SafetyGuardType.RATE,
                    order_id=order.order_id,
                    reason=f"Global rate limit exceeded ({global_count} >= {self.config.max_orders_per_minute} per minute)",
                    details={
                        "currentCount": global_count,
                        "limit": self.config.max_orders_per_minute,
                        "limitType": "global"
                    }
                )
            
            # Check 2: Symbol rate limit
            symbol_count = len(self._symbol_orders.get(order.symbol, []))
            if symbol_count >= self.config.max_orders_per_symbol_per_minute:
                return SafetyDecisionResult(
                    decision=SafetyDecision.BLOCK,
                    guard=SafetyGuardType.RATE,
                    order_id=order.order_id,
                    reason=f"Symbol rate limit exceeded for {order.symbol} ({symbol_count} >= {self.config.max_orders_per_symbol_per_minute})",
                    details={
                        "symbol": order.symbol,
                        "currentCount": symbol_count,
                        "limit": self.config.max_orders_per_symbol_per_minute,
                        "limitType": "symbol"
                    }
                )
            
            # Check 3: Strategy rate limit
            if order.strategy_id:
                strategy_count = len(self._strategy_orders.get(order.strategy_id, []))
                if strategy_count >= self.config.max_orders_per_strategy_per_minute:
                    return SafetyDecisionResult(
                        decision=SafetyDecision.BLOCK,
                        guard=SafetyGuardType.RATE,
                        order_id=order.order_id,
                        reason=f"Strategy rate limit exceeded for {order.strategy_id} ({strategy_count} >= {self.config.max_orders_per_strategy_per_minute})",
                        details={
                            "strategyId": order.strategy_id,
                            "currentCount": strategy_count,
                            "limit": self.config.max_orders_per_strategy_per_minute,
                            "limitType": "strategy"
                        }
                    )
            
            # Record this order
            self._record_order(order, now)
        
        return SafetyDecisionResult(
            decision=SafetyDecision.ALLOW,
            order_id=order.order_id,
            reason="Rate limits OK"
        )
    
    def _cleanup_old_entries(self, cutoff: datetime):
        """Remove entries older than cutoff"""
        self._global_orders = [t for t in self._global_orders if t > cutoff]
        
        for symbol in list(self._symbol_orders.keys()):
            self._symbol_orders[symbol] = [t for t in self._symbol_orders[symbol] if t > cutoff]
            if not self._symbol_orders[symbol]:
                del self._symbol_orders[symbol]
        
        for strategy in list(self._strategy_orders.keys()):
            self._strategy_orders[strategy] = [t for t in self._strategy_orders[strategy] if t > cutoff]
            if not self._strategy_orders[strategy]:
                del self._strategy_orders[strategy]
    
    def _record_order(self, order: OrderValidationRequest, timestamp: datetime):
        """Record order for rate tracking"""
        self._global_orders.append(timestamp)
        self._symbol_orders[order.symbol].append(timestamp)
        if order.strategy_id:
            self._strategy_orders[order.strategy_id].append(timestamp)
    
    def get_current_rates(self) -> Dict:
        """Get current rate usage"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        
        with self._lock:
            self._cleanup_old_entries(window_start)
            
            return {
                "global": {
                    "current": len(self._global_orders),
                    "limit": self.config.max_orders_per_minute,
                    "available": max(0, self.config.max_orders_per_minute - len(self._global_orders))
                },
                "bySymbol": {
                    symbol: {
                        "current": len(orders),
                        "limit": self.config.max_orders_per_symbol_per_minute
                    }
                    for symbol, orders in self._symbol_orders.items()
                },
                "byStrategy": {
                    strategy: {
                        "current": len(orders),
                        "limit": self.config.max_orders_per_strategy_per_minute
                    }
                    for strategy, orders in self._strategy_orders.items()
                }
            }
    
    def reset(self):
        """Reset all rate counters"""
        with self._lock:
            self._global_orders.clear()
            self._symbol_orders.clear()
            self._strategy_orders.clear()
    
    def get_stats(self) -> Dict:
        """Get guard statistics"""
        rates = self.get_current_rates()
        return {
            "globalRate": rates["global"],
            "symbolsTracked": len(self._symbol_orders),
            "strategiesTracked": len(self._strategy_orders),
            "enabled": self.config.enabled
        }


# Global instance
execution_rate_guard = ExecutionRateGuard()
