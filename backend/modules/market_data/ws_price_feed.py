"""WebSocket Price Feed — PHASE 1: REAL MARKET DATA

Binance Spot WS stream (!ticker@arr) → in-memory price cache.

Features:
- Singleton: единственный WS connection для всех клиентов
- In-memory cache: {symbol: {price, timestamp, source}}
- Auto-reconnect с exponential backoff
- Heartbeat/keepalive
- Graceful shutdown

Architecture:
- WS stream: wss://stream.binance.com:9443/ws/!ticker@arr
- Message: {"e":"24hrTicker","s":"BTCUSDT","c":"67123.45",...}
- Cache: простой dict с lock для thread-safety
- Lifecycle: start() → background task → stop()
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class WSPriceFeed:
    """WebSocket Price Feed — Singleton."""
    
    _instance: Optional['WSPriceFeed'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        # WS config
        # Using combined stream for specific symbols (lowercase)
        symbols = ["btcusdt", "ethusdt", "solusdt", "bnbusdt", "xrpusdt", "adausdt", "avaxusdt", "linkusdt", "dogeusdt"]
        streams = [f"{s}@ticker" for s in symbols]
        self.ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        
        # Price cache: {symbol: {price: float, timestamp: float, source: str}}
        self.cache: Dict[str, dict] = {}
        self.cache_lock = asyncio.Lock()
        
        # State
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_update = 0.0
        
        # Reconnect config
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        self.backoff_multiplier = 2.0
    
    @classmethod
    async def get_instance(cls) -> 'WSPriceFeed':
        """Get singleton instance."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    async def start(self):
        """Start WS feed in background."""
        if self.running:
            logger.warning("[WSPriceFeed] Already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("[WSPriceFeed] Started")
    
    async def stop(self):
        """Stop WS feed gracefully."""
        if not self.running:
            return
        
        self.running = False
        
        if self.ws:
            await self.ws.close()
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("[WSPriceFeed] Stopped")
    
    async def _run(self):
        """Main WS loop with reconnect."""
        current_delay = self.reconnect_delay
        
        while self.running:
            try:
                await self._connect_and_listen()
                # Успешный disconnect → reset delay
                current_delay = self.reconnect_delay
            
            except (ConnectionClosed, WebSocketException) as e:
                logger.warning(f"[WSPriceFeed] Connection error: {e}. Reconnecting in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay = min(current_delay * self.backoff_multiplier, self.max_reconnect_delay)
            
            except Exception as e:
                logger.error(f"[WSPriceFeed] Unexpected error: {e}", exc_info=True)
                await asyncio.sleep(current_delay)
                current_delay = min(current_delay * self.backoff_multiplier, self.max_reconnect_delay)
    
    async def _connect_and_listen(self):
        """Connect to WS and listen for messages."""
        logger.info(f"[WSPriceFeed] Connecting to {self.ws_url}...")
        
        async with websockets.connect(
            self.ws_url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self.ws = ws
            logger.info("[WSPriceFeed] ✅ Connected")
            
            async for message in ws:
                if not self.running:
                    break
                
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(f"[WSPriceFeed] Error processing message: {e}", exc_info=True)
    
    async def _process_message(self, raw_message: str):
        """Process ticker message.
        
        Combined stream format:
        {
            "stream": "btcusdt@ticker",
            "data": {
                "e": "24hrTicker",
                "E": 1672515782136,
                "s": "BTCUSDT",
                "c": "16523.45",  // close price (current price)
                ...
            }
        }
        
        Or single stream:
        {
            "e": "24hrTicker",
            "s": "BTCUSDT",
            "c": "16523.45",
            ...
        }
        """
        msg = json.loads(raw_message)
        
        # Handle combined stream format
        if "stream" in msg and "data" in msg:
            data = msg["data"]
        else:
            data = msg
        
        # Filter только ticker события
        if data.get("e") != "24hrTicker":
            return
        
        symbol = data.get("s")
        price_str = data.get("c")
        
        if not symbol or not price_str:
            return
        
        try:
            price = float(price_str)
        except (ValueError, TypeError):
            logger.warning(f"[WSPriceFeed] Invalid price for {symbol}: {price_str}")
            return
        
        # Update cache (symbol is UPPERCASE from Binance)
        async with self.cache_lock:
            self.cache[symbol] = {
                "price": price,
                "timestamp": time.time(),
                "source": "WS",
            }
            self.last_update = time.time()
        
        logger.debug(f"[WSPriceFeed] {symbol} = ${price:.2f}")
    
    async def get_price(self, symbol: str) -> Optional[dict]:
        """Get cached price for symbol.
        
        Returns:
            {price: float, timestamp: float, source: str} or None
        """
        async with self.cache_lock:
            return self.cache.get(symbol)
    
    async def get_all_prices(self) -> Dict[str, dict]:
        """Get all cached prices."""
        async with self.cache_lock:
            return self.cache.copy()
    
    def get_status(self) -> dict:
        """Get feed status."""
        return {
            "running": self.running,
            "connected": self.ws is not None and self.ws.open if self.ws else False,
            "cached_symbols": len(self.cache),
            "last_update": self.last_update,
            "age": time.time() - self.last_update if self.last_update > 0 else None,
        }


# Singleton accessor
async def get_ws_price_feed() -> WSPriceFeed:
    """Get global WS price feed instance."""
    return await WSPriceFeed.get_instance()
