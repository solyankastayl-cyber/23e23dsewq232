"""
Order Manager

Local registry for tracking all orders across all venues.
Provides unified interface for order state management.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Local order registry.
    
    Tracks all orders (paper, simulation, binance) in a unified format.
    Provides CRUD operations and queries.
    """
    
    def __init__(self):
        self.orders: Dict[str, Dict[str, Any]] = {}
    
    def register(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new order.
        
        Args:
            order: Order dictionary (must contain 'order_id')
            
        Returns:
            Registered order with timestamps
        """
        order_id = order.get("order_id")
        if not order_id:
            logger.error("[OrderManager] Cannot register order without order_id")
            return order
        
        now = datetime.now(timezone.utc).isoformat()
        
        registered_order = {
            **order,
            "created_at": now,
            "updated_at": now,
        }
        
        self.orders[order_id] = registered_order
        logger.info(f"[OrderManager] Registered order: {order_id}")
        
        return registered_order
    
    def update(self, order_id: str, **fields) -> Optional[Dict[str, Any]]:
        """
        Update an existing order.
        
        Args:
            order_id: Order ID to update
            **fields: Fields to update
            
        Returns:
            Updated order or None if not found
        """
        if order_id not in self.orders:
            logger.warning(f"[OrderManager] Order not found: {order_id}")
            return None
        
        self.orders[order_id].update(fields)
        self.orders[order_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"[OrderManager] Updated order: {order_id}")
        return self.orders[order_id]
    
    def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order dict or None
        """
        return self.orders.get(order_id)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all orders.
        
        Returns:
            List of all orders
        """
        return list(self.orders.values())
    
    def list_open(self) -> List[Dict[str, Any]]:
        """
        List only open orders (not filled, cancelled, rejected, or failed).
        
        Returns:
            List of open orders
        """
        terminal_statuses = {"FILLED", "CANCELLED", "REJECTED", "FAILED"}
        return [
            order for order in self.orders.values()
            if order.get("status") not in terminal_statuses
        ]
    
    def count(self) -> Dict[str, int]:
        """
        Get order counts by status.
        
        Returns:
            Dict with status counts
        """
        counts = {
            "total": len(self.orders),
            "open": len(self.list_open()),
        }
        return counts
