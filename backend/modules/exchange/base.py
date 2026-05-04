"""
Exchange Adapter Base Protocol

Unified interface for all exchange adapters (Paper, Binance, Bybit, etc.)
All adapters MUST implement this protocol.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .models import Balance, Position, Order, Fill, AccountInfo


class ExchangeAdapter(ABC):
    """
    Base protocol for exchange adapters.
    
    All methods return normalized models (Balance, Position, Order, Fill).
    """
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to exchange / initialize adapter.
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """
        Get account info (account ID, type, status, etc.)
        
        Returns:
            AccountInfo: normalized account info
        """
        pass
    
    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """
        Get all account balances.
        
        Returns:
            List[Balance]: list of normalized balances
        """
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get open positions.
        
        Args:
            symbol: filter by symbol (optional)
        
        Returns:
            List[Position]: list of normalized positions
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get open orders.
        
        Args:
            symbol: filter by symbol (optional)
        
        Returns:
            List[Order]: list of normalized orders
        """
        pass
    
    @abstractmethod
    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Order]:
        """
        Get order history.
        
        Args:
            symbol: filter by symbol (optional)
            limit: max number of orders to return
        
        Returns:
            List[Order]: list of normalized orders
        """
        pass
    
    @abstractmethod
    async def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Fill]:
        """
        Get recent fills/trades.
        
        Args:
            symbol: filter by symbol (optional)
            limit: max number of fills to return
        
        Returns:
            List[Fill]: list of normalized fills
        """
        pass
    
    @abstractmethod
    async def place_order(self, order_request: Dict[str, Any]) -> Order:
        """
        Place a new order.
        
        Args:
            order_request: {
                "symbol": "BTCUSDT",
                "side": "BUY" | "SELL",
                "type": "MARKET" | "LIMIT",
                "quantity": 0.05,
                "price": 70000.0 (for LIMIT orders),
                "stop_price": 68000.0 (for STOP orders, optional),
                "reduce_only": False (optional)
            }
        
        Returns:
            Order: normalized order
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: order ID to cancel
            symbol: symbol (optional, some exchanges require it)
        
        Returns:
            bool: True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all open orders.
        
        Args:
            symbol: filter by symbol (optional)
        
        Returns:
            int: number of orders cancelled
        """
        pass
    
    @abstractmethod
    async def get_mark_price(self, symbol: str) -> float:
        """
        Get current mark price for a symbol.
        
        Args:
            symbol: symbol (e.g. "BTCUSDT")
        
        Returns:
            float: mark price
        """
        pass
    
    @abstractmethod
    async def sync_state(self) -> Dict[str, Any]:
        """
        Sync exchange state (balances, positions, orders).
        
        Used for periodic reconciliation.
        
        Returns:
            Dict: {
                "balances": [...],
                "positions": [...],
                "open_orders": [...]
            }
        """
        pass
