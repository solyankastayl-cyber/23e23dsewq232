"""
Capital Efficiency Engine
=========================

PHASE 3.4 - Calculates capital efficiency metrics for strategies.
"""

import time
from typing import Dict, List, Optional, Any

from .capital_types import (
    StrategyPerformance,
    CapitalEfficiency,
    PerformanceGrade
)


class CapitalEfficiencyEngine:
    """
    Calculates capital efficiency:
    - Return on capital
    - Return per risk unit
    - Capital utilization
    - Efficiency scoring
    """
    
    def __init__(self):
        # Efficiency thresholds
        self._efficiency_grades = {
            PerformanceGrade.EXCELLENT: 80,
            PerformanceGrade.GOOD: 60,
            PerformanceGrade.AVERAGE: 40,
            PerformanceGrade.BELOW: 20,
            PerformanceGrade.POOR: 0
        }
        
        # Benchmark metrics
        self._benchmark = {
            "return_on_capital": 0.15,    # 15% annual
            "sharpe_ratio": 1.5,
            "profit_factor": 1.5,
            "win_rate": 55
        }
        
        print("[CapitalEfficiencyEngine] Initialized (PHASE 3.4)")
    
    def calculate_efficiency(
        self,
        strategy_id: str,
        performance: StrategyPerformance,
        allocated_capital: float,
        utilized_capital: float,
        risk_taken: float,
        missed_opportunities: int = 0
    ) -> CapitalEfficiency:
        """Calculate capital efficiency for a strategy"""
        
        efficiency = CapitalEfficiency(
            strategy_id=strategy_id,
            computed_at=int(time.time() * 1000)
        )
        
        # Return on capital
        if allocated_capital > 0:
            efficiency.return_on_capital = performance.total_pnl / allocated_capital
        
        # Return per risk unit
        if risk_taken > 0:
            efficiency.return_per_risk_unit = performance.total_pnl / risk_taken
        
        # Capital utilization
        if allocated_capital > 0:
            efficiency.capital_utilization = (utilized_capital / allocated_capital) * 100
        
        # Capital turnover (simplified)
        if allocated_capital > 0 and performance.avg_trade_duration > 0:
            trades_per_month = 30 * 24 / max(1, performance.avg_trade_duration)
            efficiency.capital_turnover = trades_per_month * (utilized_capital / allocated_capital)
        
        # Efficiency score (0-100)
        efficiency.efficiency_score = self._calculate_efficiency_score(
            performance, efficiency.return_on_capital, efficiency.capital_utilization
        )
        
        # Opportunity metrics
        efficiency.missed_opportunities = missed_opportunities
        if performance.losing_trades > 0 and performance.total_trades > 0:
            efficiency.capital_locked_pct = (performance.gross_loss / max(1, allocated_capital)) * 100
        
        # Comparison
        efficiency.vs_benchmark = efficiency.return_on_capital / self._benchmark["return_on_capital"] - 1
        efficiency.vs_average = 0  # Set externally based on portfolio
        
        return efficiency
    
    def _calculate_efficiency_score(
        self,
        performance: StrategyPerformance,
        return_on_capital: float,
        utilization: float
    ) -> float:
        """Calculate overall efficiency score"""
        
        score = 50  # Base score
        
        # Return on capital contribution (0-25)
        if return_on_capital > 0.30:
            score += 25
        elif return_on_capital > 0.20:
            score += 20
        elif return_on_capital > 0.10:
            score += 15
        elif return_on_capital > 0.05:
            score += 10
        elif return_on_capital > 0:
            score += 5
        else:
            score -= 15
        
        # Profit factor contribution (0-15)
        if performance.profit_factor >= 2.5:
            score += 15
        elif performance.profit_factor >= 2.0:
            score += 12
        elif performance.profit_factor >= 1.5:
            score += 8
        elif performance.profit_factor >= 1.2:
            score += 4
        else:
            score -= 10
        
        # Utilization contribution (0-10)
        if 50 <= utilization <= 80:
            score += 10  # Optimal range
        elif 30 <= utilization < 50 or 80 < utilization <= 90:
            score += 5
        elif utilization > 90:
            score -= 5  # Over-utilized
        elif utilization < 30:
            score -= 5  # Under-utilized
        
        # Consistency contribution (0-10)
        if performance.consistency_score >= 75:
            score += 10
        elif performance.consistency_score >= 50:
            score += 5
        elif performance.consistency_score < 30:
            score -= 5
        
        return max(0, min(100, score))
    
    def calculate_performance(
        self,
        strategy_id: str,
        strategy_name: str,
        trades: List[Dict[str, Any]],
        evaluation_days: int = 30
    ) -> StrategyPerformance:
        """Calculate performance metrics from trade history"""
        
        perf = StrategyPerformance(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            evaluation_period_days=evaluation_days,
            computed_at=int(time.time() * 1000)
        )
        
        if not trades:
            perf.grade = PerformanceGrade.AVERAGE
            return perf
        
        perf.total_trades = len(trades)
        
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) <= 0]
        
        perf.winning_trades = len(wins)
        perf.losing_trades = len(losses)
        
        # Returns
        perf.total_pnl = sum(t.get("pnl", 0) for t in trades)
        perf.gross_profit = sum(t.get("pnl", 0) for t in wins) if wins else 0
        perf.gross_loss = abs(sum(t.get("pnl", 0) for t in losses)) if losses else 0
        
        # Ratios
        if perf.total_trades > 0:
            perf.win_rate = (perf.winning_trades / perf.total_trades) * 100
        
        if perf.gross_loss > 0:
            perf.profit_factor = perf.gross_profit / perf.gross_loss
        elif perf.gross_profit > 0:
            perf.profit_factor = 10.0  # Cap at 10
        
        if perf.total_trades > 0:
            perf.expectancy = perf.total_pnl / perf.total_trades
        
        # Averages
        if wins:
            perf.avg_win = perf.gross_profit / len(wins)
        if losses:
            perf.avg_loss = perf.gross_loss / len(losses)
        
        if perf.avg_loss > 0:
            perf.risk_reward = perf.avg_win / perf.avg_loss
        
        # Drawdown (simplified)
        equity = 0
        max_equity = 0
        max_dd = 0
        for t in trades:
            equity += t.get("pnl", 0)
            max_equity = max(max_equity, equity)
            dd = (max_equity - equity) / max(1, max_equity) * 100 if max_equity > 0 else 0
            max_dd = max(max_dd, dd)
        perf.max_drawdown = max_dd
        
        # Duration
        durations = [t.get("duration_hours", 0) for t in trades if t.get("duration_hours")]
        if durations:
            perf.avg_trade_duration = sum(durations) / len(durations)
        
        # Consistency score
        perf.consistency_score = self._calculate_consistency(trades)
        
        # Sharpe ratio (simplified)
        if trades:
            returns = [t.get("pnl_pct", 0) for t in trades]
            if returns:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std = variance ** 0.5 if variance > 0 else 0.01
                perf.sharpe_ratio = (avg_return / std) * (252 ** 0.5) if std > 0 else 0
        
        # Grade
        perf.grade = self._grade_performance(perf)
        
        # Last trade
        if trades:
            perf.last_trade_at = max(t.get("closed_at", 0) for t in trades)
        
        return perf
    
    def _calculate_consistency(self, trades: List[Dict]) -> float:
        """Calculate consistency score"""
        if len(trades) < 5:
            return 50.0
        
        # Win/loss streaks
        max_win_streak = 0
        max_loss_streak = 0
        current_streak = 0
        
        for t in trades:
            if t.get("pnl", 0) > 0:
                if current_streak > 0:
                    current_streak += 1
                else:
                    current_streak = 1
                max_win_streak = max(max_win_streak, current_streak)
            else:
                if current_streak < 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                max_loss_streak = max(max_loss_streak, abs(current_streak))
        
        # Score based on streaks
        score = 60
        
        if max_win_streak >= 5:
            score += 15
        elif max_win_streak >= 3:
            score += 10
        
        if max_loss_streak >= 5:
            score -= 20
        elif max_loss_streak >= 3:
            score -= 10
        
        # PnL variance
        pnls = [t.get("pnl", 0) for t in trades]
        avg_pnl = sum(pnls) / len(pnls)
        variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls)
        
        if variance < avg_pnl ** 2 * 2:
            score += 10  # Low variance
        elif variance > avg_pnl ** 2 * 10:
            score -= 10  # High variance
        
        return max(0, min(100, score))
    
    def _grade_performance(self, perf: StrategyPerformance) -> PerformanceGrade:
        """Grade strategy performance"""
        
        points = 0
        
        # Win rate
        if perf.win_rate >= 60:
            points += 2
        elif perf.win_rate >= 50:
            points += 1
        elif perf.win_rate < 40:
            points -= 2
        
        # Profit factor
        if perf.profit_factor >= 2.5:
            points += 3
        elif perf.profit_factor >= 2.0:
            points += 2
        elif perf.profit_factor >= 1.5:
            points += 1
        elif perf.profit_factor < 1.0:
            points -= 3
        
        # Drawdown
        if perf.max_drawdown <= 10:
            points += 2
        elif perf.max_drawdown <= 20:
            points += 1
        elif perf.max_drawdown > 30:
            points -= 2
        
        # Consistency
        if perf.consistency_score >= 70:
            points += 2
        elif perf.consistency_score >= 50:
            points += 1
        elif perf.consistency_score < 30:
            points -= 1
        
        # Grade
        if points >= 6:
            return PerformanceGrade.EXCELLENT
        elif points >= 4:
            return PerformanceGrade.GOOD
        elif points >= 2:
            return PerformanceGrade.AVERAGE
        elif points >= 0:
            return PerformanceGrade.BELOW
        else:
            return PerformanceGrade.POOR
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "CapitalEfficiencyEngine",
            "version": "1.0.0",
            "phase": "3.4",
            "status": "active",
            "benchmark": self._benchmark,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
capital_efficiency_engine = CapitalEfficiencyEngine()
