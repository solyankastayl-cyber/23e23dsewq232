"""
Order Tracker
=============

PHASE 4.1 - Tracks and manages orders through their lifecycle.
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .order_types import (
    Order,
    OrderState,
    OrderType,
    OrderSide,
    TimeInForce,
    OrderFill,
    OrderSummary
)
from .order_state_machine import order_state_machine
from .order_events import order_event_emitter


class OrderTracker:
    """
    Order Tracker:
    - Creates and manages orders
    - Tracks order states
    - Handles fills and partial fills
    - Provides order queries
    """
    
    def __init__(self):
        # Active orders
        self._orders: Dict[str, Order] = {}
        
        # Indexes
        self._by_client_id: Dict[str, str] = {}
        self._by_symbol: Dict[str, List[str]] = {}
        self._by_strategy: Dict[str, List[str]] = {}
        self._by_position: Dict[str, List[str]] = {}
        
        # History (closed orders)
        self._history: List[Order] = []
        self._max_history = 1000
        
        print("[OrderTracker] Initialized (PHASE 4.1)")
    
    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float = 0.0,
        stop_price: float = 0.0,
        time_in_force: TimeInForce = TimeInForce.GTC,
        strategy_id: str = "",
        position_id: str = "",
        exchange: str = "BINANCE",
        expected_price: float = 0.0,
        client_order_id: str = "",
        expires_at: int = 0,
        tags: Optional[Dict[str, str]] = None
    ) -> Order:
        """Create a new order"""
        
        now = int(time.time() * 1000)
        
        order = Order(
            order_id=f"ord_{uuid.uuid4().hex[:12]}",
            client_order_id=client_order_id or f"cli_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            exchange=exchange,
            strategy_id=strategy_id,
            position_id=position_id,
            side=side,
            order_type=order_type,
            time_in_force=time_in_force,
            quantity=quantity,
            remaining_quantity=quantity,
            price=price,
            stop_price=stop_price,
            expected_price=expected_price or price,
            state=OrderState.NEW,
            previous_state=OrderState.NEW,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            tags=tags or {}
        )
        
        # Store order
        self._orders[order.order_id] = order
        self._index_order(order)
        
        # Emit created event
        order_event_emitter.emit_created(order)
        
        return order
    
    def submit_order(self, order_id: str, exchange_order_id: str = "") -> tuple[bool, str]:
        """Submit order to exchange"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        success, error = order_state_machine.transition(order, OrderState.SUBMITTED)
        
        if success:
            order.exchange_order_id = exchange_order_id
            order_event_emitter.emit_submitted(order, exchange_order_id)
        
        return success, error
    
    def accept_order(self, order_id: str) -> tuple[bool, str]:
        """Mark order as accepted by exchange"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        success, error = order_state_machine.transition(order, OrderState.ACCEPTED)
        
        if success:
            order_event_emitter.emit_accepted(order)
        
        return success, error
    
    def fill_order(
        self,
        order_id: str,
        filled_qty: float,
        fill_price: float,
        commission: float = 0.0,
        commission_asset: str = "USDT",
        exchange_fill_id: str = ""
    ) -> tuple[bool, str]:
        """Record a fill for order"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        # Create fill
        fill = OrderFill(
            fill_id=f"fill_{uuid.uuid4().hex[:8]}",
            order_id=order_id,
            filled_qty=filled_qty,
            fill_price=fill_price,
            commission=commission,
            commission_asset=commission_asset,
            filled_at=int(time.time() * 1000),
            exchange_fill_id=exchange_fill_id
        )
        
        # Determine target state
        remaining_after_fill = order.remaining_quantity - filled_qty
        target_state = OrderState.FILLED if remaining_after_fill <= 0.00000001 else OrderState.PARTIAL_FILL
        
        # Transition
        success, error = order_state_machine.transition(order, target_state, fill=fill)
        
        if success:
            if target_state == OrderState.FILLED:
                order_event_emitter.emit_filled(order, fill)
                self._move_to_history(order_id)
            else:
                order_event_emitter.emit_partial_fill(order, fill)
        
        return success, error
    
    def cancel_order(self, order_id: str, reason: str = "") -> tuple[bool, str]:
        """Cancel an order"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        success, error = order_state_machine.transition(order, OrderState.CANCELLED)
        
        if success:
            order_event_emitter.emit_cancelled(order, reason)
            self._move_to_history(order_id)
        
        return success, error
    
    def reject_order(self, order_id: str, error_code: str, error_message: str) -> tuple[bool, str]:
        """Mark order as rejected"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        success, error = order_state_machine.transition(
            order, OrderState.REJECTED,
            error_code=error_code,
            error_message=error_message
        )
        
        if success:
            order_event_emitter.emit_rejected(order, error_code, error_message)
            self._move_to_history(order_id)
        
        return success, error
    
    def fail_order(self, order_id: str, error_code: str, error_message: str) -> tuple[bool, str]:
        """Mark order as failed"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        order.retry_count += 1
        
        # If retries not exhausted, don't fail yet
        if order.retry_count < order.max_retries:
            return False, f"Retry {order.retry_count}/{order.max_retries}"
        
        success, error = order_state_machine.transition(
            order, OrderState.FAILED,
            error_code=error_code,
            error_message=error_message
        )
        
        if success:
            order_event_emitter.emit_failed(order, error_code, error_message)
            self._move_to_history(order_id)
        
        return success, error
    
    def expire_order(self, order_id: str) -> tuple[bool, str]:
        """Mark order as expired"""
        
        order = self._orders.get(order_id)
        if not order:
            return False, f"Order not found: {order_id}"
        
        success, error = order_state_machine.transition(order, OrderState.EXPIRED)
        
        if success:
            order_event_emitter.emit_expired(order)
            self._move_to_history(order_id)
        
        return success, error
    
    def _index_order(self, order: Order):
        """Add order to indexes"""
        
        self._by_client_id[order.client_order_id] = order.order_id
        
        if order.symbol not in self._by_symbol:
            self._by_symbol[order.symbol] = []
        self._by_symbol[order.symbol].append(order.order_id)
        
        if order.strategy_id:
            if order.strategy_id not in self._by_strategy:
                self._by_strategy[order.strategy_id] = []
            self._by_strategy[order.strategy_id].append(order.order_id)
        
        if order.position_id:
            if order.position_id not in self._by_position:
                self._by_position[order.position_id] = []
            self._by_position[order.position_id].append(order.order_id)
    
    def _move_to_history(self, order_id: str):
        """Move order to history"""
        
        order = self._orders.pop(order_id, None)
        if order:
            self._history.append(order)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
    
    # Query methods
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        """Get order by client ID"""
        order_id = self._by_client_id.get(client_order_id)
        return self._orders.get(order_id) if order_id else None
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders"""
        return [o for o in self._orders.values() if o.is_active()]
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get orders by symbol"""
        order_ids = self._by_symbol.get(symbol, [])
        return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """Get orders by strategy"""
        order_ids = self._by_strategy.get(strategy_id, [])
        return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_position(self, position_id: str) -> List[Order]:
        """Get orders by position"""
        order_ids = self._by_position.get(position_id, [])
        return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_state(self, state: OrderState) -> List[Order]:
        """Get orders by state"""
        return [o for o in self._orders.values() if o.state == state]
    
    def get_history(self, limit: int = 50) -> List[Order]:
        """Get order history"""
        return self._history[-limit:]
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders (active and history)"""
        return list(self._orders.values()) + self._history
    
    def get_summary(self) -> OrderSummary:
        """Get order summary"""
        
        all_orders = self.get_all_orders()
        
        summary = OrderSummary()
        summary.total_orders = len(all_orders)
        
        fill_times = []
        slippages = []
        
        for order in all_orders:
            # Count by state
            state = order.state.value
            summary.by_state[state] = summary.by_state.get(state, 0) + 1
            
            # Count by symbol
            summary.by_symbol[order.symbol] = summary.by_symbol.get(order.symbol, 0) + 1
            
            # Count by strategy
            if order.strategy_id:
                summary.by_strategy[order.strategy_id] = summary.by_strategy.get(order.strategy_id, 0) + 1
            
            # Metrics
            if order.state == OrderState.FILLED:
                summary.filled_orders += 1
                summary.total_volume += order.filled_quantity * order.avg_fill_price
                summary.total_commission += order.total_commission
                
                if order.submitted_at and order.filled_at:
                    fill_times.append(order.filled_at - order.submitted_at)
                
                if order.slippage_pct != 0:
                    slippages.append(order.slippage_pct)
            elif order.state == OrderState.CANCELLED:
                summary.cancelled_orders += 1
            elif order.state in [OrderState.FAILED, OrderState.REJECTED]:
                summary.failed_orders += 1
            elif order.is_active():
                summary.active_orders += 1
        
        if fill_times:
            summary.avg_fill_time_ms = sum(fill_times) / len(fill_times)
        if slippages:
            summary.avg_slippage_pct = sum(slippages) / len(slippages)
        
        return summary
    
    def check_expired_orders(self) -> List[str]:
        """Check and expire orders that have passed expires_at"""
        
        now = int(time.time() * 1000)
        expired = []
        
        for order in list(self._orders.values()):
            if order.expires_at and order.expires_at < now and order.is_active():
                success, _ = self.expire_order(order.order_id)
                if success:
                    expired.append(order.order_id)
        
        return expired
    
    def clear(self):
        """Clear all orders"""
        self._orders.clear()
        self._by_client_id.clear()
        self._by_symbol.clear()
        self._by_strategy.clear()
        self._by_position.clear()
        self._history.clear()
    
    def get_health(self) -> Dict:
        """Get tracker health"""
        return {
            "engine": "OrderTracker",
            "version": "1.0.0",
            "phase": "4.1",
            "status": "active",
            "orders": {
                "active": len(self._orders),
                "history": len(self._history)
            },
            "indexes": {
                "bySymbol": len(self._by_symbol),
                "byStrategy": len(self._by_strategy),
                "byPosition": len(self._by_position)
            },
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
order_tracker = OrderTracker()
