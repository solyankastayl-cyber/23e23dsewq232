"""
PHASE 6.3 - Drawdown Analyzer
==============================
Analyzes drawdown distribution across simulations.
"""

import math
from typing import Dict, List, Optional, Tuple
import statistics

from .monte_types import EquityCurve, DrawdownDistribution


class DrawdownAnalyzer:
    """
    Analyzes drawdown characteristics from equity curves.
    """
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        curves: List[EquityCurve]
    ) -> DrawdownDistribution:
        """
        Calculate drawdown distribution statistics.
        """
        if not curves:
            return DrawdownDistribution(
                p50_drawdown=0, p75_drawdown=0, p90_drawdown=0,
                p95_drawdown=0, p99_drawdown=0,
                mean_drawdown=0, max_observed=0
            )
        
        # Collect max drawdowns
        max_drawdowns = [c.max_drawdown for c in curves]
        max_drawdowns.sort()
        
        n = len(max_drawdowns)
        
        return DrawdownDistribution(
            p50_drawdown=self._percentile(max_drawdowns, 50),
            p75_drawdown=self._percentile(max_drawdowns, 75),
            p90_drawdown=self._percentile(max_drawdowns, 90),
            p95_drawdown=self._percentile(max_drawdowns, 95),
            p99_drawdown=self._percentile(max_drawdowns, 99),
            mean_drawdown=statistics.mean(max_drawdowns),
            max_observed=max(max_drawdowns)
        )
    
    def _percentile(self, sorted_data: List[float], p: int) -> float:
        """Calculate percentile from sorted data"""
        if not sorted_data:
            return 0.0
        
        n = len(sorted_data)
        idx = int((p / 100) * n)
        idx = min(max(0, idx), n - 1)
        return sorted_data[idx]
    
    def calculate_drawdown_series(
        self,
        equity_values: List[float]
    ) -> List[float]:
        """
        Calculate drawdown at each point in equity curve.
        """
        if not equity_values:
            return []
        
        drawdowns = []
        peak = equity_values[0]
        
        for value in equity_values:
            if value > peak:
                peak = value
            
            if peak > 0:
                dd = (peak - value) / peak
            else:
                dd = 0
            
            drawdowns.append(dd)
        
        return drawdowns
    
    def find_drawdown_periods(
        self,
        equity_values: List[float],
        threshold: float = 0.05
    ) -> List[Dict]:
        """
        Find all drawdown periods exceeding threshold.
        """
        drawdowns = self.calculate_drawdown_series(equity_values)
        periods = []
        
        in_drawdown = False
        start_idx = 0
        max_dd = 0
        
        for i, dd in enumerate(drawdowns):
            if dd > threshold and not in_drawdown:
                # Start of drawdown
                in_drawdown = True
                start_idx = i
                max_dd = dd
            elif in_drawdown:
                if dd > max_dd:
                    max_dd = dd
                
                if dd < threshold * 0.1:  # Recovered (within 10% of threshold)
                    # End of drawdown
                    periods.append({
                        "start_idx": start_idx,
                        "end_idx": i,
                        "duration": i - start_idx,
                        "max_drawdown": max_dd
                    })
                    in_drawdown = False
        
        # Handle ongoing drawdown
        if in_drawdown:
            periods.append({
                "start_idx": start_idx,
                "end_idx": len(drawdowns) - 1,
                "duration": len(drawdowns) - 1 - start_idx,
                "max_drawdown": max_dd
            })
        
        return periods
    
    def calculate_underwater_time(
        self,
        curves: List[EquityCurve]
    ) -> Dict:
        """
        Calculate time spent underwater (below peak).
        """
        if not curves:
            return {}
        
        underwater_ratios = []
        
        for curve in curves:
            drawdowns = self.calculate_drawdown_series(curve.equity_values)
            underwater_points = sum(1 for dd in drawdowns if dd > 0.01)  # 1% threshold
            ratio = underwater_points / len(drawdowns) if drawdowns else 0
            underwater_ratios.append(ratio)
        
        return {
            "mean_underwater_ratio": statistics.mean(underwater_ratios),
            "median_underwater_ratio": statistics.median(underwater_ratios),
            "max_underwater_ratio": max(underwater_ratios),
            "min_underwater_ratio": min(underwater_ratios)
        }
    
    def calculate_recovery_statistics(
        self,
        curves: List[EquityCurve]
    ) -> Dict:
        """
        Calculate recovery time statistics.
        """
        if not curves:
            return {}
        
        recovery_times = []
        
        for curve in curves:
            drawdowns = self.calculate_drawdown_series(curve.equity_values)
            periods = self.find_drawdown_periods(curve.equity_values, threshold=0.05)
            
            for period in periods:
                recovery_times.append(period["duration"])
        
        if not recovery_times:
            return {
                "mean_recovery_time": 0,
                "median_recovery_time": 0,
                "max_recovery_time": 0,
                "total_drawdown_periods": 0
            }
        
        return {
            "mean_recovery_time": statistics.mean(recovery_times),
            "median_recovery_time": statistics.median(recovery_times),
            "max_recovery_time": max(recovery_times),
            "total_drawdown_periods": len(recovery_times)
        }
