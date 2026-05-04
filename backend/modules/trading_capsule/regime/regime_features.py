"""
Regime Feature Calculator
=========================

Computes features for regime classification from OHLCV data.
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .regime_types import RegimeFeatureSet, RegimeConfig


@dataclass
class Candle:
    """Simple candle structure"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class RegimeFeatureCalculator:
    """
    Calculates regime classification features from price data.
    
    All features are normalized to 0-1 range for easy comparison.
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
    
    def compute_features(
        self,
        candles: List[Candle],
        symbol: str = "",
        timeframe: str = ""
    ) -> RegimeFeatureSet:
        """
        Compute all features from candle data.
        
        Requires at least 50 candles for accurate computation.
        """
        
        features = RegimeFeatureSet(symbol=symbol, timeframe=timeframe)
        
        if len(candles) < 20:
            return features
        
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        
        # 1. Trend Strength
        features.trend_strength = self._compute_trend_strength(closes, highs, lows)
        
        # 2. Volatility Level
        vol_level, atr, atr_sma = self._compute_volatility(closes, highs, lows)
        features.volatility_level = vol_level
        features.raw_atr = atr
        features.raw_atr_sma = atr_sma
        features.atr_ratio = atr / atr_sma if atr_sma > 0 else 1.0
        
        # 3. Range Compression
        features.range_compression = self._compute_compression(closes, highs, lows)
        
        # 4. Structure Clarity
        features.structure_clarity = self._compute_structure_clarity(highs, lows)
        
        # 5. Breakout Pressure
        features.breakout_pressure = self._compute_breakout_pressure(
            closes, highs, lows, features.range_compression, features.volatility_level
        )
        
        # 6. Directional Consistency
        features.directional_consistency = self._compute_directional_consistency(closes)
        
        # 7. MA Separation
        features.ma_separation = self._compute_ma_separation(closes)
        
        # 8. Volume Trend
        features.volume_trend = self._compute_volume_trend(volumes)
        
        # 9. Candle Body Ratio
        features.candle_body_ratio = self._compute_body_ratio(candles)
        
        # Raw range
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        features.raw_range = (recent_high - recent_low) / recent_low if recent_low > 0 else 0
        
        return features
    
    def _compute_trend_strength(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> float:
        """
        Compute trend strength (0-1).
        
        Uses combination of:
        - Price slope
        - MA alignment
        - Higher highs / lower lows count
        """
        if len(closes) < 20:
            return 0.5
        
        # 1. Linear regression slope
        slope_score = self._compute_slope_score(closes)
        
        # 2. MA alignment score
        ma_short = sum(closes[-20:]) / 20
        ma_long = sum(closes[-50:]) / 50 if len(closes) >= 50 else sum(closes) / len(closes)
        
        ma_diff = (ma_short - ma_long) / ma_long if ma_long > 0 else 0
        ma_score = min(abs(ma_diff) * 10, 1.0)  # Normalize
        
        # 3. Structure score (HH/HL or LH/LL)
        structure_score = self._compute_trend_structure(highs, lows)
        
        # Combine
        trend_strength = slope_score * 0.4 + ma_score * 0.3 + structure_score * 0.3
        
        return min(max(trend_strength, 0), 1)
    
    def _compute_slope_score(self, closes: List[float]) -> float:
        """Compute normalized slope score"""
        n = min(len(closes), self.config.slope_period)
        if n < 5:
            return 0.5
        
        recent = closes[-n:]
        
        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        
        numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.5
        
        slope = numerator / denominator
        
        # Normalize by price level
        normalized_slope = slope / y_mean if y_mean > 0 else 0
        
        # Map to 0-1 (assuming +/- 2% per bar is extreme)
        score = min(abs(normalized_slope) * 50, 1.0)
        
        return score
    
    def _compute_trend_structure(self, highs: List[float], lows: List[float]) -> float:
        """Analyze HH/HL or LH/LL structure"""
        if len(highs) < 10:
            return 0.5
        
        recent_highs = highs[-10:]
        recent_lows = lows[-10:]
        
        # Count higher highs and higher lows
        hh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1])
        hl_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] > recent_lows[i-1])
        
        # Count lower highs and lower lows
        lh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] < recent_highs[i-1])
        ll_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] < recent_lows[i-1])
        
        total = len(recent_highs) - 1
        
        # Uptrend structure
        uptrend_score = (hh_count + hl_count) / (total * 2)
        
        # Downtrend structure
        downtrend_score = (lh_count + ll_count) / (total * 2)
        
        # Return max of either (indicates clear trend)
        return max(uptrend_score, downtrend_score)
    
    def _compute_volatility(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> Tuple[float, float, float]:
        """
        Compute volatility level (0-1) and ATR values.
        """
        if len(closes) < self.config.atr_period:
            return 0.5, 0, 0
        
        # Calculate ATR
        tr_values = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)
        
        if len(tr_values) < self.config.atr_period:
            return 0.5, 0, 0
        
        # Current ATR
        atr = sum(tr_values[-self.config.atr_period:]) / self.config.atr_period
        
        # ATR SMA (historical average)
        atr_history = []
        for i in range(self.config.atr_period, len(tr_values)):
            period_atr = sum(tr_values[i-self.config.atr_period:i]) / self.config.atr_period
            atr_history.append(period_atr)
        
        if not atr_history:
            atr_sma = atr
        else:
            atr_sma = sum(atr_history[-self.config.atr_sma_period:]) / min(len(atr_history), self.config.atr_sma_period)
        
        # Normalize ATR ratio to 0-1
        # Ratio of 1.0 = normal, 2.0+ = high vol, 0.5 = low vol
        atr_ratio = atr / atr_sma if atr_sma > 0 else 1.0
        
        # Map to 0-1 score
        if atr_ratio >= 2.0:
            vol_level = 1.0
        elif atr_ratio <= 0.5:
            vol_level = 0.0
        else:
            # Linear interpolation
            vol_level = (atr_ratio - 0.5) / 1.5
        
        return vol_level, atr, atr_sma
    
    def _compute_compression(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> float:
        """
        Compute range compression (0-1).
        
        High compression = tight range = low volatility compression
        """
        if len(closes) < 20:
            return 0.5
        
        # Current range (last 5 bars)
        recent_range = max(highs[-5:]) - min(lows[-5:])
        
        # Historical range (last 20 bars)
        hist_range = max(highs[-20:]) - min(lows[-20:])
        
        if hist_range == 0:
            return 0.5
        
        # Compression ratio
        compression_ratio = 1 - (recent_range / hist_range)
        
        # Additional: Bollinger Band width comparison
        if len(closes) >= 20:
            sma = sum(closes[-20:]) / 20
            std = math.sqrt(sum((c - sma) ** 2 for c in closes[-20:]) / 20)
            bb_width = (std * 2) / sma if sma > 0 else 0
            
            # Narrow BB = compression
            bb_compression = max(0, 1 - bb_width * 10)  # Normalize
            
            compression = compression_ratio * 0.6 + bb_compression * 0.4
        else:
            compression = compression_ratio
        
        return min(max(compression, 0), 1)
    
    def _compute_structure_clarity(self, highs: List[float], lows: List[float]) -> float:
        """
        Compute structure clarity (0-1).
        
        Clear structure = consistent swing highs/lows pattern.
        """
        if len(highs) < 10:
            return 0.5
        
        # Find swing points
        swings = self._find_swing_points(highs, lows)
        
        if len(swings) < 4:
            return 0.3  # Not enough swings = unclear
        
        # Analyze swing consistency
        swing_highs = [s for s in swings if s['type'] == 'high']
        swing_lows = [s for s in swings if s['type'] == 'low']
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return 0.4
        
        # Check if swings form clear pattern
        # Higher highs + higher lows = uptrend (clear)
        # Lower highs + lower lows = downtrend (clear)
        # Mixed = unclear
        
        hh_count = sum(1 for i in range(1, len(swing_highs)) 
                       if swing_highs[i]['price'] > swing_highs[i-1]['price'])
        lh_count = len(swing_highs) - 1 - hh_count
        
        hl_count = sum(1 for i in range(1, len(swing_lows)) 
                       if swing_lows[i]['price'] > swing_lows[i-1]['price'])
        ll_count = len(swing_lows) - 1 - hl_count
        
        # Calculate clarity score
        if len(swing_highs) > 1 and len(swing_lows) > 1:
            up_clarity = (hh_count / (len(swing_highs) - 1) + hl_count / (len(swing_lows) - 1)) / 2
            down_clarity = (lh_count / (len(swing_highs) - 1) + ll_count / (len(swing_lows) - 1)) / 2
            
            clarity = max(up_clarity, down_clarity)
        else:
            clarity = 0.4
        
        return min(max(clarity, 0), 1)
    
    def _find_swing_points(
        self,
        highs: List[float],
        lows: List[float],
        lookback: int = 3
    ) -> List[Dict]:
        """Find swing highs and lows"""
        swings = []
        
        for i in range(lookback, len(highs) - lookback):
            # Swing high
            is_swing_high = all(highs[i] > highs[i-j] for j in range(1, lookback+1))
            is_swing_high = is_swing_high and all(highs[i] > highs[i+j] for j in range(1, lookback+1))
            
            if is_swing_high:
                swings.append({'type': 'high', 'index': i, 'price': highs[i]})
            
            # Swing low
            is_swing_low = all(lows[i] < lows[i-j] for j in range(1, lookback+1))
            is_swing_low = is_swing_low and all(lows[i] < lows[i+j] for j in range(1, lookback+1))
            
            if is_swing_low:
                swings.append({'type': 'low', 'index': i, 'price': lows[i]})
        
        return sorted(swings, key=lambda x: x['index'])
    
    def _compute_breakout_pressure(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        compression: float,
        volatility: float
    ) -> float:
        """
        Compute breakout pressure (0-1).
        
        High when compression + momentum building.
        """
        if len(closes) < 10:
            return 0.5
        
        # Factor 1: Compression (higher = more pressure)
        compression_factor = compression
        
        # Factor 2: Price near range boundary
        recent_range = max(highs[-20:]) - min(lows[-20:]) if len(highs) >= 20 else 0
        range_high = max(highs[-20:]) if len(highs) >= 20 else highs[-1]
        range_low = min(lows[-20:]) if len(lows) >= 20 else lows[-1]
        current_price = closes[-1]
        
        if recent_range > 0:
            position_in_range = (current_price - range_low) / recent_range
            # Pressure high when near boundaries (0 or 1)
            boundary_pressure = 1 - 2 * abs(position_in_range - 0.5)
        else:
            boundary_pressure = 0.5
        
        # Factor 3: Volume building (if volume data available)
        # Simplified: assume moderate
        volume_factor = 0.5
        
        # Factor 4: Decreasing volatility (squeeze)
        if volatility < 0.3:
            squeeze_factor = 0.8
        elif volatility < 0.5:
            squeeze_factor = 0.5
        else:
            squeeze_factor = 0.2
        
        # Combine factors
        pressure = (
            compression_factor * 0.35 +
            boundary_pressure * 0.25 +
            squeeze_factor * 0.25 +
            volume_factor * 0.15
        )
        
        return min(max(pressure, 0), 1)
    
    def _compute_directional_consistency(self, closes: List[float]) -> float:
        """Compute how consistent the price direction is"""
        if len(closes) < 10:
            return 0.5
        
        recent = closes[-10:]
        
        up_bars = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
        down_bars = len(recent) - 1 - up_bars
        
        # Consistency = dominant direction percentage
        consistency = max(up_bars, down_bars) / (len(recent) - 1)
        
        return consistency
    
    def _compute_ma_separation(self, closes: List[float]) -> float:
        """Compute MA separation (normalized)"""
        if len(closes) < 50:
            return 0.5
        
        ma_short = sum(closes[-20:]) / 20
        ma_long = sum(closes[-50:]) / 50
        
        separation = abs(ma_short - ma_long) / ma_long if ma_long > 0 else 0
        
        # Normalize (5% separation = 1.0)
        normalized = min(separation / 0.05, 1.0)
        
        return normalized
    
    def _compute_volume_trend(self, volumes: List[float]) -> float:
        """Compute volume trend (increasing/decreasing)"""
        if len(volumes) < 10 or all(v == 0 for v in volumes):
            return 0.5
        
        recent = volumes[-5:]
        older = volumes[-10:-5]
        
        if sum(older) == 0:
            return 0.5
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        if older_avg == 0:
            return 0.5
        
        ratio = recent_avg / older_avg
        
        # Map to 0-1 (0.5 = neutral, 1.0 = increasing, 0.0 = decreasing)
        if ratio > 1.5:
            return 1.0
        elif ratio < 0.5:
            return 0.0
        else:
            return ratio / 2
    
    def _compute_body_ratio(self, candles: List[Candle]) -> float:
        """Compute average body to range ratio"""
        if len(candles) < 5:
            return 0.5
        
        ratios = []
        for c in candles[-5:]:
            range_size = c.high - c.low
            if range_size > 0:
                body = abs(c.close - c.open)
                ratios.append(body / range_size)
        
        if not ratios:
            return 0.5
        
        return sum(ratios) / len(ratios)


# Global calculator instance
feature_calculator = RegimeFeatureCalculator()
