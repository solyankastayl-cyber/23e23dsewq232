"""
Exchange Adapter Layer - PHASE 5.1
==================================

Universal exchange integration layer.

Components:
- exchange_types: Unified types for orders, positions, balances
- base_exchange_adapter: Abstract base class for all exchanges
- binance_adapter: Binance implementation
- bybit_adapter: Bybit implementation
- okx_adapter: OKX implementation
- exchange_router: Routes requests to appropriate exchange
- ws_manager: WebSocket stream manager
- exchange_repository: Persistence layer
- exchange_routes: REST API endpoints
"""

from .exchange_types import (
    ExchangeId,
    OrderSide,
    OrderType,
    TimeInForce,
    OrderStatus,
    PositionSide,
    MarginMode,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangePosition,
    ExchangeBalance,
    ExchangeTicker,
    OrderbookLevel,
    ExchangeOrderbook,
    ExchangeConnectionStatus,
    StreamType,
    StreamStatus
)

from .base_exchange_adapter import BaseExchangeAdapter
from .exchange_router import ExchangeRouter
from .ws_manager import WebSocketManager

__all__ = [
    "ExchangeId",
    "OrderSide",
    "OrderType",
    "TimeInForce",
    "OrderStatus",
    "PositionSide",
    "MarginMode",
    "ExchangeOrderRequest",
    "ExchangeOrderResponse",
    "ExchangePosition",
    "ExchangeBalance",
    "ExchangeTicker",
    "OrderbookLevel",
    "ExchangeOrderbook",
    "ExchangeConnectionStatus",
    "StreamType",
    "StreamStatus",
    "BaseExchangeAdapter",
    "ExchangeRouter",
    "WebSocketManager"
]
