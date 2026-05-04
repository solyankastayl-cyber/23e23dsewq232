"""
Circuit Breaker Types

PHASE 41.4 — Circuit Breaker Engine

Automatic risk-control system.

Rules:
- portfolio_drawdown > 5% → reduce size
- daily_loss > 3% → block new entries
- slippage > 50 bps → switch to LIMIT only
- drawdown > 10% → trigger kill switch
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class BreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"          # Normal — all systems go
    OPEN = "OPEN"              # Tripped — protective actions active
    HALF_OPEN = "HALF_OPEN"    # Recovery — testing if safe to resume


class BreakerRuleType(str, Enum):
    """Types of circuit breaker rules."""
    PORTFOLIO_DRAWDOWN = "PORTFOLIO_DRAWDOWN"
    DAILY_LOSS = "DAILY_LOSS"
    SLIPPAGE = "SLIPPAGE"
    LOSS_STREAK = "LOSS_STREAK"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    LIQUIDITY_VACUUM = "LIQUIDITY_VACUUM"
    CASCADE_RISK = "CASCADE_RISK"
    CORRELATION_SPIKE = "CORRELATION_SPIKE"
    EXECUTION_ERRORS = "EXECUTION_ERRORS"


class BreakerAction(str, Enum):
    """Actions taken when breaker trips."""
    REDUCE_POSITION_SIZE = "REDUCE_POSITION_SIZE"
    BLOCK_NEW_ENTRIES = "BLOCK_NEW_ENTRIES"
    LIMIT_ONLY = "LIMIT_ONLY"
    PAUSE_STRATEGY = "PAUSE_STRATEGY"
    REDUCE_LEVERAGE = "REDUCE_LEVERAGE"
    TRIGGER_KILL_SWITCH = "TRIGGER_KILL_SWITCH"
    SWITCH_SAFE_MODE = "SWITCH_SAFE_MODE"
    ALERT_ONLY = "ALERT_ONLY"


class BreakerSeverity(str, Enum):
    """Severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BreakerRule(BaseModel):
    """
    A single circuit breaker rule.
    """
    rule_id: str
    rule_type: BreakerRuleType
    name: str
    description: str = ""

    # Thresholds
    warning_threshold: float
    trigger_threshold: float
    critical_threshold: float

    # Actions
    warning_actions: List[BreakerAction] = Field(default_factory=list)
    trigger_actions: List[BreakerAction] = Field(default_factory=list)
    critical_actions: List[BreakerAction] = Field(default_factory=list)

    # Modifiers
    size_modifier_warning: float = 0.75
    size_modifier_trigger: float = 0.5
    size_modifier_critical: float = 0.0

    # Recovery
    recovery_threshold: float = 0.0
    cooldown_seconds: int = 300

    # State
    enabled: bool = True
    current_value: float = 0.0
    state: BreakerState = BreakerState.CLOSED
    last_triggered_at: Optional[datetime] = None
    trip_count: int = 0


class BreakerEvent(BaseModel):
    """Circuit breaker event."""
    event_id: str = Field(default_factory=lambda: f"cb_evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    rule_id: str
    rule_type: BreakerRuleType
    severity: BreakerSeverity

    previous_state: BreakerState
    new_state: BreakerState

    current_value: float
    threshold: float
    actions_taken: List[BreakerAction] = Field(default_factory=list)
    size_modifier: float = 1.0

    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BreakerStatus(BaseModel):
    """Overall circuit breaker status."""
    state: BreakerState = BreakerState.CLOSED
    active_rules: int = 0
    tripped_rules: int = 0
    total_rules: int = 0

    # Aggregate modifiers
    size_modifier: float = 1.0
    new_entries_blocked: bool = False
    limit_only: bool = False
    strategies_paused: List[str] = Field(default_factory=list)
    kill_switch_triggered: bool = False

    # Tripped rule details
    tripped_rule_ids: List[str] = Field(default_factory=list)
    tripped_details: List[Dict[str, Any]] = Field(default_factory=list)

    # Stats
    total_trips: int = 0
    trips_last_24h: int = 0
    last_trip_at: Optional[datetime] = None

    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    enabled: bool = True
    check_interval_seconds: int = 5
    auto_recovery: bool = True
    recovery_check_interval_seconds: int = 60

    # Default thresholds
    drawdown_warning: float = 0.03
    drawdown_trigger: float = 0.05
    drawdown_critical: float = 0.10

    daily_loss_warning: float = 0.02
    daily_loss_trigger: float = 0.03
    daily_loss_critical: float = 0.05

    slippage_warning_bps: float = 30.0
    slippage_trigger_bps: float = 50.0
    slippage_critical_bps: float = 100.0

    loss_streak_warning: int = 3
    loss_streak_trigger: int = 5
    loss_streak_critical: int = 8

    volatility_spike_warning: float = 2.0
    volatility_spike_trigger: float = 3.0
    volatility_spike_critical: float = 5.0

    max_execution_errors: int = 5
    error_window_seconds: int = 60


class BreakerCheckResult(BaseModel):
    """Result of a circuit breaker check before order."""
    allowed: bool = True
    state: BreakerState = BreakerState.CLOSED

    size_modifier: float = 1.0
    new_entries_blocked: bool = False
    limit_only: bool = False

    tripped_rules: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    blocked_reason: Optional[str] = None

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
