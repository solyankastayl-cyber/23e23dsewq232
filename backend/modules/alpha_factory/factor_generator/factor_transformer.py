"""
PHASE 13.3 - Factor Transformer
================================
Transforms for factor computation.

Supported transforms:
- zscore
- rank
- percentile
- lag
- rolling_mean
- rolling_std
- binary_threshold
- weighted_sum
- ratio
- difference
- product
- conditional
- regime_mask
"""

from typing import Dict, List, Optional, Any
import math


class FactorTransformer:
    """
    Transforms for factor computation.
    """
    
    @staticmethod
    def weighted_sum(values_list: List[List[float]], weights: List[float] = None) -> List[float]:
        """
        Weighted sum of multiple feature series.
        """
        if not values_list:
            return []
        
        n_features = len(values_list)
        n_points = len(values_list[0])
        
        if weights is None:
            weights = [1.0 / n_features] * n_features
        
        result = []
        for i in range(n_points):
            total = sum(values_list[j][i] * weights[j] for j in range(n_features))
            result.append(total)
        
        return result
    
    @staticmethod
    def ratio(numerator: List[float], denominator: List[float], epsilon: float = 1e-8) -> List[float]:
        """
        Compute ratio of two series.
        """
        result = []
        for n, d in zip(numerator, denominator):
            if abs(d) < epsilon:
                result.append(0.0)
            else:
                result.append(n / d)
        return result
    
    @staticmethod
    def difference(values1: List[float], values2: List[float]) -> List[float]:
        """
        Compute difference of two series.
        """
        return [v1 - v2 for v1, v2 in zip(values1, values2)]
    
    @staticmethod
    def product(values1: List[float], values2: List[float]) -> List[float]:
        """
        Compute product of two series.
        """
        return [v1 * v2 for v1, v2 in zip(values1, values2)]
    
    @staticmethod
    def conditional(signal: List[float], condition: List[float], threshold: float = 0.5) -> List[float]:
        """
        Apply signal only when condition exceeds threshold.
        """
        return [s if c > threshold else 0.0 for s, c in zip(signal, condition)]
    
    @staticmethod
    def regime_mask(values: List[float], regime_series: List[str], target_regime: str) -> List[float]:
        """
        Apply values only in target regime.
        """
        return [v if r == target_regime else 0.0 for v, r in zip(values, regime_series)]
    
    @staticmethod
    def zscore(values: List[float], window: int = 20) -> List[float]:
        """
        Rolling Z-score.
        """
        result = []
        for i in range(len(values)):
            if i < window - 1:
                window_vals = values[:i+1]
            else:
                window_vals = values[i-window+1:i+1]
            
            mean = sum(window_vals) / len(window_vals)
            variance = sum((x - mean) ** 2 for x in window_vals) / len(window_vals)
            std = math.sqrt(variance) if variance > 0 else 1.0
            
            result.append((values[i] - mean) / std if std > 0 else 0.0)
        
        return result
    
    @staticmethod
    def rank(values: List[float]) -> List[float]:
        """
        Cross-sectional rank (0-1).
        """
        if not values:
            return []
        
        sorted_indices = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for rank, idx in enumerate(sorted_indices):
            ranks[idx] = rank / (len(values) - 1) if len(values) > 1 else 0.5
        return ranks
    
    @staticmethod
    def percentile(values: List[float], window: int = 100) -> List[float]:
        """
        Rolling percentile rank.
        """
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
    def rolling_mean(values: List[float], window: int = 20) -> List[float]:
        """
        Rolling mean.
        """
        result = []
        for i in range(len(values)):
            if i < window - 1:
                result.append(sum(values[:i+1]) / (i + 1))
            else:
                result.append(sum(values[i-window+1:i+1]) / window)
        return result
    
    @staticmethod
    def rolling_std(values: List[float], window: int = 20) -> List[float]:
        """
        Rolling standard deviation.
        """
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
    def binary_threshold(values: List[float], threshold: float = 0.5) -> List[int]:
        """
        Binary threshold.
        """
        return [1 if v > threshold else 0 for v in values]
    
    @staticmethod
    def lag(values: List[float], periods: int = 1) -> List[float]:
        """
        Lag values by n periods.
        """
        if len(values) <= periods:
            return [0.0] * len(values)
        return [0.0] * periods + values[:-periods]
    
    @staticmethod
    def clip(values: List[float], lower: float = -3.0, upper: float = 3.0) -> List[float]:
        """
        Clip values to range.
        """
        return [max(lower, min(upper, v)) for v in values]
    
    @classmethod
    def apply_transforms(
        cls,
        values: List[float],
        transforms: List[str],
        params: Dict = None
    ) -> List[float]:
        """
        Apply sequence of transforms to values.
        """
        params = params or {}
        result = values.copy()
        
        for transform in transforms:
            if transform == "zscore":
                result = cls.zscore(result, params.get("window", 20))
            elif transform == "rank":
                result = cls.rank(result)
            elif transform == "percentile":
                result = cls.percentile(result, params.get("window", 100))
            elif transform == "rolling_mean":
                result = cls.rolling_mean(result, params.get("window", 20))
            elif transform == "rolling_std":
                result = cls.rolling_std(result, params.get("window", 20))
            elif transform == "binary_threshold":
                result = [float(x) for x in cls.binary_threshold(result, params.get("threshold", 0.5))]
            elif transform == "lag":
                result = cls.lag(result, params.get("periods", 1))
            elif transform == "clip":
                result = cls.clip(result, params.get("lower", -3), params.get("upper", 3))
        
        return result
    
    @classmethod
    def get_available_transforms(cls) -> List[str]:
        """Get list of available transforms."""
        return [
            "weighted_sum", "ratio", "difference", "product",
            "conditional", "regime_mask",
            "zscore", "rank", "percentile",
            "rolling_mean", "rolling_std",
            "binary_threshold", "lag", "clip"
        ]
