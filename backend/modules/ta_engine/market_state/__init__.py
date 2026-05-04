"""
Market State Engine (Layer A)
=============================

NOT pattern figures. This is the CONTEXT layer.

Defines:
- trend direction
- channel type
- volatility regime
- momentum regime
- wyckoff phase
- trend strength
- major/minor trend

This is rendered as BACKGROUND and CONTEXT, not as "main pattern".
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class TrendDirection(str, Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


class ChannelType(str, Enum):
    ASCENDING = "ascending_channel"
    DESCENDING = "descending_channel"
    HORIZONTAL = "horizontal_channel"
    NONE = "no_channel"


class VolatilityRegime(str, Enum):
    HIGH = "high_volatility"
    NORMAL = "normal_volatility"
    LOW = "low_volatility"
    COMPRESSION = "compression"
    EXPANSION = "expansion"


class MomentumRegime(str, Enum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class WyckoffPhase(str, Enum):
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class TrendStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NO_TREND = "no_trend"


@dataclass
class MarketState:
    """Complete market state definition."""
    trend_direction: TrendDirection
    trend_strength: TrendStrength
    channel_type: ChannelType
    volatility_regime: VolatilityRegime
    momentum_regime: MomentumRegime
    wyckoff_phase: WyckoffPhase
    major_trend: TrendDirection
    minor_trend: TrendDirection
    atr_normalized: float
    volatility_percentile: float
    trend_score: float  # -1 to +1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_direction": self.trend_direction.value,
            "trend_strength": self.trend_strength.value,
            "channel_type": self.channel_type.value,
            "volatility_regime": self.volatility_regime.value,
            "momentum_regime": self.momentum_regime.value,
            "wyckoff_phase": self.wyckoff_phase.value,
            "major_trend": self.major_trend.value,
            "minor_trend": self.minor_trend.value,
            "atr_normalized": self.atr_normalized,
            "volatility_percentile": self.volatility_percentile,
            "trend_score": self.trend_score,
        }


class MarketStateEngine:
    """
    Determines market state for a timeframe.
    
    This is Layer A — context, not patterns.
    """
    
    def __init__(self):
        self._ema_periods = [20, 50, 200]
        self._atr_period = 14
        self._rsi_period = 14
        self._adx_period = 14
    
    def analyze(
        self,
        candles: List[Dict[str, Any]],
        indicators: Optional[Dict[str, Any]] = None,
    ) -> MarketState:
        """
        Analyze market state from candles.
        
        Args:
            candles: OHLCV data
            indicators: Pre-computed indicators (optional)
        
        Returns:
            MarketState object
        """
        if len(candles) < 50:
            return self._default_state()
        
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        # Compute EMAs
        ema_20 = self._ema(closes, 20)
        ema_50 = self._ema(closes, 50)
        ema_200 = self._ema(closes, 200) if len(closes) >= 200 else ema_50
        
        # Compute ATR
        atr = self._atr(candles)
        atr_normalized = atr / closes[-1] if closes[-1] > 0 else 0
        
        # Compute RSI
        rsi = self._rsi(closes)
        
        # Determine trend direction from EMA stack
        trend_direction = self._determine_trend_direction(closes[-1], ema_20, ema_50, ema_200)
        
        # Determine trend strength from ADX approximation
        trend_strength = self._determine_trend_strength(candles)
        
        # Determine channel type
        channel_type = self._determine_channel(highs, lows, closes)
        
        # Determine volatility regime
        volatility_regime, volatility_percentile = self._determine_volatility(atr_normalized, candles)
        
        # Determine momentum regime from RSI
        momentum_regime = self._determine_momentum(rsi)
        
        # Determine Wyckoff phase (simplified)
        wyckoff_phase = self._determine_wyckoff(candles, trend_direction, volatility_regime)
        
        # Major vs minor trend
        major_trend = self._determine_major_trend(closes, ema_200)
        minor_trend = self._determine_minor_trend(closes, ema_20, ema_50)
        
        # Overall trend score (-1 to +1)
        trend_score = self._compute_trend_score(closes[-1], ema_20, ema_50, ema_200, rsi)
        
        return MarketState(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            channel_type=channel_type,
            volatility_regime=volatility_regime,
            momentum_regime=momentum_regime,
            wyckoff_phase=wyckoff_phase,
            major_trend=major_trend,
            minor_trend=minor_trend,
            atr_normalized=atr_normalized,
            volatility_percentile=volatility_percentile,
            trend_score=trend_score,
        )
    
    def _default_state(self) -> MarketState:
        """Default state when not enough data."""
        return MarketState(
            trend_direction=TrendDirection.UNKNOWN,
            trend_strength=TrendStrength.NO_TREND,
            channel_type=ChannelType.NONE,
            volatility_regime=VolatilityRegime.NORMAL,
            momentum_regime=MomentumRegime.NEUTRAL,
            wyckoff_phase=WyckoffPhase.UNKNOWN,
            major_trend=TrendDirection.UNKNOWN,
            minor_trend=TrendDirection.UNKNOWN,
            atr_normalized=0.0,
            volatility_percentile=50.0,
            trend_score=0.0,
        )
    
    def _ema(self, data: List[float], period: int) -> float:
        """Compute EMA."""
        if len(data) < period:
            return data[-1] if data else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _atr(self, candles: List[Dict[str, Any]], period: int = 14) -> float:
        """Compute ATR."""
        if len(candles) < period + 1:
            return 0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i-1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        if len(trs) < period:
            return sum(trs) / len(trs) if trs else 0
        
        # EMA of TR
        atr = sum(trs[:period]) / period
        mult = 2 / (period + 1)
        for tr in trs[period:]:
            atr = (tr - atr) * mult + atr
        
        return atr
    
    def _rsi(self, closes: List[float], period: int = 14) -> float:
        """Compute RSI."""
        if len(closes) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            delta = closes[i] - closes[i-1]
            if delta > 0:
                gains.append(delta)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(delta))
        
        if len(gains) < period:
            return 50
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _determine_trend_direction(
        self, price: float, ema_20: float, ema_50: float, ema_200: float
    ) -> TrendDirection:
        """Determine trend from EMA alignment."""
        bullish_count = 0
        bearish_count = 0
        
        if price > ema_20:
            bullish_count += 1
        else:
            bearish_count += 1
        
        if ema_20 > ema_50:
            bullish_count += 1
        else:
            bearish_count += 1
        
        if ema_50 > ema_200:
            bullish_count += 1
        else:
            bearish_count += 1
        
        if bullish_count >= 2:
            return TrendDirection.UPTREND
        elif bearish_count >= 2:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _determine_trend_strength(self, candles: List[Dict[str, Any]]) -> TrendStrength:
        """Determine trend strength (ADX approximation)."""
        if len(candles) < 20:
            return TrendStrength.NO_TREND
        
        closes = [c["close"] for c in candles[-20:]]
        highs = [c["high"] for c in candles[-20:]]
        lows = [c["low"] for c in candles[-20:]]
        
        # Simple directional movement
        plus_dm = sum(max(0, highs[i] - highs[i-1]) for i in range(1, len(highs)))
        minus_dm = sum(max(0, lows[i-1] - lows[i]) for i in range(1, len(lows)))
        
        total_dm = plus_dm + minus_dm
        if total_dm == 0:
            return TrendStrength.NO_TREND
        
        direction_ratio = abs(plus_dm - minus_dm) / total_dm
        
        if direction_ratio > 0.6:
            return TrendStrength.STRONG
        elif direction_ratio > 0.3:
            return TrendStrength.MODERATE
        elif direction_ratio > 0.1:
            return TrendStrength.WEAK
        else:
            return TrendStrength.NO_TREND
    
    def _determine_channel(
        self, highs: List[float], lows: List[float], closes: List[float]
    ) -> ChannelType:
        """Determine channel type from linear regression of highs/lows."""
        if len(highs) < 20:
            return ChannelType.NONE
        
        # Use last 50 candles for channel detection
        n = min(50, len(highs))
        recent_highs = highs[-n:]
        recent_lows = lows[-n:]
        
        # Linear regression slope
        x = list(range(n))
        high_slope = self._linear_regression_slope(x, recent_highs)
        low_slope = self._linear_regression_slope(x, recent_lows)
        
        # Normalize slopes
        price_range = max(recent_highs) - min(recent_lows)
        if price_range == 0:
            return ChannelType.NONE
        
        high_slope_norm = high_slope / price_range * 100
        low_slope_norm = low_slope / price_range * 100
        avg_slope = (high_slope_norm + low_slope_norm) / 2
        
        # Determine channel type
        if avg_slope > 0.5:
            return ChannelType.ASCENDING
        elif avg_slope < -0.5:
            return ChannelType.DESCENDING
        elif abs(avg_slope) <= 0.5:
            # Check if it's a valid horizontal channel
            high_std = self._std(recent_highs)
            low_std = self._std(recent_lows)
            avg_std = (high_std + low_std) / 2
            if avg_std / price_range < 0.1:
                return ChannelType.HORIZONTAL
        
        return ChannelType.NONE
    
    def _linear_regression_slope(self, x: List[float], y: List[float]) -> float:
        """Compute linear regression slope."""
        n = len(x)
        if n < 2:
            return 0
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_xx = sum(xi * xi for xi in x)
        
        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            return 0
        
        return (n * sum_xy - sum_x * sum_y) / denominator
    
    def _std(self, data: List[float]) -> float:
        """Compute standard deviation."""
        if len(data) < 2:
            return 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5
    
    def _determine_volatility(
        self, atr_normalized: float, candles: List[Dict[str, Any]]
    ) -> tuple[VolatilityRegime, float]:
        """Determine volatility regime."""
        if len(candles) < 50:
            return VolatilityRegime.NORMAL, 50.0
        
        # Compute historical ATR percentile
        atrs = []
        for i in range(14, len(candles)):
            window = candles[i-14:i]
            atr = self._atr(window, 14)
            price = candles[i]["close"]
            if price > 0:
                atrs.append(atr / price)
        
        if not atrs:
            return VolatilityRegime.NORMAL, 50.0
        
        current_atr = atr_normalized
        percentile = sum(1 for a in atrs if a <= current_atr) / len(atrs) * 100
        
        # Check for compression/expansion
        recent_atrs = atrs[-10:] if len(atrs) >= 10 else atrs
        older_atrs = atrs[-30:-10] if len(atrs) >= 30 else atrs[:len(atrs)//2]
        
        if recent_atrs and older_atrs:
            recent_avg = sum(recent_atrs) / len(recent_atrs)
            older_avg = sum(older_atrs) / len(older_atrs)
            
            if recent_avg < older_avg * 0.7:
                return VolatilityRegime.COMPRESSION, percentile
            elif recent_avg > older_avg * 1.5:
                return VolatilityRegime.EXPANSION, percentile
        
        if percentile > 80:
            return VolatilityRegime.HIGH, percentile
        elif percentile < 20:
            return VolatilityRegime.LOW, percentile
        else:
            return VolatilityRegime.NORMAL, percentile
    
    def _determine_momentum(self, rsi: float) -> MomentumRegime:
        """Determine momentum regime from RSI."""
        if rsi > 70:
            return MomentumRegime.STRONG_BULLISH
        elif rsi > 55:
            return MomentumRegime.BULLISH
        elif rsi < 30:
            return MomentumRegime.STRONG_BEARISH
        elif rsi < 45:
            return MomentumRegime.BEARISH
        else:
            return MomentumRegime.NEUTRAL
    
    def _determine_wyckoff(
        self,
        candles: List[Dict[str, Any]],
        trend: TrendDirection,
        volatility: VolatilityRegime,
    ) -> WyckoffPhase:
        """Determine Wyckoff phase (simplified)."""
        if len(candles) < 50:
            return WyckoffPhase.UNKNOWN
        
        # Simple heuristic based on trend + volatility
        if trend == TrendDirection.SIDEWAYS and volatility in [VolatilityRegime.LOW, VolatilityRegime.COMPRESSION]:
            # Could be accumulation or distribution
            # Check volume trend
            volumes = [c.get("volume", 0) for c in candles[-20:]]
            vol_trend = self._linear_regression_slope(list(range(len(volumes))), volumes)
            
            if vol_trend > 0:
                return WyckoffPhase.ACCUMULATION
            else:
                return WyckoffPhase.DISTRIBUTION
        
        elif trend == TrendDirection.UPTREND:
            return WyckoffPhase.MARKUP
        elif trend == TrendDirection.DOWNTREND:
            return WyckoffPhase.MARKDOWN
        
        return WyckoffPhase.UNKNOWN
    
    def _determine_major_trend(self, closes: List[float], ema_200: float) -> TrendDirection:
        """Determine major trend from EMA 200."""
        if not closes:
            return TrendDirection.UNKNOWN
        
        price = closes[-1]
        if price > ema_200 * 1.02:
            return TrendDirection.UPTREND
        elif price < ema_200 * 0.98:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _determine_minor_trend(
        self, closes: List[float], ema_20: float, ema_50: float
    ) -> TrendDirection:
        """Determine minor trend from EMA 20/50."""
        if not closes:
            return TrendDirection.UNKNOWN
        
        price = closes[-1]
        
        if price > ema_20 and ema_20 > ema_50:
            return TrendDirection.UPTREND
        elif price < ema_20 and ema_20 < ema_50:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _compute_trend_score(
        self,
        price: float,
        ema_20: float,
        ema_50: float,
        ema_200: float,
        rsi: float,
    ) -> float:
        """Compute overall trend score from -1 to +1."""
        score = 0.0
        
        # Price vs EMAs
        if price > ema_20:
            score += 0.2
        else:
            score -= 0.2
        
        if price > ema_50:
            score += 0.2
        else:
            score -= 0.2
        
        if price > ema_200:
            score += 0.2
        else:
            score -= 0.2
        
        # EMA alignment
        if ema_20 > ema_50:
            score += 0.15
        else:
            score -= 0.15
        
        if ema_50 > ema_200:
            score += 0.15
        else:
            score -= 0.15
        
        # RSI contribution
        rsi_norm = (rsi - 50) / 50  # -1 to +1
        score += rsi_norm * 0.1
        
        return max(-1.0, min(1.0, score))


# Singleton
_market_state_engine: Optional[MarketStateEngine] = None


def get_market_state_engine() -> MarketStateEngine:
    global _market_state_engine
    if _market_state_engine is None:
        _market_state_engine = MarketStateEngine()
    return _market_state_engine
