"""
Level Engine
=============
Detects key price levels.

Supports:
- Support/Resistance
- Fibonacci levels
- Liquidity zones
- Pivot points
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from modules.ta_engine.setup.setup_types import (
    PriceLevel,
    LevelType,
)


class LevelEngine:
    """Detects and ranks key price levels."""
    
    def __init__(self):
        self.fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.level_tolerance = 0.01  # 1% tolerance for level clustering
    
    def analyze_all(self, candles: List[Dict]) -> List[PriceLevel]:
        """
        Detect all significant levels.
        Returns list sorted by strength (highest first).
        """
        if len(candles) < 20:
            return []
        
        levels = []
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        times = [c.get("timestamp", c.get("time")) for c in candles]
        
        # Support/Resistance from swing points
        levels.extend(self._find_support_resistance(highs, lows, times))
        
        # Fibonacci levels
        levels.extend(self._find_fibonacci_levels(highs, lows))
        
        # Liquidity zones
        levels.extend(self._find_liquidity_zones(highs, lows, times))
        
        # Cluster overlapping levels
        levels = self._cluster_levels(levels, closes[-1])
        
        # Sort by strength
        levels.sort(key=lambda l: l.strength, reverse=True)
        
        return levels[:15]  # Return top 15 levels
    
    def _find_support_resistance(
        self, 
        highs: List[float], 
        lows: List[float], 
        times: List
    ) -> List[PriceLevel]:
        """Find support and resistance levels from swing points."""
        levels = []
        
        # Find swing highs (resistance)
        swing_highs = self._find_swing_points(highs, is_high=True)
        for idx in swing_highs:
            price = highs[idx]
            touches = self._count_touches(highs, price, is_high=True)
            
            levels.append(PriceLevel(
                level_type=LevelType.RESISTANCE,
                price=price,
                strength=min(0.5 + touches * 0.15, 1.0),
                touches=touches,
                last_touch=self._parse_datetime(times[idx]) if times else None,
            ))
        
        # Find swing lows (support)
        swing_lows = self._find_swing_points(lows, is_high=False)
        for idx in swing_lows:
            price = lows[idx]
            touches = self._count_touches(lows, price, is_high=False)
            
            levels.append(PriceLevel(
                level_type=LevelType.SUPPORT,
                price=price,
                strength=min(0.5 + touches * 0.15, 1.0),
                touches=touches,
                last_touch=self._parse_datetime(times[idx]) if times else None,
            ))
        
        return levels
    
    def _find_fibonacci_levels(self, highs: List[float], lows: List[float]) -> List[PriceLevel]:
        """Calculate Fibonacci retracement levels."""
        levels = []
        
        # Find the major swing
        lookback = min(100, len(highs))
        recent_high = max(highs[-lookback:])
        recent_low = min(lows[-lookback:])
        
        high_idx = highs[-lookback:].index(recent_high)
        low_idx = lows[-lookback:].index(recent_low)
        
        # Determine trend direction
        swing_range = recent_high - recent_low
        
        if high_idx > low_idx:  # Uptrend - calculate retracements from low
            for i, ratio in enumerate(self.fib_ratios):
                fib_price = recent_high - (swing_range * ratio)
                level_type = [LevelType.FIB_236, LevelType.FIB_382, LevelType.FIB_500, 
                             LevelType.FIB_618, LevelType.FIB_786][i]
                
                levels.append(PriceLevel(
                    level_type=level_type,
                    price=fib_price,
                    strength=0.6 if ratio in [0.382, 0.618] else 0.5,  # Golden ratios stronger
                    touches=0,
                    last_touch=None,
                ))
        else:  # Downtrend - calculate retracements from high
            for i, ratio in enumerate(self.fib_ratios):
                fib_price = recent_low + (swing_range * ratio)
                level_type = [LevelType.FIB_236, LevelType.FIB_382, LevelType.FIB_500, 
                             LevelType.FIB_618, LevelType.FIB_786][i]
                
                levels.append(PriceLevel(
                    level_type=level_type,
                    price=fib_price,
                    strength=0.6 if ratio in [0.382, 0.618] else 0.5,
                    touches=0,
                    last_touch=None,
                ))
        
        return levels
    
    def _find_liquidity_zones(
        self, 
        highs: List[float], 
        lows: List[float], 
        times: List
    ) -> List[PriceLevel]:
        """Find liquidity zones (areas with clustered highs/lows)."""
        levels = []
        
        # Equal highs (liquidity above)
        equal_high = self._find_equal_levels(highs, tolerance=0.005)
        if equal_high:
            levels.append(PriceLevel(
                level_type=LevelType.LIQUIDITY_HIGH,
                price=equal_high,
                strength=0.7,
                touches=self._count_touches(highs, equal_high, is_high=True),
                last_touch=None,
            ))
        
        # Equal lows (liquidity below)
        equal_low = self._find_equal_levels(lows, tolerance=0.005)
        if equal_low:
            levels.append(PriceLevel(
                level_type=LevelType.LIQUIDITY_LOW,
                price=equal_low,
                strength=0.7,
                touches=self._count_touches(lows, equal_low, is_high=False),
                last_touch=None,
            ))
        
        return levels
    
    def _cluster_levels(self, levels: List[PriceLevel], current_price: float) -> List[PriceLevel]:
        """Cluster nearby levels and combine strength."""
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda l: l.price)
        
        clustered = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if this level is close to cluster
            cluster_price = sum(l.price for l in current_cluster) / len(current_cluster)
            tolerance = cluster_price * self.level_tolerance
            
            if abs(level.price - cluster_price) < tolerance:
                current_cluster.append(level)
            else:
                # Save current cluster and start new one
                clustered.append(self._merge_cluster(current_cluster))
                current_cluster = [level]
        
        # Don't forget last cluster
        clustered.append(self._merge_cluster(current_cluster))
        
        # Boost strength for levels near current price
        for level in clustered:
            distance = abs(level.price - current_price) / current_price
            if distance < 0.02:
                level.strength = min(level.strength + 0.1, 1.0)
        
        return clustered
    
    def _merge_cluster(self, cluster: List[PriceLevel]) -> PriceLevel:
        """Merge a cluster of levels into one."""
        if len(cluster) == 1:
            return cluster[0]
        
        avg_price = sum(l.price for l in cluster) / len(cluster)
        max_strength = max(l.strength for l in cluster)
        total_touches = sum(l.touches for l in cluster)
        
        # Determine dominant type
        type_counts = {}
        for l in cluster:
            type_counts[l.level_type] = type_counts.get(l.level_type, 0) + 1
        dominant_type = max(type_counts, key=type_counts.get)
        
        return PriceLevel(
            level_type=dominant_type,
            price=avg_price,
            strength=min(max_strength + len(cluster) * 0.05, 1.0),  # Boost for confluence
            touches=total_touches,
            last_touch=max((l.last_touch for l in cluster if l.last_touch), default=None),
        )
    
    def _find_swing_points(self, prices: List[float], is_high: bool, lookback: int = 5) -> List[int]:
        """Find swing high/low indices."""
        swings = []
        for i in range(lookback, len(prices) - lookback):
            if is_high:
                if all(prices[i] >= prices[i-j] for j in range(1, lookback+1)) and \
                   all(prices[i] >= prices[i+j] for j in range(1, min(lookback+1, len(prices)-i))):
                    swings.append(i)
            else:
                if all(prices[i] <= prices[i-j] for j in range(1, lookback+1)) and \
                   all(prices[i] <= prices[i+j] for j in range(1, min(lookback+1, len(prices)-i))):
                    swings.append(i)
        return swings
    
    def _count_touches(self, prices: List[float], level: float, is_high: bool, tolerance: float = 0.005) -> int:
        """Count how many times price touched a level."""
        touches = 0
        level_range = level * tolerance
        
        for price in prices:
            if abs(price - level) < level_range:
                touches += 1
        
        return touches
    
    def _find_equal_levels(self, prices: List[float], tolerance: float = 0.005) -> Optional[float]:
        """Find price level with multiple equal touches (liquidity)."""
        # Count price clusters
        price_counts = {}
        
        for price in prices[-50:]:  # Last 50 candles
            rounded = round(price / (price * tolerance)) * (price * tolerance)
            price_counts[rounded] = price_counts.get(rounded, 0) + 1
        
        # Find most common
        if price_counts:
            most_common = max(price_counts, key=price_counts.get)
            if price_counts[most_common] >= 3:  # At least 3 touches
                return most_common
        
        return None
    
    def _parse_datetime(self, ts) -> datetime:
        """Convert any timestamp form into aware UTC datetime via unified normalizer."""
        from modules.ta_engine.utils.time_utils import normalize_timestamp
        return normalize_timestamp(ts) or datetime.now(timezone.utc)


# Singleton
_engine: Optional[LevelEngine] = None


def get_level_engine() -> LevelEngine:
    global _engine
    if _engine is None:
        _engine = LevelEngine()
    return _engine
