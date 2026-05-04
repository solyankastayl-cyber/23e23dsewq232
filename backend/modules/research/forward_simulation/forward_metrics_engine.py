"""
Forward Metrics Engine
======================

Calculates performance metrics from simulation (PHASE 2.3)
"""

import math
from typing import Dict, List, Optional, Any

from .forward_types import (
    SimulatedTrade,
    TradeStatus,
    ForwardMetrics,
    EquityCurve,
    EquityPoint,
    SimulationConfig
)


class ForwardMetricsEngine:
    """
    Calculates comprehensive metrics from forward simulation.
    
    Metrics:
    - Win rate, profit factor, expectancy
    - Equity curve, drawdown
    - Sharpe, Sortino ratios
    - Strategy/regime breakdown
    """
    
    def __init__(self):
        print("[ForwardMetricsEngine] Initialized (PHASE 2.3)")
    
    def calculate_metrics(
        self,
        trades: List[SimulatedTrade],
        equity_curve: EquityCurve,
        config: SimulationConfig
    ) -> ForwardMetrics:
        """
        Calculate all metrics from trades.
        """
        
        metrics = ForwardMetrics()
        
        if not trades:
            return metrics
        
        # Filter closed trades
        closed_trades = [t for t in trades if t.status != TradeStatus.OPEN]
        
        if not closed_trades:
            return metrics
        
        # Basic counts
        metrics.total_trades = len(closed_trades)
        metrics.winning_trades = len([t for t in closed_trades if t.pnl > 0])
        metrics.losing_trades = len([t for t in closed_trades if t.pnl <= 0])
        
        # Win rate
        metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0
        
        # P&L metrics
        winners = [t for t in closed_trades if t.pnl > 0]
        losers = [t for t in closed_trades if t.pnl <= 0]
        
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        
        # Profit factor (cap at 999.99 for JSON serialization)
        if gross_loss > 0:
            metrics.profit_factor = min(999.99, gross_profit / gross_loss)
        elif gross_profit > 0:
            metrics.profit_factor = 999.99  # Cap instead of inf
        else:
            metrics.profit_factor = 0
        
        # Returns
        metrics.total_return = sum(t.pnl for t in closed_trades)
        metrics.total_return_pct = (metrics.total_return / config.initial_capital) * 100 if config.initial_capital > 0 else 0
        
        # Average trade
        metrics.average_trade = metrics.total_return / metrics.total_trades if metrics.total_trades > 0 else 0
        
        # Average win/loss
        metrics.average_win = gross_profit / len(winners) if winners else 0
        metrics.average_loss = gross_loss / len(losers) if losers else 0
        
        # Largest win/loss
        if closed_trades:
            metrics.largest_win = max(t.pnl for t in closed_trades)
            metrics.largest_loss = min(t.pnl for t in closed_trades)
        
        # Average R-multiple
        metrics.avg_r_multiple = sum(t.r_multiple for t in closed_trades) / len(closed_trades)
        
        # Expectancy
        metrics.expectancy = metrics.avg_r_multiple
        
        # Duration metrics
        durations = [t.duration_bars for t in closed_trades]
        metrics.avg_duration_bars = sum(durations) / len(durations) if durations else 0
        
        winner_durations = [t.duration_bars for t in winners]
        loser_durations = [t.duration_bars for t in losers]
        
        metrics.avg_winner_duration = sum(winner_durations) / len(winner_durations) if winner_durations else 0
        metrics.avg_loser_duration = sum(loser_durations) / len(loser_durations) if loser_durations else 0
        
        # Costs
        metrics.total_slippage = sum(t.slippage_cost for t in closed_trades)
        metrics.total_commission = sum(t.commission_cost for t in closed_trades)
        metrics.total_costs = metrics.total_slippage + metrics.total_commission
        
        # Drawdown from equity curve
        metrics.max_drawdown = equity_curve.max_drawdown
        metrics.max_drawdown_pct = equity_curve.max_drawdown_pct
        
        # Sharpe and Sortino
        metrics.sharpe_ratio = self._calculate_sharpe(closed_trades, config.initial_capital)
        metrics.sortino_ratio = self._calculate_sortino(closed_trades, config.initial_capital)
        
        # Strategy breakdown
        metrics.strategy_contribution = self._calculate_strategy_contribution(closed_trades)
        
        # Regime breakdown
        metrics.regime_performance = self._calculate_regime_performance(closed_trades)
        
        return metrics
    
    def build_equity_curve(
        self,
        trades: List[SimulatedTrade],
        config: SimulationConfig,
        total_bars: int
    ) -> EquityCurve:
        """
        Build equity curve from trades.
        """
        
        curve = EquityCurve()
        curve.starting_equity = config.initial_capital
        
        # Initialize equity at starting capital
        equity = config.initial_capital
        peak_equity = equity
        
        # Build trade timeline
        trade_by_bar = {}
        for trade in trades:
            if trade.status != TradeStatus.OPEN:
                bar = trade.exit_bar
                if bar not in trade_by_bar:
                    trade_by_bar[bar] = []
                trade_by_bar[bar].append(trade)
        
        # Generate equity points
        for bar in range(total_bars):
            # Apply any closed trades at this bar
            if bar in trade_by_bar:
                for trade in trade_by_bar[bar]:
                    equity += trade.pnl
            
            # Track peak
            if equity > peak_equity:
                peak_equity = equity
            
            # Calculate drawdown
            drawdown = peak_equity - equity
            drawdown_pct = drawdown / peak_equity if peak_equity > 0 else 0
            
            # Track max drawdown
            if drawdown > curve.max_drawdown:
                curve.max_drawdown = drawdown
                curve.max_drawdown_pct = drawdown_pct
            
            # Store point (sample every 10 bars to reduce size)
            if bar % 10 == 0 or bar == total_bars - 1:
                point = EquityPoint(
                    bar=bar,
                    timestamp=int(time.time() * 1000),
                    equity=equity,
                    drawdown=drawdown,
                    drawdown_pct=drawdown_pct,
                    open_positions=0  # Simplified
                )
                curve.points.append(point)
        
        curve.ending_equity = equity
        curve.peak_equity = peak_equity
        
        return curve
    
    def _calculate_sharpe(
        self,
        trades: List[SimulatedTrade],
        initial_capital: float,
        risk_free: float = 0.0
    ) -> float:
        """Calculate Sharpe ratio"""
        
        if len(trades) < 2:
            return 0.0
        
        # Calculate returns
        returns = [t.pnl / initial_capital for t in trades]
        
        avg_return = sum(returns) / len(returns)
        
        # Standard deviation
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        if std_dev == 0:
            return 0.0
        
        # Annualized (assuming ~250 trades per year)
        annualization_factor = math.sqrt(min(250, len(trades)))
        
        sharpe = ((avg_return - risk_free) / std_dev) * annualization_factor
        
        # Cap at reasonable value for JSON serialization
        return min(99.99, max(-99.99, sharpe))
    
    def _calculate_sortino(
        self,
        trades: List[SimulatedTrade],
        initial_capital: float,
        risk_free: float = 0.0
    ) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        
        if len(trades) < 2:
            return 0.0
        
        returns = [t.pnl / initial_capital for t in trades]
        avg_return = sum(returns) / len(returns)
        
        # Downside deviation (only negative returns)
        negative_returns = [r for r in returns if r < 0]
        
        if not negative_returns:
            return min(999.99, 99.99) if avg_return > 0 else 0  # Cap instead of inf
        
        downside_variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        downside_dev = math.sqrt(downside_variance)
        
        if downside_dev == 0:
            return 0.0
        
        annualization_factor = math.sqrt(min(250, len(trades)))
        
        sortino = ((avg_return - risk_free) / downside_dev) * annualization_factor
        
        # Cap at reasonable value for JSON serialization
        return min(99.99, max(-99.99, sortino))
    
    def _calculate_strategy_contribution(
        self,
        trades: List[SimulatedTrade]
    ) -> Dict[str, float]:
        """Calculate P&L contribution by strategy"""
        
        contribution = {}
        
        for trade in trades:
            strategy = trade.strategy or "UNKNOWN"
            if strategy not in contribution:
                contribution[strategy] = 0.0
            contribution[strategy] += trade.pnl
        
        # Round values
        return {k: round(v, 2) for k, v in contribution.items()}
    
    def _calculate_regime_performance(
        self,
        trades: List[SimulatedTrade]
    ) -> Dict[str, float]:
        """Calculate P&L by regime"""
        
        performance = {}
        
        for trade in trades:
            regime = trade.regime or "UNKNOWN"
            if regime not in performance:
                performance[regime] = 0.0
            performance[regime] += trade.pnl
        
        return {k: round(v, 2) for k, v in performance.items()}


# Import time at module level
import time

# Global singleton
forward_metrics_engine = ForwardMetricsEngine()
