"""
Execution Live Module

Real execution layer for routing trading intents to exchanges.
Supports: simulation, paper, binance routing.
"""

from .exchange_router import ExchangeRouter
from .order_manager import OrderManager
from .execution_sync import ExecutionSync
from .execution_config import EXECUTION_CONFIG

__all__ = [
    "ExchangeRouter",
    "OrderManager",
    "ExecutionSync",
    "EXECUTION_CONFIG",
]
