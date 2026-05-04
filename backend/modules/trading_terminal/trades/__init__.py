"""
Trading Terminal - Trades Module (TR3)
======================================

Trade Monitor - orders, fills, executions, trade history.

Components:
- trade_types: Type definitions
- order_service: Order management
- trade_aggregator: Fill to trade conversion
- execution_log_service: Execution logs
- trade_routes: API endpoints
"""

from .trade_types import (
    OrderStatus,
    OrderType,
    OrderSide,
    Order,
    Fill,
    Trade,
    ExecutionLog,
    ExecutionLogType,
    TradesSummary
)

from .order_service import (
    OrderService,
    order_service
)

from .trade_aggregator import (
    TradeAggregator,
    trade_aggregator
)

from .trade_service import (
    TradeService,
    trade_service
)

__all__ = [
    # Types
    "OrderStatus",
    "OrderType",
    "OrderSide",
    "Order",
    "Fill",
    "Trade",
    "ExecutionLog",
    "ExecutionLogType",
    "TradesSummary",
    # Services
    "OrderService",
    "order_service",
    "TradeAggregator",
    "trade_aggregator",
    "TradeService",
    "trade_service"
]
