"""
Strategy Types (STG1)
=====================

Type definitions for Strategy Taxonomy.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class StrategyType(Enum):
    """Base strategy types"""
    TREND_CONFIRMATION = "TREND_CONFIRMATION"
    MOMENTUM_BREAKOUT = "MOMENTUM_BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "TRENDING"
    RANGE = "RANGE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    TRANSITION = "TRANSITION"


class ProfileType(Enum):
    """Trading profile types"""
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class ExitReason(Enum):
    """Exit reason types"""
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_EXIT = "TIME_EXIT"
    STRUCTURE_BREAK = "STRUCTURE_BREAK"
    INVALIDATION = "INVALIDATION"
    MANUAL_EXIT = "MANUAL_EXIT"
    KILL_SWITCH = "KILL_SWITCH"
    OPPOSING_SIGNAL = "OPPOSING_SIGNAL"


class ActionType(Enum):
    """Strategy action types"""
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


# ===========================================
# Model Definitions
# ===========================================

@dataclass
class EntryModel:
    """Entry conditions model"""
    signal_threshold: float = 0.65
    min_confidence: float = 0.5
    confirmation_filters: List[str] = field(default_factory=lambda: ["trend", "structure"])
    max_entries_per_day: int = 5
    require_structure_alignment: bool = True
    require_momentum_confirmation: bool = False
    require_volume_confirmation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signalThreshold": self.signal_threshold,
            "minConfidence": self.min_confidence,
            "confirmationFilters": self.confirmation_filters,
            "maxEntriesPerDay": self.max_entries_per_day,
            "requireStructureAlignment": self.require_structure_alignment,
            "requireMomentumConfirmation": self.require_momentum_confirmation,
            "requireVolumeConfirmation": self.require_volume_confirmation
        }


@dataclass
class ExitModel:
    """Exit conditions model"""
    take_profit_pct: float = 0.04
    stop_loss_pct: float = 0.015
    trailing_stop_enabled: bool = False
    trailing_stop_pct: float = 0.02
    max_holding_bars: int = 48
    time_exit_enabled: bool = True
    exit_on_structure_break: bool = True
    exit_on_opposing_signal: bool = True
    opposing_signal_threshold: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "takeProfitPct": self.take_profit_pct,
            "stopLossPct": self.stop_loss_pct,
            "trailingStopEnabled": self.trailing_stop_enabled,
            "trailingStopPct": self.trailing_stop_pct,
            "maxHoldingBars": self.max_holding_bars,
            "timeExitEnabled": self.time_exit_enabled,
            "exitOnStructureBreak": self.exit_on_structure_break,
            "exitOnOpposingSignal": self.exit_on_opposing_signal,
            "opposingSignalThreshold": self.opposing_signal_threshold
        }


@dataclass
class RiskModel:
    """Risk parameters model"""
    max_position_size_pct: float = 0.05
    max_leverage: float = 3.0
    max_scaling_depth: int = 2
    max_risk_per_trade_pct: float = 0.02
    max_daily_loss_pct: float = 0.05
    max_correlated_positions: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "maxPositionSizePct": self.max_position_size_pct,
            "maxLeverage": self.max_leverage,
            "maxScalingDepth": self.max_scaling_depth,
            "maxRiskPerTradePct": self.max_risk_per_trade_pct,
            "maxDailyLossPct": self.max_daily_loss_pct,
            "maxCorrelatedPositions": self.max_correlated_positions
        }


# ===========================================
# Strategy Definition
# ===========================================

@dataclass
class StrategyDefinition:
    """
    Complete strategy definition.
    
    Defines everything about how a strategy operates.
    """
    strategy_id: str = field(default_factory=lambda: f"strat_{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    strategy_type: StrategyType = StrategyType.TREND_CONFIRMATION
    
    # Market compatibility
    compatible_regimes: List[MarketRegime] = field(default_factory=list)
    hostile_regimes: List[MarketRegime] = field(default_factory=list)
    
    # Profile compatibility
    compatible_profiles: List[ProfileType] = field(default_factory=list)
    
    # Trading models
    entry_model: EntryModel = field(default_factory=EntryModel)
    exit_model: ExitModel = field(default_factory=ExitModel)
    risk_model: RiskModel = field(default_factory=RiskModel)
    
    # Asset compatibility
    allowed_assets: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    spot_compatible: bool = True
    futures_compatible: bool = True
    
    # State
    enabled: bool = True
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "strategyType": self.strategy_type.value,
            "compatibleRegimes": [r.value for r in self.compatible_regimes],
            "hostileRegimes": [r.value for r in self.hostile_regimes],
            "compatibleProfiles": [p.value for p in self.compatible_profiles],
            "entryModel": self.entry_model.to_dict(),
            "exitModel": self.exit_model.to_dict(),
            "riskModel": self.risk_model.to_dict(),
            "allowedAssets": self.allowed_assets,
            "spotCompatible": self.spot_compatible,
            "futuresCompatible": self.futures_compatible,
            "enabled": self.enabled,
            "version": self.version,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_compatible_with_regime(self, regime: MarketRegime) -> bool:
        """Check if strategy is compatible with market regime"""
        if regime in self.hostile_regimes:
            return False
        return regime in self.compatible_regimes
    
    def is_compatible_with_profile(self, profile: ProfileType) -> bool:
        """Check if strategy is compatible with profile"""
        return profile in self.compatible_profiles


# ===========================================
# Strategy Statistics (for STG3 integration)
# ===========================================

@dataclass
class StrategyStats:
    """Statistics for a strategy"""
    strategy_id: str = ""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_pnl_pct: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_holding_bars: float = 0.0
    max_winning_streak: int = 0
    max_losing_streak: int = 0
    sharpe_ratio: float = 0.0
    
    # Recent performance
    trades_7d: int = 0
    win_rate_7d: float = 0.0
    pnl_7d_pct: float = 0.0
    trades_30d: int = 0
    win_rate_30d: float = 0.0
    pnl_30d_pct: float = 0.0
    
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "totalTrades": self.total_trades,
            "winningTrades": self.winning_trades,
            "losingTrades": self.losing_trades,
            "winRate": round(self.win_rate, 4),
            "avgPnlPct": round(self.avg_pnl_pct, 4),
            "profitFactor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 4),
            "maxDrawdownPct": round(self.max_drawdown_pct, 4),
            "avgHoldingBars": round(self.avg_holding_bars, 1),
            "maxWinningStreak": self.max_winning_streak,
            "maxLosingStreak": self.max_losing_streak,
            "sharpeRatio": round(self.sharpe_ratio, 2),
            "recent": {
                "trades7d": self.trades_7d,
                "winRate7d": round(self.win_rate_7d, 4),
                "pnl7d": round(self.pnl_7d_pct, 4),
                "trades30d": self.trades_30d,
                "winRate30d": round(self.win_rate_30d, 4),
                "pnl30d": round(self.pnl_30d_pct, 4)
            },
            "lastUpdated": self.last_updated.isoformat() if self.last_updated else None
        }
