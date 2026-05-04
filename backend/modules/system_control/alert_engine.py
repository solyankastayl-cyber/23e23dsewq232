"""
Alert Engine

PHASE 33 — System Control Layer

System alert generation and management.
"""

import hashlib
import uuid
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta

from .control_types import (
    Alert,
    AlertType,
    SeverityType,
    ALERT_TYPES,
)


# ══════════════════════════════════════════════════════════════
# Alert Thresholds
# ══════════════════════════════════════════════════════════════

ALERT_THRESHOLDS = {
    "regime_shift_confidence": 0.7,
    "liquidity_stress": 0.6,
    "cascade_probability": 0.25,
    "scenario_change_probability": 0.15,
    "risk_escalation": 0.6,
    "opportunity_confidence": 0.7,
}


# ══════════════════════════════════════════════════════════════
# Alert Engine
# ══════════════════════════════════════════════════════════════

class AlertEngine:
    """
    Alert Engine — PHASE 33
    
    Generates and manages system alerts.
    
    Alert triggers:
    - Regime shift
    - Liquidity vacuum/stress
    - Cascade probability
    - Scenario change
    - Risk escalation
    - Opportunity detection
    """
    
    def __init__(self):
        self._alerts: Dict[str, List[Alert]] = {}
        self._active_alerts: Dict[str, List[Alert]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Alert Generation
    # ═══════════════════════════════════════════════════════════
    
    def check_and_generate_alerts(
        self,
        symbol: str,
    ) -> List[Alert]:
        """
        Check all alert conditions and generate alerts.
        """
        symbol = symbol.upper()
        
        new_alerts = []
        
        # Check regime shift
        regime_alert = self._check_regime_shift(symbol)
        if regime_alert:
            new_alerts.append(regime_alert)
        
        # Check liquidity event
        liquidity_alert = self._check_liquidity_event(symbol)
        if liquidity_alert:
            new_alerts.append(liquidity_alert)
        
        # Check cascade risk
        cascade_alert = self._check_cascade_risk(symbol)
        if cascade_alert:
            new_alerts.append(cascade_alert)
        
        # Check scenario change
        scenario_alert = self._check_scenario_change(symbol)
        if scenario_alert:
            new_alerts.append(scenario_alert)
        
        # Check risk escalation
        risk_alert = self._check_risk_escalation(symbol)
        if risk_alert:
            new_alerts.append(risk_alert)
        
        # Check opportunity
        opportunity_alert = self._check_opportunity(symbol)
        if opportunity_alert:
            new_alerts.append(opportunity_alert)
        
        # Store alerts
        for alert in new_alerts:
            self._store_alert(symbol, alert)
        
        return new_alerts
    
    def _check_regime_shift(self, symbol: str) -> Optional[Alert]:
        """Check for regime shift alert."""
        try:
            from modules.regime_intelligence_v2 import get_regime_engine
            engine = get_regime_engine()
            regime = engine.get_current_regime(symbol)
            if regime:
                transition = regime.transition_state if hasattr(regime, 'transition_state') else "STABLE"
                if transition == "ACTIVE_TRANSITION":
                    return self._create_alert(
                        symbol=symbol,
                        alert_type="MARKET_SHIFT",
                        severity="WARNING",
                        title="Regime Shift Detected",
                        message=f"{symbol} entering active regime transition from {regime.regime_type}",
                        trigger_value=regime.confidence,
                        threshold_value=ALERT_THRESHOLDS["regime_shift_confidence"],
                    )
        except Exception:
            pass
        
        return None
    
    def _check_liquidity_event(self, symbol: str) -> Optional[Alert]:
        """Check for liquidity stress event."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_engine
            engine = get_microstructure_engine()
            snapshot = engine.get_current_snapshot(symbol)
            if snapshot:
                if snapshot.microstructure_state == "STRESSED":
                    stress = snapshot.stress_indicator if hasattr(snapshot, 'stress_indicator') else 0.8
                    return self._create_alert(
                        symbol=symbol,
                        alert_type="LIQUIDITY_EVENT",
                        severity="CRITICAL",
                        title="Liquidity Stress",
                        message=f"{symbol} microstructure under stress - liquidity impaired",
                        trigger_value=stress,
                        threshold_value=ALERT_THRESHOLDS["liquidity_stress"],
                    )
                elif snapshot.microstructure_state == "FRAGILE":
                    return self._create_alert(
                        symbol=symbol,
                        alert_type="LIQUIDITY_EVENT",
                        severity="WARNING",
                        title="Fragile Liquidity",
                        message=f"{symbol} showing fragile microstructure conditions",
                        trigger_value=0.6,
                        threshold_value=ALERT_THRESHOLDS["liquidity_stress"],
                    )
        except Exception:
            pass
        
        return None
    
    def _check_cascade_risk(self, symbol: str) -> Optional[Alert]:
        """Check for cascade risk alert."""
        try:
            from modules.market_simulation import get_simulation_engine
            engine = get_simulation_engine()
            result = engine.get_current_simulation(symbol)
            if result:
                for scenario in result.scenarios:
                    if scenario.scenario_type == "LIQUIDATION_EVENT":
                        if scenario.probability > ALERT_THRESHOLDS["cascade_probability"]:
                            return self._create_alert(
                                symbol=symbol,
                                alert_type="CASCADE_RISK",
                                severity="CRITICAL",
                                title="Cascade Risk Elevated",
                                message=f"{symbol} liquidation scenario probability elevated: {scenario.probability:.1%}",
                                trigger_value=scenario.probability,
                                threshold_value=ALERT_THRESHOLDS["cascade_probability"],
                            )
                        break
        except Exception:
            pass
        
        return None
    
    def _check_scenario_change(self, symbol: str) -> Optional[Alert]:
        """Check for significant scenario change."""
        try:
            from modules.market_simulation import get_simulation_engine
            engine = get_simulation_engine()
            
            # Compare current with previous
            history = engine.get_history(symbol, 2)
            if len(history) >= 2:
                current = history[0]
                previous = history[1]
                
                if current.top_scenario and previous.top_scenario:
                    if current.top_scenario.scenario_type != previous.top_scenario.scenario_type:
                        prob_change = current.top_scenario.probability - previous.top_scenario.probability
                        if abs(prob_change) > ALERT_THRESHOLDS["scenario_change_probability"]:
                            return self._create_alert(
                                symbol=symbol,
                                alert_type="SCENARIO_CHANGE",
                                severity="INFO",
                                title="Scenario Change",
                                message=f"{symbol} top scenario changed: {previous.top_scenario.scenario_type} → {current.top_scenario.scenario_type}",
                                trigger_value=abs(prob_change),
                                threshold_value=ALERT_THRESHOLDS["scenario_change_probability"],
                            )
        except Exception:
            pass
        
        return None
    
    def _check_risk_escalation(self, symbol: str) -> Optional[Alert]:
        """Check for risk level escalation."""
        try:
            from .risk_engine import get_risk_engine
            engine = get_risk_engine()
            risk = engine.get_current_risk(symbol)
            
            if risk is None:
                risk = engine.assess_risk(symbol)
            
            if risk.risk_level == "EXTREME":
                return self._create_alert(
                    symbol=symbol,
                    alert_type="RISK_ALERT",
                    severity="CRITICAL",
                    title="Extreme Risk Level",
                    message=f"{symbol} risk level EXTREME - consider risk reduction",
                    trigger_value=risk.risk_score,
                    threshold_value=ALERT_THRESHOLDS["risk_escalation"],
                )
            elif risk.risk_level == "HIGH" and risk.risk_score > 0.6:
                return self._create_alert(
                    symbol=symbol,
                    alert_type="RISK_ALERT",
                    severity="WARNING",
                    title="High Risk Level",
                    message=f"{symbol} risk elevated - factors: {', '.join(risk.risk_factors[:3])}",
                    trigger_value=risk.risk_score,
                    threshold_value=ALERT_THRESHOLDS["risk_escalation"],
                )
        except Exception:
            pass
        
        return None
    
    def _check_opportunity(self, symbol: str) -> Optional[Alert]:
        """Check for trading opportunity."""
        try:
            from .decision_engine import get_decision_engine
            engine = get_decision_engine()
            decision = engine.get_current_decision(symbol)
            
            if decision is None:
                decision = engine.generate_decision(symbol)
            
            if (decision.market_state in ["BREAKOUT_SETUP", "TRENDING"] 
                and decision.confidence > ALERT_THRESHOLDS["opportunity_confidence"]
                and decision.risk_level in ["LOW", "MEDIUM"]):
                return self._create_alert(
                    symbol=symbol,
                    alert_type="OPPORTUNITY",
                    severity="INFO",
                    title="Trading Opportunity",
                    message=f"{symbol} {decision.market_state} setup detected - {decision.recommended_direction} signal",
                    trigger_value=decision.confidence,
                    threshold_value=ALERT_THRESHOLDS["opportunity_confidence"],
                )
        except Exception:
            pass
        
        return None
    
    def _create_alert(
        self,
        symbol: str,
        alert_type: AlertType,
        severity: SeverityType,
        title: str,
        message: str,
        trigger_value: float,
        threshold_value: float,
    ) -> Alert:
        """Create alert object."""
        alert_id = f"{symbol}_{alert_type}_{uuid.uuid4().hex[:8]}"
        
        # Set expiry based on severity
        expiry_hours = {"INFO": 1, "WARNING": 4, "CRITICAL": 8}
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours.get(severity, 2))
        
        return Alert(
            alert_id=alert_id,
            symbol=symbol,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            trigger_value=trigger_value,
            threshold_value=threshold_value,
            expires_at=expires_at,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Storage and Retrieval
    # ═══════════════════════════════════════════════════════════
    
    def _store_alert(
        self,
        symbol: str,
        alert: Alert,
    ) -> None:
        """Store alert."""
        if symbol not in self._alerts:
            self._alerts[symbol] = []
        self._alerts[symbol].append(alert)
        
        if symbol not in self._active_alerts:
            self._active_alerts[symbol] = []
        self._active_alerts[symbol].append(alert)
    
    def get_active_alerts(
        self,
        symbol: str,
    ) -> List[Alert]:
        """Get active (non-expired, non-acknowledged) alerts."""
        now = datetime.now(timezone.utc)
        alerts = self._active_alerts.get(symbol.upper(), [])
        
        active = []
        for alert in alerts:
            if not alert.acknowledged:
                if alert.expires_at is None or alert.expires_at > now:
                    active.append(alert)
        
        return sorted(active, key=lambda a: a.created_at, reverse=True)
    
    def get_all_alerts(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[Alert]:
        """Get all alerts for symbol."""
        alerts = self._alerts.get(symbol.upper(), [])
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)[:limit]
    
    def acknowledge_alert(
        self,
        symbol: str,
        alert_id: str,
    ) -> bool:
        """Acknowledge an alert."""
        alerts = self._active_alerts.get(symbol.upper(), [])
        for alert in alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def get_alerts_by_severity(
        self,
        symbol: str,
        severity: SeverityType,
    ) -> List[Alert]:
        """Get alerts by severity."""
        alerts = self.get_active_alerts(symbol)
        return [a for a in alerts if a.severity == severity]
    
    def get_critical_alerts(
        self,
        symbol: str,
    ) -> List[Alert]:
        """Get critical alerts."""
        return self.get_alerts_by_severity(symbol, "CRITICAL")


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_alert_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    """Get singleton instance of AlertEngine."""
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertEngine()
    return _alert_engine
