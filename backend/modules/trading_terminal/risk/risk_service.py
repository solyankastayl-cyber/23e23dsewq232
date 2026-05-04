"""
Risk Service (TR4)
==================

Main service orchestrating risk monitoring.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .risk_types import PortfolioRiskState, RiskMetrics, ExposureMetrics, ConcentrationMetrics, TailRiskMetrics, RiskAlert, RiskGuardrailEvent
from .risk_metrics import risk_metrics_calculator
from .risk_alert_engine import risk_alert_engine
from .risk_guardrails import risk_guardrails


class RiskService:
    """Main Risk Dashboard Service."""
    
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
        
        # Snapshot history
        self._snapshots: List[PortfolioRiskState] = []
        self._max_snapshots = 500
        
        # VaR cache (from Monte Carlo)
        self._tail_risk = TailRiskMetrics()
        
        # Connect guardrails to strategy switch
        self._connect_guardrails()
        
        self._initialized = True
        print("[RiskService] Initialized")
    
    def _connect_guardrails(self):
        """Connect guardrails to strategy switching."""
        def on_guardrail_action(action_type: str, reason: str):
            if action_type == "switch_conservative":
                try:
                    from ...trading_capsule.strategy_switch import strategy_switch_service
                    strategy_switch_service.manual_switch("CONSERVATIVE", reason=f"Guardrail: {reason}", initiated_by="risk_guardrails")
                except ImportError:
                    print(f"[RiskService] Cannot switch - STR3 not available: {reason}")
        
        risk_guardrails.set_action_callback(on_guardrail_action)
    
    def get_risk_state(self, portfolio_state=None) -> PortfolioRiskState:
        """Get complete risk state."""
        # Get portfolio data
        if portfolio_state is None:
            try:
                from ..portfolio import portfolio_service
                portfolio_state = portfolio_service.get_portfolio_state()
            except ImportError:
                portfolio_state = None
        
        equity = portfolio_state.total_equity if portfolio_state else 0
        
        # Calculate metrics
        metrics = risk_metrics_calculator.calculate_risk_metrics(equity)
        exposure = risk_metrics_calculator.calculate_exposure_metrics(portfolio_state) if portfolio_state else ExposureMetrics()
        concentration = risk_metrics_calculator.calculate_concentration_metrics(portfolio_state) if portfolio_state else ConcentrationMetrics()
        
        # Calculate risk level
        level, reason = risk_metrics_calculator.calculate_risk_level(metrics, exposure, concentration, self._tail_risk)
        
        # Evaluate alerts
        alerts = risk_alert_engine.evaluate_alerts(metrics, exposure, concentration, self._tail_risk)
        
        # Evaluate guardrails
        guardrail_events = risk_guardrails.evaluate_guardrails(metrics, exposure)
        
        # Build state
        state = PortfolioRiskState(
            risk_level=level,
            risk_level_reason=reason,
            equity_usd=equity,
            metrics=metrics,
            exposure=exposure,
            concentration=concentration,
            tail_risk=self._tail_risk,
            active_alerts_count=len(risk_alert_engine.get_active_alerts())
        )
        
        # Store snapshot
        self._snapshots.append(state)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        
        return state
    
    def get_metrics(self) -> RiskMetrics:
        """Get risk metrics."""
        state = self.get_risk_state()
        return state.metrics
    
    def get_exposure(self) -> ExposureMetrics:
        """Get exposure metrics."""
        state = self.get_risk_state()
        return state.exposure
    
    def get_concentration(self) -> ConcentrationMetrics:
        """Get concentration metrics."""
        state = self.get_risk_state()
        return state.concentration
    
    def get_tail_risk(self) -> TailRiskMetrics:
        """Get tail risk metrics."""
        return self._tail_risk
    
    def update_tail_risk(self, var_95: float, cvar_95: float, var_99: float = 0, cvar_99: float = 0) -> None:
        """Update VaR/CVaR from Monte Carlo."""
        self._tail_risk = TailRiskMetrics(
            var_95_pct=var_95, var_99_pct=var_99,
            cvar_95_pct=cvar_95, cvar_99_pct=cvar_99,
            last_calculated_at=datetime.now(timezone.utc)
        )
    
    def get_alerts(self, active_only: bool = True) -> List[RiskAlert]:
        """Get risk alerts."""
        if active_only:
            return risk_alert_engine.get_active_alerts()
        return risk_alert_engine.get_alert_history()
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "admin") -> bool:
        """Acknowledge an alert."""
        return risk_alert_engine.acknowledge_alert(alert_id, acknowledged_by)
    
    def get_guardrail_events(self, limit: int = 50) -> List[RiskGuardrailEvent]:
        """Get guardrail events."""
        return risk_guardrails.get_events(limit)
    
    def get_guardrail_rules(self) -> Dict[str, Any]:
        """Get guardrail rules."""
        return risk_guardrails.get_rules()
    
    def enable_guardrail(self, rule_name: str) -> bool:
        return risk_guardrails.enable_rule(rule_name)
    
    def disable_guardrail(self, rule_name: str) -> bool:
        return risk_guardrails.disable_rule(rule_name)
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data."""
        state = self.get_risk_state()
        dashboard = state.to_dashboard_dict()
        dashboard["alerts"] = [a.alert_type.value for a in risk_alert_engine.get_active_alerts()]
        return dashboard
    
    def get_snapshots(self, limit: int = 100) -> List[PortfolioRiskState]:
        """Get snapshot history."""
        return list(reversed(self._snapshots[-limit:]))
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health."""
        return {
            "module": "Risk Dashboard",
            "phase": "TR4",
            "status": "healthy",
            "components": {
                "metrics_calculator": risk_metrics_calculator.get_health(),
                "alert_engine": risk_alert_engine.get_health(),
                "guardrails": risk_guardrails.get_health()
            },
            "snapshots_stored": len(self._snapshots)
        }


risk_service = RiskService()
