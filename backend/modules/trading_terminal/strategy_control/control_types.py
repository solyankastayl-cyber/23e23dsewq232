"""
Strategy Control Types (TR5)
============================

Type definitions for Strategy Control module.

Key entities:
- ControlMode: NORMAL, PAUSED, SOFT_KILL, HARD_KILL
- KillSwitchMode: SOFT, HARD
- StrategyControlState: Current system control state
- StrategyControlEvent: Control action log
- KillSwitchConfig: Kill switch configuration
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class ControlMode(Enum):
    """System control mode hierarchy: NORMAL → PAUSED → SOFT_KILL → HARD_KILL"""
    NORMAL = "NORMAL"
    PAUSED = "PAUSED"
    SOFT_KILL = "SOFT_KILL"
    HARD_KILL = "HARD_KILL"


class KillSwitchMode(Enum):
    """Kill switch mode"""
    SOFT = "SOFT"
    HARD = "HARD"


class ControlAction(Enum):
    """Control action types"""
    PROFILE_SWITCH = "PROFILE_SWITCH"
    CONFIG_SWITCH = "CONFIG_SWITCH"
    TRADING_PAUSE = "TRADING_PAUSE"
    TRADING_RESUME = "TRADING_RESUME"
    SOFT_KILL_SWITCH = "SOFT_KILL_SWITCH"
    HARD_KILL_SWITCH = "HARD_KILL_SWITCH"
    KILL_SWITCH_RESET = "KILL_SWITCH_RESET"
    OVERRIDE_ENABLE = "OVERRIDE_ENABLE"
    OVERRIDE_DISABLE = "OVERRIDE_DISABLE"


class ActorType(Enum):
    """Who initiated the action"""
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"
    POLICY = "POLICY"
    API = "API"


# ===========================================
# KillSwitchConfig
# ===========================================

@dataclass
class KillSwitchConfig:
    """
    Kill switch configuration.
    
    Defines behavior for SOFT and HARD kill switches.
    """
    mode: KillSwitchMode = KillSwitchMode.SOFT
    
    # Actions
    cancel_open_orders: bool = True
    block_new_entries: bool = True
    allow_reductions: bool = True
    force_close_positions: bool = False
    
    # Optional position close config
    close_method: str = "market"  # market, staged, close_only
    close_timeout_seconds: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "cancel_open_orders": self.cancel_open_orders,
            "block_new_entries": self.block_new_entries,
            "allow_reductions": self.allow_reductions,
            "force_close_positions": self.force_close_positions,
            "close_method": self.close_method,
            "close_timeout_seconds": self.close_timeout_seconds
        }
    
    @classmethod
    def soft(cls) -> "KillSwitchConfig":
        """Create SOFT kill switch config"""
        return cls(
            mode=KillSwitchMode.SOFT,
            cancel_open_orders=True,
            block_new_entries=True,
            allow_reductions=True,
            force_close_positions=False
        )
    
    @classmethod
    def hard(cls) -> "KillSwitchConfig":
        """Create HARD kill switch config"""
        return cls(
            mode=KillSwitchMode.HARD,
            cancel_open_orders=True,
            block_new_entries=True,
            allow_reductions=True,
            force_close_positions=True,
            close_method="market"
        )


# ===========================================
# StrategyControlState
# ===========================================

@dataclass
class StrategyControlState:
    """
    Current control state of the trading system.
    
    Single source of truth for admin control.
    """
    state_id: str = field(default_factory=lambda: f"ctrl_{uuid.uuid4().hex[:8]}")
    
    # Trading enabled/disabled
    trading_enabled: bool = True
    
    # Active profile & config
    active_profile: str = "BALANCED"
    active_config: str = ""
    
    # Control mode (hierarchy)
    mode: ControlMode = ControlMode.NORMAL
    
    # Individual flags
    paused: bool = False
    kill_switch_active: bool = False
    kill_switch_mode: Optional[KillSwitchMode] = None
    override_mode: bool = False
    
    # Kill switch config (if active)
    kill_switch_config: Optional[KillSwitchConfig] = None
    
    # Timestamps
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    paused_at: Optional[datetime] = None
    kill_switch_at: Optional[datetime] = None
    override_at: Optional[datetime] = None
    
    # Actor who made last change
    last_actor: str = "system"
    last_action: str = ""
    last_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "trading_enabled": self.trading_enabled,
            "active_profile": self.active_profile,
            "active_config": self.active_config,
            "mode": self.mode.value,
            "paused": self.paused,
            "kill_switch": {
                "active": self.kill_switch_active,
                "mode": self.kill_switch_mode.value if self.kill_switch_mode else None,
                "config": self.kill_switch_config.to_dict() if self.kill_switch_config else None,
                "activated_at": self.kill_switch_at.isoformat() if self.kill_switch_at else None
            },
            "override_mode": self.override_mode,
            "timestamps": {
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "paused_at": self.paused_at.isoformat() if self.paused_at else None,
                "override_at": self.override_at.isoformat() if self.override_at else None
            },
            "last_change": {
                "actor": self.last_actor,
                "action": self.last_action,
                "reason": self.last_reason
            }
        }
    
    def to_dashboard_dict(self) -> Dict[str, Any]:
        """Simplified dict for dashboard API"""
        return {
            "tradingEnabled": self.trading_enabled,
            "activeProfile": self.active_profile,
            "activeConfig": self.active_config,
            "paused": self.paused,
            "killSwitch": self.kill_switch_active,
            "killSwitchMode": self.kill_switch_mode.value if self.kill_switch_mode else None,
            "overrideMode": self.override_mode,
            "mode": self.mode.value
        }


# ===========================================
# StrategyControlEvent
# ===========================================

@dataclass
class StrategyControlEvent:
    """
    Log entry for control actions.
    
    Used for audit trail and diagnostics.
    """
    event_id: str = field(default_factory=lambda: f"cevt_{uuid.uuid4().hex[:8]}")
    
    # Action
    action: ControlAction = ControlAction.PROFILE_SWITCH
    
    # Actor
    actor: str = "admin"
    actor_type: ActorType = ActorType.ADMIN
    
    # Reason
    reason: str = ""
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # State before/after
    previous_state: Dict[str, Any] = field(default_factory=dict)
    new_state: Dict[str, Any] = field(default_factory=dict)
    
    # Result
    success: bool = True
    error_message: str = ""
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action": self.action.value,
            "actor": self.actor,
            "actor_type": self.actor_type.value,
            "reason": self.reason,
            "details": self.details,
            "state_change": {
                "previous": self.previous_state,
                "new": self.new_state
            },
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# ProfileSwitchRequest
# ===========================================

@dataclass
class ProfileSwitchRequest:
    """Request to switch strategy profile"""
    profile: str = "BALANCED"
    reason: str = ""
    actor: str = "admin"
    
    def validate(self) -> tuple:
        """Validate request. Returns (is_valid, error_message)"""
        valid_profiles = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
        if self.profile.upper() not in valid_profiles:
            return False, f"Invalid profile: {self.profile}. Valid: {valid_profiles}"
        return True, ""


# ===========================================
# ConfigSwitchRequest
# ===========================================

@dataclass
class ConfigSwitchRequest:
    """Request to switch strategy config"""
    config_id: str = ""
    reason: str = ""
    actor: str = "admin"
    
    def validate(self) -> tuple:
        """Validate request. Returns (is_valid, error_message)"""
        if not self.config_id:
            return False, "config_id is required"
        return True, ""


# ===========================================
# KillSwitchRequest
# ===========================================

@dataclass
class KillSwitchRequest:
    """Request to trigger kill switch"""
    mode: KillSwitchMode = KillSwitchMode.SOFT
    reason: str = ""
    actor: str = "admin"
    
    # Optional overrides
    force_close_positions: Optional[bool] = None
    close_method: str = "market"


# ===========================================
# OverrideSettings
# ===========================================

@dataclass
class OverrideSettings:
    """Override mode settings"""
    manual_order_routing: bool = True
    disable_auto_switching: bool = True
    disable_strategy_runtime: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "manual_order_routing": self.manual_order_routing,
            "disable_auto_switching": self.disable_auto_switching,
            "disable_strategy_runtime": self.disable_strategy_runtime
        }
