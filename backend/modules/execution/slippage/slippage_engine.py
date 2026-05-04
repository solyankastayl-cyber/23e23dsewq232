"""
Slippage Engine Facade - PHASE 5.3
==================================

Unified interface for slippage analysis.
"""

from typing import Dict, Optional, Any
from datetime import datetime


class SlippageEngine:
    """
    Unified interface for slippage analysis.
    Provides simple slippage estimation without external dependencies.
    """
    
    def __init__(self):
        # In-memory cache for stats
        self._stats_cache: Dict[str, Dict] = {}
    
    def estimate_slippage(
        self,
        exchange: str,
        symbol: str,
        side: str,
        size: float
    ) -> Dict[str, Any]:
        """
        Estimate expected slippage for an order.
        """
        # Simple size-based estimation
        # Larger orders = more slippage
        base_slippage = 2.0  # Base 2 bps
        
        # Size factor (larger orders have more slippage)
        if symbol.endswith("USDT"):
            if "BTC" in symbol:
                size_factor = size / 10  # 10 BTC = 1x multiplier
            elif "ETH" in symbol:
                size_factor = size / 100  # 100 ETH = 1x
            else:
                size_factor = size / 1000  # 1000 units = 1x
        else:
            size_factor = size / 100
        
        estimated_slippage = base_slippage * (1 + size_factor * 0.5)
        
        # Exchange adjustment
        exchange_factor = {
            "BINANCE": 1.0,
            "BYBIT": 1.1,
            "OKX": 1.05
        }.get(exchange.upper(), 1.0)
        
        estimated_slippage *= exchange_factor
        
        return {
            "exchange": exchange,
            "symbol": symbol,
            "side": side,
            "size": size,
            "expected_slippage_bps": round(estimated_slippage, 2),
            "confidence": 0.7,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_slippage_stats(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get slippage statistics for exchange/symbol."""
        cache_key = f"{exchange}:{symbol}"
        
        # Return cached or default stats
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]
        
        # Default stats
        return {
            "exchange": exchange,
            "symbol": symbol,
            "avg_slippage_bps": 3.0,
            "max_slippage_bps": 15.0,
            "min_slippage_bps": 0.5,
            "sample_count": 100,
            "fill_rate": 0.98,
            "trend": "STABLE"
        }
    
    def record_execution(
        self,
        exchange: str,
        symbol: str,
        side: str,
        size: float,
        expected_price: float,
        actual_price: float
    ) -> Dict[str, Any]:
        """Record execution for slippage tracking"""
        slippage_bps = abs(actual_price - expected_price) / expected_price * 10000
        
        # Update cache
        cache_key = f"{exchange}:{symbol}"
        if cache_key not in self._stats_cache:
            self._stats_cache[cache_key] = {
                "exchange": exchange,
                "symbol": symbol,
                "avg_slippage_bps": slippage_bps,
                "max_slippage_bps": slippage_bps,
                "min_slippage_bps": slippage_bps,
                "sample_count": 1,
                "fill_rate": 1.0,
                "trend": "STABLE"
            }
        else:
            stats = self._stats_cache[cache_key]
            stats["sample_count"] += 1
            stats["avg_slippage_bps"] = (
                stats["avg_slippage_bps"] * 0.9 + slippage_bps * 0.1
            )
            stats["max_slippage_bps"] = max(stats["max_slippage_bps"], slippage_bps)
            stats["min_slippage_bps"] = min(stats["min_slippage_bps"], slippage_bps)
        
        return {
            "recorded": True,
            "slippage_bps": round(slippage_bps, 2)
        }


# Global instance
_slippage_engine: Optional[SlippageEngine] = None


def get_slippage_engine() -> SlippageEngine:
    """Get or create global slippage engine"""
    global _slippage_engine
    if _slippage_engine is None:
        _slippage_engine = SlippageEngine()
    return _slippage_engine
