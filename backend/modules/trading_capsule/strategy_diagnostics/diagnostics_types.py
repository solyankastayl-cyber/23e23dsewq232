"""
Strategy Diagnostics Types (STR4)
=================================

Type definitions for Strategy Diagnostics layer.

Key entities:
- StrategyState: Active profile/config state
- StrategyHealthState: Health evaluation
- PerformanceSummary: Performance metrics
- RiskSummary: Risk metrics
- StrategyDiagnosticsSnapshot: Full snapshot
- StrategyWarning: Warning/alert
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class HealthStatus(Enum):
    """Strategy health status levels - values indicate severity (higher = worse)"""
    HEALTHY = 1    # All normal
    WARNING = 2    # Minor deviations
    DEGRADED = 3   # Needs attention
    CRITICAL = 4   # Manual intervention needed


class WarningType(Enum):
    """Types of strategy warnings"""
    HIGH_DRAWDOWN = "HIGH_DRAWDOWN"
    LOSS_LIMIT_NEAR = "LOSS_LIMIT_NEAR"
    LOSS_LIMIT_BREACH = "LOSS_LIMIT_BREACH"
    TOO_MANY_SWITCHES = "TOO_MANY_SWITCHES"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    PROFILE_UNSTABLE = "PROFILE_UNSTABLE"
    VOLATILITY_ALERT = "VOLATILITY_ALERT"
    HIGH_EXPOSURE = "HIGH_EXPOSURE"
    LOW_WIN_RATE = "LOW_WIN_RATE"
    EXECUTION_ISSUES = "EXECUTION_ISSUES"


class WarningSeverity(Enum):
    """Warning severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ===========================================
# StrategyState
# ===========================================

@dataclass
class StrategyState:
    """
    Current active strategy state.
    
    Shows what's currently active and why.
    """
    # Active profile
    active_profile: str = "BALANCED"
    active_profile_id: str = ""
    
    # Active config
    active_config_id: str = ""
    active_config_name: str = ""
    
    # Source of activation
    activation_source: str = "MANUAL"  # MANUAL / RULE / SCHEDULE
    activation_reason: str = ""
    activated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_by: str = "system"
    
    # Policy info (if rule/schedule triggered)
    triggered_policy_id: str = ""
    triggered_policy_name: str = ""
    
    # Duration
    active_duration_minutes: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_profile": self.active_profile,
            "active_profile_id": self.active_profile_id,
            "active_config_id": self.active_config_id,
            "active_config_name": self.active_config_name,
            "activation": {
                "source": self.activation_source,
                "reason": self.activation_reason,
                "at": self.activated_at.isoformat() if self.activated_at else None,
                "by": self.activated_by
            },
            "policy": {
                "id": self.triggered_policy_id,
                "name": self.triggered_policy_name
            } if self.triggered_policy_id else None,
            "active_duration_minutes": round(self.active_duration_minutes, 1)
        }


# ===========================================
# StrategyHealthState
# ===========================================

@dataclass
class StrategyHealthState:
    """
    Strategy health evaluation.
    
    Determines overall health status.
    """
    status: HealthStatus = HealthStatus.HEALTHY
    status_reason: str = ""
    
    # Metrics that affect health
    switches_last_24h: int = 0
    consecutive_losses: int = 0
    
    daily_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    
    # Health checks
    drawdown_check: str = "PASS"  # PASS / WARNING / FAIL
    loss_limit_check: str = "PASS"
    stability_check: str = "PASS"
    performance_check: str = "PASS"
    
    # Active warnings count
    active_warnings_count: int = 0
    
    # Timestamp
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.name,
            "status_reason": self.status_reason,
            "metrics": {
                "switches_last_24h": self.switches_last_24h,
                "consecutive_losses": self.consecutive_losses,
                "daily_pnl_pct": round(self.daily_pnl_pct, 4),
                "drawdown_pct": round(self.drawdown_pct, 4)
            },
            "checks": {
                "drawdown": self.drawdown_check,
                "loss_limit": self.loss_limit_check,
                "stability": self.stability_check,
                "performance": self.performance_check
            },
            "active_warnings_count": self.active_warnings_count,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None
        }


# ===========================================
# PerformanceSummary
# ===========================================

@dataclass
class PerformanceSummary:
    """
    Performance summary for current period.
    """
    # PnL
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    monthly_pnl_pct: float = 0.0
    total_pnl_usd: float = 0.0
    
    # Win rate
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Trades
    trades_today: int = 0
    trades_this_week: int = 0
    
    # Recent performance
    last_trade_pnl_pct: float = 0.0
    last_trade_at: Optional[datetime] = None
    
    # Best/Worst
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    
    # Expectancy
    expectancy: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pnl": {
                "daily_pct": round(self.daily_pnl_pct, 4),
                "weekly_pct": round(self.weekly_pnl_pct, 4),
                "monthly_pct": round(self.monthly_pnl_pct, 4),
                "total_usd": round(self.total_pnl_usd, 2)
            },
            "rates": {
                "win_rate": round(self.win_rate, 4),
                "profit_factor": round(self.profit_factor, 2),
                "expectancy": round(self.expectancy, 4)
            },
            "trades": {
                "today": self.trades_today,
                "this_week": self.trades_this_week
            },
            "last_trade": {
                "pnl_pct": round(self.last_trade_pnl_pct, 4),
                "at": self.last_trade_at.isoformat() if self.last_trade_at else None
            },
            "extremes": {
                "best_trade_pct": round(self.best_trade_pct, 4),
                "worst_trade_pct": round(self.worst_trade_pct, 4),
                "avg_win_pct": round(self.avg_win_pct, 4),
                "avg_loss_pct": round(self.avg_loss_pct, 4)
            }
        }


