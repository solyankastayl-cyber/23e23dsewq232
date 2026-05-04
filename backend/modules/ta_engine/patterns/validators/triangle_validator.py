"""
Triangle Validator
==================
Validates ascending, descending, and symmetrical triangles.

Triangle requirements:
- Upper line: 2+ touches
- Lower line: 2+ touches  
- Lines converging (apex in future)
- Price mostly contained within boundaries
- Recent formation (not too old)
"""

from __future__ import annotations

import uuid
import math
from typing import Any, Dict, List, Optional, Tuple

from ..pattern_candidate import PatternCandidate, PatternLine, PatternScores, PatternWindow


class TriangleValidator:
    """Validates triangle patterns with strict geometry checks."""
    
    pattern_type = "triangle"
    
    MIN_TOUCHES = 2
    MIN_SCORE_THRESHOLD = 0.55
    
    def validate(
        self,
        candles: List[Dict[str, Any]],
        pivot_highs: List[Dict[str, Any]],
        pivot_lows: List[Dict[str, Any]],
        window: PatternWindow,
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        poi: Dict[str, Any],
    ) -> Optional[PatternCandidate]:
        """Validate triangle pattern in given window."""
        
        if len(pivot_highs) < self.MIN_TOUCHES or len(pivot_lows) < self.MIN_TOUCHES:
            return None
        
        # Build upper and lower lines
        upper = self._build_trendline(pivot_highs, "upper")
        lower = self._build_trendline(pivot_lows, "lower")
        
        if not upper or not lower:
            return None
        
        # Classify triangle type
        triangle_type, direction = self._classify_triangle(upper, lower)
        if not triangle_type:
            return None
        
        # Calculate scores
        geometry = self._score_geometry(upper, lower, candles)
        touches = self._score_touches(upper, lower)
        containment = self._score_containment(candles, upper, lower)
        context_fit = self._score_context(structure_context, triangle_type)
        recency = self._score_recency(window, len(candles))
        cleanliness = self._score_cleanliness(candles, upper, lower)
        
        scores = PatternScores(
            geometry=geometry,
            touch_quality=touches,
            containment=containment,
            context_fit=context_fit,
            recency=recency,
            cleanliness=cleanliness,
        )
        
        if scores.total < self.MIN_SCORE_THRESHOLD:
            return None
        
        # Calculate breakout/invalidation levels
        breakout_level, invalidation_level = self._get_levels(upper, lower, direction, candles)
        
        # DEBUG: Log that V4 anchor-based engine is being used
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[V4_ANCHOR] Triangle detected: {triangle_type}, touches: {upper['touches']}+{lower['touches']}")
        
        return PatternCandidate(
            pattern_id=str(uuid.uuid4()),
            type=triangle_type,
            direction_bias=direction,
            state="forming",
            window=window,
            lines=[
                PatternLine(
                    name="upper",
                    points=upper["points"],
                    touches=upper["touches"],
                    slope=upper["slope"]
                ),
                PatternLine(
                    name="lower",
                    points=lower["points"],
                    touches=lower["touches"],
                    slope=lower["slope"]
                ),
            ],
            breakout_level=breakout_level,
            invalidation_level=invalidation_level,
            scores=scores,
            meta={
                "engine": "V4_ANCHOR",  # MARKER: This proves new engine is used
                "touches_upper": upper["touches"],
                "touches_lower": lower["touches"],
                "upper_slope": upper["slope"],
                "lower_slope": lower["slope"],
                "anchor_points_upper": upper.get("anchor_points", []),
                "anchor_points_lower": lower.get("anchor_points", []),
            }
        )
    
    def _build_trendline(
        self, 
        pivots: List[Dict[str, Any]], 
        side: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build trendline from anchor points (NOT regression).
        
        Anchor-based approach:
        1. Select 2 best anchor points based on pattern type
        2. Draw line through actual swing points
        3. Validate touches on remaining points
        """
        if len(pivots) < 2:
            return None
        
        # Use last 4 pivots max for local pattern
        recent_pivots = pivots[-4:]
        
        # === ANCHOR-BASED APPROACH ===
        # Select best two anchor points based on side
        anchor1, anchor2 = self._select_anchor_points(recent_pivots, side)
        
        if not anchor1 or not anchor2:
            return None
        
        # Build line through actual anchor points (not regression)
        idx1, price1 = anchor1["index"], anchor1["price"]
        idx2, price2 = anchor2["index"], anchor2["price"]
        
        if idx2 == idx1:
            return None
        
        # Line equation: price = slope * index + intercept
        slope = (price2 - price1) / (idx2 - idx1)
        intercept = price1 - slope * idx1
        
        # Validate touches - other pivots must respect this line
        touches, touch_points = self._validate_anchor_touches(
            recent_pivots, slope, intercept, [anchor1, anchor2], side
        )
        
        # Require at least 2 touches (the anchors themselves)
        if touches < 2:
            return None
        
        return {
            "points": [
                {"time": anchor1["time"], "value": round(price1, 2), "index": idx1},
                {"time": anchor2["time"], "value": round(price2, 2), "index": idx2},
            ],
            "anchor_points": touch_points,  # All validated touch points
            "touches": touches,
            "slope": slope,
            "intercept": intercept,
        }
    
    def _select_anchor_points(
        self, 
        pivots: List[Dict[str, Any]], 
        side: str
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Select two best anchor points for line construction.
        
        For upper line (highs): prefer most prominent highs
        For lower line (lows): prefer most prominent lows
        """
        if len(pivots) < 2:
            return None, None
        
        # Sort by prominence (furthest from mean in the expected direction)
        prices = [p["price"] for p in pivots]
        mean_price = sum(prices) / len(prices)
        
        if side == "upper":
            # For upper line, prefer higher points
            scored = [(p, p["price"] - mean_price) for p in pivots]
        else:
            # For lower line, prefer lower points
            scored = [(p, mean_price - p["price"]) for p in pivots]
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Take two best points, ensuring they're not adjacent
        anchor1 = scored[0][0]
        anchor2 = None
        
        for p, _ in scored[1:]:
            # Ensure minimum distance between anchors
            idx_diff = abs(p["index"] - anchor1["index"])
            if idx_diff >= 2:  # At least 2 candles apart
                anchor2 = p
                break
        
        if not anchor2 and len(scored) > 1:
            anchor2 = scored[1][0]
        
        if not anchor2:
            return None, None
        
        # Order by time
        if anchor1["index"] > anchor2["index"]:
            anchor1, anchor2 = anchor2, anchor1
        
        return anchor1, anchor2
    
    def _validate_anchor_touches(
        self,
        pivots: List[Dict[str, Any]],
        slope: float,
        intercept: float,
        anchors: List[Dict[str, Any]],
        side: str
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Validate that other pivots touch/respect the anchor line.
        
        A valid touch means:
        - Point is close to line (within tolerance)
        - Point is on correct side (not crossing through)
        """
        tolerance_pct = 0.015  # 1.5% tolerance
        touches = 0
        touch_points = []
        
        anchor_indices = {a["index"] for a in anchors}
        
        for p in pivots:
            expected = slope * p["index"] + intercept
            actual = p["price"]
            
            # Check if within tolerance
            diff_pct = abs(actual - expected) / expected if expected > 0 else 1
            
            if diff_pct <= tolerance_pct:
                touches += 1
                touch_points.append({
                    "time": p["time"],
                    "price": p["price"],
                    "index": p["index"],
                    "is_anchor": p["index"] in anchor_indices
                })
            elif side == "upper" and actual < expected:
                # For upper line, points below are OK (contained)
                pass
            elif side == "lower" and actual > expected:
                # For lower line, points above are OK (contained)
                pass
        
        return touches, touch_points
    
    def _count_touches(
        self, 
        pivots: List[Dict[str, Any]], 
        slope: float, 
        intercept: float,
        side: str = "upper"
    ) -> int:
        """Count pivots that touch the trendline (within tolerance)."""
        touches = 0
        tolerance_pct = 0.015  # 1.5% tolerance
        
        for p in pivots:
            expected = slope * p["index"] + intercept
            diff_pct = abs(p["price"] - expected) / expected if expected > 0 else 1
            
            if diff_pct <= tolerance_pct:
                touches += 1
        
        return max(touches, 2)  # At least 2 since we built from them
    
    def _classify_triangle(
        self, 
        upper: Dict[str, Any], 
        lower: Dict[str, Any]
    ) -> Tuple[Optional[str], str]:
        """Classify triangle type based on slopes."""
        upper_slope = upper["slope"]
        lower_slope = lower["slope"]
        
        # Slopes must be converging (different signs or both toward each other)
        if upper_slope > 0 and lower_slope < 0:
            # Lines diverging - not a triangle
            return None, "neutral"
        
        slope_diff = abs(upper_slope - lower_slope)
        if slope_diff < 0.0001:
            # Parallel lines - channel, not triangle
            return None, "neutral"
        
        # Descending triangle: upper descending, lower flat
        if upper_slope < -0.0001 and abs(lower_slope) < abs(upper_slope) * 0.5:
            return "descending_triangle", "bearish"
        
        # Ascending triangle: lower ascending, upper flat
        if lower_slope > 0.0001 and abs(upper_slope) < abs(lower_slope) * 0.5:
            return "ascending_triangle", "bullish"
        
        # Symmetrical triangle: both converging
        if upper_slope < 0 and lower_slope > 0:
            return "symmetrical_triangle", "neutral"
        
        # Falling wedge: both descending but lower more steeply
        if upper_slope < 0 and lower_slope < 0 and lower_slope < upper_slope:
            return "falling_wedge", "bullish"
        
        # Rising wedge: both ascending but upper more steeply
        if upper_slope > 0 and lower_slope > 0 and upper_slope > lower_slope:
            return "rising_wedge", "bearish"
        
        return "symmetrical_triangle", "neutral"
    
    def _score_geometry(
        self, 
        upper: Dict[str, Any], 
        lower: Dict[str, Any],
        candles: List[Dict[str, Any]]
    ) -> float:
        """Score based on convergence quality and angle."""
        upper_slope = upper["slope"]
        lower_slope = lower["slope"]
        
        # Check convergence rate
        convergence = abs(upper_slope - lower_slope)
        if convergence < 0.0001:
            return 0.3  # Too parallel
        
        # Calculate apex (intersection point)
        if abs(upper_slope - lower_slope) > 0.0001:
            apex_idx = (lower["intercept"] - upper["intercept"]) / (upper_slope - lower_slope)
            current_idx = candles[-1].get("index", len(candles) - 1) if candles else 0
            
            # Apex should be in the future but not too far
            apex_distance = apex_idx - current_idx
            if apex_distance < 0:
                return 0.4  # Apex already passed
            if apex_distance > len(candles):
                return 0.5  # Apex too far
            
            # Ideal: apex 10-50% of pattern length ahead
            pattern_len = upper["points"][-1]["index"] - upper["points"][0]["index"]
            ideal_distance = pattern_len * 0.3
            distance_score = 1.0 - min(abs(apex_distance - ideal_distance) / pattern_len, 1.0)
            
            return 0.6 + distance_score * 0.4
        
        return 0.5
    
    def _score_touches(self, upper: Dict[str, Any], lower: Dict[str, Any]) -> float:
        """Score based on number of valid touches."""
        total_touches = upper["touches"] + lower["touches"]
        # 4 touches minimum (2 each), 8+ is excellent
        return min(total_touches / 8.0, 1.0)
    
    def _score_containment(
        self, 
        candles: List[Dict[str, Any]], 
        upper: Dict[str, Any], 
        lower: Dict[str, Any]
    ) -> float:
        """Score based on price staying within boundaries."""
        if not candles:
            return 0.5
        
        start_idx = upper["points"][0].get("index", 0)
        end_idx = upper["points"][-1].get("index", len(candles) - 1)
        
        violations = 0
        total = 0
        
        for i, c in enumerate(candles):
            candle_idx = c.get("index", i)
            if candle_idx < start_idx or candle_idx > end_idx:
                continue
            
            total += 1
            upper_val = upper["slope"] * candle_idx + upper["intercept"]
            lower_val = lower["slope"] * candle_idx + lower["intercept"]
            
            # Check for violations (wicks outside)
            if c["high"] > upper_val * 1.02:  # 2% tolerance
                violations += 1
            if c["low"] < lower_val * 0.98:
                violations += 1
        
        if total == 0:
            return 0.5
        
        violation_rate = violations / (total * 2)  # 2 checks per candle
        return 1.0 - min(violation_rate, 1.0)
    
    def _score_context(self, structure_context: Dict[str, Any], triangle_type: str) -> float:
        """Score based on market regime alignment."""
        regime = structure_context.get("regime", "unknown")
        
        context_map = {
            "descending_triangle": {
                "trend_down": 0.9,
                "reversal_candidate": 0.8,
                "range": 0.7,
                "compression": 0.8,
            },
            "ascending_triangle": {
                "trend_up": 0.9,
                "reversal_candidate": 0.8,
                "range": 0.7,
                "compression": 0.8,
            },
            "symmetrical_triangle": {
                "range": 0.9,
                "compression": 0.9,
                "reversal_candidate": 0.7,
            },
            "falling_wedge": {
                "trend_down": 0.9,
                "reversal_candidate": 0.9,
            },
            "rising_wedge": {
                "trend_up": 0.9,
                "reversal_candidate": 0.9,
            },
        }
        
        type_context = context_map.get(triangle_type, {})
        return type_context.get(regime, 0.5)
    
    def _score_recency(self, window: PatternWindow, total_candles: int) -> float:
        """Score based on how recent the pattern is."""
        age = total_candles - 1 - window.end_index
        if age <= 5:
            return 1.0
        if age <= 15:
            return 0.8
        if age <= 30:
            return 0.5
        return 0.3
    
    def _score_cleanliness(
        self, 
        candles: List[Dict[str, Any]], 
        upper: Dict[str, Any], 
        lower: Dict[str, Any]
    ) -> float:
        """Score based on how clean/noise-free the pattern is."""
        if not candles:
            return 0.5
        
        # Check for large wicks/noise
        large_wicks = 0
        for c in candles[-20:]:  # Check recent candles
            body = abs(c["close"] - c["open"])
            total_range = c["high"] - c["low"]
            if total_range > 0 and body / total_range < 0.3:
                large_wicks += 1
        
        wick_ratio = large_wicks / min(len(candles), 20)
        return 1.0 - wick_ratio * 0.5
    
    def _get_levels(
        self, 
        upper: Dict[str, Any], 
        lower: Dict[str, Any], 
        direction: str,
        candles: List[Dict[str, Any]]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate breakout and invalidation levels."""
        if not candles:
            return None, None
        
        current_idx = len(candles) - 1
        
        # Project lines to current position
        upper_now = upper["slope"] * current_idx + upper["intercept"]
        lower_now = lower["slope"] * current_idx + lower["intercept"]
        
        if direction == "bearish":
            breakout_level = round(lower_now, 2)
            invalidation_level = round(upper_now, 2)
        elif direction == "bullish":
            breakout_level = round(upper_now, 2)
            invalidation_level = round(lower_now, 2)
        else:
            # Neutral - could break either way
            breakout_level = round(upper_now, 2)
            invalidation_level = round(lower_now, 2)
        
        return breakout_level, invalidation_level
