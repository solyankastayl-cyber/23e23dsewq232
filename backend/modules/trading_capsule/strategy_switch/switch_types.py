"""
Strategy Switch Types (STR3)
============================

Type definitions for Strategy Switching & Policy Logic.

Key entities:
- SwitchPolicy: Policy definition for switching
- SwitchContext: Context for policy evaluation
- SwitchEvent: Switch event log
- SwitchDecision: Policy evaluation result
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, time
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class SwitchTriggerType(Enum):
    """Types of switch triggers"""
    MANUAL = "MANUAL"           # Admin/user manual switch
    SCHEDULE = "SCHEDULE"       # Time-based switch
    RULE = "RULE"               # Condition-based switch
    AUTO = "AUTO"               # AI/automated switch (future)


class SwitchPriority(Enum):
    """Priority levels for policy evaluation"""
    CRITICAL = 1    # Highest - emergency switches
    HIGH = 2        # High - loss protection
    MEDIUM = 3      # Medium - schedule based
    LOW = 4         # Low - optimization


class PolicyStatus(Enum):
    """Policy status"""
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    PENDING = "PENDING"


class ConditionOperator(Enum):
    """Operators for condition evaluation"""
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="
    IN = "in"
    NOT_IN = "not_in"


# ===========================================
# PolicyCondition
# ===========================================

@dataclass
class PolicyCondition:
    """
    Single condition for policy evaluation.
    
    Example:
        field="daily_loss_pct", operator=">=", value=0.05
        -> Triggers when daily loss >= 5%
    """
    condition_id: str = field(default_factory=lambda: f"cond_{uuid.uuid4().hex[:6]}")
    
    field: str = ""                          # Context field to check
    operator: ConditionOperator = ConditionOperator.GREATER_EQUAL
    value: Any = None                        # Threshold value
    
    description: str = ""
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context"""
        if self.field not in context:
            return False
        
        ctx_value = context.get(self.field)
        
        if self.operator == ConditionOperator.GREATER_THAN:
            return ctx_value > self.value
        elif self.operator == ConditionOperator.GREATER_EQUAL:
            return ctx_value >= self.value
        elif self.operator == ConditionOperator.LESS_THAN:
            return ctx_value < self.value
        elif self.operator == ConditionOperator.LESS_EQUAL:
            return ctx_value <= self.value
        elif self.operator == ConditionOperator.EQUAL:
            return ctx_value == self.value
        elif self.operator == ConditionOperator.NOT_EQUAL:
            return ctx_value != self.value
        elif self.operator == ConditionOperator.IN:
            return ctx_value in self.value
        elif self.operator == ConditionOperator.NOT_IN:
            return ctx_value not in self.value
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "description": self.description
        }


# ===========================================
# ScheduleConfig
# ===========================================

