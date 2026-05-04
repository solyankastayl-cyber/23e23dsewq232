"""
Anchor Selector v1
==================

Selects anchor points for pattern construction.
NOT regression fitting, but EXPLICIT swing selection.

Key principle:
- Трейдер выбирает 2-3 ключевые точки, а не "все highs/lows"
- Линия строится через конкретные anchor points
- Другие точки проверяются как touches, а не используются для построения

For each pattern type:
- falling_wedge: 2+ lower_highs, 2+ lower_lows, both descending
- ascending_triangle: 2+ flat_highs, 2+ higher_lows
- descending_triangle: 2+ flat_lows, 2+ lower_highs
- channel: parallel boundaries with consistent touches
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class SwingPoint:
    """Represents a significant swing high/low."""
    index: int
    time: int
    price: float
    swing_type: str  # 'high' or 'low'
    is_major: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "time": self.time,
            "price": self.price,
            "type": self.swing_type,
            "is_major": self.is_major,
        }


class AnchorSelector:
    """
    Selects anchor points for pattern boundaries.
    
    NOT all points, but specifically:
    - Major swings only
    - Points that form clear structural pattern
    - Points with sufficient separation
    """
    
    def __init__(self, tolerance_pct: float = 0.015, min_separation: int = 3):
        """
        Args:
            tolerance_pct: Price tolerance for "same level" (1.5% default)
            min_separation: Minimum candles between anchor points
        """
        self.tolerance_pct = tolerance_pct
        self.min_separation = min_separation
    
    def extract_swings(self, candles: List[Dict], lookback: int = 5) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """
        Extract swing highs and lows from candles.
        
        Uses simple pivot detection:
        - Swing high: higher than `lookback` candles on both sides
        - Swing low: lower than `lookback` candles on both sides
        
        Returns:
            (swing_highs, swing_lows)
        """
        swing_highs = []
        swing_lows = []
        
        n = len(candles)
        
        for i in range(lookback, n - lookback):
            candle = candles[i]
            high = candle.get("high", candle.get("h", 0))
            low = candle.get("low", candle.get("l", 0))
            time = candle.get("time", candle.get("timestamp", 0))
            
            # Check for swing high
            is_swing_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i:
                    other_high = candles[j].get("high", candles[j].get("h", 0))
                    if other_high >= high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                swing_highs.append(SwingPoint(
                    index=i,
                    time=time,
                    price=high,
                    swing_type="high",
                ))
            
            # Check for swing low
            is_swing_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i:
                    other_low = candles[j].get("low", candles[j].get("l", 0))
                    if other_low <= low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                swing_lows.append(SwingPoint(
                    index=i,
                    time=time,
                    price=low,
                    swing_type="low",
                ))
        
        # Mark major swings (remove minor ones that are too close)
        swing_highs = self._filter_major_swings(swing_highs)
        swing_lows = self._filter_major_swings(swing_lows)
        
        return swing_highs, swing_lows
    
    def _filter_major_swings(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Filter to keep only major swings with sufficient separation."""
        if len(swings) <= 1:
            return swings
        
        major = []
        for i, swing in enumerate(swings):
            # Check if this swing is significant compared to neighbors
            is_major = True
            for other in swings:
                if other.index == swing.index:
                    continue
                # If another swing is too close and more extreme, skip this one
                if abs(other.index - swing.index) < self.min_separation:
                    if swing.swing_type == "high" and other.price > swing.price:
                        is_major = False
                        break
                    if swing.swing_type == "low" and other.price < swing.price:
                        is_major = False
                        break
            
            if is_major:
                swing.is_major = True
                major.append(swing)
        
        return major
    
    # ═══════════════════════════════════════════════════════════════
    # PATTERN-SPECIFIC ANCHOR SELECTION
    # ═══════════════════════════════════════════════════════════════
    
    def select_falling_wedge_anchors(
        self, 
        swing_highs: List[SwingPoint], 
        swing_lows: List[SwingPoint]
    ) -> Optional[Dict]:
        """
        Select anchors for falling wedge.
        
        Requirements:
        - 2+ descending highs (lower highs)
        - 2+ descending lows (lower lows)
        - Upper line steeper than lower line (converging)
        - Both lines descending
        """
        # Need at least 2 highs and 2 lows
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # Sort by time
        highs = sorted(swing_highs, key=lambda x: x.index)
        lows = sorted(swing_lows, key=lambda x: x.index)
        
        # Find descending highs (lower highs)
        upper_anchors = self._find_descending_sequence(highs, min_points=2)
        if not upper_anchors:
            return None
        
        # Find descending lows (lower lows)
        lower_anchors = self._find_descending_sequence(lows, min_points=2)
        if not lower_anchors:
            return None
        
        # Calculate slopes
        upper_slope = self._calc_slope(upper_anchors)
        lower_slope = self._calc_slope(lower_anchors)
        
        # Validation:
        # 1. Both slopes must be negative (descending)
        if upper_slope >= 0 or lower_slope >= 0:
            return None
        
        # 2. Upper slope must be steeper (more negative) than lower slope
        # This ensures convergence
        if abs(upper_slope) <= abs(lower_slope):
            return None
        
        return {
            "type": "falling_wedge",
            "upper_anchors": [a.to_dict() for a in upper_anchors],
            "lower_anchors": [a.to_dict() for a in lower_anchors],
            "upper_slope": upper_slope,
            "lower_slope": lower_slope,
        }
    
    def select_ascending_triangle_anchors(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Optional[Dict]:
        """
        Select anchors for ascending triangle.
        
        Requirements:
        - 2+ flat highs (within tolerance)
        - 2+ ascending lows (higher lows)
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        highs = sorted(swing_highs, key=lambda x: x.index)
        lows = sorted(swing_lows, key=lambda x: x.index)
        
        # Find flat highs (resistance level)
        upper_anchors = self._find_flat_sequence(highs, min_points=2)
        if not upper_anchors:
            return None
        
        # Find ascending lows (higher lows)
        lower_anchors = self._find_ascending_sequence(lows, min_points=2)
        if not lower_anchors:
            return None
        
        upper_slope = self._calc_slope(upper_anchors)
        lower_slope = self._calc_slope(lower_anchors)
        
        # Upper should be approximately flat
        avg_price = sum(a.price for a in upper_anchors) / len(upper_anchors)
        slope_tolerance = avg_price * 0.001  # 0.1% slope tolerance
        
        if abs(upper_slope) > slope_tolerance:
            return None
        
        # Lower must be ascending
        if lower_slope <= 0:
            return None
        
        return {
            "type": "ascending_triangle",
            "upper_anchors": [a.to_dict() for a in upper_anchors],
            "lower_anchors": [a.to_dict() for a in lower_anchors],
            "upper_slope": upper_slope,
            "lower_slope": lower_slope,
            "resistance_level": avg_price,
        }
    
    def select_descending_triangle_anchors(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Optional[Dict]:
        """
        Select anchors for descending triangle.
        
        Requirements:
        - 2+ flat lows (within tolerance)
        - 2+ descending highs (lower highs)
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        highs = sorted(swing_highs, key=lambda x: x.index)
        lows = sorted(swing_lows, key=lambda x: x.index)
        
        # Find descending highs
        upper_anchors = self._find_descending_sequence(highs, min_points=2)
        if not upper_anchors:
            return None
        
        # Find flat lows (support level)
        lower_anchors = self._find_flat_sequence(lows, min_points=2)
        if not lower_anchors:
            return None
        
        upper_slope = self._calc_slope(upper_anchors)
        lower_slope = self._calc_slope(lower_anchors)
        
        # Lower should be approximately flat
        avg_price = sum(a.price for a in lower_anchors) / len(lower_anchors)
        slope_tolerance = avg_price * 0.001
        
        if abs(lower_slope) > slope_tolerance:
            return None
        
        # Upper must be descending
        if upper_slope >= 0:
            return None
        
        return {
            "type": "descending_triangle",
            "upper_anchors": [a.to_dict() for a in upper_anchors],
            "lower_anchors": [a.to_dict() for a in lower_anchors],
            "upper_slope": upper_slope,
            "lower_slope": lower_slope,
            "support_level": avg_price,
        }
    
    def select_channel_anchors(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Optional[Dict]:
        """
        Select anchors for channel.
        
        Requirements:
        - 2+ highs forming trendline
        - 2+ lows forming parallel trendline
        - Slopes approximately equal
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        highs = sorted(swing_highs, key=lambda x: x.index)
        lows = sorted(swing_lows, key=lambda x: x.index)
        
        # Try to find parallel lines
        # First: find best fit for highs
        upper_anchors = highs[:3] if len(highs) >= 3 else highs[:2]
        upper_slope = self._calc_slope(upper_anchors)
        
        # Then: find lows with similar slope
        lower_anchors = lows[:3] if len(lows) >= 3 else lows[:2]
        lower_slope = self._calc_slope(lower_anchors)
        
        # Check if slopes are parallel (within 20% tolerance)
        if upper_slope == 0 and lower_slope == 0:
            # Horizontal channel
            pass
        elif upper_slope == 0 or lower_slope == 0:
            return None
        else:
            slope_ratio = upper_slope / lower_slope if lower_slope != 0 else float('inf')
            if abs(slope_ratio - 1) > 0.3:  # 30% tolerance
                return None
        
        # Determine channel type
        avg_slope = (upper_slope + lower_slope) / 2
        if abs(avg_slope) < 0.0001:
            channel_type = "horizontal_channel"
        elif avg_slope > 0:
            channel_type = "ascending_channel"
        else:
            channel_type = "descending_channel"
        
        return {
            "type": channel_type,
            "upper_anchors": [a.to_dict() for a in upper_anchors],
            "lower_anchors": [a.to_dict() for a in lower_anchors],
            "upper_slope": upper_slope,
            "lower_slope": lower_slope,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _find_descending_sequence(self, points: List[SwingPoint], min_points: int = 2) -> List[SwingPoint]:
        """Find a sequence of descending points (each lower than previous)."""
        if len(points) < min_points:
            return []
        
        # Start from most recent, look backwards for descending sequence
        result = [points[-1]]
        for i in range(len(points) - 2, -1, -1):
            if points[i].price > result[0].price:
                result.insert(0, points[i])
                if len(result) >= min_points:
                    break
        
        if len(result) >= min_points:
            return result
        
        # Try forward scan
        result = [points[0]]
        for i in range(1, len(points)):
            if points[i].price < result[-1].price:
                result.append(points[i])
        
        return result if len(result) >= min_points else []
    
    def _find_ascending_sequence(self, points: List[SwingPoint], min_points: int = 2) -> List[SwingPoint]:
        """Find a sequence of ascending points (each higher than previous)."""
        if len(points) < min_points:
            return []
        
        result = [points[0]]
        for i in range(1, len(points)):
            if points[i].price > result[-1].price:
                result.append(points[i])
        
        return result if len(result) >= min_points else []
    
    def _find_flat_sequence(self, points: List[SwingPoint], min_points: int = 2) -> List[SwingPoint]:
        """Find a sequence of points at approximately the same level."""
        if len(points) < min_points:
            return []
        
        # Find cluster of points within tolerance
        for i, anchor in enumerate(points):
            cluster = [anchor]
            for j, other in enumerate(points):
                if i == j:
                    continue
                pct_diff = abs(other.price - anchor.price) / anchor.price
                if pct_diff <= self.tolerance_pct:
                    cluster.append(other)
            
            if len(cluster) >= min_points:
                return sorted(cluster, key=lambda x: x.index)
        
        return []
    
    def _calc_slope(self, points: List[SwingPoint]) -> float:
        """Calculate slope between first and last anchor point."""
        if len(points) < 2:
            return 0
        
        p1, p2 = points[0], points[-1]
        dx = p2.index - p1.index
        if dx == 0:
            return 0
        
        return (p2.price - p1.price) / dx


# Singleton
_anchor_selector = None

def get_anchor_selector() -> AnchorSelector:
    """Get anchor selector singleton."""
    global _anchor_selector
    if _anchor_selector is None:
        _anchor_selector = AnchorSelector()
    return _anchor_selector
