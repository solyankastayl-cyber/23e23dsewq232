"""
PHASE 7 - Correlation Matrix Engine
=====================================
Calculates correlation matrices for multiple asset pairs.
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import statistics

from .correlation_types import (
    AssetPair, CorrelationValue, CorrelationMethod, CorrelationStrength,
    DEFAULT_PAIRS
)


class CorrelationMatrixEngine:
    """
    Calculates correlation matrices for asset pairs.
    """
    
    def __init__(self):
        self.default_window = 30  # 30 candles
    
    def calculate_correlation(
        self,
        returns_a: List[float],
        returns_b: List[float],
        method: CorrelationMethod = CorrelationMethod.PEARSON
    ) -> Tuple[float, float]:
        """
        Calculate correlation between two return series.
        
        Returns: (correlation, p_value)
        """
        if len(returns_a) != len(returns_b) or len(returns_a) < 3:
            return 0.0, 1.0
        
        if method == CorrelationMethod.PEARSON:
            corr = self._pearson_correlation(returns_a, returns_b)
        elif method == CorrelationMethod.SPEARMAN:
            corr = self._spearman_correlation(returns_a, returns_b)
        elif method == CorrelationMethod.KENDALL:
            corr = self._kendall_correlation(returns_a, returns_b)
        else:
            corr = self._pearson_correlation(returns_a, returns_b)
        
        # Approximate p-value (simplified)
        n = len(returns_a)
        if abs(corr) < 1:
            t_stat = corr * math.sqrt(n - 2) / math.sqrt(1 - corr**2)
            # Simplified p-value approximation
            p_value = 2 * (1 - min(0.9999, abs(t_stat) / (abs(t_stat) + 1)))
        else:
            p_value = 0.0
        
        return corr, p_value
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        n = len(x)
        if n == 0:
            return 0.0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _spearman_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Spearman rank correlation"""
        n = len(x)
        if n == 0:
            return 0.0
        
        # Rank the values
        rank_x = self._rank_data(x)
        rank_y = self._rank_data(y)
        
        # Calculate Pearson on ranks
        return self._pearson_correlation(rank_x, rank_y)
    
    def _kendall_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Kendall tau correlation"""
        n = len(x)
        if n < 2:
            return 0.0
        
        concordant = 0
        discordant = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                x_diff = x[i] - x[j]
                y_diff = y[i] - y[j]
                
                product = x_diff * y_diff
                
                if product > 0:
                    concordant += 1
                elif product < 0:
                    discordant += 1
        
        total_pairs = n * (n - 1) / 2
        
        if total_pairs == 0:
            return 0.0
        
        return (concordant - discordant) / total_pairs
    
    def _rank_data(self, data: List[float]) -> List[float]:
        """Rank data for Spearman correlation"""
        n = len(data)
        sorted_indices = sorted(range(n), key=lambda i: data[i])
        ranks = [0.0] * n
        
        for rank, idx in enumerate(sorted_indices):
            ranks[idx] = float(rank + 1)
        
        return ranks
    
    def classify_strength(self, correlation: float) -> CorrelationStrength:
        """Classify correlation strength"""
        if correlation >= 0.7:
            return CorrelationStrength.STRONG_POSITIVE
        elif correlation >= 0.3:
            return CorrelationStrength.MODERATE_POSITIVE
        elif correlation >= -0.3:
            return CorrelationStrength.WEAK
        elif correlation >= -0.7:
            return CorrelationStrength.MODERATE_NEGATIVE
        else:
            return CorrelationStrength.STRONG_NEGATIVE
    
    def calculate_matrix(
        self,
        asset_returns: Dict[str, List[float]],
        pairs: List[AssetPair] = None,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        window_size: int = None
    ) -> Dict[str, CorrelationValue]:
        """
        Calculate correlation matrix for multiple pairs.
        
        Args:
            asset_returns: Dict mapping asset name to return series
            pairs: Asset pairs to calculate (default: DEFAULT_PAIRS)
            method: Correlation method
            window_size: Window size for calculation
        
        Returns:
            Dict mapping pair_id to CorrelationValue
        """
        if pairs is None:
            pairs = DEFAULT_PAIRS
        
        if window_size is None:
            window_size = self.default_window
        
        now = datetime.now(timezone.utc)
        matrix = {}
        
        for pair in pairs:
            if pair.asset_a not in asset_returns or pair.asset_b not in asset_returns:
                continue
            
            returns_a = asset_returns[pair.asset_a][-window_size:]
            returns_b = asset_returns[pair.asset_b][-window_size:]
            
            if len(returns_a) < 10 or len(returns_b) < 10:
                continue
            
            corr, p_value = self.calculate_correlation(returns_a, returns_b, method)
            strength = self.classify_strength(corr)
            
            # Calculate confidence
            confidence = 1 - p_value if p_value else 0.5
            confidence = min(0.95, max(0.1, confidence))
            
            matrix[pair.pair_id] = CorrelationValue(
                pair=pair,
                value=corr,
                method=method,
                window_size=len(returns_a),
                timestamp=now,
                p_value=p_value,
                confidence=confidence,
                strength=strength
            )
        
        return matrix
    
    def get_strongest_correlations(
        self,
        matrix: Dict[str, CorrelationValue],
        n: int = 5,
        positive_only: bool = False
    ) -> List[CorrelationValue]:
        """Get the N strongest correlations"""
        values = list(matrix.values())
        
        if positive_only:
            values = [v for v in values if v.value > 0]
        
        # Sort by absolute correlation
        values.sort(key=lambda x: abs(x.value), reverse=True)
        
        return values[:n]
    
    def get_matrix_summary(
        self,
        matrix: Dict[str, CorrelationValue]
    ) -> Dict:
        """Get summary statistics for correlation matrix"""
        if not matrix:
            return {}
        
        values = [v.value for v in matrix.values()]
        
        # Count by strength
        strength_counts = {}
        for strength in CorrelationStrength:
            strength_counts[strength.value] = len([
                v for v in matrix.values() if v.strength == strength
            ])
        
        return {
            "total_pairs": len(matrix),
            "avg_correlation": statistics.mean(values),
            "avg_abs_correlation": statistics.mean([abs(v) for v in values]),
            "max_correlation": max(values),
            "min_correlation": min(values),
            "by_strength": strength_counts
        }