@dataclass
class ScheduleConfig:
    """
    Configuration for scheduled switches.
    
    Example:
        days=["SATURDAY", "SUNDAY"], 
        start_time="00:00",
        target_profile="CONSERVATIVE"
    """
    days: List[str] = field(default_factory=list)  # MONDAY, TUESDAY, etc.
    start_time: str = "00:00"                       # HH:MM format
    end_time: str = "23:59"                         # HH:MM format
    timezone: str = "UTC"
    
    def is_active(self, dt: Optional[datetime] = None) -> bool:
        """Check if schedule is currently active"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        
        # Check day of week
        day_names = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", 
                     "FRIDAY", "SATURDAY", "SUNDAY"]
        current_day = day_names[dt.weekday()]
        
        if self.days and current_day not in self.days:
            return False
        
        # Check time range
        try:
            start = datetime.strptime(self.start_time, "%H:%M").time()
            end = datetime.strptime(self.end_time, "%H:%M").time()
            current_time = dt.time()
            
            if start <= end:
                return start <= current_time <= end
            else:  # Overnight range
                return current_time >= start or current_time <= end
        except ValueError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "days": self.days,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timezone": self.timezone
        }


# ===========================================
# SwitchPolicy (STR3.1)
# ===========================================

@dataclass
class SwitchPolicy:
    """
    Switch Policy - defines when and how to switch profiles.
    
    Components:
    - trigger_type: MANUAL, SCHEDULE, or RULE
    - conditions: List of conditions (for RULE type)
    - schedule: Schedule config (for SCHEDULE type)
    - target_profile: Profile to switch to
    """
    policy_id: str = field(default_factory=lambda: f"policy_{uuid.uuid4().hex[:8]}")
    
    # Identity
    name: str = ""
    description: str = ""
    
    # Trigger Configuration
    trigger_type: SwitchTriggerType = SwitchTriggerType.MANUAL
    
    # Target
    target_profile: str = "CONSERVATIVE"  # Profile mode to switch to
    
    # Conditions (for RULE type)
    conditions: List[PolicyCondition] = field(default_factory=list)
    condition_logic: str = "AND"  # AND / OR for multiple conditions
    
    # Schedule (for SCHEDULE type)
    schedule: Optional[ScheduleConfig] = None
    
    # Priority & Status
    priority: SwitchPriority = SwitchPriority.MEDIUM
    status: PolicyStatus = PolicyStatus.ENABLED
    
    # Auto-revert settings
    auto_revert: bool = False
    revert_profile: str = "BALANCED"
    revert_delay_minutes: int = 60
    
    # Cooldown to prevent rapid switching
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate if policy should trigger.
        
        Returns True if policy conditions are met.
        """
        if self.status != PolicyStatus.ENABLED:
            return False
        
        # Check cooldown
        if self.last_triggered:
            cooldown_delta = datetime.now(timezone.utc) - self.last_triggered
            if cooldown_delta.total_seconds() < self.cooldown_minutes * 60:
                return False
        
        # Evaluate based on trigger type
        if self.trigger_type == SwitchTriggerType.MANUAL:
            return False  # Manual policies are explicit
        
        elif self.trigger_type == SwitchTriggerType.SCHEDULE:
            if self.schedule:
                return self.schedule.is_active()
            return False
        
        elif self.trigger_type == SwitchTriggerType.RULE:
            return self._evaluate_conditions(context)
        
        return False
    
    def _evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate rule conditions"""
        if not self.conditions:
            return False
        
        results = [c.evaluate(context) for c in self.conditions]
        
        if self.condition_logic.upper() == "AND":
            return all(results)
        elif self.condition_logic.upper() == "OR":
            return any(results)
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type.value,
            "target_profile": self.target_profile,
            "conditions": [c.to_dict() for c in self.conditions],
            "condition_logic": self.condition_logic,
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "priority": self.priority.value,
            "status": self.status.value,
            "auto_revert": self.auto_revert,
            "revert_profile": self.revert_profile,
            "revert_delay_minutes": self.revert_delay_minutes,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "tags": self.tags
        }


# ===========================================
# SwitchContext (STR3.2)
# ===========================================

@dataclass
class SwitchContext:
    """
    Context for policy evaluation.
    
    Contains all metrics and state needed to evaluate switch policies.
    """
    # Current state
    current_profile: str = "BALANCED"
    current_config_id: str = ""
    
    # Portfolio metrics
    daily_loss_pct: float = 0.0
    portfolio_drawdown_pct: float = 0.0
    total_exposure_pct: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Market metrics
    volatility_score: float = 0.0
    market_regime: str = "NEUTRAL"  # BULL, BEAR, NEUTRAL
    btc_24h_change_pct: float = 0.0
    
    # Time context
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    day_of_week: str = ""
    hour: int = 0
    
    # Trading activity
    trades_today: int = 0
    consecutive_losses: int = 0
    win_rate_today: float = 0.0
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for condition evaluation"""
        return {
            "current_profile": self.current_profile,
            "current_config_id": self.current_config_id,
            "daily_loss_pct": self.daily_loss_pct,
            "portfolio_drawdown_pct": self.portfolio_drawdown_pct,
            "total_exposure_pct": self.total_exposure_pct,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "volatility_score": self.volatility_score,
            "market_regime": self.market_regime,
            "btc_24h_change_pct": self.btc_24h_change_pct,
            "timestamp": self.timestamp,
            "day_of_week": self.day_of_week,
            "hour": self.hour,
            "trades_today": self.trades_today,
            "consecutive_losses": self.consecutive_losses,
            "win_rate_today": self.win_rate_today
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_profile": self.current_profile,
            "current_config_id": self.current_config_id,
            "portfolio": {
                "daily_loss_pct": round(self.daily_loss_pct, 4),
                "drawdown_pct": round(self.portfolio_drawdown_pct, 4),
                "exposure_pct": round(self.total_exposure_pct, 4),
                "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 4)
            },
            "market": {
                "volatility_score": round(self.volatility_score, 2),
                "regime": self.market_regime,
                "btc_24h_change_pct": round(self.btc_24h_change_pct, 4)
            },
            "time": {
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "day_of_week": self.day_of_week,
                "hour": self.hour
            },
            "activity": {
                "trades_today": self.trades_today,
                "consecutive_losses": self.consecutive_losses,
                "win_rate_today": round(self.win_rate_today, 4)
            }
        }


