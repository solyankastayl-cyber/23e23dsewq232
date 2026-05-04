"""
Kill Switch Types

PHASE 41.3 — Kill Switch Engine

Emergency stop system for trading operations.

States:
- ACTIVE: System operating normally
- DISABLED: Kill switch triggered, all operations stopped
- EMERGENCY_STOP: Critical emergency, immediate halt

Triggers:
- Manual trigger
- Portfolio risk breach
- Execution error loop
- Exchange disconnection
- PnL collapse
"""

from typing import Literal, Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

class KillSwitchState(str, Enum):
    """Kill switch states."""
    ACTIVE = "ACTIVE"              # System operating normally
    DISABLED = "DISABLED"          # Kill switch triggered
    EMERGENCY_STOP = "EMERGENCY_STOP"  # Critical emergency
    SAFE_MODE = "SAFE_MODE"        # Reduced operations


class KillSwitchTrigger(str, Enum):
    """Kill switch trigger types."""
    MANUAL = "MANUAL"
    PORTFOLIO_RISK_BREACH = "PORTFOLIO_RISK_BREACH"
    EXECUTION_ERROR_LOOP = "EXECUTION_ERROR_LOOP"
    EXCHANGE_DISCONNECTION = "EXCHANGE_DISCONNECTION"
    PNL_COLLAPSE = "PNL_COLLAPSE"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class KillSwitchAction(str, Enum):
    """Actions taken when kill switch activates."""
    BLOCK_NEW_ORDERS = "BLOCK_NEW_ORDERS"
    CANCEL_PENDING = "CANCEL_PENDING"
    CLOSE_POSITIONS = "CLOSE_POSITIONS"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    SWITCH_TO_SAFE_MODE = "SWITCH_TO_SAFE_MODE"


# ══════════════════════════════════════════════════════════════
# Kill Switch Status
# ══════════════════════════════════════════════════════════════

class KillSwitchStatus(BaseModel):
    """
    Current kill switch status.
    """
    state: KillSwitchState = KillSwitchState.ACTIVE
    
    # Activation info
    is_active: bool = True  # System operating
    is_safe_mode: bool = False
    
    # Last activation
    last_trigger: Optional[KillSwitchTrigger] = None
    last_trigger_reason: Optional[str] = None
    last_triggered_at: Optional[datetime] = None
    triggered_by: Optional[str] = None
    
    # Recovery
    can_auto_recover: bool = False
    recovery_conditions: List[str] = Field(default_factory=list)
    
    # Actions taken
    actions_taken: List[KillSwitchAction] = Field(default_factory=list)
    
    # Stats
    blocked_orders_count: int = 0
    cancelled_orders_count: int = 0
    closed_positions_count: int = 0
    
    # Timestamps
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_since: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Kill Switch Event
# ══════════════════════════════════════════════════════════════

class KillSwitchEvent(BaseModel):
    """
    Kill switch activation/deactivation event.
    """
    event_id: str = Field(default_factory=lambda: f"ks_evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    event_type: str  # ACTIVATED, DEACTIVATED, STATE_CHANGE
    
    previous_state: KillSwitchState
    new_state: KillSwitchState
    
    trigger: Optional[KillSwitchTrigger] = None
    trigger_reason: str = ""
    
    # Context
    portfolio_risk: float = 0.0
    portfolio_pnl: float = 0.0
    drawdown: float = 0.0
    
    # Actions
    actions_taken: List[KillSwitchAction] = Field(default_factory=list)
    
    # User
    triggered_by: str = "system"
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Kill Switch Config
# ══════════════════════════════════════════════════════════════

class KillSwitchConfig(BaseModel):
    """
    Kill switch configuration.
    
    Thresholds for automatic triggers.
    """
    # Risk thresholds
    portfolio_risk_limit: float = 0.25        # 25% - trigger
    portfolio_risk_emergency: float = 0.30    # 30% - emergency stop
    
    # Drawdown thresholds
    drawdown_warning: float = 0.05            # 5%
    drawdown_limit: float = 0.10              # 10% - trigger
    drawdown_emergency: float = 0.15          # 15% - emergency stop
    
    # PnL thresholds
    daily_loss_limit: float = 0.03            # 3% daily loss
    daily_loss_emergency: float = 0.05        # 5% - emergency stop
    
    # Execution error thresholds
    max_execution_errors: int = 5             # Errors before trigger
    error_window_seconds: int = 60            # Time window
    
    # Exchange connection
    exchange_disconnect_timeout: int = 30     # Seconds
    
    # Actions
    auto_cancel_pending: bool = True
    auto_close_positions: bool = False        # Dangerous, default off
    auto_reduce_exposure: bool = True
    exposure_reduction_factor: float = 0.5    # Reduce to 50%
    
    # Recovery
    auto_recovery_enabled: bool = False       # Manual recovery by default
    recovery_cooldown_seconds: int = 300      # 5 minutes


# ══════════════════════════════════════════════════════════════
# Activation Request
# ══════════════════════════════════════════════════════════════

class ActivateKillSwitchRequest(BaseModel):
    """Request to activate kill switch."""
    trigger: KillSwitchTrigger = KillSwitchTrigger.MANUAL
    reason: str = ""
    user: str = "operator"
    
    # Actions to take
    cancel_pending: bool = True
    close_positions: bool = False
    reduce_exposure: bool = True
    
    # Options
    emergency: bool = False  # Emergency stop (more severe)


class DeactivateKillSwitchRequest(BaseModel):
    """Request to deactivate kill switch."""
    user: str = "operator"
    reason: str = ""
    confirm_safe: bool = False  # Must confirm safe to proceed


# ══════════════════════════════════════════════════════════════
# Kill Switch Check Result
# ══════════════════════════════════════════════════════════════

class KillSwitchCheckResult(BaseModel):
    """
    Result of kill switch check.
    
    Called before order execution.
    """
    allowed: bool = True
    state: KillSwitchState = KillSwitchState.ACTIVE
    
    blocked_reason: Optional[str] = None
    
    # Modifications
    size_modified: bool = False
    size_modifier: float = 1.0
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
