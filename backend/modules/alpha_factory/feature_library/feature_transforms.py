"""
PHASE 13.2 - Feature Transforms
================================
Feature transformation layer for Alpha Factory.

Provides transforms:
- lag
- rolling_mean
- rolling_std
- zscore
- percentile_rank
- minmax_scale
- log_transform
- difference
- ratio
- binary_threshold
- clip
- rank
- ema
- sma
"""

from typing import List, Dict, Optional, Union, Any
import math

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False


class FeatureTransformer:
    """
    Feature transformation engine.
    
    Provides stateless transformations for feature computation.
    """
    
    @staticmethod
    def lag(values: List[float], periods: int = 1) -> List[float]:
        """Lag values by n periods."""
        if len(values) <= periods:
            return [0.0] * len(values)
        return [0.0] * periods + values[:-periods]
    
    @staticmethod
    def difference(values: List[float], periods: int = 1) -> List[float]:
        """Calculate difference over n periods."""
        if len(values) <= periods:
            return [0.0] * len(values)
        result = [0.0] * periods
        for i in range(periods, len(values)):
            result.append(values[i] - values[i - periods])
        return result
    
    @staticmethod
    def pct_change(values: List[float], periods: int = 1) -> List[float]:
        """Calculate percentage change over n periods."""
        if len(values) <= periods:
            return [0.0] * len(values)
        result = [0.0] * periods
        for i in range(periods, len(values)):
            if values[i - periods] != 0:
                result.append((values[i] - values[i - periods]) / values[i - periods])
            else:
                result.append(0.0)
        return result
    
    @staticmethod
    def rolling_mean(values: List[float], window: int = 20) -> List[float]:
        """Calculate rolling mean."""
        result = []
        for i in range(len(values)):
            if i < window - 1:
                result.append(sum(values[:i+1]) / (i + 1))
            else:
                result.append(sum(values[i-window+1:i+1]) / window)
        return result
    
    @staticmethod
    def rolling_std(values: List[float], window: int = 20) -> List[float]:
        """Calculate rolling standard deviation."""
        result = []
        for i in range(len(values)):
            if i < window - 1:
                window_vals = values[:i+1]
            else:
                window_vals = values[i-window+1:i+1]
            
            if len(window_vals) < 2:
                result.append(0.0)
            else:
                mean = sum(window_vals) / len(window_vals)
                variance = sum((x - mean) ** 2 for x in window_vals) / len(window_vals)
                result.append(math.sqrt(variance))
        return result
    
    @staticmethod
    def zscore(values: List[float], window: int = 20) -> List[float]:
        """Calculate rolling Z-score."""
        means = FeatureTransformer.rolling_mean(values, window)
        stds = FeatureTransformer.rolling_std(values, window)
        
        result = []
        for i in range(len(values)):
            if stds[i] == 0:
                result.append(0.0)
            else:
                result.append((values[i] - means[i]) / stds[i])
        return result
    
    @staticmethod
    def percentile_rank(values: List[float], window: int = 100) -> List[float]:
        """Calculate rolling percentile rank (0-1)."""
        result = []
        for i in range(len(values)):
            if i < 1:
                result.append(0.5)
            else:
                start = max(0, i - window + 1)
                window_vals = values[start:i+1]
                count_below = sum(1 for v in window_vals if v < values[i])
                result.append(count_below / len(window_vals))
        return result
    
    @staticmethod
    def minmax_scale(values: List[float], window: int = 20) -> List[float]:
        """Min-max scaling within window."""
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            window_vals = values[start:i+1]
            min_val = min(window_vals)
            max_val = max(window_vals)
            
            if max_val == min_val:
                result.append(0.5)
            else:
                result.append((values[i] - min_val) / (max_val - min_val))
        return result
    
    @staticmethod
    def log_transform(values: List[float]) -> List[float]:
        """Natural log transform (for positive values)."""
        result = []
        for v in values:
            if v > 0:
                result.append(math.log(v))
            else:
                result.append(0.0)
        return result
    
    @staticmethod
    def ratio(values1: List[float], values2: List[float]) -> List[float]:
        """Calculate ratio of two series."""
        result = []
        for v1, v2 in zip(values1, values2):
            if v2 != 0:
                result.append(v1 / v2)
            else:
                result.append(0.0)
        return result
    
    @staticmethod
    def binary_threshold(values: List[float], threshold: float = 0.5) -> List[int]:
        """Binary threshold transform."""
        return [1 if v > threshold else 0 for v in values]
    
    @staticmethod
    def clip(values: List[float], lower: float = -3.0, upper: float = 3.0) -> List[float]:
        """Clip values to range."""
        return [max(lower, min(upper, v)) for v in values]
    
    @staticmethod
    def rank(values: List[float]) -> List[float]:
        """Cross-sectional rank (0-1)."""
        if not values:
            return []
        
        sorted_indices = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for rank, idx in enumerate(sorted_indices):
            ranks[idx] = rank / (len(values) - 1) if len(values) > 1 else 0.5
        return ranks
    
    @staticmethod
    def ema(values: List[float], period: int = 20) -> List[float]:
        """Exponential moving average."""
        if not values:
            return []
        
        alpha = 2.0 / (period + 1)
        result = [values[0]]
        
        for i in range(1, len(values)):
            ema_val = alpha * values[i] + (1 - alpha) * result[-1]
            result.append(ema_val)
        
        return result
    
    @staticmethod
    def sma(values: List[float], period: int = 20) -> List[float]:
        """Simple moving average."""
        return FeatureTransformer.rolling_mean(values, period)
    
    @staticmethod
    def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
        """Average True Range."""
        if len(high) < 2:
            return [0.0] * len(high)
        
        true_ranges = [high[0] - low[0]]
        
        for i in range(1, len(high)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            true_ranges.append(tr)
        
        return FeatureTransformer.ema(true_ranges, period)
    
    @staticmethod
    def rsi(values: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index."""
        if len(values) < 2:
            return [50.0] * len(values)
        
        gains = [0.0]
        losses = [0.0]
        
        for i in range(1, len(values)):
            change = values[i] - values[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))
        
        avg_gain = FeatureTransformer.ema(gains, period)
        avg_loss = FeatureTransformer.ema(losses, period)
        
        result = []
        for g, l in zip(avg_gain, avg_loss):
            if l == 0:
                result.append(100.0 if g > 0 else 50.0)
            else:
                rs = g / l
                result.append(100.0 - (100.0 / (1.0 + rs)))
        
        return result
    
    @staticmethod
    def bollinger_bandwidth(values: List[float], period: int = 20, std_mult: float = 2.0) -> List[float]:
        """Bollinger Bandwidth."""
        sma = FeatureTransformer.rolling_mean(values, period)
        std = FeatureTransformer.rolling_std(values, period)
        
        result = []
        for m, s in zip(sma, std):
            if m == 0:
                result.append(0.0)
            else:
                bandwidth = (2 * std_mult * s) / m
                result.append(bandwidth)
        
        return result
    
    @classmethod
    def apply_transform(
        cls,
        transform_name: str,
        values: List[float],
        params: Dict = None,
        secondary_values: List[float] = None
    ) -> List[float]:
        """
        Apply named transform to values.
        
        Args:
            transform_name: Name of transform to apply
            values: Primary input values
            params: Transform parameters
            secondary_values: Secondary values for ratio, etc.
        
        Returns:
            Transformed values
        """
        params = params or {}
        
        transforms = {
            "raw": lambda v, p: v,
            "lag": lambda v, p: cls.lag(v, p.get("periods", 1)),
            "difference": lambda v, p: cls.difference(v, p.get("periods", 1)),
            "pct_change": lambda v, p: cls.pct_change(v, p.get("periods", 1)),
            "rolling_mean": lambda v, p: cls.rolling_mean(v, p.get("window", 20)),
            "rolling_std": lambda v, p: cls.rolling_std(v, p.get("window", 20)),
            "zscore": lambda v, p: cls.zscore(v, p.get("window", 20)),
            "percentile_rank": lambda v, p: cls.percentile_rank(v, p.get("window", 100)),
            "minmax_scale": lambda v, p: cls.minmax_scale(v, p.get("window", 20)),
            "log_transform": lambda v, p: cls.log_transform(v),
            "binary_threshold": lambda v, p: cls.binary_threshold(v, p.get("threshold", 0.5)),
            "clip": lambda v, p: cls.clip(v, p.get("lower", -3), p.get("upper", 3)),
            "rank": lambda v, p: cls.rank(v),
            "ema": lambda v, p: cls.ema(v, p.get("period", 20)),
            "sma": lambda v, p: cls.sma(v, p.get("period", 20)),
        }
        
        if transform_name == "ratio" and secondary_values:
            return cls.ratio(values, secondary_values)
        
        transform_func = transforms.get(transform_name.lower())
        if transform_func:
            return transform_func(values, params)
        
        # Unknown transform, return raw
        return values
    
    @classmethod
    def get_available_transforms(cls) -> List[str]:
        """Get list of available transforms."""
        return [
            "raw", "lag", "difference", "pct_change", 
            "rolling_mean", "rolling_std", "zscore", "percentile_rank",
            "minmax_scale", "log_transform", "ratio", 
            "binary_threshold", "clip", "rank", "ema", "sma"
        ]
