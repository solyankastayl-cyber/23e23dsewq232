"""
Metrics Normalizer (S2.3)
=========================

Normalizes metrics for comparison.

Positive metrics (higher is better):
- sharpe_ratio, sortino_ratio, profit_factor, annual_return
- expectancy, calmar_ratio, recovery_factor, win_rate

Negative metrics (lower is better):
- max_drawdown_pct, volatility_annual

Normalization: min-max scaling to 0-1 range.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


# Metrics classification
POSITIVE_METRICS = {
    "sharpe_ratio",
    "sortino_ratio",
    "profit_factor",
    "expectancy",
    "total_return_pct",
    "annual_return_pct",
    "calmar_ratio",
    "recovery_factor",
    "win_rate"
}

NEGATIVE_METRICS = {
    "max_drawdown_pct",
    "volatility_annual"
}

# All metrics used for comparison
ALL_METRICS = POSITIVE_METRICS | NEGATIVE_METRICS


@dataclass
class MetricRange:
    """Min-max range for a metric"""
    metric: str
    min_value: float
    max_value: float
    is_positive: bool


class MetricsNormalizer:
    """
    Normalizes metrics for fair comparison.
    """
    
    def __init__(self):
        self._ranges: Dict[str, MetricRange] = {}
    
    def compute_ranges(
        self,
        metrics_list: List[Dict[str, float]]
    ) -> Dict[str, MetricRange]:
        """
        Compute min-max ranges for each metric.
        
        Args:
            metrics_list: List of raw metrics dicts
            
        Returns:
            Dict of metric -> MetricRange
        """
        if not metrics_list:
            return {}
        
        ranges = {}
        
        for metric in ALL_METRICS:
            values = [
                m.get(metric, 0)
                for m in metrics_list
                if metric in m
            ]
            
            if values:
                ranges[metric] = MetricRange(
                    metric=metric,
                    min_value=min(values),
                    max_value=max(values),
                    is_positive=metric in POSITIVE_METRICS
                )
        
        self._ranges = ranges
        return ranges
    
    def normalize_metric(
        self,
        metric: str,
        value: float,
        range_info: MetricRange = None
    ) -> float:
        """
        Normalize a single metric value to 0-1 scale.
        
        For positive metrics: (value - min) / (max - min)
        For negative metrics: (max - value) / (max - min)
        
        Args:
            metric: Metric name
            value: Raw value
            range_info: Optional MetricRange (uses stored if not provided)
            
        Returns:
            Normalized value (0-1)
        """
        if range_info is None:
            range_info = self._ranges.get(metric)
        
        if range_info is None:
            return 0.5  # Default middle value if no range
        
        min_val = range_info.min_value
        max_val = range_info.max_value
        
        # Handle edge cases
        if max_val == min_val:
            return 0.5 if value == min_val else (1.0 if value > min_val else 0.0)
        
        # Normalize based on metric type
        if range_info.is_positive:
            # Higher is better
            normalized = (value - min_val) / (max_val - min_val)
        else:
            # Lower is better (invert)
            normalized = (max_val - value) / (max_val - min_val)
        
        # Clamp to 0-1
        return max(0.0, min(1.0, normalized))
    
    def normalize_all(
        self,
        raw_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Normalize all metrics in a dict.
        
        Args:
            raw_metrics: Dict of metric -> raw value
            
        Returns:
            Dict of metric -> normalized value
        """
        normalized = {}
        
        for metric, value in raw_metrics.items():
            if metric in ALL_METRICS:
                normalized[metric] = self.normalize_metric(metric, value)
        
        return normalized
    
    def batch_normalize(
        self,
        metrics_list: List[Dict[str, float]]
    ) -> List[Dict[str, float]]:
        """
        Normalize a batch of metrics.
        
        Computes ranges from batch first, then normalizes all.
        
        Args:
            metrics_list: List of raw metrics dicts
            
        Returns:
            List of normalized metrics dicts
        """
        # Compute ranges from batch
        self.compute_ranges(metrics_list)
        
        # Normalize each
        return [self.normalize_all(m) for m in metrics_list]


# Convenience function
def normalize_metrics(
    metrics_list: List[Dict[str, float]]
) -> Tuple[List[Dict[str, float]], Dict[str, MetricRange]]:
    """
    Convenience function to normalize a batch of metrics.
    
    Returns:
        Tuple of (normalized_list, ranges)
    """
    normalizer = MetricsNormalizer()
    ranges = normalizer.compute_ranges(metrics_list)
    normalized = [normalizer.normalize_all(m) for m in metrics_list]
    return normalized, ranges
