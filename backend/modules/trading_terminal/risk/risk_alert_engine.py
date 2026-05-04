"""
Risk Alert Engine (TR4)
=======================

Generates risk alerts based on thresholds.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .risk_types import RiskAlert, AlertType, AlertSeverity, RiskMetrics, ExposureMetrics, ConcentrationMetrics, TailRiskMetrics


class RiskAlertEngine:
    """Generates and manages risk alerts."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._alerts: Dict[str, RiskAlert] = {}
        self._alert_history: List[RiskAlert] = []
        
        # Thresholds
        self._thresholds = {
            "drawdown_warning": 0.08, "drawdown_high": 0.12, "drawdown_critical": 0.18,
            "daily_loss_warning": 0.03, "daily_loss_high": 0.04, "daily_loss_critical": 0.05,
            "leverage_warning": 2.0, "leverage_high": 3.0, "leverage_critical": 5.0,
            "concentration_warning": 0.35, "concentration_high": 0.50,
            "var95_warning": 0.15, "var95_high": 0.25
        }
        
        self._initialized = True
        print("[RiskAlertEngine] Initialized")
    
    def evaluate_alerts(self, metrics: RiskMetrics, exposure: ExposureMetrics, concentration: ConcentrationMetrics, tail: TailRiskMetrics) -> List[RiskAlert]:
        """Evaluate all metrics and generate alerts."""
        new_alerts = []
        
        # Drawdown alerts
        dd_alert = self._check_drawdown(metrics.current_drawdown_pct)
        if dd_alert:
            new_alerts.append(dd_alert)
        
        # Daily loss alerts
        dl_alert = self._check_daily_loss(metrics.daily_loss_pct)
        if dl_alert:
            new_alerts.append(dl_alert)
        
        # Leverage alerts
        lev_alert = self._check_leverage(exposure.current_leverage)
        if lev_alert:
            new_alerts.append(lev_alert)
        
        # Concentration alerts
        conc_alert = self._check_concentration(concentration.max_asset_weight_pct, concentration.max_asset)
        if conc_alert:
            new_alerts.append(conc_alert)
        
        # VaR alerts
        var_alert = self._check_var(tail.var_95_pct)
        if var_alert:
            new_alerts.append(var_alert)
        
        # Update active alerts
        self._update_alerts(new_alerts)
        
        return new_alerts
    
    def _check_drawdown(self, dd_pct: float) -> Optional[RiskAlert]:
        if dd_pct >= self._thresholds["drawdown_critical"]:
            return RiskAlert(
                alert_type=AlertType.DRAWDOWN, severity=AlertSeverity.CRITICAL,
                title="Critical Drawdown", message=f"Drawdown at {dd_pct*100:.1f}% - exceeds critical threshold",
                metric_name="drawdown_pct", current_value=dd_pct, threshold_value=self._thresholds["drawdown_critical"],
                suggested_action="Consider switching to CONSERVATIVE profile or pausing trading"
            )
        elif dd_pct >= self._thresholds["drawdown_high"]:
            return RiskAlert(
                alert_type=AlertType.DRAWDOWN, severity=AlertSeverity.HIGH,
                title="High Drawdown", message=f"Drawdown at {dd_pct*100:.1f}%",
                metric_name="drawdown_pct", current_value=dd_pct, threshold_value=self._thresholds["drawdown_high"],
                suggested_action="Monitor closely, consider risk reduction"
            )
        elif dd_pct >= self._thresholds["drawdown_warning"]:
            return RiskAlert(
                alert_type=AlertType.DRAWDOWN, severity=AlertSeverity.WARNING,
                title="Elevated Drawdown", message=f"Drawdown at {dd_pct*100:.1f}%",
                metric_name="drawdown_pct", current_value=dd_pct, threshold_value=self._thresholds["drawdown_warning"],
                suggested_action="Monitor situation"
            )
        return None
    
    def _check_daily_loss(self, loss_pct: float) -> Optional[RiskAlert]:
        if loss_pct >= self._thresholds["daily_loss_critical"]:
            return RiskAlert(
                alert_type=AlertType.DAILY_LOSS, severity=AlertSeverity.CRITICAL,
                title="Daily Loss Limit Breached", message=f"Daily loss {loss_pct*100:.1f}% exceeds 5% limit",
                metric_name="daily_loss_pct", current_value=loss_pct, threshold_value=self._thresholds["daily_loss_critical"],
                suggested_action="Switch to CONSERVATIVE immediately"
            )
        elif loss_pct >= self._thresholds["daily_loss_high"]:
            return RiskAlert(
                alert_type=AlertType.DAILY_LOSS, severity=AlertSeverity.HIGH,
                title="Near Daily Loss Limit", message=f"Daily loss at {loss_pct*100:.1f}%",
                metric_name="daily_loss_pct", current_value=loss_pct, threshold_value=self._thresholds["daily_loss_high"],
                suggested_action="Reduce position sizes"
            )
        return None
    
    def _check_leverage(self, leverage: float) -> Optional[RiskAlert]:
        if leverage >= self._thresholds["leverage_critical"]:
            return RiskAlert(
                alert_type=AlertType.LEVERAGE, severity=AlertSeverity.CRITICAL,
                title="Critical Leverage", message=f"Leverage at {leverage:.1f}x - extremely high",
                metric_name="leverage", current_value=leverage, threshold_value=self._thresholds["leverage_critical"],
                suggested_action="Reduce positions immediately"
            )
        elif leverage >= self._thresholds["leverage_high"]:
            return RiskAlert(
                alert_type=AlertType.LEVERAGE, severity=AlertSeverity.HIGH,
                title="High Leverage", message=f"Leverage at {leverage:.1f}x",
                metric_name="leverage", current_value=leverage, threshold_value=self._thresholds["leverage_high"],
                suggested_action="Consider reducing leverage"
            )
        return None
    
    def _check_concentration(self, max_weight: float, max_asset: str) -> Optional[RiskAlert]:
        if max_weight >= self._thresholds["concentration_high"]:
            return RiskAlert(
                alert_type=AlertType.CONCENTRATION, severity=AlertSeverity.HIGH,
                title="High Concentration Risk", message=f"{max_asset} represents {max_weight*100:.0f}% of portfolio",
                metric_name="max_asset_weight", current_value=max_weight, threshold_value=self._thresholds["concentration_high"],
                suggested_action="Diversify holdings"
            )
        elif max_weight >= self._thresholds["concentration_warning"]:
            return RiskAlert(
                alert_type=AlertType.CONCENTRATION, severity=AlertSeverity.WARNING,
                title="Concentration Warning", message=f"{max_asset} at {max_weight*100:.0f}% of portfolio",
                metric_name="max_asset_weight", current_value=max_weight, threshold_value=self._thresholds["concentration_warning"],
                suggested_action="Monitor concentration"
            )
        return None
    
    def _check_var(self, var_95: float) -> Optional[RiskAlert]:
        var_abs = abs(var_95)
        if var_abs >= self._thresholds["var95_high"]:
            return RiskAlert(
                alert_type=AlertType.VAR, severity=AlertSeverity.HIGH,
                title="High Tail Risk", message=f"VaR95 at {var_abs*100:.1f}% potential loss",
                metric_name="var_95", current_value=var_abs, threshold_value=self._thresholds["var95_high"],
                suggested_action="Review risk exposure"
            )
        elif var_abs >= self._thresholds["var95_warning"]:
            return RiskAlert(
                alert_type=AlertType.VAR, severity=AlertSeverity.WARNING,
                title="Elevated Tail Risk", message=f"VaR95 at {var_abs*100:.1f}%",
                metric_name="var_95", current_value=var_abs, threshold_value=self._thresholds["var95_warning"],
                suggested_action="Monitor tail risk"
            )
        return None
    
    def _update_alerts(self, new_alerts: List[RiskAlert]) -> None:
        """Update active alerts, resolve old ones."""
        new_types = {a.alert_type for a in new_alerts}
        
        # Resolve alerts no longer triggered
        for alert_id, alert in list(self._alerts.items()):
            if alert.alert_type not in new_types and alert.is_active:
                alert.is_active = False
                alert.resolved_at = datetime.now(timezone.utc)
                self._alert_history.append(alert)
                del self._alerts[alert_id]
        
        # Add new alerts
        for alert in new_alerts:
            existing = next((a for a in self._alerts.values() if a.alert_type == alert.alert_type), None)
            if existing:
                existing.current_value = alert.current_value
                existing.message = alert.message
                existing.severity = alert.severity
            else:
                self._alerts[alert.alert_id] = alert
    
    def get_active_alerts(self) -> List[RiskAlert]:
        return [a for a in self._alerts.values() if a.is_active]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        if alert_id in self._alerts:
            self._alerts[alert_id].acknowledged = True
            self._alerts[alert_id].acknowledged_by = acknowledged_by
            self._alerts[alert_id].acknowledged_at = datetime.now(timezone.utc)
            return True
        return False
    
    def get_alert_history(self, limit: int = 50) -> List[RiskAlert]:
        return list(reversed(self._alert_history[-limit:]))
    
    def get_health(self) -> Dict[str, Any]:
        return {"service": "RiskAlertEngine", "status": "healthy", "phase": "TR4", "active_alerts": len(self.get_active_alerts())}


risk_alert_engine = RiskAlertEngine()
