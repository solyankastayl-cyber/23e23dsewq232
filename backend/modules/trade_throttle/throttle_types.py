"""
Trade Throttle Types

PHASE 43.4 — Trade Throttle Engine

Types for execution rate limiting and risk throttling.

Prevents:
- Overtrading
- Signal explosion
- Feedback loops
- Execution storms
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class ThrottleLevel(str, Enum):
    """Throttle level"""
    NONE = "NONE"           # No throttling
    LOW = "LOW"             # Minor delays
    MEDIUM = "MEDIUM"       # Significant delays
    HIGH = "HIGH"           # Heavy throttling
    BLOCKED = "BLOCKED"     # All execution blocked


class ThrottleReason(str, Enum):
    """Reason for throttling"""
    NONE = "NONE"
    TRADE_RATE = "TRADE_RATE"           # Too many trades/minute
    TURNOVER_RATE = "TURNOVER_RATE"     # Too much capital turnover
    POSITION_CHURN = "POSITION_CHURN"   # Too many position changes
    LOSS_STREAK = "LOSS_STREAK"         # Consecutive losses
    VOLATILITY = "VOLATILITY"           # High market volatility
    MANUAL = "MANUAL"                   # Manually activated


class TradeThrottleState(BaseModel):
    """
    Current throttle state.
    
    PHASE 43.4 Contract.
    """
    throttle_id: str = Field(default_factory=lambda: f"thr_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Current state
    throttle_level: ThrottleLevel = ThrottleLevel.NONE
    throttle_reason: ThrottleReason = ThrottleReason.NONE
    
    # Rate tracking (per 5 minutes)
    trades_last_5min: int = 0
    trades_limit_5min: int = 3
    
    # Turnover tracking (per hour)
    turnover_last_hour_pct: float = 0.0
    turnover_limit_hour_pct: float = 15.0  # 15% portfolio
    
    # Position churn tracking
    position_changes_last_hour: int = 0
    position_change_limit: int = 10
    
    # Loss tracking
    consecutive_losses: int = 0
    loss_streak_cooldown_active: bool = False
    cooldown_ends_at: Optional[datetime] = None
    
    # Blocked trades queue
    blocked_trades_count: int = 0
    queued_trades_count: int = 0
    
    # Stats
    trades_allowed_today: int = 0
    trades_blocked_today: int = 0
    trades_delayed_today: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThrottleConfig(BaseModel):
    """
    Trade Throttle configuration.
    
    Default pilot-safe limits.
    """
    # Trade rate limits
    max_trades_per_5min: int = 3
    max_trades_per_hour: int = 10
    max_trades_per_day: int = 50
    
    # Turnover limits (% of portfolio)
    max_turnover_per_hour_pct: float = 15.0
    max_turnover_per_day_pct: float = 50.0
    
    # Position change limits
    max_position_change_per_trade_pct: float = 20.0  # Max 20% of position
    max_position_changes_per_hour: int = 10
    
    # Loss streak protection
    loss_streak_threshold: int = 3
    cooldown_after_loss_streak_minutes: int = 10
    
    # Symbol-specific limits
    max_trades_per_symbol_per_hour: int = 5
    
    # Time delays
    min_trade_interval_seconds: int = 30
    
    # Emergency
    emergency_block_enabled: bool = False


class ThrottleCheckResult(BaseModel):
    """Result of throttle check."""
    allowed: bool
    throttle_level: ThrottleLevel
    reason: ThrottleReason
    delay_seconds: int = 0
    reduced_size_pct: Optional[float] = None  # If size should be reduced
    message: str = ""


class TradeRecord(BaseModel):
    """Record of a trade for throttle tracking."""
    trade_id: str
    timestamp: datetime
    symbol: str
    side: str
    size_usd: float
    strategy: str
    is_profit: Optional[bool] = None
    pnl: Optional[float] = None


class ThrottleQueuedTrade(BaseModel):
    """Trade that was queued due to throttling."""
    queue_id: str = Field(default_factory=lambda: f"q_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Original request
    request_id: str
    symbol: str
    side: str
    size_usd: float
    strategy: str
    
    # Queue info
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    throttle_reason: ThrottleReason
    estimated_release: datetime
    
    # Status
    status: str = "QUEUED"  # QUEUED, RELEASED, CANCELLED, EXPIRED
    released_at: Optional[datetime] = None
