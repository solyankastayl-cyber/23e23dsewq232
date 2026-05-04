"""
Calibration Metrics Calculator
==============================

Calculates performance metrics for Strategy Calibration Matrix (PHASE 2.1)
"""

import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .calibration_types import CalibrationMetrics, StrategyGrade


@dataclass
class Trade:
    """Single trade for metrics calculation"""
    entry_price: float
    exit_price: float
    direction: str  # LONG or SHORT
    size: float
    r_multiple: float  # Actual R-multiple achieved
    pnl: float
    pnl_pct: float
    is_winner: bool
    blocked: bool = False  # Was signal blocked by filters


class CalibrationMetricsCalculator:
    """
    Calculates calibration metrics from trade list.
    
    Metrics:
    - win_rate: Winners / Total
    - profit_factor: Gross Profit / Gross Loss
    - expectancy: Average P&L per trade
    - max_drawdown: Maximum peak-to-trough decline
    - average_trade: Average trade result
    - sample_size: Number of trades
    - block_rate: % of signals blocked
    """
    
    def __init__(self):
        pass
    
    def calculate(
        self,
        trades: List[Trade],
        blocked_signals: int = 0
    ) -> CalibrationMetrics:
        """
        Calculate all metrics from trade list.
        """
        
        metrics = CalibrationMetrics()
        
        if not trades:
            return metrics
        
        # Basic counts
        total = len(trades)
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        metrics.total_trades = total
        metrics.winning_trades = len(winners)
        metrics.losing_trades = len(losers)
        metrics.sample_size = total
        
        # Win rate
        metrics.win_rate = len(winners) / total if total > 0 else 0
        
        # Gross profit/loss
        metrics.gross_profit = sum(t.pnl for t in winners) if winners else 0
        metrics.gross_loss = abs(sum(t.pnl for t in losers)) if losers else 0
        
        # Profit factor
        if metrics.gross_loss > 0:
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
        else:
            metrics.profit_factor = float('inf') if metrics.gross_profit > 0 else 0
        
        # Average trade
        total_pnl = sum(t.pnl for t in trades)
        metrics.average_trade = total_pnl / total if total > 0 else 0
        
        # Expectancy (same as average trade in R)
        avg_r = sum(t.r_multiple for t in trades) / total if total > 0 else 0
        metrics.expectancy = avg_r
        metrics.avg_r_multiple = avg_r
        
        # Largest win/loss
        if winners:
            metrics.largest_win = max(t.pnl for t in winners)
            metrics.avg_win = metrics.gross_profit / len(winners)
        
        if losers:
            metrics.largest_loss = min(t.pnl for t in losers)
            metrics.avg_loss = metrics.gross_loss / len(losers)
        
        # Max drawdown
        metrics.max_drawdown = self._calculate_max_drawdown(trades)
        
        # Block rate
        total_signals = total + blocked_signals
        metrics.block_rate = blocked_signals / total_signals if total_signals > 0 else 0
        
        # Sharpe ratio (simplified)
        metrics.sharpe_ratio = self._calculate_sharpe(trades)
        
        return metrics
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown from equity curve"""
        
        if not trades:
            return 0.0
        
        # Build equity curve
        equity = [0.0]
        for trade in trades:
            equity.append(equity[-1] + trade.pnl)
        
        # Find max drawdown
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe(self, trades: List[Trade], risk_free: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        
        if len(trades) < 2:
            return 0.0
        
        returns = [t.pnl_pct for t in trades]
        avg_return = sum(returns) / len(returns)
        
        # Standard deviation
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        if std_dev == 0:
            return 0.0
        
        # Annualized (assuming daily trades)
        sharpe = (avg_return - risk_free) / std_dev * math.sqrt(252)
        
        return sharpe
    
    def grade_metrics(self, metrics: CalibrationMetrics) -> StrategyGrade:
        """Assign grade based on metrics"""
        return metrics.get_grade()
    
    def compare_metrics(
        self,
        metrics_a: CalibrationMetrics,
        metrics_b: CalibrationMetrics
    ) -> Dict[str, Any]:
        """Compare two sets of metrics"""
        
        return {
            "winRateDelta": metrics_a.win_rate - metrics_b.win_rate,
            "profitFactorDelta": metrics_a.profit_factor - metrics_b.profit_factor,
            "expectancyDelta": metrics_a.expectancy - metrics_b.expectancy,
            "maxDrawdownDelta": metrics_a.max_drawdown - metrics_b.max_drawdown,
            "sampleSizeDelta": metrics_a.sample_size - metrics_b.sample_size,
            "winner": "A" if metrics_a.profit_factor > metrics_b.profit_factor else "B"
        }


# Global instance
calibration_metrics_calculator = CalibrationMetricsCalculator()
