"""
Indicator Insights Engine V2
============================
RSI + MACD → market stage + actionable signal.

RSI = market stage (NOT direction)
- oversold: potential reversal UP
- near_oversold: selling pressure exhausting
- neutral: no signal
- bullish: market rising
- overbought: potential pullback

MACD = momentum regime
- below_zero + growing: bearish acceleration
- below_zero + fading: bearish weakening
- above_zero + growing: bullish acceleration
- above_zero + fading: bullish weakening

Combined Signal:
- WATCH LONG: RSI near_oversold/oversold + MACD below + fading
- WATCH SHORT: RSI overbought + MACD above + fading
- BEARISH CONTINUATION: MACD below + growing
- BULLISH CONTINUATION: MACD above + growing
- NO TRADE: no edge
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class RSIInsight:
    value: float
    state: str      # oversold, near_oversold, neutral, bullish, overbought
    bias: str       # bullish, bearish_weakening, neutral, bullish_weakening, bearish
    summary: str
    color: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MACDInsight:
    macd_value: float
    signal_value: float
    histogram: float
    zone: str       # above_zero, below_zero
    momentum: str   # growing, fading
    state: str      # bullish_growing, bullish_fading, bearish_growing, bearish_fading
    summary: str
    color: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CombinedSignal:
    signal: str     # WATCH_LONG, WATCH_SHORT, BEARISH_CONTINUATION, BULLISH_CONTINUATION, NO_TRADE
    confidence: str # high, medium, low
    summary: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class IndicatorInsights:
    rsi: Optional[RSIInsight] = None
    macd: Optional[MACDInsight] = None
    combined: Optional[CombinedSignal] = None
    
    def to_dict(self) -> Dict:
        result = {}
        if self.rsi:
            result["rsi"] = self.rsi.to_dict()
        if self.macd:
            result["macd"] = self.macd.to_dict()
        if self.combined:
            result["combined"] = self.combined.to_dict()
        return result


class IndicatorInsightsEngine:
    """
    RSI + MACD → market context + decision
    """
    
    def analyze(self, panes: List[Dict], lookback: int = 5) -> IndicatorInsights:
        insights = IndicatorInsights()
        
        for pane in panes:
            pane_id = pane.get("id", "").lower()
            if pane_id == "rsi":
                insights.rsi = self._analyze_rsi(pane)
            elif pane_id == "macd":
                insights.macd = self._analyze_macd(pane)
        
        # Combined signal from RSI + MACD
        if insights.rsi and insights.macd:
            insights.combined = self._get_combined_signal(insights.rsi, insights.macd)
        
        return insights
    
    def _analyze_rsi(self, pane: Dict) -> Optional[RSIInsight]:
        data = pane.get("data", [])
        if not data:
            return None
        
        value = data[-1].get("value")
        if value is None:
            return None
        value = float(value)
        
        # RSI state = market stage
        if value < 30:
            state = "oversold"
            bias = "bullish"  # potential reversal UP
            summary = "Oversold — potential reversal zone"
            color = "#22c55e"  # green
        elif value < 40:
            state = "near_oversold"
            bias = "bearish_weakening"
            summary = "Near oversold — selling pressure exhausting"
            color = "#86efac"  # light green
        elif value < 60:
            state = "neutral"
            bias = "neutral"
            summary = "Neutral — no clear signal"
            color = "#64748b"  # gray
        elif value < 70:
            state = "bullish"
            bias = "bullish"
            summary = "Bullish pressure — momentum up"
            color = "#fbbf24"  # amber
        else:
            state = "overbought"
            bias = "bearish"  # potential pullback
            summary = "Overbought — potential pullback zone"
            color = "#ef4444"  # red
        
        return RSIInsight(
            value=round(value, 2),
            state=state,
            bias=bias,
            summary=summary,
            color=color
        )
    
    def _analyze_macd(self, pane: Dict) -> Optional[MACDInsight]:
        data = pane.get("data", [])
        extra_lines = pane.get("extra_lines", [])
        
        if not data or len(data) < 2:
            return None
        
        macd_value = data[-1].get("value")
        if macd_value is None:
            return None
        macd_value = float(macd_value)
        
        # Get signal and histogram
        signal_value = 0
        histogram = 0
        histogram_prev = 0
        
        for line in extra_lines or []:
            name = (line.get("id") or line.get("name") or "").lower()
            line_data = line.get("data", [])
            
            if "signal" in name and line_data:
                signal_value = float(line_data[-1].get("value", 0) or 0)
            elif "hist" in name and len(line_data) >= 2:
                histogram = float(line_data[-1].get("value", 0) or 0)
                histogram_prev = float(line_data[-2].get("value", 0) or 0)
        
        # If no histogram data, calculate from MACD - signal
        if histogram == 0:
            histogram = macd_value - signal_value
            if len(data) >= 2:
                macd_prev = float(data[-2].get("value", 0) or 0)
                histogram_prev = macd_prev - signal_value
        
        # MACD zone
        zone = "above_zero" if macd_value > 0 else "below_zero"
        
        # Momentum direction (histogram growing or fading)
        momentum = "growing" if abs(histogram) > abs(histogram_prev) else "fading"
        
        # State and interpretation
        if zone == "above_zero":
            if momentum == "growing":
                state = "bullish_growing"
                summary = "Bullish — momentum building"
                color = "#22c55e"
            else:
                state = "bullish_fading"
                summary = "Bullish fading — watch for reversal"
                color = "#86efac"
        else:
            if momentum == "growing":
                state = "bearish_growing"
                summary = "Bearish — momentum building"
                color = "#ef4444"
            else:
                state = "bearish_fading"
                summary = "Bearish fading — selling pressure easing"
                color = "#fca5a5"
        
        return MACDInsight(
            macd_value=round(macd_value, 2),
            signal_value=round(signal_value, 2),
            histogram=round(histogram, 2),
            zone=zone,
            momentum=momentum,
            state=state,
            summary=summary,
            color=color
        )
    
    def _get_combined_signal(self, rsi: RSIInsight, macd: MACDInsight) -> CombinedSignal:
        """
        RSI + MACD → actionable signal
        """
        rsi_state = rsi.state
        macd_zone = macd.zone
        momentum = macd.momentum
        
        # WATCH LONG: RSI oversold/near_oversold + MACD below + fading
        if rsi_state in ("oversold", "near_oversold") and macd_zone == "below_zero" and momentum == "fading":
            return CombinedSignal(
                signal="WATCH_LONG",
                confidence="high" if rsi_state == "oversold" else "medium",
                summary="Oversold + bearish momentum fading — watch for long entry"
            )
        
        # WATCH SHORT: RSI overbought + MACD above + fading
        if rsi_state == "overbought" and macd_zone == "above_zero" and momentum == "fading":
            return CombinedSignal(
                signal="WATCH_SHORT",
                confidence="high",
                summary="Overbought + bullish momentum fading — watch for short entry"
            )
        
        # BEARISH CONTINUATION: MACD below + growing (regardless of RSI unless oversold)
        if macd_zone == "below_zero" and momentum == "growing" and rsi_state not in ("oversold",):
            return CombinedSignal(
                signal="BEARISH_CONTINUATION",
                confidence="medium",
                summary="Bearish momentum building — downtrend continues"
            )
        
        # BULLISH CONTINUATION: MACD above + growing (regardless of RSI unless overbought)
        if macd_zone == "above_zero" and momentum == "growing" and rsi_state not in ("overbought",):
            return CombinedSignal(
                signal="BULLISH_CONTINUATION",
                confidence="medium",
                summary="Bullish momentum building — uptrend continues"
            )
        
        # NO TRADE: no clear edge
        return CombinedSignal(
            signal="NO_TRADE",
            confidence="low",
            summary="No clear setup — wait for better conditions"
        )


# Singleton
_insights_engine: Optional[IndicatorInsightsEngine] = None

def get_indicator_insights_engine() -> IndicatorInsightsEngine:
    global _insights_engine
    if _insights_engine is None:
        _insights_engine = IndicatorInsightsEngine()
    return _insights_engine
