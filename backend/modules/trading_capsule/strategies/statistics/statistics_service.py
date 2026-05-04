"""
Strategy Statistics Service (STG3)
==================================

Main service for computing and managing strategy statistics.
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics as stats_lib
import uuid

from .statistics_types import (
    StrategyStatisticsSnapshot,
    StrategyDecisionStatistics,
    StrategyProfileStatistics,
    StrategySymbolStatistics,
    StrategyRegimeStatistics,
    TradeRecord,
    DecisionRecord
)


class StatisticsService:
    """
    Strategy Statistics Service.
    
    Computes statistics at multiple levels:
    - Strategy level (overall)
    - Profile level (per profile)
    - Symbol level (per symbol)
    - Regime level (per market regime)
    - Decision level (action distribution)
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
        
        # Trade history storage (in-memory for now, could be MongoDB)
        self._trades: Dict[str, List[TradeRecord]] = defaultdict(list)
        
        # Decision history storage
        self._decisions: Dict[str, List[DecisionRecord]] = defaultdict(list)
        
        # Cached statistics
        self._snapshots: Dict[str, StrategyStatisticsSnapshot] = {}
        self._decision_stats: Dict[str, StrategyDecisionStatistics] = {}
        self._profile_stats: Dict[str, Dict[str, StrategyProfileStatistics]] = defaultdict(dict)
        self._symbol_stats: Dict[str, Dict[str, StrategySymbolStatistics]] = defaultdict(dict)
        self._regime_stats: Dict[str, Dict[str, StrategyRegimeStatistics]] = defaultdict(dict)
        
        self._initialized = True
        print("[StatisticsService] Initialized (STG3)")
    
    # ===========================================
    # Trade Recording
    # ===========================================
    
    def record_trade(self, trade: TradeRecord):
        """Record a completed trade"""
        self._trades[trade.strategy_id].append(trade)
        
        # Trigger recalculation
        self._recalculate_strategy_stats(trade.strategy_id)
    
    def record_trade_from_dict(self, data: Dict[str, Any]) -> TradeRecord:
        """Record trade from dictionary data"""
        trade = TradeRecord(
            trade_id=data.get("trade_id", f"trade_{uuid.uuid4().hex[:8]}"),
            strategy_id=data.get("strategy_id", ""),
            symbol=data.get("symbol", ""),
            profile_id=data.get("profile_id", "BALANCED"),
            regime=data.get("regime", "TRENDING"),
            side=data.get("side", "LONG"),
            entry_price=data.get("entry_price", 0),
            exit_price=data.get("exit_price", 0),
            size=data.get("size", 0),
            pnl=data.get("pnl", 0),
            pnl_pct=data.get("pnl_pct", 0),
            is_winner=data.get("pnl", 0) > 0,
            entry_reason=data.get("entry_reason", ""),
            exit_reason=data.get("exit_reason", ""),
            hold_bars=data.get("hold_bars", 0),
            hold_minutes=data.get("hold_minutes", 0),
            entry_time=data.get("entry_time"),
            exit_time=data.get("exit_time") or datetime.now(timezone.utc)
        )
        
        self.record_trade(trade)
        return trade
    
    # ===========================================
    # Decision Recording
    # ===========================================
    
    def record_decision(self, decision: DecisionRecord):
        """Record a strategy decision"""
        self._decisions[decision.strategy_id].append(decision)
        
        # Limit history
        if len(self._decisions[decision.strategy_id]) > 10000:
            self._decisions[decision.strategy_id] = self._decisions[decision.strategy_id][-5000:]
    
    def record_decision_from_dict(self, data: Dict[str, Any]) -> DecisionRecord:
        """Record decision from dictionary data"""
        decision = DecisionRecord(
            decision_id=data.get("decision_id", f"dec_{uuid.uuid4().hex[:8]}"),
            strategy_id=data.get("strategy_id", ""),
            symbol=data.get("symbol", ""),
            profile_id=data.get("profile_id", "BALANCED"),
            regime=data.get("regime", "TRENDING"),
            action=data.get("action", "HOLD"),
            reason=data.get("reason", ""),
            signal_score=data.get("signal_score", 0),
            confidence=data.get("confidence", 0),
            filters_passed=data.get("filters_passed", []),
            filters_blocked=data.get("filters_blocked", []),
            risk_veto=data.get("risk_veto", False)
        )
        
        self.record_decision(decision)
        return decision
    
    # ===========================================
    # Statistics Calculation
    # ===========================================
    
    def _recalculate_strategy_stats(self, strategy_id: str):
        """Recalculate all statistics for a strategy"""
        trades = self._trades.get(strategy_id, [])
        
        if not trades:
            return
        
        # Core statistics
        snapshot = self._calculate_core_stats(strategy_id, trades)
        self._snapshots[strategy_id] = snapshot
        
        # Profile statistics
        profile_trades = defaultdict(list)
        for t in trades:
            profile_trades[t.profile_id].append(t)
        
        for profile_id, ptrades in profile_trades.items():
            self._profile_stats[strategy_id][profile_id] = self._calculate_profile_stats(strategy_id, profile_id, ptrades)
        
        # Symbol statistics
        symbol_trades = defaultdict(list)
        for t in trades:
            symbol_trades[t.symbol].append(t)
        
        for symbol, strades in symbol_trades.items():
            self._symbol_stats[strategy_id][symbol] = self._calculate_symbol_stats(strategy_id, symbol, strades)
        
        # Regime statistics
        regime_trades = defaultdict(list)
        for t in trades:
            regime_trades[t.regime].append(t)
        
        for regime, rtrades in regime_trades.items():
            self._regime_stats[strategy_id][regime] = self._calculate_regime_stats(strategy_id, regime, rtrades)
    
    def _calculate_core_stats(self, strategy_id: str, trades: List[TradeRecord]) -> StrategyStatisticsSnapshot:
        """Calculate core strategy statistics"""
        if not trades:
            return StrategyStatisticsSnapshot(strategy_id=strategy_id)
        
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        total = len(trades)
        winning = len(winners)
        losing = len(losers)
        
        win_rate = winning / total if total > 0 else 0
        
        # PnL
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        avg_win = sum(t.pnl for t in winners) / winning if winning > 0 else 0
        avg_loss = sum(t.pnl for t in losers) / losing if losing > 0 else 0
        
        # Expectancy: (Win% × AvgWin) - (Loss% × AvgLoss)
        expectancy = (win_rate * abs(avg_win)) - ((1 - win_rate) * abs(avg_loss))
        
        # Profit factor: gross profit / gross loss
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        # Drawdown
        equity_curve = []
        running = 0
        for t in trades:
            running += t.pnl
            equity_curve.append(running)
        
        max_drawdown = 0
        peak = 0
        drawdowns = []
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            drawdowns.append(dd)
            if dd > max_drawdown:
                max_drawdown = dd
        
        avg_drawdown = sum(drawdowns) / len(drawdowns) if drawdowns else 0
        
        # Hold time
        hold_bars = [t.hold_bars for t in trades if t.hold_bars > 0]
        hold_minutes = [t.hold_minutes for t in trades if t.hold_minutes > 0]
        
        avg_hold_bars = sum(hold_bars) / len(hold_bars) if hold_bars else 0
        avg_hold_minutes = sum(hold_minutes) / len(hold_minutes) if hold_minutes else 0
        median_hold_bars = stats_lib.median(hold_bars) if hold_bars else 0
        
        # Streaks
        max_winning, max_losing, current, current_type = self._calculate_streaks(trades)
        
        # Recent stats
        now = datetime.now(timezone.utc)
        trades_7d = [t for t in trades if t.exit_time and (now - t.exit_time).days <= 7]
        trades_30d = [t for t in trades if t.exit_time and (now - t.exit_time).days <= 30]
        
        win_rate_7d = len([t for t in trades_7d if t.is_winner]) / len(trades_7d) if trades_7d else 0
        pnl_7d = sum(t.pnl for t in trades_7d)
        
        win_rate_30d = len([t for t in trades_30d if t.is_winner]) / len(trades_30d) if trades_30d else 0
        pnl_30d = sum(t.pnl for t in trades_30d)
        
        return StrategyStatisticsSnapshot(
            strategy_id=strategy_id,
            total_trades=total,
            winning_trades=winning,
            losing_trades=losing,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            profit_factor=min(profit_factor, 99.99),
            max_drawdown=max_drawdown,
            avg_drawdown=avg_drawdown,
            avg_hold_bars=avg_hold_bars,
            avg_hold_minutes=avg_hold_minutes,
            median_hold_bars=median_hold_bars,
            max_winning_streak=max_winning,
            max_losing_streak=max_losing,
            current_streak=current,
            current_streak_type=current_type,
            trades_7d=len(trades_7d),
            win_rate_7d=win_rate_7d,
            pnl_7d=pnl_7d,
            trades_30d=len(trades_30d),
            win_rate_30d=win_rate_30d,
            pnl_30d=pnl_30d
        )
    
    def _calculate_streaks(self, trades: List[TradeRecord]):
        """Calculate winning/losing streaks"""
        if not trades:
            return 0, 0, 0, ""
        
        max_winning = 0
        max_losing = 0
        current = 0
        current_type = ""
        
        streak = 0
        last_win = None
        
        for t in trades:
            if t.is_winner:
                if last_win:
                    streak += 1
                else:
                    streak = 1
                last_win = True
                if streak > max_winning:
                    max_winning = streak
            else:
                if not last_win and last_win is not None:
                    streak += 1
                else:
                    streak = 1
                last_win = False
                if streak > max_losing:
                    max_losing = streak
        
        current = streak
        current_type = "WIN" if last_win else "LOSS"
        
        return max_winning, max_losing, current, current_type
    
    def _calculate_profile_stats(self, strategy_id: str, profile_id: str, trades: List[TradeRecord]) -> StrategyProfileStatistics:
        """Calculate statistics for strategy × profile"""
        if not trades:
            return StrategyProfileStatistics(strategy_id=strategy_id, profile_id=profile_id)
        
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        total = len(trades)
        winning = len(winners)
        losing = len(losers)
        
        win_rate = winning / total if total > 0 else 0
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        avg_win = sum(t.pnl for t in winners) / winning if winning > 0 else 0
        avg_loss = sum(t.pnl for t in losers) / losing if losing > 0 else 0
        
        expectancy = (win_rate * abs(avg_win)) - ((1 - win_rate) * abs(avg_loss))
        
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Simplified drawdown
        equity_curve = []
        running = 0
        for t in trades:
            running += t.pnl
            equity_curve.append(running)
        
        max_drawdown = 0
        peak = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd
        
        avg_hold_bars = sum(t.hold_bars for t in trades) / total if total > 0 else 0
        
        return StrategyProfileStatistics(
            strategy_id=strategy_id,
            profile_id=profile_id,
            total_trades=total,
            winning_trades=winning,
            losing_trades=losing,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            expectancy=expectancy,
            profit_factor=min(profit_factor, 99.99),
            max_drawdown=max_drawdown,
            avg_hold_bars=avg_hold_bars
        )
    
    def _calculate_symbol_stats(self, strategy_id: str, symbol: str, trades: List[TradeRecord]) -> StrategySymbolStatistics:
        """Calculate statistics for strategy × symbol"""
        if not trades:
            return StrategySymbolStatistics(strategy_id=strategy_id, symbol=symbol)
        
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        total = len(trades)
        winning = len(winners)
        losing = len(losers)
        
        win_rate = winning / total if total > 0 else 0
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        avg_win = sum(t.pnl for t in winners) / winning if winning > 0 else 0
        avg_loss = sum(t.pnl for t in losers) / losing if losing > 0 else 0
        
        expectancy = (win_rate * abs(avg_win)) - ((1 - win_rate) * abs(avg_loss))
        
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Simplified drawdown
        equity_curve = []
        running = 0
        for t in trades:
            running += t.pnl
            equity_curve.append(running)
        
        max_drawdown = 0
        peak = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd
        
        avg_hold_bars = sum(t.hold_bars for t in trades) / total if total > 0 else 0
        
        return StrategySymbolStatistics(
            strategy_id=strategy_id,
            symbol=symbol,
            total_trades=total,
            winning_trades=winning,
            losing_trades=losing,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            expectancy=expectancy,
            profit_factor=min(profit_factor, 99.99),
            max_drawdown=max_drawdown,
            avg_hold_bars=avg_hold_bars
        )
    
    def _calculate_regime_stats(self, strategy_id: str, regime: str, trades: List[TradeRecord]) -> StrategyRegimeStatistics:
        """Calculate statistics for strategy × regime"""
        if not trades:
            return StrategyRegimeStatistics(strategy_id=strategy_id, regime=regime)
        
        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if not t.is_winner]
        
        total = len(trades)
        winning = len(winners)
        losing = len(losers)
        
        win_rate = winning / total if total > 0 else 0
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        avg_win = sum(t.pnl for t in winners) / winning if winning > 0 else 0
        avg_loss = sum(t.pnl for t in losers) / losing if losing > 0 else 0
        
        expectancy = (win_rate * abs(avg_win)) - ((1 - win_rate) * abs(avg_loss))
        
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Regime compatibility score based on performance
        score = 0.5  # neutral
        if profit_factor > 1.5 and win_rate > 0.5:
            score = 0.8
        elif profit_factor > 1.0 and win_rate > 0.45:
            score = 0.6
        elif profit_factor < 0.8 or win_rate < 0.35:
            score = 0.2
        
        return StrategyRegimeStatistics(
            strategy_id=strategy_id,
            regime=regime,
            total_trades=total,
            winning_trades=winning,
            losing_trades=losing,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            expectancy=expectancy,
            profit_factor=min(profit_factor, 99.99),
            regime_compatibility_score=score
        )
    
    def calculate_decision_stats(self, strategy_id: str) -> StrategyDecisionStatistics:
        """Calculate decision-level statistics"""
        decisions = self._decisions.get(strategy_id, [])
        
        if not decisions:
            return StrategyDecisionStatistics(strategy_id=strategy_id)
        
        total = len(decisions)
        
        # Action counts
        enter_long = len([d for d in decisions if d.action == "ENTER_LONG"])
        enter_short = len([d for d in decisions if d.action == "ENTER_SHORT"])
        exit_count = len([d for d in decisions if d.action == "EXIT"])
        hold_count = len([d for d in decisions if d.action == "HOLD"])
        block_count = len([d for d in decisions if d.action == "BLOCK"])
        
        # Rates
        entry_rate = (enter_long + enter_short) / total if total > 0 else 0
        block_rate = block_count / total if total > 0 else 0
        hold_rate = hold_count / total if total > 0 else 0
        
        # Top reasons
        block_reasons = defaultdict(int)
        exit_reasons = defaultdict(int)
        entry_reasons = defaultdict(int)
        
        for d in decisions:
            if d.action == "BLOCK":
                block_reasons[d.reason] += 1
            elif d.action == "EXIT":
                exit_reasons[d.reason] += 1
            elif d.action.startswith("ENTER"):
                entry_reasons[d.reason] += 1
        
        # Sort and limit
        top_block = dict(sorted(block_reasons.items(), key=lambda x: x[1], reverse=True)[:5])
        top_exit = dict(sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True)[:5])
        top_entry = dict(sorted(entry_reasons.items(), key=lambda x: x[1], reverse=True)[:5])
        
        stats = StrategyDecisionStatistics(
            strategy_id=strategy_id,
            enter_long_count=enter_long,
            enter_short_count=enter_short,
            exit_count=exit_count,
            hold_count=hold_count,
            block_count=block_count,
            entry_rate=entry_rate,
            block_rate=block_rate,
            hold_rate=hold_rate,
            top_block_reasons=top_block,
            top_exit_reasons=top_exit,
            top_entry_reasons=top_entry,
            total_decisions=total
        )
        
        self._decision_stats[strategy_id] = stats
        return stats
    
    # ===========================================
    # Getters
    # ===========================================
    
    def get_statistics(self, strategy_id: str) -> Optional[StrategyStatisticsSnapshot]:
        """Get strategy statistics snapshot"""
        return self._snapshots.get(strategy_id)
    
    def get_decision_statistics(self, strategy_id: str) -> Optional[StrategyDecisionStatistics]:
        """Get decision statistics"""
        if strategy_id not in self._decision_stats:
            return self.calculate_decision_stats(strategy_id)
        return self._decision_stats.get(strategy_id)
    
    def get_profile_statistics(self, strategy_id: str) -> Dict[str, StrategyProfileStatistics]:
        """Get all profile statistics for strategy"""
        return dict(self._profile_stats.get(strategy_id, {}))
    
    def get_profile_stat(self, strategy_id: str, profile_id: str) -> Optional[StrategyProfileStatistics]:
        """Get specific profile statistics"""
        return self._profile_stats.get(strategy_id, {}).get(profile_id)
    
    def get_symbol_statistics(self, strategy_id: str) -> Dict[str, StrategySymbolStatistics]:
        """Get all symbol statistics for strategy"""
        return dict(self._symbol_stats.get(strategy_id, {}))
    
    def get_symbol_stat(self, strategy_id: str, symbol: str) -> Optional[StrategySymbolStatistics]:
        """Get specific symbol statistics"""
        return self._symbol_stats.get(strategy_id, {}).get(symbol)
    
    def get_regime_statistics(self, strategy_id: str) -> Dict[str, StrategyRegimeStatistics]:
        """Get all regime statistics for strategy"""
        return dict(self._regime_stats.get(strategy_id, {}))
    
    def get_regime_stat(self, strategy_id: str, regime: str) -> Optional[StrategyRegimeStatistics]:
        """Get specific regime statistics"""
        return self._regime_stats.get(strategy_id, {}).get(regime)
    
    def get_trades(self, strategy_id: str, limit: int = 100) -> List[TradeRecord]:
        """Get trade history"""
        trades = self._trades.get(strategy_id, [])
        return trades[-limit:]
    
    def get_all_statistics_summary(self) -> Dict[str, Any]:
        """Get summary of all strategies"""
        summaries = []
        for strategy_id, snapshot in self._snapshots.items():
            summaries.append({
                "strategyId": strategy_id,
                "totalTrades": snapshot.total_trades,
                "winRate": round(snapshot.win_rate, 4),
                "profitFactor": round(snapshot.profit_factor, 2),
                "expectancy": round(snapshot.expectancy, 4)
            })
        
        return {
            "strategies": summaries,
            "count": len(summaries)
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "Strategy Statistics Layer",
            "phase": "STG3",
            "status": "healthy",
            "strategiesTracked": len(self._trades),
            "totalTrades": sum(len(t) for t in self._trades.values()),
            "totalDecisions": sum(len(d) for d in self._decisions.values()),
            "snapshotsGenerated": len(self._snapshots)
        }


# Global singleton
statistics_service = StatisticsService()
