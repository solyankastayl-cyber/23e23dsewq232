"""
Base Exchange Adapter - PHASE 5.1
=================================

Abstract base class defining the unified exchange interface.
All exchange adapters must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .exchange_types import (
    ExchangeId,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangePosition,
    ExchangeBalance,
    ExchangeTicker,
    ExchangeOrderbook,
    ExchangeConnectionStatus,
    OrderStatus,
    StreamType
)


class BaseExchangeAdapter(ABC):
    """
    Abstract base class for exchange adapters.
    
    Provides unified interface for:
    - Connection management
    - Account operations (balances, positions)
    - Order operations (create, cancel, status)
    - Market data (ticker, orderbook)
    - WebSocket streams
    """
    
    def __init__(
        self,
        exchange_id: ExchangeId,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        testnet: bool = False
    ):
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet
        
        # Connection state
        self._connected = False
        self._authenticated = False
        self._connected_at: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._error_count = 0
        
        # Rate limit tracking
        self._rate_limit_remaining = 1000
        self._rate_limit_reset: Optional[datetime] = None
    
    # ============================================
    # Connection Management
    # ============================================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to exchange.
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from exchange.
        
        Returns:
            bool: True if disconnection successful
        """
        pass
    
    def get_connection_status(self) -> ExchangeConnectionStatus:
        """Get current connection status"""
        return ExchangeConnectionStatus(
            exchange=self.exchange_id,
            connected=self._connected,
            authenticated=self._authenticated,
            rest_available=self._connected,
            rate_limit_remaining=self._rate_limit_remaining,
            rate_limit_reset_at=self._rate_limit_reset,
            last_error=self._last_error,
            error_count=self._error_count,
            connected_at=self._connected_at,
            updated_at=datetime.utcnow()
        )
    
    # ============================================
    # Account Operations
    # ============================================
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> List[ExchangeBalance]:
        """
        Get account balances.
        
        Args:
            asset: Specific asset to query, or None for all
            
        Returns:
            List of balances
        """
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[ExchangePosition]:
        """
        Get open positions.
        
        Args:
            symbol: Specific symbol to query, or None for all
            
        Returns:
            List of positions
        """
        pass
    
    # ============================================
    # Order Operations
    # ============================================
    
    @abstractmethod
    async def create_order(self, order: ExchangeOrderRequest) -> ExchangeOrderResponse:
        """
        Create a new order.
        
        Args:
            order: Order request
            
        Returns:
            Order response
        """
        pass
    
    @abstractmethod
    async def cancel_order(
        self,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """
        Cancel an order.
        
        Args:
            order_id: Exchange order ID
            symbol: Symbol (required by some exchanges)
            
        Returns:
            Updated order response
        """
        pass
    
    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrderResponse]:
        """
        Cancel all open orders.
        
        Args:
            symbol: Cancel only for this symbol, or all if None
            
        Returns:
            List of cancelled orders
        """
        pass
    
    @abstractmethod
    async def get_order_status(
        self,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """
        Get order status.
        
        Args:
            order_id: Exchange order ID
            symbol: Symbol (required by some exchanges)
            
        Returns:
            Order response
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[ExchangeOrderResponse]:
        """
        Get all open orders.
        
        Args:
            symbol: Filter by symbol, or all if None
            
        Returns:
            List of open orders
        """
        pass
    
    # ============================================
    # Market Data
    # ============================================
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> ExchangeTicker:
        """
        Get ticker for symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker data
        """
        pass
    
    @abstractmethod
    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20
    ) -> ExchangeOrderbook:
        """
        Get orderbook for symbol.
        
        Args:
            symbol: Trading pair
            depth: Number of levels to fetch
            
        Returns:
            Orderbook data
        """
        pass
    
    # ============================================
    # WebSocket Streams
    # ============================================
    
    @abstractmethod
    async def subscribe_market_data(
        self,
        symbols: List[str],
        stream_type: StreamType
    ) -> bool:
        """
        Subscribe to market data stream.
        
        Args:
            symbols: List of symbols to subscribe
            stream_type: Type of stream (TICKER, ORDERBOOK, TRADES, etc.)
            
        Returns:
            True if subscription successful
        """
        pass
    
    @abstractmethod
    async def subscribe_user_stream(self) -> bool:
        """
        Subscribe to user data stream (orders, positions, balance).
        
        Returns:
            True if subscription successful
        """
        pass
    
    @abstractmethod
    async def unsubscribe(
        self,
        symbols: List[str],
        stream_type: StreamType
    ) -> bool:
        """
        Unsubscribe from stream.
        
        Args:
            symbols: List of symbols to unsubscribe
            stream_type: Type of stream
            
        Returns:
            True if unsubscription successful
        """
        pass
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def generate_client_order_id(self) -> str:
        """Generate unique client order ID"""
        return f"{self.exchange_id.value}_{uuid.uuid4().hex[:16]}"
    
    def _record_error(self, error: str) -> None:
        """Record error for tracking"""
        self._last_error = error
        self._error_count += 1
    
    def _clear_error(self) -> None:
        """Clear error state on success"""
        self._last_error = None
    
    @abstractmethod
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to exchange format.
        
        Args:
            symbol: Unified symbol format (e.g., BTCUSDT)
            
        Returns:
            Exchange-specific symbol format
        """
        pass
    
    @abstractmethod
    def _parse_symbol(self, exchange_symbol: str) -> str:
        """
        Parse exchange symbol to unified format.
        
        Args:
            exchange_symbol: Exchange-specific symbol
            
        Returns:
            Unified symbol format
        """
        pass
