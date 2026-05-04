"""
Alerts Engine

PHASE 40.3 — Alerts + Audit Engine

Generates system alerts for dashboard.

Alert categories:
- RISK: Portfolio risk, drawdown
- LIQUIDITY: Impact, vacuum
- EXECUTION: Blocked, failed
- MARKET: Regime shift, cascade
- SYSTEM: Connection, latency
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from .dashboard_types import DashboardAlert, AlertSeverity


# ══════════════════════════════════════════════════════════════
# Alert Thresholds
# ══════════════════════════════════════════════════════════════

ALERT_THRESHOLDS = {
    # Risk alerts
    "PORTFOLIO_RISK_WARNING": 0.15,
    "PORTFOLIO_RISK_CRITICAL": 0.18,
    "PORTFOLIO_RISK_EMERGENCY": 0.22,
    
    # Drawdown
    "DRAWDOWN_WARNING": 0.03,
    "DRAWDOWN_CRITICAL": 0.05,
    "DRAWDOWN_EMERGENCY": 0.10,
    
    # Execution
    "SLIPPAGE_WARNING_BPS": 30,
    "SLIPPAGE_CRITICAL_BPS": 75,
    
    # Liquidity
    "IMPACT_WARNING_BPS": 50,
    "IMPACT_CRITICAL_BPS": 100,
}


# ══════════════════════════════════════════════════════════════
# Alerts Engine
# ══════════════════════════════════════════════════════════════

class AlertsEngine:
    """
    Alerts Engine — PHASE 40.3
    
    Generates and manages system alerts.
    """
    
    def __init__(self, retention_hours: int = 24):
        self._alerts: Dict[str, DashboardAlert] = {}
        self._history: List[DashboardAlert] = []
        self._retention_hours = retention_hours
        
        # Alert counters (for deduplication)
        self._alert_counts: Dict[str, int] = defaultdict(int)
        self._last_alert_times: Dict[str, datetime] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Create Alert
    # ═══════════════════════════════════════════════════════════
    
    def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        category: str,
        source: str,
        symbol: str = "SYSTEM",
        value: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> DashboardAlert:
        """Create new alert."""
        # Dedupe key
        dedupe_key = f"{category}:{title}:{symbol}"
        
        # Check if similar alert recently created
        if self._should_dedupe(dedupe_key):
            # Update existing alert
            existing = self._find_existing_alert(dedupe_key)
            if existing:
                existing.message = message
                existing.value = value
                existing.created_at = datetime.now(timezone.utc)
                return existing
        
        alert = DashboardAlert(
            symbol=symbol,
            severity=severity,
            title=title,
            message=message,
            source=source,
            category=category,
            value=value,
            threshold=threshold,
        )
        
        self._alerts[alert.alert_id] = alert
        self._alert_counts[dedupe_key] += 1
        self._last_alert_times[dedupe_key] = datetime.now(timezone.utc)
        
        return alert
    
    def _should_dedupe(self, key: str, min_interval_seconds: int = 60) -> bool:
        """Check if alert should be deduplicated."""
        if key not in self._last_alert_times:
            return False
        
        elapsed = (datetime.now(timezone.utc) - self._last_alert_times[key]).total_seconds()
        return elapsed < min_interval_seconds
    
    def _find_existing_alert(self, dedupe_key: str) -> Optional[DashboardAlert]:
        """Find existing alert matching dedupe key."""
        for alert in self._alerts.values():
            key = f"{alert.category}:{alert.title}:{alert.symbol}"
            if key == dedupe_key:
                return alert
        return None
    
    # ═══════════════════════════════════════════════════════════
    # 2. Get Alerts
    # ═══════════════════════════════════════════════════════════
    
    def get_active_alerts(
        self,
        symbol: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50,
    ) -> List[DashboardAlert]:
        """Get active alerts."""
        # Clean expired
        self._clean_expired()
        
        alerts = list(self._alerts.values())
        
        # Filter
        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol or a.symbol == "SYSTEM"]
        if category:
            alerts = [a for a in alerts if a.category == category]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by severity then time
        severity_order = {"EMERGENCY": 0, "CRITICAL": 1, "WARNING": 2, "INFO": 3}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), -a.created_at.timestamp()))
        
        return alerts[:limit]
    
    def get_alert(self, alert_id: str) -> Optional[DashboardAlert]:
        """Get alert by ID."""
        return self._alerts.get(alert_id)
    
    def get_alert_count(
        self,
        severity: Optional[AlertSeverity] = None,
    ) -> int:
        """Get count of active alerts."""
        alerts = list(self._alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return len(alerts)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Acknowledge Alert
    # ═══════════════════════════════════════════════════════════
    
    def acknowledge_alert(
        self,
        alert_id: str,
        user: str = "operator",
    ) -> bool:
        """Acknowledge alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.acknowledged = True
        alert.acknowledged_by = user
        alert.acknowledged_at = datetime.now(timezone.utc)
        
        return True
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss alert (remove)."""
        if alert_id not in self._alerts:
            return False
        
        alert = self._alerts.pop(alert_id)
        self._history.append(alert)
        
        return True
    
    # ═══════════════════════════════════════════════════════════
    # 4. Generate Alerts from System State
    # ═══════════════════════════════════════════════════════════
    
    def check_risk_alerts(self):
        """Check and generate risk-related alerts."""
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            state = engine.get_portfolio_risk_budget()
            
            risk = state.total_risk
            
            if risk > ALERT_THRESHOLDS["PORTFOLIO_RISK_EMERGENCY"]:
                self.create_alert(
                    title="Portfolio Risk Emergency",
                    message=f"Portfolio risk at {risk*100:.1f}% - IMMEDIATE ACTION REQUIRED",
                    severity="EMERGENCY",
                    category="RISK",
                    source="RiskBudgetEngine",
                    value=risk,
                    threshold=ALERT_THRESHOLDS["PORTFOLIO_RISK_EMERGENCY"],
                )
            elif risk > ALERT_THRESHOLDS["PORTFOLIO_RISK_CRITICAL"]:
                self.create_alert(
                    title="Portfolio Risk Critical",
                    message=f"Portfolio risk at {risk*100:.1f}% exceeds {ALERT_THRESHOLDS['PORTFOLIO_RISK_CRITICAL']*100:.0f}% threshold",
                    severity="CRITICAL",
                    category="RISK",
                    source="RiskBudgetEngine",
                    value=risk,
                    threshold=ALERT_THRESHOLDS["PORTFOLIO_RISK_CRITICAL"],
                )
            elif risk > ALERT_THRESHOLDS["PORTFOLIO_RISK_WARNING"]:
                self.create_alert(
                    title="Portfolio Risk Elevated",
                    message=f"Portfolio risk at {risk*100:.1f}% approaching limit",
                    severity="WARNING",
                    category="RISK",
                    source="RiskBudgetEngine",
                    value=risk,
                    threshold=ALERT_THRESHOLDS["PORTFOLIO_RISK_WARNING"],
                )
                
        except Exception:
            pass
    
    def check_execution_alerts(self):
        """Check and generate execution-related alerts."""
        try:
            from modules.execution_gateway import get_gateway_repository
            repo = get_gateway_repository()
            
            stats = repo.get_fill_statistics(hours_back=1)
            avg_slippage = stats.get("avg_slippage_bps", 0)
            
            if avg_slippage > ALERT_THRESHOLDS["SLIPPAGE_CRITICAL_BPS"]:
                self.create_alert(
                    title="High Slippage Detected",
                    message=f"Average slippage {avg_slippage:.1f} bps in last hour",
                    severity="CRITICAL",
                    category="EXECUTION",
                    source="ExecutionGateway",
                    value=avg_slippage,
                    threshold=ALERT_THRESHOLDS["SLIPPAGE_CRITICAL_BPS"],
                )
            elif avg_slippage > ALERT_THRESHOLDS["SLIPPAGE_WARNING_BPS"]:
                self.create_alert(
                    title="Elevated Slippage",
                    message=f"Average slippage {avg_slippage:.1f} bps in last hour",
                    severity="WARNING",
                    category="EXECUTION",
                    source="ExecutionGateway",
                    value=avg_slippage,
                    threshold=ALERT_THRESHOLDS["SLIPPAGE_WARNING_BPS"],
                )
                
        except Exception:
            pass
    
    def check_liquidity_alerts(self, symbol: str = "BTC"):
        """Check and generate liquidity-related alerts."""
        try:
            from modules.execution.slippage import get_liquidity_impact_engine
            engine = get_liquidity_impact_engine()
            
            impact = engine.estimate_impact(
                symbol=symbol,
                size_usd=100000,
                side="BUY",
            )
            
            impact_bps = impact.get("impact_bps", 0)
            
            if impact_bps > ALERT_THRESHOLDS["IMPACT_CRITICAL_BPS"]:
                self.create_alert(
                    title="Liquidity Vacuum",
                    message=f"{symbol} liquidity critically low - impact {impact_bps:.0f} bps",
                    severity="CRITICAL",
                    category="LIQUIDITY",
                    source="LiquidityImpactEngine",
                    symbol=symbol,
                    value=impact_bps,
                    threshold=ALERT_THRESHOLDS["IMPACT_CRITICAL_BPS"],
                )
            elif impact_bps > ALERT_THRESHOLDS["IMPACT_WARNING_BPS"]:
                self.create_alert(
                    title="Low Liquidity",
                    message=f"{symbol} liquidity reduced - impact {impact_bps:.0f} bps",
                    severity="WARNING",
                    category="LIQUIDITY",
                    source="LiquidityImpactEngine",
                    symbol=symbol,
                    value=impact_bps,
                    threshold=ALERT_THRESHOLDS["IMPACT_WARNING_BPS"],
                )
                
        except Exception:
            pass
    
    def check_regime_alerts(self, symbol: str = "BTC"):
        """Check for regime shift alerts."""
        try:
            from modules.regime_intelligence_v2 import get_regime_engine_v2
            engine = get_regime_engine_v2()
            
            transition = engine.get_recent_transition(symbol)
            if transition:
                if transition.get("is_shift", False):
                    self.create_alert(
                        title="Regime Shift Detected",
                        message=f"{symbol} regime shifted from {transition.get('from')} to {transition.get('to')}",
                        severity="WARNING",
                        category="MARKET",
                        source="RegimeEngine",
                        symbol=symbol,
                    )
        except Exception:
            pass
    
    def run_all_checks(self):
        """Run all alert checks."""
        self.check_risk_alerts()
        self.check_execution_alerts()
        
        for symbol in ["BTC", "ETH", "SOL"]:
            self.check_liquidity_alerts(symbol)
            self.check_regime_alerts(symbol)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _clean_expired(self):
        """Clean expired alerts."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._retention_hours)
        
        expired = []
        for alert_id, alert in self._alerts.items():
            if alert.created_at < cutoff:
                expired.append(alert_id)
            elif alert.expires_at and datetime.now(timezone.utc) > alert.expires_at:
                expired.append(alert_id)
        
        for alert_id in expired:
            alert = self._alerts.pop(alert_id)
            self._history.append(alert)
    
    def get_history(self, limit: int = 100) -> List[DashboardAlert]:
        """Get alert history."""
        return self._history[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get alert statistics."""
        active = list(self._alerts.values())
        
        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        
        for alert in active:
            by_severity[alert.severity] += 1
            by_category[alert.category] += 1
        
        return {
            "total_active": len(active),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "acknowledged": sum(1 for a in active if a.acknowledged),
            "unacknowledged": sum(1 for a in active if not a.acknowledged),
            "history_count": len(self._history),
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_alerts_engine: Optional[AlertsEngine] = None


def get_alerts_engine() -> AlertsEngine:
    """Get singleton instance."""
    global _alerts_engine
    if _alerts_engine is None:
        _alerts_engine = AlertsEngine()
    return _alerts_engine
