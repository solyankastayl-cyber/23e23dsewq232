"""
Indicator Visualization Engine
==============================
Computes indicator values for chart rendering.

Returns:
- Overlay data: EMA/SMA/BB/VWAP series for main chart
- Pane data: RSI/MACD/Stochastic/OBV/ATR series for separate panes
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IndicatorSeries:
    """Time series data for an indicator."""
    id: str
    name: str
    type: str  # overlay | oscillator | momentum | volume | volatility | trend
    data: List[Dict]  # [{time, value}, ...]
    color: str = "#3b82f6"
    line_width: int = 1
    style: str = "line"  # line | histogram | area
    
    # For multi-line indicators
    extra_lines: Optional[List[Dict]] = None  # [{name, data, color}, ...]
    
    # For bounded indicators
    overbought: Optional[float] = None
    oversold: Optional[float] = None
    zero_line: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "data": self.data,
            "color": self.color,
            "line_width": self.line_width,
            "style": self.style,
            "extra_lines": self.extra_lines,
            "overbought": self.overbought,
            "oversold": self.oversold,
            "zero_line": self.zero_line,
        }


class IndicatorVisualizationEngine:
    """Computes indicator values for visualization."""
    
    def __init__(self):
        self.colors = {
            "ema_20": "#3b82f6",   # Blue
            "ema_50": "#f59e0b",   # Amber
            "ema_200": "#ef4444",  # Red
            "sma_20": "#22c55e",   # Green
            "bb_upper": "#8b5cf6", # Purple
            "bb_middle": "#8b5cf6",
            "bb_lower": "#8b5cf6",
            "vwap": "#ec4899",     # Pink
            "rsi": "#3b82f6",
            "macd": "#22c55e",
            "macd_signal": "#ef4444",
            "macd_histogram": "#64748b",
            "stoch_k": "#3b82f6",
            "stoch_d": "#ef4444",
            "obv": "#22c55e",
            "atr": "#f59e0b",
            "adx": "#8b5cf6",
            "volume_up": "#22c55e",
            "volume_down": "#ef4444",
        }
    
    def compute_all(
        self,
        candles: List[Dict],
        enabled_indicators: List[str] = None
    ) -> Dict:
        """
        Compute all indicators for visualization.
        
        Args:
            candles: OHLCV candles [{time, open, high, low, close, volume}, ...]
            enabled_indicators: List of indicator IDs to compute (None = all core)
        
        Returns:
            {
                "overlays": [...],  # For main chart
                "panes": [...]      # Separate panes
            }
        """
        if len(candles) < 50:
            return {"overlays": [], "panes": []}
        
        # Default enabled indicators
        if enabled_indicators is None:
            enabled_indicators = [
                "ema_20", "ema_50", "ema_200",
                "bollinger_bands",
                "rsi", "macd", "stochastic",
                "obv", "atr", "adx", "volume"
            ]
        
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        times = [c.get("time", c.get("timestamp", i)) for i, c in enumerate(candles)]
        
        overlays = []
        panes = []
        
        # ═══════════════════════════════════════════════════════════════
        # OVERLAYS
        # ═══════════════════════════════════════════════════════════════
        
        if "ema_20" in enabled_indicators:
            ema20_values = self._ema_series(closes, 20)
            overlays.append(IndicatorSeries(
                id="ema_20", name="EMA 20", type="overlay",
                data=self._build_series(times, ema20_values),
                color=self.colors["ema_20"], line_width=1
            ))
        
        if "ema_50" in enabled_indicators:
            ema50_values = self._ema_series(closes, 50)
            overlays.append(IndicatorSeries(
                id="ema_50", name="EMA 50", type="overlay",
                data=self._build_series(times, ema50_values),
                color=self.colors["ema_50"], line_width=1
            ))
        
        if "ema_200" in enabled_indicators and len(closes) >= 200:
            ema200_values = self._ema_series(closes, 200)
            overlays.append(IndicatorSeries(
                id="ema_200", name="EMA 200", type="overlay",
                data=self._build_series(times, ema200_values),
                color=self.colors["ema_200"], line_width=2
            ))
        
        if "bollinger_bands" in enabled_indicators:
            bb_data = self._bollinger_bands(closes, 20, 2.0)
            overlays.append(IndicatorSeries(
                id="bb_middle", name="BB Middle", type="overlay",
                data=self._build_series(times, bb_data["middle"]),
                color=self.colors["bb_middle"], line_width=1,
                extra_lines=[
                    {"name": "BB Upper", "data": self._build_series(times, bb_data["upper"]), "color": self.colors["bb_upper"], "style": "dashed"},
                    {"name": "BB Lower", "data": self._build_series(times, bb_data["lower"]), "color": self.colors["bb_lower"], "style": "dashed"},
                ]
            ))
        
        if "vwap" in enabled_indicators:
            vwap_values = self._vwap(candles)
            overlays.append(IndicatorSeries(
                id="vwap", name="VWAP", type="overlay",
                data=self._build_series(times, vwap_values),
                color=self.colors["vwap"], line_width=2
            ))
        
        # ═══════════════════════════════════════════════════════════════
        # OSCILLATORS (Separate panes)
        # ═══════════════════════════════════════════════════════════════
        
        if "rsi" in enabled_indicators:
            rsi_values = self._rsi_series(closes, 14)
            panes.append(IndicatorSeries(
                id="rsi", name="RSI (14)", type="oscillator",
                data=self._build_series(times, rsi_values),
                color=self.colors["rsi"], line_width=2,
                overbought=70, oversold=30
            ))
        
        if "stochastic" in enabled_indicators:
            stoch_k, stoch_d = self._stochastic(closes, highs, lows, 14, 3)
            panes.append(IndicatorSeries(
                id="stochastic", name="Stochastic (14,3)", type="oscillator",
                data=self._build_series(times, stoch_k),
                color=self.colors["stoch_k"], line_width=2,
                extra_lines=[
                    {"name": "%D", "data": self._build_series(times, stoch_d), "color": self.colors["stoch_d"]}
                ],
                overbought=80, oversold=20
            ))
        
        # ═══════════════════════════════════════════════════════════════
        # MOMENTUM (Separate panes)
        # ═══════════════════════════════════════════════════════════════
        
        if "macd" in enabled_indicators:
            macd_line, signal_line, histogram = self._macd(closes, 12, 26, 9)
            panes.append(IndicatorSeries(
                id="macd", name="MACD (12,26,9)", type="momentum",
                data=self._build_series(times, macd_line),
                color=self.colors["macd"], line_width=2,
                extra_lines=[
                    {"name": "Signal", "data": self._build_series(times, signal_line), "color": self.colors["macd_signal"]},
                    {"name": "Histogram", "data": self._build_series(times, histogram), "color": self.colors["macd_histogram"], "style": "histogram"},
                ],
                zero_line=True
            ))
        
        # ═══════════════════════════════════════════════════════════════
        # VOLUME (Separate panes)
        # ═══════════════════════════════════════════════════════════════
        
        if "volume" in enabled_indicators:
            vol_data = []
            for i, (t, v, c) in enumerate(zip(times, volumes, closes)):
                prev_close = closes[i-1] if i > 0 else c
                color = self.colors["volume_up"] if c >= prev_close else self.colors["volume_down"]
                vol_data.append({"time": t, "value": v, "color": color})
            
            panes.append(IndicatorSeries(
                id="volume", name="Volume", type="volume",
                data=vol_data,
                color=self.colors["volume_up"],
                style="histogram"
            ))
        
        if "obv" in enabled_indicators:
            obv_values = self._obv(closes, volumes)
            panes.append(IndicatorSeries(
                id="obv", name="OBV", type="volume",
                data=self._build_series(times, obv_values),
                color=self.colors["obv"], line_width=2
            ))
        
        # ═══════════════════════════════════════════════════════════════
        # VOLATILITY (Separate panes)
        # ═══════════════════════════════════════════════════════════════
        
        if "atr" in enabled_indicators:
            atr_values = self._atr_series(candles, 14)
            panes.append(IndicatorSeries(
                id="atr", name="ATR (14)", type="volatility",
                data=self._build_series(times, atr_values),
                color=self.colors["atr"], line_width=2
            ))
        
        # ═══════════════════════════════════════════════════════════════
        # TREND (Separate panes)
        # ═══════════════════════════════════════════════════════════════
        
        if "adx" in enabled_indicators:
            adx_values = self._adx(candles, 14)
            panes.append(IndicatorSeries(
                id="adx", name="ADX (14)", type="trend",
                data=self._build_series(times, adx_values),
                color=self.colors["adx"], line_width=2
            ))
        
        return {
            "overlays": [o.to_dict() for o in overlays],
            "panes": [p.to_dict() for p in panes],
        }
    
    def _build_series(self, times: List, values: List) -> List[Dict]:
        """Build time-value series, filtering None values."""
        result = []
        for t, v in zip(times, values):
            if v is not None:
                result.append({"time": t, "value": round(v, 6)})
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # CALCULATION METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _ema_series(self, data: List[float], period: int) -> List[Optional[float]]:
        """Calculate EMA series."""
        result = [None] * len(data)
        if len(data) < period:
            return result
        
        multiplier = 2 / (period + 1)
        
        # First EMA = SMA
        sma = sum(data[:period]) / period
        result[period - 1] = sma
        
        ema = sma
        for i in range(period, len(data)):
            ema = (data[i] * multiplier) + (ema * (1 - multiplier))
            result[i] = ema
        
        return result
    
    def _sma_series(self, data: List[float], period: int) -> List[Optional[float]]:
        """Calculate SMA series."""
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            result[i] = sum(data[i - period + 1:i + 1]) / period
        return result
    
    def _bollinger_bands(self, closes: List[float], period: int, std_mult: float) -> Dict:
        """Calculate Bollinger Bands."""
        middle = self._sma_series(closes, period)
        upper = [None] * len(closes)
        lower = [None] * len(closes)
        
        for i in range(period - 1, len(closes)):
            if middle[i] is not None:
                window = closes[i - period + 1:i + 1]
                std = self._std(window)
                upper[i] = middle[i] + std_mult * std
                lower[i] = middle[i] - std_mult * std
        
        return {"middle": middle, "upper": upper, "lower": lower}
    
    def _std(self, data: List[float]) -> float:
        """Calculate standard deviation."""
        if len(data) < 2:
            return 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5
    
    def _vwap(self, candles: List[Dict]) -> List[Optional[float]]:
        """Calculate VWAP (cumulative for the day)."""
        result = [None] * len(candles)
        cum_volume = 0
        cum_vp = 0
        
        for i, c in enumerate(candles):
            typical_price = (c["high"] + c["low"] + c["close"]) / 3
            volume = c.get("volume", 0)
            
            cum_volume += volume
            cum_vp += typical_price * volume
            
            if cum_volume > 0:
                result[i] = cum_vp / cum_volume
        
        return result
    
    def _rsi_series(self, closes: List[float], period: int) -> List[Optional[float]]:
        """Calculate RSI series."""
        result = [None] * len(closes)
        if len(closes) < period + 1:
            return result
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        # First RSI
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            result[period] = 100
        else:
            rs = avg_gain / avg_loss
            result[period] = 100 - (100 / (1 + rs))
        
        # Subsequent RSI (smoothed)
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                result[i + 1] = 100
            else:
                rs = avg_gain / avg_loss
                result[i + 1] = 100 - (100 / (1 + rs))
        
        return result
    
    def _stochastic(self, closes: List[float], highs: List[float], lows: List[float], k_period: int, d_period: int) -> Tuple[List, List]:
        """Calculate Stochastic %K and %D."""
        k_values = [None] * len(closes)
        d_values = [None] * len(closes)
        
        for i in range(k_period - 1, len(closes)):
            highest = max(highs[i - k_period + 1:i + 1])
            lowest = min(lows[i - k_period + 1:i + 1])
            
            if highest != lowest:
                k_values[i] = ((closes[i] - lowest) / (highest - lowest)) * 100
            else:
                k_values[i] = 50
        
        # %D is SMA of %K
        for i in range(k_period + d_period - 2, len(closes)):
            k_window = [k for k in k_values[i - d_period + 1:i + 1] if k is not None]
            if k_window:
                d_values[i] = sum(k_window) / len(k_window)
        
        return k_values, d_values
    
    def _macd(self, closes: List[float], fast: int, slow: int, signal: int) -> Tuple[List, List, List]:
        """Calculate MACD line, signal line, histogram."""
        ema_fast = self._ema_series(closes, fast)
        ema_slow = self._ema_series(closes, slow)
        
        macd_line = [None] * len(closes)
        for i in range(len(closes)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]
        
        # Signal line = EMA of MACD
        macd_values = [v for v in macd_line if v is not None]
        signal_ema = self._ema_series(macd_values, signal)
        
        signal_line = [None] * len(closes)
        histogram = [None] * len(closes)
        
        macd_idx = 0
        for i in range(len(closes)):
            if macd_line[i] is not None:
                if macd_idx < len(signal_ema) and signal_ema[macd_idx] is not None:
                    signal_line[i] = signal_ema[macd_idx]
                    histogram[i] = macd_line[i] - signal_ema[macd_idx]
                macd_idx += 1
        
        return macd_line, signal_line, histogram
    
    def _obv(self, closes: List[float], volumes: List[float]) -> List[float]:
        """Calculate OBV."""
        result = [0.0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                result.append(result[-1] + volumes[i])
            elif closes[i] < closes[i - 1]:
                result.append(result[-1] - volumes[i])
            else:
                result.append(result[-1])
        return result
    
    def _atr_series(self, candles: List[Dict], period: int) -> List[Optional[float]]:
        """Calculate ATR series."""
        result = [None] * len(candles)
        if len(candles) < period + 1:
            return result
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        # First ATR = average of first N TRs
        if len(trs) >= period:
            result[period] = sum(trs[:period]) / period
            
            # Subsequent ATRs (smoothed)
            for i in range(period, len(trs)):
                result[i + 1] = (result[i] * (period - 1) + trs[i]) / period
        
        return result
    
    def _adx(self, candles: List[Dict], period: int) -> List[Optional[float]]:
        """Calculate ADX."""
        result = [None] * len(candles)
        if len(candles) < period * 2:
            return result
        
        plus_dm = []
        minus_dm = []
        trs = []
        
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_high = candles[i - 1]["high"]
            prev_low = candles[i - 1]["low"]
            prev_close = candles[i - 1]["close"]
            
            # True Range
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
            
            # Directional Movement
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
        
        # Smooth the values
        if len(trs) >= period:
            atr = sum(trs[:period])
            plus_di_sum = sum(plus_dm[:period])
            minus_di_sum = sum(minus_dm[:period])
            
            dx_values = []
            
            for i in range(period, len(trs)):
                atr = atr - (atr / period) + trs[i]
                plus_di_sum = plus_di_sum - (plus_di_sum / period) + plus_dm[i]
                minus_di_sum = minus_di_sum - (minus_di_sum / period) + minus_dm[i]
                
                if atr > 0:
                    plus_di = 100 * plus_di_sum / atr
                    minus_di = 100 * minus_di_sum / atr
                    
                    di_sum = plus_di + minus_di
                    if di_sum > 0:
                        dx = 100 * abs(plus_di - minus_di) / di_sum
                        dx_values.append(dx)
            
            # ADX = smoothed DX
            if len(dx_values) >= period:
                adx = sum(dx_values[:period]) / period
                result[period * 2] = adx
                
                for i in range(period, len(dx_values)):
                    adx = (adx * (period - 1) + dx_values[i]) / period
                    result[period + i + 1] = adx
        
        return result


# Singleton
_engine: Optional[IndicatorVisualizationEngine] = None


def get_indicator_visualization_engine() -> IndicatorVisualizationEngine:
    global _engine
    if _engine is None:
        _engine = IndicatorVisualizationEngine()
    return _engine
