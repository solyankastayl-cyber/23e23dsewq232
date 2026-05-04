"""
Pattern Validation Engine
=========================

PIVOT-BASED pattern detection with strict validation.

Rules:
1. Lines are built ONLY from pivot points
2. Minimum 2-3 touches required for each line
3. Parallel check for channels
4. If validation fails → NO PATTERN (not garbage lines)

Better to show nothing than show garbage.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import math


class Pivot:
    """Swing point in price data."""
    def __init__(self, index: int, time: int, value: float, pivot_type: str):
        self.index = index
        self.time = time
        self.value = value
        self.type = pivot_type  # "high" or "low"
    
    def __repr__(self):
        return f"Pivot({self.type}, idx={self.index}, val={self.value:.2f})"


class TrendLine:
    """Line built from pivots."""
    def __init__(self, p1: Pivot, p2: Pivot):
        self.p1 = p1
        self.p2 = p2
        self.slope = self._calc_slope()
        self.intercept = self._calc_intercept()
    
    def _calc_slope(self) -> float:
        dt = self.p2.time - self.p1.time
        if dt == 0:
            return 0
        return (self.p2.value - self.p1.value) / dt
    
    def _calc_intercept(self) -> float:
        return self.p1.value - self.slope * self.p1.time
    
    def value_at(self, time: int) -> float:
        """Get line value at given time."""
        return self.slope * time + self.intercept
    
    def extend_to(self, time: int) -> Dict:
        """Extend line to time, return point."""
        return {"time": time, "value": self.value_at(time)}


class PatternValidationEngine:
    """
    Strict pattern detection with pivot validation.
    """
    
    def __init__(self, timeframe: str = "1D"):
        # Pivot window depends on timeframe
        self.pivot_windows = {
            "4H": 3,
            "1D": 5,
            "7D": 7,
            "30D": 10,
            "180D": 12,
            "1Y": 15,
        }
        self.pivot_window = self.pivot_windows.get(timeframe, 5)
        
        # Validation thresholds
        self.min_touches = 3  # Minimum touches for valid line
        self.parallel_threshold = 0.15  # Max slope difference for parallel lines (relative)
        self.touch_tolerance = 0.015  # 1.5% tolerance for "touching" a line
        self.min_pattern_width = 0.005  # Min 0.5% width between channel lines
    
    def find_pivots(self, candles: List[Dict]) -> List[Pivot]:
        """
        Find pivot highs and lows.
        
        A pivot high is a high that is higher than all surrounding highs
        within the window.
        """
        pivots = []
        window = self.pivot_window
        
        for i in range(window, len(candles) - window):
            c = candles[i]
            high = c['high']
            low = c['low']
            time = c.get('timestamp', c.get('time', 0))
            if time > 1e12:
                time = time // 1000
            
            # Check if pivot high
            is_pivot_high = True
            for j in range(1, window + 1):
                if high <= candles[i - j]['high'] or high <= candles[i + j]['high']:
                    is_pivot_high = False
                    break
            
            # Check if pivot low
            is_pivot_low = True
            for j in range(1, window + 1):
                if low >= candles[i - j]['low'] or low >= candles[i + j]['low']:
                    is_pivot_low = False
                    break
            
            if is_pivot_high:
                pivots.append(Pivot(i, time, high, "high"))
            
            if is_pivot_low:
                pivots.append(Pivot(i, time, low, "low"))
        
        return pivots
    
    def count_touches(self, line: TrendLine, candles: List[Dict], line_type: str) -> int:
        """
        Count how many candles touch the trendline.
        
        line_type: "high" or "low" - determines which price to check
        """
        touches = 0
        
        for c in candles:
            time = c.get('timestamp', c.get('time', 0))
            if time > 1e12:
                time = time // 1000
            
            line_value = line.value_at(time)
            
            if line_type == "high":
                price = c['high']
                # Price should be near or above line for resistance
                if abs(price - line_value) / line_value < self.touch_tolerance:
                    touches += 1
            else:
                price = c['low']
                # Price should be near or below line for support
                if abs(price - line_value) / line_value < self.touch_tolerance:
                    touches += 1
        
        return touches
    
    def are_lines_parallel(self, line1: TrendLine, line2: TrendLine) -> bool:
        """Check if two lines are approximately parallel."""
        if line1.slope == 0 and line2.slope == 0:
            return True
        
        if line1.slope == 0 or line2.slope == 0:
            # One is horizontal, other is not
            return abs(line1.slope - line2.slope) < 0.0001
        
        # Relative slope difference
        slope_diff = abs(line1.slope - line2.slope) / max(abs(line1.slope), abs(line2.slope))
        return slope_diff < self.parallel_threshold
    
    def detect_channel(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Detect channel pattern with strict validation.
        
        Returns None if no valid channel found.
        """
        if len(candles) < 20:
            return None
        
        # Find pivots
        pivots = self.find_pivots(candles)
        
        # Separate highs and lows
        pivot_highs = [p for p in pivots if p.type == "high"]
        pivot_lows = [p for p in pivots if p.type == "low"]
        
        # Need at least 2 pivot highs and 2 pivot lows
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        # Try to build lines from recent pivots
        # Take last 3-4 pivots for each line
        recent_highs = pivot_highs[-4:]
        recent_lows = pivot_lows[-4:]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        # Build upper line from first and last pivot high
        upper_line = TrendLine(recent_highs[0], recent_highs[-1])
        
        # Build lower line from first and last pivot low
        lower_line = TrendLine(recent_lows[0], recent_lows[-1])
        
        # VALIDATION 1: Check parallel
        if not self.are_lines_parallel(upper_line, lower_line):
            return None
        
        # VALIDATION 2: Count touches
        upper_touches = self.count_touches(upper_line, candles[-50:], "high")
        lower_touches = self.count_touches(lower_line, candles[-50:], "low")
        
        total_touches = upper_touches + lower_touches
        
        if total_touches < self.min_touches:
            return None
        
        # VALIDATION 3: Check minimum width
        current_time = candles[-1].get('timestamp', candles[-1].get('time', 0))
        if current_time > 1e12:
            current_time = current_time // 1000
        
        upper_value = upper_line.value_at(current_time)
        lower_value = lower_line.value_at(current_time)
        
        channel_width = (upper_value - lower_value) / lower_value
        
        if channel_width < self.min_pattern_width:
            return None
        
        # VALIDATION 4: Price should be inside channel
        current_price = candles[-1]['close']
        
        if current_price > upper_value * 1.02 or current_price < lower_value * 0.98:
            # Price broke out of channel - pattern is over
            return None
        
        # Determine channel type
        avg_slope = (upper_line.slope + lower_line.slope) / 2
        
        # Normalize slope to price percentage per day
        avg_price = (upper_value + lower_value) / 2
        daily_slope_pct = (avg_slope * 86400) / avg_price  # slope per day as percentage
        
        if daily_slope_pct > 0.001:  # >0.1% per day up
            channel_type = "ascending_channel"
            direction = "bullish"
        elif daily_slope_pct < -0.001:  # >0.1% per day down
            channel_type = "descending_channel"
            direction = "bearish"
        else:
            channel_type = "horizontal_channel"
            direction = "neutral"
        
        # Calculate confidence based on touches
        confidence = min(0.9, 0.5 + (total_touches * 0.08))
        
        # Build geometry points
        start_time = recent_highs[0].time
        end_time = current_time
        
        # Extend lines slightly into future for projection
        future_time = end_time + (end_time - start_time) * 0.1
        
        return {
            "type": channel_type,
            "direction": direction,
            "confidence": round(confidence, 2),
            "touches": total_touches,
            "points": {
                "upper": [
                    {"time": start_time, "value": round(upper_line.value_at(start_time), 2)},
                    {"time": end_time, "value": round(upper_line.value_at(end_time), 2)},
                ],
                "lower": [
                    {"time": start_time, "value": round(lower_line.value_at(start_time), 2)},
                    {"time": end_time, "value": round(lower_line.value_at(end_time), 2)},
                ],
            },
            "breakout_level": round(upper_value if direction != "bearish" else lower_value, 2),
            "invalidation": round(lower_value if direction == "bullish" else upper_value, 2),
        }
    
    def detect_triangle(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Detect triangle pattern with converging lines.
        """
        if len(candles) < 20:
            return None
        
        pivots = self.find_pivots(candles)
        
        pivot_highs = [p for p in pivots if p.type == "high"]
        pivot_lows = [p for p in pivots if p.type == "low"]
        
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        recent_highs = pivot_highs[-3:]
        recent_lows = pivot_lows[-3:]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        upper_line = TrendLine(recent_highs[0], recent_highs[-1])
        lower_line = TrendLine(recent_lows[0], recent_lows[-1])
        
        # For triangle, lines should CONVERGE (not parallel)
        if self.are_lines_parallel(upper_line, lower_line):
            return None  # That's a channel, not triangle
        
        # Determine triangle type
        avg_price = candles[-1]['close']
        upper_slope_pct = (upper_line.slope * 86400) / avg_price
        lower_slope_pct = (lower_line.slope * 86400) / avg_price
        
        if abs(upper_slope_pct) < 0.0005 and lower_slope_pct > 0.0005:
            # Flat top, rising bottom = ascending triangle
            triangle_type = "ascending_triangle"
            direction = "bullish"
        elif upper_slope_pct < -0.0005 and abs(lower_slope_pct) < 0.0005:
            # Falling top, flat bottom = descending triangle
            triangle_type = "descending_triangle"
            direction = "bearish"
        elif upper_slope_pct < 0 and lower_slope_pct > 0:
            # Both converging = symmetrical
            triangle_type = "symmetrical_triangle"
            direction = "neutral"
        else:
            return None
        
        # Validate touches
        upper_touches = self.count_touches(upper_line, candles[-40:], "high")
        lower_touches = self.count_touches(lower_line, candles[-40:], "low")
        
        if upper_touches + lower_touches < 3:
            return None
        
        confidence = min(0.85, 0.5 + (upper_touches + lower_touches) * 0.07)
        
        current_time = candles[-1].get('timestamp', candles[-1].get('time', 0))
        if current_time > 1e12:
            current_time = current_time // 1000
        
        start_time = recent_highs[0].time
        
        return {
            "type": triangle_type,
            "direction": direction,
            "confidence": round(confidence, 2),
            "touches": upper_touches + lower_touches,
            "points": {
                "upper": [
                    {"time": start_time, "value": round(upper_line.value_at(start_time), 2)},
                    {"time": current_time, "value": round(upper_line.value_at(current_time), 2)},
                ],
                "lower": [
                    {"time": start_time, "value": round(lower_line.value_at(start_time), 2)},
                    {"time": current_time, "value": round(lower_line.value_at(current_time), 2)},
                ],
            },
            "breakout_level": round(upper_line.value_at(current_time), 2),
            "invalidation": round(lower_line.value_at(current_time), 2),
        }
    
    def detect_best_pattern(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Detect the best (highest confidence) valid pattern.
        
        Returns None if no valid pattern found.
        
        RULE: Better to return nothing than garbage.
        """
        patterns = []
        
        # Try channel
        channel = self.detect_channel(candles)
        if channel:
            patterns.append(channel)
        
        # Try triangle
        triangle = self.detect_triangle(candles)
        if triangle:
            patterns.append(triangle)
        
        if not patterns:
            return None
        
        # Return highest confidence
        patterns.sort(key=lambda p: p["confidence"], reverse=True)
        return patterns[0]


# Singleton instance
_pattern_engine = None

def get_pattern_validation_engine(timeframe: str = "1D") -> PatternValidationEngine:
    global _pattern_engine
    if _pattern_engine is None or _pattern_engine.pivot_window != PatternValidationEngine(timeframe).pivot_window:
        _pattern_engine = PatternValidationEngine(timeframe)
    return _pattern_engine
