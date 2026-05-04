"""
Pattern Validation Engine v2 with Best-Fit Boundary Selection
==============================================================

P0 GEOMETRY FIXES:
------------------
1. extendLine() - линии через весь паттерн, не p1→p2
2. pivot window filter - фильтр pivot по pattern_start
3. anchor penalty - штраф за слишком ранние anchor
4. violation hard filter - усиленный штраф + отсечка
5. confidence threshold - не показывать если < 0.6

Rules:
1. Each pattern type has its own validator
2. If ANY requirement fails → return None (no garbage)
3. Lines extend to END of chart (not p1→p2)
4. Better NO pattern than garbage pattern
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Pivot:
    """Swing point in price data."""
    index: int
    time: int
    value: float
    pivot_type: str  # "high" or "low"


@dataclass
class TrendLine:
    """Line built from exactly 2 pivots."""
    p1: Pivot
    p2: Pivot
    slope: float
    slope_normalized: float
    score: float = 0.0
    
    @classmethod
    def from_pivots(cls, p1: Pivot, p2: Pivot) -> 'TrendLine':
        dt = p2.time - p1.time
        if dt == 0:
            slope = 0
        else:
            slope = (p2.value - p1.value) / dt
        
        avg_price = (p1.value + p2.value) / 2
        slope_normalized = (slope * 86400) / avg_price if avg_price > 0 else 0
        
        return cls(p1=p1, p2=p2, slope=slope, slope_normalized=slope_normalized)
    
    def value_at_index(self, index: int) -> float:
        """Get line value at given index using slope."""
        if self.p2.index == self.p1.index:
            return self.p1.value
        slope_idx = (self.p2.value - self.p1.value) / (self.p2.index - self.p1.index)
        return self.p1.value + slope_idx * (index - self.p1.index)
    
    def extend_line(self, candles: List[Dict], pattern_start_index: int) -> List[Dict]:
        """
        P0.1 FIX: Extend line through ENTIRE pattern.
        
        NOT p1→p2, but pattern_start → chart_end
        This makes lines look like real trendlines.
        """
        # Start from pattern beginning (or p1 if later)
        start_index = max(pattern_start_index, self.p1.index)
        end_index = len(candles) - 1
        
        # Calculate prices at extended points
        start_price = self.value_at_index(start_index)
        end_price = self.value_at_index(end_index)
        
        # Get times from candles
        start_time = candles[start_index].get('time', candles[start_index].get('timestamp', 0))
        end_time = candles[end_index].get('time', candles[end_index].get('timestamp', 0))
        
        # Normalize timestamps
        if start_time > 1e12:
            start_time = start_time // 1000
        if end_time > 1e12:
            end_time = end_time // 1000
        
        return [
            {"time": start_time, "value": round(start_price, 2)},
            {"time": end_time, "value": round(end_price, 2)},
        ]
    
    def to_points(self) -> List[Dict]:
        """Legacy: Return p1→p2 points."""
        return [
            {"time": self.p1.time, "value": round(self.p1.value, 2)},
            {"time": self.p2.time, "value": round(self.p2.value, 2)},
        ]


class PatternValidatorV2:
    """
    Strict pattern validation with geometry fixes.
    """
    
    # Thresholds
    HORIZONTAL_SLOPE_THRESHOLD = 0.0003
    TOUCH_TOLERANCE = 0.008  # 0.8%
    MIN_PIVOTS_PER_LINE = 2
    PRICE_CONTAINMENT_RATIO = 0.70
    
    # P0.4: Violation thresholds (усиленные)
    VIOLATION_PENALTY = 6  # was 4
    MAX_VIOLATIONS = 3  # hard filter - отбрасываем линию если больше
    
    # P0.5: Confidence threshold
    MIN_CONFIDENCE = 0.60  # не показываем паттерн если ниже
    
    def __init__(self, timeframe: str = "1D", config: Dict = None):
        """
        Initialize with TF-specific config from Multi-Scale Analysis.
        
        Config can override:
        - pivot_window
        - pattern_window  
        - min_pivot_distance
        """
        # Use external config if provided (Multi-Scale Analysis)
        if config:
            self.pivot_window = config.get("pivot_window", 5)
            self.pattern_window = config.get("pattern_window", 120)
            self.MIN_PIVOT_DISTANCE = config.get("min_pivot_distance", 10)
        else:
            # Legacy: internal defaults by TF
            self.pivot_windows = {
                "4H": 3, "1D": 5, "7D": 9, "30D": 15, "180D": 25, "1Y": 40
            }
            self.pivot_window = self.pivot_windows.get(timeframe.upper(), 5)
            
            self.pattern_windows = {
                "4H": 80, "1D": 100, "7D": 250, "30D": 500, "180D": 800, "1Y": 1200
            }
            self.pattern_window = self.pattern_windows.get(timeframe.upper(), 120)
            
            self.min_pivot_distances = {
                "4H": 5, "1D": 8, "7D": 15, "30D": 30, "180D": 60, "1Y": 100
            }
            self.MIN_PIVOT_DISTANCE = self.min_pivot_distances.get(timeframe.upper(), 10)
        
        self._recent_candles: List[Dict] = []
        self._pattern_start_index: int = 0
    
    def find_pivots(self, candles: List[Dict]) -> Tuple[List[Pivot], List[Pivot]]:
        """Find pivot highs and lows within pattern window."""
        if len(candles) < self.pivot_window * 2 + 1:
            return [], []
        
        # Use only recent candles for pattern detection
        self._recent_candles = candles[-self.pattern_window:] if len(candles) > self.pattern_window else candles
        self._pattern_start_index = 0  # Start of recent_candles
        
        recent = self._recent_candles
        pivot_highs = []
        pivot_lows = []
        window = self.pivot_window
        
        for i in range(window, len(recent) - window):
            c = recent[i]
            high = c['high']
            low = c['low']
            time = c.get('timestamp', c.get('time', 0))
            if time > 1e12:
                time = time // 1000
            
            # Check pivot high
            is_pivot_high = True
            for j in range(1, window + 1):
                if high <= recent[i - j]['high'] or high <= recent[i + j]['high']:
                    is_pivot_high = False
                    break
            
            # Check pivot low
            is_pivot_low = True
            for j in range(1, window + 1):
                if low >= recent[i - j]['low'] or low >= recent[i + j]['low']:
                    is_pivot_low = False
                    break
            
            if is_pivot_high:
                pivot_highs.append(Pivot(index=i, time=time, value=high, pivot_type="high"))
            
            if is_pivot_low:
                pivot_lows.append(Pivot(index=i, time=time, value=low, pivot_type="low"))
        
        return pivot_highs, pivot_lows
    
    def filter_pivots_by_window(self, pivots: List[Pivot], min_index: int) -> List[Pivot]:
        """
        P0.2 FIX: Filter pivots to only include those within pattern window.
        No more "anchor from 6 months ago".
        """
        return [p for p in pivots if p.index >= min_index]
    
    def generate_line_candidates(self, pivots: List[Pivot]) -> List[TrendLine]:
        """Generate all candidate lines from pivot combinations."""
        lines = []
        for i in range(len(pivots)):
            for j in range(i + 1, len(pivots)):
                p1 = pivots[i]
                p2 = pivots[j]
                if abs(p2.index - p1.index) < self.MIN_PIVOT_DISTANCE:
                    continue
                line = TrendLine.from_pivots(p1, p2)
                lines.append(line)
        return lines
    
    def score_trendline(
        self, 
        line: TrendLine, 
        pivots: List[Pivot], 
        candles: List[Dict], 
        line_type: str,
        pattern_start: int
    ) -> Tuple[float, int]:
        """
        Score a trendline with P0.3 and P0.4 fixes.
        
        Returns: (score, violation_count)
        """
        touch_count = 0
        pivot_confirmations = 0
        candle_violations = 0
        tolerance = self.TOUCH_TOLERANCE
        
        # Score candle touches and violations
        for i in range(line.p1.index, min(line.p2.index + 1, len(candles))):
            if i < 0 or i >= len(candles):
                continue
            candle = candles[i]
            expected_price = line.value_at_index(i)
            
            if line_type == "high":
                price = candle['high']
                distance = abs(price - expected_price) / expected_price if expected_price > 0 else 1
                if distance < tolerance:
                    touch_count += 1
                # Violation: price breaks above line
                if price > expected_price * (1 + tolerance * 1.5):
                    candle_violations += 1
            else:
                price = candle['low']
                distance = abs(price - expected_price) / expected_price if expected_price > 0 else 1
                if distance < tolerance:
                    touch_count += 1
                # Violation: price breaks below line
                if price < expected_price * (1 - tolerance * 1.5):
                    candle_violations += 1
        
        # Score pivot confirmations
        for pivot in pivots:
            if pivot.index < line.p1.index or pivot.index > line.p2.index:
                continue
            expected_price = line.value_at_index(pivot.index)
            dist = abs(pivot.value - expected_price) / expected_price if expected_price > 0 else 1
            if dist < tolerance:
                pivot_confirmations += 1
        
        # Time span bonus (prefer longer patterns)
        time_span = line.p2.index - line.p1.index
        time_bonus = min(time_span / 50, 2.0)
        
        # P0.3 FIX: Anchor penalty - штраф за слишком ранний anchor
        anchor_distance = line.p1.index - pattern_start
        anchor_penalty = max(0, anchor_distance) / 30  # Штраф за каждые 30 свечей от начала
        
        # Calculate final score
        # P0.4 FIX: Усиленный штраф за violations (6 вместо 4)
        score = (
            touch_count * 2 +
            pivot_confirmations * 3 -
            candle_violations * self.VIOLATION_PENALTY +
            time_bonus -
            anchor_penalty
        )
        
        return score, candle_violations
    
    def find_best_line(
        self, 
        pivots: List[Pivot], 
        candles: List[Dict],
        line_type: str,
        slope_constraint: Optional[str] = None,
        pattern_start: int = 0
    ) -> Optional[TrendLine]:
        """
        V4 ANCHOR-BASED: Build line from best anchor points (NOT regression/scoring).
        
        Key principle:
        - Select 2 BEST anchor points for the pattern type
        - Draw line directly through them
        - Validate that other pivots respect this line
        """
        if len(pivots) < 2:
            return None
        
        # === ANCHOR SELECTION (not all combinations) ===
        anchor1, anchor2 = self._select_best_anchors(pivots, line_type, slope_constraint)
        
        if not anchor1 or not anchor2:
            return None
        
        # Build line through actual anchors
        line = TrendLine.from_pivots(anchor1, anchor2)
        
        # Check slope constraint
        if slope_constraint == "descending" and line.slope_normalized >= 0:
            return None
        elif slope_constraint == "ascending" and line.slope_normalized <= 0:
            return None
        elif slope_constraint == "horizontal" and abs(line.slope_normalized) > self.HORIZONTAL_SLOPE_THRESHOLD:
            return None
        
        # Validate touches
        touch_count = self._count_anchor_touches(line, pivots, line_type)
        if touch_count < self.MIN_PIVOTS_PER_LINE:
            return None
        
        # Check for violations
        violations = self._count_violations(line, candles, line_type)
        if violations > self.MAX_VIOLATIONS:
            return None
        
        line.score = touch_count * 3 - violations * 2
        return line
    
    def _select_best_anchors(
        self,
        pivots: List[Pivot],
        line_type: str,
        slope_constraint: Optional[str]
    ) -> Tuple[Optional[Pivot], Optional[Pivot]]:
        """
        V4 ANCHOR SELECTION: Pick 2 best pivots for the line.
        
        For upper line (highs): prefer most prominent highs
        For lower line (lows): prefer most prominent lows
        """
        if len(pivots) < 2:
            return None, None
        
        # Sort by prominence (price extremeness)
        prices = [p.value for p in pivots]
        mean_price = sum(prices) / len(prices)
        
        if line_type == "high":
            # For upper line, prefer higher points
            scored = [(p, p.value - mean_price) for p in pivots]
        else:
            # For lower line, prefer lower points  
            scored = [(p, mean_price - p.value) for p in pivots]
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Take best point as first anchor
        anchor1 = scored[0][0]
        anchor2 = None
        
        # Find second anchor with proper separation and slope direction
        for p, _ in scored[1:]:
            idx_diff = abs(p.index - anchor1.index)
            if idx_diff < self.MIN_PIVOT_DISTANCE:
                continue
            
            # Check slope direction if constrained
            if slope_constraint:
                test_slope = (p.value - anchor1.value) / (p.index - anchor1.index) if p.index != anchor1.index else 0
                # Normalize by price
                normalized_slope = (test_slope * 86400) / mean_price if mean_price > 0 else 0
                
                if slope_constraint == "descending" and normalized_slope >= 0:
                    continue
                elif slope_constraint == "ascending" and normalized_slope <= 0:
                    continue
                elif slope_constraint == "horizontal" and abs(normalized_slope) > self.HORIZONTAL_SLOPE_THRESHOLD:
                    continue
            
            anchor2 = p
            break
        
        # Fallback: just take second best if no valid found
        if not anchor2 and len(scored) > 1:
            anchor2 = scored[1][0]
        
        if not anchor2:
            return None, None
        
        # Order by index (earlier first)
        if anchor1.index > anchor2.index:
            anchor1, anchor2 = anchor2, anchor1
        
        return anchor1, anchor2
    
    def _count_anchor_touches(
        self, 
        line: TrendLine, 
        pivots: List[Pivot],
        line_type: str
    ) -> int:
        """Count pivots that touch the anchor line (within tolerance)."""
        touches = 0
        for p in pivots:
            expected = line.value_at_index(p.index)
            if expected <= 0:
                continue
            diff_pct = abs(p.value - expected) / expected
            if diff_pct <= self.TOUCH_TOLERANCE:
                touches += 1
        return max(touches, 2)  # At least 2 (the anchors)
    
    def _count_violations(
        self,
        line: TrendLine,
        candles: List[Dict],
        line_type: str
    ) -> int:
        """Count candles that violate the line."""
        violations = 0
        for i in range(line.p1.index, min(line.p2.index + 1, len(candles))):
            if i < 0 or i >= len(candles):
                continue
            c = candles[i]
            expected = line.value_at_index(i)
            
            if line_type == "high":
                if c['high'] > expected * (1 + self.TOUCH_TOLERANCE * 1.5):
                    violations += 1
            else:
                if c['low'] < expected * (1 - self.TOUCH_TOLERANCE * 1.5):
                    violations += 1
        return violations
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def count_line_touches(self, line: TrendLine, candles: List[Dict], line_type: str) -> int:
        """Count candle touches on line."""
        touches = 0
        for i in range(line.p1.index, min(line.p2.index + 1, len(candles))):
            if i < 0 or i >= len(candles):
                continue
            c = candles[i]
            line_value = line.value_at_index(i)
            price = c['high'] if line_type == "high" else c['low']
            if abs(price - line_value) / line_value < self.TOUCH_TOLERANCE:
                touches += 1
        return touches
    
    def check_price_containment(self, upper: TrendLine, lower: TrendLine, candles: List[Dict]) -> float:
        """Check percentage of candles contained between lines."""
        inside_count = 0
        total_count = 0
        start_idx = max(upper.p1.index, lower.p1.index)
        end_idx = min(upper.p2.index, lower.p2.index)
        
        for i in range(start_idx, end_idx + 1):
            if i < 0 or i >= len(candles):
                continue
            total_count += 1
            c = candles[i]
            upper_val = upper.value_at_index(i)
            lower_val = lower.value_at_index(i)
            if c['high'] <= upper_val * 1.02 and c['low'] >= lower_val * 0.98:
                inside_count += 1
        
        return inside_count / total_count if total_count > 0 else 0
    
    def check_narrowing(self, upper: TrendLine, lower: TrendLine) -> bool:
        """Check if pattern is narrowing (converging)."""
        width_start = upper.p1.value - lower.p1.value
        width_end = upper.p2.value - lower.p2.value
        return width_end < width_start * 0.95
    
    def count_pivot_touches(self, line: TrendLine, pivots: List[Pivot]) -> int:
        """Count pivot points touching line."""
        touches = 0
        for p in pivots:
            if p.index < line.p1.index or p.index > line.p2.index:
                continue
            line_val = line.value_at_index(p.index)
            if abs(p.value - line_val) / line_val < self.TOUCH_TOLERANCE:
                touches += 1
        return touches
    
    # =========================================================================
    # PATTERN VALIDATORS (with extended lines)
    # =========================================================================
    
    def validate_descending_triangle(
        self,
        pivot_highs: List[Pivot],
        pivot_lows: List[Pivot],
        candles: List[Dict]
    ) -> Optional[Dict]:
        """Validate DESCENDING TRIANGLE with extended lines."""
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        # P0.2 FIX: Filter pivots by pattern window
        pattern_start = len(candles) // 3  # Start from 1/3 of recent candles
        recent_highs = self.filter_pivots_by_window(pivot_highs, pattern_start)
        recent_lows = self.filter_pivots_by_window(pivot_lows, pattern_start)
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        # Find best lines with pattern_start for anchor penalty
        upper_line = self.find_best_line(
            recent_highs, candles, "high", 
            slope_constraint="descending", 
            pattern_start=pattern_start
        )
        lower_line = self.find_best_line(
            recent_lows, candles, "low", 
            slope_constraint="horizontal",
            pattern_start=pattern_start
        )
        
        if not upper_line or not lower_line:
            return None
        
        # Validations
        upper_touches = self.count_pivot_touches(upper_line, recent_highs)
        lower_touches = self.count_pivot_touches(lower_line, recent_lows)
        
        if upper_touches < self.MIN_PIVOTS_PER_LINE or lower_touches < self.MIN_PIVOTS_PER_LINE:
            return None
        
        if not self.check_narrowing(upper_line, lower_line):
            return None
        
        containment = self.check_price_containment(upper_line, lower_line, candles)
        if containment < self.PRICE_CONTAINMENT_RATIO:
            return None
        
        # Calculate confidence
        total_touches = upper_touches + lower_touches
        candle_touches = self.count_line_touches(upper_line, candles, "high") + \
                         self.count_line_touches(lower_line, candles, "low")
        
        touch_score = min(1.0, total_touches / 6)
        line_score = min(1.0, (upper_line.score + lower_line.score) / 20)
        confidence = 0.4 + (touch_score * 0.15) + (containment * 0.25) + \
                     (min(1.0, candle_touches / 10) * 0.1) + (line_score * 0.1)
        confidence = round(min(0.85, confidence), 2)
        
        # P0.5 FIX: Don't return low-confidence patterns
        if confidence < self.MIN_CONFIDENCE:
            return None
        
        # P0.1 FIX: Use extended lines for rendering
        return {
            "type": "descending_triangle",
            "direction": "bearish",
            "engine": "V4_ANCHOR",  # MARKER: Proves new anchor-based engine
            "confidence": confidence,
            "touches": total_touches,
            "candle_touches": candle_touches,
            "containment": round(containment, 2),
            "line_scores": {
                "upper": round(upper_line.score, 1),
                "lower": round(lower_line.score, 1)
            },
            "points": {
                "upper": upper_line.extend_line(candles, pattern_start),
                "lower": lower_line.extend_line(candles, pattern_start),
            },
            "anchor_points": {
                "upper": upper_line.to_points(),
                "lower": lower_line.to_points(),
            },
            "breakout_level": round(lower_line.p2.value, 2),
            "invalidation": round(upper_line.p2.value, 2),
        }
    
    def validate_ascending_triangle(
        self,
        pivot_highs: List[Pivot],
        pivot_lows: List[Pivot],
        candles: List[Dict]
    ) -> Optional[Dict]:
        """Validate ASCENDING TRIANGLE with extended lines."""
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        pattern_start = len(candles) // 3
        recent_highs = self.filter_pivots_by_window(pivot_highs, pattern_start)
        recent_lows = self.filter_pivots_by_window(pivot_lows, pattern_start)
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        upper_line = self.find_best_line(
            recent_highs, candles, "high",
            slope_constraint="horizontal",
            pattern_start=pattern_start
        )
        lower_line = self.find_best_line(
            recent_lows, candles, "low",
            slope_constraint="ascending",
            pattern_start=pattern_start
        )
        
        if not upper_line or not lower_line:
            return None
        
        upper_touches = self.count_pivot_touches(upper_line, recent_highs)
        lower_touches = self.count_pivot_touches(lower_line, recent_lows)
        
        if upper_touches < self.MIN_PIVOTS_PER_LINE or lower_touches < self.MIN_PIVOTS_PER_LINE:
            return None
        
        if not self.check_narrowing(upper_line, lower_line):
            return None
        
        containment = self.check_price_containment(upper_line, lower_line, candles)
        if containment < self.PRICE_CONTAINMENT_RATIO:
            return None
        
        total_touches = upper_touches + lower_touches
        candle_touches = self.count_line_touches(upper_line, candles, "high") + \
                         self.count_line_touches(lower_line, candles, "low")
        
        touch_score = min(1.0, total_touches / 6)
        line_score = min(1.0, (upper_line.score + lower_line.score) / 20)
        confidence = 0.4 + (touch_score * 0.15) + (containment * 0.25) + \
                     (min(1.0, candle_touches / 10) * 0.1) + (line_score * 0.1)
        confidence = round(min(0.85, confidence), 2)
        
        if confidence < self.MIN_CONFIDENCE:
            return None
        
        return {
            "type": "ascending_triangle",
            "direction": "bullish",
            "engine": "V4_ANCHOR",
            "confidence": confidence,
            "touches": total_touches,
            "candle_touches": candle_touches,
            "containment": round(containment, 2),
            "line_scores": {
                "upper": round(upper_line.score, 1),
                "lower": round(lower_line.score, 1)
            },
            "points": {
                "upper": upper_line.extend_line(candles, pattern_start),
                "lower": lower_line.extend_line(candles, pattern_start),
            },
            "anchor_points": {
                "upper": upper_line.to_points(),
                "lower": lower_line.to_points(),
            },
            "breakout_level": round(upper_line.p2.value, 2),
            "invalidation": round(lower_line.p2.value, 2),
        }
    
    def validate_symmetrical_triangle(
        self,
        pivot_highs: List[Pivot],
        pivot_lows: List[Pivot],
        candles: List[Dict]
    ) -> Optional[Dict]:
        """Validate SYMMETRICAL TRIANGLE with extended lines."""
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        pattern_start = len(candles) // 3
        recent_highs = self.filter_pivots_by_window(pivot_highs, pattern_start)
        recent_lows = self.filter_pivots_by_window(pivot_lows, pattern_start)
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        upper_line = self.find_best_line(
            recent_highs, candles, "high",
            slope_constraint="descending",
            pattern_start=pattern_start
        )
        lower_line = self.find_best_line(
            recent_lows, candles, "low",
            slope_constraint="ascending",
            pattern_start=pattern_start
        )
        
        if not upper_line or not lower_line:
            return None
        
        # Check symmetry
        if lower_line.slope_normalized == 0:
            return None
        slope_ratio = abs(upper_line.slope_normalized) / abs(lower_line.slope_normalized)
        if slope_ratio < 0.3 or slope_ratio > 3.0:
            return None
        
        upper_touches = self.count_pivot_touches(upper_line, recent_highs)
        lower_touches = self.count_pivot_touches(lower_line, recent_lows)
        
        if upper_touches < self.MIN_PIVOTS_PER_LINE or lower_touches < self.MIN_PIVOTS_PER_LINE:
            return None
        
        if not self.check_narrowing(upper_line, lower_line):
            return None
        
        containment = self.check_price_containment(upper_line, lower_line, candles)
        if containment < self.PRICE_CONTAINMENT_RATIO:
            return None
        
        total_touches = upper_touches + lower_touches
        candle_touches = self.count_line_touches(upper_line, candles, "high") + \
                         self.count_line_touches(lower_line, candles, "low")
        
        touch_score = min(1.0, total_touches / 6)
        line_score = min(1.0, (upper_line.score + lower_line.score) / 20)
        confidence = 0.4 + (touch_score * 0.15) + (containment * 0.25) + \
                     (min(1.0, candle_touches / 10) * 0.1) + (line_score * 0.1)
        confidence = round(min(0.85, confidence), 2)
        
        if confidence < self.MIN_CONFIDENCE:
            return None
        
        return {
            "type": "symmetrical_triangle",
            "direction": "neutral",
            "engine": "V4_ANCHOR",
            "confidence": confidence,
            "touches": total_touches,
            "candle_touches": candle_touches,
            "containment": round(containment, 2),
            "slope_ratio": round(slope_ratio, 2),
            "line_scores": {
                "upper": round(upper_line.score, 1),
                "lower": round(lower_line.score, 1)
            },
            "points": {
                "upper": upper_line.extend_line(candles, pattern_start),
                "lower": lower_line.extend_line(candles, pattern_start),
            },
            "anchor_points": {
                "upper": upper_line.to_points(),
                "lower": lower_line.to_points(),
            },
            "breakout_level": round((upper_line.p2.value + lower_line.p2.value) / 2, 2),
            "invalidation": None,
        }
    
    def validate_channel(
        self,
        pivot_highs: List[Pivot],
        pivot_lows: List[Pivot],
        candles: List[Dict]
    ) -> Optional[Dict]:
        """Validate CHANNEL pattern with extended lines."""
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        pattern_start = len(candles) // 3
        recent_highs = self.filter_pivots_by_window(pivot_highs, pattern_start)
        recent_lows = self.filter_pivots_by_window(pivot_lows, pattern_start)
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        upper_line = self.find_best_line(
            recent_highs, candles, "high",
            pattern_start=pattern_start
        )
        lower_line = self.find_best_line(
            recent_lows, candles, "low",
            pattern_start=pattern_start
        )
        
        if not upper_line or not lower_line:
            return None
        
        # Same direction check (parallel)
        if upper_line.slope_normalized * lower_line.slope_normalized < -0.00001:
            return None
        
        # Parallel check
        if abs(upper_line.slope_normalized) > 0.0001 or abs(lower_line.slope_normalized) > 0.0001:
            max_slope = max(abs(upper_line.slope_normalized), abs(lower_line.slope_normalized))
            if max_slope > 0:
                slope_diff_ratio = abs(upper_line.slope_normalized - lower_line.slope_normalized) / max_slope
                if slope_diff_ratio > 0.5:
                    return None
        
        upper_touches = self.count_pivot_touches(upper_line, recent_highs)
        lower_touches = self.count_pivot_touches(lower_line, recent_lows)
        
        if upper_touches < self.MIN_PIVOTS_PER_LINE or lower_touches < self.MIN_PIVOTS_PER_LINE:
            return None
        
        # Channel should NOT be narrowing
        if self.check_narrowing(upper_line, lower_line):
            return None
        
        containment = self.check_price_containment(upper_line, lower_line, candles)
        if containment < self.PRICE_CONTAINMENT_RATIO:
            return None
        
        # Determine channel type
        avg_slope = (upper_line.slope_normalized + lower_line.slope_normalized) / 2
        if avg_slope > 0.0003:
            channel_type = "ascending_channel"
            direction = "bullish"
        elif avg_slope < -0.0003:
            channel_type = "descending_channel"
            direction = "bearish"
        else:
            channel_type = "horizontal_channel"
            direction = "neutral"
        
        total_touches = upper_touches + lower_touches
        candle_touches = self.count_line_touches(upper_line, candles, "high") + \
                         self.count_line_touches(lower_line, candles, "low")
        
        touch_score = min(1.0, total_touches / 6)
        line_score = min(1.0, (upper_line.score + lower_line.score) / 20)
        confidence = 0.4 + (touch_score * 0.15) + (containment * 0.25) + \
                     (min(1.0, candle_touches / 10) * 0.1) + (line_score * 0.1)
        confidence = round(min(0.85, confidence), 2)
        
        if confidence < self.MIN_CONFIDENCE:
            return None
        
        return {
            "type": channel_type,
            "direction": direction,
            "engine": "V4_ANCHOR",
            "confidence": confidence,
            "touches": total_touches,
            "candle_touches": candle_touches,
            "containment": round(containment, 2),
            "line_scores": {
                "upper": round(upper_line.score, 1),
                "lower": round(lower_line.score, 1)
            },
            "points": {
                "upper": upper_line.extend_line(candles, pattern_start),
                "lower": lower_line.extend_line(candles, pattern_start),
            },
            "anchor_points": {
                "upper": upper_line.to_points(),
                "lower": lower_line.to_points(),
            },
            "breakout_level": round(upper_line.p2.value if direction != "bearish" else lower_line.p2.value, 2),
            "invalidation": round(lower_line.p2.value if direction == "bullish" else upper_line.p2.value, 2),
        }
    
    # =========================================================================
    # MAIN DETECTION
    # =========================================================================
    
    def detect_best_pattern(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Detect best pattern with all P0 fixes.
        Returns None if no high-quality pattern found.
        """
        if len(candles) < 30:
            return None
        
        pivot_highs, pivot_lows = self.find_pivots(candles)
        
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            return None
        
        recent_candles = self._recent_candles if self._recent_candles else candles[-self.pattern_window:]
        
        patterns = []
        
        # Try each validator
        result = self.validate_descending_triangle(pivot_highs, pivot_lows, recent_candles)
        if result:
            patterns.append(result)
        
        result = self.validate_ascending_triangle(pivot_highs, pivot_lows, recent_candles)
        if result:
            patterns.append(result)
        
        result = self.validate_symmetrical_triangle(pivot_highs, pivot_lows, recent_candles)
        if result:
            patterns.append(result)
        
        result = self.validate_channel(pivot_highs, pivot_lows, recent_candles)
        if result:
            patterns.append(result)
        
        if not patterns:
            return None
        
        # Return highest confidence pattern
        patterns.sort(key=lambda p: (
            p["confidence"],
            p.get("line_scores", {}).get("upper", 0) + p.get("line_scores", {}).get("lower", 0)
        ), reverse=True)
        
        return patterns[0]


def get_pattern_validator_v2(timeframe: str = "1D", config: Dict = None) -> PatternValidatorV2:
    """Factory function with optional Multi-Scale config."""
    return PatternValidatorV2(timeframe, config)