# ===========================================
# SwitchDecision (STR3.3)
# ===========================================

@dataclass
class SwitchDecision:
    """
    Result of policy evaluation.
    
    Contains the decision and reasoning.
    """
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")
    
    should_switch: bool = False
    target_profile: str = ""
    
    # Source
    triggered_by_policy_id: str = ""
    triggered_by_policy_name: str = ""
    trigger_type: SwitchTriggerType = SwitchTriggerType.MANUAL
    
    # Reasoning
    reason: str = ""
    matched_conditions: List[str] = field(default_factory=list)
    
    # Priority
    priority: int = 3
    
    # Timestamp
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "should_switch": self.should_switch,
            "target_profile": self.target_profile,
            "triggered_by": {
                "policy_id": self.triggered_by_policy_id,
                "policy_name": self.triggered_by_policy_name,
                "trigger_type": self.trigger_type.value
            },
            "reason": self.reason,
            "matched_conditions": self.matched_conditions,
            "priority": self.priority,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None
        }


# ===========================================
# SwitchEvent (STR3.4)
# ===========================================

@dataclass
class SwitchEvent:
    """
    Log entry for switch events.
    
    Used for audit trail and diagnostics.
    """
    event_id: str = field(default_factory=lambda: f"swe_{uuid.uuid4().hex[:8]}")
    
    # What changed
    from_profile: str = ""
    to_profile: str = ""
    
    from_config_id: str = ""
    to_config_id: str = ""
    
    # Trigger info
    trigger_type: SwitchTriggerType = SwitchTriggerType.MANUAL
    triggered_by_policy_id: str = ""
    
    # Reason
    reason: str = ""
    initiated_by: str = "system"  # admin, system, policy_name
    
    # Context snapshot
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Result
    success: bool = True
    error_message: str = ""
    
    # Timestamps
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "from_profile": self.from_profile,
            "to_profile": self.to_profile,
            "from_config_id": self.from_config_id,
            "to_config_id": self.to_config_id,
            "trigger_type": self.trigger_type.value,
            "triggered_by_policy_id": self.triggered_by_policy_id,
            "reason": self.reason,
            "initiated_by": self.initiated_by,
            "context_snapshot": self.context_snapshot,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# ActiveProfileState (STR3.5)
# ===========================================

@dataclass
class ActiveProfileState:
    """
    Current active profile state.
    
    Single source of truth for active profile.
    """
    profile_id: str = ""
    profile_mode: str = "BALANCED"
    config_id: str = ""
    
    # Activation info
    activated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_by: str = "system"
    activation_reason: str = ""
    activation_trigger_type: SwitchTriggerType = SwitchTriggerType.MANUAL
    
    # Policy reference
    activated_by_policy_id: str = ""
    
    # Auto-revert tracking
    scheduled_revert_at: Optional[datetime] = None
    revert_to_profile: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_mode": self.profile_mode,
            "config_id": self.config_id,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "activated_by": self.activated_by,
            "activation_reason": self.activation_reason,
            "activation_trigger_type": self.activation_trigger_type.value,
            "activated_by_policy_id": self.activated_by_policy_id,
            "scheduled_revert": {
                "scheduled_at": self.scheduled_revert_at.isoformat() if self.scheduled_revert_at else None,
                "revert_to": self.revert_to_profile
            } if self.scheduled_revert_at else None
        }
