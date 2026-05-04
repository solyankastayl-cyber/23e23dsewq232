"""Exchange Adapter Layer — Week 3

Provides unified interface for multiple execution venues:
- PAPER (simulated trading)
- BINANCE_TESTNET (Binance testnet)
- BYBIT_DEMO (Bybit demo account)
"""

from .base_adapter import BaseExchangeAdapter
from .adapter_factory import get_exchange_adapter
from .models import OrderRequest, OrderResponse, AccountInfo, Balance, Position

__all__ = [
    "BaseExchangeAdapter",
    "get_exchange_adapter",
    "OrderRequest",
    "OrderResponse",
    "AccountInfo",
    "Balance",
    "Position",
]
