"""
Execution Repository
====================

In-memory storage for execution intents and orders.
Later can be swapped for MongoDB persistence.
"""

from typing import Dict, List, Optional
from .execution_models import ExecutionIntent, OrderState


class ExecutionRepository:
    """In-memory repository for execution data"""
    
    def __init__(self):
        self.intents: Dict[str, ExecutionIntent] = {}
        self.orders: Dict[str, OrderState] = {}

    # ---- Intent Operations ----
    
    def save_intent(self, intent: ExecutionIntent) -> ExecutionIntent:
        """Save or update intent"""
        self.intents[intent.intent_id] = intent
        return intent

    def get_intent(self, intent_id: str) -> Optional[ExecutionIntent]:
        """Get intent by ID"""
        return self.intents.get(intent_id)

    def list_intents(self, symbol: Optional[str] = None) -> List[ExecutionIntent]:
        """List all intents, optionally filtered by symbol"""
        values = list(self.intents.values())
        if symbol:
            values = [x for x in values if x.symbol == symbol.upper()]
        return sorted(values, key=lambda x: x.updated_at, reverse=True)

    def get_latest_intent(self, symbol: str, timeframe: str) -> Optional[ExecutionIntent]:
        """Get most recent intent for symbol/timeframe"""
        items = [
            x for x in self.intents.values()
            if x.symbol == symbol.upper() and x.timeframe == timeframe.upper()
        ]
        if not items:
            return None
        return sorted(items, key=lambda x: x.updated_at, reverse=True)[0]

    def delete_intent(self, intent_id: str) -> bool:
        """Delete intent by ID"""
        if intent_id in self.intents:
            del self.intents[intent_id]
            return True
        return False

    # ---- Order Operations ----
    
    def save_order(self, order: OrderState) -> OrderState:
        """Save or update order"""
        self.orders[order.order_id] = order
        return order

    def get_order(self, order_id: str) -> Optional[OrderState]:
        """Get order by ID"""
        return self.orders.get(order_id)

    def list_orders(
        self, 
        symbol: Optional[str] = None, 
        open_only: bool = False,
        limit: int = 100
    ) -> List[OrderState]:
        """List orders with optional filters"""
        values = list(self.orders.values())
        
        if symbol:
            values = [x for x in values if x.symbol == symbol.upper()]
        
        if open_only:
            values = [x for x in values if x.status in {"ORDER_PLACED", "PARTIAL_FILL"}]
        
        sorted_values = sorted(values, key=lambda x: x.updated_at, reverse=True)
        return sorted_values[:limit]

    def get_latest_order_by_intent(self, intent_id: str) -> Optional[OrderState]:
        """Get most recent order for an intent"""
        items = [x for x in self.orders.values() if x.intent_id == intent_id]
        if not items:
            return None
        return sorted(items, key=lambda x: x.updated_at, reverse=True)[0]

    def get_orders_by_symbol(self, symbol: str) -> List[OrderState]:
        """Get all orders for a symbol"""
        return [x for x in self.orders.values() if x.symbol == symbol.upper()]

    def delete_order(self, order_id: str) -> bool:
        """Delete order by ID"""
        if order_id in self.orders:
            del self.orders[order_id]
            return True
        return False

    # ---- Statistics ----
    
    def count_open_orders(self, symbol: Optional[str] = None) -> int:
        """Count open orders"""
        orders = self.list_orders(symbol=symbol, open_only=True)
        return len(orders)

    def get_total_filled_size(self, symbol: str) -> float:
        """Get total filled size for symbol"""
        orders = [x for x in self.orders.values() 
                  if x.symbol == symbol.upper() and x.status == "FILLED"]
        return sum(o.filled_size for o in orders)


# Singleton instance
_execution_repo: Optional[ExecutionRepository] = None


def get_execution_repository() -> ExecutionRepository:
    """Get singleton repository instance"""
    global _execution_repo
    if _execution_repo is None:
        _execution_repo = ExecutionRepository()
    return _execution_repo
