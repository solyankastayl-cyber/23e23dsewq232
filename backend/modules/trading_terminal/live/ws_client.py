"""
Binance WebSocket Client for Live Microstructure Data
Handles: depth@100ms, aggTrade, bookTicker streams
Production-ready with reconnect logic, buffering, and snapshot sync
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Callable, List
from datetime import datetime, timezone
import aiohttp

logger = logging.getLogger(__name__)


class BinanceWSClient:
    """
    Binance WebSocket Client with automatic reconnection and multiplexed streams.
    
    Streams:
    - depth@100ms: Orderbook depth updates (100ms interval)
    - aggTrade: Aggregated trades
    - bookTicker: Best bid/ask price and quantity
    """
    
    BASE_URL = "wss://stream.binance.com:9443/stream"
    REST_BASE = "https://api.binance.com/api/v3"
    
    def __init__(self, symbol: str):
        self.symbol = symbol.lower()
        self.symbol_upper = symbol.upper()
        
        # Stream names
        self.depth_stream = f"{self.symbol}@depth@100ms"
        self.trade_stream = f"{self.symbol}@aggTrade"
        self.ticker_stream = f"{self.symbol}@bookTicker"
        
        # State
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.connected = False
        self.reconnect_delay = 1  # seconds
        self.max_reconnect_delay = 60
        
        # Callbacks
        self._on_depth: Optional[Callable] = None
        self._on_trade: Optional[Callable] = None
        self._on_ticker: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        
        # Stats
        self.messages_received = 0
        self.last_message_time: Optional[datetime] = None
        self.connection_count = 0
    
    @property
    def streams(self) -> List[str]:
        return [self.depth_stream, self.trade_stream, self.ticker_stream]
    
    @property
    def stream_url(self) -> str:
        streams_param = "/".join(self.streams)
        return f"{self.BASE_URL}?streams={streams_param}"
    
    def on_depth(self, callback: Callable):
        """Register callback for depth updates"""
        self._on_depth = callback
    
    def on_trade(self, callback: Callable):
        """Register callback for trade updates"""
        self._on_trade = callback
    
    def on_ticker(self, callback: Callable):
        """Register callback for ticker updates"""
        self._on_ticker = callback
    
    def on_connect(self, callback: Callable):
        """Register callback for connection events"""
        self._on_connect = callback
    
    def on_disconnect(self, callback: Callable):
        """Register callback for disconnection events"""
        self._on_disconnect = callback
    
    async def get_orderbook_snapshot(self, limit: int = 100) -> Optional[Dict]:
        """
        Get REST API snapshot for orderbook initialization.
        CRITICAL: Must sync with WebSocket updates using lastUpdateId.
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.REST_BASE}/depth?symbol={self.symbol_upper}&limit={limit}"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"[WS] Got orderbook snapshot for {self.symbol_upper}, lastUpdateId: {data.get('lastUpdateId')}")
                    return data
                else:
                    logger.error(f"[WS] Failed to get snapshot: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"[WS] Snapshot error: {e}")
            return None
    
    async def connect(self):
        """
        Establish WebSocket connection with automatic reconnection.
        """
        self.running = True
        
        while self.running:
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()
                
                logger.info(f"[WS] Connecting to Binance: {self.symbol_upper}")
                
                async with self.session.ws_connect(
                    self.stream_url,
                    heartbeat=30,
                    receive_timeout=60
                ) as ws:
                    self.ws = ws
                    self.connected = True
                    self.connection_count += 1
                    self.reconnect_delay = 1  # Reset on successful connection
                    
                    logger.info(f"[WS] Connected to Binance {self.symbol_upper} (attempt #{self.connection_count})")
                    
                    if self._on_connect:
                        await self._on_connect()
                    
                    # Process messages
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message(msg.data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"[WS] Error: {ws.exception()}")
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.warning(f"[WS] Connection closed")
                            break
                
            except asyncio.CancelledError:
                logger.info(f"[WS] Connection cancelled for {self.symbol_upper}")
                break
            except Exception as e:
                logger.error(f"[WS] Connection error: {e}")
            
            # Disconnected
            self.connected = False
            self.ws = None
            
            if self._on_disconnect:
                await self._on_disconnect()
            
            if self.running:
                logger.info(f"[WS] Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    async def _handle_message(self, data: str):
        """Process incoming WebSocket message"""
        try:
            msg = json.loads(data)
            self.messages_received += 1
            self.last_message_time = datetime.now(timezone.utc)
            
            stream = msg.get("stream", "")
            payload = msg.get("data", {})
            
            if self.depth_stream in stream and self._on_depth:
                await self._on_depth(payload)
            elif self.trade_stream in stream and self._on_trade:
                await self._on_trade(payload)
            elif self.ticker_stream in stream and self._on_ticker:
                await self._on_ticker(payload)
                
        except json.JSONDecodeError as e:
            logger.error(f"[WS] JSON parse error: {e}")
        except Exception as e:
            logger.error(f"[WS] Message handling error: {e}")
    
    async def disconnect(self):
        """Gracefully disconnect from WebSocket"""
        self.running = False
        
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        if self.session and not self.session.closed:
            await self.session.close()
        
        self.ws = None
        self.session = None
        self.connected = False
        
        logger.info(f"[WS] Disconnected from {self.symbol_upper}")
    
    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            "symbol": self.symbol_upper,
            "connected": self.connected,
            "messages_received": self.messages_received,
            "last_message": self.last_message_time.isoformat() if self.last_message_time else None,
            "connection_count": self.connection_count,
            "streams": self.streams
        }
