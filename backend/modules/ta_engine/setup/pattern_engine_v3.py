"""
Pattern Engine v3.0
===================

Proper pattern detection from clean structure.

Key differences from v2:
1. Works on CLEAN structure (not raw pivots)
2. Uses line FITTING (not point connection)
3. Validates TOUCHES (not just shape)
4. Returns GEOMETRY ready for rendering

Pattern types:
- Triangles (ascending, descending, symmetrical)
- Channels (ascending, descending, horizontal)
- Double Top/Bottom
- Head & Shoulders

Pipeline:
structure → pattern candidates → validation → geometry → output
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PatternResult:
    """Pattern detection result with geometry."""
    type: str
    direction: str
    confidence: float
    geometry: Dict[str, Any]
    touches_upper: int = 0
    touches_lower: int = 0
    slope_upper: float = 0.0
    slope_lower: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "direction": self.direction,
            "confidence": round(self.confidence, 2),
            "engine": "V4_ANCHOR",  # MARKER: Proves anchor-based engine is used
            "source": "ANCHOR_V4",  # MARKER: For frontend detection
            "geometry": self.geometry,
            "touches": {
                "upper": self.touches_upper,
                "lower": self.touches_lower,
            },
            "slopes": {
                "upper": round(self.slope_upper, 6),
                "lower": round(self.slope_lower, 6),
            },
        }


class PatternEngineV3:
    """
    Pattern detection engine v3.
    
    Works on clean structure from StructureBuilder.
    Returns patterns with geometry ready for rendering.
    """
    
    # Thresholds
    MIN_TOUCHES = 2
    MIN_POINTS_TRIANGLE = 4
    MIN_POINTS_CHANNEL = 4
    MIN_POINTS_DOUBLE = 4
    MIN_POINTS_HS = 5
    
    SLOPE_HORIZONTAL_THRESHOLD = 0.0001  # Consider horizontal if slope < this
    SLOPE_PARALLEL_THRESHOLD = 0.002     # Consider parallel if diff < this
    PRICE_TOLERANCE = 0.02               # 2% tolerance for price matching
    
    def __init__(self, timeframe: str = "4H"):
        self.timeframe = timeframe
        self.touch_tolerance = self._get_touch_tolerance(timeframe)
    
    def _get_touch_tolerance(self, tf: str) -> float:
        """Get touch tolerance based on timeframe."""
        tolerances = {
            "1H": 0.008,
            "4H": 0.010,
            "1D": 0.012,
            "7D": 0.015,
            "30D": 0.020,
            "180D": 0.025,
            "1Y": 0.030,
        }
        return tolerances.get(tf, 0.010)
    
    # ═══════════════════════════════════════════════════════════════
    # LINE UTILITIES
    # ═══════════════════════════════════════════════════════════════
    
    def _fit_line(self, points: List[Dict]) -> Tuple[float, float]:
        """
        V4 ANCHOR-BASED: Build line through BEST ANCHOR POINTS, not regression.
        
        Select 2 most prominent points and draw line directly through them.
        """
        if len(points) < 2:
            return 0.0, 0.0
        
        # Extract data
        data = [(p.get("index", p.get("time", i)), p.get("price", p.get("value", 0))) 
                for i, p in enumerate(points)]
        
        if len(data) < 2:
            return 0.0, float(np.mean([d[1] for d in data])) if data else 0.0
        
        # === ANCHOR-BASED SELECTION ===
        # Select most prominent point (furthest from mean)
        prices = [d[1] for d in data]
        mean_price = sum(prices) / len(prices)
        
        # Score points by prominence (distance from mean)
        scored = [(d, abs(d[1] - mean_price)) for d in data]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Take best point as first anchor
        anchor1 = scored[0][0]
        
        # Find second anchor with proper separation
        anchor2 = None
        for d, _ in scored[1:]:
            if abs(d[0] - anchor1[0]) >= 2:  # Min 2 units apart
                anchor2 = d
                break
        
        if not anchor2 and len(scored) > 1:
            anchor2 = scored[1][0]
        
        if not anchor2:
            return 0.0, anchor1[1]
        
        # Order by index
        if anchor1[0] > anchor2[0]:
            anchor1, anchor2 = anchor2, anchor1
        
        # Calculate line through anchors
        x1, y1 = anchor1
        x2, y2 = anchor2
        
        if x2 == x1:
            return 0.0, y1
        
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        
        return float(slope), float(intercept)
    
    def _line_value(self, slope: float, intercept: float, x: float) -> float:
        """Get y value at x on the line."""
        return slope * x + intercept
    
    def _count_touches(self, points: List[Dict], slope: float, intercept: float) -> int:
        """Count how many points touch the line."""
        touches = 0
        for p in points:
            x = p.get("index", p.get("time", 0))
            actual = p.get("price", p.get("value", 0))
            expected = self._line_value(slope, intercept, x)
            
            if expected == 0:
                continue
            
            dist = abs(actual - expected) / expected
            if dist < self.touch_tolerance:
                touches += 1
        
        return touches
    
    def _get_price(self, p: Dict) -> float:
        """Extract price from point dict."""
        return p.get("price", p.get("value", 0))
    
    def _get_index(self, p: Dict) -> int:
        """Extract index from point dict."""
        return p.get("index", p.get("time", 0))
    
    # ═══════════════════════════════════════════════════════════════
    # TRIANGLE DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def detect_triangle(self, highs: List[Dict], lows: List[Dict], all_points: List[Dict]) -> Optional[PatternResult]:
        """
        Detect triangle pattern from structure.
        
        Types:
        - Ascending: flat top, rising bottom
        - Descending: falling top, flat bottom
        - Symmetrical: converging lines
        """
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Use last N points
        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows
        
        # Fit lines
        h_slope, h_intercept = self._fit_line(recent_highs)
        l_slope, l_intercept = self._fit_line(recent_lows)
        
        # Count touches
        touches_upper = self._count_touches(recent_highs, h_slope, h_intercept)
        touches_lower = self._count_touches(recent_lows, l_slope, l_intercept)
        
        if touches_upper < self.MIN_TOUCHES or touches_lower < self.MIN_TOUCHES:
            print(f"[PatternV3] Triangle rejected: touches upper={touches_upper}, lower={touches_lower}")
            return None
        
        # Check convergence (lines must converge, not diverge)
        x_start = min(self._get_index(p) for p in recent_highs + recent_lows)
        x_end = max(self._get_index(p) for p in recent_highs + recent_lows)
        
        dist_start = self._line_value(h_slope, h_intercept, x_start) - self._line_value(l_slope, l_intercept, x_start)
        dist_end = self._line_value(h_slope, h_intercept, x_end) - self._line_value(l_slope, l_intercept, x_end)
        
        if dist_end >= dist_start:
            print(f"[PatternV3] Triangle rejected: lines not converging")
            return None
        
        # Determine triangle type
        h_is_flat = abs(h_slope) < self.SLOPE_HORIZONTAL_THRESHOLD
        l_is_flat = abs(l_slope) < self.SLOPE_HORIZONTAL_THRESHOLD
        
        if h_is_flat and l_slope > 0:
            pattern_type = "ascending_triangle"
            direction = "bullish"
            confidence = 0.80
        elif l_is_flat and h_slope < 0:
            pattern_type = "descending_triangle"
            direction = "bearish"
            confidence = 0.80
        elif h_slope < 0 and l_slope > 0:
            pattern_type = "symmetrical_triangle"
            direction = "neutral"
            confidence = 0.70
        else:
            return None
        
        # Build geometry
        geometry = self._build_line_geometry(
            recent_highs, recent_lows,
            h_slope, h_intercept,
            l_slope, l_intercept
        )
        
        print(f"[PatternV3] Triangle detected: {pattern_type}, touches={touches_upper}+{touches_lower}")
        
        return PatternResult(
            type=pattern_type,
            direction=direction,
            confidence=confidence,
            geometry=geometry,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
            slope_upper=h_slope,
            slope_lower=l_slope,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # CHANNEL DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def detect_channel(self, highs: List[Dict], lows: List[Dict], all_points: List[Dict]) -> Optional[PatternResult]:
        """
        Detect channel pattern (parallel lines).
        
        Types:
        - Ascending channel: both lines rising
        - Descending channel: both lines falling
        - Horizontal channel: both lines flat
        """
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        recent_highs = highs[-4:] if len(highs) >= 4 else highs
        recent_lows = lows[-4:] if len(lows) >= 4 else lows
        
        h_slope, h_intercept = self._fit_line(recent_highs)
        l_slope, l_intercept = self._fit_line(recent_lows)
        
        touches_upper = self._count_touches(recent_highs, h_slope, h_intercept)
        touches_lower = self._count_touches(recent_lows, l_slope, l_intercept)
        
        if touches_upper < self.MIN_TOUCHES or touches_lower < self.MIN_TOUCHES:
            return None
        
        # Check parallelism
        slope_diff = abs(h_slope - l_slope)
        if slope_diff > self.SLOPE_PARALLEL_THRESHOLD:
            return None  # Not parallel, might be triangle
        
        # Determine channel type
        avg_slope = (h_slope + l_slope) / 2
        
        if abs(avg_slope) < self.SLOPE_HORIZONTAL_THRESHOLD:
            pattern_type = "horizontal_channel"
            direction = "neutral"
        elif avg_slope > 0:
            pattern_type = "ascending_channel"
            direction = "bullish"
        else:
            pattern_type = "descending_channel"
            direction = "bearish"
        
        geometry = self._build_line_geometry(
            recent_highs, recent_lows,
            h_slope, h_intercept,
            l_slope, l_intercept
        )
        
        print(f"[PatternV3] Channel detected: {pattern_type}, touches={touches_upper}+{touches_lower}")
        
        return PatternResult(
            type=pattern_type,
            direction=direction,
            confidence=0.75,
            geometry=geometry,
            touches_upper=touches_upper,
            touches_lower=touches_lower,
            slope_upper=h_slope,
            slope_lower=l_slope,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # DOUBLE TOP/BOTTOM DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def detect_double(self, highs: List[Dict], lows: List[Dict], all_points: List[Dict]) -> Optional[PatternResult]:
        """
        Detect double top or double bottom.
        
        Double top: two highs at similar price
        Double bottom: two lows at similar price
        """
        # Check double top
        if len(highs) >= 2:
            h1, h2 = highs[-2], highs[-1]
            h1_price = self._get_price(h1)
            h2_price = self._get_price(h2)
            
            if h1_price > 0 and abs(h1_price - h2_price) / h1_price < self.PRICE_TOLERANCE:
                # Find neckline (lowest low between the tops)
                h1_idx = self._get_index(h1)
                h2_idx = self._get_index(h2)
                
                between_lows = [l for l in lows if h1_idx < self._get_index(l) < h2_idx]
                if between_lows:
                    neckline = min(between_lows, key=lambda x: self._get_price(x))
                    
                    geometry = {
                        "peaks": [
                            {"time": self._get_index(h1), "price": h1_price},
                            {"time": self._get_index(h2), "price": h2_price},
                        ],
                        "neckline": {"time": self._get_index(neckline), "price": self._get_price(neckline)},
                    }
                    
                    print(f"[PatternV3] Double Top detected")
                    
                    return PatternResult(
                        type="double_top",
                        direction="bearish",
                        confidence=0.80,
                        geometry=geometry,
                        touches_upper=2,
                        touches_lower=1,
                    )
        
        # Check double bottom
        if len(lows) >= 2:
            l1, l2 = lows[-2], lows[-1]
            l1_price = self._get_price(l1)
            l2_price = self._get_price(l2)
            
            if l1_price > 0 and abs(l1_price - l2_price) / l1_price < self.PRICE_TOLERANCE:
                # Find neckline (highest high between the bottoms)
                l1_idx = self._get_index(l1)
                l2_idx = self._get_index(l2)
                
                between_highs = [h for h in highs if l1_idx < self._get_index(h) < l2_idx]
                if between_highs:
                    neckline = max(between_highs, key=lambda x: self._get_price(x))
                    
                    geometry = {
                        "troughs": [
                            {"time": self._get_index(l1), "price": l1_price},
                            {"time": self._get_index(l2), "price": l2_price},
                        ],
                        "neckline": {"time": self._get_index(neckline), "price": self._get_price(neckline)},
                    }
                    
                    print(f"[PatternV3] Double Bottom detected")
                    
                    return PatternResult(
                        type="double_bottom",
                        direction="bullish",
                        confidence=0.80,
                        geometry=geometry,
                        touches_upper=1,
                        touches_lower=2,
                    )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # HEAD & SHOULDERS DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def detect_head_shoulders(self, highs: List[Dict], lows: List[Dict], all_points: List[Dict]) -> Optional[PatternResult]:
        """
        Detect Head & Shoulders pattern.
        
        H&S: left_shoulder < head > right_shoulder, with neckline
        """
        if len(highs) < 3:
            return None
        
        # Check last 3 highs
        left, head, right = highs[-3], highs[-2], highs[-1]
        
        left_price = self._get_price(left)
        head_price = self._get_price(head)
        right_price = self._get_price(right)
        
        # Head must be highest
        if not (head_price > left_price and head_price > right_price):
            return None
        
        # Shoulders should be similar height
        if abs(left_price - right_price) / left_price > 0.05:  # 5% tolerance
            return None
        
        # Find neckline from lows between shoulders
        left_idx = self._get_index(left)
        head_idx = self._get_index(head)
        right_idx = self._get_index(right)
        
        neckline_lows = [l for l in lows if left_idx < self._get_index(l) < right_idx]
        
        if len(neckline_lows) < 2:
            return None
        
        # Fit neckline
        nl_slope, nl_intercept = self._fit_line(neckline_lows)
        
        geometry = {
            "markers": {
                "left_shoulder": {"time": left_idx, "price": left_price},
                "head": {"time": head_idx, "price": head_price},
                "right_shoulder": {"time": right_idx, "price": right_price},
            },
            "neckline": {
                "slope": nl_slope,
                "intercept": nl_intercept,
                "points": [
                    {"time": self._get_index(neckline_lows[0]), "price": self._get_price(neckline_lows[0])},
                    {"time": self._get_index(neckline_lows[-1]), "price": self._get_price(neckline_lows[-1])},
                ],
            },
        }
        
        print(f"[PatternV3] Head & Shoulders detected")
        
        return PatternResult(
            type="head_shoulders",
            direction="bearish",
            confidence=0.85,
            geometry=geometry,
            touches_upper=3,
            touches_lower=len(neckline_lows),
        )
    
    # ═══════════════════════════════════════════════════════════════
    # GEOMETRY BUILDER
    # ═══════════════════════════════════════════════════════════════
    
    def _build_line_geometry(
        self,
        highs: List[Dict],
        lows: List[Dict],
        h_slope: float,
        h_intercept: float,
        l_slope: float,
        l_intercept: float
    ) -> Dict[str, Any]:
        """Build geometry for line-based patterns (triangles, channels)."""
        
        all_points = highs + lows
        x_min = min(self._get_index(p) for p in all_points)
        x_max = max(self._get_index(p) for p in all_points)
        
        # Extended lines for rendering
        upper_line = [
            {"time": x_min, "price": self._line_value(h_slope, h_intercept, x_min)},
            {"time": x_max, "price": self._line_value(h_slope, h_intercept, x_max)},
        ]
        
        lower_line = [
            {"time": x_min, "price": self._line_value(l_slope, l_intercept, x_min)},
            {"time": x_max, "price": self._line_value(l_slope, l_intercept, x_max)},
        ]
        
        return {
            "upper": upper_line,
            "lower": lower_line,
            "anchor_highs": [{"time": self._get_index(h), "price": self._get_price(h)} for h in highs],
            "anchor_lows": [{"time": self._get_index(l), "price": self._get_price(l)} for l in lows],
        }
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN DETECTION ENTRY
    # ═══════════════════════════════════════════════════════════════
    
    def detect(self, structure_data: Dict[str, Any]) -> List[PatternResult]:
        """
        Run all pattern detectors on structure.
        
        Args:
            structure_data: Output from StructureBuilder.build()
        
        Returns:
            List of detected patterns
        """
        highs = structure_data.get("highs", [])
        lows = structure_data.get("lows", [])
        all_points = structure_data.get("structure", [])
        
        if len(all_points) < 4:
            print(f"[PatternV3] Not enough structure points: {len(all_points)}")
            return []
        
        patterns = []
        
        # Detect in priority order
        
        # 1. Head & Shoulders (most specific)
        hs = self.detect_head_shoulders(highs, lows, all_points)
        if hs:
            patterns.append(hs)
        
        # 2. Double Top/Bottom
        double = self.detect_double(highs, lows, all_points)
        if double:
            patterns.append(double)
        
        # 3. Triangle (before channel, as triangles are more specific)
        triangle = self.detect_triangle(highs, lows, all_points)
        if triangle:
            patterns.append(triangle)
        
        # 4. Channel (least specific)
        # Only if no triangle found (to avoid conflict)
        if not triangle:
            channel = self.detect_channel(highs, lows, all_points)
            if channel:
                patterns.append(channel)
        
        print(f"[PatternV3] Detected {len(patterns)} patterns")
        return patterns


# Factory function
def get_pattern_engine_v3(timeframe: str = "4H") -> PatternEngineV3:
    """Create pattern engine for timeframe."""
    return PatternEngineV3(timeframe)