# ===========================================
# RiskSummary
# ===========================================

@dataclass
class RiskSummary:
    """
    Risk metrics summary.
    """
    # Drawdown
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    drawdown_duration_hours: float = 0.0
    
    # Daily loss
    daily_loss_pct: float = 0.0
    daily_loss_limit_pct: float = 0.05
    daily_loss_remaining_pct: float = 0.05
    
    # Exposure
    total_exposure_pct: float = 0.0
    max_exposure_pct: float = 0.40
    
    # Leverage
    current_leverage: float = 1.0
    max_leverage: float = 3.0
    
    # VaR (if calculated)
    var_95_pct: Optional[float] = None
    cvar_95_pct: Optional[float] = None
    
    # Active protections
    loss_protection_active: bool = False
    drawdown_protection_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "drawdown": {
                "current_pct": round(self.current_drawdown_pct, 4),
                "max_pct": round(self.max_drawdown_pct, 4),
                "duration_hours": round(self.drawdown_duration_hours, 1)
            },
            "daily_loss": {
                "current_pct": round(self.daily_loss_pct, 4),
                "limit_pct": round(self.daily_loss_limit_pct, 4),
                "remaining_pct": round(self.daily_loss_remaining_pct, 4)
            },
            "exposure": {
                "current_pct": round(self.total_exposure_pct, 4),
                "max_pct": round(self.max_exposure_pct, 4)
            },
            "leverage": {
                "current": round(self.current_leverage, 2),
                "max": round(self.max_leverage, 2)
            },
            "var": {
                "var_95_pct": round(self.var_95_pct, 4) if self.var_95_pct else None,
                "cvar_95_pct": round(self.cvar_95_pct, 4) if self.cvar_95_pct else None
            } if self.var_95_pct else None,
            "protections": {
                "loss_protection_active": self.loss_protection_active,
                "drawdown_protection_active": self.drawdown_protection_active
            }
        }


# ===========================================
# StrategyWarning
# ===========================================

@dataclass
class StrategyWarning:
    """
    Strategy warning/alert.
    """
    warning_id: str = field(default_factory=lambda: f"warn_{uuid.uuid4().hex[:8]}")
    
    warning_type: WarningType = WarningType.HIGH_DRAWDOWN
    severity: WarningSeverity = WarningSeverity.WARNING
    
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    related_metric: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0
    
    # Status
    is_active: bool = True
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "type": self.warning_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "metric": {
                "name": self.related_metric,
                "current": self.current_value,
                "threshold": self.threshold_value
            },
            "status": {
                "is_active": self.is_active,
                "acknowledged": self.acknowledged,
                "acknowledged_by": self.acknowledged_by,
                "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


# ===========================================
# SwitchTrace
# ===========================================

@dataclass
class SwitchTrace:
    """
    Switch event trace for history.
    """
    event_id: str = ""
    
    from_profile: str = ""
    to_profile: str = ""
    
    reason: str = ""
    trigger_type: str = ""  # MANUAL / RULE / SCHEDULE
    
    policy_id: str = ""
    policy_name: str = ""
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "from_profile": self.from_profile,
            "to_profile": self.to_profile,
            "reason": self.reason,
            "trigger_type": self.trigger_type,
            "policy": {
                "id": self.policy_id,
                "name": self.policy_name
            } if self.policy_id else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# StrategyDiagnosticsSnapshot
# ===========================================

@dataclass
class StrategyDiagnosticsSnapshot:
    """
    Full diagnostics snapshot.
    
    Aggregates all diagnostics data.
    """
    snapshot_id: str = field(default_factory=lambda: f"diag_{uuid.uuid4().hex[:8]}")
    
    # State
    state: StrategyState = field(default_factory=StrategyState)
    
    # Health
    health: StrategyHealthState = field(default_factory=StrategyHealthState)
    
    # Performance
    performance: PerformanceSummary = field(default_factory=PerformanceSummary)
    
    # Risk
    risk: RiskSummary = field(default_factory=RiskSummary)
    
    # Warnings
    warnings: List[StrategyWarning] = field(default_factory=list)
    
    # Recent switches
    recent_switches: List[SwitchTrace] = field(default_factory=list)
    
    # Timestamp
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "state": self.state.to_dict(),
            "health": self.health.to_dict(),
            "performance": self.performance.to_dict(),
            "risk": self.risk.to_dict(),
            "warnings": [w.to_dict() for w in self.warnings],
            "recent_switches": [s.to_dict() for s in self.recent_switches],
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }
    
    def to_dashboard_dict(self) -> Dict[str, Any]:
        """Compact dashboard format"""
        return {
            "activeProfile": self.state.active_profile,
            "activeConfigId": self.state.active_config_id,
            "source": self.state.activation_source,
            "health": self.health.status.name,
            "performance": {
                "dailyPnlPct": round(self.performance.daily_pnl_pct, 4),
                "winRate": round(self.performance.win_rate, 4),
                "tradesToday": self.performance.trades_today
            },
            "risk": {
                "drawdownPct": round(self.risk.current_drawdown_pct, 4),
                "exposurePct": round(self.risk.total_exposure_pct, 4),
                "dailyLossPct": round(self.risk.daily_loss_pct, 4)
            },
            "warnings": [w.warning_type.value for w in self.warnings if w.is_active],
            "warningsCount": len([w for w in self.warnings if w.is_active]),
            "generatedAt": self.generated_at.isoformat() if self.generated_at else None
        }
