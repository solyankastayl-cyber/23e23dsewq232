"""
Risk Types (TR4)
================

Type definitions for Risk Dashboard.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class RiskLevel(Enum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    DRAWDOWN = "DRAWDOWN"
    DAILY_LOSS = "DAILY_LOSS"
    LEVERAGE = "LEVERAGE"
    CONCENTRATION = "CONCENTRATION"
    VAR = "VAR"
    EXPOSURE = "EXPOSURE"


class AlertSeverity(Enum):
    INFO = 1
    WARNING = 2
    HIGH = 3
    CRITICAL = 4


class GuardrailAction(Enum):
    ALERT_ONLY = "ALERT_ONLY"
    SWITCH_CONSERVATIVE = "SWITCH_CONSERVATIVE"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    PAUSE_TRADING = "PAUSE_TRADING"
    KILL_SWITCH = "KILL_SWITCH"


@dataclass
class RiskMetrics:
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    drawdown_duration_hours: float = 0.0
    daily_loss_pct: float = 0.0
    daily_loss_limit_pct: float = 0.05
    daily_loss_remaining_pct: float = 0.05
    peak_equity: float = 0.0
    current_equity: float = 0.0
    start_of_day_equity: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "drawdown": {"current_pct": round(self.current_drawdown_pct, 4), "max_pct": round(self.max_drawdown_pct, 4), "duration_hours": round(self.drawdown_duration_hours, 1)},
            "daily_loss": {"current_pct": round(self.daily_loss_pct, 4), "limit_pct": round(self.daily_loss_limit_pct, 4), "remaining_pct": round(self.daily_loss_remaining_pct, 4)},
            "equity": {"current": round(self.current_equity, 2), "peak": round(self.peak_equity, 2), "start_of_day": round(self.start_of_day_equity, 2)}
        }


@dataclass
class ExposureMetrics:
    gross_exposure_usd: float = 0.0
    gross_exposure_pct: float = 0.0
    net_exposure_usd: float = 0.0
    net_exposure_pct: float = 0.0
    long_exposure_pct: float = 0.0
    short_exposure_pct: float = 0.0
    current_leverage: float = 1.0
    max_leverage: float = 3.0
    exposure_limit_pct: float = 0.80
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross": {"usd": round(self.gross_exposure_usd, 2), "pct": round(self.gross_exposure_pct, 4)},
            "net": {"usd": round(self.net_exposure_usd, 2), "pct": round(self.net_exposure_pct, 4)},
            "directional": {"long_pct": round(self.long_exposure_pct, 4), "short_pct": round(self.short_exposure_pct, 4)},
            "leverage": {"current": round(self.current_leverage, 2), "max": round(self.max_leverage, 2)},
            "limit_pct": round(self.exposure_limit_pct, 4)
        }


@dataclass
class ConcentrationMetrics:
    max_asset: str = ""
    max_asset_weight_pct: float = 0.0
    top_3_assets_weight_pct: float = 0.0
    stablecoin_weight_pct: float = 0.0
    btc_weight_pct: float = 0.0
    eth_weight_pct: float = 0.0
    altcoin_weight_pct: float = 0.0
    concentration_score: float = 0.0
    single_asset_limit_pct: float = 0.40
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_asset": {"asset": self.max_asset, "weight_pct": round(self.max_asset_weight_pct, 4)},
            "top_3_weight_pct": round(self.top_3_assets_weight_pct, 4),
            "by_category": {"stablecoin": round(self.stablecoin_weight_pct, 4), "btc": round(self.btc_weight_pct, 4), "eth": round(self.eth_weight_pct, 4), "altcoin": round(self.altcoin_weight_pct, 4)},
            "concentration_score": round(self.concentration_score, 4),
            "single_asset_limit_pct": round(self.single_asset_limit_pct, 4)
        }


@dataclass
class TailRiskMetrics:
    var_95_pct: float = 0.0
    var_99_pct: float = 0.0
    cvar_95_pct: float = 0.0
    cvar_99_pct: float = 0.0
    calculation_method: str = "monte_carlo"
    last_calculated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "var": {"var_95_pct": round(self.var_95_pct, 4), "var_99_pct": round(self.var_99_pct, 4)},
            "cvar": {"cvar_95_pct": round(self.cvar_95_pct, 4), "cvar_99_pct": round(self.cvar_99_pct, 4)},
            "calculation_method": self.calculation_method,
            "last_calculated_at": self.last_calculated_at.isoformat() if self.last_calculated_at else None
        }


@dataclass
class RiskAlert:
    alert_id: str = field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:8]}")
    alert_type: AlertType = AlertType.DRAWDOWN
    severity: AlertSeverity = AlertSeverity.WARNING
    title: str = ""
    message: str = ""
    metric_name: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0
    is_active: bool = True
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: Optional[datetime] = None
    suggested_action: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id, "type": self.alert_type.value, "severity": self.severity.name,
            "title": self.title, "message": self.message,
            "metric": {"name": self.metric_name, "current": round(self.current_value, 4), "threshold": round(self.threshold_value, 4)},
            "status": {"is_active": self.is_active, "acknowledged": self.acknowledged, "acknowledged_by": self.acknowledged_by, "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None},
            "suggested_action": self.suggested_action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class RiskGuardrailEvent:
    event_id: str = field(default_factory=lambda: f"guard_{uuid.uuid4().hex[:8]}")
    trigger_type: str = ""
    action: GuardrailAction = GuardrailAction.ALERT_ONLY
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    execution_result: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id, "trigger_type": self.trigger_type, "action": self.action.value,
            "reason": self.reason, "details": self.details, "executed": self.executed,
            "execution_result": self.execution_result, "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class PortfolioRiskState:
    state_id: str = field(default_factory=lambda: f"rsk_{uuid.uuid4().hex[:8]}")
    risk_level: RiskLevel = RiskLevel.LOW
    risk_level_reason: str = ""
    equity_usd: float = 0.0
    metrics: RiskMetrics = field(default_factory=RiskMetrics)
    exposure: ExposureMetrics = field(default_factory=ExposureMetrics)
    concentration: ConcentrationMetrics = field(default_factory=ConcentrationMetrics)
    tail_risk: TailRiskMetrics = field(default_factory=TailRiskMetrics)
    active_alerts_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id, "risk_level": self.risk_level.name, "risk_level_reason": self.risk_level_reason,
            "equity_usd": round(self.equity_usd, 2), "metrics": self.metrics.to_dict(), "exposure": self.exposure.to_dict(),
            "concentration": self.concentration.to_dict(), "tail_risk": self.tail_risk.to_dict(),
            "active_alerts_count": self.active_alerts_count, "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }
    
    def to_dashboard_dict(self) -> Dict[str, Any]:
        return {
            "riskLevel": self.risk_level.name, "drawdownPct": round(self.metrics.current_drawdown_pct, 4),
            "dailyLossPct": round(self.metrics.daily_loss_pct, 4), "portfolioExposurePct": round(self.exposure.gross_exposure_pct, 4),
            "leverage": round(self.exposure.current_leverage, 2), "maxAssetWeightPct": round(self.concentration.max_asset_weight_pct, 4),
            "var95": round(self.tail_risk.var_95_pct, 4), "cvar95": round(self.tail_risk.cvar_95_pct, 4),
            "alertsCount": self.active_alerts_count, "generatedAt": self.generated_at.isoformat() if self.generated_at else None
        }
