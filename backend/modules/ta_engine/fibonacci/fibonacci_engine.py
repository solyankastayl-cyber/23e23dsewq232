"""
Fibonacci Engine
================
Auto-detects swing highs/lows and calculates Fibonacci retracement/extension levels.

Features:
- Auto swing high/low detection
- Retracement levels: 0.236, 0.382, 0.5, 0.618, 0.786
- Extension levels: 1.0, 1.272, 1.618, 2.0, 2.618
- One active fib set per chart (most recent significant swing)
- Trend-aware: uses appropriate swing direction
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FibLevel:
    """Single Fibonacci level."""
    ratio: float
    price: float
    label: str
    is_key_level: bool = False  # 0.618 and 0.5 are key levels
    
    def to_dict(self) -> Dict:
        return {
            "ratio": self.ratio,
            "price": round(self.price, 2),
            "label": self.label,
            "is_key_level": self.is_key_level,
        }


@dataclass
class FibonacciSet:
    """Complete Fibonacci retracement/extension set."""
    swing_high: Dict[str, Any]  # {time, price, index}
    swing_low: Dict[str, Any]   # {time, price, index}
    direction: str              # bullish (low->high) or bearish (high->low)
    retracement_levels: List[FibLevel] = field(default_factory=list)
    extension_levels: List[FibLevel] = field(default_factory=list)
    is_valid: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "swing_high": {
                "time": self.swing_high["time"],
                "price": round(self.swing_high["price"], 2),
            },
            "swing_low": {
                "time": self.swing_low["time"],
                "price": round(self.swing_low["price"], 2),
            },
            "direction": self.direction,
            "retracement_levels": [l.to_dict() for l in self.retracement_levels],
            "extension_levels": [l.to_dict() for l in self.extension_levels],
            "is_valid": self.is_valid,
        }


class FibonacciEngine:
    """
    Fibonacci Engine for auto swing detection and level calculation.
    """
    
    # Standard Fibonacci ratios
    RETRACEMENT_RATIOS = [
        (0.236, "23.6%"),
        (0.382, "38.2%"),
        (0.5, "50%"),
        (0.618, "61.8%"),
        (0.786, "78.6%"),
    ]
    
    EXTENSION_RATIOS = [
        (1.0, "100%"),
        (1.272, "127.2%"),
        (1.618, "161.8%"),
        (2.0, "200%"),
        (2.618, "261.8%"),
    ]
    
    KEY_LEVELS = {0.5, 0.618, 1.618}  # Most important levels
    
    def __init__(self):
        self.min_swing_bars = 10  # Minimum bars between swings
        self.min_swing_pct = 0.05  # Minimum 5% swing size
    
    def build(
        self,
        candles: List[Dict[str, Any]],
        pivot_highs: List[Dict[str, Any]],
        pivot_lows: List[Dict[str, Any]],
        structure_context: Dict[str, Any],
        timeframe: str,
    ) -> Dict[str, Any]:
        """
        Build Fibonacci set from candles and pivots.
        
        Returns:
            {
                "fib_set": {...} or None,
                "fib_levels_for_chart": [...],  # For rendering
            }
        """
        if len(candles) < 50:
            return self._empty_result()
        
        # Adjust min swing based on timeframe
        tf_config = {
            "4H": {"min_bars": 8, "min_pct": 0.03},
            "1D": {"min_bars": 10, "min_pct": 0.05},
            "7D": {"min_bars": 5, "min_pct": 0.08},
            "30D": {"min_bars": 3, "min_pct": 0.10},
        }
        config = tf_config.get(timeframe.upper(), {"min_bars": 10, "min_pct": 0.05})
        self.min_swing_bars = config["min_bars"]
        self.min_swing_pct = config["min_pct"]
        
        # Find most significant recent swing
        swing_high, swing_low = self._find_significant_swing(
            candles, pivot_highs, pivot_lows
        )
        
        if not swing_high or not swing_low:
            return self._empty_result()
        
        # Determine direction based on which came first
        if swing_low["index"] < swing_high["index"]:
            direction = "bullish"  # Low to high swing
        else:
            direction = "bearish"  # High to low swing
        
        # Calculate levels
        fib_set = self._calculate_fib_set(swing_high, swing_low, direction)
        
        # Convert to chart format
        chart_levels = self._to_chart_format(fib_set, candles)
        
        return {
            "fib_set": fib_set.to_dict() if fib_set else None,
            "fib_levels_for_chart": chart_levels,
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        return {
            "fib_set": None,
            "fib_levels_for_chart": [],
        }
    
    def _find_significant_swing(
        self,
        candles: List[Dict],
        pivot_highs: List[Dict],
        pivot_lows: List[Dict],
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Find the most significant recent swing.
        
        Rules:
        - Use the most recent major swing
        - Swing must be >= min_swing_pct of price
        - Prefer swings in the last 60% of chart
        """
        if not pivot_highs or not pivot_lows:
            return None, None
        
        # Look for swings in recent portion of chart
        recent_start = int(len(candles) * 0.4)
        
        # Filter to recent pivots
        recent_highs = [p for p in pivot_highs if p["index"] >= recent_start]
        recent_lows = [p for p in pivot_lows if p["index"] >= recent_start]
        
        # Fall back to all pivots if no recent ones
        if len(recent_highs) < 1:
            recent_highs = pivot_highs[-3:]
        if len(recent_lows) < 1:
            recent_lows = pivot_lows[-3:]
        
        best_high = None
        best_low = None
        best_swing_size = 0
        
        # Find the swing with largest magnitude
        for high in recent_highs:
            for low in recent_lows:
                # Check minimum bar distance
                bar_distance = abs(high["index"] - low["index"])
                if bar_distance < self.min_swing_bars:
                    continue
                
                # Calculate swing size
                swing_size = abs(high["price"] - low["price"])
                swing_pct = swing_size / min(high["price"], low["price"])
                
                if swing_pct < self.min_swing_pct:
                    continue
                
                # Prefer the swing ending most recently
                recency_score = max(high["index"], low["index"])
                combined_score = swing_pct * 0.6 + (recency_score / len(candles)) * 0.4
                
                if combined_score > best_swing_size:
                    best_swing_size = combined_score
                    best_high = high
                    best_low = low
        
        return best_high, best_low
    
    def _calculate_fib_set(
        self,
        swing_high: Dict,
        swing_low: Dict,
        direction: str,
    ) -> FibonacciSet:
        """Calculate Fibonacci levels for the swing."""
        
        high_price = swing_high["price"]
        low_price = swing_low["price"]
        price_range = high_price - low_price
        
        retracement_levels = []
        extension_levels = []
        
        # Calculate retracement levels
        for ratio, label in self.RETRACEMENT_RATIOS:
            if direction == "bullish":
                # Retracement from high down
                price = high_price - (price_range * ratio)
            else:
                # Retracement from low up
                price = low_price + (price_range * ratio)
            
            retracement_levels.append(FibLevel(
                ratio=ratio,
                price=price,
                label=label,
                is_key_level=ratio in self.KEY_LEVELS,
            ))
        
        # Calculate extension levels
        for ratio, label in self.EXTENSION_RATIOS:
            if direction == "bullish":
                # Extension above high
                price = low_price + (price_range * ratio)
            else:
                # Extension below low
                price = high_price - (price_range * ratio)
            
            extension_levels.append(FibLevel(
                ratio=ratio,
                price=price,
                label=label,
                is_key_level=ratio in self.KEY_LEVELS,
            ))
        
        return FibonacciSet(
            swing_high=swing_high,
            swing_low=swing_low,
            direction=direction,
            retracement_levels=retracement_levels,
            extension_levels=extension_levels,
            is_valid=True,
        )
    
    def _to_chart_format(
        self,
        fib_set: FibonacciSet,
        candles: List[Dict],
    ) -> List[Dict]:
        """Convert Fibonacci set to chart rendering format."""
        if not fib_set:
            return []
        
        # Get time range for rendering
        start_time = min(fib_set.swing_high["time"], fib_set.swing_low["time"])
        end_time = candles[-1]["time"] if candles else max(fib_set.swing_high["time"], fib_set.swing_low["time"])
        
        chart_levels = []
        
        # Add swing points as special markers
        chart_levels.append({
            "type": "swing",
            "subtype": "high",
            "time": fib_set.swing_high["time"],
            "price": fib_set.swing_high["price"],
            "label": "Swing High",
        })
        chart_levels.append({
            "type": "swing",
            "subtype": "low",
            "time": fib_set.swing_low["time"],
            "price": fib_set.swing_low["price"],
            "label": "Swing Low",
        })
        
        # Add retracement levels as horizontal lines
        for level in fib_set.retracement_levels:
            chart_levels.append({
                "type": "retracement",
                "ratio": level.ratio,
                "price": level.price,
                "label": level.label,
                "is_key": level.is_key_level,
                "start_time": start_time,
                "end_time": end_time,
                "color": "#f59e0b" if level.is_key_level else "#94a3b8",
                "line_style": "solid" if level.is_key_level else "dashed",
            })
        
        # Add extension levels
        for level in fib_set.extension_levels:
            chart_levels.append({
                "type": "extension",
                "ratio": level.ratio,
                "price": level.price,
                "label": level.label,
                "is_key": level.is_key_level,
                "start_time": start_time,
                "end_time": end_time,
                "color": "#8b5cf6" if level.is_key_level else "#64748b",
                "line_style": "solid" if level.is_key_level else "dotted",
            })
        
        return chart_levels


# Singleton
_engine: Optional[FibonacciEngine] = None


def get_fibonacci_engine() -> FibonacciEngine:
    global _engine
    if _engine is None:
        _engine = FibonacciEngine()
    return _engine
