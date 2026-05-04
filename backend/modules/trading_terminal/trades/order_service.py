"""
Order Service (TR3)
===================

Order management service - storage and lifecycle tracking.
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .trade_types import (
    Order,
    OrderStatus,
    OrderType,
    OrderSide,
    Fill
)


class OrderService:
    """
    Order management service.
    
    Internal source of truth for orders.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Orders storage
        self._orders: Dict[str, Order] = {}
        
        # Fills storage
        self._fills: Dict[str, Fill] = {}
        
        # Order listeners
        self._listeners: List[callable] = []
        
        # Initialize with mock data
        self._init_mock_data()
        
        self._initialized = True
        print("[OrderService] Initialized")
    
    def _init_mock_data(self):
        """Initialize with demo orders"""
        now = datetime.now(timezone.utc)
        
        # Sample orders
        orders = [
            Order(
                order_id="ord_demo_001",
                exchange="MOCK",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                quantity=0.1,
                filled_quantity=0.1,
                avg_fill_price=42500.0,
                status=OrderStatus.FILLED,
                total_fee=4.25,
                fee_asset="USDT",
                created_at=now - timedelta(hours=2),
                filled_at=now - timedelta(hours=2)
            ),
            Order(
                order_id="ord_demo_002",
                exchange="MOCK",
                symbol="ETHUSDT",
                side=OrderSide.SELL,
                type=OrderType.LIMIT,
                quantity=2.0,
                filled_quantity=0.0,
                price=2200.0,
                status=OrderStatus.NEW,
                created_at=now - timedelta(minutes=30)
            ),
            Order(
                order_id="ord_demo_003",
                exchange="MOCK",
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                quantity=0.1,
                filled_quantity=0.1,
                avg_fill_price=43200.0,
                status=OrderStatus.FILLED,
                total_fee=4.32,
                fee_asset="USDT",
                created_at=now - timedelta(hours=1),
                filled_at=now - timedelta(hours=1)
            )
        ]
        
        for order in orders:
            self._orders[order.order_id] = order
        
        # Sample fills
        fills = [
            Fill(
                fill_id="fill_demo_001",
                order_id="ord_demo_001",
                exchange="MOCK",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=0.1,
                price=42500.0,
                fee=4.25,
                fee_asset="USDT",
                notional_value=4250.0,
                timestamp=now - timedelta(hours=2)
            ),
            Fill(
                fill_id="fill_demo_002",
                order_id="ord_demo_003",
                exchange="MOCK",
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                quantity=0.1,
                price=43200.0,
                fee=4.32,
                fee_asset="USDT",
                notional_value=4320.0,
                timestamp=now - timedelta(hours=1)
            )
        ]
        
        for fill in fills:
            self._fills[fill.fill_id] = fill
    
    # ===========================================
    # Order CRUD
    # ===========================================
    
    def create_order(self, order: Order) -> Order:
        """Store new order"""
        order.remaining_quantity = order.quantity - order.filled_quantity
        self._orders[order.order_id] = order
        self._notify_listeners("ORDER_CREATED", order)
        return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders"""
        return list(self._orders.values())
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get orders by status"""
        return [o for o in self._orders.values() if o.status == status]
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get orders by symbol"""
        return [o for o in self._orders.values() if o.symbol == symbol]
    
    def get_open_orders(self) -> List[Order]:
        """Get open orders (NEW, PARTIAL)"""
        return [
            o for o in self._orders.values() 
            if o.status in [OrderStatus.NEW, OrderStatus.PARTIAL]
        ]
    
    def get_recent_orders(self, limit: int = 50) -> List[Order]:
        """Get recent orders sorted by creation time"""
        sorted_orders = sorted(
            self._orders.values(),
            key=lambda o: o.created_at,
            reverse=True
        )
        return sorted_orders[:limit]
    
    def update_order(self, order_id: str, updates: Dict[str, Any]) -> Optional[Order]:
        """Update order fields"""
        order = self._orders.get(order_id)
        if not order:
            return None
        
        for key, value in updates.items():
            if hasattr(order, key):
                setattr(order, key, value)
        
        order.updated_at = datetime.now(timezone.utc)
        self._notify_listeners("ORDER_UPDATED", order)
        return order
    
    def cancel_order(self, order_id: str) -> Optional[Order]:
        """Cancel an order"""
        order = self._orders.get(order_id)
        if not order:
            return None
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return order
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        self._notify_listeners("ORDER_CANCELLED", order)
        return order
    
    # ===========================================
    # Fills
    # ===========================================
    
    def add_fill(self, fill: Fill) -> Fill:
        """Add a fill execution"""
        self._fills[fill.fill_id] = fill
        
        # Update order
        order = self._orders.get(fill.order_id)
        if order:
            order.filled_quantity += fill.quantity
            order.remaining_quantity = order.quantity - order.filled_quantity
            order.total_fee += fill.fee
            
            # Update avg fill price
            if order.avg_fill_price == 0:
                order.avg_fill_price = fill.price
            else:
                total_value = order.avg_fill_price * (order.filled_quantity - fill.quantity) + fill.price * fill.quantity
                order.avg_fill_price = total_value / order.filled_quantity
            
            # Update status
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now(timezone.utc)
            elif order.filled_quantity > 0:
                order.status = OrderStatus.PARTIAL
            
            order.updated_at = datetime.now(timezone.utc)
            self._notify_listeners("ORDER_FILLED", order)
        
        return fill
    
    def get_fills(self, order_id: Optional[str] = None) -> List[Fill]:
        """Get fills, optionally filtered by order"""
        if order_id:
            return [f for f in self._fills.values() if f.order_id == order_id]
        return list(self._fills.values())
    
    def get_recent_fills(self, limit: int = 50) -> List[Fill]:
        """Get recent fills"""
        sorted_fills = sorted(
            self._fills.values(),
            key=lambda f: f.timestamp,
            reverse=True
        )
        return sorted_fills[:limit]
    
    # ===========================================
    # Listeners
    # ===========================================
    
    def add_listener(self, callback: callable) -> None:
        """Add order event listener"""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event: str, order: Order) -> None:
        """Notify all listeners"""
        for listener in self._listeners:
            try:
                listener(event, order)
            except Exception as e:
                print(f"[OrderService] Listener error: {e}")
    
    # ===========================================
    # Statistics
    # ===========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get order statistics"""
        orders = list(self._orders.values())
        
        return {
            "total_orders": len(orders),
            "filled": len([o for o in orders if o.status == OrderStatus.FILLED]),
            "cancelled": len([o for o in orders if o.status == OrderStatus.CANCELLED]),
            "open": len([o for o in orders if o.status in [OrderStatus.NEW, OrderStatus.PARTIAL]]),
            "total_fills": len(self._fills)
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "OrderService",
            "status": "healthy",
            "phase": "TR3",
            "orders_count": len(self._orders),
            "fills_count": len(self._fills)
        }


# Global singleton
order_service = OrderService()
