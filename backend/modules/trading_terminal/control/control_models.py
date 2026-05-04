"""
TT5 - Control Models
====================
Data models for system control state, pending actions, and overrides.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ControlState:
    """Global system control state"""
    # Trading controls
    trading_enabled: bool
    new_entries_enabled: bool
    position_management_enabled: bool
    
    # Alpha Factory mode
    alpha_mode: str  # AUTO / MANUAL / OFF
    
    # System state
    system_state: str  # ACTIVE / PAUSED / SOFT_KILL / HARD_KILL / EMERGENCY
    
    # Kill switches
    emergency: bool
    soft_kill: bool
    hard_kill: bool
    
    # Timestamps
    last_state_change: str = ""
    last_alpha_run: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PendingAction:
    """Alpha action waiting for approval"""
    pending_id: str
    scope: str          # symbol / entry_mode
    scope_key: str      # BTCUSDT / ENTER_NOW
    
    action: str         # DISABLE_SYMBOL / REDUCE_RISK / etc.
    magnitude: float
    reason: str
    
    # Source info
    source: str         # alpha_factory / manual
    confidence: float
    auto_apply: bool
    
    # Status
    status: str         # PENDING / APPROVED / REJECTED / APPLIED / EXPIRED
    
    created_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None  # system / operator
    
    def to_dict(self):
        return asdict(self)


@dataclass
class OverrideRule:
    """Manual operator override"""
    rule_id: str
    override_type: str  # DISABLE_SYMBOL / ENABLE_SYMBOL / FORCE_REDUCE_RISK / BLOCK_ENTRY_MODE
    scope_key: str
    value: bool
    reason: str
    created_at: str
    expires_at: Optional[str] = None
    active: bool = True
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ControlSummary:
    """Summary for UI display"""
    system_state: str
    alpha_mode: str
    trading_enabled: bool
    new_entries_enabled: bool
    soft_kill: bool
    hard_kill: bool
    emergency: bool
    pending_actions_count: int
    active_overrides_count: int
    
    def to_dict(self):
        return asdict(self)
