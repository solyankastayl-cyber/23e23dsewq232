"""
Double Pattern Validator
========================
Validates Double Top and Double Bottom patterns.

Requirements:
- Two peaks/valleys at similar price levels
- Clear neckline
- Neckline break for confirmation
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..pattern_candidate import PatternCandidate, PatternLine, PatternScores, PatternWindow


class DoublePatternValidator:
    """Validates double top and double bottom patterns."""
    
    pattern_type = "double"
    
    MIN_SCORE_THRESHOLD = 0.55
    PRICE_TOLERANCE = 0.03  # 3% tolerance for matching peaks/valleys
    
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
        """Try to find double top or double bottom."""
        
        # Try double top first
        result = self._validate_double_top(candles, pivot_highs, pivot_lows, window, structure_context)
        if result:
            return result
        
        # Try double bottom
        result = self._validate_double_bottom(candles, pivot_highs, pivot_lows, window, structure_context)
        return result
    
    def _validate_double_top(
        self,
        candles: List[Dict],
        pivot_highs: List[Dict],
        pivot_lows: List[Dict],
        window: PatternWindow,
        structure_context: Dict,
    ) -> Optional[PatternCandidate]:
        """Validate double top pattern."""
        if len(pivot_highs) < 2:
            return None
        
        # Find two similar highs
        for i in range(len(pivot_highs) - 1):
            h1 = pivot_highs[i]
            for j in range(i + 1, len(pivot_highs)):
                h2 = pivot_highs[j]
                
                # Check price similarity
                price_diff = abs(h1["price"] - h2["price"]) / max(h1["price"], h2["price"])
                if price_diff > self.PRICE_TOLERANCE:
                    continue
                
                # Find neckline (lowest low between the two highs)
                neckline = self._find_neckline_between(pivot_lows, h1["index"], h2["index"])
                if not neckline:
                    continue
                
                # Score the pattern
                scores = self._score_double_pattern(
                    h1, h2, neckline, candles, structure_context, "double_top"
                )
                
                if scores.total < self.MIN_SCORE_THRESHOLD:
                    continue
                
                avg_peak = (h1["price"] + h2["price"]) / 2
                
                return PatternCandidate(
                    pattern_id=str(uuid.uuid4()),
                    type="double_top",
                    direction_bias="bearish",
                    state="forming",
                    window=window,
                    lines=[
                        PatternLine(
                            name="peaks",
                            points=[
                                {"time": h1["time"], "value": h1["price"]},
                                {"time": h2["time"], "value": h2["price"]},
                            ],
                            touches=2,
                        ),
                        PatternLine(
                            name="neckline",
                            points=[
                                {"time": h1["time"], "value": neckline["price"]},
                                {"time": h2["time"], "value": neckline["price"]},
                            ],
                            touches=1,
                        ),
                    ],
                    breakout_level=round(neckline["price"], 2),
                    invalidation_level=round(avg_peak * 1.02, 2),
                    scores=scores,
                    meta={
                        "peak_diff_pct": round(price_diff * 100, 2),
                        "neckline_depth": round((avg_peak - neckline["price"]) / avg_peak * 100, 2),
                    }
                )
        
        return None
    
    def _validate_double_bottom(
        self,
        candles: List[Dict],
        pivot_highs: List[Dict],
        pivot_lows: List[Dict],
        window: PatternWindow,
        structure_context: Dict,
    ) -> Optional[PatternCandidate]:
        """Validate double bottom pattern."""
        if len(pivot_lows) < 2:
            return None
        
        for i in range(len(pivot_lows) - 1):
            l1 = pivot_lows[i]
            for j in range(i + 1, len(pivot_lows)):
                l2 = pivot_lows[j]
                
                price_diff = abs(l1["price"] - l2["price"]) / max(l1["price"], l2["price"])
                if price_diff > self.PRICE_TOLERANCE:
                    continue
                
                neckline = self._find_neckline_between(pivot_highs, l1["index"], l2["index"], high=True)
                if not neckline:
                    continue
                
                scores = self._score_double_pattern(
                    l1, l2, neckline, candles, structure_context, "double_bottom"
                )
                
                if scores.total < self.MIN_SCORE_THRESHOLD:
                    continue
                
                avg_valley = (l1["price"] + l2["price"]) / 2
                
                return PatternCandidate(
                    pattern_id=str(uuid.uuid4()),
                    type="double_bottom",
                    direction_bias="bullish",
                    state="forming",
                    window=window,
                    lines=[
                        PatternLine(
                            name="valleys",
                            points=[
                                {"time": l1["time"], "value": l1["price"]},
                                {"time": l2["time"], "value": l2["price"]},
                            ],
                            touches=2,
                        ),
                        PatternLine(
                            name="neckline",
                            points=[
                                {"time": l1["time"], "value": neckline["price"]},
                                {"time": l2["time"], "value": neckline["price"]},
                            ],
                            touches=1,
                        ),
                    ],
                    breakout_level=round(neckline["price"], 2),
                    invalidation_level=round(avg_valley * 0.98, 2),
                    scores=scores,
                    meta={
                        "valley_diff_pct": round(price_diff * 100, 2),
                        "neckline_height": round((neckline["price"] - avg_valley) / avg_valley * 100, 2),
                    }
                )
        
        return None
    
    def _find_neckline_between(
        self, 
        pivots: List[Dict], 
        start_idx: int, 
        end_idx: int,
        high: bool = False
    ) -> Optional[Dict]:
        """Find neckline pivot between two indices."""
        between = [p for p in pivots if start_idx < p["index"] < end_idx]
        if not between:
            return None
        if high:
            return max(between, key=lambda p: p["price"])
        return min(between, key=lambda p: p["price"])
    
    def _score_double_pattern(
        self,
        p1: Dict,
        p2: Dict,
        neckline: Dict,
        candles: List[Dict],
        context: Dict,
        pattern_type: str,
    ) -> PatternScores:
        """Score double top/bottom pattern."""
        
        # Geometry: how symmetric are the peaks/valleys
        price_diff = abs(p1["price"] - p2["price"]) / max(p1["price"], p2["price"])
        geometry = 1.0 - price_diff * 10  # Penalize difference
        
        # Touch quality
        touches = 0.8  # Fixed 2 touches
        
        # Containment: neckline should be significantly different from peaks
        avg_peak = (p1["price"] + p2["price"]) / 2
        neckline_depth = abs(avg_peak - neckline["price"]) / avg_peak
        containment = min(neckline_depth * 5, 1.0)  # 20%+ depth is excellent
        
        # Context fit
        regime = context.get("regime", "unknown")
        if pattern_type == "double_top":
            context_fit = 0.9 if regime in {"trend_up", "distribution"} else 0.5
        else:
            context_fit = 0.9 if regime in {"trend_down", "accumulation"} else 0.5
        
        # Recency
        total = len(candles)
        age = total - 1 - p2["index"]
        recency = 1.0 if age <= 10 else 0.7 if age <= 20 else 0.4
        
        return PatternScores(
            geometry=max(geometry, 0.3),
            touch_quality=touches,
            containment=containment,
            context_fit=context_fit,
            recency=recency,
            cleanliness=0.7,
        )
