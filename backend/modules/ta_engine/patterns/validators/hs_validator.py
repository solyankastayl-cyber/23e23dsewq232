"""
Head and Shoulders Validator
============================
Validates Head & Shoulders (top) and Inverse H&S (bottom) patterns.

Requirements:
- Left shoulder
- Head (higher/lower than shoulders)
- Right shoulder (similar to left)
- Neckline connecting the valleys/peaks
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..pattern_candidate import PatternCandidate, PatternLine, PatternScores, PatternWindow


class HeadShouldersValidator:
    """Validates head and shoulders patterns."""
    
    pattern_type = "head_shoulders"
    
    MIN_SCORE_THRESHOLD = 0.55
    SHOULDER_TOLERANCE = 0.05  # 5% tolerance for shoulder symmetry
    HEAD_MIN_RATIO = 1.02      # Head must be at least 2% beyond shoulders
    
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
        """Try to find H&S or inverse H&S."""
        
        # Try H&S top
        result = self._validate_hs_top(candles, pivot_highs, pivot_lows, window, structure_context)
        if result:
            return result
        
        # Try inverse H&S
        result = self._validate_hs_bottom(candles, pivot_highs, pivot_lows, window, structure_context)
        return result
    
    def _validate_hs_top(
        self,
        candles: List[Dict],
        pivot_highs: List[Dict],
        pivot_lows: List[Dict],
        window: PatternWindow,
        context: Dict,
    ) -> Optional[PatternCandidate]:
        """Validate head and shoulders top pattern."""
        if len(pivot_highs) < 3:
            return None
        
        # Find potential head (highest high)
        for head_idx in range(1, len(pivot_highs) - 1):
            head = pivot_highs[head_idx]
            
            # Find left and right shoulders
            left_candidates = pivot_highs[:head_idx]
            right_candidates = pivot_highs[head_idx + 1:]
            
            for left in left_candidates:
                # Left shoulder must be lower than head
                if left["price"] >= head["price"] * (1 / self.HEAD_MIN_RATIO):
                    continue
                
                for right in right_candidates:
                    # Right shoulder must be lower than head
                    if right["price"] >= head["price"] * (1 / self.HEAD_MIN_RATIO):
                        continue
                    
                    # Shoulders should be similar
                    shoulder_diff = abs(left["price"] - right["price"]) / max(left["price"], right["price"])
                    if shoulder_diff > self.SHOULDER_TOLERANCE:
                        continue
                    
                    # Find neckline points (lows between shoulders and head)
                    nl_left = self._find_pivot_between(pivot_lows, left["index"], head["index"])
                    nl_right = self._find_pivot_between(pivot_lows, head["index"], right["index"])
                    
                    if not nl_left or not nl_right:
                        continue
                    
                    scores = self._score_hs(left, head, right, nl_left, nl_right, candles, context, "hs_top")
                    
                    if scores.total < self.MIN_SCORE_THRESHOLD:
                        continue
                    
                    neckline_level = (nl_left["price"] + nl_right["price"]) / 2
                    
                    return PatternCandidate(
                        pattern_id=str(uuid.uuid4()),
                        type="head_shoulders",
                        direction_bias="bearish",
                        state="forming",
                        window=window,
                        lines=[
                            PatternLine(
                                name="shoulders",
                                points=[
                                    {"time": left["time"], "value": left["price"]},
                                    {"time": right["time"], "value": right["price"]},
                                ],
                                touches=2,
                            ),
                            PatternLine(
                                name="head",
                                points=[
                                    {"time": left["time"], "value": head["price"]},
                                    {"time": right["time"], "value": head["price"]},
                                ],
                                touches=1,
                            ),
                            PatternLine(
                                name="neckline",
                                points=[
                                    {"time": nl_left["time"], "value": nl_left["price"]},
                                    {"time": nl_right["time"], "value": nl_right["price"]},
                                ],
                                touches=2,
                            ),
                        ],
                        breakout_level=round(neckline_level, 2),
                        invalidation_level=round(head["price"] * 1.02, 2),
                        scores=scores,
                        meta={
                            "shoulder_symmetry": round((1 - shoulder_diff) * 100, 2),
                            "head_prominence": round((head["price"] / left["price"] - 1) * 100, 2),
                        }
                    )
        
        return None
    
    def _validate_hs_bottom(
        self,
        candles: List[Dict],
        pivot_highs: List[Dict],
        pivot_lows: List[Dict],
        window: PatternWindow,
        context: Dict,
    ) -> Optional[PatternCandidate]:
        """Validate inverse head and shoulders pattern."""
        if len(pivot_lows) < 3:
            return None
        
        for head_idx in range(1, len(pivot_lows) - 1):
            head = pivot_lows[head_idx]
            
            left_candidates = pivot_lows[:head_idx]
            right_candidates = pivot_lows[head_idx + 1:]
            
            for left in left_candidates:
                if left["price"] <= head["price"] * self.HEAD_MIN_RATIO:
                    continue
                
                for right in right_candidates:
                    if right["price"] <= head["price"] * self.HEAD_MIN_RATIO:
                        continue
                    
                    shoulder_diff = abs(left["price"] - right["price"]) / max(left["price"], right["price"])
                    if shoulder_diff > self.SHOULDER_TOLERANCE:
                        continue
                    
                    nl_left = self._find_pivot_between(pivot_highs, left["index"], head["index"], high=True)
                    nl_right = self._find_pivot_between(pivot_highs, head["index"], right["index"], high=True)
                    
                    if not nl_left or not nl_right:
                        continue
                    
                    scores = self._score_hs(left, head, right, nl_left, nl_right, candles, context, "hs_bottom")
                    
                    if scores.total < self.MIN_SCORE_THRESHOLD:
                        continue
                    
                    neckline_level = (nl_left["price"] + nl_right["price"]) / 2
                    
                    return PatternCandidate(
                        pattern_id=str(uuid.uuid4()),
                        type="inverse_head_shoulders",
                        direction_bias="bullish",
                        state="forming",
                        window=window,
                        lines=[
                            PatternLine(
                                name="shoulders",
                                points=[
                                    {"time": left["time"], "value": left["price"]},
                                    {"time": right["time"], "value": right["price"]},
                                ],
                                touches=2,
                            ),
                            PatternLine(
                                name="head",
                                points=[
                                    {"time": left["time"], "value": head["price"]},
                                    {"time": right["time"], "value": head["price"]},
                                ],
                                touches=1,
                            ),
                            PatternLine(
                                name="neckline",
                                points=[
                                    {"time": nl_left["time"], "value": nl_left["price"]},
                                    {"time": nl_right["time"], "value": nl_right["price"]},
                                ],
                                touches=2,
                            ),
                        ],
                        breakout_level=round(neckline_level, 2),
                        invalidation_level=round(head["price"] * 0.98, 2),
                        scores=scores,
                        meta={
                            "shoulder_symmetry": round((1 - shoulder_diff) * 100, 2),
                            "head_depth": round((1 - head["price"] / left["price"]) * 100, 2),
                        }
                    )
        
        return None
    
    def _find_pivot_between(
        self, 
        pivots: List[Dict], 
        start: int, 
        end: int,
        high: bool = False
    ) -> Optional[Dict]:
        """Find pivot between two indices."""
        between = [p for p in pivots if start < p["index"] < end]
        if not between:
            return None
        return max(between, key=lambda p: p["price"]) if high else min(between, key=lambda p: p["price"])
    
    def _score_hs(
        self,
        left: Dict, head: Dict, right: Dict,
        nl_left: Dict, nl_right: Dict,
        candles: List[Dict],
        context: Dict,
        pattern_type: str,
    ) -> PatternScores:
        """Score H&S pattern."""
        
        # Geometry: shoulder symmetry + head prominence
        shoulder_diff = abs(left["price"] - right["price"]) / max(left["price"], right["price"])
        head_ratio = head["price"] / ((left["price"] + right["price"]) / 2)
        geometry = (1 - shoulder_diff) * 0.5 + min((abs(1 - head_ratio) * 10), 0.5)
        
        # Touches
        touches = 0.85
        
        # Containment: neckline should be clear
        neckline_slope = (nl_right["price"] - nl_left["price"]) / max(nl_right["index"] - nl_left["index"], 1)
        containment = 0.8 if abs(neckline_slope) < 50 else 0.5
        
        # Context
        regime = context.get("regime", "unknown")
        if pattern_type == "hs_top":
            context_fit = 0.9 if regime in {"trend_up", "distribution"} else 0.5
        else:
            context_fit = 0.9 if regime in {"trend_down", "accumulation"} else 0.5
        
        # Recency
        age = len(candles) - 1 - right["index"]
        recency = 1.0 if age <= 10 else 0.7 if age <= 25 else 0.4
        
        return PatternScores(
            geometry=max(geometry, 0.4),
            touch_quality=touches,
            containment=containment,
            context_fit=context_fit,
            recency=recency,
            cleanliness=0.7,
        )
