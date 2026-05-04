"""
Health Alert Engine
===================

PHASE 3.2 - Generates and manages health alerts for positions.
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .health_types import (
    HealthStatus,
    AlertSeverity,
    HealthAlert,
    AdvancedTradeHealthScore
)


class HealthAlertEngine:
    """
    Generates alerts based on health conditions:
    - INFO: Informational updates
    - WARNING: Attention needed
    - CRITICAL: Immediate action required
    - EMERGENCY: Position at extreme risk
    """
    
    def __init__(self):
        # Alert thresholds
        self._thresholds = {
            "health_critical": 25,
            "health_warning": 40,
            "rapid_decline_rate": 5,  # Per bar
            "stability_low": 30,
            "stop_proximity_pct": 25
        }
        
        # Alert TTL
        self._alert_ttl = {
            AlertSeverity.INFO: 4 * 3600 * 1000,      # 4 hours
            AlertSeverity.WARNING: 2 * 3600 * 1000,   # 2 hours
            AlertSeverity.CRITICAL: 1 * 3600 * 1000,  # 1 hour
            AlertSeverity.EMERGENCY: 30 * 60 * 1000   # 30 min
        }
        
        # Action recommendations
        self._action_map = {
            AlertSeverity.INFO: ("MONITOR", "LOW"),
            AlertSeverity.WARNING: ("MONITOR", "MEDIUM"),
            AlertSeverity.CRITICAL: ("REDUCE", "HIGH"),
            AlertSeverity.EMERGENCY: ("CLOSE", "IMMEDIATE")
        }
        
        # Tracking
        self._position_alerts: Dict[str, List[HealthAlert]] = {}
        
        print("[HealthAlertEngine] Initialized (PHASE 3.2)")
    
    def generate_alerts(
        self,
        position_id: str,
        health: AdvancedTradeHealthScore
    ) -> List[HealthAlert]:
        """
        Generate alerts based on current health state.
        """
        
        alerts = []
        now = int(time.time() * 1000)
        
        # Check for critical health
        if health.current_health <= self._thresholds["health_critical"]:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.EMERGENCY if health.current_health <= 15 else AlertSeverity.CRITICAL,
                title="Critical Health Level",
                message=f"Position health at {health.current_health:.0f}%. Status: {health.status.value}",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check for warning health
        elif health.current_health <= self._thresholds["health_warning"]:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.WARNING,
                title="Low Health Warning",
                message=f"Position health declining: {health.current_health:.0f}%",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check for rapid decline
        if health.health_trend == "DETERIORATING" and health.trend_strength > 0.6:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.WARNING if health.current_health > 50 else AlertSeverity.CRITICAL,
                title="Rapid Health Decline",
                message=f"Health declining rapidly ({health.trend_strength:.0%} strength). Change: {health.health_change:.1f}",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check stability
        if health.stability and health.stability.stability_score < self._thresholds["stability_low"]:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.WARNING,
                title="Low Stability",
                message=f"Trade stability at {health.stability.stability_score:.0f}%",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check stop approach
        if health.pnl_health < 25:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.CRITICAL,
                title="Stop Loss Approach",
                message=f"Position approaching stop loss. PnL health: {health.pnl_health:.0f}%",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check momentum loss
        if health.momentum_health < 30:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.INFO,
                title="Momentum Weakening",
                message=f"Momentum health at {health.momentum_health:.0f}%",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check structure break
        if health.structure_health < 35:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.WARNING,
                title="Structure Breakdown",
                message=f"Market structure weakening. Structure health: {health.structure_health:.0f}%",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Check recovery blocked
        if health.recovery_blocked:
            alert = self._create_alert(
                position_id=position_id,
                severity=AlertSeverity.INFO,
                title="Recovery Blocked",
                message=f"Recovery trades blocked: {health.recovery_block_reason}",
                current_health=health.current_health,
                health_trend=health.health_trend,
                now=now
            )
            alerts.append(alert)
        
        # Store alerts
        if position_id not in self._position_alerts:
            self._position_alerts[position_id] = []
        self._position_alerts[position_id].extend(alerts)
        
        # Clean expired
        self._clean_expired_alerts(position_id, now)
        
        return alerts
    
    def _create_alert(
        self,
        position_id: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        current_health: float,
        health_trend: str,
        now: int,
        trigger_event_id: Optional[str] = None
    ) -> HealthAlert:
        """Create a new alert"""
        
        action, urgency = self._action_map.get(severity, ("MONITOR", "LOW"))
        ttl = self._alert_ttl.get(severity, 3600000)
        
        return HealthAlert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            position_id=position_id,
            severity=severity,
            title=title,
            message=message,
            current_health=current_health,
            health_trend=health_trend,
            trigger_event_id=trigger_event_id,
            recommended_action=action,
            action_urgency=urgency,
            acknowledged=False,
            resolved=False,
            created_at=now,
            expires_at=now + ttl
        )
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for position_id, alerts in self._position_alerts.items():
            for alert in alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = int(time.time() * 1000)
                    return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for position_id, alerts in self._position_alerts.items():
            for alert in alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = int(time.time() * 1000)
                    return True
        return False
    
    def get_alerts(self, position_id: str) -> List[HealthAlert]:
        """Get all alerts for a position"""
        return self._position_alerts.get(position_id, [])
    
    def get_active_alerts(self, position_id: str) -> List[HealthAlert]:
        """Get unresolved alerts"""
        alerts = self._position_alerts.get(position_id, [])
        return [a for a in alerts if not a.resolved]
    
    def get_critical_alerts(self, position_id: str) -> List[HealthAlert]:
        """Get critical and emergency alerts"""
        alerts = self._position_alerts.get(position_id, [])
        return [
            a for a in alerts 
            if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY] 
            and not a.resolved
        ]
    
    def get_all_active_alerts(self) -> List[HealthAlert]:
        """Get all active alerts across positions"""
        all_alerts = []
        for alerts in self._position_alerts.values():
            all_alerts.extend([a for a in alerts if not a.resolved])
        return sorted(all_alerts, key=lambda x: x.created_at, reverse=True)
    
    def _clean_expired_alerts(self, position_id: str, now: int):
        """Remove expired alerts"""
        if position_id in self._position_alerts:
            self._position_alerts[position_id] = [
                a for a in self._position_alerts[position_id]
                if a.expires_at > now or not a.resolved
            ]
    
    def clear_alerts(self, position_id: str):
        """Clear all alerts for a position"""
        if position_id in self._position_alerts:
            del self._position_alerts[position_id]
    
    def get_alert_summary(self) -> Dict[str, int]:
        """Get summary of all alerts by severity"""
        summary = {s.value: 0 for s in AlertSeverity}
        
        for alerts in self._position_alerts.values():
            for alert in alerts:
                if not alert.resolved:
                    summary[alert.severity.value] += 1
        
        return summary
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        total_alerts = sum(len(a) for a in self._position_alerts.values())
        active_alerts = len(self.get_all_active_alerts())
        
        return {
            "engine": "HealthAlertEngine",
            "version": "1.0.0",
            "phase": "3.2",
            "status": "active",
            "severityLevels": [s.value for s in AlertSeverity],
            "trackedPositions": len(self._position_alerts),
            "totalAlerts": total_alerts,
            "activeAlerts": active_alerts,
            "summary": self.get_alert_summary(),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
health_alert_engine = HealthAlertEngine()
