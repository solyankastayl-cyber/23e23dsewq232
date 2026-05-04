"""
Indicator API — PHASE 48.2

Provides ready-to-render indicator series:
- EMA / SMA
- VWAP
- RSI
- MACD
- ATR bands
- Bollinger
- Supertrend
- Custom alpha indicators
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import numpy as np

from modules.ta_engine.utils.time_utils import normalize_timestamp


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class IndicatorValue(BaseModel):
    """Single indicator value."""
    timestamp: str
    value: float
    extra: Dict[str, float] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_ts(cls, v):
        dt = normalize_timestamp(v)
        return dt.isoformat() if dt is not None else (str(v) if v is not None else "")


class IndicatorSeries(BaseModel):
    """Complete indicator series."""
    indicator_id: str
    name: str
    type: str  # line, histogram, area, band
    color: str = "#3B82F6"
    values: List[IndicatorValue] = Field(default_factory=list)
    
    # For bands
    upper_band: List[float] = Field(default_factory=list)
    lower_band: List[float] = Field(default_factory=list)
    middle_band: List[float] = Field(default_factory=list)
    
    # Metadata
    params: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IndicatorConfig(BaseModel):
    """Indicator configuration."""
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    color: Optional[str] = None
    visible: bool = True


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class IndicatorService:
    """Service for indicator calculations."""
    
    AVAILABLE_INDICATORS = [
        "sma", "ema", "vwap", "rsi", "macd", "atr",
        "bollinger", "supertrend", "volume_profile",
        "momentum", "stochastic", "adx", "obv",
        "cci", "williams_r", "ichimoku", "parabolic_sar",
        "donchian", "keltner",
    ]
    
    def calculate_indicator(
        self,
        name: str,
        candles: List[Dict[str, Any]],
        **params
    ) -> IndicatorSeries:
        """Calculate a single indicator."""
        
        if name == "sma":
            return self._calculate_sma(candles, **params)
        elif name == "ema":
            return self._calculate_ema(candles, **params)
        elif name == "rsi":
            return self._calculate_rsi(candles, **params)
        elif name == "macd":
            return self._calculate_macd(candles, **params)
        elif name == "bollinger":
            return self._calculate_bollinger(candles, **params)
        elif name == "atr":
            return self._calculate_atr(candles, **params)
        elif name == "vwap":
            return self._calculate_vwap(candles, **params)
        elif name == "supertrend":
            return self._calculate_supertrend(candles, **params)
        elif name == "volume_profile":
            return self._calculate_volume_profile(candles, **params)
        elif name == "cci":
            return self._calculate_cci(candles, **params)
        elif name == "williams_r":
            return self._calculate_williams_r(candles, **params)
        elif name == "ichimoku":
            return self._calculate_ichimoku(candles, **params)
        elif name == "parabolic_sar":
            return self._calculate_parabolic_sar(candles, **params)
        elif name == "donchian":
            return self._calculate_donchian(candles, **params)
        elif name == "keltner":
            return self._calculate_keltner(candles, **params)
        else:
            # Return empty series for unknown indicator
            return IndicatorSeries(
                indicator_id=f"{name}_unknown",
                name=name,
                type="line",
            )
    
    def calculate_batch(
        self,
        indicators: List[IndicatorConfig],
        candles: List[Dict[str, Any]]
    ) -> List[IndicatorSeries]:
        """Calculate multiple indicators."""
        results = []
        
        for config in indicators:
            series = self.calculate_indicator(
                config.name,
                candles,
                **config.params
            )
            
            if config.color:
                series.color = config.color
            
            results.append(series)
        
        return results
    
    def get_available_indicators(self) -> List[str]:
        """Get list of available indicators."""
        return self.AVAILABLE_INDICATORS.copy()
    
    # ═══════════════════════════════════════════════════════════════
    # Indicator Calculations
    # ═══════════════════════════════════════════════════════════════
    
    def _calculate_sma(
        self,
        candles: List[Dict[str, Any]],
        period: int = 20,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Simple Moving Average."""
        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        sma_values = []
        for i in range(len(closes)):
            if i < period - 1:
                sma = np.mean(closes[:i+1])
            else:
                sma = np.mean(closes[i-period+1:i+1])
            sma_values.append(sma)
        
        return IndicatorSeries(
            indicator_id=f"sma_{period}",
            name=f"SMA {period}",
            type="line",
            color="#F59E0B",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, sma_values)
            ],
            params={"period": period},
        )
    
    def _calculate_ema(
        self,
        candles: List[Dict[str, Any]],
        period: int = 20,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Exponential Moving Average."""
        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        multiplier = 2 / (period + 1)
        ema_values = [closes[0]]
        
        for i in range(1, len(closes)):
            ema = closes[i] * multiplier + ema_values[-1] * (1 - multiplier)
            ema_values.append(ema)
        
        return IndicatorSeries(
            indicator_id=f"ema_{period}",
            name=f"EMA {period}",
            type="line",
            color="#10B981",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, ema_values)
            ],
            params={"period": period},
        )
    
    def _calculate_rsi(
        self,
        candles: List[Dict[str, Any]],
        period: int = 14,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Relative Strength Index."""
        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        if len(closes) < 2:
            return IndicatorSeries(
                indicator_id=f"rsi_{period}",
                name=f"RSI {period}",
                type="line",
            )
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi_values = [50.0]  # First value
        
        avg_gain = np.mean(gains[:period]) if len(gains) >= period else np.mean(gains)
        avg_loss = np.mean(losses[:period]) if len(losses) >= period else np.mean(losses)
        
        for i in range(len(deltas)):
            if i < period:
                avg_gain = np.mean(gains[:i+1]) if i > 0 else gains[0]
                avg_loss = np.mean(losses[:i+1]) if i > 0 else losses[0]
            else:
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return IndicatorSeries(
            indicator_id=f"rsi_{period}",
            name=f"RSI {period}",
            type="line",
            color="#8B5CF6",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, rsi_values)
            ],
            params={"period": period},
            metadata={"overbought": 70, "oversold": 30},
        )
    
    def _calculate_macd(
        self,
        candles: List[Dict[str, Any]],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate MACD."""
        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        # Calculate EMAs
        def ema(data, period):
            multiplier = 2 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                result.append(data[i] * multiplier + result[-1] * (1 - multiplier))
            return result
        
        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = ema(macd_line, signal)
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        
        return IndicatorSeries(
            indicator_id=f"macd_{fast}_{slow}_{signal}",
            name=f"MACD ({fast},{slow},{signal})",
            type="histogram",
            color="#EF4444",
            values=[
                IndicatorValue(
                    timestamp=ts,
                    value=round(h, 4),
                    extra={"macd": round(m, 4), "signal": round(s, 4)}
                )
                for ts, h, m, s in zip(timestamps, histogram, macd_line, signal_line)
            ],
            params={"fast": fast, "slow": slow, "signal": signal},
        )
    
    def _calculate_bollinger(
        self,
        candles: List[Dict[str, Any]],
        period: int = 20,
        std_dev: float = 2.0,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Bollinger Bands."""
        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        upper = []
        middle = []
        lower = []
        
        for i in range(len(closes)):
            if i < period - 1:
                window = closes[:i+1]
            else:
                window = closes[i-period+1:i+1]
            
            sma = np.mean(window)
            std = np.std(window)
            
            middle.append(sma)
            upper.append(sma + std_dev * std)
            lower.append(sma - std_dev * std)
        
        return IndicatorSeries(
            indicator_id=f"bollinger_{period}_{std_dev}",
            name=f"Bollinger ({period}, {std_dev})",
            type="band",
            color="#06B6D4",
            values=[
                IndicatorValue(timestamp=ts, value=round(m, 2))
                for ts, m in zip(timestamps, middle)
            ],
            upper_band=[round(u, 2) for u in upper],
            middle_band=[round(m, 2) for m in middle],
            lower_band=[round(l, 2) for l in lower],
            params={"period": period, "std_dev": std_dev},
        )
    
    def _calculate_atr(
        self,
        candles: List[Dict[str, Any]],
        period: int = 14,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Average True Range."""
        timestamps = [c["timestamp"] for c in candles]
        
        tr_values = []
        for i in range(len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            if i == 0:
                tr = high - low
            else:
                prev_close = candles[i-1]["close"]
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
            tr_values.append(tr)
        
        atr_values = []
        for i in range(len(tr_values)):
            if i < period - 1:
                atr = np.mean(tr_values[:i+1])
            else:
                atr = np.mean(tr_values[i-period+1:i+1])
            atr_values.append(atr)
        
        return IndicatorSeries(
            indicator_id=f"atr_{period}",
            name=f"ATR {period}",
            type="line",
            color="#F97316",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, atr_values)
            ],
            params={"period": period},
        )
    
    def _calculate_vwap(
        self,
        candles: List[Dict[str, Any]],
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Volume Weighted Average Price."""
        timestamps = [c["timestamp"] for c in candles]
        
        cumulative_tpv = 0  # typical price * volume
        cumulative_volume = 0
        vwap_values = []
        
        for c in candles:
            typical_price = (c["high"] + c["low"] + c["close"]) / 3
            cumulative_tpv += typical_price * c["volume"]
            cumulative_volume += c["volume"]
            
            vwap = cumulative_tpv / cumulative_volume if cumulative_volume > 0 else typical_price
            vwap_values.append(vwap)
        
        return IndicatorSeries(
            indicator_id="vwap",
            name="VWAP",
            type="line",
            color="#EC4899",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, vwap_values)
            ],
        )
    
    def _calculate_supertrend(
        self,
        candles: List[Dict[str, Any]],
        period: int = 10,
        multiplier: float = 3.0,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Supertrend indicator."""
        timestamps = [c["timestamp"] for c in candles]
        
        # Calculate ATR first
        atr_values = []
        for i in range(len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            if i == 0:
                tr = high - low
            else:
                prev_close = candles[i-1]["close"]
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            
            if i < period - 1:
                atr = np.mean([tr])
            else:
                # Simplified ATR
                trs = []
                for j in range(max(0, i-period+1), i+1):
                    h = candles[j]["high"]
                    l = candles[j]["low"]
                    pc = candles[j-1]["close"] if j > 0 else h
                    trs.append(max(h-l, abs(h-pc), abs(l-pc)))
                atr = np.mean(trs)
            
            atr_values.append(atr)
        
        # Calculate Supertrend
        supertrend = []
        direction = []
        
        for i in range(len(candles)):
            hl2 = (candles[i]["high"] + candles[i]["low"]) / 2
            
            upper_band = hl2 + multiplier * atr_values[i]
            lower_band = hl2 - multiplier * atr_values[i]
            
            if i == 0:
                direction.append(1)
                supertrend.append(lower_band)
            else:
                if candles[i]["close"] > supertrend[-1]:
                    direction.append(1)
                    supertrend.append(lower_band)
                else:
                    direction.append(-1)
                    supertrend.append(upper_band)
        
        return IndicatorSeries(
            indicator_id=f"supertrend_{period}_{multiplier}",
            name=f"Supertrend ({period}, {multiplier})",
            type="line",
            color="#22C55E",
            values=[
                IndicatorValue(
                    timestamp=ts,
                    value=round(v, 2),
                    extra={"direction": d}
                )
                for ts, v, d in zip(timestamps, supertrend, direction)
            ],
            params={"period": period, "multiplier": multiplier},
        )
    
    def _calculate_volume_profile(
        self,
        candles: List[Dict[str, Any]],
        bins: int = 20,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Volume Profile."""
        if not candles:
            return IndicatorSeries(
                indicator_id="volume_profile",
                name="Volume Profile",
                type="histogram",
            )
        
        # Find price range
        all_prices = []
        for c in candles:
            all_prices.extend([c["high"], c["low"]])
        
        price_min = min(all_prices)
        price_max = max(all_prices)
        bin_size = (price_max - price_min) / bins
        
        # Aggregate volume by price level
        profile = {}
        for c in candles:
            avg_price = (c["high"] + c["low"]) / 2
            bin_idx = int((avg_price - price_min) / bin_size)
            bin_idx = min(bin_idx, bins - 1)
            bin_price = price_min + bin_idx * bin_size + bin_size / 2
            
            if bin_price not in profile:
                profile[bin_price] = 0
            profile[bin_price] += c["volume"]
        
        # Find POC (Point of Control)
        poc_price = max(profile.keys(), key=lambda p: profile[p])
        
        return IndicatorSeries(
            indicator_id="volume_profile",
            name="Volume Profile",
            type="histogram",
            color="#6366F1",
            values=[
                IndicatorValue(
                    timestamp="",
                    value=round(volume, 2),
                    extra={"price_level": round(price, 2)}
                )
                for price, volume in sorted(profile.items())
            ],
            metadata={"poc": round(poc_price, 2), "bins": bins},
        )

    # ═══════════════════════════════════════════════════════════════
    # NEW INDICATORS — PHASE TA-1
    # ═══════════════════════════════════════════════════════════════

    def _calculate_cci(
        self,
        candles: List[Dict[str, Any]],
        period: int = 20,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Commodity Channel Index."""
        timestamps = [c["timestamp"] for c in candles]
        
        tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in candles]
        
        cci_values = []
        for i in range(len(tp)):
            if i < period - 1:
                window = tp[:i+1]
            else:
                window = tp[i-period+1:i+1]
            
            sma = np.mean(window)
            mean_dev = np.mean([abs(v - sma) for v in window])
            
            if mean_dev == 0:
                cci_values.append(0.0)
            else:
                cci_values.append((tp[i] - sma) / (0.015 * mean_dev))
        
        return IndicatorSeries(
            indicator_id=f"cci_{period}",
            name=f"CCI {period}",
            type="line",
            color="#F59E0B",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, cci_values)
            ],
            params={"period": period},
            metadata={"overbought": 100, "oversold": -100},
        )

    def _calculate_williams_r(
        self,
        candles: List[Dict[str, Any]],
        period: int = 14,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Williams %R."""
        timestamps = [c["timestamp"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        
        wr_values = []
        for i in range(len(candles)):
            if i < period - 1:
                window_highs = highs[:i+1]
                window_lows = lows[:i+1]
            else:
                window_highs = highs[i-period+1:i+1]
                window_lows = lows[i-period+1:i+1]
            
            highest = max(window_highs)
            lowest = min(window_lows)
            
            if highest == lowest:
                wr_values.append(-50.0)
            else:
                wr = ((highest - closes[i]) / (highest - lowest)) * -100
                wr_values.append(wr)
        
        return IndicatorSeries(
            indicator_id=f"williams_r_{period}",
            name=f"Williams %R {period}",
            type="line",
            color="#6366F1",
            values=[
                IndicatorValue(timestamp=ts, value=round(v, 2))
                for ts, v in zip(timestamps, wr_values)
            ],
            params={"period": period},
            metadata={"overbought": -20, "oversold": -80},
        )

    def _calculate_ichimoku(
        self,
        candles: List[Dict[str, Any]],
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Ichimoku Cloud."""
        timestamps = [c["timestamp"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        
        def donchian_mid(data_h, data_l, period, idx):
            start = max(0, idx - period + 1)
            return (max(data_h[start:idx+1]) + min(data_l[start:idx+1])) / 2
        
        tenkan = []
        kijun = []
        span_a = []
        span_b = []
        chikou = []
        
        for i in range(len(candles)):
            tenkan.append(donchian_mid(highs, lows, tenkan_period, i))
            kijun.append(donchian_mid(highs, lows, kijun_period, i))
            span_a.append((tenkan[-1] + kijun[-1]) / 2)
            span_b.append(donchian_mid(highs, lows, senkou_b_period, i))
            chikou.append(closes[i])
        
        values = [
            IndicatorValue(
                timestamp=ts,
                value=round(t, 2),
                extra={
                    "kijun": round(k, 2),
                    "span_a": round(sa, 2),
                    "span_b": round(sb, 2),
                    "chikou": round(ch, 2),
                }
            )
            for ts, t, k, sa, sb, ch in zip(timestamps, tenkan, kijun, span_a, span_b, chikou)
        ]
        
        return IndicatorSeries(
            indicator_id="ichimoku",
            name="Ichimoku Cloud",
            type="band",
            color="#059669",
            values=values,
            upper_band=[round(max(a, b), 2) for a, b in zip(span_a, span_b)],
            lower_band=[round(min(a, b), 2) for a, b in zip(span_a, span_b)],
            middle_band=[round(t, 2) for t in tenkan],
            params={
                "tenkan_period": tenkan_period,
                "kijun_period": kijun_period,
                "senkou_b_period": senkou_b_period,
            },
        )

    def _calculate_parabolic_sar(
        self,
        candles: List[Dict[str, Any]],
        af_start: float = 0.02,
        af_step: float = 0.02,
        af_max: float = 0.20,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Parabolic SAR."""
        timestamps = [c["timestamp"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        if len(candles) < 2:
            return IndicatorSeries(
                indicator_id="psar", name="PSAR", type="line",
            )
        
        # Initialize
        trend_up = True
        af = af_start
        ep = highs[0]
        sar = lows[0]
        sar_values = [sar]
        directions = [1]
        
        for i in range(1, len(candles)):
            prev_sar = sar
            
            if trend_up:
                sar = prev_sar + af * (ep - prev_sar)
                sar = min(sar, lows[i-1])
                if i >= 2:
                    sar = min(sar, lows[i-2])
                
                if lows[i] < sar:
                    trend_up = False
                    sar = ep
                    ep = lows[i]
                    af = af_start
                else:
                    if highs[i] > ep:
                        ep = highs[i]
                        af = min(af + af_step, af_max)
            else:
                sar = prev_sar + af * (ep - prev_sar)
                sar = max(sar, highs[i-1])
                if i >= 2:
                    sar = max(sar, highs[i-2])
                
                if highs[i] > sar:
                    trend_up = True
                    sar = ep
                    ep = highs[i]
                    af = af_start
                else:
                    if lows[i] < ep:
                        ep = lows[i]
                        af = min(af + af_step, af_max)
            
            sar_values.append(sar)
            directions.append(1 if trend_up else -1)
        
        return IndicatorSeries(
            indicator_id="psar",
            name="Parabolic SAR",
            type="line",
            color="#EF4444",
            values=[
                IndicatorValue(
                    timestamp=ts, value=round(v, 2),
                    extra={"direction": d}
                )
                for ts, v, d in zip(timestamps, sar_values, directions)
            ],
            params={"af_start": af_start, "af_step": af_step, "af_max": af_max},
        )

    def _calculate_donchian(
        self,
        candles: List[Dict[str, Any]],
        period: int = 20,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Donchian Channel."""
        timestamps = [c["timestamp"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        upper = []
        lower = []
        middle = []
        
        for i in range(len(candles)):
            start = max(0, i - period + 1)
            h = max(highs[start:i+1])
            l = min(lows[start:i+1])
            upper.append(h)
            lower.append(l)
            middle.append((h + l) / 2)
        
        return IndicatorSeries(
            indicator_id=f"donchian_{period}",
            name=f"Donchian {period}",
            type="band",
            color="#0EA5E9",
            values=[
                IndicatorValue(timestamp=ts, value=round(m, 2))
                for ts, m in zip(timestamps, middle)
            ],
            upper_band=[round(u, 2) for u in upper],
            lower_band=[round(l, 2) for l in lower],
            middle_band=[round(m, 2) for m in middle],
            params={"period": period},
        )

    def _calculate_keltner(
        self,
        candles: List[Dict[str, Any]],
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0,
        **kwargs
    ) -> IndicatorSeries:
        """Calculate Keltner Channel."""
        timestamps = [c["timestamp"] for c in candles]
        closes = [c["close"] for c in candles]
        
        # EMA of close
        ema_mult = 2 / (ema_period + 1)
        ema_values = [closes[0]]
        for i in range(1, len(closes)):
            ema_values.append(closes[i] * ema_mult + ema_values[-1] * (1 - ema_mult))
        
        # ATR
        tr_values = []
        for i in range(len(candles)):
            h = candles[i]["high"]
            l = candles[i]["low"]
            if i == 0:
                tr_values.append(h - l)
            else:
                pc = candles[i-1]["close"]
                tr_values.append(max(h - l, abs(h - pc), abs(l - pc)))
        
        atr_values = []
        for i in range(len(tr_values)):
            start = max(0, i - atr_period + 1)
            atr_values.append(np.mean(tr_values[start:i+1]))
        
        upper = [e + multiplier * a for e, a in zip(ema_values, atr_values)]
        lower = [e - multiplier * a for e, a in zip(ema_values, atr_values)]
        
        return IndicatorSeries(
            indicator_id=f"keltner_{ema_period}_{atr_period}",
            name=f"Keltner ({ema_period}, {atr_period})",
            type="band",
            color="#D97706",
            values=[
                IndicatorValue(timestamp=ts, value=round(m, 2))
                for ts, m in zip(timestamps, ema_values)
            ],
            upper_band=[round(u, 2) for u in upper],
            lower_band=[round(l, 2) for l in lower],
            middle_band=[round(m, 2) for m in ema_values],
            params={"ema_period": ema_period, "atr_period": atr_period, "multiplier": multiplier},
        )


# Singleton
_indicator_service: Optional[IndicatorService] = None

def get_indicator_service() -> IndicatorService:
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorService()
    return _indicator_service
