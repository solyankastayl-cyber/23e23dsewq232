"""
Indicator Engine
=================
Extracts signals from technical indicators.

Supports:
- EMA (20, 50, 200)
- RSI
- MACD
- Bollinger Bands
- Stochastic
- ATR
- Ichimoku
- Supertrend
- OBV
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from modules.ta_engine.setup.setup_types import (
    IndicatorSignal,
    Direction,
)


class IndicatorEngine:
    """Extracts trading signals from technical indicators."""
    
    def __init__(self):
        self.ema_periods = [20, 50, 200]
        self.rsi_period = 14
        self.bb_period = 20
        self.bb_std = 2.0
    
    def analyze_all(self, candles: List[Dict]) -> List[IndicatorSignal]:
        """
        Analyze all indicators and return signals.
        Returns list sorted by strength (highest first).
        """
        if len(candles) < 50:
            return []
        
        signals = []
        
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        
        # EMA signals
        signals.extend(self._analyze_ema(closes))
        
        # RSI signal (always returns something)
        rsi_signal = self._analyze_rsi_full(closes)
        signals.append(rsi_signal)
        
        # MACD signal (always returns something)
        macd_signal = self._analyze_macd_full(closes)
        signals.append(macd_signal)
        
        # Bollinger Bands signal (always returns something)
        bb_signal = self._analyze_bollinger_full(closes)
        signals.append(bb_signal)
        
        # Stochastic signal (always returns something)
        stoch_signal = self._analyze_stochastic_full(closes, highs, lows)
        signals.append(stoch_signal)
        
        # ATR signal
        atr_signal = self._analyze_atr(candles)
        if atr_signal:
            signals.append(atr_signal)
        
        # OBV signal (always returns something)
        obv_signal = self._analyze_obv_full(closes, volumes)
        signals.append(obv_signal)
        
        # ADX (trend strength)
        adx_signal = self._analyze_adx(candles)
        signals.append(adx_signal)
        
        # CCI
        cci_signal = self._analyze_cci(candles)
        signals.append(cci_signal)
        
        # MFI (Money Flow Index)
        mfi_signal = self._analyze_mfi(candles)
        signals.append(mfi_signal)
        
        # Williams %R
        willr_signal = self._analyze_williams_r(candles)
        signals.append(willr_signal)
        
        # Momentum
        mom_signal = self._analyze_momentum(closes)
        signals.append(mom_signal)
        
        # ROC (Rate of Change)
        roc_signal = self._analyze_roc(closes)
        signals.append(roc_signal)
        
        # SMA signals
        signals.extend(self._analyze_sma(closes))
        
        # VWAP
        signals.append(self._analyze_vwap(candles))
        
        # VWMA
        signals.append(self._analyze_vwma(closes, volumes))
        
        # HMA (Hull Moving Average)
        signals.append(self._analyze_hma(closes))
        
        # Keltner Channels
        signals.append(self._analyze_keltner(candles))
        
        # Donchian Channels
        signals.append(self._analyze_donchian(candles))
        
        # Supertrend
        signals.append(self._analyze_supertrend(candles))
        
        # Ichimoku
        signals.append(self._analyze_ichimoku(closes))
        
        # Parabolic SAR
        signals.append(self._analyze_psar(candles))
        
        # Stochastic RSI
        signals.append(self._analyze_stoch_rsi(closes))
        
        # TRIX
        signals.append(self._analyze_trix(closes))
        
        # ADL (Accumulation/Distribution Line)
        signals.append(self._analyze_adl(candles))
        
        # CMF (Chaikin Money Flow)
        signals.append(self._analyze_cmf(candles))
        
        # Volume with MA
        signals.append(self._analyze_volume(candles))
        
        # BB Width
        signals.append(self._analyze_bb_width(closes))
        
        # Historical Volatility
        signals.append(self._analyze_hist_vol(closes))
        
        # DMI (+DI/-DI)
        signals.append(self._analyze_dmi(candles))
        
        # Aroon
        signals.append(self._analyze_aroon(candles))
        
        # Sort by strength
        signals.sort(key=lambda s: s.strength, reverse=True)
        
        return signals
    
    def _analyze_rsi_full(self, closes: List[float]) -> IndicatorSignal:
        """Analyze RSI - ALWAYS returns a signal (even neutral)."""
        rsi = self._rsi(closes, 14)
        
        if rsi > 70:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BEARISH,
                strength=0.6 + (rsi - 70) / 60,
                value=rsi,
                signal_type="overbought",
                description=f"RSI at {rsi:.1f} — overbought territory"
            )
        elif rsi < 30:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BULLISH,
                strength=0.6 + (30 - rsi) / 60,
                value=rsi,
                signal_type="oversold",
                description=f"RSI at {rsi:.1f} — oversold territory"
            )
        elif 50 < rsi < 70:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BULLISH,
                strength=0.4,
                value=rsi,
                signal_type="bullish_momentum",
                description=f"RSI at {rsi:.1f} — bullish momentum"
            )
        elif 30 < rsi < 50:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BEARISH,
                strength=0.4,
                value=rsi,
                signal_type="bearish_momentum",
                description=f"RSI at {rsi:.1f} — bearish momentum"
            )
        else:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.NEUTRAL,
                strength=0.2,
                value=rsi,
                signal_type="neutral",
                description=f"RSI at {rsi:.1f} — neutral zone"
            )
    
    def _analyze_macd_full(self, closes: List[float]) -> IndicatorSignal:
        """Analyze MACD - ALWAYS returns a signal."""
        if len(closes) < 35:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient data for MACD"
            )
        
        macd_line, signal_line, histogram = self._macd(closes)
        prev_closes = closes[:-1]
        prev_macd, prev_signal, prev_hist = self._macd(prev_closes)
        
        if prev_macd < prev_signal and macd_line > signal_line:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BULLISH,
                strength=0.75,
                value=histogram,
                signal_type="bullish_cross",
                description="MACD crossed above signal line — bullish momentum"
            )
        elif prev_macd > prev_signal and macd_line < signal_line:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BEARISH,
                strength=0.75,
                value=histogram,
                signal_type="bearish_cross",
                description="MACD crossed below signal line — bearish momentum"
            )
        elif histogram > 0:
            strength = min(0.6, 0.3 + abs(histogram) / 100)
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BULLISH,
                strength=strength,
                value=histogram,
                signal_type="bullish_histogram",
                description=f"MACD histogram positive ({histogram:.2f})"
            )
        elif histogram < 0:
            strength = min(0.6, 0.3 + abs(histogram) / 100)
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BEARISH,
                strength=strength,
                value=histogram,
                signal_type="bearish_histogram",
                description=f"MACD histogram negative ({histogram:.2f})"
            )
        else:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.NEUTRAL,
                strength=0.2,
                value=histogram,
                signal_type="neutral",
                description="MACD neutral"
            )
    
    def _analyze_bollinger_full(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Bollinger Bands - ALWAYS returns a signal."""
        if len(closes) < 20:
            return IndicatorSignal(
                name="BB",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient data for Bollinger Bands"
            )
        
        upper, middle, lower = self._bollinger_bands(closes, 20, 2.0)
        current_price = closes[-1]
        
        # Position within bands
        band_range = upper - lower if upper != lower else 1
        position = (current_price - lower) / band_range  # 0 to 1
        
        if current_price > upper:
            return IndicatorSignal(
                name="BB",
                direction=Direction.BEARISH,
                strength=0.6,
                value=position,
                signal_type="above_upper",
                description="Price above upper Bollinger Band — overbought"
            )
        elif current_price < lower:
            return IndicatorSignal(
                name="BB",
                direction=Direction.BULLISH,
                strength=0.6,
                value=position,
                signal_type="below_lower",
                description="Price below lower Bollinger Band — oversold"
            )
        elif position > 0.7:
            return IndicatorSignal(
                name="BB",
                direction=Direction.BEARISH,
                strength=0.35,
                value=position,
                signal_type="upper_zone",
                description="Price in upper Bollinger zone"
            )
        elif position < 0.3:
            return IndicatorSignal(
                name="BB",
                direction=Direction.BULLISH,
                strength=0.35,
                value=position,
                signal_type="lower_zone",
                description="Price in lower Bollinger zone"
            )
        else:
            return IndicatorSignal(
                name="BB",
                direction=Direction.NEUTRAL,
                strength=0.2,
                value=position,
                signal_type="middle_zone",
                description="Price in middle Bollinger zone"
            )
    
    def _analyze_stochastic_full(self, closes: List[float], highs: List[float], lows: List[float]) -> IndicatorSignal:
        """Analyze Stochastic - ALWAYS returns a signal."""
        if len(closes) < 14:
            return IndicatorSignal(
                name="STOCH",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=50,
                signal_type="insufficient_data",
                description="Insufficient data for Stochastic"
            )
        
        k, d = self._stochastic(closes, highs, lows)
        
        if k > 80:
            strength = 0.5 + (k - 80) / 40
            return IndicatorSignal(
                name="STOCH",
                direction=Direction.BEARISH,
                strength=min(strength, 0.8),
                value=k,
                signal_type="overbought",
                description=f"Stochastic at {k:.1f} — overbought"
            )
        elif k < 20:
            strength = 0.5 + (20 - k) / 40
            return IndicatorSignal(
                name="STOCH",
                direction=Direction.BULLISH,
                strength=min(strength, 0.8),
                value=k,
                signal_type="oversold",
                description=f"Stochastic at {k:.1f} — oversold"
            )
        elif k > 50:
            return IndicatorSignal(
                name="STOCH",
                direction=Direction.BULLISH,
                strength=0.35,
                value=k,
                signal_type="bullish_zone",
                description=f"Stochastic at {k:.1f} — bullish zone"
            )
        elif k < 50:
            return IndicatorSignal(
                name="STOCH",
                direction=Direction.BEARISH,
                strength=0.35,
                value=k,
                signal_type="bearish_zone",
                description=f"Stochastic at {k:.1f} — bearish zone"
            )
        else:
            return IndicatorSignal(
                name="STOCH",
                direction=Direction.NEUTRAL,
                strength=0.2,
                value=k,
                signal_type="neutral",
                description=f"Stochastic at {k:.1f} — neutral"
            )
    
    def _analyze_obv_full(self, closes: List[float], volumes: List[float]) -> IndicatorSignal:
        """Analyze OBV - ALWAYS returns a signal."""
        if len(closes) < 20 or sum(volumes) == 0:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient volume data"
            )
        
        obv = self._obv(closes, volumes)
        obv_ma = sum(obv[-20:]) / 20 if len(obv) >= 20 else obv[-1]
        current_obv = obv[-1]
        
        # OBV trend
        obv_5_ago = obv[-5] if len(obv) >= 5 else obv[0]
        obv_change = (current_obv - obv_5_ago) / abs(obv_5_ago) if obv_5_ago != 0 else 0
        
        # Price trend
        price_5_ago = closes[-5] if len(closes) >= 5 else closes[0]
        price_change = (closes[-1] - price_5_ago) / price_5_ago if price_5_ago != 0 else 0
        
        # Divergence check
        if obv_change > 0.05 and price_change < -0.02:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BULLISH,
                strength=0.7,
                value=current_obv,
                signal_type="bullish_divergence",
                description="OBV rising while price falls — bullish divergence"
            )
        elif obv_change < -0.05 and price_change > 0.02:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BEARISH,
                strength=0.7,
                value=current_obv,
                signal_type="bearish_divergence",
                description="OBV falling while price rises — bearish divergence"
            )
        elif current_obv > obv_ma:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BULLISH,
                strength=0.5,
                value=current_obv,
                signal_type="volume_confirmation",
                description="OBV confirms bullish price movement"
            )
        elif current_obv < obv_ma:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BEARISH,
                strength=0.5,
                value=current_obv,
                signal_type="volume_rejection",
                description="OBV shows bearish volume trend"
            )
        else:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.NEUTRAL,
                strength=0.2,
                value=current_obv,
                signal_type="neutral",
                description="OBV neutral"
            )
    
    def _analyze_adx(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze ADX for trend strength."""
        if len(candles) < 28:
            return IndicatorSignal(
                name="ADX",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient data for ADX"
            )
        
        adx = self._adx(candles)
        
        if adx > 40:
            return IndicatorSignal(
                name="ADX",
                direction=Direction.BULLISH,  # Strong trend (direction from +DI/-DI)
                strength=0.6,
                value=adx,
                signal_type="strong_trend",
                description=f"ADX at {adx:.1f} — very strong trend"
            )
        elif adx > 25:
            return IndicatorSignal(
                name="ADX",
                direction=Direction.BULLISH,
                strength=0.45,
                value=adx,
                signal_type="trending",
                description=f"ADX at {adx:.1f} — trending market"
            )
        elif adx < 20:
            return IndicatorSignal(
                name="ADX",
                direction=Direction.NEUTRAL,
                strength=0.3,
                value=adx,
                signal_type="ranging",
                description=f"ADX at {adx:.1f} — ranging/consolidation"
            )
        else:
            return IndicatorSignal(
                name="ADX",
                direction=Direction.NEUTRAL,
                strength=0.25,
                value=adx,
                signal_type="weak_trend",
                description=f"ADX at {adx:.1f} — weak trend"
            )
    
    def _analyze_cci(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze CCI (Commodity Channel Index)."""
        if len(candles) < 20:
            return IndicatorSignal(
                name="CCI",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient data for CCI"
            )
        
        cci = self._cci(candles)
        
        if cci > 100:
            return IndicatorSignal(
                name="CCI",
                direction=Direction.BEARISH,
                strength=min(0.7, 0.4 + abs(cci) / 400),
                value=cci,
                signal_type="overbought",
                description=f"CCI at {cci:.1f} — overbought"
            )
        elif cci < -100:
            return IndicatorSignal(
                name="CCI",
                direction=Direction.BULLISH,
                strength=min(0.7, 0.4 + abs(cci) / 400),
                value=cci,
                signal_type="oversold",
                description=f"CCI at {cci:.1f} — oversold"
            )
        elif cci > 0:
            return IndicatorSignal(
                name="CCI",
                direction=Direction.BULLISH,
                strength=0.35,
                value=cci,
                signal_type="bullish_zone",
                description=f"CCI at {cci:.1f} — bullish"
            )
        else:
            return IndicatorSignal(
                name="CCI",
                direction=Direction.BEARISH,
                strength=0.35,
                value=cci,
                signal_type="bearish_zone",
                description=f"CCI at {cci:.1f} — bearish"
            )
    
    def _analyze_mfi(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Money Flow Index."""
        if len(candles) < 14:
            return IndicatorSignal(
                name="MFI",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=50,
                signal_type="insufficient_data",
                description="Insufficient data for MFI"
            )
        
        mfi = self._mfi(candles)
        
        if mfi > 80:
            return IndicatorSignal(
                name="MFI",
                direction=Direction.BEARISH,
                strength=0.55,
                value=mfi,
                signal_type="overbought",
                description=f"MFI at {mfi:.1f} — overbought, money flowing out"
            )
        elif mfi < 20:
            return IndicatorSignal(
                name="MFI",
                direction=Direction.BULLISH,
                strength=0.55,
                value=mfi,
                signal_type="oversold",
                description=f"MFI at {mfi:.1f} — oversold, money flowing in"
            )
        elif mfi > 50:
            return IndicatorSignal(
                name="MFI",
                direction=Direction.BULLISH,
                strength=0.35,
                value=mfi,
                signal_type="bullish_flow",
                description=f"MFI at {mfi:.1f} — positive money flow"
            )
        else:
            return IndicatorSignal(
                name="MFI",
                direction=Direction.BEARISH,
                strength=0.35,
                value=mfi,
                signal_type="bearish_flow",
                description=f"MFI at {mfi:.1f} — negative money flow"
            )
    
    def _analyze_williams_r(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Williams %R."""
        if len(candles) < 14:
            return IndicatorSignal(
                name="WILLR",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=-50,
                signal_type="insufficient_data",
                description="Insufficient data for Williams %R"
            )
        
        willr = self._williams_r(candles)
        
        if willr > -20:
            return IndicatorSignal(
                name="WILLR",
                direction=Direction.BEARISH,
                strength=0.5,
                value=willr,
                signal_type="overbought",
                description=f"Williams %R at {willr:.1f} — overbought"
            )
        elif willr < -80:
            return IndicatorSignal(
                name="WILLR",
                direction=Direction.BULLISH,
                strength=0.5,
                value=willr,
                signal_type="oversold",
                description=f"Williams %R at {willr:.1f} — oversold"
            )
        elif willr > -50:
            return IndicatorSignal(
                name="WILLR",
                direction=Direction.BULLISH,
                strength=0.3,
                value=willr,
                signal_type="bullish_zone",
                description=f"Williams %R at {willr:.1f}"
            )
        else:
            return IndicatorSignal(
                name="WILLR",
                direction=Direction.BEARISH,
                strength=0.3,
                value=willr,
                signal_type="bearish_zone",
                description=f"Williams %R at {willr:.1f}"
            )
    
    def _analyze_momentum(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Momentum indicator."""
        if len(closes) < 14:
            return IndicatorSignal(
                name="MOM",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient data for Momentum"
            )
        
        mom = closes[-1] - closes[-14]
        mom_pct = mom / closes[-14] * 100 if closes[-14] != 0 else 0
        
        if mom_pct > 5:
            return IndicatorSignal(
                name="MOM",
                direction=Direction.BULLISH,
                strength=min(0.65, 0.4 + abs(mom_pct) / 20),
                value=mom,
                signal_type="strong_bullish",
                description=f"Momentum at {mom_pct:.1f}% — strong bullish"
            )
        elif mom_pct < -5:
            return IndicatorSignal(
                name="MOM",
                direction=Direction.BEARISH,
                strength=min(0.65, 0.4 + abs(mom_pct) / 20),
                value=mom,
                signal_type="strong_bearish",
                description=f"Momentum at {mom_pct:.1f}% — strong bearish"
            )
        elif mom > 0:
            return IndicatorSignal(
                name="MOM",
                direction=Direction.BULLISH,
                strength=0.35,
                value=mom,
                signal_type="bullish",
                description=f"Momentum at {mom_pct:.1f}% — bullish"
            )
        else:
            return IndicatorSignal(
                name="MOM",
                direction=Direction.BEARISH,
                strength=0.35,
                value=mom,
                signal_type="bearish",
                description=f"Momentum at {mom_pct:.1f}% — bearish"
            )
    
    def _analyze_roc(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Rate of Change."""
        if len(closes) < 14:
            return IndicatorSignal(
                name="ROC",
                direction=Direction.NEUTRAL,
                strength=0.1,
                value=0,
                signal_type="insufficient_data",
                description="Insufficient data for ROC"
            )
        
        roc = ((closes[-1] - closes[-14]) / closes[-14]) * 100 if closes[-14] != 0 else 0
        
        if roc > 5:
            return IndicatorSignal(
                name="ROC",
                direction=Direction.BULLISH,
                strength=min(0.6, 0.35 + abs(roc) / 20),
                value=roc,
                signal_type="strong_bullish",
                description=f"ROC at {roc:.1f}% — strong momentum"
            )
        elif roc < -5:
            return IndicatorSignal(
                name="ROC",
                direction=Direction.BEARISH,
                strength=min(0.6, 0.35 + abs(roc) / 20),
                value=roc,
                signal_type="strong_bearish",
                description=f"ROC at {roc:.1f}% — strong decline"
            )
        elif roc > 0:
            return IndicatorSignal(
                name="ROC",
                direction=Direction.BULLISH,
                strength=0.3,
                value=roc,
                signal_type="bullish",
                description=f"ROC at {roc:.1f}%"
            )
        else:
            return IndicatorSignal(
                name="ROC",
                direction=Direction.BEARISH,
                strength=0.3,
                value=roc,
                signal_type="bearish",
                description=f"ROC at {roc:.1f}%"
            )
    
    # ═══════════════════════════════════════════════════════════════
    # NEW INDICATORS — always return signal, never None
    # ═══════════════════════════════════════════════════════════════
    
    def _analyze_sma(self, closes: List[float]) -> List[IndicatorSignal]:
        """Analyze SMA alignment."""
        signals = []
        if len(closes) < 50:
            signals.append(IndicatorSignal(name="SMA_STACK", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for SMA"))
            return signals
        sma20 = self._sma(closes, 20)
        sma50 = self._sma(closes, 50)
        sma200 = self._sma(closes, 200) if len(closes) >= 200 else sma50
        price = closes[-1]
        if sma20 > sma50 > sma200:
            signals.append(IndicatorSignal(name="SMA_STACK", direction=Direction.BULLISH, strength=0.7, value=sma20, signal_type="bullish_alignment", description="SMA 20 > 50 > 200 — bullish stack"))
        elif sma20 < sma50 < sma200:
            signals.append(IndicatorSignal(name="SMA_STACK", direction=Direction.BEARISH, strength=0.7, value=sma20, signal_type="bearish_alignment", description="SMA 20 < 50 < 200 — bearish stack"))
        else:
            signals.append(IndicatorSignal(name="SMA_STACK", direction=Direction.NEUTRAL, strength=0.2, value=sma20, signal_type="mixed", description="SMA mixed alignment"))
        return signals

    def _analyze_vwap(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze VWAP — price vs VWAP."""
        if len(candles) < 20:
            return IndicatorSignal(name="VWAP", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for VWAP")
        cum_tp_vol = 0.0
        cum_vol = 0.0
        for c in candles[-50:]:
            tp = (c["high"] + c["low"] + c["close"]) / 3
            vol = c.get("volume", 0)
            cum_tp_vol += tp * vol
            cum_vol += vol
        vwap = cum_tp_vol / cum_vol if cum_vol > 0 else candles[-1]["close"]
        price = candles[-1]["close"]
        pct_diff = (price - vwap) / vwap if vwap else 0
        if pct_diff > 0.02:
            return IndicatorSignal(name="VWAP", direction=Direction.BULLISH, strength=0.5, value=vwap, signal_type="above_vwap", description=f"Price {pct_diff*100:.1f}% above VWAP — bullish")
        elif pct_diff < -0.02:
            return IndicatorSignal(name="VWAP", direction=Direction.BEARISH, strength=0.5, value=vwap, signal_type="below_vwap", description=f"Price {abs(pct_diff)*100:.1f}% below VWAP — bearish")
        else:
            return IndicatorSignal(name="VWAP", direction=Direction.NEUTRAL, strength=0.2, value=vwap, signal_type="at_vwap", description="Price near VWAP — neutral")

    def _analyze_vwma(self, closes: List[float], volumes: List[float]) -> IndicatorSignal:
        """Analyze VWMA vs SMA divergence."""
        if len(closes) < 20 or sum(volumes[-20:]) == 0:
            return IndicatorSignal(name="VWMA", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for VWMA")
        period = 20
        vwma_val = sum(closes[-period+i] * volumes[-period+i] for i in range(period)) / sum(volumes[-period:]) if sum(volumes[-period:]) > 0 else closes[-1]
        sma_val = self._sma(closes, period)
        price = closes[-1]
        if price > vwma_val and vwma_val > sma_val:
            return IndicatorSignal(name="VWMA", direction=Direction.BULLISH, strength=0.45, value=vwma_val, signal_type="bullish_volume", description="VWMA above SMA — volume-backed bullish")
        elif price < vwma_val and vwma_val < sma_val:
            return IndicatorSignal(name="VWMA", direction=Direction.BEARISH, strength=0.45, value=vwma_val, signal_type="bearish_volume", description="VWMA below SMA — volume-backed bearish")
        else:
            return IndicatorSignal(name="VWMA", direction=Direction.NEUTRAL, strength=0.2, value=vwma_val, signal_type="neutral", description="VWMA neutral")

    def _analyze_hma(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Hull Moving Average direction."""
        if len(closes) < 40:
            return IndicatorSignal(name="HMA", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for HMA")
        # HMA(n) = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
        n = 20
        half_n = n // 2
        sqrt_n = int(n ** 0.5)
        wma_half = self._wma(closes, half_n)
        wma_full = self._wma(closes, n)
        diff = 2 * wma_half - wma_full
        # Simplified: use diff vs price
        price = closes[-1]
        prev_diff = 2 * self._wma(closes[:-1], half_n) - self._wma(closes[:-1], n)
        if diff > prev_diff and price > diff:
            return IndicatorSignal(name="HMA", direction=Direction.BULLISH, strength=0.5, value=diff, signal_type="hma_rising", description="HMA rising — bullish momentum")
        elif diff < prev_diff and price < diff:
            return IndicatorSignal(name="HMA", direction=Direction.BEARISH, strength=0.5, value=diff, signal_type="hma_falling", description="HMA falling — bearish momentum")
        else:
            return IndicatorSignal(name="HMA", direction=Direction.NEUTRAL, strength=0.2, value=diff, signal_type="hma_flat", description="HMA flat — neutral")

    def _analyze_keltner(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Keltner Channels."""
        if len(candles) < 20:
            return IndicatorSignal(name="KC", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for Keltner")
        closes = [c["close"] for c in candles]
        ema20 = self._ema(closes, 20)
        atr_val = self._atr(candles, 10)
        upper = ema20 + 2 * atr_val
        lower = ema20 - 2 * atr_val
        price = closes[-1]
        if price > upper:
            return IndicatorSignal(name="KC", direction=Direction.BULLISH, strength=0.55, value=price, signal_type="above_upper", description="Price above upper Keltner — strong bullish")
        elif price < lower:
            return IndicatorSignal(name="KC", direction=Direction.BEARISH, strength=0.55, value=price, signal_type="below_lower", description="Price below lower Keltner — strong bearish")
        elif price > ema20:
            return IndicatorSignal(name="KC", direction=Direction.BULLISH, strength=0.3, value=price, signal_type="upper_half", description="Price in upper Keltner half")
        elif price < ema20:
            return IndicatorSignal(name="KC", direction=Direction.BEARISH, strength=0.3, value=price, signal_type="lower_half", description="Price in lower Keltner half")
        else:
            return IndicatorSignal(name="KC", direction=Direction.NEUTRAL, strength=0.15, value=price, signal_type="mid", description="Price at Keltner midline")

    def _analyze_donchian(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Donchian Channels."""
        if len(candles) < 20:
            return IndicatorSignal(name="DC", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for Donchian")
        period = 20
        highest = max(c["high"] for c in candles[-period:])
        lowest = min(c["low"] for c in candles[-period:])
        mid = (highest + lowest) / 2
        price = candles[-1]["close"]
        band_range = highest - lowest if highest != lowest else 1
        pos = (price - lowest) / band_range
        if pos > 0.9:
            return IndicatorSignal(name="DC", direction=Direction.BULLISH, strength=0.55, value=price, signal_type="near_high", description="Price near Donchian high — bullish breakout")
        elif pos < 0.1:
            return IndicatorSignal(name="DC", direction=Direction.BEARISH, strength=0.55, value=price, signal_type="near_low", description="Price near Donchian low — bearish breakdown")
        elif pos > 0.5:
            return IndicatorSignal(name="DC", direction=Direction.BULLISH, strength=0.3, value=price, signal_type="upper_half", description="Price in upper Donchian half")
        else:
            return IndicatorSignal(name="DC", direction=Direction.BEARISH, strength=0.3, value=price, signal_type="lower_half", description="Price in lower Donchian half")

    def _analyze_supertrend(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Supertrend indicator."""
        if len(candles) < 14:
            return IndicatorSignal(name="ST", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for Supertrend")
        atr_val = self._atr(candles, 10)
        multiplier = 3.0
        closes = [c["close"] for c in candles]
        hl2 = (candles[-1]["high"] + candles[-1]["low"]) / 2
        upper_band = hl2 + multiplier * atr_val
        lower_band = hl2 - multiplier * atr_val
        price = closes[-1]
        if price > upper_band:
            return IndicatorSignal(name="ST", direction=Direction.BULLISH, strength=0.6, value=lower_band, signal_type="bullish_trend", description="Supertrend bullish — price above upper band")
        elif price < lower_band:
            return IndicatorSignal(name="ST", direction=Direction.BEARISH, strength=0.6, value=upper_band, signal_type="bearish_trend", description="Supertrend bearish — price below lower band")
        # Simple approach: compare to midpoint
        elif price > hl2:
            return IndicatorSignal(name="ST", direction=Direction.BULLISH, strength=0.4, value=hl2, signal_type="bullish", description="Supertrend leaning bullish")
        else:
            return IndicatorSignal(name="ST", direction=Direction.BEARISH, strength=0.4, value=hl2, signal_type="bearish", description="Supertrend leaning bearish")

    def _analyze_ichimoku(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Ichimoku Cloud."""
        if len(closes) < 52:
            return IndicatorSignal(name="ICHI", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for Ichimoku")
        # Tenkan-sen (9)
        tenkan = (max(closes[-9:]) + min(closes[-9:])) / 2
        # Kijun-sen (26)
        kijun = (max(closes[-26:]) + min(closes[-26:])) / 2
        # Senkou Span A
        senkou_a = (tenkan + kijun) / 2
        # Senkou Span B (52)
        senkou_b = (max(closes[-52:]) + min(closes[-52:])) / 2
        price = closes[-1]
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        if price > cloud_top and tenkan > kijun:
            return IndicatorSignal(name="ICHI", direction=Direction.BULLISH, strength=0.7, value=price, signal_type="above_cloud_bullish", description="Price above Ichimoku cloud + TK cross bullish")
        elif price > cloud_top:
            return IndicatorSignal(name="ICHI", direction=Direction.BULLISH, strength=0.5, value=price, signal_type="above_cloud", description="Price above Ichimoku cloud")
        elif price < cloud_bottom and tenkan < kijun:
            return IndicatorSignal(name="ICHI", direction=Direction.BEARISH, strength=0.7, value=price, signal_type="below_cloud_bearish", description="Price below Ichimoku cloud + TK cross bearish")
        elif price < cloud_bottom:
            return IndicatorSignal(name="ICHI", direction=Direction.BEARISH, strength=0.5, value=price, signal_type="below_cloud", description="Price below Ichimoku cloud")
        else:
            return IndicatorSignal(name="ICHI", direction=Direction.NEUTRAL, strength=0.3, value=price, signal_type="inside_cloud", description="Price inside Ichimoku cloud — indecision")

    def _analyze_psar(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Parabolic SAR."""
        if len(candles) < 20:
            return IndicatorSignal(name="PSAR", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for PSAR")
        # Simplified PSAR: use recent high/low trend
        price = candles[-1]["close"]
        recent_highs = [c["high"] for c in candles[-10:]]
        recent_lows = [c["low"] for c in candles[-10:]]
        # If highs are rising and lows are rising -> bullish (PSAR below price)
        hh = all(recent_highs[i] >= recent_highs[i-1] for i in range(1, len(recent_highs)))
        hl = all(recent_lows[i] >= recent_lows[i-1] for i in range(1, len(recent_lows)))
        ll = all(recent_lows[i] <= recent_lows[i-1] for i in range(1, len(recent_lows)))
        lh = all(recent_highs[i] <= recent_highs[i-1] for i in range(1, len(recent_highs)))
        if hh and hl:
            return IndicatorSignal(name="PSAR", direction=Direction.BULLISH, strength=0.55, value=price, signal_type="bullish_trend", description="PSAR below price — bullish trend")
        elif ll and lh:
            return IndicatorSignal(name="PSAR", direction=Direction.BEARISH, strength=0.55, value=price, signal_type="bearish_trend", description="PSAR above price — bearish trend")
        elif price > (sum(recent_highs) / len(recent_highs) + sum(recent_lows) / len(recent_lows)) / 2:
            return IndicatorSignal(name="PSAR", direction=Direction.BULLISH, strength=0.3, value=price, signal_type="bullish_lean", description="PSAR leaning bullish")
        else:
            return IndicatorSignal(name="PSAR", direction=Direction.BEARISH, strength=0.3, value=price, signal_type="bearish_lean", description="PSAR leaning bearish")

    def _analyze_stoch_rsi(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Stochastic RSI."""
        if len(closes) < 28:
            return IndicatorSignal(name="SRSI", direction=Direction.NEUTRAL, strength=0.1, value=50, signal_type="insufficient_data", description="Insufficient data for Stoch RSI")
        # Compute RSI series for last 14 bars
        rsi_values = []
        for i in range(14, min(28, len(closes))):
            rsi_values.append(self._rsi(closes[:len(closes)-14+i+1], 14))
        if not rsi_values:
            rsi_values = [self._rsi(closes, 14)]
        # Stochastic of RSI
        min_rsi = min(rsi_values)
        max_rsi = max(rsi_values)
        current_rsi = rsi_values[-1]
        if max_rsi == min_rsi:
            stoch_rsi = 50.0
        else:
            stoch_rsi = ((current_rsi - min_rsi) / (max_rsi - min_rsi)) * 100
        if stoch_rsi > 80:
            return IndicatorSignal(name="SRSI", direction=Direction.BEARISH, strength=0.5, value=stoch_rsi, signal_type="overbought", description=f"Stoch RSI at {stoch_rsi:.0f} — overbought")
        elif stoch_rsi < 20:
            return IndicatorSignal(name="SRSI", direction=Direction.BULLISH, strength=0.5, value=stoch_rsi, signal_type="oversold", description=f"Stoch RSI at {stoch_rsi:.0f} — oversold")
        elif stoch_rsi > 50:
            return IndicatorSignal(name="SRSI", direction=Direction.BULLISH, strength=0.3, value=stoch_rsi, signal_type="bullish", description=f"Stoch RSI at {stoch_rsi:.0f}")
        else:
            return IndicatorSignal(name="SRSI", direction=Direction.BEARISH, strength=0.3, value=stoch_rsi, signal_type="bearish", description=f"Stoch RSI at {stoch_rsi:.0f}")

    def _analyze_trix(self, closes: List[float]) -> IndicatorSignal:
        """Analyze TRIX (Triple Exponential Average)."""
        if len(closes) < 45:
            return IndicatorSignal(name="TRIX", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for TRIX")
        # Triple EMA of closes
        ema1 = self._ema_series(closes, 15)
        ema2 = self._ema_series(ema1, 15)
        ema3 = self._ema_series(ema2, 15)
        if len(ema3) < 2:
            return IndicatorSignal(name="TRIX", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for TRIX")
        trix = ((ema3[-1] - ema3[-2]) / ema3[-2]) * 100 if ema3[-2] != 0 else 0
        if trix > 0.05:
            return IndicatorSignal(name="TRIX", direction=Direction.BULLISH, strength=min(0.55, 0.3 + abs(trix)), value=trix, signal_type="bullish", description=f"TRIX at {trix:.3f} — bullish momentum")
        elif trix < -0.05:
            return IndicatorSignal(name="TRIX", direction=Direction.BEARISH, strength=min(0.55, 0.3 + abs(trix)), value=trix, signal_type="bearish", description=f"TRIX at {trix:.3f} — bearish momentum")
        else:
            return IndicatorSignal(name="TRIX", direction=Direction.NEUTRAL, strength=0.2, value=trix, signal_type="neutral", description=f"TRIX at {trix:.3f} — flat")

    def _analyze_adl(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Accumulation/Distribution Line."""
        if len(candles) < 20:
            return IndicatorSignal(name="ADL", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for ADL")
        adl = 0.0
        adl_values = []
        for c in candles:
            hl = c["high"] - c["low"]
            if hl > 0:
                clv = ((c["close"] - c["low"]) - (c["high"] - c["close"])) / hl
            else:
                clv = 0
            adl += clv * c.get("volume", 0)
            adl_values.append(adl)
        # Compare current ADL to 20-bar average
        adl_ma = sum(adl_values[-20:]) / 20
        price_change = (candles[-1]["close"] - candles[-20]["close"]) / candles[-20]["close"] if candles[-20]["close"] != 0 else 0
        adl_trend = 1 if adl_values[-1] > adl_ma else -1
        if adl_trend > 0 and price_change < -0.01:
            return IndicatorSignal(name="ADL", direction=Direction.BULLISH, strength=0.6, value=adl, signal_type="bullish_divergence", description="ADL rising while price falls — accumulation")
        elif adl_trend < 0 and price_change > 0.01:
            return IndicatorSignal(name="ADL", direction=Direction.BEARISH, strength=0.6, value=adl, signal_type="bearish_divergence", description="ADL falling while price rises — distribution")
        elif adl_values[-1] > adl_ma:
            return IndicatorSignal(name="ADL", direction=Direction.BULLISH, strength=0.4, value=adl, signal_type="accumulation", description="ADL above average — accumulation")
        elif adl_values[-1] < adl_ma:
            return IndicatorSignal(name="ADL", direction=Direction.BEARISH, strength=0.4, value=adl, signal_type="distribution", description="ADL below average — distribution")
        else:
            return IndicatorSignal(name="ADL", direction=Direction.NEUTRAL, strength=0.2, value=adl, signal_type="neutral", description="ADL neutral")

    def _analyze_cmf(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Chaikin Money Flow."""
        if len(candles) < 20:
            return IndicatorSignal(name="CMF", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for CMF")
        period = 20
        mfv_sum = 0.0
        vol_sum = 0.0
        for c in candles[-period:]:
            hl = c["high"] - c["low"]
            vol = c.get("volume", 0)
            if hl > 0:
                mfm = ((c["close"] - c["low"]) - (c["high"] - c["close"])) / hl
            else:
                mfm = 0
            mfv_sum += mfm * vol
            vol_sum += vol
        cmf = mfv_sum / vol_sum if vol_sum > 0 else 0
        if cmf > 0.1:
            return IndicatorSignal(name="CMF", direction=Direction.BULLISH, strength=0.55, value=cmf, signal_type="strong_inflow", description=f"CMF at {cmf:.3f} — strong money inflow")
        elif cmf > 0:
            return IndicatorSignal(name="CMF", direction=Direction.BULLISH, strength=0.35, value=cmf, signal_type="inflow", description=f"CMF at {cmf:.3f} — money inflow")
        elif cmf < -0.1:
            return IndicatorSignal(name="CMF", direction=Direction.BEARISH, strength=0.55, value=cmf, signal_type="strong_outflow", description=f"CMF at {cmf:.3f} — strong money outflow")
        elif cmf < 0:
            return IndicatorSignal(name="CMF", direction=Direction.BEARISH, strength=0.35, value=cmf, signal_type="outflow", description=f"CMF at {cmf:.3f} — money outflow")
        else:
            return IndicatorSignal(name="CMF", direction=Direction.NEUTRAL, strength=0.15, value=cmf, signal_type="neutral", description="CMF neutral")

    def _analyze_volume(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Volume vs MA."""
        if len(candles) < 20:
            return IndicatorSignal(name="VOL", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for Volume")
        volumes = [c.get("volume", 0) for c in candles]
        vol_ma = sum(volumes[-20:]) / 20
        current_vol = volumes[-1]
        price_change = candles[-1]["close"] - candles[-2]["close"] if len(candles) >= 2 else 0
        ratio = current_vol / vol_ma if vol_ma > 0 else 1.0
        if ratio > 1.5 and price_change > 0:
            return IndicatorSignal(name="VOL", direction=Direction.BULLISH, strength=0.55, value=current_vol, signal_type="high_vol_up", description=f"Volume {ratio:.1f}x average on up move")
        elif ratio > 1.5 and price_change < 0:
            return IndicatorSignal(name="VOL", direction=Direction.BEARISH, strength=0.55, value=current_vol, signal_type="high_vol_down", description=f"Volume {ratio:.1f}x average on down move")
        elif ratio < 0.5:
            return IndicatorSignal(name="VOL", direction=Direction.NEUTRAL, strength=0.3, value=current_vol, signal_type="low_volume", description="Low volume — weak conviction")
        else:
            return IndicatorSignal(name="VOL", direction=Direction.NEUTRAL, strength=0.15, value=current_vol, signal_type="normal", description="Volume near average")

    def _analyze_bb_width(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Bollinger Band Width (squeeze detection)."""
        if len(closes) < 40:
            return IndicatorSignal(name="BBW", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for BB Width")
        upper, middle, lower = self._bollinger_bands(closes, 20, 2.0)
        width = (upper - lower) / middle if middle > 0 else 0
        # Historical width for comparison
        widths = []
        for i in range(20, min(len(closes), 60)):
            u, m, l = self._bollinger_bands(closes[:i], 20, 2.0)
            if m > 0:
                widths.append((u - l) / m)
        avg_width = sum(widths) / len(widths) if widths else width
        ratio = width / avg_width if avg_width > 0 else 1
        if ratio < 0.6:
            return IndicatorSignal(name="BBW", direction=Direction.NEUTRAL, strength=0.6, value=width, signal_type="squeeze", description="BB Squeeze — low volatility, expect breakout")
        elif ratio > 1.5:
            return IndicatorSignal(name="BBW", direction=Direction.NEUTRAL, strength=0.4, value=width, signal_type="expansion", description="BB Expansion — high volatility")
        else:
            return IndicatorSignal(name="BBW", direction=Direction.NEUTRAL, strength=0.2, value=width, signal_type="normal", description="BB Width normal")

    def _analyze_hist_vol(self, closes: List[float]) -> IndicatorSignal:
        """Analyze Historical Volatility."""
        if len(closes) < 21:
            return IndicatorSignal(name="HV", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for HV")
        # Log returns
        returns = []
        for i in range(1, min(21, len(closes))):
            if closes[-i-1] > 0:
                returns.append((closes[-i] - closes[-i-1]) / closes[-i-1])
        if not returns:
            return IndicatorSignal(name="HV", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for HV")
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        hv = (variance ** 0.5) * (252 ** 0.5) * 100  # Annualized
        if hv > 80:
            return IndicatorSignal(name="HV", direction=Direction.NEUTRAL, strength=0.55, value=hv, signal_type="extreme_volatility", description=f"Historical volatility at {hv:.0f}% — extreme")
        elif hv > 40:
            return IndicatorSignal(name="HV", direction=Direction.NEUTRAL, strength=0.4, value=hv, signal_type="high_volatility", description=f"Historical volatility at {hv:.0f}% — elevated")
        elif hv < 15:
            return IndicatorSignal(name="HV", direction=Direction.NEUTRAL, strength=0.45, value=hv, signal_type="low_volatility", description=f"Historical volatility at {hv:.0f}% — low, expect move")
        else:
            return IndicatorSignal(name="HV", direction=Direction.NEUTRAL, strength=0.2, value=hv, signal_type="normal", description=f"Historical volatility at {hv:.0f}%")

    def _analyze_dmi(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze DMI (+DI / -DI)."""
        if len(candles) < 28:
            return IndicatorSignal(name="DMI", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for DMI")
        period = 14
        plus_dm_sum = 0
        minus_dm_sum = 0
        tr_sum = 0
        for i in range(-period, 0):
            h = candles[i]["high"]
            l = candles[i]["low"]
            ph = candles[i-1]["high"]
            pl = candles[i-1]["low"]
            pc = candles[i-1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_sum += tr
            up_move = h - ph
            down_move = pl - l
            plus_dm_sum += up_move if (up_move > down_move and up_move > 0) else 0
            minus_dm_sum += down_move if (down_move > up_move and down_move > 0) else 0
        plus_di = (plus_dm_sum / tr_sum) * 100 if tr_sum > 0 else 0
        minus_di = (minus_dm_sum / tr_sum) * 100 if tr_sum > 0 else 0
        if plus_di > minus_di and (plus_di - minus_di) > 10:
            return IndicatorSignal(name="DMI", direction=Direction.BULLISH, strength=min(0.6, 0.35 + (plus_di - minus_di) / 50), value=plus_di, signal_type="bullish_trend", description=f"+DI ({plus_di:.0f}) > -DI ({minus_di:.0f}) — bullish trend")
        elif minus_di > plus_di and (minus_di - plus_di) > 10:
            return IndicatorSignal(name="DMI", direction=Direction.BEARISH, strength=min(0.6, 0.35 + (minus_di - plus_di) / 50), value=minus_di, signal_type="bearish_trend", description=f"-DI ({minus_di:.0f}) > +DI ({plus_di:.0f}) — bearish trend")
        else:
            return IndicatorSignal(name="DMI", direction=Direction.NEUTRAL, strength=0.2, value=plus_di, signal_type="no_trend", description=f"+DI ({plus_di:.0f}) ≈ -DI ({minus_di:.0f}) — no clear trend")

    def _analyze_aroon(self, candles: List[Dict]) -> IndicatorSignal:
        """Analyze Aroon Up/Down."""
        period = 25
        if len(candles) < period:
            return IndicatorSignal(name="AROON", direction=Direction.NEUTRAL, strength=0.1, value=0, signal_type="insufficient_data", description="Insufficient data for Aroon")
        recent = candles[-period:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        days_since_high = period - 1 - highs.index(max(highs))
        days_since_low = period - 1 - lows.index(min(lows))
        aroon_up = ((period - days_since_high) / period) * 100
        aroon_down = ((period - days_since_low) / period) * 100
        if aroon_up > 70 and aroon_down < 30:
            return IndicatorSignal(name="AROON", direction=Direction.BULLISH, strength=0.55, value=aroon_up, signal_type="strong_uptrend", description=f"Aroon Up {aroon_up:.0f}, Down {aroon_down:.0f} — strong uptrend")
        elif aroon_down > 70 and aroon_up < 30:
            return IndicatorSignal(name="AROON", direction=Direction.BEARISH, strength=0.55, value=aroon_down, signal_type="strong_downtrend", description=f"Aroon Up {aroon_up:.0f}, Down {aroon_down:.0f} — strong downtrend")
        elif aroon_up > aroon_down:
            return IndicatorSignal(name="AROON", direction=Direction.BULLISH, strength=0.3, value=aroon_up, signal_type="bullish", description=f"Aroon Up {aroon_up:.0f} > Down {aroon_down:.0f}")
        elif aroon_down > aroon_up:
            return IndicatorSignal(name="AROON", direction=Direction.BEARISH, strength=0.3, value=aroon_down, signal_type="bearish", description=f"Aroon Down {aroon_down:.0f} > Up {aroon_up:.0f}")
        else:
            return IndicatorSignal(name="AROON", direction=Direction.NEUTRAL, strength=0.2, value=50, signal_type="neutral", description="Aroon neutral")

    def _analyze_ema(self, closes: List[float]) -> List[IndicatorSignal]:
        """Analyze EMA alignment and crossovers."""
        signals = []
        
        ema20 = self._ema(closes, 20)
        ema50 = self._ema(closes, 50)
        ema200 = self._ema(closes, 200) if len(closes) >= 200 else ema50
        
        current_price = closes[-1]
        
        # EMA Stack alignment
        if ema20 > ema50 > ema200:
            signals.append(IndicatorSignal(
                name="EMA_STACK",
                direction=Direction.BULLISH,
                strength=0.8,
                value=ema20,
                signal_type="bullish_alignment",
                description="EMA 20 > 50 > 200 — bullish stack alignment"
            ))
        elif ema20 < ema50 < ema200:
            signals.append(IndicatorSignal(
                name="EMA_STACK",
                direction=Direction.BEARISH,
                strength=0.8,
                value=ema20,
                signal_type="bearish_alignment",
                description="EMA 20 < 50 < 200 — bearish stack alignment"
            ))
        
        # Price position relative to EMAs
        above_count = sum([
            1 if current_price > ema20 else 0,
            1 if current_price > ema50 else 0,
            1 if current_price > ema200 else 0,
        ])
        
        if above_count == 3:
            signals.append(IndicatorSignal(
                name="PRICE_EMA_POSITION",
                direction=Direction.BULLISH,
                strength=0.7,
                value=current_price,
                signal_type="above_all_ema",
                description="Price above all major EMAs"
            ))
        elif above_count == 0:
            signals.append(IndicatorSignal(
                name="PRICE_EMA_POSITION",
                direction=Direction.BEARISH,
                strength=0.7,
                value=current_price,
                signal_type="below_all_ema",
                description="Price below all major EMAs"
            ))
        
        # EMA crossovers (check last few candles)
        ema20_prev = self._ema(closes[:-1], 20)
        ema50_prev = self._ema(closes[:-1], 50)
        
        if ema20_prev < ema50_prev and ema20 > ema50:
            signals.append(IndicatorSignal(
                name="EMA_CROSS",
                direction=Direction.BULLISH,
                strength=0.85,
                value=ema20,
                signal_type="golden_cross_20_50",
                description="EMA 20 crossed above EMA 50 — bullish signal"
            ))
        elif ema20_prev > ema50_prev and ema20 < ema50:
            signals.append(IndicatorSignal(
                name="EMA_CROSS",
                direction=Direction.BEARISH,
                strength=0.85,
                value=ema20,
                signal_type="death_cross_20_50",
                description="EMA 20 crossed below EMA 50 — bearish signal"
            ))
        
        return signals
    
    def _analyze_rsi(self, closes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze RSI for overbought/oversold and divergence."""
        rsi = self._rsi(closes, 14)
        
        if rsi > 70:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BEARISH,
                strength=0.6 + (rsi - 70) / 60,  # Higher RSI = stronger signal
                value=rsi,
                signal_type="overbought",
                description=f"RSI at {rsi:.1f} — overbought territory"
            )
        elif rsi < 30:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BULLISH,
                strength=0.6 + (30 - rsi) / 60,
                value=rsi,
                signal_type="oversold",
                description=f"RSI at {rsi:.1f} — oversold territory"
            )
        elif 50 < rsi < 70:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BULLISH,
                strength=0.4,
                value=rsi,
                signal_type="bullish_momentum",
                description=f"RSI at {rsi:.1f} — bullish momentum"
            )
        elif 30 < rsi < 50:
            return IndicatorSignal(
                name="RSI",
                direction=Direction.BEARISH,
                strength=0.4,
                value=rsi,
                signal_type="bearish_momentum",
                description=f"RSI at {rsi:.1f} — bearish momentum"
            )
        
        return None
    
    def _analyze_macd(self, closes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze MACD for crossovers and divergence."""
        if len(closes) < 35:
            return None
        
        macd_line, signal_line, histogram = self._macd(closes)
        
        # Check for crossover
        prev_closes = closes[:-1]
        prev_macd, prev_signal, prev_hist = self._macd(prev_closes)
        
        if prev_macd < prev_signal and macd_line > signal_line:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BULLISH,
                strength=0.75,
                value=histogram,
                signal_type="bullish_cross",
                description="MACD crossed above signal line — bullish momentum"
            )
        elif prev_macd > prev_signal and macd_line < signal_line:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BEARISH,
                strength=0.75,
                value=histogram,
                signal_type="bearish_cross",
                description="MACD crossed below signal line — bearish momentum"
            )
        
        # Histogram direction
        if histogram > 0 and histogram > prev_hist:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BULLISH,
                strength=0.5,
                value=histogram,
                signal_type="bullish_histogram",
                description="MACD histogram expanding positive"
            )
        elif histogram < 0 and histogram < prev_hist:
            return IndicatorSignal(
                name="MACD",
                direction=Direction.BEARISH,
                strength=0.5,
                value=histogram,
                signal_type="bearish_histogram",
                description="MACD histogram expanding negative"
            )
        
        return None
    
    def _analyze_bollinger(self, closes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze Bollinger Bands for squeeze and breakout."""
        if len(closes) < 20:
            return None
        
        middle = self._sma(closes, 20)
        std = self._std(closes[-20:])
        upper = middle + 2 * std
        lower = middle - 2 * std
        
        current_price = closes[-1]
        band_width = (upper - lower) / middle
        
        # Calculate historical band width for comparison
        historical_widths = []
        for i in range(20, min(50, len(closes))):
            hist_middle = self._sma(closes[:i], 20)
            hist_std = self._std(closes[i-20:i])
            hist_width = (2 * hist_std) / hist_middle
            historical_widths.append(hist_width)
        
        if historical_widths:
            avg_width = sum(historical_widths) / len(historical_widths)
            squeeze_ratio = band_width / avg_width
            
            if squeeze_ratio < 0.7:
                return IndicatorSignal(
                    name="BOLLINGER",
                    direction=Direction.NEUTRAL,
                    strength=0.7,
                    value=band_width,
                    signal_type="squeeze",
                    description="Bollinger Bands squeeze — volatility contraction"
                )
        
        # Check for band touches
        if current_price > upper:
            return IndicatorSignal(
                name="BOLLINGER",
                direction=Direction.BULLISH,
                strength=0.6,
                value=current_price - upper,
                signal_type="upper_breakout",
                description="Price breaking above upper Bollinger Band"
            )
        elif current_price < lower:
            return IndicatorSignal(
                name="BOLLINGER",
                direction=Direction.BEARISH,
                strength=0.6,
                value=lower - current_price,
                signal_type="lower_breakout",
                description="Price breaking below lower Bollinger Band"
            )
        
        return None
    
    def _analyze_stochastic(self, closes: List[float], highs: List[float], lows: List[float]) -> Optional[IndicatorSignal]:
        """Analyze Stochastic oscillator."""
        if len(closes) < 14:
            return None
        
        # Calculate %K
        period = 14
        lowest_low = min(lows[-period:])
        highest_high = max(highs[-period:])
        
        if highest_high == lowest_low:
            return None
        
        k = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        if k > 80:
            return IndicatorSignal(
                name="STOCHASTIC",
                direction=Direction.BEARISH,
                strength=0.55,
                value=k,
                signal_type="overbought",
                description=f"Stochastic %K at {k:.1f} — overbought"
            )
        elif k < 20:
            return IndicatorSignal(
                name="STOCHASTIC",
                direction=Direction.BULLISH,
                strength=0.55,
                value=k,
                signal_type="oversold",
                description=f"Stochastic %K at {k:.1f} — oversold"
            )
        
        return None
    
    def _analyze_atr(self, candles: List[Dict]) -> Optional[IndicatorSignal]:
        """Analyze ATR for volatility."""
        if len(candles) < 14:
            return None
        
        atr = self._atr(candles, 14)
        current_price = candles[-1]["close"]
        volatility_pct = (atr / current_price) * 100
        
        if volatility_pct > 4:
            return IndicatorSignal(
                name="ATR",
                direction=Direction.NEUTRAL,
                strength=0.5,
                value=atr,
                signal_type="high_volatility",
                description=f"ATR indicates high volatility ({volatility_pct:.1f}%)"
            )
        elif volatility_pct < 1.5:
            return IndicatorSignal(
                name="ATR",
                direction=Direction.NEUTRAL,
                strength=0.6,
                value=atr,
                signal_type="low_volatility",
                description=f"ATR indicates low volatility ({volatility_pct:.1f}%) — potential breakout"
            )
        
        return None
    
    def _analyze_obv(self, closes: List[float], volumes: List[float]) -> Optional[IndicatorSignal]:
        """Analyze On-Balance Volume."""
        if len(closes) < 20 or all(v == 0 for v in volumes):
            return None
        
        # Calculate OBV
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        # Compare recent OBV trend to price trend
        price_change = (closes[-1] - closes[-20]) / closes[-20]
        obv_change = (obv[-1] - obv[-20]) / max(abs(obv[-20]), 1)
        
        # Divergence check
        if price_change > 0.02 and obv_change < -0.1:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BEARISH,
                strength=0.6,
                value=obv[-1],
                signal_type="bearish_divergence",
                description="OBV divergence: price up, volume down — bearish warning"
            )
        elif price_change < -0.02 and obv_change > 0.1:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BULLISH,
                strength=0.6,
                value=obv[-1],
                signal_type="bullish_divergence",
                description="OBV divergence: price down, volume up — bullish signal"
            )
        
        # Confirmation
        if price_change > 0.02 and obv_change > 0.1:
            return IndicatorSignal(
                name="OBV",
                direction=Direction.BULLISH,
                strength=0.5,
                value=obv[-1],
                signal_type="volume_confirmation",
                description="OBV confirms bullish price movement"
            )
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # Calculation helpers
    # ═══════════════════════════════════════════════════════════════
    
    def _wma(self, data: List[float], period: int) -> float:
        """Weighted Moving Average."""
        if len(data) < period:
            return sum(data) / len(data) if data else 0
        subset = data[-period:]
        weights = list(range(1, period + 1))
        return sum(s * w for s, w in zip(subset, weights)) / sum(weights)
    
    def _ema_series(self, data: List[float], period: int) -> List[float]:
        """EMA as a series (needed for TRIX)."""
        if not data:
            return []
        multiplier = 2 / (period + 1)
        result = [data[0]]
        for val in data[1:]:
            result.append(val * multiplier + result[-1] * (1 - multiplier))
        return result

    def _sma(self, data: List[float], period: int) -> float:
        if len(data) < period:
            return sum(data) / len(data) if data else 0
        return sum(data[-period:]) / period
    
    def _ema(self, data: List[float], period: int) -> float:
        if not data:
            return 0
        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _std(self, data: List[float]) -> float:
        if len(data) < 2:
            return 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5
    
    def _rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _macd(self, closes: List[float]) -> Tuple[float, float, float]:
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd_line = ema12 - ema26
        
        # Calculate signal line (9-period EMA of MACD)
        macd_values = []
        for i in range(26, len(closes) + 1):
            e12 = self._ema(closes[:i], 12)
            e26 = self._ema(closes[:i], 26)
            macd_values.append(e12 - e26)
        
        signal_line = self._ema(macd_values, 9) if len(macd_values) >= 9 else macd_line
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _atr(self, candles: List[Dict], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i-1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        return sum(trs[-period:]) / period
    
    def _adx(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ADX (Average Directional Index)."""
        if len(candles) < period * 2:
            return 25.0  # Default neutral
        
        plus_dm = []
        minus_dm = []
        trs = []
        
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_high = candles[i-1]["high"]
            prev_low = candles[i-1]["low"]
            prev_close = candles[i-1]["close"]
            
            # True Range
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
            
            # +DM and -DM
            up_move = high - prev_high
            down_move = prev_low - low
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        # Smoothed averages
        atr = sum(trs[-period:]) / period
        plus_di = (sum(plus_dm[-period:]) / period) / atr * 100 if atr != 0 else 0
        minus_di = (sum(minus_dm[-period:]) / period) / atr * 100 if atr != 0 else 0
        
        # DX
        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum != 0 else 0
        
        # ADX (simplified - use DX as proxy)
        return dx
    
    def _cci(self, candles: List[Dict], period: int = 20) -> float:
        """Calculate CCI (Commodity Channel Index)."""
        if len(candles) < period:
            return 0.0
        
        typical_prices = []
        for c in candles[-period:]:
            tp = (c["high"] + c["low"] + c["close"]) / 3
            typical_prices.append(tp)
        
        sma_tp = sum(typical_prices) / period
        mean_dev = sum(abs(tp - sma_tp) for tp in typical_prices) / period
        
        if mean_dev == 0:
            return 0.0
        
        current_tp = (candles[-1]["high"] + candles[-1]["low"] + candles[-1]["close"]) / 3
        cci = (current_tp - sma_tp) / (0.015 * mean_dev)
        
        return cci
    
    def _mfi(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate MFI (Money Flow Index)."""
        if len(candles) < period + 1:
            return 50.0
        
        positive_flow = 0
        negative_flow = 0
        
        for i in range(-period, 0):
            tp = (candles[i]["high"] + candles[i]["low"] + candles[i]["close"]) / 3
            prev_tp = (candles[i-1]["high"] + candles[i-1]["low"] + candles[i-1]["close"]) / 3
            mf = tp * candles[i].get("volume", 0)
            
            if tp > prev_tp:
                positive_flow += mf
            elif tp < prev_tp:
                negative_flow += mf
        
        if negative_flow == 0:
            return 100.0
        
        mfr = positive_flow / negative_flow
        mfi = 100 - (100 / (1 + mfr))
        
        return mfi
    
    def _williams_r(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Williams %R."""
        if len(candles) < period:
            return -50.0
        
        highest_high = max(c["high"] for c in candles[-period:])
        lowest_low = min(c["low"] for c in candles[-period:])
        current_close = candles[-1]["close"]
        
        if highest_high == lowest_low:
            return -50.0
        
        willr = ((highest_high - current_close) / (highest_high - lowest_low)) * -100
        
        return willr
    
    def _bollinger_bands(self, closes: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands."""
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1]
        
        middle = sum(closes[-period:]) / period
        variance = sum((x - middle) ** 2 for x in closes[-period:]) / period
        std = variance ** 0.5
        
        upper = middle + num_std * std
        lower = middle - num_std * std
        
        return upper, middle, lower
    
    def _stochastic(self, closes: List[float], highs: List[float], lows: List[float], period: int = 14) -> Tuple[float, float]:
        """Calculate Stochastic K and D."""
        if len(closes) < period:
            return 50.0, 50.0
        
        lowest_low = min(lows[-period:])
        highest_high = max(highs[-period:])
        
        if highest_high == lowest_low:
            return 50.0, 50.0
        
        k = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # Simplified D as 3-period SMA of K
        d = k  # Simplified
        
        return k, d
    
    def _obv(self, closes: List[float], volumes: List[float]) -> List[float]:
        """Calculate OBV (On-Balance Volume)."""
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        return obv


# Singleton
_engine: Optional[IndicatorEngine] = None


def get_indicator_engine() -> IndicatorEngine:
    global _engine
    if _engine is None:
        _engine = IndicatorEngine()
    return _engine
