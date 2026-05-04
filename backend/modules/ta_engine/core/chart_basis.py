"""
TA Engine - Core Chart Basis Builder
Builds common data structures used by all 10 layers
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import statistics


@dataclass
class Pivot:
    """A swing high or swing low point"""
    time: int
    price: float
    index: int
    type: str  # "high" or "low"
    strength: float = 1.0  # How significant
    
    def to_dict(self):
        return {
            "time": self.time,
            "price": self.price,
            "index": self.index,
            "type": self.type,
            "strength": self.strength,
        }


@dataclass
class Swing:
    """A swing movement from one pivot to another"""
    start: Pivot
    end: Pivot
    direction: str  # "up" or "down"
    magnitude: float  # Price change
    duration: int  # Candles
    
    def to_dict(self):
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "direction": self.direction,
            "magnitude": self.magnitude,
            "duration": self.duration,
        }


@dataclass
class ChartBasis:
    """
    Common chart data used by ALL layers.
    Built once, passed to all 10 groups.
    """
    # Raw data
    candles: List[Dict] = field(default_factory=list)
    timeframe: str = "1D"
    symbol: str = "BTC"
    
    # Derived structures
    pivots: List[Pivot] = field(default_factory=list)
    swings: List[Swing] = field(default_factory=list)
    
    # Price stats
    current_price: float = 0.0
    price_high: float = 0.0
    price_low: float = 0.0
    atr: float = 0.0
    
    # Time range
    start_time: int = 0
    end_time: int = 0
    
    def to_dict(self):
        return {
            "timeframe": self.timeframe,
            "symbol": self.symbol,
            "candle_count": len(self.candles),
            "pivot_count": len(self.pivots),
            "swing_count": len(self.swings),
            "current_price": self.current_price,
            "price_range": [self.price_low, self.price_high],
            "atr": self.atr,
        }


class ChartBasisBuilder:
    """
    Builds ChartBasis from raw candles.
    This is run ONCE and shared by all layers.
    """
    
    def __init__(self, pivot_lookback: int = 5):
        self.pivot_lookback = pivot_lookback
    
    def build(self, candles: List[Dict], timeframe: str = "1D", symbol: str = "BTC") -> ChartBasis:
        """Build complete chart basis from candles"""
        if not candles or len(candles) < 10:
            return ChartBasis(candles=candles, timeframe=timeframe, symbol=symbol)
        
        basis = ChartBasis(
            candles=candles,
            timeframe=timeframe,
            symbol=symbol,
        )
        
        # Price stats
        closes = [c.get("close", c.get("c", 0)) for c in candles]
        highs = [c.get("high", c.get("h", 0)) for c in candles]
        lows = [c.get("low", c.get("l", 0)) for c in candles]
        
        basis.current_price = closes[-1] if closes else 0
        basis.price_high = max(highs) if highs else 0
        basis.price_low = min(lows) if lows else 0
        
        # Time range
        basis.start_time = candles[0].get("time", candles[0].get("t", 0))
        basis.end_time = candles[-1].get("time", candles[-1].get("t", 0))
        
        # ATR
        basis.atr = self._calculate_atr(candles)
        
        # Pivots
        basis.pivots = self._find_pivots(candles)
        
        # Swings
        basis.swings = self._build_swings(basis.pivots)
        
        return basis
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(candles) < period + 1:
            return 0.0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i].get("high", candles[i].get("h", 0))
            low = candles[i].get("low", candles[i].get("l", 0))
            prev_close = candles[i-1].get("close", candles[i-1].get("c", 0))
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        
        if len(trs) >= period:
            return statistics.mean(trs[-period:])
        return statistics.mean(trs) if trs else 0.0
    
    def _find_pivots(self, candles: List[Dict]) -> List[Pivot]:
        """Find swing high/low pivots"""
        pivots = []
        n = len(candles)
        lookback = self.pivot_lookback
        
        for i in range(lookback, n - lookback):
            candle = candles[i]
            high = candle.get("high", candle.get("h", 0))
            low = candle.get("low", candle.get("l", 0))
            time = candle.get("time", candle.get("t", 0))
            
            # Check for swing high
            is_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i:
                    other_high = candles[j].get("high", candles[j].get("h", 0))
                    if other_high >= high:
                        is_high = False
                        break
            
            if is_high:
                strength = self._calc_pivot_strength(candles, i, "high")
                pivots.append(Pivot(
                    time=time,
                    price=high,
                    index=i,
                    type="high",
                    strength=strength,
                ))
            
            # Check for swing low
            is_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i:
                    other_low = candles[j].get("low", candles[j].get("l", 0))
                    if other_low <= low:
                        is_low = False
                        break
            
            if is_low:
                strength = self._calc_pivot_strength(candles, i, "low")
                pivots.append(Pivot(
                    time=time,
                    price=low,
                    index=i,
                    type="low",
                    strength=strength,
                ))
        
        # Sort by index
        pivots.sort(key=lambda p: p.index)
        return pivots
    
    def _calc_pivot_strength(self, candles: List[Dict], idx: int, pivot_type: str) -> float:
        """Calculate how significant a pivot is"""
        # Simple: based on how far price moved away
        if idx < 3 or idx >= len(candles) - 3:
            return 0.5
        
        pivot_price = candles[idx].get("high" if pivot_type == "high" else "low", 0)
        
        # Look at 3 candles before and after
        distances = []
        for offset in [-3, -2, -1, 1, 2, 3]:
            other_idx = idx + offset
            if 0 <= other_idx < len(candles):
                other_price = candles[other_idx].get("high" if pivot_type == "high" else "low", 0)
                distances.append(abs(pivot_price - other_price))
        
        if not distances:
            return 0.5
        
        avg_distance = statistics.mean(distances)
        # Normalize to 0-1 (rough)
        atr = self._calculate_atr(candles[max(0, idx-14):idx+1])
        if atr > 0:
            return min(1.0, avg_distance / (atr * 2))
        return 0.5
    
    def _build_swings(self, pivots: List[Pivot]) -> List[Swing]:
        """Build swing movements from pivots"""
        swings = []
        
        for i in range(1, len(pivots)):
            start = pivots[i - 1]
            end = pivots[i]
            
            direction = "up" if end.price > start.price else "down"
            magnitude = end.price - start.price
            duration = end.index - start.index
            
            swings.append(Swing(
                start=start,
                end=end,
                direction=direction,
                magnitude=magnitude,
                duration=duration,
            ))
        
        return swings


# Singleton
_basis_builder = None

def get_basis_builder() -> ChartBasisBuilder:
    global _basis_builder
    if _basis_builder is None:
        _basis_builder = ChartBasisBuilder()
    return _basis_builder
