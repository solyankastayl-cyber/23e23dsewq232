"""
Structure Context Engine
========================

FIRST LAYER: Before any pattern detection, understand the market regime.

Regimes:
- trend_up: HH + HL sequence, positive trend_score
- trend_down: LH + LL sequence, negative trend_score
- range: Low volatility, no clear direction
- compression: Narrowing range (precedes breakout)
- expansion: High volatility spike
- reversal_candidate: Structure shift detected
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class StructureContext:
    """Market structure context - the foundation for all analysis."""
    regime: str                 # trend_up / trend_down / range / compression / expansion / reversal_candidate
    bias: str                   # bullish / bearish / neutral
    hh_count: int
    hl_count: int
    lh_count: int
    ll_count: int
    swing_span_pct: float       # Total price range as % of current price
    volatility_pct: float       # Recent average candle range
    compression_score: float    # 0-1, how much range is narrowing
    trend_score: float          # Positive = up, negative = down
    
    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "bias": self.bias,
            "hh_count": self.hh_count,
            "hl_count": self.hl_count,
            "lh_count": self.lh_count,
            "ll_count": self.ll_count,
            "swing_span_pct": round(self.swing_span_pct, 4),
            "volatility_pct": round(self.volatility_pct, 4),
            "compression_score": round(self.compression_score, 2),
            "trend_score": round(self.trend_score, 4),
        }


class StructureContextEngine:
    """
    Determines market regime BEFORE pattern detection.
    
    This is the key insight:
    - Pattern detection should be GUIDED by structure
    - Triangle in compression → valid
    - Triangle in strong trend → probably wrong
    """
    
    def __init__(self):
        pass

    def build(self, candles: List[dict], pivots_high: List, pivots_low: List) -> StructureContext:
        """Build structure context from candles and pivots."""
        if len(candles) < 30:
            return self._empty_context()
        
        hh, hl, lh, ll = self._count_structure(pivots_high, pivots_low)

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        last_close = closes[-1] if closes else 1
        swing_span_pct = ((max(highs) - min(lows)) / last_close) if last_close else 0.0

        recent_volatility = self._calc_volatility_pct(candles)
        compression_score = self._calc_compression_score(candles)
        trend_score = self._calc_trend_score(closes)

        regime, bias = self._classify(
            hh, hl, lh, ll,
            compression_score,
            trend_score,
            recent_volatility
        )

        return StructureContext(
            regime=regime,
            bias=bias,
            hh_count=hh,
            hl_count=hl,
            lh_count=lh,
            ll_count=ll,
            swing_span_pct=swing_span_pct,
            volatility_pct=recent_volatility,
            compression_score=compression_score,
            trend_score=trend_score,
        )

    def _empty_context(self) -> StructureContext:
        return StructureContext(
            regime="unknown",
            bias="neutral",
            hh_count=0, hl_count=0, lh_count=0, ll_count=0,
            swing_span_pct=0, volatility_pct=0,
            compression_score=0, trend_score=0
        )

    def _count_structure(self, pivots_high: List, pivots_low: List) -> Tuple[int, int, int, int]:
        """Count HH, HL, LH, LL from pivot sequences."""
        hh = hl = lh = ll = 0
        
        def get_value(pivot):
            """Get value from Pivot object or dict."""
            if hasattr(pivot, 'value'):
                return pivot.value
            return pivot.get('price', pivot.get('value', 0))

        for i in range(1, len(pivots_high)):
            if get_value(pivots_high[i]) > get_value(pivots_high[i - 1]):
                hh += 1
            else:
                lh += 1

        for i in range(1, len(pivots_low)):
            if get_value(pivots_low[i]) > get_value(pivots_low[i - 1]):
                hl += 1
            else:
                ll += 1

        return hh, hl, lh, ll

    def _calc_volatility_pct(self, candles: List[dict]) -> float:
        """Average candle range as % of close (last 20 candles)."""
        if len(candles) < 20:
            return 0.0
        ranges = []
        for c in candles[-20:]:
            if c["close"] and c["close"] > 0:
                ranges.append((c["high"] - c["low"]) / c["close"])
        return sum(ranges) / len(ranges) if ranges else 0.0

    def _calc_compression_score(self, candles: List[dict]) -> float:
        """
        How much is the range narrowing?
        0 = expanding, 1 = heavily compressing
        """
        if len(candles) < 40:
            return 0.0
        
        recent = candles[-20:]
        base = candles[-40:-20]

        recent_avg = sum((c["high"] - c["low"]) for c in recent) / max(len(recent), 1)
        base_avg = sum((c["high"] - c["low"]) for c in base) / max(len(base), 1)

        if base_avg == 0:
            return 0.0

        # If recent range is smaller than base → compression
        ratio = recent_avg / base_avg
        return max(0.0, min(1.0, 1.0 - ratio))

    def _calc_trend_score(self, closes: List[float]) -> float:
        """
        Simple trend score: % change over last 30 candles.
        Positive = uptrend, negative = downtrend.
        """
        if len(closes) < 30:
            return 0.0
        start = closes[-30]
        end = closes[-1]
        if start == 0:
            return 0.0
        return (end - start) / start

    def _classify(
        self, 
        hh: int, hl: int, lh: int, ll: int,
        compression_score: float,
        trend_score: float,
        volatility_pct: float
    ) -> Tuple[str, str]:
        """
        Classify market regime based on structure metrics.
        
        Priority:
        1. Compression (if range narrowing significantly)
        2. Strong trend (HH/HL or LH/LL dominant + trend_score)
        3. Range (low volatility, mixed structure)
        4. Reversal candidate (structure shift)
        """
        # High compression → likely triangle/wedge forming
        if compression_score > 0.35:
            return "compression", "neutral"
        
        # Strong uptrend: HH > LH AND HL > LL AND positive trend
        if hh > lh and hl > ll and trend_score > 0.05:
            return "trend_up", "bullish"

        # Strong downtrend: LH > HH AND LL > HL AND negative trend
        if lh > hh and ll > hl and trend_score < -0.05:
            return "trend_down", "bearish"

        # Low volatility → range bound
        if volatility_pct < 0.018:
            return "range", "neutral"

        # No clear direction
        if abs(trend_score) < 0.03:
            return "range", "neutral"
        
        # Structure shifting but not clear yet
        return "reversal_candidate", "neutral"


# Singleton instance
structure_context_engine = StructureContextEngine()
