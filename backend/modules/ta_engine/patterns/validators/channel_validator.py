"""
Channel Validator
=================
Validates ascending, descending, and horizontal channels.

Channel requirements:
- Upper and lower lines nearly parallel
- Multiple touches on both sides
- Price oscillating between boundaries
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..pattern_candidate import PatternCandidate, PatternLine, PatternScores, PatternWindow


class ChannelValidator:
    """Validates channel patterns with parallel boundary lines."""
    
    pattern_type = "channel"
    
    MIN_TOUCHES = 2
    MIN_SCORE_THRESHOLD = 0.55
    MAX_SLOPE_DIFF_RATIO = 0.3  # Lines must be within 30% slope difference
    
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
        """Validate channel pattern in given window."""
        
        if len(pivot_highs) < self.MIN_TOUCHES or len(pivot_lows) < self.MIN_TOUCHES:
            return None
        
        upper = self._build_trendline(pivot_highs, "upper")
        lower = self._build_trendline(pivot_lows, "lower")
        
        if not upper or not lower:
            return None
        
        # Check if lines are parallel enough
        if not self._are_parallel(upper["slope"], lower["slope"]):
            return None
        
        channel_type, direction = self._classify_channel(upper["slope"], lower["slope"])
        
        # Calculate scores
        geometry = self._score_geometry(upper, lower)
        touches = self._score_touches(upper, lower)
        containment = self._score_containment(candles, upper, lower)
        context_fit = self._score_context(structure_context, channel_type)
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
        
        breakout_level, invalidation_level = self._get_levels(upper, lower, direction, candles)
        
        return PatternCandidate(
            pattern_id=str(uuid.uuid4()),
            type=channel_type,
            direction_bias=direction,
            state="forming",
            window=window,
            lines=[
                PatternLine(name="upper", points=upper["points"], touches=upper["touches"], slope=upper["slope"]),
                PatternLine(name="lower", points=lower["points"], touches=lower["touches"], slope=lower["slope"]),
            ],
            breakout_level=breakout_level,
            invalidation_level=invalidation_level,
            scores=scores,
            meta={
                "channel_width": upper["points"][-1]["value"] - lower["points"][-1]["value"],
                "slope_diff": abs(upper["slope"] - lower["slope"]),
            }
        )
    
    def _build_trendline(self, pivots: List[Dict[str, Any]], side: str = "upper") -> Optional[Dict[str, Any]]:
        """
        Build trendline using anchor-based approach (NOT regression).
        
        For channels, we select anchor points that best represent the boundary.
        """
        if len(pivots) < 2:
            return None
        
        recent = pivots[-4:]
        
        # === ANCHOR-BASED APPROACH ===
        # Select best two anchor points
        anchor1, anchor2 = self._select_anchors(recent, side)
        
        if not anchor1 or not anchor2:
            return None
        
        idx1, price1 = anchor1["index"], anchor1["price"]
        idx2, price2 = anchor2["index"], anchor2["price"]
        
        if idx2 == idx1:
            return None
        
        slope = (price2 - price1) / (idx2 - idx1)
        intercept = price1 - slope * idx1
        
        # Count touches
        tolerance_pct = 0.015
        touches = sum(
            1 for p in recent 
            if abs(p["price"] - (slope * p["index"] + intercept)) / p["price"] <= tolerance_pct
        )
        
        return {
            "points": [
                {"time": anchor1["time"], "value": round(price1, 2), "index": idx1},
                {"time": anchor2["time"], "value": round(price2, 2), "index": idx2},
            ],
            "touches": max(touches, 2),
            "slope": slope,
            "intercept": intercept,
        }
    
    def _select_anchors(
        self, 
        pivots: List[Dict[str, Any]], 
        side: str
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Select two best anchor points for line construction."""
        if len(pivots) < 2:
            return None, None
        
        prices = [p["price"] for p in pivots]
        mean_price = sum(prices) / len(prices)
        
        if side == "upper":
            scored = [(p, p["price"] - mean_price) for p in pivots]
        else:
            scored = [(p, mean_price - p["price"]) for p in pivots]
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        anchor1 = scored[0][0]
        anchor2 = None
        
        for p, _ in scored[1:]:
            if abs(p["index"] - anchor1["index"]) >= 2:
                anchor2 = p
                break
        
        if not anchor2 and len(scored) > 1:
            anchor2 = scored[1][0]
        
        if not anchor2:
            return None, None
        
        if anchor1["index"] > anchor2["index"]:
            anchor1, anchor2 = anchor2, anchor1
        
        return anchor1, anchor2
    
    def _are_parallel(self, slope1: float, slope2: float) -> bool:
        """Check if two slopes are parallel enough."""
        if abs(slope1) < 0.0001 and abs(slope2) < 0.0001:
            return True  # Both horizontal
        
        avg_slope = (abs(slope1) + abs(slope2)) / 2
        if avg_slope < 0.0001:
            return True
        
        diff_ratio = abs(slope1 - slope2) / avg_slope
        return diff_ratio < self.MAX_SLOPE_DIFF_RATIO
    
    def _classify_channel(self, upper_slope: float, lower_slope: float) -> Tuple[str, str]:
        """Classify channel type."""
        avg_slope = (upper_slope + lower_slope) / 2
        
        if avg_slope > 0.001:
            return "ascending_channel", "bullish"
        elif avg_slope < -0.001:
            return "descending_channel", "bearish"
        else:
            return "horizontal_channel", "neutral"
    
    def _score_geometry(self, upper: Dict, lower: Dict) -> float:
        """Score based on parallelism."""
        slope_diff = abs(upper["slope"] - lower["slope"])
        avg = (abs(upper["slope"]) + abs(lower["slope"])) / 2
        if avg < 0.0001:
            return 0.9  # Horizontal channel
        return max(0.4, 1.0 - (slope_diff / avg))
    
    def _score_touches(self, upper: Dict, lower: Dict) -> float:
        return min((upper["touches"] + lower["touches"]) / 8.0, 1.0)
    
    def _score_containment(self, candles: List[Dict], upper: Dict, lower: Dict) -> float:
        if not candles:
            return 0.5
        violations = 0
        total = len(candles[-30:])
        for i, c in enumerate(candles[-30:]):
            idx = len(candles) - 30 + i
            u_val = upper["slope"] * idx + upper["intercept"]
            l_val = lower["slope"] * idx + lower["intercept"]
            if c["high"] > u_val * 1.03 or c["low"] < l_val * 0.97:
                violations += 1
        return 1.0 - (violations / total) if total > 0 else 0.5
    
    def _score_context(self, context: Dict, channel_type: str) -> float:
        regime = context.get("regime", "unknown")
        if channel_type == "ascending_channel" and regime in {"trend_up", "range"}:
            return 0.85
        if channel_type == "descending_channel" and regime in {"trend_down", "range"}:
            return 0.85
        if channel_type == "horizontal_channel" and regime == "range":
            return 0.9
        return 0.5
    
    def _score_recency(self, window: PatternWindow, total: int) -> float:
        age = total - 1 - window.end_index
        return 1.0 if age <= 5 else 0.8 if age <= 15 else 0.5
    
    def _score_cleanliness(self, candles: List[Dict], upper: Dict, lower: Dict) -> float:
        return 0.75  # Simplified
    
    def _get_levels(self, upper: Dict, lower: Dict, direction: str, candles: List[Dict]) -> Tuple[float, float]:
        idx = len(candles) - 1
        u_now = upper["slope"] * idx + upper["intercept"]
        l_now = lower["slope"] * idx + lower["intercept"]
        
        if direction == "bullish":
            return round(u_now, 2), round(l_now, 2)
        elif direction == "bearish":
            return round(l_now, 2), round(u_now, 2)
        return round(u_now, 2), round(l_now, 2)
