"""
Strategy Statistics Types (STG3)
================================

Type definitions for Strategy Statistics Layer.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Core Statistics
# ===========================================

@dataclass
class StrategyStatisticsSnapshot:
    """Complete statistics snapshot for a strategy"""
    snapshot_id: str = field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:8]}")
    strategy_id: str = ""
    
    # Core metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # PnL metrics
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    
    # Time metrics
    avg_hold_bars: float = 0.0
    avg_hold_minutes: float = 0.0
    median_hold_bars: float = 0.0
    
    # Streak metrics
    max_winning_streak: int = 0
    max_losing_streak: int = 0
    current_streak: int = 0
    current_streak_type: str = ""  # WIN / LOSS
    
    # Recent performance
    trades_7d: int = 0
    win_rate_7d: float = 0.0
    pnl_7d: float = 0.0
    trades_30d: int = 0
    win_rate_30d: float = 0.0
    pnl_30d: float = 0.0
    
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshotId": self.snapshot_id,
            "strategyId": self.strategy_id,
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "winRate": round(self.win_rate, 4)
            },
            "pnl": {
                "total": round(self.total_pnl, 2),
                "avg": round(self.avg_pnl, 4),
                "avgWin": round(self.avg_win, 4),
                "avgLoss": round(self.avg_loss, 4),
                "expectancy": round(self.expectancy, 4),
                "profitFactor": round(self.profit_factor, 2)
            },
            "risk": {
                "maxDrawdown": round(self.max_drawdown, 4),
                "avgDrawdown": round(self.avg_drawdown, 4)
            },
            "holdTime": {
                "avgBars": round(self.avg_hold_bars, 1),
                "avgMinutes": round(self.avg_hold_minutes, 1),
                "medianBars": round(self.median_hold_bars, 1)
            },
            "streaks": {
                "maxWinning": self.max_winning_streak,
                "maxLosing": self.max_losing_streak,
                "current": self.current_streak,
                "currentType": self.current_streak_type
            },
            "recent": {
                "trades7d": self.trades_7d,
                "winRate7d": round(self.win_rate_7d, 4),
                "pnl7d": round(self.pnl_7d, 4),
                "trades30d": self.trades_30d,
                "winRate30d": round(self.win_rate_30d, 4),
                "pnl30d": round(self.pnl_30d, 4)
            },
            "generatedAt": self.generated_at.isoformat() if self.generated_at else None
        }


# ===========================================
# Decision Statistics
# ===========================================

@dataclass
class StrategyDecisionStatistics:
    """Decision-level statistics for a strategy"""
    strategy_id: str = ""
    
    # Action counts
    enter_long_count: int = 0
    enter_short_count: int = 0
    exit_count: int = 0
    hold_count: int = 0
    block_count: int = 0
    
    # Ratios
    entry_rate: float = 0.0
    block_rate: float = 0.0
    hold_rate: float = 0.0
    
    # Top reasons
    top_block_reasons: Dict[str, int] = field(default_factory=dict)
    top_exit_reasons: Dict[str, int] = field(default_factory=dict)
    top_entry_reasons: Dict[str, int] = field(default_factory=dict)
    
    total_decisions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "actions": {
                "enterLong": self.enter_long_count,
                "enterShort": self.enter_short_count,
                "exit": self.exit_count,
                "hold": self.hold_count,
                "block": self.block_count
            },
            "rates": {
                "entryRate": round(self.entry_rate, 4),
                "blockRate": round(self.block_rate, 4),
                "holdRate": round(self.hold_rate, 4)
            },
            "topReasons": {
                "block": self.top_block_reasons,
                "exit": self.top_exit_reasons,
                "entry": self.top_entry_reasons
            },
            "totalDecisions": self.total_decisions
        }


# ===========================================
# Profile Statistics
# ===========================================

@dataclass
class StrategyProfileStatistics:
    """Statistics per profile for a strategy"""
    strategy_id: str = ""
    profile_id: str = ""
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    
    max_drawdown: float = 0.0
    avg_hold_bars: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "profileId": self.profile_id,
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "winRate": round(self.win_rate, 4)
            },
            "pnl": {
                "total": round(self.total_pnl, 2),
                "avg": round(self.avg_pnl, 4),
                "expectancy": round(self.expectancy, 4),
                "profitFactor": round(self.profit_factor, 2)
            },
            "maxDrawdown": round(self.max_drawdown, 4),
            "avgHoldBars": round(self.avg_hold_bars, 1)
        }


# ===========================================
# Symbol Statistics
# ===========================================

@dataclass
class StrategySymbolStatistics:
    """Statistics per symbol for a strategy"""
    strategy_id: str = ""
    symbol: str = ""
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    
    max_drawdown: float = 0.0
    avg_hold_bars: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "symbol": self.symbol,
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "winRate": round(self.win_rate, 4)
            },
            "pnl": {
                "total": round(self.total_pnl, 2),
                "avg": round(self.avg_pnl, 4),
                "expectancy": round(self.expectancy, 4),
                "profitFactor": round(self.profit_factor, 2)
            },
            "maxDrawdown": round(self.max_drawdown, 4),
            "avgHoldBars": round(self.avg_hold_bars, 1)
        }


# ===========================================
# Regime Statistics
# ===========================================

@dataclass
class StrategyRegimeStatistics:
    """Statistics per market regime for a strategy"""
    strategy_id: str = ""
    regime: str = ""
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    
    # How well strategy performs in this regime
    regime_compatibility_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "regime": self.regime,
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "winRate": round(self.win_rate, 4)
            },
            "pnl": {
                "total": round(self.total_pnl, 2),
                "avg": round(self.avg_pnl, 4),
                "expectancy": round(self.expectancy, 4),
                "profitFactor": round(self.profit_factor, 2)
            },
            "regimeCompatibilityScore": round(self.regime_compatibility_score, 4)
        }


# ===========================================
# Trade Record (for aggregation)
# ===========================================

@dataclass
class TradeRecord:
    """Trade record for statistics calculation"""
    trade_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    profile_id: str = ""
    regime: str = ""
    
    side: str = ""  # LONG / SHORT
    entry_price: float = 0.0
    exit_price: float = 0.0
    size: float = 0.0
    
    pnl: float = 0.0
    pnl_pct: float = 0.0
    
    is_winner: bool = False
    
    entry_reason: str = ""
    exit_reason: str = ""
    
    hold_bars: int = 0
    hold_minutes: float = 0.0
    
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "strategyId": self.strategy_id,
            "symbol": self.symbol,
            "profileId": self.profile_id,
            "regime": self.regime,
            "side": self.side,
            "entryPrice": self.entry_price,
            "exitPrice": self.exit_price,
            "size": self.size,
            "pnl": round(self.pnl, 2),
            "pnlPct": round(self.pnl_pct, 4),
            "isWinner": self.is_winner,
            "entryReason": self.entry_reason,
            "exitReason": self.exit_reason,
            "holdBars": self.hold_bars,
            "holdMinutes": round(self.hold_minutes, 1),
            "entryTime": self.entry_time.isoformat() if self.entry_time else None,
            "exitTime": self.exit_time.isoformat() if self.exit_time else None
        }


# ===========================================
# Decision Record (for decision stats)
# ===========================================

@dataclass
class DecisionRecord:
    """Decision record for statistics"""
    decision_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    profile_id: str = ""
    regime: str = ""
    
    action: str = ""  # ENTER_LONG, ENTER_SHORT, EXIT, HOLD, BLOCK
    reason: str = ""
    
    signal_score: float = 0.0
    confidence: float = 0.0
    
    filters_passed: List[str] = field(default_factory=list)
    filters_blocked: List[str] = field(default_factory=list)
    
    risk_veto: bool = False
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "strategyId": self.strategy_id,
            "symbol": self.symbol,
            "profileId": self.profile_id,
            "regime": self.regime,
            "action": self.action,
            "reason": self.reason,
            "signalScore": round(self.signal_score, 4),
            "confidence": round(self.confidence, 4),
            "filtersPassed": self.filters_passed,
            "filtersBlocked": self.filters_blocked,
            "riskVeto": self.risk_veto,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
