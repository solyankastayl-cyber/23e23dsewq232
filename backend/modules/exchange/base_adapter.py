"""Base Exchange Adapter — Week 3"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import (
    OrderRequest,
    OrderResponse,
    AccountInfo,
    Balance,
    Position,
)


class BaseExchangeAdapter(ABC):
    """Base interface for all exchange adapters."""

    def __init__(self, config: dict):
        self.config = config
        self.connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to exchange."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from exchange."""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Ping exchange (health check)."""
        pass

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        pass

    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """Get account balances."""
        pass

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order."""
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[OrderResponse]:
        """Get order by ID."""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Get open orders."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get positions."""
        pass

    @abstractmethod
    async def get_recent_fills(self, symbol: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get recent fills."""
        pass
