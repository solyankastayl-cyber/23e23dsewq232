"""
Pattern State Engine
====================

КЛЮЧЕВОЙ СДВИГ:
Level 1: "рисуем линии" → Level 2: "описываем поведение рынка"

Pattern States:
- forming: паттерн формируется
- maturing: близко к точке решения  
- breakout: пробой верхней границы
- breakdown: пробой нижней границы
- invalidated: паттерн инвалидирован
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class PatternState:
    """Complete pattern state with trading context."""
    pattern_type: str
    direction: str
    state: str  # forming, maturing, breakout, breakdown, invalidated
    state_reason: str = ""
    progress_pct: float = 0.0
    age_candles: int = 0
    upper_boundary: float = 0.0
    lower_boundary: float = 0.0
    trigger_level: float = 0.0
    invalidation_level: float = 0.0
    target_level: float = 0.0
    confidence: float = 0.0
    respect_score: float = 0.0
    compression_score: float = 0.0
    reaction_score: float = 0.0
    touches_upper: int = 0
    touches_lower: int = 0
    reactions_upper: int = 0
    reactions_lower: int = 0
    slope_upper: float = 0.0
    slope_lower: float = 0.0
    slope_convergence: float = 0.0
    bias: str = "neutral"
    signal_strength: float = 0.0
    pattern_start_time: int = 0
    pattern_end_time: int = 0
    geometry: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.pattern_type,
            "direction": self.direction,
            "state": self.state,
            "state_reason": self.state_reason,
            "progress_pct": round(self.progress_pct, 1),
            "levels": {
                "upper_boundary": round(self.upper_boundary, 2),
                "lower_boundary": round(self.lower_boundary, 2),
                "trigger": round(self.trigger_level, 2),
                "invalidation": round(self.invalidation_level, 2),
                "target": round(self.target_level, 2),
            },
            "scores": {
                "confidence": round(self.confidence, 2),
                "respect": round(self.respect_score, 2),
                "compression": round(self.compression_score, 2),
                "reaction": round(self.reaction_score, 2),
            },
            "touches": {
                "upper": self.touches_upper,
                "lower": self.touches_lower,
                "reactions_upper": self.reactions_upper,
                "reactions_lower": self.reactions_lower,
            },
            "trading": {
                "bias": self.bias,
                "signal_strength": round(self.signal_strength, 2),
            },
            "geometry": self.geometry,
        }
    
    def get_summary(self) -> str:
        type_label = self.pattern_type.replace("_", " ").title()
        if self.state == "forming":
            return f"{type_label} forming. Progress: {self.progress_pct:.0f}%."
        elif self.state == "maturing":
            return f"{type_label} maturing. Bias: {self.bias}."
        elif self.state == "breakout":
            return f"{type_label} BREAKOUT. Target: {self.target_level:.2f}."
        elif self.state == "breakdown":
            return f"{type_label} breakdown."
        return f"{type_label} - {self.state}"


class PatternStateEngine:
    """Transforms pattern geometry into trading-relevant state."""
    
    REACTION_THRESHOLD = 0.003
    BREAKOUT_THRESHOLD = 0.005
    MATURING_PROGRESS = 70
    MIN_TOUCHES_FOR_VALID = 2
    MIN_RESPECT_SCORE = 0.5
    
    def __init__(self, atr: float = 0.0, timeframe: str = "4H"):
        self.atr = atr
        self.timeframe = timeframe
        self._adjust_thresholds()
    
    def _adjust_thresholds(self):
        mult = {"1H": 0.5, "4H": 1.0, "1D": 1.5, "7D": 2.0}.get(self.timeframe, 1.0)
        self.REACTION_THRESHOLD *= mult
        self.BREAKOUT_THRESHOLD *= mult
    
    def evaluate(
        self,
        pattern_type: str,
        direction: str,
        candles: List[Dict],
        upper_points: List[Dict],
        lower_points: List[Dict],
        pattern_start_index: int,
        window_end_index: int = None,
    ) -> PatternState:
        if not candles or not upper_points or not lower_points:
            return PatternState(pattern_type=pattern_type, direction=direction, 
                              state="invalidated", state_reason="No data")
        
        window_end = window_end_index or len(candles) - 1
        current_price = candles[-1].get("close", 0)
        
        upper_slope, upper_intercept = self._fit_line(upper_points)
        lower_slope, lower_intercept = self._fit_line(lower_points)
        
        upper_boundary = self._line_val(upper_slope, upper_intercept, window_end)
        lower_boundary = self._line_val(lower_slope, lower_intercept, window_end)
        
        if self.atr <= 0:
            self.atr = self._calc_atr(candles)
        
        touches_u, reactions_u = self._count_touches(candles, upper_slope, upper_intercept, True)
        touches_l, reactions_l = self._count_touches(candles, lower_slope, lower_intercept, False)
        
        total_touches = touches_u + touches_l
        total_reactions = reactions_u + reactions_l
        respect_score = total_reactions / total_touches if total_touches > 0 else 0.0
        
        compression_score = self._calc_compression(candles, pattern_start_index, window_end)
        reaction_score = self._calc_reaction_score(candles, upper_slope, upper_intercept, 
                                                    lower_slope, lower_intercept)
        
        age = window_end - pattern_start_index
        progress_pct = min(100, compression_score * 100 + age / 2)
        
        state, reason = self._determine_state(current_price, upper_boundary, lower_boundary,
                                               direction, progress_pct, respect_score, 
                                               touches_u, touches_l)
        
        trigger, invalid, target = self._calc_levels(direction, upper_boundary, 
                                                      lower_boundary, abs(upper_boundary - lower_boundary))
        
        bias, signal = self._calc_bias(state, direction, respect_score, compression_score)
        confidence = self._calc_confidence(respect_score, compression_score, reaction_score,
                                           touches_u, touches_l)
        
        geometry = self._build_geometry(upper_points, lower_points, upper_slope, upper_intercept,
                                        lower_slope, lower_intercept, candles, pattern_start_index)
        
        return PatternState(
            pattern_type=pattern_type, direction=direction, state=state, state_reason=reason,
            progress_pct=progress_pct, age_candles=age,
            upper_boundary=upper_boundary, lower_boundary=lower_boundary,
            trigger_level=trigger, invalidation_level=invalid, target_level=target,
            confidence=confidence, respect_score=respect_score,
            compression_score=compression_score, reaction_score=reaction_score,
            touches_upper=touches_u, touches_lower=touches_l,
            reactions_upper=reactions_u, reactions_lower=reactions_l,
            slope_upper=upper_slope, slope_lower=lower_slope,
            slope_convergence=abs(upper_slope - lower_slope),
            bias=bias, signal_strength=signal, geometry=geometry,
        )
    
    def _determine_state(self, price, upper, lower, direction, progress, respect, t_u, t_l):
        if respect < self.MIN_RESPECT_SCORE and t_u + t_l > 4:
            return "invalidated", f"Low respect ({respect:.2f})"
        if upper > 0 and (price - upper) / upper > self.BREAKOUT_THRESHOLD:
            return "breakout", "Price above upper boundary"
        if lower > 0 and (lower - price) / lower > self.BREAKOUT_THRESHOLD:
            return "breakdown", "Price below lower boundary"
        if progress >= self.MATURING_PROGRESS:
            return "maturing", f"Progress {progress:.0f}%"
        return "forming", f"Progress {progress:.0f}%"
    
    def _count_touches(self, candles, slope, intercept, is_upper, tol=0.01):
        touches, reactions = 0, 0
        for i, c in enumerate(candles):
            line_v = self._line_val(slope, intercept, i)
            if line_v <= 0: continue
            touch_p = c.get("high" if is_upper else "low", 0)
            if abs(touch_p - line_v) / line_v < tol:
                touches += 1
                if i + 1 < len(candles):
                    nc = candles[i + 1]
                    if is_upper and nc["close"] < c["close"]:
                        if abs(c["close"] - nc["close"]) / c["close"] > self.REACTION_THRESHOLD:
                            reactions += 1
                    elif not is_upper and nc["close"] > c["close"]:
                        if abs(nc["close"] - c["close"]) / c["close"] > self.REACTION_THRESHOLD:
                            reactions += 1
        return touches, reactions
    
    def _calc_reaction_score(self, candles, u_slope, u_int, l_slope, l_int):
        strengths = []
        for i in range(len(candles) - 1):
            c, nc = candles[i], candles[i + 1]
            uv = self._line_val(u_slope, u_int, i)
            lv = self._line_val(l_slope, l_int, i)
            if uv > 0 and abs(c["high"] - uv) / uv < 0.01 and nc["close"] < c["close"]:
                strengths.append((c["close"] - nc["close"]) / c["close"])
            if lv > 0 and abs(c["low"] - lv) / lv < 0.01 and nc["close"] > c["close"]:
                strengths.append((nc["close"] - c["close"]) / c["close"])
        return min(1.0, sum(strengths) / len(strengths) / 0.01) if strengths else 0.0
    
    def _calc_compression(self, candles, start, end):
        if start >= end or start >= len(candles): return 0.0
        sc = candles[start:start + 5]
        ec = candles[max(0, end - 5):end + 1]
        if not sc or not ec: return 0.0
        sr = max(c["high"] for c in sc) - min(c["low"] for c in sc)
        er = max(c["high"] for c in ec) - min(c["low"] for c in ec)
        return max(0.0, min(1.0, 1.0 - er / sr)) if sr > 0 else 0.0
    
    def _calc_levels(self, direction, upper, lower, height):
        if direction == "bullish":
            return upper, lower, upper + height * 0.618
        elif direction == "bearish":
            return lower, upper, lower - height * 0.618
        return upper, lower, (upper + lower) / 2 + height * 0.5
    
    def _calc_bias(self, state, direction, respect, compression):
        if state == "breakout": return "bullish", min(1.0, 0.7 + respect * 0.3)
        if state == "breakdown": return "bearish", min(1.0, 0.7 + respect * 0.3)
        if state == "maturing": return direction, min(1.0, 0.4 + compression * 0.4 + respect * 0.2)
        return "neutral", 0.2 + compression * 0.3
    
    def _calc_confidence(self, respect, compression, reaction, t_u, t_l):
        base = respect * 0.35 + compression * 0.25 + reaction * 0.25
        touch_bonus = min(0.15, (t_u + t_l) * 0.02)
        balance = min(t_u, t_l) / max(t_u, t_l) * 0.1 if t_u > 0 and t_l > 0 else 0
        return min(1.0, max(0.0, base + touch_bonus + balance))
    
    def _fit_line(self, points):
        if len(points) < 2: return 0.0, 0.0
        p1, p2 = points[0], points[-1]
        x1, y1 = p1.get("index", 0), p1.get("price", p1.get("value", 0))
        x2, y2 = p2.get("index", 0), p2.get("price", p2.get("value", 0))
        if x2 == x1: return 0.0, y1
        slope = (y2 - y1) / (x2 - x1)
        return slope, y1 - slope * x1
    
    def _line_val(self, slope, intercept, x): return slope * x + intercept
    
    def _calc_atr(self, candles, period=14):
        if len(candles) < period + 1: return 0.0
        tr = []
        for i in range(1, len(candles)):
            h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(tr[-period:]) / period if len(tr) >= period else sum(tr) / len(tr)
    
    def _build_geometry(self, up, low, us, ui, ls, li, candles, start):
        end = len(candles) - 1
        st = candles[start].get("time", 0)
        et = candles[-1].get("time", 0)
        if st > 1e12: st //= 1000
        if et > 1e12: et //= 1000
        return {
            "upper_line": [{"time": st, "price": round(self._line_val(us, ui, start), 2)},
                          {"time": et, "price": round(self._line_val(us, ui, end), 2)}],
            "lower_line": [{"time": st, "price": round(self._line_val(ls, li, start), 2)},
                          {"time": et, "price": round(self._line_val(ls, li, end), 2)}],
        }


def get_pattern_state_engine(atr: float = 0.0, timeframe: str = "4H") -> PatternStateEngine:
    return PatternStateEngine(atr=atr, timeframe=timeframe)
