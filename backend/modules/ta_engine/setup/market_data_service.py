"""
Market Data Service
====================
Fetches REAL market data from Coinbase Exchange API.
Caches candles in MongoDB for performance.
"""

import os
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timezone

from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

# Coinbase Exchange API (no auth required for public data)
COINBASE_API_URL = "https://api.exchange.coinbase.com"


class MarketDataService:
    """Fetches real market data from Coinbase and caches in MongoDB."""
    
    # Symbol mapping: internal -> Coinbase format
    SYMBOL_MAP = {
        "BTCUSDT": "BTC-USD",
        "ETHUSDT": "ETH-USD",
        "SOLUSDT": "SOL-USD",
        "AVAXUSDT": "AVAX-USD",
        "LINKUSDT": "LINK-USD",
        "DOTUSDT": "DOT-USD",
        "ADAUSDT": "ADA-USD",
        "XRPUSDT": "XRP-USD",
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "BTCUSD": "BTC-USD",
        "ETHUSD": "ETH-USD",
        "SOLUSD": "SOL-USD",
    }
    
    # Timeframe to Coinbase granularity (in seconds)
    GRANULARITY_MAP = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "7d": 86400,  # Use daily
        "30d": 86400,
        "180d": 86400,
        "1y": 86400,
    }
    
    # Cache duration in minutes
    CACHE_DURATION = {
        "1m": 1,
        "5m": 5,
        "15m": 10,
        "1h": 30,
        "4h": 60,
        "1d": 240,
    }
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self._http_client: Optional[httpx.Client] = None
    
    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to internal format."""
        s = symbol.upper().replace("-", "").replace("/", "")
        if s.endswith("USD") and not s.endswith("USDT"):
            s = s[:-3] + "USDT"
        if not s.endswith("USDT"):
            s = s + "USDT"
        return s

    @staticmethod
    def _to_internal_tf(timeframe: str) -> str:
        """Map canonical TF (1H, 4H, 1D, ...) → internal lowercase keys used here."""
        if not timeframe:
            return "1d"
        s = str(timeframe).strip()
        # internal maps use lowercase: 1m,5m,15m,1h,4h,1d,7d,30d,180d,1y
        return s.lower()
    
    def _get_coinbase_symbol(self, symbol: str) -> Optional[str]:
        """Convert internal symbol to Coinbase format."""
        norm = self._normalize_symbol(symbol)
        return self.SYMBOL_MAP.get(norm)
    
    def _is_cache_valid(self, symbol: str, timeframe: str) -> bool:
        """Check if cached data is still valid."""
        cache_minutes = self.CACHE_DURATION.get(timeframe, 60)
        
        latest = self.db.candles.find_one(
            {"symbol": symbol.upper(), "timeframe": timeframe},
            {"timestamp": 1},
            sort=[("timestamp", DESCENDING)]
        )
        
        if not latest:
            return False
        
        cached_time = latest.get("timestamp")
        if isinstance(cached_time, str):
            cached_time = datetime.fromisoformat(cached_time.replace("Z", "+00:00"))
        elif isinstance(cached_time, (int, float)):
            cached_time = datetime.fromtimestamp(cached_time / 1000 if cached_time > 1e12 else cached_time, tz=timezone.utc)
        
        if cached_time.tzinfo is None:
            cached_time = cached_time.replace(tzinfo=timezone.utc)
        
        cache_age = datetime.now(timezone.utc) - cached_time
        return cache_age.total_seconds() < cache_minutes * 60
    
    def _fetch_from_coinbase(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Fetch candles from Coinbase API."""
        client = self._get_http_client()
        coinbase_symbol = self._get_coinbase_symbol(symbol)
        
        if not coinbase_symbol:
            print(f"[MarketData] Symbol {symbol} not supported for Coinbase")
            return []
        
        granularity = self.GRANULARITY_MAP.get(timeframe, 86400)
        
        try:
            response = client.get(
                f"{COINBASE_API_URL}/products/{coinbase_symbol}/candles",
                params={"granularity": granularity}
            )
            response.raise_for_status()
            raw_candles = response.json()
            
            # Coinbase format: [[timestamp, low, high, open, close, volume], ...]
            # Sorted newest first, we need oldest first
            candles = []
            for row in raw_candles:
                if len(row) >= 6:
                    ts = row[0]
                    candles.append({
                        "symbol": self._normalize_symbol(symbol),
                        "timeframe": timeframe,
                        "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                        "open": float(row[3]),
                        "high": float(row[2]),
                        "low": float(row[1]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                        "source": "coinbase"
                    })
            
            # Sort by timestamp ascending
            candles.sort(key=lambda x: x["timestamp"])
            
            # Return last N candles
            candles = candles[-limit:] if len(candles) > limit else candles
            
            print(f"[MarketData] Got {len(candles)} candles from Coinbase for {symbol}")
            return candles
            
        except Exception as e:
            print(f"[MarketData] Coinbase error for {symbol}: {e}")
            return []
    
    def _save_to_cache(self, candles: List[Dict], symbol: str, timeframe: str) -> None:
        """Save candles to MongoDB cache."""
        if not candles:
            return
        
        for candle in candles:
            self.db.candles.update_one(
                {
                    "symbol": symbol.upper(),
                    "timeframe": timeframe,
                    "timestamp": candle["timestamp"]
                },
                {"$set": candle},
                upsert=True
            )
    
    def _get_from_cache(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Get candles from MongoDB cache."""
        cursor = self.db.candles.find(
            {"symbol": symbol.upper(), "timeframe": timeframe},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        candles = list(cursor)
        return list(reversed(candles))
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        """
        Get candles - tries cache first, then fetches from Coinbase.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "BTC", "ETH")
            timeframe: Timeframe (e.g., "1h", "4h", "1d")
            limit: Number of candles to return
            
        Returns:
            List of candle dictionaries with OHLCV data
        """
        symbol = self._normalize_symbol(symbol)
        # Internal maps (GRANULARITY_MAP, CACHE_DURATION) use lowercase keys
        # while normalize_tf() emits canonical 1H/4H/1D. Map canonical → internal.
        timeframe = self._to_internal_tf(timeframe)
        
        # Check cache validity
        if self._is_cache_valid(symbol, timeframe):
            cached = self._get_from_cache(symbol, timeframe, limit)
            if len(cached) >= limit * 0.8:
                return cached[:limit]
        
        # Fetch fresh data from Coinbase
        fresh_candles = self._fetch_from_coinbase(symbol, timeframe, limit)
        
        if fresh_candles:
            self._save_to_cache(fresh_candles, symbol, timeframe)
            return fresh_candles[:limit]
        
        # Fallback to cache even if stale
        cached = self._get_from_cache(symbol, timeframe, limit)
        if cached:
            return cached
        
        print(f"[MarketData] Warning: No data available for {symbol} {timeframe}")
        return []
    
    def refresh_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        """Force refresh candles from exchange."""
        symbol = self._normalize_symbol(symbol)
        
        # Delete old cache
        self.db.candles.delete_many({
            "symbol": symbol.upper(),
            "timeframe": timeframe
        })
        
        # Fetch fresh
        return self.get_candles(symbol, timeframe, limit)
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price from Coinbase."""
        client = self._get_http_client()
        coinbase_symbol = self._get_coinbase_symbol(symbol)
        
        if not coinbase_symbol:
            return None
        
        try:
            response = client.get(f"{COINBASE_API_URL}/products/{coinbase_symbol}/ticker")
            response.raise_for_status()
            data = response.json()
            return float(data.get("price", 0))
        except Exception as e:
            print(f"[MarketData] Error getting price for {symbol}: {e}")
            return None
    
    def get_24h_stats(self, symbol: str) -> Optional[Dict]:
        """Get 24h statistics from Coinbase."""
        client = self._get_http_client()
        coinbase_symbol = self._get_coinbase_symbol(symbol)
        
        if not coinbase_symbol:
            return None
        
        try:
            response = client.get(f"{COINBASE_API_URL}/products/{coinbase_symbol}/ticker")
            response.raise_for_status()
            data = response.json()
            
            return {
                "symbol": self._normalize_symbol(symbol),
                "price": float(data.get("price", 0)),
                "volume_24h": float(data.get("volume", 0)),
                "bid": float(data.get("bid", 0)),
                "ask": float(data.get("ask", 0)),
            }
        except Exception as e:
            print(f"[MarketData] Error getting stats for {symbol}: {e}")
            return None


# Singleton
_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    global _service
    if _service is None:
        _service = MarketDataService()
    return _service


# CLI for testing
if __name__ == "__main__":
    service = get_market_data_service()
    
    print("Testing Coinbase data fetch...")
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    timeframes = ["4h", "1d"]
    
    for symbol in symbols:
        for tf in timeframes:
            print(f"\nFetching {symbol} {tf}...")
            candles = service.refresh_candles(symbol, tf, 50)
            if candles:
                print(f"  Got {len(candles)} candles from {candles[0].get('source', 'unknown')}")
                print(f"  Latest: ${candles[-1]['close']} at {candles[-1]['timestamp']}")
            else:
                print(f"  FAILED to get candles")
    
    # Test price endpoint
    price = service.get_latest_price("BTCUSDT")
    print(f"\nBTC Price: ${price}")
    
    print("\nDone!")
