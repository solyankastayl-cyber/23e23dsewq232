"""Market Data Service — Unified Source of Truth for Candles"""

import logging
from collections import defaultdict
from typing import Optional

from modules.market_data_live.binance_rest_client import BinanceRestClient
from modules.market_data_live.binance_ws_feed import BinanceWSFeed

logger = logging.getLogger(__name__)


class MarketDataService:
    """Unified market data service with REST bootstrap + WebSocket updates."""
    
    def __init__(self):
        self.rest = BinanceRestClient()
        self.cache = defaultdict(list)
        self.ws = BinanceWSFeed(self._on_kline, testnet=False)
        logger.info("[MarketDataService] Initialized")
    
    def _key(self, symbol: str, interval: str):
        """Generate cache key."""
        return f"{symbol.upper()}:{interval}"
    
    async def bootstrap(self, symbols: list[str], interval: str = "4h", limit: int = 200):
        """Bootstrap historical candles via REST API.
        
        Args:
            symbols: List of trading pairs
            interval: Timeframe
            limit: Number of historical candles
        """
        logger.info(f"[MarketDataService] Bootstrapping {len(symbols)} symbols with {limit} candles")
        
        for symbol in symbols:
            try:
                candles = await self.rest.get_klines(symbol, interval=interval, limit=limit)
                if candles:
                    self.cache[self._key(symbol, interval)] = candles
                    logger.info(f"[MarketDataService] ✅ {symbol}: {len(candles)} candles cached")
            except Exception as e:
                logger.error(f"[MarketDataService] Failed to bootstrap {symbol}: {e}")
    
    async def _on_kline(self, candle: dict):
        """WebSocket kline callback — update cache."""
        key = self._key(candle["symbol"], candle["interval"])
        arr = self.cache[key]
        
        if not arr:
            arr.append(candle)
            self.cache[key] = arr
            return
        
        # Update last candle if same timestamp, otherwise append
        if arr[-1]["open_time"] == candle["open_time"]:
            arr[-1] = candle
        else:
            arr.append(candle)
        
        # Keep only last 300 candles
        self.cache[key] = arr[-300:]
        
        if candle["is_closed"]:
            logger.info(f"[MarketDataService] 🕯 {candle['symbol']} {candle['interval']} closed @ {candle['close']}")
    
    async def start_stream(self, symbols: list[str], interval: str = "4h"):
        """Start live WebSocket feed.
        
        Args:
            symbols: List of trading pairs
            interval: Timeframe
        """
        await self.ws.start(symbols, interval)
        logger.info(f"[MarketDataService] 📡 WebSocket stream started for {symbols} {interval}")
    
    async def stop_stream(self):
        """Stop WebSocket feed."""
        await self.ws.stop()
    
    async def get_candles(self, symbol: str, timeframe: str = "4h", limit: int = 120):
        """Get candles from cache.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            limit: Number of candles
        
        Returns:
            List of candle dicts
        """
        key = self._key(symbol, timeframe)
        rows = self.cache.get(key, [])
        return rows[-limit:]
    
    async def get_last_price(self, symbol: str, timeframe: str = "4h") -> Optional[float]:
        """Get last close price.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
        
        Returns:
            Last close price or None
        """
        candles = await self.get_candles(symbol, timeframe=timeframe, limit=1)
        if not candles:
            return None
        return candles[-1]["close"]


# Global instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get global market data service instance."""
    global _market_data_service
    if _market_data_service is None:
        raise ValueError("MarketDataService not initialized")
    return _market_data_service


def init_market_data_service() -> MarketDataService:
    """Initialize global market data service."""
    global _market_data_service
    _market_data_service = MarketDataService()
    return _market_data_service
