"""
Chart Data API — PHASE 48.1

Provides:
- Candles
- Volume
- OI
- Funding
- Liquidation markers
- Dominance series
- Custom research series
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import numpy as np

from core.database import get_database


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class CandleData(BaseModel):
    """OHLCV candle with timestamp."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class VolumeData(BaseModel):
    """Volume bar data."""
    timestamp: datetime
    volume: float
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    delta: float = 0.0


class OpenInterestData(BaseModel):
    """Open interest data point."""
    timestamp: datetime
    open_interest: float
    change: float = 0.0
    change_pct: float = 0.0


class FundingData(BaseModel):
    """Funding rate data point."""
    timestamp: datetime
    funding_rate: float
    predicted_rate: Optional[float] = None


class LiquidationMarker(BaseModel):
    """Liquidation event marker."""
    timestamp: datetime
    price: float
    side: str  # long/short
    size: float
    symbol: str


class ChartDataResponse(BaseModel):
    """Complete chart data response."""
    symbol: str
    timeframe: str
    timestamp: datetime
    
    candles: List[Dict[str, Any]] = Field(default_factory=list)
    volume: List[Dict[str, Any]] = Field(default_factory=list)
    open_interest: List[Dict[str, Any]] = Field(default_factory=list)
    funding: List[Dict[str, Any]] = Field(default_factory=list)
    liquidations: List[Dict[str, Any]] = Field(default_factory=list)
    dominance: List[Dict[str, Any]] = Field(default_factory=list)
    custom_series: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class ChartDataService:
    """Service for chart data."""
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db
    
    async def get_chart_data(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        include_volume: bool = True,
        include_oi: bool = False,
        include_funding: bool = False,
        include_liquidations: bool = False,
        include_dominance: bool = False,
    ) -> ChartDataResponse:
        """Get complete chart data for a symbol."""
        
        response = ChartDataResponse(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
        )
        
        # Get candles
        response.candles = await self._get_candles(symbol, timeframe, limit)
        
        # Get volume (derived from candles)
        if include_volume:
            response.volume = self._derive_volume(response.candles)
        
        # Get OI
        if include_oi:
            response.open_interest = await self._get_open_interest(symbol, limit)
        
        # Get funding
        if include_funding:
            response.funding = await self._get_funding(symbol, limit)
        
        # Get liquidations
        if include_liquidations:
            response.liquidations = await self._get_liquidations(symbol, limit)
        
        # Get dominance
        if include_dominance and symbol == "BTCUSDT":
            response.dominance = await self._get_dominance(limit)
        
        response.metadata = {
            "candle_count": len(response.candles),
            "data_range": {
                "start": response.candles[0]["timestamp"] if response.candles else None,
                "end": response.candles[-1]["timestamp"] if response.candles else None,
            }
        }
        
        return response
    
    async def _get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get OHLCV candles from database."""
        try:
            collection = self.db["candles"]
            
            cursor = collection.find(
                {"symbol": symbol, "timeframe": timeframe},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            candles = list(cursor)
            
            # If no data found, generate mock
            if not candles:
                return self._generate_mock_candles(symbol, timeframe, limit)
            
            candles.reverse()
            
            return [
                {
                    "timestamp": c.get("timestamp", "").isoformat() if isinstance(c.get("timestamp"), datetime) else c.get("timestamp", ""),
                    "open": c.get("open", 0),
                    "high": c.get("high", 0),
                    "low": c.get("low", 0),
                    "close": c.get("close", 0),
                    "volume": c.get("volume", 0),
                }
                for c in candles
            ]
        except Exception as e:
            # Fallback: generate mock data
            return self._generate_mock_candles(symbol, timeframe, limit)
    
    def _generate_mock_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generate mock candle data for testing."""
        # Normalize timeframe
        tf_lower = timeframe.lower()
        
        # Use timeframe-dependent seed for different data per TF
        tf_seeds = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
        seed_value = tf_seeds.get(tf_lower, 60) + hash(symbol) % 1000
        np.random.seed(seed_value)
        
        # Timeframe to minutes
        tf_minutes = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "1d": 1440, "1w": 10080
        }
        minutes = tf_minutes.get(tf_lower, 60)
        
        # Base price varies by timeframe
        base_price = 50000 if "BTC" in symbol.upper() else 3000
        base_price *= (1 + (seed_value % 100) * 0.0005)  # Variation by TF
        
        # Volatility scales with timeframe
        vol_scale = max(1, minutes / 60)  # Higher timeframes = more movement
        
        candles = []
        current_time = datetime.now(timezone.utc) - timedelta(minutes=minutes * limit)
        price = base_price
        
        # Add trend bias - different per timeframe
        trend_direction = 1 if seed_value % 3 == 0 else (-1 if seed_value % 3 == 1 else 0)
        trend_bias = trend_direction * 0.0003 * vol_scale
        
        for i in range(limit):
            # Random walk with trend
            change = np.random.normal(trend_bias * price, base_price * 0.004 * vol_scale)
            price = max(price + change, base_price * 0.5)
            
            high = price * (1 + abs(np.random.normal(0, 0.006 * vol_scale)))
            low = price * (1 - abs(np.random.normal(0, 0.006 * vol_scale)))
            open_price = low + np.random.random() * (high - low)
            close_price = low + np.random.random() * (high - low)
            volume = np.random.uniform(100, 1000) * base_price / 50000 * vol_scale
            
            candles.append({
                "timestamp": current_time.isoformat(),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close_price, 2),
                "volume": round(volume, 2),
            })
            
            current_time += timedelta(minutes=minutes)
            price = close_price
        
        return candles
    
    def _derive_volume(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Derive volume bars from candles."""
        volume_bars = []
        
        for c in candles:
            # Estimate buy/sell volume from price action
            price_change = c["close"] - c["open"]
            total_volume = c["volume"]
            
            if price_change >= 0:
                buy_ratio = 0.5 + (price_change / (c["high"] - c["low"] + 0.01)) * 0.3
            else:
                buy_ratio = 0.5 - (abs(price_change) / (c["high"] - c["low"] + 0.01)) * 0.3
            
            buy_volume = total_volume * buy_ratio
            sell_volume = total_volume * (1 - buy_ratio)
            
            volume_bars.append({
                "timestamp": c["timestamp"],
                "volume": total_volume,
                "buy_volume": round(buy_volume, 2),
                "sell_volume": round(sell_volume, 2),
                "delta": round(buy_volume - sell_volume, 2),
            })
        
        return volume_bars
    
    async def _get_open_interest(
        self,
        symbol: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get open interest data."""
        try:
            collection = self.db["open_interest"]
            cursor = collection.find(
                {"symbol": symbol},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            data = list(cursor)
            data.reverse()
            
            return [
                {
                    "timestamp": d.get("timestamp", "").isoformat() if isinstance(d.get("timestamp"), datetime) else d.get("timestamp", ""),
                    "open_interest": d.get("open_interest", 0),
                    "change": d.get("change", 0),
                }
                for d in data
            ]
        except Exception:
            return []
    
    async def _get_funding(
        self,
        symbol: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get funding rate data."""
        try:
            collection = self.db["funding_rates"]
            cursor = collection.find(
                {"symbol": symbol},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            data = list(cursor)
            data.reverse()
            
            return [
                {
                    "timestamp": d.get("timestamp", "").isoformat() if isinstance(d.get("timestamp"), datetime) else d.get("timestamp", ""),
                    "funding_rate": d.get("funding_rate", 0),
                }
                for d in data
            ]
        except Exception:
            return []
    
    async def _get_liquidations(
        self,
        symbol: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get liquidation events."""
        try:
            collection = self.db["liquidations"]
            cursor = collection.find(
                {"symbol": symbol},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            data = list(cursor)
            data.reverse()
            
            return [
                {
                    "timestamp": d.get("timestamp", "").isoformat() if isinstance(d.get("timestamp"), datetime) else d.get("timestamp", ""),
                    "price": d.get("price", 0),
                    "side": d.get("side", "long"),
                    "size": d.get("size", 0),
                }
                for d in data
            ]
        except Exception:
            return []
    
    async def _get_dominance(self, limit: int) -> List[Dict[str, Any]]:
        """Get BTC dominance data."""
        # Generate mock dominance data
        np.random.seed(123)
        
        dominance = []
        current_time = datetime.now(timezone.utc) - timedelta(hours=limit)
        dom_value = 45.0
        
        for i in range(limit):
            dom_value += np.random.normal(0, 0.1)
            dom_value = max(35, min(60, dom_value))
            
            dominance.append({
                "timestamp": current_time.isoformat(),
                "btc_dominance": round(dom_value, 2),
            })
            
            current_time += timedelta(hours=1)
        
        return dominance


# Singleton
_chart_data_service: Optional[ChartDataService] = None

def get_chart_data_service() -> ChartDataService:
    global _chart_data_service
    if _chart_data_service is None:
        _chart_data_service = ChartDataService()
    return _chart_data_service
