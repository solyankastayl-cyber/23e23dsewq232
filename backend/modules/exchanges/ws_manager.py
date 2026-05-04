"""
WebSocket Manager - PHASE 5.1
=============================

Manages WebSocket connections and streams for all exchanges.
"""

from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from collections import defaultdict
import asyncio
import json

from .exchange_types import (
    ExchangeId,
    StreamType,
    StreamStatus,
    StreamConfig,
    ExchangeTicker,
    ExchangeOrderbook
)


class StreamHandler:
    """Handles a single stream"""
    
    def __init__(
        self,
        exchange: ExchangeId,
        stream_type: StreamType,
        symbols: List[str]
    ):
        self.exchange = exchange
        self.stream_type = stream_type
        self.symbols = symbols
        self.status = StreamStatus.DISCONNECTED
        self.callbacks: List[Callable] = []
        self.last_message: Optional[datetime] = None
        self.message_count = 0
        self.error_count = 0
        self._task: Optional[asyncio.Task] = None
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for stream data"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable) -> None:
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def notify(self, data: Any) -> None:
        """Notify all callbacks"""
        self.last_message = datetime.utcnow()
        self.message_count += 1
        
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.error_count += 1
                print(f"Stream callback error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get stream status"""
        return {
            "exchange": self.exchange.value,
            "stream_type": self.stream_type.value,
            "symbols": self.symbols,
            "status": self.status.value,
            "last_message": self.last_message.isoformat() if self.last_message else None,
            "message_count": self.message_count,
            "error_count": self.error_count
        }


class WebSocketManager:
    """
    WebSocket Manager for all exchanges.
    
    Manages:
    - Market data streams (ticker, orderbook, trades)
    - User data streams (orders, positions, balance)
    - Connection lifecycle
    - Auto-reconnection
    """
    
    def __init__(self):
        # Stream handlers: exchange -> stream_type -> handler
        self._handlers: Dict[ExchangeId, Dict[StreamType, StreamHandler]] = defaultdict(dict)
        
        # Connection status
        self._connections: Dict[ExchangeId, StreamStatus] = {}
        
        # Global callbacks
        self._global_callbacks: Dict[StreamType, List[Callable]] = defaultdict(list)
        
        # Simulated data for demo
        self._simulate_task: Optional[asyncio.Task] = None
    
    # ============================================
    # Stream Management
    # ============================================
    
    async def start_stream(
        self,
        config: StreamConfig,
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Start a stream.
        
        Args:
            config: Stream configuration
            callback: Optional callback for stream data
            
        Returns:
            True if started successfully
        """
        exchange = config.exchange
        stream_type = config.stream_type
        symbols = config.symbols
        
        # Create or get handler
        if stream_type not in self._handlers[exchange]:
            handler = StreamHandler(exchange, stream_type, symbols)
            self._handlers[exchange][stream_type] = handler
        else:
            handler = self._handlers[exchange][stream_type]
            handler.symbols = list(set(handler.symbols + symbols))
        
        # Add callback
        if callback:
            handler.add_callback(callback)
        
        # Start stream (in real impl, would connect to WebSocket)
        handler.status = StreamStatus.CONNECTED
        
        # For demo, start simulated data
        if self._simulate_task is None:
            self._simulate_task = asyncio.create_task(self._simulate_data())
        
        return True
    
    async def stop_stream(
        self,
        exchange: ExchangeId,
        stream_type: StreamType,
        symbols: Optional[List[str]] = None
    ) -> bool:
        """
        Stop a stream.
        
        Args:
            exchange: Exchange ID
            stream_type: Stream type
            symbols: Specific symbols to unsubscribe (None = all)
            
        Returns:
            True if stopped successfully
        """
        if exchange not in self._handlers:
            return True
        
        if stream_type not in self._handlers[exchange]:
            return True
        
        handler = self._handlers[exchange][stream_type]
        
        if symbols:
            handler.symbols = [s for s in handler.symbols if s not in symbols]
            if not handler.symbols:
                handler.status = StreamStatus.DISCONNECTED
        else:
            handler.status = StreamStatus.DISCONNECTED
            handler.symbols = []
        
        return True
    
    async def stop_all_streams(self, exchange: Optional[ExchangeId] = None) -> bool:
        """Stop all streams for exchange or all exchanges"""
        if exchange:
            if exchange in self._handlers:
                for handler in self._handlers[exchange].values():
                    handler.status = StreamStatus.DISCONNECTED
                    handler.symbols = []
        else:
            for ex_handlers in self._handlers.values():
                for handler in ex_handlers.values():
                    handler.status = StreamStatus.DISCONNECTED
                    handler.symbols = []
        
        return True
    
    # ============================================
    # Callback Management
    # ============================================
    
    def add_global_callback(
        self,
        stream_type: StreamType,
        callback: Callable
    ) -> None:
        """Add global callback for stream type"""
        self._global_callbacks[stream_type].append(callback)
    
    def remove_global_callback(
        self,
        stream_type: StreamType,
        callback: Callable
    ) -> None:
        """Remove global callback"""
        if callback in self._global_callbacks[stream_type]:
            self._global_callbacks[stream_type].remove(callback)
    
    # ============================================
    # Status
    # ============================================
    
    def get_stream_status(
        self,
        exchange: Optional[ExchangeId] = None,
        stream_type: Optional[StreamType] = None
    ) -> Dict[str, Any]:
        """Get status of streams"""
        if exchange and stream_type:
            handler = self._handlers.get(exchange, {}).get(stream_type)
            if handler:
                return handler.get_status()
            return {"status": "NOT_FOUND"}
        
        if exchange:
            return {
                st.value: handler.get_status()
                for st, handler in self._handlers.get(exchange, {}).items()
            }
        
        return {
            ex.value: {
                st.value: handler.get_status()
                for st, handler in handlers.items()
            }
            for ex, handlers in self._handlers.items()
        }
    
    def get_active_streams(self) -> List[Dict[str, Any]]:
        """Get list of active streams"""
        active = []
        for exchange, handlers in self._handlers.items():
            for stream_type, handler in handlers.items():
                if handler.status == StreamStatus.CONNECTED:
                    active.append(handler.get_status())
        return active
    
    # ============================================
    # Simulated Data (Demo Mode)
    # ============================================
    
    async def _simulate_data(self) -> None:
        """Simulate market data for demo purposes"""
        import random
        
        base_prices = {
            "BTCUSDT": 45000.0,
            "ETHUSDT": 2500.0,
            "SOLUSDT": 100.0
        }
        
        while True:
            await asyncio.sleep(1)  # Update every second
            
            for exchange, handlers in self._handlers.items():
                for stream_type, handler in handlers.items():
                    if handler.status != StreamStatus.CONNECTED:
                        continue
                    
                    for symbol in handler.symbols:
                        if stream_type == StreamType.TICKER:
                            base_price = base_prices.get(symbol, 100.0)
                            price_change = random.uniform(-0.001, 0.001)
                            new_price = base_price * (1 + price_change)
                            base_prices[symbol] = new_price
                            
                            ticker_data = {
                                "type": "ticker",
                                "exchange": exchange.value,
                                "symbol": symbol,
                                "last_price": round(new_price, 2),
                                "bid_price": round(new_price * 0.9999, 2),
                                "ask_price": round(new_price * 1.0001, 2),
                                "volume_24h": random.uniform(1000, 10000),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            
                            await handler.notify(ticker_data)
                            
                            # Also notify global callbacks
                            for cb in self._global_callbacks.get(StreamType.TICKER, []):
                                try:
                                    if asyncio.iscoroutinefunction(cb):
                                        await cb(ticker_data)
                                    else:
                                        cb(ticker_data)
                                except Exception as e:
                                    print(f"Global callback error: {e}")
                        
                        elif stream_type == StreamType.ORDERBOOK:
                            base_price = base_prices.get(symbol, 100.0)
                            
                            # Generate orderbook
                            bids = []
                            asks = []
                            for i in range(10):
                                bid_price = base_price * (1 - 0.0001 * (i + 1))
                                ask_price = base_price * (1 + 0.0001 * (i + 1))
                                bids.append({"price": round(bid_price, 2), "size": round(random.uniform(0.1, 5), 3)})
                                asks.append({"price": round(ask_price, 2), "size": round(random.uniform(0.1, 5), 3)})
                            
                            orderbook_data = {
                                "type": "orderbook",
                                "exchange": exchange.value,
                                "symbol": symbol,
                                "bids": bids,
                                "asks": asks,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            
                            await handler.notify(orderbook_data)
    
    async def shutdown(self) -> None:
        """Shutdown manager"""
        if self._simulate_task:
            self._simulate_task.cancel()
            try:
                await self._simulate_task
            except asyncio.CancelledError:
                pass
        
        await self.stop_all_streams()


# Global instance
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get or create global WebSocket manager"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
