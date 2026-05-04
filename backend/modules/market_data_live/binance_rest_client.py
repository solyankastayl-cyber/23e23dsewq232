"""Binance REST Client for Historical Klines"""

import aiohttp
import logging

logger = logging.getLogger(__name__)


class BinanceRestClient:
    """Binance REST API client for market data."""
    
    def __init__(self, base_url: str = "https://data-api.binance.vision"):
        self.base_url = base_url.rstrip("/")
    
    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200):
        """
        Fetch OHLCV klines from Binance.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Timeframe (e.g., "1h", "4h", "1d")
            limit: Number of candles (max 1000)
        
        Returns:
            List of candle dicts
        """
        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            
            candles = []
            for row in data:
                candles.append({
                    "open_time": row[0],
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                    "close_time": row[6],
                    "is_closed": True,
                })
            
            logger.info(f"[BinanceREST] Fetched {len(candles)} klines for {symbol} {interval}")
            return candles
        
        except Exception as e:
            logger.error(f"[BinanceREST] Error fetching klines for {symbol}: {e}")
            return []
