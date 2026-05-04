"""
Strategy Profile Types (STR1)
=============================

Type definitions for Strategy Profile Engine.

Strategy Profiles are trading modes that control:
- Risk parameters
- Position sizing
- Holding horizon
- Trade frequency
- Leverage

Profiles: CONSERVATIVE, BALANCED, AGGRESSIVE
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class ProfileMode(Enum):
    """Trading profile modes"""
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class MarketMode(Enum):
    """Market type for trading"""
    SPOT_ONLY = "SPOT_ONLY"
    SPOT_FUTURES = "SPOT_FUTURES"
    FUTURES_ONLY = "FUTURES_ONLY"


class HoldingHorizon(Enum):
    """Position holding horizon"""
    SCALP = "SCALP"           # Minutes
    INTRADAY = "INTRADAY"     # Hours
    SWING = "SWING"           # Days
    POSITION = "POSITION"     # Weeks


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# ===========================================
# Strategy Profile (STR1.1)
# ===========================================

@dataclass
class StrategyProfile:
    """
    Strategy Profile - trading mode configuration.
    
    Controls all trading parameters without changing
    the underlying strategy algorithm.
    """
    profile_id: str = field(default_factory=lambda: f"profile_{uuid.uuid4().hex[:8]}")
    
    # Identity
    name: str = ""
    mode: ProfileMode = ProfileMode.BALANCED
    description: str = ""
    
    # Market Configuration
    market_mode: MarketMode = MarketMode.SPOT_ONLY
    allowed_symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    
    # Leverage
    max_leverage: float = 1.0          # 1x = spot only
    default_leverage: float = 1.0
    
    # Signal Thresholds
    signal_threshold: float = 0.70     # Min confidence to enter
    exit_threshold: float = 0.50       # Confidence to exit
    
    # Position Sizing
    max_position_pct: float = 0.05     # Max 5% per position
    max_portfolio_exposure_pct: float = 0.20  # Max 20% total exposure
    min_position_usd: float = 100.0
    max_position_usd: float = 10000.0
    
    # Risk Limits
    max_drawdown_pct: float = 0.10     # 10% max drawdown trigger
    daily_loss_limit_pct: float = 0.03 # 3% daily loss limit
    risk_level: RiskLevel = RiskLevel.LOW
    
    # Holding Period
    holding_horizon: HoldingHorizon = HoldingHorizon.SWING
    min_holding_bars: int = 6          # Minimum bars to hold
    max_holding_bars: int = 100        # Maximum bars to hold
    
    # Trade Frequency
    max_trades_per_day: int = 5
    min_time_between_trades_minutes: int = 60
    
    # Stop Loss / Take Profit
    default_stop_loss_pct: float = 0.02   # 2% stop loss
    default_take_profit_pct: float = 0.04 # 4% take profit
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 0.01
    
    # Status
    is_active: bool = False
    is_enabled: bool = True
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_switched_at: Optional[datetime] = None
    
    # Version for optimistic locking
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "mode": self.mode.value,
            "description": self.description,
            "market": {
                "mode": self.market_mode.value,
                "allowed_symbols": self.allowed_symbols
            },
            "leverage": {
                "max": self.max_leverage,
                "default": self.default_leverage
            },
            "signals": {
                "entry_threshold": self.signal_threshold,
                "exit_threshold": self.exit_threshold
            },
            "position_sizing": {
                "max_position_pct": self.max_position_pct,
                "max_portfolio_exposure_pct": self.max_portfolio_exposure_pct,
                "min_position_usd": self.min_position_usd,
                "max_position_usd": self.max_position_usd
            },
            "risk": {
                "level": self.risk_level.value,
                "max_drawdown_pct": self.max_drawdown_pct,
                "daily_loss_limit_pct": self.daily_loss_limit_pct
            },
            "holding": {
                "horizon": self.holding_horizon.value,
                "min_bars": self.min_holding_bars,
                "max_bars": self.max_holding_bars
            },
            "frequency": {
                "max_trades_per_day": self.max_trades_per_day,
                "min_time_between_trades_minutes": self.min_time_between_trades_minutes
            },
            "stops": {
                "stop_loss_pct": self.default_stop_loss_pct,
                "take_profit_pct": self.default_take_profit_pct,
                "use_trailing": self.use_trailing_stop,
                "trailing_pct": self.trailing_stop_pct
            },
            "status": {
                "is_active": self.is_active,
                "is_enabled": self.is_enabled
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "last_switched_at": self.last_switched_at.isoformat() if self.last_switched_at else None
            },
            "version": self.version
        }


# ===========================================
# Profile Switch Event
# ===========================================

@dataclass
class ProfileSwitchEvent:
    """Event when profile is switched"""
    event_id: str = field(default_factory=lambda: f"pse_{uuid.uuid4().hex[:8]}")
    
    from_profile_id: str = ""
    to_profile_id: str = ""
    
    from_mode: str = ""
    to_mode: str = ""
    
    switched_by: str = "system"
    reason: str = ""
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "from_profile_id": self.from_profile_id,
            "to_profile_id": self.to_profile_id,
            "from_mode": self.from_mode,
            "to_mode": self.to_mode,
            "switched_by": self.switched_by,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Profile Validation Result
# ===========================================

@dataclass
class ProfileValidationResult:
    """Result of profile validation against current market state"""
    profile_id: str = ""
    is_valid: bool = True
    
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Risk checks
    exposure_check_passed: bool = True
    drawdown_check_passed: bool = True
    daily_loss_check_passed: bool = True
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "is_valid": self.is_valid,
            "warnings": self.warnings,
            "errors": self.errors,
            "checks": {
                "exposure": self.exposure_check_passed,
                "drawdown": self.drawdown_check_passed,
                "daily_loss": self.daily_loss_check_passed
            },
            "recommendations": self.recommendations
        }


# ===========================================
# Profile Summary
# ===========================================

@dataclass
class ProfileSummary:
    """Summary of profile performance"""
    profile_id: str = ""
    profile_mode: str = ""
    
    # Usage stats
    total_switches: int = 0
    total_active_time_hours: float = 0.0
    
    # Performance (when active)
    trades_executed: int = 0
    win_rate: float = 0.0
    total_pnl_usd: float = 0.0
    avg_holding_hours: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_mode": self.profile_mode,
            "usage": {
                "total_switches": self.total_switches,
                "active_hours": round(self.total_active_time_hours, 2)
            },
            "performance": {
                "trades_executed": self.trades_executed,
                "win_rate": round(self.win_rate, 4),
                "total_pnl_usd": round(self.total_pnl_usd, 2),
                "avg_holding_hours": round(self.avg_holding_hours, 2)
            }
        }
