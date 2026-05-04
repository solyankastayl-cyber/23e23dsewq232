"""
Exchange Router - PHASE 5.1
===========================

Routes exchange requests to appropriate adapters.
Manages adapter lifecycle and provides unified interface.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .exchange_types import (
    ExchangeId,
    ExchangeOrderRequest,
    ExchangeOrderResponse,
    ExchangePosition,
    ExchangeBalance,
    ExchangeTicker,
    ExchangeOrderbook,
    ExchangeConnectionStatus,
    StreamType
)
from .base_exchange_adapter import BaseExchangeAdapter
from .binance_adapter import BinanceAdapter
from .bybit_adapter import BybitAdapter
from .okx_adapter import OKXAdapter


class ExchangeRouter:
    """
    Routes requests to appropriate exchange adapters.
    
    Features:
    - Adapter lifecycle management
    - Request routing
    - Best exchange selection (future)
    - Failover routing (future)
    """
    
    def __init__(self):
        self._adapters: Dict[ExchangeId, BaseExchangeAdapter] = {}
        self._default_exchange = ExchangeId.BINANCE
        
        # Exchange routing config (symbol -> preferred exchange)
        self._symbol_routes: Dict[str, ExchangeId] = {}
    
    # ============================================
    # Adapter Management
    # ============================================
    
    def register_adapter(
        self,
        exchange_id: ExchangeId,
        adapter: BaseExchangeAdapter
    ) -> None:
        """Register an exchange adapter"""
        self._adapters[exchange_id] = adapter
    
    def get_adapter(self, exchange_id: ExchangeId) -> Optional[BaseExchangeAdapter]:
        """Get adapter for exchange"""
        return self._adapters.get(exchange_id)
    
    def get_or_create_adapter(
        self,
        exchange_id: ExchangeId,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        testnet: bool = False
    ) -> BaseExchangeAdapter:
        """Get existing adapter or create new one"""
        if exchange_id in self._adapters:
            return self._adapters[exchange_id]
        
        # Create new adapter
        adapter = self._create_adapter(
            exchange_id, api_key, api_secret, passphrase, testnet
        )
        self._adapters[exchange_id] = adapter
        return adapter
    
    def _create_adapter(
        self,
        exchange_id: ExchangeId,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        testnet: bool = False
    ) -> BaseExchangeAdapter:
        """Create adapter for exchange"""
        if exchange_id == ExchangeId.BINANCE:
            return BinanceAdapter(api_key, api_secret, testnet)
        elif exchange_id == ExchangeId.BYBIT:
            return BybitAdapter(api_key, api_secret, testnet)
        elif exchange_id == ExchangeId.OKX:
            return OKXAdapter(api_key, api_secret, passphrase, testnet)
        else:
            raise ValueError(f"Unknown exchange: {exchange_id}")
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def connect(
        self,
        exchange_id: ExchangeId,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        testnet: bool = False
    ) -> bool:
        """Connect to exchange"""
        adapter = self.get_or_create_adapter(
            exchange_id, api_key, api_secret, passphrase, testnet
        )
        return await adapter.connect()
    
    async def disconnect(self, exchange_id: ExchangeId) -> bool:
        """Disconnect from exchange"""
        adapter = self.get_adapter(exchange_id)
        if adapter:
            return await adapter.disconnect()
        return False
    
    async def disconnect_all(self) -> Dict[ExchangeId, bool]:
        """Disconnect from all exchanges"""
        results = {}
        for exchange_id, adapter in self._adapters.items():
            results[exchange_id] = await adapter.disconnect()
        return results
    
    def get_connection_status(
        self,
        exchange_id: Optional[ExchangeId] = None
    ) -> Dict[ExchangeId, ExchangeConnectionStatus]:
        """Get connection status for exchanges"""
        if exchange_id:
            adapter = self.get_adapter(exchange_id)
            if adapter:
                return {exchange_id: adapter.get_connection_status()}
            return {}
        
        return {
            eid: adapter.get_connection_status()
            for eid, adapter in self._adapters.items()
        }
    
    # ============================================
    # Order Routing
    # ============================================
    
    def set_symbol_route(self, symbol: str, exchange_id: ExchangeId) -> None:
        """Set preferred exchange for symbol"""
        self._symbol_routes[symbol.upper()] = exchange_id
    
    def get_exchange_for_symbol(self, symbol: str) -> ExchangeId:
        """Get preferred exchange for symbol"""
        return self._symbol_routes.get(symbol.upper(), self._default_exchange)
    
    async def route_order(
        self,
        order: ExchangeOrderRequest
    ) -> ExchangeOrderResponse:
        """Route order to appropriate exchange"""
        exchange_id = order.exchange or self.get_exchange_for_symbol(order.symbol)
        
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.create_order(order)
    
    # ============================================
    # Account Operations
    # ============================================
    
    async def get_balances(
        self,
        exchange_id: Optional[ExchangeId] = None,
        asset: Optional[str] = None
    ) -> Dict[ExchangeId, List[ExchangeBalance]]:
        """Get balances from exchanges"""
        if exchange_id:
            adapter = self.get_adapter(exchange_id)
            if adapter:
                balances = await adapter.get_balance(asset)
                return {exchange_id: balances}
            return {}
        
        results = {}
        for eid, adapter in self._adapters.items():
            try:
                balances = await adapter.get_balance(asset)
                results[eid] = balances
            except Exception as e:
                print(f"Error getting balances from {eid}: {e}")
        
        return results
    
    async def get_positions(
        self,
        exchange_id: Optional[ExchangeId] = None,
        symbol: Optional[str] = None
    ) -> Dict[ExchangeId, List[ExchangePosition]]:
        """Get positions from exchanges"""
        if exchange_id:
            adapter = self.get_adapter(exchange_id)
            if adapter:
                positions = await adapter.get_positions(symbol)
                return {exchange_id: positions}
            return {}
        
        results = {}
        for eid, adapter in self._adapters.items():
            try:
                positions = await adapter.get_positions(symbol)
                results[eid] = positions
            except Exception as e:
                print(f"Error getting positions from {eid}: {e}")
        
        return results
    
    async def get_open_orders(
        self,
        exchange_id: Optional[ExchangeId] = None,
        symbol: Optional[str] = None
    ) -> Dict[ExchangeId, List[ExchangeOrderResponse]]:
        """Get open orders from exchanges"""
        if exchange_id:
            adapter = self.get_adapter(exchange_id)
            if adapter:
                orders = await adapter.get_open_orders(symbol)
                return {exchange_id: orders}
            return {}
        
        results = {}
        for eid, adapter in self._adapters.items():
            try:
                orders = await adapter.get_open_orders(symbol)
                results[eid] = orders
            except Exception as e:
                print(f"Error getting open orders from {eid}: {e}")
        
        return results
    
    # ============================================
    # Order Operations
    # ============================================
    
    async def create_order(
        self,
        exchange_id: ExchangeId,
        order: ExchangeOrderRequest
    ) -> ExchangeOrderResponse:
        """Create order on exchange"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.create_order(order)
    
    async def cancel_order(
        self,
        exchange_id: ExchangeId,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """Cancel order on exchange"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.cancel_order(order_id, symbol)
    
    async def cancel_all_orders(
        self,
        exchange_id: ExchangeId,
        symbol: Optional[str] = None
    ) -> List[ExchangeOrderResponse]:
        """Cancel all orders on exchange"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.cancel_all_orders(symbol)
    
    async def get_order_status(
        self,
        exchange_id: ExchangeId,
        order_id: str,
        symbol: Optional[str] = None
    ) -> ExchangeOrderResponse:
        """Get order status from exchange"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.get_order_status(order_id, symbol)
    
    # ============================================
    # Market Data
    # ============================================
    
    async def get_ticker(
        self,
        exchange_id: ExchangeId,
        symbol: str
    ) -> ExchangeTicker:
        """Get ticker from exchange"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.get_ticker(symbol)
    
    async def get_tickers(
        self,
        symbol: str
    ) -> Dict[ExchangeId, ExchangeTicker]:
        """Get ticker from all connected exchanges"""
        results = {}
        for eid, adapter in self._adapters.items():
            try:
                ticker = await adapter.get_ticker(symbol)
                results[eid] = ticker
            except Exception as e:
                print(f"Error getting ticker from {eid}: {e}")
        
        return results
    
    async def get_orderbook(
        self,
        exchange_id: ExchangeId,
        symbol: str,
        depth: int = 20
    ) -> ExchangeOrderbook:
        """Get orderbook from exchange"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.get_orderbook(symbol, depth)
    
    # ============================================
    # Best Price Selection (Future Enhancement)
    # ============================================
    
    async def get_best_price(
        self,
        symbol: str,
        side: str
    ) -> Dict[str, Any]:
        """Get best price across exchanges"""
        tickers = await self.get_tickers(symbol)
        
        if not tickers:
            return {"error": "No tickers available"}
        
        if side.upper() == "BUY":
            # Best ask (lowest sell price)
            best = min(tickers.items(), key=lambda x: x[1].ask_price)
        else:
            # Best bid (highest buy price)
            best = max(tickers.items(), key=lambda x: x[1].bid_price)
        
        exchange_id, ticker = best
        
        return {
            "exchange": exchange_id.value,
            "symbol": symbol,
            "side": side,
            "price": ticker.ask_price if side.upper() == "BUY" else ticker.bid_price,
            "all_prices": {
                eid.value: {
                    "bid": t.bid_price,
                    "ask": t.ask_price
                }
                for eid, t in tickers.items()
            }
        }
    
    # ============================================
    # Stream Management
    # ============================================
    
    async def subscribe_market_data(
        self,
        exchange_id: ExchangeId,
        symbols: List[str],
        stream_type: StreamType
    ) -> bool:
        """Subscribe to market data stream"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.subscribe_market_data(symbols, stream_type)
    
    async def subscribe_user_stream(
        self,
        exchange_id: ExchangeId
    ) -> bool:
        """Subscribe to user data stream"""
        adapter = self.get_adapter(exchange_id)
        if not adapter:
            raise ValueError(f"No adapter registered for {exchange_id}")
        
        return await adapter.subscribe_user_stream()
    
    # ============================================
    # Utility
    # ============================================
    
    def get_registered_exchanges(self) -> List[ExchangeId]:
        """Get list of registered exchanges"""
        return list(self._adapters.keys())
    
    def get_router_status(self) -> Dict[str, Any]:
        """Get router status"""
        return {
            "registered_exchanges": [e.value for e in self._adapters.keys()],
            "default_exchange": self._default_exchange.value,
            "symbol_routes": {
                sym: ex.value for sym, ex in self._symbol_routes.items()
            },
            "connections": {
                ex.value: adapter.get_connection_status().dict()
                for ex, adapter in self._adapters.items()
            },
            "updated_at": datetime.utcnow().isoformat()
        }


# Global router instance
_router: Optional[ExchangeRouter] = None


def get_exchange_router() -> ExchangeRouter:
    """Get or create global exchange router"""
    global _router
    if _router is None:
        _router = ExchangeRouter()
    return _router
