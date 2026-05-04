"""
Binance REST API Client for Microstructure Data
Provides fallback when WebSocket is not available.
"""

import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BinanceRESTClient:
    """
    Binance REST API client for orderbook and trade data.
    Used as fallback when WebSocket is unavailable.
    """
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0
    
    async def _ensure_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """
        Get orderbook snapshot.
        Returns: {"bids": [[price, qty], ...], "asks": [...], "lastUpdateId": ...}
        """
        await self._ensure_session()
        
        try:
            url = f"{self.BASE_URL}/depth?symbol={symbol.upper()}&limit={limit}"
            async with self.session.get(url) as resp:
                self._request_count += 1
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"[REST] Orderbook error: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"[REST] Orderbook request failed: {e}")
            return None
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> Optional[List]:
        """
        Get recent trades.
        Returns: [{"price": "...", "qty": "...", "time": ..., "isBuyerMaker": bool}, ...]
        """
        await self._ensure_session()
        
        try:
            url = f"{self.BASE_URL}/trades?symbol={symbol.upper()}&limit={limit}"
            async with self.session.get(url) as resp:
                self._request_count += 1
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"[REST] Trades error: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"[REST] Trades request failed: {e}")
            return None
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get 24h ticker.
        Returns price, volume, etc.
        """
        await self._ensure_session()
        
        try:
            url = f"{self.BASE_URL}/ticker/24hr?symbol={symbol.upper()}"
            async with self.session.get(url) as resp:
                self._request_count += 1
                if resp.status == 200:
                    return await resp.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"[REST] Ticker request failed: {e}")
            return None
    
    async def get_book_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get best bid/ask (book ticker).
        Returns: {"bidPrice": "...", "bidQty": "...", "askPrice": "...", "askQty": "..."}
        """
        await self._ensure_session()
        
        try:
            url = f"{self.BASE_URL}/ticker/bookTicker?symbol={symbol.upper()}"
            async with self.session.get(url) as resp:
                self._request_count += 1
                if resp.status == 200:
                    return await resp.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"[REST] Book ticker request failed: {e}")
            return None
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


# Global client instance
_rest_client: Optional[BinanceRESTClient] = None


async def get_rest_client() -> BinanceRESTClient:
    global _rest_client
    if _rest_client is None:
        _rest_client = BinanceRESTClient()
    return _rest_client


async def get_live_micro_rest(symbol: str) -> Dict:
    """
    Get microstructure data using REST API (polling fallback).
    """
    client = await get_rest_client()
    
    try:
        # Get orderbook
        orderbook = await client.get_orderbook(symbol, limit=20)
        if not orderbook:
            return _error_response(symbol, "Failed to get orderbook")
        
        # Parse orderbook
        bids = [(float(b[0]), float(b[1])) for b in orderbook.get("bids", [])]
        asks = [(float(a[0]), float(a[1])) for a in orderbook.get("asks", [])]
        
        if not bids or not asks:
            return _error_response(symbol, "Empty orderbook")
        
        # Calculate metrics
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_bps = (spread / mid_price) * 10000
        
        # Calculate imbalance (top 10 levels)
        bid_vol = sum(qty for _, qty in bids[:10])
        ask_vol = sum(qty for _, qty in asks[:10])
        total_vol = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0
        
        # Calculate depth in USD
        bid_depth_usd = sum(price * qty for price, qty in bids[:10])
        ask_depth_usd = sum(price * qty for price, qty in asks[:10])
        
        # Liquidity score (normalized to ~$5M typical)
        liquidity_score = min((bid_depth_usd + ask_depth_usd) / 10_000_000, 1.0)
        
        # Liquidity state
        if liquidity_score < 0.1:
            liquidity_state = "thin"
        elif liquidity_score < 0.3:
            liquidity_state = "light"
        elif imbalance > 0.3:
            liquidity_state = "strong_bid"
        elif imbalance < -0.3:
            liquidity_state = "strong_ask"
        else:
            liquidity_state = "balanced"
        
        # Micro state
        if liquidity_score < 0.1 or spread_bps > 5.0:
            state = "hostile"
            confidence = 0.3
        elif spread_bps > 3.0 or liquidity_score < 0.2:
            state = "caution"
            confidence = 0.5
        elif abs(imbalance) > 0.2 and liquidity_score > 0.4 and spread_bps < 2.0:
            state = "favorable"
            confidence = min(0.9, 0.7 + abs(imbalance) * 0.2)
        else:
            state = "neutral"
            confidence = 0.6
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "REST",
            "imbalance": round(imbalance, 3),
            "spread": round(spread, 4),
            "spread_bps": round(spread_bps, 2),
            "liquidity_score": round(liquidity_score, 3),
            "liquidity_state": liquidity_state,
            "state": state,
            "confidence": round(confidence, 2),
            "sweep_status": "none",
            "bid_volume": round(bid_vol, 4),
            "ask_volume": round(ask_vol, 4),
            "trade_pressure": "unknown",  # Would need recent trades
            "best_bid": round(best_bid, 2),
            "best_ask": round(best_ask, 2),
            "mid_price": round(mid_price, 2),
            "bid_depth_usd": round(bid_depth_usd, 2),
            "ask_depth_usd": round(ask_depth_usd, 2)
        }
        
    except Exception as e:
        logger.error(f"[REST] Error getting micro data: {e}")
        return _error_response(symbol, str(e))


def _error_response(symbol: str, error: str) -> Dict:
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "ERROR",
        "error": error,
        "imbalance": 0,
        "spread": 0,
        "spread_bps": 0,
        "liquidity_score": 0,
        "liquidity_state": "unknown",
        "state": "error",
        "confidence": 0,
        "sweep_status": "none",
        "bid_volume": 0,
        "ask_volume": 0,
        "trade_pressure": "unknown",
        "best_bid": 0,
        "best_ask": 0,
        "mid_price": 0
    }
