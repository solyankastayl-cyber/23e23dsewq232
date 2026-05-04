"""
Indicator Signal Engine — PHASE TA-FINAL

Transforms raw indicator values into actionable signals:
- bullish / bearish / neutral direction
- strength (0.0 - 1.0)
- score (-1.0 ... +1.0)
- signal type: trend, momentum, volatility, breakout, mean_reversion, structure

This module is the core of multi-factor model integration.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

SignalDirection = Literal["bullish", "bearish", "neutral"]
SignalType = Literal["trend", "momentum", "volatility", "breakout", "mean_reversion", "structure"]


class IndicatorSignal(BaseModel):
    """Signal extracted from a single indicator."""
    indicator: str
    signal_type: SignalType
    direction: SignalDirection
    strength: float = Field(ge=0.0, le=1.0)  # 0.0 - 1.0
    score: float = Field(ge=-1.0, le=1.0)    # -1.0 (bearish) to +1.0 (bullish)
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IndicatorSignalBatch(BaseModel):
    """Batch of signals from multiple indicators."""
    symbol: str
    timeframe: str
    timestamp: str
    signals: List[IndicatorSignal] = Field(default_factory=list)
    
    # Aggregated scores by type
    trend_signals: List[IndicatorSignal] = Field(default_factory=list)
    momentum_signals: List[IndicatorSignal] = Field(default_factory=list)
    volatility_signals: List[IndicatorSignal] = Field(default_factory=list)
    breakout_signals: List[IndicatorSignal] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Indicator Weights Configuration
# ═══════════════════════════════════════════════════════════════

INDICATOR_WEIGHTS = {
    # Trend indicators - highest weight for direction
    "ema": 2.0,
    "sma": 1.5,
    "ichimoku": 2.0,
    "supertrend": 2.0,
    "psar": 1.5,
    
    # Momentum indicators - medium weight
    "rsi": 1.0,
    "cci": 1.0,
    "williams_r": 1.0,
    "macd": 1.5,
    "stochastic": 1.0,
    "momentum": 1.0,
    "obv": 1.0,
    
    # Volatility indicators
    "atr": 1.0,
    "bollinger": 1.5,
    "keltner": 1.2,
    
    # Breakout indicators
    "donchian": 1.5,
}

INDICATOR_TYPES: Dict[str, SignalType] = {
    "ema": "trend",
    "sma": "trend",
    "ichimoku": "trend",
    "supertrend": "trend",
    "psar": "trend",
    "rsi": "momentum",
    "cci": "momentum",
    "williams_r": "momentum",
    "macd": "momentum",
    "stochastic": "momentum",
    "momentum": "momentum",
    "obv": "momentum",
    "atr": "volatility",
    "bollinger": "volatility",
    "keltner": "volatility",
    "donchian": "breakout",
}


# ═══════════════════════════════════════════════════════════════
# Signal Engine Service
# ═══════════════════════════════════════════════════════════════

class IndicatorSignalEngine:
    """
    Engine to extract actionable signals from indicator values.
    
    This is the core transformation layer:
    raw indicator values → standardized signals → feature vector
    """
    
    def __init__(self):
        self.weights = INDICATOR_WEIGHTS
        self.types = INDICATOR_TYPES
    
    def extract_signals(
        self,
        candles: List[Dict[str, Any]],
        symbol: str = "UNKNOWN",
        timeframe: str = "1H"
    ) -> IndicatorSignalBatch:
        """
        Extract signals from all indicators based on candle data.
        
        Args:
            candles: OHLCV candle data
            symbol: Trading symbol
            timeframe: Chart timeframe
        
        Returns:
            IndicatorSignalBatch with all extracted signals
        """
        if len(candles) < 50:
            return IndicatorSignalBatch(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        
        signals = []
        
        # Extract trend signals
        signals.append(self._extract_ema_signal(candles))
        signals.append(self._extract_sma_signal(candles))
        signals.append(self._extract_ichimoku_signal(candles))
        signals.append(self._extract_supertrend_signal(candles))
        signals.append(self._extract_psar_signal(candles))
        
        # Extract momentum signals
        signals.append(self._extract_rsi_signal(candles))
        signals.append(self._extract_cci_signal(candles))
        signals.append(self._extract_williams_r_signal(candles))
        signals.append(self._extract_macd_signal(candles))
        signals.append(self._extract_stochastic_signal(candles))
        signals.append(self._extract_momentum_signal(candles))
        signals.append(self._extract_obv_signal(candles))
        
        # Extract volatility signals
        signals.append(self._extract_bollinger_signal(candles))
        signals.append(self._extract_keltner_signal(candles))
        signals.append(self._extract_atr_signal(candles))
        
        # Extract breakout signals
        signals.append(self._extract_donchian_signal(candles))
        
        # Filter out None signals
        valid_signals = [s for s in signals if s is not None]
        
        # Group by type
        trend_signals = [s for s in valid_signals if s.signal_type == "trend"]
        momentum_signals = [s for s in valid_signals if s.signal_type == "momentum"]
        volatility_signals = [s for s in valid_signals if s.signal_type == "volatility"]
        breakout_signals = [s for s in valid_signals if s.signal_type == "breakout"]
        
        return IndicatorSignalBatch(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc).isoformat(),
            signals=valid_signals,
            trend_signals=trend_signals,
            momentum_signals=momentum_signals,
            volatility_signals=volatility_signals,
            breakout_signals=breakout_signals,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # TREND INDICATORS
    # ═══════════════════════════════════════════════════════════════
    
    def _extract_ema_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        EMA Stack Signal:
        - EMA20 > EMA50 > EMA200 → Strong Bullish (+0.9)
        - EMA20 < EMA50 < EMA200 → Strong Bearish (-0.9)
        - Mixed alignment → Neutral
        """
        closes = [c["close"] for c in candles]
        
        ema20 = self._ema(closes, 20)[-1]
        ema50 = self._ema(closes, 50)[-1]
        ema200 = self._ema(closes, min(200, len(closes)))[-1]
        
        current_price = closes[-1]
        
        # Perfect bullish stack
        if ema20 > ema50 > ema200:
            # Check price position relative to EMAs
            if current_price > ema20:
                score = 0.9
                strength = 0.9
                reason = "Perfect bullish EMA stack: EMA20 > EMA50 > EMA200, price above all"
            else:
                score = 0.6
                strength = 0.7
                reason = "Bullish EMA stack: EMA20 > EMA50 > EMA200, minor pullback"
            direction = "bullish"
            
        # Perfect bearish stack
        elif ema20 < ema50 < ema200:
            if current_price < ema20:
                score = -0.9
                strength = 0.9
                reason = "Perfect bearish EMA stack: EMA20 < EMA50 < EMA200, price below all"
            else:
                score = -0.6
                strength = 0.7
                reason = "Bearish EMA stack: EMA20 < EMA50 < EMA200, minor bounce"
            direction = "bearish"
            
        # Mixed
        else:
            # Check short-term momentum
            if ema20 > ema50:
                score = 0.3
                direction = "bullish"
                reason = "Mixed EMAs with short-term bullish bias"
            elif ema20 < ema50:
                score = -0.3
                direction = "bearish"
                reason = "Mixed EMAs with short-term bearish bias"
            else:
                score = 0.0
                direction = "neutral"
                reason = "EMAs converging, no clear direction"
            strength = 0.4
        
        return IndicatorSignal(
            indicator="ema",
            signal_type="trend",
            direction=direction,
            strength=strength,
            score=score,
            reason=reason,
            metadata={
                "ema20": round(ema20, 2),
                "ema50": round(ema50, 2),
                "ema200": round(ema200, 2),
                "price": round(current_price, 2),
            }
        )
    
    def _extract_sma_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """SMA crossover signal."""
        closes = [c["close"] for c in candles]
        
        sma20 = np.mean(closes[-20:])
        sma50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma20
        current = closes[-1]
        
        if current > sma20 > sma50:
            score = 0.7
            direction = "bullish"
            reason = "Price above rising SMAs"
        elif current < sma20 < sma50:
            score = -0.7
            direction = "bearish"
            reason = "Price below falling SMAs"
        else:
            score = 0.0
            direction = "neutral"
            reason = "Mixed SMA alignment"
        
        return IndicatorSignal(
            indicator="sma",
            signal_type="trend",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"sma20": round(sma20, 2), "sma50": round(sma50, 2)}
        )
    
    def _extract_ichimoku_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        Ichimoku Cloud signal:
        - Price above cloud + Tenkan > Kijun → Bullish
        - Price below cloud + Tenkan < Kijun → Bearish
        """
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        
        # Tenkan-sen (9-period)
        tenkan = (max(highs[-9:]) + min(lows[-9:])) / 2
        
        # Kijun-sen (26-period)
        kijun = (max(highs[-26:]) + min(lows[-26:])) / 2 if len(highs) >= 26 else tenkan
        
        # Senkou Span A (displaced forward)
        span_a = (tenkan + kijun) / 2
        
        # Senkou Span B (52-period)
        span_b = (max(highs[-52:]) + min(lows[-52:])) / 2 if len(highs) >= 52 else span_a
        
        current = closes[-1]
        cloud_top = max(span_a, span_b)
        cloud_bottom = min(span_a, span_b)
        
        # Price position
        above_cloud = current > cloud_top
        below_cloud = current < cloud_bottom
        in_cloud = cloud_bottom <= current <= cloud_top
        
        # TK cross
        tk_bullish = tenkan > kijun
        tk_bearish = tenkan < kijun
        
        # Cloud color (future sentiment)
        cloud_bullish = span_a > span_b
        
        if above_cloud and tk_bullish and cloud_bullish:
            score = 0.9
            direction = "bullish"
            reason = "Strong Ichimoku bullish: above green cloud, TK bullish cross"
        elif above_cloud and tk_bullish:
            score = 0.7
            direction = "bullish"
            reason = "Ichimoku bullish: above cloud with TK bullish"
        elif below_cloud and tk_bearish and not cloud_bullish:
            score = -0.9
            direction = "bearish"
            reason = "Strong Ichimoku bearish: below red cloud, TK bearish cross"
        elif below_cloud and tk_bearish:
            score = -0.7
            direction = "bearish"
            reason = "Ichimoku bearish: below cloud with TK bearish"
        elif in_cloud:
            score = 0.0
            direction = "neutral"
            reason = "Price inside Ichimoku cloud - consolidation"
        elif above_cloud:
            score = 0.4
            direction = "bullish"
            reason = "Above cloud but mixed signals"
        elif below_cloud:
            score = -0.4
            direction = "bearish"
            reason = "Below cloud but mixed signals"
        else:
            score = 0.0
            direction = "neutral"
            reason = "Unclear Ichimoku setup"
        
        return IndicatorSignal(
            indicator="ichimoku",
            signal_type="trend",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={
                "tenkan": round(tenkan, 2),
                "kijun": round(kijun, 2),
                "span_a": round(span_a, 2),
                "span_b": round(span_b, 2),
            }
        )
    
    def _extract_supertrend_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Supertrend direction signal."""
        period = 10
        multiplier = 3.0
        
        atr_values = self._calculate_atr_series(candles, period)
        
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        # Calculate Supertrend
        supertrend = []
        direction_list = []
        
        for i in range(len(candles)):
            hl2 = (highs[i] + lows[i]) / 2
            atr = atr_values[i] if i < len(atr_values) else atr_values[-1]
            
            upper = hl2 + multiplier * atr
            lower = hl2 - multiplier * atr
            
            if i == 0:
                direction_list.append(1)
                supertrend.append(lower)
            else:
                if closes[i] > supertrend[-1]:
                    direction_list.append(1)
                    supertrend.append(lower)
                else:
                    direction_list.append(-1)
                    supertrend.append(upper)
        
        current_direction = direction_list[-1]
        trend_duration = 0
        for d in reversed(direction_list):
            if d == current_direction:
                trend_duration += 1
            else:
                break
        
        if current_direction == 1:
            # Strength based on duration
            score = min(0.5 + trend_duration * 0.05, 0.9)
            direction = "bullish"
            reason = f"Supertrend bullish for {trend_duration} periods"
        else:
            score = max(-0.5 - trend_duration * 0.05, -0.9)
            direction = "bearish"
            reason = f"Supertrend bearish for {trend_duration} periods"
        
        return IndicatorSignal(
            indicator="supertrend",
            signal_type="trend",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"direction": current_direction, "duration": trend_duration}
        )
    
    def _extract_psar_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Parabolic SAR direction signal."""
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        
        af_start, af_step, af_max = 0.02, 0.02, 0.20
        
        trend_up = True
        af = af_start
        ep = highs[0]
        sar = lows[0]
        
        for i in range(1, len(candles)):
            prev_sar = sar
            
            if trend_up:
                sar = prev_sar + af * (ep - prev_sar)
                sar = min(sar, lows[i-1], lows[max(0, i-2)])
                
                if lows[i] < sar:
                    trend_up = False
                    sar = ep
                    ep = lows[i]
                    af = af_start
                elif highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_step, af_max)
            else:
                sar = prev_sar + af * (ep - prev_sar)
                sar = max(sar, highs[i-1], highs[max(0, i-2)])
                
                if highs[i] > sar:
                    trend_up = True
                    sar = ep
                    ep = highs[i]
                    af = af_start
                elif lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_step, af_max)
        
        if trend_up:
            score = 0.6
            direction = "bullish"
            reason = "PSAR below price - bullish trend"
        else:
            score = -0.6
            direction = "bearish"
            reason = "PSAR above price - bearish trend"
        
        return IndicatorSignal(
            indicator="psar",
            signal_type="trend",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"sar": round(sar, 2), "trend_up": trend_up}
        )
    
    # ═══════════════════════════════════════════════════════════════
    # MOMENTUM INDICATORS
    # ═══════════════════════════════════════════════════════════════
    
    def _extract_rsi_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        RSI Signal:
        - RSI >= 70 → Overbought (Bearish bias) -0.4
        - RSI <= 30 → Oversold (Bullish bias) +0.4
        - RSI 30-70 → Neutral with momentum tilt
        """
        closes = [c["close"] for c in candles]
        rsi = self._calculate_rsi(closes, 14)
        
        if rsi >= 80:
            score = -0.6
            direction = "bearish"
            reason = f"RSI extremely overbought ({rsi:.1f}) - reversal likely"
            strength = 0.8
        elif rsi >= 70:
            score = -0.4
            direction = "bearish"
            reason = f"RSI overbought ({rsi:.1f}) - caution for longs"
            strength = 0.6
        elif rsi <= 20:
            score = 0.6
            direction = "bullish"
            reason = f"RSI extremely oversold ({rsi:.1f}) - bounce likely"
            strength = 0.8
        elif rsi <= 30:
            score = 0.4
            direction = "bullish"
            reason = f"RSI oversold ({rsi:.1f}) - potential reversal"
            strength = 0.6
        elif rsi > 50:
            score = 0.2
            direction = "bullish"
            reason = f"RSI bullish momentum ({rsi:.1f})"
            strength = 0.3
        elif rsi < 50:
            score = -0.2
            direction = "bearish"
            reason = f"RSI bearish momentum ({rsi:.1f})"
            strength = 0.3
        else:
            score = 0.0
            direction = "neutral"
            reason = "RSI neutral at 50"
            strength = 0.1
        
        return IndicatorSignal(
            indicator="rsi",
            signal_type="momentum",
            direction=direction,
            strength=strength,
            score=score,
            reason=reason,
            metadata={"rsi": round(rsi, 2)}
        )
    
    def _extract_cci_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        CCI Signal:
        - CCI >= 100 → Overbought
        - CCI <= -100 → Oversold
        """
        tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in candles]
        period = 20
        
        sma = np.mean(tp[-period:])
        mean_dev = np.mean([abs(v - sma) for v in tp[-period:]])
        cci = (tp[-1] - sma) / (0.015 * mean_dev) if mean_dev != 0 else 0
        
        if cci >= 200:
            score = -0.5
            direction = "bearish"
            reason = f"CCI extreme overbought ({cci:.1f})"
        elif cci >= 100:
            score = -0.35
            direction = "bearish"
            reason = f"CCI overbought ({cci:.1f})"
        elif cci <= -200:
            score = 0.5
            direction = "bullish"
            reason = f"CCI extreme oversold ({cci:.1f})"
        elif cci <= -100:
            score = 0.35
            direction = "bullish"
            reason = f"CCI oversold ({cci:.1f})"
        else:
            score = cci / 500  # Scaled momentum
            direction = "bullish" if cci > 0 else "bearish" if cci < 0 else "neutral"
            reason = f"CCI neutral range ({cci:.1f})"
        
        return IndicatorSignal(
            indicator="cci",
            signal_type="momentum",
            direction=direction,
            strength=min(abs(score), 1.0),
            score=max(-1.0, min(1.0, score)),
            reason=reason,
            metadata={"cci": round(cci, 2)}
        )
    
    def _extract_williams_r_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Williams %R signal (-100 to 0 range)."""
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        period = 14
        
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        wr = ((highest - closes[-1]) / (highest - lowest)) * -100 if highest != lowest else -50
        
        if wr >= -20:
            score = -0.4
            direction = "bearish"
            reason = f"Williams %R overbought ({wr:.1f})"
        elif wr <= -80:
            score = 0.4
            direction = "bullish"
            reason = f"Williams %R oversold ({wr:.1f})"
        else:
            score = -(wr + 50) / 150  # Scaled
            direction = "bullish" if wr < -50 else "bearish" if wr > -50 else "neutral"
            reason = f"Williams %R neutral ({wr:.1f})"
        
        return IndicatorSignal(
            indicator="williams_r",
            signal_type="momentum",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"williams_r": round(wr, 2)}
        )
    
    def _extract_macd_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        MACD Signal:
        - MACD > Signal + positive histogram → Bullish
        - MACD < Signal + negative histogram → Bearish
        - Crossovers add strength
        """
        closes = [c["close"] for c in candles]
        
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd_line = [f - s for f, s in zip(ema12, ema26)]
        signal_line = self._ema(macd_line, 9)
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_hist = histogram[-1]
        prev_hist = histogram[-2] if len(histogram) > 1 else 0
        
        # Detect crossover
        crossover_bullish = prev_hist < 0 and current_hist > 0
        crossover_bearish = prev_hist > 0 and current_hist < 0
        
        if crossover_bullish:
            score = 0.8
            direction = "bullish"
            reason = "MACD bullish crossover"
        elif crossover_bearish:
            score = -0.8
            direction = "bearish"
            reason = "MACD bearish crossover"
        elif current_macd > current_signal and current_hist > 0:
            # Histogram growing
            if current_hist > prev_hist:
                score = 0.6
                reason = "MACD bullish with growing momentum"
            else:
                score = 0.4
                reason = "MACD bullish but momentum fading"
            direction = "bullish"
        elif current_macd < current_signal and current_hist < 0:
            if current_hist < prev_hist:
                score = -0.6
                reason = "MACD bearish with growing momentum"
            else:
                score = -0.4
                reason = "MACD bearish but momentum fading"
            direction = "bearish"
        else:
            score = 0.0
            direction = "neutral"
            reason = "MACD neutral - no clear signal"
        
        return IndicatorSignal(
            indicator="macd",
            signal_type="momentum",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={
                "macd": round(current_macd, 4),
                "signal": round(current_signal, 4),
                "histogram": round(current_hist, 4),
            }
        )
    
    def _extract_stochastic_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Stochastic %K signal."""
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        period = 14
        
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        k = ((closes[-1] - lowest) / (highest - lowest)) * 100 if highest != lowest else 50
        
        if k >= 80:
            score = -0.35
            direction = "bearish"
            reason = f"Stochastic overbought ({k:.1f})"
        elif k <= 20:
            score = 0.35
            direction = "bullish"
            reason = f"Stochastic oversold ({k:.1f})"
        else:
            score = (k - 50) / 150
            direction = "bullish" if k > 50 else "bearish" if k < 50 else "neutral"
            reason = f"Stochastic neutral ({k:.1f})"
        
        return IndicatorSignal(
            indicator="stochastic",
            signal_type="momentum",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"stochastic_k": round(k, 2)}
        )
    
    def _extract_momentum_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Price momentum (ROC) signal."""
        closes = [c["close"] for c in candles]
        period = 10
        
        if len(closes) <= period:
            return None
        
        momentum = closes[-1] - closes[-period-1]
        momentum_pct = (momentum / closes[-period-1]) * 100
        
        if momentum_pct >= 5:
            score = 0.7
            direction = "bullish"
            reason = f"Strong bullish momentum ({momentum_pct:.1f}%)"
        elif momentum_pct >= 2:
            score = 0.4
            direction = "bullish"
            reason = f"Moderate bullish momentum ({momentum_pct:.1f}%)"
        elif momentum_pct <= -5:
            score = -0.7
            direction = "bearish"
            reason = f"Strong bearish momentum ({momentum_pct:.1f}%)"
        elif momentum_pct <= -2:
            score = -0.4
            direction = "bearish"
            reason = f"Moderate bearish momentum ({momentum_pct:.1f}%)"
        else:
            score = momentum_pct / 10
            direction = "neutral"
            reason = f"Weak momentum ({momentum_pct:.1f}%)"
        
        return IndicatorSignal(
            indicator="momentum",
            signal_type="momentum",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"momentum_pct": round(momentum_pct, 2)}
        )
    
    def _extract_obv_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """On Balance Volume signal."""
        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]
        
        obv = 0
        obv_values = []
        for i in range(len(candles)):
            if i > 0:
                if closes[i] > closes[i-1]:
                    obv += volumes[i]
                elif closes[i] < closes[i-1]:
                    obv -= volumes[i]
            obv_values.append(obv)
        
        # OBV trend (20-period)
        obv_sma = np.mean(obv_values[-20:]) if len(obv_values) >= 20 else obv_values[-1]
        obv_trend = (obv_values[-1] - obv_sma) / abs(obv_sma) if obv_sma != 0 else 0
        
        # Price trend
        price_trend = (closes[-1] - np.mean(closes[-20:])) / np.mean(closes[-20:]) if len(closes) >= 20 else 0
        
        # Divergence check
        if obv_trend > 0.1 and price_trend < -0.02:
            score = 0.5
            direction = "bullish"
            reason = "Bullish OBV divergence - volume accumulating"
        elif obv_trend < -0.1 and price_trend > 0.02:
            score = -0.5
            direction = "bearish"
            reason = "Bearish OBV divergence - volume distributing"
        elif obv_trend > 0.05:
            score = 0.3
            direction = "bullish"
            reason = "OBV uptrend - buying pressure"
        elif obv_trend < -0.05:
            score = -0.3
            direction = "bearish"
            reason = "OBV downtrend - selling pressure"
        else:
            score = 0.0
            direction = "neutral"
            reason = "OBV neutral"
        
        return IndicatorSignal(
            indicator="obv",
            signal_type="momentum",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"obv_trend": round(obv_trend, 4)}
        )
    
    # ═══════════════════════════════════════════════════════════════
    # VOLATILITY INDICATORS
    # ═══════════════════════════════════════════════════════════════
    
    def _extract_bollinger_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        Bollinger Bands signal:
        - Price near upper band → Mean reversion bearish
        - Price near lower band → Mean reversion bullish
        - Squeeze → Breakout expected
        """
        closes = [c["close"] for c in candles]
        period = 20
        std_mult = 2.0
        
        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        upper = sma + std_mult * std
        lower = sma - std_mult * std
        
        current = closes[-1]
        bandwidth = (upper - lower) / sma if sma > 0 else 0
        
        # Position within bands (0 = lower, 1 = upper)
        position = (current - lower) / (upper - lower) if upper != lower else 0.5
        
        # Squeeze detection (low bandwidth)
        avg_bandwidth = np.mean([
            (np.mean(closes[i-period:i]) + 2*np.std(closes[i-period:i]) - 
             np.mean(closes[i-period:i]) + 2*np.std(closes[i-period:i])) / np.mean(closes[i-period:i])
            for i in range(-10, 0)
        ]) if len(closes) >= period + 10 else bandwidth
        
        is_squeeze = bandwidth < avg_bandwidth * 0.7
        
        if is_squeeze:
            score = 0.1  # Neutral but alert
            direction = "neutral"
            reason = "Bollinger squeeze - breakout imminent"
            strength = 0.5
        elif position >= 0.95:
            score = -0.4
            direction = "bearish"
            reason = "Price at upper Bollinger Band - overbought"
            strength = 0.6
        elif position <= 0.05:
            score = 0.4
            direction = "bullish"
            reason = "Price at lower Bollinger Band - oversold"
            strength = 0.6
        elif position > 0.7:
            score = -0.2
            direction = "bearish"
            reason = "Price near upper Bollinger Band"
            strength = 0.4
        elif position < 0.3:
            score = 0.2
            direction = "bullish"
            reason = "Price near lower Bollinger Band"
            strength = 0.4
        else:
            score = 0.0
            direction = "neutral"
            reason = "Price in middle of Bollinger Bands"
            strength = 0.2
        
        return IndicatorSignal(
            indicator="bollinger",
            signal_type="volatility",
            direction=direction,
            strength=strength,
            score=score,
            reason=reason,
            metadata={
                "upper": round(upper, 2),
                "lower": round(lower, 2),
                "middle": round(sma, 2),
                "bandwidth": round(bandwidth, 4),
                "position": round(position, 2),
                "is_squeeze": is_squeeze,
            }
        )
    
    def _extract_keltner_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Keltner Channel signal."""
        closes = [c["close"] for c in candles]
        ema_period = 20
        atr_period = 10
        multiplier = 2.0
        
        ema = self._ema(closes, ema_period)[-1]
        atr = self._calculate_atr(candles, atr_period)
        
        upper = ema + multiplier * atr
        lower = ema - multiplier * atr
        current = closes[-1]
        
        if current > upper:
            score = 0.6
            direction = "bullish"
            reason = "Price breaking above Keltner Channel - strong trend"
        elif current < lower:
            score = -0.6
            direction = "bearish"
            reason = "Price breaking below Keltner Channel - strong trend"
        else:
            position = (current - lower) / (upper - lower) if upper != lower else 0.5
            score = (position - 0.5) * 0.4
            direction = "bullish" if position > 0.5 else "bearish" if position < 0.5 else "neutral"
            reason = f"Price within Keltner Channel (position: {position:.2f})"
        
        return IndicatorSignal(
            indicator="keltner",
            signal_type="volatility",
            direction=direction,
            strength=abs(score),
            score=score,
            reason=reason,
            metadata={"upper": round(upper, 2), "lower": round(lower, 2), "ema": round(ema, 2)}
        )
    
    def _extract_atr_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """ATR volatility signal."""
        atr = self._calculate_atr(candles, 14)
        current_price = candles[-1]["close"]
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Historical ATR comparison
        atr_values = self._calculate_atr_series(candles, 14)
        avg_atr = np.mean(atr_values[-50:]) if len(atr_values) >= 50 else atr
        
        volatility_ratio = atr / avg_atr if avg_atr > 0 else 1.0
        
        if volatility_ratio >= 1.5:
            score = 0.3  # High volatility can be bullish for breakouts
            direction = "bullish"
            reason = f"High volatility ({volatility_ratio:.2f}x) - breakout potential"
            strength = 0.7
        elif volatility_ratio <= 0.6:
            score = 0.1
            direction = "neutral"
            reason = f"Low volatility ({volatility_ratio:.2f}x) - compression"
            strength = 0.4
        else:
            score = 0.0
            direction = "neutral"
            reason = f"Normal volatility ({volatility_ratio:.2f}x)"
            strength = 0.3
        
        return IndicatorSignal(
            indicator="atr",
            signal_type="volatility",
            direction=direction,
            strength=strength,
            score=score,
            reason=reason,
            metadata={
                "atr": round(atr, 2),
                "atr_pct": round(atr_pct, 2),
                "volatility_ratio": round(volatility_ratio, 2),
            }
        )
    
    # ═══════════════════════════════════════════════════════════════
    # BREAKOUT INDICATORS
    # ═══════════════════════════════════════════════════════════════
    
    def _extract_donchian_signal(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """
        Donchian Channel breakout signal:
        - Price > upper band → Bullish breakout
        - Price < lower band → Bearish breakout
        """
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        period = 20
        
        upper = max(highs[-period:])
        lower = min(lows[-period:])
        current = closes[-1]
        
        # Check for new highs/lows
        is_new_high = current >= upper * 0.998
        is_new_low = current <= lower * 1.002
        
        if is_new_high:
            score = 0.8
            direction = "bullish"
            reason = "Donchian breakout - new period high"
            strength = 0.9
        elif is_new_low:
            score = -0.8
            direction = "bearish"
            reason = "Donchian breakdown - new period low"
            strength = 0.9
        else:
            # Position within channel
            position = (current - lower) / (upper - lower) if upper != lower else 0.5
            
            if position > 0.8:
                score = 0.4
                direction = "bullish"
                reason = "Near Donchian upper band - bullish pressure"
            elif position < 0.2:
                score = -0.4
                direction = "bearish"
                reason = "Near Donchian lower band - bearish pressure"
            else:
                score = 0.0
                direction = "neutral"
                reason = "Within Donchian range"
            strength = abs(score)
        
        return IndicatorSignal(
            indicator="donchian",
            signal_type="breakout",
            direction=direction,
            strength=strength,
            score=score,
            reason=reason,
            metadata={
                "upper": round(upper, 2),
                "lower": round(lower, 2),
                "is_breakout": is_new_high or is_new_low,
            }
        )
    
    # ═══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        """Calculate EMA."""
        if not data:
            return []
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(data[i] * multiplier + ema[-1] * (1 - multiplier))
        return ema
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI value."""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR."""
        if len(candles) < 2:
            return 0.0
        
        tr_values = []
        for i in range(1, min(len(candles), period + 1)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"])
            )
            tr_values.append(tr)
        
        return np.mean(tr_values) if tr_values else 0.0
    
    def _calculate_atr_series(self, candles: List[Dict], period: int = 14) -> List[float]:
        """Calculate ATR series."""
        atr_values = []
        for i in range(len(candles)):
            if i < 1:
                atr_values.append(candles[i]["high"] - candles[i]["low"])
            else:
                tr = max(
                    candles[i]["high"] - candles[i]["low"],
                    abs(candles[i]["high"] - candles[i-1]["close"]),
                    abs(candles[i]["low"] - candles[i-1]["close"])
                )
                start = max(0, i - period + 1)
                atr_values.append(np.mean([
                    max(candles[j]["high"] - candles[j]["low"],
                        abs(candles[j]["high"] - candles[j-1]["close"]) if j > 0 else 0,
                        abs(candles[j]["low"] - candles[j-1]["close"]) if j > 0 else 0)
                    for j in range(start, i + 1)
                ]))
        return atr_values


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_signal_engine: Optional[IndicatorSignalEngine] = None

def get_indicator_signal_engine() -> IndicatorSignalEngine:
    """Get singleton instance."""
    global _signal_engine
    if _signal_engine is None:
        _signal_engine = IndicatorSignalEngine()
    return _signal_engine
