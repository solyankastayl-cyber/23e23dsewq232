"""
PHASE 7 - Rolling Correlation Engine
======================================
Calculates rolling correlations over time windows.
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import statistics

from .correlation_types import (
    AssetPair, RollingCorrelation, CorrelationMethod
)
from .correlation_matrix import CorrelationMatrixEngine


class RollingCorrelationEngine:
    """
    Calculates rolling correlations for tracking correlation changes.
    """
    
    def __init__(self):
        self.matrix_engine = CorrelationMatrixEngine()
        self.default_windows = [24, 96, 168, 720]  # 1d, 4d, 1w, 1mo in hourly candles
    
    def calculate_rolling(
        self,
        returns_a: List[float],
        returns_b: List[float],
        pair: AssetPair,
        window_size: int = 30,
        method: CorrelationMethod = CorrelationMethod.PEARSON
    ) -> RollingCorrelation:
        """
        Calculate rolling correlation between two assets.
        """
        n = len(returns_a)
        if n != len(returns_b) or n < window_size:
            return RollingCorrelation(
                pair=pair,
                window_size=window_size,
                method=method
            )
        
        # Calculate correlation for each window
        correlations = []
        timestamps = []
        
        for i in range(window_size, n + 1):
            window_a = returns_a[i - window_size:i]
            window_b = returns_b[i - window_size:i]
            
            corr, _ = self.matrix_engine.calculate_correlation(window_a, window_b, method)
            correlations.append(corr)
            # Use index as timestamp proxy
            timestamps.append(datetime.now(timezone.utc))
        
        if not correlations:
            return RollingCorrelation(
                pair=pair,
                window_size=window_size,
                method=method
            )
        
        # Calculate statistics
        current = correlations[-1]
        mean_val = statistics.mean(correlations)
        std_val = statistics.stdev(correlations) if len(correlations) > 1 else 0.0
        
        # Determine trend
        if len(correlations) >= 10:
            recent = statistics.mean(correlations[-5:])
            older = statistics.mean(correlations[-10:-5])
            
            if recent > older + 0.1:
                trend = "INCREASING"
            elif recent < older - 0.1:
                trend = "DECREASING"
            else:
                trend = "STABLE"
        else:
            trend = "STABLE"
        
        return RollingCorrelation(
            pair=pair,
            window_size=window_size,
            method=method,
            timestamps=timestamps,
            values=correlations,
            current_value=current,
            mean_value=mean_val,
            std_value=std_val,
            min_value=min(correlations),
            max_value=max(correlations),
            trend=trend
        )
    
    def calculate_multi_window(
        self,
        returns_a: List[float],
        returns_b: List[float],
        pair: AssetPair,
        windows: List[int] = None,
        method: CorrelationMethod = CorrelationMethod.PEARSON
    ) -> Dict[int, RollingCorrelation]:
        """
        Calculate rolling correlation for multiple window sizes.
        """
        if windows is None:
            windows = self.default_windows
        
        results = {}
        
        for window in windows:
            if len(returns_a) >= window:
                results[window] = self.calculate_rolling(
                    returns_a, returns_b, pair, window, method
                )
        
        return results
    
    def detect_correlation_breakout(
        self,
        rolling: RollingCorrelation,
        threshold_std: float = 2.0
    ) -> Optional[Dict]:
        """
        Detect if current correlation is a breakout from normal range.
        """
        if not rolling.values or rolling.std_value == 0:
            return None
        
        z_score = (rolling.current_value - rolling.mean_value) / rolling.std_value
        
        if abs(z_score) >= threshold_std:
            return {
                "pair": rolling.pair.pair_id,
                "z_score": round(z_score, 2),
                "current": round(rolling.current_value, 4),
                "mean": round(rolling.mean_value, 4),
                "std": round(rolling.std_value, 4),
                "direction": "HIGH" if z_score > 0 else "LOW",
                "breakout_type": "CORRELATION_SURGE" if z_score > 0 else "CORRELATION_DROP"
            }
        
        return None
    
    def get_correlation_change(
        self,
        rolling: RollingCorrelation,
        lookback: int = 10
    ) -> Dict:
        """
        Calculate correlation change over recent period.
        """
        if len(rolling.values) < lookback + 1:
            return {
                "change": 0.0,
                "pct_change": 0.0,
                "direction": "STABLE"
            }
        
        current = rolling.values[-1]
        past = rolling.values[-(lookback + 1)]
        
        change = current - past
        pct_change = change / abs(past) if past != 0 else 0
        
        if change > 0.1:
            direction = "STRENGTHENING"
        elif change < -0.1:
            direction = "WEAKENING"
        else:
            direction = "STABLE"
        
        return {
            "change": round(change, 4),
            "pct_change": round(pct_change, 4),
            "direction": direction,
            "current": round(current, 4),
            "past": round(past, 4)
        }
    
    def calculate_correlation_volatility(
        self,
        rolling: RollingCorrelation
    ) -> Dict:
        """
        Calculate how volatile the correlation has been.
        """
        if len(rolling.values) < 5:
            return {"volatility": 0, "regime": "STABLE"}
        
        # Calculate volatility of correlation
        corr_changes = [
            abs(rolling.values[i] - rolling.values[i-1])
            for i in range(1, len(rolling.values))
        ]
        
        avg_change = statistics.mean(corr_changes)
        
        if avg_change < 0.02:
            regime = "STABLE"
        elif avg_change < 0.05:
            regime = "MODERATE"
        else:
            regime = "VOLATILE"
        
        return {
            "volatility": round(avg_change, 4),
            "regime": regime,
            "max_change": round(max(corr_changes), 4),
            "min_change": round(min(corr_changes), 4)
        }
