"""
Binance Market Data Provider (sync)

Uses Binance US public API (no auth required).
Native 4h and 1d support — no aggregation hacks.

Rate limit: ~1200 req/min (public).
We add 100ms delay between requests.
"""

import time
import threading
from typing import List, Dict, Any, Optional

import httpx

from .provider import MarketDataProvider


# Binance kline intervals
_TF_MAP = {
    "4H": "4h",
    "1D": "1d",
    "1H": "1h",
}

# Cache: key = "BTCUSDT:4H" → (timestamp, candles)
_cache: Dict[str, tuple] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 300  # 5 minutes


def _normalize_symbol(symbol: str) -> str:
    """
    Normalize symbol to Binance format: BTCUSDT.
    
    Accepts: BTC, btc, BTCUSDT, btcusdt, BTC-USD
    """
    s = symbol.upper().replace("-USD", "").replace("-USDT", "")
    if not s.endswith("USDT"):
        s = s + "USDT"
    return s


class BinanceProvider(MarketDataProvider):
    """
    Sync Binance US data provider.
    
    - Uses public API (no keys)
    - Native 4h, 1d timeframes
    - Thread-safe cache (5 min TTL)
    - Rate-limited (100ms between requests)
    """
    
    BASE_URL = "https://api.binance.us/api/v3"
    
    def __init__(self):
        self._last_request_time = 0.0
        self._rate_limit_ms = 100  # ms between requests
    
    def get_provider_name(self) -> str:
        return "binance_us"
    
    def supports_symbol(self, symbol: str) -> bool:
        return symbol.upper().endswith("USDT")
    
    def supports_timeframe(self, timeframe: str) -> bool:
        return timeframe.upper() in _TF_MAP
    
    def get_last_price(self, symbol: str, timeframe: str = "4h") -> Optional[float]:
        """
        Get the most recent close price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "BTC")
            timeframe: Timeframe context (default: "4h")
        
        Returns:
            Latest close price or None if unavailable
        
        Note: Uses get_candles with limit=1 to fetch latest candle.
              This is a sync method but can be called with await in async context.
              For intraday/mark-price use cases prefer ``get_ticker_price``
              which bypasses the 5-min candle cache and is interval-agnostic.
        """
        try:
            # Short-timeframe fallback: if the requested TF is not in the
            # kline map (e.g. "1m"/"30s") transparently serve the real-time
            # ticker. Keeps the mark-price updater happy without special
            # casing at the call site.
            if timeframe and timeframe.upper() not in _TF_MAP:
                return self.get_ticker_price(symbol)
            candles = self.get_candles(symbol, timeframe, limit=1)
            if candles and len(candles) > 0:
                return candles[-1].get("close")
            return None
        except Exception as e:
            print(f"[BinanceProvider] Error getting last price for {symbol}: {e}")
            return None

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        Real-time last trade price via Binance US ``/ticker/price`` endpoint.

        This is the canonical mark-price source:
          * no interval,
          * no cache (always fresh),
          * single-symbol round-trip is ~50 ms.

        Used by ``mark_price_updater`` (Phase closing-loop.MARK) to refresh
        ``trading_cases.mark_price`` every ~8 s. Returns ``None`` on any
        transport / parse error so the caller can skip gracefully.
        """
        sym_upper = _normalize_symbol(symbol)
        url = f"{self.BASE_URL}/ticker/price"
        try:
            self._rate_limit()
            resp = httpx.get(url, params={"symbol": sym_upper}, timeout=10)
            if resp.status_code != 200:
                print(
                    f"[BinanceProvider] ticker/price HTTP {resp.status_code} for {sym_upper}"
                )
                return None
            data = resp.json()
            price_str = (data or {}).get("price")
            if price_str is None:
                return None
            price = float(price_str)
            return price if price > 0 else None
        except httpx.TimeoutException:
            print(f"[BinanceProvider] ticker/price timeout for {sym_upper}")
            return None
        except Exception as e:
            print(f"[BinanceProvider] ticker/price error for {sym_upper}: {e}")
            return None
    
    async def get_last_price_async(self, symbol: str, timeframe: str = "4h") -> Optional[float]:
        """Async wrapper for get_last_price (runs sync code in executor)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_last_price, symbol, timeframe)
    
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Fetch candles from Binance US.
        
        Uses cache to avoid hammering API during batch scans.
        Accepts: BTC, BTCUSDT, btcusdt → normalized to BTCUSDT
        """
        tf_upper = timeframe.upper()
        sym_upper = _normalize_symbol(symbol)
        
        # Check cache first
        cache_key = f"{sym_upper}:{tf_upper}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached[-limit:] if len(cached) > limit else cached
        
        # Map timeframe
        interval = _TF_MAP.get(tf_upper)
        if not interval:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(_TF_MAP.keys())}")
        
        # Rate limit
        self._rate_limit()
        
        # Fetch
        candles = self._fetch(sym_upper, interval, limit)
        
        # Cache result
        self._set_cached(cache_key, candles)
        
        return candles
    
    def _fetch(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Raw HTTP fetch from Binance US."""
        url = f"{self.BASE_URL}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),
        }
        
        try:
            resp = httpx.get(url, params=params, timeout=15)
            
            if resp.status_code != 200:
                print(f"[BinanceProvider] HTTP {resp.status_code} for {symbol}:{interval}")
                return []
            
            raw = resp.json()
            if not isinstance(raw, list):
                print(f"[BinanceProvider] Unexpected response for {symbol}: {str(raw)[:200]}")
                return []
            
            # Convert Binance kline format to unified candle format
            candles = []
            for k in raw:
                candles.append({
                    "time": int(k[0]) // 1000,  # ms → seconds
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            
            # Sort by time ascending (Binance already returns ascending, but be safe)
            candles.sort(key=lambda c: c["time"])
            
            return candles
        
        except httpx.TimeoutException:
            print(f"[BinanceProvider] Timeout for {symbol}:{interval}")
            return []
        except Exception as e:
            print(f"[BinanceProvider] Error for {symbol}:{interval}: {e}")
            return []
    
    def _rate_limit(self):
        """Simple rate limiter — 100ms between requests."""
        now = time.time()
        elapsed_ms = (now - self._last_request_time) * 1000
        if elapsed_ms < self._rate_limit_ms:
            time.sleep((self._rate_limit_ms - elapsed_ms) / 1000)
        self._last_request_time = time.time()
    
    def _get_cached(self, key: str) -> Optional[List[Dict]]:
        """Get from cache if fresh."""
        with _cache_lock:
            if key in _cache:
                ts, data = _cache[key]
                if time.time() - ts < _CACHE_TTL:
                    return data
                else:
                    del _cache[key]
        return None
    
    def _set_cached(self, key: str, data: List[Dict]):
        """Store in cache."""
        with _cache_lock:
            _cache[key] = (time.time(), data)


# Singleton
_provider: Optional[BinanceProvider] = None


def get_market_data_provider() -> BinanceProvider:
    """Get singleton market data provider."""
    global _provider
    if _provider is None:
        _provider = BinanceProvider()
    return _provider
