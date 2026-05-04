"""
Performance Aggregator (STR4)
=============================

Aggregates performance metrics from various sources.

Metrics:
- PnL (daily, weekly, monthly)
- Win rate
- Profit factor
- Trade counts
- Expectancy
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .diagnostics_types import PerformanceSummary


class PerformanceAggregator:
    """
    Aggregates performance metrics.
    
    Collects data from:
    - Trade history
    - Position manager
    - Metrics engine
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Cache for performance data
        self._trades_cache: List[Dict[str, Any]] = []
        self._last_update: Optional[datetime] = None
        
        # Simulated baseline performance (for demo)
        self._baseline_pnl = 0.0
        
        self._initialized = True
        print("[PerformanceAggregator] Initialized")
    
    # ===========================================
    # Main Aggregation
    # ===========================================
    
    def get_performance_summary(
        self,
        trades: Optional[List[Dict[str, Any]]] = None
    ) -> PerformanceSummary:
        """
        Get aggregated performance summary.
        
        Args:
            trades: Optional list of trade records
        
        Returns:
            PerformanceSummary with all metrics
        """
        if trades:
            self._trades_cache = trades
            self._last_update = datetime.now(timezone.utc)
        
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        
        # Filter trades by period
        trades_today = self._filter_trades_by_date(self._trades_cache, today_start)
        trades_week = self._filter_trades_by_date(self._trades_cache, week_start)
        trades_month = self._filter_trades_by_date(self._trades_cache, month_start)
        
        # Calculate metrics
        summary = PerformanceSummary(
            daily_pnl_pct=self._calculate_pnl_pct(trades_today),
            weekly_pnl_pct=self._calculate_pnl_pct(trades_week),
            monthly_pnl_pct=self._calculate_pnl_pct(trades_month),
            total_pnl_usd=self._calculate_total_pnl(self._trades_cache),
            win_rate=self._calculate_win_rate(self._trades_cache),
            profit_factor=self._calculate_profit_factor(self._trades_cache),
            trades_today=len(trades_today),
            trades_this_week=len(trades_week),
            expectancy=self._calculate_expectancy(self._trades_cache)
        )
        
        # Recent trade info
        if self._trades_cache:
            last_trade = max(self._trades_cache, key=lambda t: t.get("closed_at", ""))
            summary.last_trade_pnl_pct = last_trade.get("pnl_pct", 0.0)
            if last_trade.get("closed_at"):
                try:
                    summary.last_trade_at = datetime.fromisoformat(
                        last_trade["closed_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass
        
        # Extremes
        if self._trades_cache:
            pnl_values = [t.get("pnl_pct", 0.0) for t in self._trades_cache]
            summary.best_trade_pct = max(pnl_values) if pnl_values else 0.0
            summary.worst_trade_pct = min(pnl_values) if pnl_values else 0.0
            
            wins = [t.get("pnl_pct", 0.0) for t in self._trades_cache if t.get("pnl_pct", 0) > 0]
            losses = [t.get("pnl_pct", 0.0) for t in self._trades_cache if t.get("pnl_pct", 0) < 0]
            
            summary.avg_win_pct = sum(wins) / len(wins) if wins else 0.0
            summary.avg_loss_pct = sum(losses) / len(losses) if losses else 0.0
        
        return summary
    
    # ===========================================
    # Calculation Methods
    # ===========================================
    
    def _filter_trades_by_date(
        self, 
        trades: List[Dict[str, Any]], 
        start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Filter trades after a given date"""
        filtered = []
        for trade in trades:
            closed_at = trade.get("closed_at")
            if closed_at:
                try:
                    trade_date = datetime.fromisoformat(
                        closed_at.replace("Z", "+00:00")
                    )
                    if trade_date >= start_date:
                        filtered.append(trade)
                except (ValueError, TypeError):
                    pass
        return filtered
    
    def _calculate_pnl_pct(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate total PnL percentage for trades"""
        if not trades:
            return 0.0
        return sum(t.get("pnl_pct", 0.0) for t in trades)
    
    def _calculate_total_pnl(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate total PnL in USD"""
        if not trades:
            return 0.0
        return sum(t.get("pnl_usd", 0.0) for t in trades)
    
    def _calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate win rate"""
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get("pnl_pct", 0) > 0)
        return wins / len(trades)
    
    def _calculate_profit_factor(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        if not trades:
            return 0.0
        
        gross_profit = sum(
            t.get("pnl_pct", 0.0) 
            for t in trades 
            if t.get("pnl_pct", 0) > 0
        )
        gross_loss = abs(sum(
            t.get("pnl_pct", 0.0) 
            for t in trades 
            if t.get("pnl_pct", 0) < 0
        ))
        
        if gross_loss == 0:
            return gross_profit * 10 if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def _calculate_expectancy(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate trade expectancy"""
        if not trades:
            return 0.0
        
        win_rate = self._calculate_win_rate(trades)
        
        wins = [t.get("pnl_pct", 0.0) for t in trades if t.get("pnl_pct", 0) > 0]
        losses = [abs(t.get("pnl_pct", 0.0)) for t in trades if t.get("pnl_pct", 0) < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    # ===========================================
    # Data Management
    # ===========================================
    
    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Add a trade to the cache"""
        self._trades_cache.append(trade)
        self._last_update = datetime.now(timezone.utc)
        
        # Keep last 1000 trades
        if len(self._trades_cache) > 1000:
            self._trades_cache = self._trades_cache[-1000:]
    
    def set_trades(self, trades: List[Dict[str, Any]]) -> None:
        """Set trades cache"""
        self._trades_cache = trades
        self._last_update = datetime.now(timezone.utc)
    
    def get_consecutive_losses(self) -> int:
        """Get current consecutive losses count"""
        if not self._trades_cache:
            return 0
        
        # Sort by date descending
        sorted_trades = sorted(
            self._trades_cache, 
            key=lambda t: t.get("closed_at", ""),
            reverse=True
        )
        
        count = 0
        for trade in sorted_trades:
            if trade.get("pnl_pct", 0) < 0:
                count += 1
            else:
                break
        
        return count
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get aggregator health"""
        return {
            "service": "PerformanceAggregator",
            "status": "healthy",
            "version": "str4",
            "trades_in_cache": len(self._trades_cache),
            "last_update": self._last_update.isoformat() if self._last_update else None
        }


# Global singleton
performance_aggregator = PerformanceAggregator()
