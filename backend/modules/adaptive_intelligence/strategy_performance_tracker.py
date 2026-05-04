"""
PHASE 11.1 - Strategy Performance Tracker
==========================================
Tracks strategy performance metrics for adaptive decisions.

Monitors:
- Win rate (recent vs long-term)
- Profit factor
- Expectancy
- Drawdown
- Regime-specific performance
"""

import random
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from collections import deque

from .adaptive_types import (
    StrategyPerformance, PerformanceTrend, DEFAULT_ADAPTIVE_CONFIG
)


class StrategyPerformanceTracker:
    """
    Strategy Performance Tracking Engine
    
    Tracks and analyzes strategy performance over time
    to identify improving or declining strategies.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        self.performance_history: Dict[str, List[StrategyPerformance]] = {}
        self.trade_history: Dict[str, deque] = {}  # strategy_id -> recent trades
        self.max_trade_history = 200
        self.max_perf_history = 100
    
    def track_performance(
        self,
        strategy_id: str,
        strategy_name: str,
        trades: Optional[List[Dict]] = None,
        current_regime: str = "NORMAL"
    ) -> StrategyPerformance:
        """
        Track and calculate performance for a strategy.
        
        Args:
            strategy_id: Strategy identifier
            strategy_name: Strategy name
            trades: Recent trade results
            current_regime: Current market regime
            
        Returns:
            StrategyPerformance analysis
        """
        now = datetime.now(timezone.utc)
        
        # Update trade history
        if trades:
            if strategy_id not in self.trade_history:
                self.trade_history[strategy_id] = deque(maxlen=self.max_trade_history)
            for trade in trades:
                self.trade_history[strategy_id].append(trade)
        
        # Get trade history
        all_trades = list(self.trade_history.get(strategy_id, []))
        
        # If no trades, generate mock data for testing
        if not all_trades:
            all_trades = self._generate_mock_trades(50)
        
        # Calculate metrics
        recent_window = self.config.get("rolling_window_size", 50)
        recent_trades = all_trades[-recent_window:] if len(all_trades) >= recent_window else all_trades
        
        # Win rate
        if recent_trades:
            recent_wins = sum(1 for t in recent_trades if t.get("pnl", 0) > 0)
            win_rate = recent_wins / len(recent_trades)
        else:
            win_rate = 0.5
        
        if all_trades:
            total_wins = sum(1 for t in all_trades if t.get("pnl", 0) > 0)
            long_term_win_rate = total_wins / len(all_trades)
        else:
            long_term_win_rate = 0.5
        
        # Profit factor
        gross_profit = sum(t["pnl"] for t in recent_trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in recent_trades if t.get("pnl", 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 2.0
        
        # Expectancy
        if recent_trades:
            expectancy = sum(t.get("pnl", 0) for t in recent_trades) / len(recent_trades)
        else:
            expectancy = 0
        
        # Drawdown
        max_dd, current_dd = self._calculate_drawdown(all_trades)
        
        # Sharpe (simplified)
        returns = [t.get("pnl", 0) for t in recent_trades]
        sharpe = self._calculate_sharpe(returns)
        
        # Performance trend
        trend, trend_strength = self._analyze_trend(strategy_id, win_rate, profit_factor)
        
        # Regime performance
        regime_perf = self._calculate_regime_performance(all_trades, current_regime)
        
        performance = StrategyPerformance(
            strategy_id=strategy_id,
            name=strategy_name,
            timestamp=now,
            win_rate=win_rate,
            long_term_win_rate=long_term_win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            sharpe_ratio=sharpe,
            performance_trend=trend,
            trend_strength=trend_strength,
            regime_performance=regime_perf,
            total_trades=len(all_trades),
            recent_trades=len(recent_trades)
        )
        
        # Save to history
        self._add_to_history(strategy_id, performance)
        
        return performance
    
    def _calculate_drawdown(self, trades: List[Dict]) -> tuple:
        """Calculate max and current drawdown."""
        if not trades:
            return 0.0, 0.0
        
        equity = 100.0  # Start with 100
        peak = equity
        max_dd = 0.0
        
        for trade in trades:
            equity += trade.get("pnl", 0)
            peak = max(peak, equity)
            dd = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        current_dd = (peak - equity) / peak if peak > 0 else 0
        
        return max_dd, current_dd
    
    def _calculate_sharpe(self, returns: List[float], risk_free: float = 0) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        import math
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.001
        
        sharpe = (mean - risk_free) / std if std > 0 else 0
        
        # Annualize (assuming daily)
        return sharpe * (252 ** 0.5)
    
    def _analyze_trend(
        self,
        strategy_id: str,
        current_wr: float,
        current_pf: float
    ) -> tuple:
        """Analyze performance trend."""
        history = self.performance_history.get(strategy_id, [])
        
        if len(history) < 3:
            return PerformanceTrend.STABLE, 0.5
        
        # Compare recent to older
        recent = history[-3:]
        older = history[-10:-3] if len(history) > 10 else history[:-3]
        
        if not older:
            return PerformanceTrend.STABLE, 0.5
        
        recent_avg_wr = sum(p.win_rate for p in recent) / len(recent)
        older_avg_wr = sum(p.win_rate for p in older) / len(older)
        
        recent_avg_pf = sum(p.profit_factor for p in recent) / len(recent)
        older_avg_pf = sum(p.profit_factor for p in older) / len(older)
        
        wr_change = recent_avg_wr - older_avg_wr
        pf_change = (recent_avg_pf - older_avg_pf) / older_avg_pf if older_avg_pf > 0 else 0
        
        # Determine trend
        decline_threshold = self.config["win_rate_decline_threshold"]
        
        if wr_change > decline_threshold and pf_change > 0.1:
            trend = PerformanceTrend.IMPROVING
            strength = min(1.0, (wr_change + pf_change) / 0.2)
        elif wr_change < -decline_threshold or pf_change < -self.config["pf_decline_threshold"]:
            if pf_change < -0.5 or current_pf < 1.0:
                trend = PerformanceTrend.CRITICAL
                strength = min(1.0, abs(pf_change))
            else:
                trend = PerformanceTrend.DECLINING
                strength = min(1.0, abs(wr_change) / decline_threshold)
        else:
            trend = PerformanceTrend.STABLE
            strength = 0.5
        
        return trend, strength
    
    def _calculate_regime_performance(
        self,
        trades: List[Dict],
        current_regime: str
    ) -> Dict[str, float]:
        """Calculate performance by regime."""
        regime_results = {}
        regime_counts = {}
        
        for trade in trades:
            regime = trade.get("regime", "UNKNOWN")
            pnl = trade.get("pnl", 0)
            
            if regime not in regime_results:
                regime_results[regime] = 0
                regime_counts[regime] = 0
            
            regime_results[regime] += pnl
            regime_counts[regime] += 1
        
        # Normalize to average per trade
        return {
            regime: results / regime_counts[regime] if regime_counts.get(regime, 0) > 0 else 0
            for regime, results in regime_results.items()
        }
    
    def _generate_mock_trades(self, count: int) -> List[Dict]:
        """Generate mock trades for testing."""
        trades = []
        regimes = ["TRENDING", "RANGING", "VOLATILE", "NORMAL"]
        
        for i in range(count):
            # Slight positive expectancy
            base_pnl = random.gauss(0.002, 0.015) * 100
            
            trades.append({
                "trade_id": f"mock_{i}",
                "pnl": base_pnl,
                "regime": random.choice(regimes),
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=count - i)).isoformat()
            })
        
        return trades
    
    def _add_to_history(self, strategy_id: str, performance: StrategyPerformance):
        """Add performance to history."""
        if strategy_id not in self.performance_history:
            self.performance_history[strategy_id] = []
        
        self.performance_history[strategy_id].append(performance)
        
        if len(self.performance_history[strategy_id]) > self.max_perf_history:
            self.performance_history[strategy_id] = \
                self.performance_history[strategy_id][-self.max_perf_history:]
    
    def get_all_strategies_summary(self) -> Dict:
        """Get summary of all tracked strategies."""
        summary = {}
        
        for sid, history in self.performance_history.items():
            if history:
                latest = history[-1]
                summary[sid] = {
                    "name": latest.name,
                    "win_rate": round(latest.win_rate, 4),
                    "profit_factor": round(latest.profit_factor, 3),
                    "trend": latest.performance_trend.value,
                    "total_trades": latest.total_trades
                }
        
        return summary
    
    def get_declining_strategies(self) -> List[str]:
        """Get list of declining strategies."""
        declining = []
        
        for sid, history in self.performance_history.items():
            if history and history[-1].performance_trend in [
                PerformanceTrend.DECLINING, PerformanceTrend.CRITICAL
            ]:
                declining.append(sid)
        
        return declining
