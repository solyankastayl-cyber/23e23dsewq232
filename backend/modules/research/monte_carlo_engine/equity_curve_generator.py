"""
PHASE 6.3 - Equity Curve Generator
====================================
Generates and analyzes equity curves from simulations.
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

from .monte_types import TradeRecord, EquityCurve


class EquityCurveGenerator:
    """
    Generates equity curves from trade sequences.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
    
    def generate_curve(
        self,
        trades: List[TradeRecord],
        path_id: int = 0
    ) -> EquityCurve:
        """
        Generate single equity curve from trade sequence.
        """
        equity_values = [self.initial_capital]
        current_equity = self.initial_capital
        peak_equity = self.initial_capital
        min_equity = self.initial_capital
        max_drawdown = 0.0
        
        for trade in trades:
            # Apply trade return
            pnl = current_equity * trade.return_pct
            current_equity += pnl
            equity_values.append(current_equity)
            
            # Track peak and drawdown
            if current_equity > peak_equity:
                peak_equity = current_equity
            
            if current_equity < min_equity:
                min_equity = current_equity
            
            # Calculate drawdown from peak
            if peak_equity > 0:
                current_dd = (peak_equity - current_equity) / peak_equity
                if current_dd > max_drawdown:
                    max_drawdown = current_dd
        
        final_return = (current_equity - self.initial_capital) / self.initial_capital
        
        return EquityCurve(
            path_id=path_id,
            equity_values=equity_values,
            final_return=final_return,
            max_drawdown=max_drawdown,
            peak_equity=peak_equity,
            min_equity=min_equity
        )
    
    def generate_curves(
        self,
        simulations: List[List[TradeRecord]]
    ) -> List[EquityCurve]:
        """
        Generate equity curves for all simulations.
        """
        curves = []
        for i, trades in enumerate(simulations):
            curve = self.generate_curve(trades, path_id=i)
            curves.append(curve)
        return curves
    
    def get_curve_statistics(
        self,
        curves: List[EquityCurve]
    ) -> Dict:
        """
        Calculate statistics across all equity curves.
        """
        if not curves:
            return {}
        
        final_returns = [c.final_return for c in curves]
        max_drawdowns = [c.max_drawdown for c in curves]
        
        return {
            "total_curves": len(curves),
            "final_return": {
                "mean": statistics.mean(final_returns),
                "median": statistics.median(final_returns),
                "std": statistics.stdev(final_returns) if len(final_returns) > 1 else 0,
                "min": min(final_returns),
                "max": max(final_returns)
            },
            "max_drawdown": {
                "mean": statistics.mean(max_drawdowns),
                "median": statistics.median(max_drawdowns),
                "std": statistics.stdev(max_drawdowns) if len(max_drawdowns) > 1 else 0,
                "min": min(max_drawdowns),
                "max": max(max_drawdowns)
            }
        }
    
    def get_percentile_curves(
        self,
        curves: List[EquityCurve],
        percentiles: List[int] = [5, 25, 50, 75, 95]
    ) -> Dict[int, EquityCurve]:
        """
        Get curves at specific percentiles of final return.
        """
        if not curves:
            return {}
        
        sorted_curves = sorted(curves, key=lambda c: c.final_return)
        n = len(sorted_curves)
        
        result = {}
        for p in percentiles:
            idx = int((p / 100) * n)
            idx = min(max(0, idx), n - 1)
            result[p] = sorted_curves[idx]
        
        return result
    
    def calculate_profit_probability(
        self,
        curves: List[EquityCurve]
    ) -> float:
        """
        Calculate probability of positive return.
        """
        if not curves:
            return 0.0
        
        profitable = sum(1 for c in curves if c.final_return > 0)
        return profitable / len(curves)
    
    def get_equity_bands(
        self,
        curves: List[EquityCurve]
    ) -> Dict:
        """
        Calculate equity bands (confidence intervals at each point).
        """
        if not curves:
            return {}
        
        # Find max length
        max_len = max(len(c.equity_values) for c in curves)
        
        bands = {
            "p5": [],
            "p25": [],
            "p50": [],
            "p75": [],
            "p95": []
        }
        
        for i in range(max_len):
            # Get all values at this point
            values = []
            for curve in curves:
                if i < len(curve.equity_values):
                    values.append(curve.equity_values[i])
            
            if values:
                values.sort()
                n = len(values)
                
                bands["p5"].append(values[int(0.05 * n)])
                bands["p25"].append(values[int(0.25 * n)])
                bands["p50"].append(values[int(0.50 * n)])
                bands["p75"].append(values[int(0.75 * n)])
                bands["p95"].append(values[min(int(0.95 * n), n - 1)])
        
        return bands
