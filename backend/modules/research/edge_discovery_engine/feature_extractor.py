"""
PHASE 6.4 - Feature Extractor
==============================
Extracts market features from price/volume data.
"""

import random
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .edge_types import MarketFeatures


class FeatureExtractor:
    """
    Extracts market features from OHLCV and orderbook data.
    """
    
    def __init__(self):
        self.lookback_period = 20
    
    def extract_features(
        self,
        candles: List[Dict],
        index: int,
        orderbook: Optional[Dict] = None
    ) -> MarketFeatures:
        """
        Extract features at a specific candle index.
        """
        if index < self.lookback_period:
            return MarketFeatures(timestamp=candles[index].get('timestamp', 0))
        
        current = candles[index]
        lookback = candles[max(0, index - self.lookback_period):index]
        
        # Calculate features
        trend_strength, trend_direction = self._calculate_trend(lookback, current)
        volatility_pct = self._calculate_volatility_percentile(lookback)
        momentum = self._calculate_momentum(lookback, current)
        volume_spike = self._calculate_volume_spike(lookback, current)
        volume_trend = self._calculate_volume_trend(lookback)
        
        # Structure features
        near_support, near_resistance = self._check_structure_levels(lookback, current)
        structure_type = self._determine_structure_type(lookback)
        
        # Simulated derivatives features (in production, from exchange API)
        funding_zscore = random.gauss(0, 1)
        oi_change = random.uniform(-10, 10)
        
        # Simulated liquidity features (in production, from orderbook)
        liquidity_score = random.uniform(0.3, 0.9)
        spread_pct = random.uniform(0.2, 0.8)
        ob_imbalance = random.uniform(-0.5, 0.5)
        
        return MarketFeatures(
            timestamp=current.get('timestamp', 0),
            trend_strength=trend_strength,
            trend_direction=trend_direction,
            volatility_percentile=volatility_pct,
            price_momentum=momentum,
            volume_spike=volume_spike,
            volume_trend=volume_trend,
            liquidity_score=liquidity_score,
            spread_percentile=spread_pct,
            orderbook_imbalance=ob_imbalance,
            funding_rate_zscore=funding_zscore,
            oi_change_pct=oi_change,
            near_support=near_support,
            near_resistance=near_resistance,
            structure_type=structure_type
        )
    
    def extract_features_batch(
        self,
        candles: List[Dict],
        start_index: int = None,
        end_index: int = None
    ) -> List[MarketFeatures]:
        """
        Extract features for a range of candles.
        """
        if start_index is None:
            start_index = self.lookback_period
        if end_index is None:
            end_index = len(candles)
        
        features_list = []
        for i in range(start_index, end_index):
            features = self.extract_features(candles, i)
            features_list.append(features)
        
        return features_list
    
    def _calculate_trend(
        self,
        lookback: List[Dict],
        current: Dict
    ) -> Tuple[float, str]:
        """Calculate trend strength and direction"""
        if len(lookback) < 2:
            return 0.0, "NEUTRAL"
        
        closes = [c['close'] for c in lookback]
        
        # Simple linear regression slope
        n = len(closes)
        x_mean = (n - 1) / 2
        y_mean = sum(closes) / n
        
        numerator = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0, "NEUTRAL"
        
        slope = numerator / denominator
        
        # Normalize slope to -1 to 1
        avg_price = y_mean
        normalized_slope = slope / avg_price * 100  # % change per candle
        
        trend_strength = min(1.0, abs(normalized_slope) * 10)  # Cap at 1
        
        if normalized_slope > 0.01:
            direction = "UP"
        elif normalized_slope < -0.01:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"
        
        return trend_strength, direction
    
    def _calculate_volatility_percentile(self, lookback: List[Dict]) -> float:
        """Calculate current volatility as percentile of recent history"""
        if len(lookback) < 5:
            return 0.5
        
        # Calculate ATR for each candle
        atrs = []
        for i in range(1, len(lookback)):
            high = lookback[i]['high']
            low = lookback[i]['low']
            prev_close = lookback[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            atrs.append(tr)
        
        if not atrs:
            return 0.5
        
        current_atr = atrs[-1]
        sorted_atrs = sorted(atrs)
        
        # Find percentile
        rank = sorted_atrs.index(current_atr) if current_atr in sorted_atrs else len(sorted_atrs) // 2
        percentile = rank / len(sorted_atrs)
        
        return percentile
    
    def _calculate_momentum(self, lookback: List[Dict], current: Dict) -> float:
        """Calculate price momentum"""
        if len(lookback) < 5:
            return 0.0
        
        # ROC (Rate of Change)
        old_close = lookback[-5]['close']
        current_close = current['close']
        
        if old_close == 0:
            return 0.0
        
        roc = (current_close - old_close) / old_close
        
        return roc
    
    def _calculate_volume_spike(self, lookback: List[Dict], current: Dict) -> float:
        """Calculate volume relative to average"""
        if len(lookback) < 5:
            return 1.0
        
        volumes = [c.get('volume', 1) for c in lookback]
        avg_volume = sum(volumes) / len(volumes) if volumes else 1
        current_volume = current.get('volume', 1)
        
        if avg_volume == 0:
            return 1.0
        
        spike = current_volume / avg_volume
        return spike
    
    def _calculate_volume_trend(self, lookback: List[Dict]) -> float:
        """Calculate volume trend (increasing/decreasing)"""
        if len(lookback) < 10:
            return 0.0
        
        volumes = [c.get('volume', 1) for c in lookback]
        
        first_half_avg = sum(volumes[:len(volumes)//2]) / (len(volumes)//2)
        second_half_avg = sum(volumes[len(volumes)//2:]) / (len(volumes) - len(volumes)//2)
        
        if first_half_avg == 0:
            return 0.0
        
        trend = (second_half_avg - first_half_avg) / first_half_avg
        return trend
    
    def _check_structure_levels(
        self,
        lookback: List[Dict],
        current: Dict
    ) -> Tuple[bool, bool]:
        """Check if price is near support or resistance"""
        if len(lookback) < 10:
            return False, False
        
        highs = [c['high'] for c in lookback]
        lows = [c['low'] for c in lookback]
        
        resistance = max(highs)
        support = min(lows)
        current_close = current['close']
        
        price_range = resistance - support
        if price_range == 0:
            return False, False
        
        threshold = 0.02  # 2% of range
        
        near_support = (current_close - support) / price_range < threshold
        near_resistance = (resistance - current_close) / price_range < threshold
        
        return near_support, near_resistance
    
    def _determine_structure_type(self, lookback: List[Dict]) -> str:
        """Determine market structure type"""
        if len(lookback) < 10:
            return "UNKNOWN"
        
        closes = [c['close'] for c in lookback]
        
        # Calculate higher highs/lower lows
        highs = [c['high'] for c in lookback]
        lows = [c['low'] for c in lookback]
        
        recent_high = max(highs[-5:])
        older_high = max(highs[:-5])
        recent_low = min(lows[-5:])
        older_low = min(lows[:-5])
        
        if recent_high > older_high and recent_low > older_low:
            return "UPTREND"
        elif recent_high < older_high and recent_low < older_low:
            return "DOWNTREND"
        else:
            return "RANGE"
