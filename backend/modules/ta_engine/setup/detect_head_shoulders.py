"""
Head & Shoulders Pattern Detector
==================================

Production-level detector for:
- Head & Shoulders (bearish)
- Inverse Head & Shoulders (bullish)

Key validations:
- Pivot-based shoulder/head detection
- Neckline quality check
- Shoulder balance validation
- Head dominance verification
- Breakout confirmation
- Expiration-aware
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Pivot:
    index: int
    time: int
    value: float
    type: str  # "high" | "low"


class HeadShouldersDetector:
    """
    Detects Head & Shoulders (bearish) and Inverse H&S (bullish).
    """

    def __init__(self, timeframe: str = "1D"):
        self.timeframe = timeframe.upper()

        self.cfg = {
            "4H":   {"lookback": 220, "pivot_window": 3,  "min_sep": 4,  "max_sep": 60},
            "1D":   {"lookback": 260, "pivot_window": 5,  "min_sep": 6,  "max_sep": 80},
            "7D":   {"lookback": 420, "pivot_window": 9,  "min_sep": 8,  "max_sep": 120},
            "30D":  {"lookback": 900, "pivot_window": 15, "min_sep": 12, "max_sep": 220},
            "180D": {"lookback": 1600,"pivot_window": 25, "min_sep": 20, "max_sep": 420},
            "1Y":   {"lookback": 2600,"pivot_window": 40, "min_sep": 30, "max_sep": 700},
        }.get(self.timeframe, {"lookback": 260, "pivot_window": 5, "min_sep": 6, "max_sep": 80})

        self.lookback = self.cfg["lookback"]
        self.min_sep = self.cfg["min_sep"]
        self.max_sep = self.cfg["max_sep"]

        self.touch_tolerance = 0.012
        self.neckline_break_tolerance = 0.005
        self.max_shoulder_height_diff = 0.10
        self.min_head_dominance = 0.03
        self.max_neckline_slope_abs = 0.25
        self.expiration_ratio = 0.35

    def detect(
        self,
        candles: List[dict],
        pivots_high: List = None,
        pivots_low: List = None,
        levels: Optional[List[dict]] = None,
        structure_ctx = None,
        **kwargs
    ) -> List[Dict]:
        """Main detection entry point."""
        if not candles or len(candles) < 40:
            return []

        candles = candles[-self.lookback:]
        start_idx = 0

        # Convert pivots if needed
        highs = self._convert_pivots(pivots_high, "high", start_idx) if pivots_high else []
        lows = self._convert_pivots(pivots_low, "low", start_idx) if pivots_low else []

        results = []

        bearish = self._detect_bearish_hs(candles, highs, lows)
        if bearish:
            results.extend(bearish)

        bullish = self._detect_inverse_hs(candles, highs, lows)
        if bullish:
            results.extend(bullish)

        return results

    def _convert_pivots(self, pivots, pivot_type: str, min_idx: int) -> List[Pivot]:
        """Convert pivot objects to internal format."""
        result = []
        for p in pivots:
            if hasattr(p, 'index'):
                idx = p.index
                time_val = p.time if hasattr(p, 'time') else 0
                value = p.value if hasattr(p, 'value') else p.price
            elif isinstance(p, dict):
                idx = p.get('index', 0)
                time_val = p.get('time', 0)
                value = p.get('value', p.get('price', 0))
            else:
                continue
            
            if idx >= min_idx:
                result.append(Pivot(index=idx, time=time_val, value=value, type=pivot_type))
        
        return result

    def _detect_bearish_hs(self, candles: List[dict], highs: List[Pivot], lows: List[Pivot]) -> List[Dict]:
        """Detect bearish Head & Shoulders pattern."""
        candidates = []

        if len(highs) < 3 or len(lows) < 2:
            return candidates

        for i in range(len(highs) - 2):
            ls = highs[i]
            for j in range(i + 1, len(highs) - 1):
                h = highs[j]
                if not self._valid_spacing(ls, h):
                    continue

                for k in range(j + 1, len(highs)):
                    rs = highs[k]
                    if not self._valid_spacing(h, rs):
                        continue
                    if rs.index - ls.index > self.max_sep * 2:
                        continue

                    # H&S rules: head higher than both shoulders
                    if not (h.value > ls.value and h.value > rs.value):
                        continue

                    avg_shoulders = (ls.value + rs.value) / 2
                    if avg_shoulders <= 0:
                        continue

                    head_dom = (h.value - avg_shoulders) / avg_shoulders
                    if head_dom < self.min_head_dominance:
                        continue

                    shoulder_diff = abs(ls.value - rs.value) / avg_shoulders
                    if shoulder_diff > self.max_shoulder_height_diff:
                        continue

                    # Find neckline lows
                    low1 = self._best_low_between(lows, ls.index, h.index)
                    low2 = self._best_low_between(lows, h.index, rs.index)
                    if not low1 or not low2:
                        continue

                    neckline = self._build_line(low1, low2)
                    if neckline is None or abs(neckline["slope"]) > self.max_neckline_slope_abs:
                        continue

                    # Breakout check
                    breakout_idx = self._find_break_below_neckline(candles, neckline, rs.index)
                    if breakout_idx is None:
                        continue

                    # Expiration check
                    width = max(rs.index - ls.index, 1)
                    age = (len(candles) - 1) - breakout_idx
                    if age > width * self.expiration_ratio:
                        continue

                    # Score the pattern
                    geom = self._score_geometry(ls, h, rs, low1, low2, is_bearish=True)
                    contain = self._score_containment(candles, ls, h, rs, neckline, is_bearish=True)
                    
                    total_geom = (
                        geom["head_score"] * 0.35 +
                        geom["shoulder_balance"] * 0.25 +
                        geom["time_symmetry"] * 0.20 +
                        geom["neckline_quality"] * 0.20
                    )

                    confidence = max(0.0, min(0.95, total_geom * 0.55 + contain * 0.45))

                    if confidence < 0.58:
                        continue

                    # Build result
                    start_time = candles[ls.index]["time"] if ls.index < len(candles) else 0
                    end_time = candles[min(breakout_idx, len(candles)-1)]["time"]
                    
                    candidates.append({
                        "type": "head_shoulders",
                        "direction": "bearish",
                        "confidence": round(confidence, 4),
                        "geometry_score": round(total_geom, 4),
                        "touch_count": 5,
                        "containment": round(contain, 4),
                        "line_scores": {"neckline": round(geom["neckline_quality"] * 10, 2)},
                        "points": {
                            "upper": [
                                {"time": start_time, "value": h.value},
                                {"time": end_time, "value": h.value}
                            ],
                            "lower": [
                                {"time": low1.time, "value": low1.value},
                                {"time": low2.time, "value": low2.value}
                            ],
                            "markers": {
                                "left_shoulder": {"time": ls.time, "value": ls.value},
                                "head": {"time": h.time, "value": h.value},
                                "right_shoulder": {"time": rs.time, "value": rs.value}
                            }
                        },
                        "anchor_points": {
                            "upper": [{"time": h.time, "value": h.value}],
                            "lower": [{"time": low1.time, "value": low1.value}, {"time": low2.time, "value": low2.value}]
                        },
                        "start_index": ls.index,
                        "end_index": breakout_idx,
                        "last_touch_index": breakout_idx,
                        "breakout_level": round(self._line_value_at(neckline, rs.index), 2),
                        "invalidation": round(h.value * 1.01, 2),
                        "meta": {
                            "head_dominance": round(head_dom, 4),
                            "shoulder_balance": round(geom["shoulder_balance"], 4)
                        }
                    })

        return candidates

    def _detect_inverse_hs(self, candles: List[dict], highs: List[Pivot], lows: List[Pivot]) -> List[Dict]:
        """Detect bullish Inverse Head & Shoulders pattern."""
        candidates = []

        if len(lows) < 3 or len(highs) < 2:
            return candidates

        for i in range(len(lows) - 2):
            ls = lows[i]
            for j in range(i + 1, len(lows) - 1):
                h = lows[j]
                if not self._valid_spacing(ls, h):
                    continue

                for k in range(j + 1, len(lows)):
                    rs = lows[k]
                    if not self._valid_spacing(h, rs):
                        continue
                    if rs.index - ls.index > self.max_sep * 2:
                        continue

                    # Inverse H&S: head lower than both shoulders
                    if not (h.value < ls.value and h.value < rs.value):
                        continue

                    avg_shoulders = (ls.value + rs.value) / 2
                    if avg_shoulders <= 0:
                        continue

                    head_dom = (avg_shoulders - h.value) / avg_shoulders
                    if head_dom < self.min_head_dominance:
                        continue

                    shoulder_diff = abs(ls.value - rs.value) / avg_shoulders
                    if shoulder_diff > self.max_shoulder_height_diff:
                        continue

                    # Find neckline highs
                    high1 = self._best_high_between(highs, ls.index, h.index)
                    high2 = self._best_high_between(highs, h.index, rs.index)
                    if not high1 or not high2:
                        continue

                    neckline = self._build_line(high1, high2)
                    if neckline is None or abs(neckline["slope"]) > self.max_neckline_slope_abs:
                        continue

                    # Breakout check
                    breakout_idx = self._find_break_above_neckline(candles, neckline, rs.index)
                    if breakout_idx is None:
                        continue

                    # Expiration check
                    width = max(rs.index - ls.index, 1)
                    age = (len(candles) - 1) - breakout_idx
                    if age > width * self.expiration_ratio:
                        continue

                    # Score
                    geom = self._score_geometry(ls, h, rs, high1, high2, is_bearish=False)
                    contain = self._score_containment(candles, ls, h, rs, neckline, is_bearish=False)
                    
                    total_geom = (
                        geom["head_score"] * 0.35 +
                        geom["shoulder_balance"] * 0.25 +
                        geom["time_symmetry"] * 0.20 +
                        geom["neckline_quality"] * 0.20
                    )

                    confidence = max(0.0, min(0.95, total_geom * 0.55 + contain * 0.45))

                    if confidence < 0.58:
                        continue

                    start_time = candles[ls.index]["time"] if ls.index < len(candles) else 0
                    end_time = candles[min(breakout_idx, len(candles)-1)]["time"]
                    
                    candidates.append({
                        "type": "inverse_head_shoulders",
                        "direction": "bullish",
                        "confidence": round(confidence, 4),
                        "geometry_score": round(total_geom, 4),
                        "touch_count": 5,
                        "containment": round(contain, 4),
                        "line_scores": {"neckline": round(geom["neckline_quality"] * 10, 2)},
                        "points": {
                            "upper": [
                                {"time": high1.time, "value": high1.value},
                                {"time": high2.time, "value": high2.value}
                            ],
                            "lower": [
                                {"time": start_time, "value": h.value},
                                {"time": end_time, "value": h.value}
                            ],
                            "markers": {
                                "left_shoulder": {"time": ls.time, "value": ls.value},
                                "head": {"time": h.time, "value": h.value},
                                "right_shoulder": {"time": rs.time, "value": rs.value}
                            }
                        },
                        "anchor_points": {
                            "upper": [{"time": high1.time, "value": high1.value}, {"time": high2.time, "value": high2.value}],
                            "lower": [{"time": h.time, "value": h.value}]
                        },
                        "start_index": ls.index,
                        "end_index": breakout_idx,
                        "last_touch_index": breakout_idx,
                        "breakout_level": round(self._line_value_at(neckline, rs.index), 2),
                        "invalidation": round(h.value * 0.99, 2),
                        "meta": {
                            "head_dominance": round(head_dom, 4),
                            "shoulder_balance": round(geom["shoulder_balance"], 4)
                        }
                    })

        return candidates

    # --- Helpers ---
    
    def _valid_spacing(self, p1: Pivot, p2: Pivot) -> bool:
        distance = p2.index - p1.index
        return self.min_sep <= distance <= self.max_sep

    def _best_low_between(self, lows: List[Pivot], left_idx: int, right_idx: int) -> Optional[Pivot]:
        candidates = [p for p in lows if left_idx < p.index < right_idx]
        return min(candidates, key=lambda x: x.value) if candidates else None

    def _best_high_between(self, highs: List[Pivot], left_idx: int, right_idx: int) -> Optional[Pivot]:
        candidates = [p for p in highs if left_idx < p.index < right_idx]
        return max(candidates, key=lambda x: x.value) if candidates else None

    def _build_line(self, p1: Pivot, p2: Pivot) -> Optional[Dict]:
        dx = p2.index - p1.index
        if dx == 0:
            return None
        slope = (p2.value - p1.value) / dx
        return {"p1": p1, "p2": p2, "slope": slope}

    def _line_value_at(self, line: Dict, idx: int) -> float:
        return line["p1"].value + line["slope"] * (idx - line["p1"].index)

    def _find_break_below_neckline(self, candles: List[dict], neckline: Dict, start_idx: int) -> Optional[int]:
        for i in range(start_idx + 1, len(candles)):
            neck = self._line_value_at(neckline, i)
            close = candles[i]["close"]
            if close < neck * (1 - self.neckline_break_tolerance):
                return i
        return None

    def _find_break_above_neckline(self, candles: List[dict], neckline: Dict, start_idx: int) -> Optional[int]:
        for i in range(start_idx + 1, len(candles)):
            neck = self._line_value_at(neckline, i)
            close = candles[i]["close"]
            if close > neck * (1 + self.neckline_break_tolerance):
                return i
        return None

    def _score_geometry(self, ls, h, rs, neck_p1, neck_p2, is_bearish: bool) -> Dict:
        avg_shoulders = (ls.value + rs.value) / 2
        
        if is_bearish:
            head_score = min(1.0, max(0.0, (h.value - avg_shoulders) / avg_shoulders / 0.08))
        else:
            head_score = min(1.0, max(0.0, (avg_shoulders - h.value) / avg_shoulders / 0.08))

        shoulder_balance = 1.0 - min(1.0, abs(ls.value - rs.value) / avg_shoulders / self.max_shoulder_height_diff)

        left_span = max(h.index - ls.index, 1)
        right_span = max(rs.index - h.index, 1)
        time_symmetry = 1.0 - min(1.0, abs(left_span - right_span) / max(left_span, right_span))

        neckline_slope = (neck_p2.value - neck_p1.value) / max(neck_p2.index - neck_p1.index, 1)
        avg_price = (neck_p1.value + neck_p2.value) / 2
        neckline_quality = 1.0 - min(1.0, abs(neckline_slope / avg_price) / 0.001) if avg_price else 0.5

        return {
            "head_score": max(0.0, head_score),
            "shoulder_balance": max(0.0, shoulder_balance),
            "time_symmetry": max(0.0, time_symmetry),
            "neckline_quality": max(0.0, neckline_quality)
        }

    def _score_containment(self, candles, ls, h, rs, neckline, is_bearish: bool) -> float:
        inside = 0
        total = 0
        for i in range(ls.index, min(rs.index + 1, len(candles))):
            total += 1
            neck = self._line_value_at(neckline, i)
            if is_bearish:
                if candles[i]["low"] >= neck * (1 - self.touch_tolerance):
                    inside += 1
            else:
                if candles[i]["high"] <= neck * (1 + self.touch_tolerance):
                    inside += 1
        return inside / total if total else 0.0


def get_head_shoulders_detector(timeframe: str = "1D") -> HeadShouldersDetector:
    """Factory function."""
    return HeadShouldersDetector(timeframe)
