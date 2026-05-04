"""
Market Data Provider — Abstract Interface

All market data goes through this layer.
No direct API calls from workers/adapters.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class MarketDataProvider(ABC):
    """
    Abstract base for all market data providers.
    
    Contract:
        get_candles(symbol, timeframe, limit) → List[candle_dict]
    
    Candle format (unified):
        {
            "time": int (unix seconds),
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float,
        }
    """
    
    @abstractmethod
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV candles.
        
        Args:
            symbol: Internal symbol format (e.g., BTCUSDT)
            timeframe: Normalized timeframe (4H, 1D)
            limit: Number of candles
        
        Returns:
            List of candle dicts sorted by time ascending
        """
        ...
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier."""
        ...
    
    @abstractmethod
    def supports_symbol(self, symbol: str) -> bool:
        """Check if provider supports this symbol."""
        ...
    
    @abstractmethod
    def supports_timeframe(self, timeframe: str) -> bool:
        """Check if provider natively supports this timeframe."""
        ...


# Normalized timeframe grid — what the system works with
SYSTEM_TIMEFRAMES = ["4H", "1D"]
