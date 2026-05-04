"""
Health Repository
=================

PHASE 3.2 - Data persistence for trade health data.
"""

import time
from typing import Dict, List, Optional, Any

from .health_types import (
    AdvancedTradeHealthScore,
    HealthEvent,
    HealthDecayRecord,
    HealthAlert,
    TradeStabilityScore,
    HealthHistoryEntry,
    HealthStatus
)


class HealthRepository:
    """
    Repository for trade health data.
    
    Stores:
    - Health scores
    - Events
    - Decay records
    - Alerts
    - Stability scores
    - Health history
    """
    
    def __init__(self):
        self._health_scores: Dict[str, AdvancedTradeHealthScore] = {}
        self._events: Dict[str, List[HealthEvent]] = {}
        self._decay_records: Dict[str, List[HealthDecayRecord]] = {}
        self._alerts: Dict[str, List[HealthAlert]] = {}
        self._stability: Dict[str, TradeStabilityScore] = {}
        self._history: Dict[str, List[HealthHistoryEntry]] = {}
        
        print("[HealthRepository] Initialized (PHASE 3.2)")
    
    # Health Scores
    def save_health(self, health: AdvancedTradeHealthScore):
        """Save health score"""
        self._health_scores[health.position_id] = health
        
        # Add to history
        self._add_history_entry(health)
    
    def get_health(self, position_id: str) -> Optional[AdvancedTradeHealthScore]:
        """Get health score for position"""
        return self._health_scores.get(position_id)
    
    def get_all_health(self) -> List[AdvancedTradeHealthScore]:
        """Get all health scores"""
        return list(self._health_scores.values())
    
    def get_health_by_status(self, status: HealthStatus) -> List[AdvancedTradeHealthScore]:
        """Get health scores by status"""
        return [h for h in self._health_scores.values() if h.status == status]
    
    # Events
    def save_events(self, position_id: str, events: List[HealthEvent]):
        """Save events for position"""
        if position_id not in self._events:
            self._events[position_id] = []
        self._events[position_id].extend(events)
    
    def get_events(self, position_id: str) -> List[HealthEvent]:
        """Get all events for position"""
        return self._events.get(position_id, [])
    
    def get_recent_events(self, position_id: str, hours: int = 4) -> List[HealthEvent]:
        """Get recent events"""
        cutoff = int(time.time() * 1000) - hours * 3600 * 1000
        events = self._events.get(position_id, [])
        return [e for e in events if e.detected_at > cutoff]
    
    # Decay Records
    def save_decay(self, position_id: str, records: List[HealthDecayRecord]):
        """Save decay records"""
        if position_id not in self._decay_records:
            self._decay_records[position_id] = []
        self._decay_records[position_id].extend(records)
    
    def get_decay(self, position_id: str) -> List[HealthDecayRecord]:
        """Get decay records"""
        return self._decay_records.get(position_id, [])
    
    def get_total_decay(self, position_id: str) -> float:
        """Get total cumulative decay"""
        records = self._decay_records.get(position_id, [])
        return sum(r.decay_amount for r in records)
    
    # Alerts
    def save_alerts(self, position_id: str, alerts: List[HealthAlert]):
        """Save alerts"""
        if position_id not in self._alerts:
            self._alerts[position_id] = []
        self._alerts[position_id].extend(alerts)
    
    def get_alerts(self, position_id: str) -> List[HealthAlert]:
        """Get all alerts"""
        return self._alerts.get(position_id, [])
    
    def get_active_alerts(self, position_id: str) -> List[HealthAlert]:
        """Get unresolved alerts"""
        alerts = self._alerts.get(position_id, [])
        return [a for a in alerts if not a.resolved]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alerts in self._alerts.values():
            for alert in alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = int(time.time() * 1000)
                    return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alerts in self._alerts.values():
            for alert in alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = int(time.time() * 1000)
                    return True
        return False
    
    # Stability
    def save_stability(self, stability: TradeStabilityScore):
        """Save stability score"""
        self._stability[stability.position_id] = stability
    
    def get_stability(self, position_id: str) -> Optional[TradeStabilityScore]:
        """Get stability score"""
        return self._stability.get(position_id)
    
    # History
    def _add_history_entry(self, health: AdvancedTradeHealthScore):
        """Add entry to health history"""
        if health.position_id not in self._history:
            self._history[health.position_id] = []
        
        entry = HealthHistoryEntry(
            position_id=health.position_id,
            timestamp=health.computed_at,
            health=health.current_health,
            status=health.status,
            price=0,  # Would come from position data
            pnl_pct=0,
            event_count=len(health.recent_events)
        )
        
        self._history[health.position_id].append(entry)
        
        # Keep last 100 entries
        if len(self._history[health.position_id]) > 100:
            self._history[health.position_id] = self._history[health.position_id][-100:]
    
    def get_history(self, position_id: str, limit: int = 50) -> List[HealthHistoryEntry]:
        """Get health history"""
        history = self._history.get(position_id, [])
        return history[-limit:]
    
    # Cleanup
    def clear_position(self, position_id: str):
        """Clear all data for a position"""
        self._health_scores.pop(position_id, None)
        self._events.pop(position_id, None)
        self._decay_records.pop(position_id, None)
        self._alerts.pop(position_id, None)
        self._stability.pop(position_id, None)
        self._history.pop(position_id, None)
    
    def clear_all(self):
        """Clear all data"""
        self._health_scores.clear()
        self._events.clear()
        self._decay_records.clear()
        self._alerts.clear()
        self._stability.clear()
        self._history.clear()
    
    # Stats
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        return {
            "positions": len(self._health_scores),
            "healthScores": len(self._health_scores),
            "events": sum(len(e) for e in self._events.values()),
            "decayRecords": sum(len(d) for d in self._decay_records.values()),
            "alerts": sum(len(a) for a in self._alerts.values()),
            "activeAlerts": sum(
                len([a for a in alerts if not a.resolved])
                for alerts in self._alerts.values()
            ),
            "stabilityScores": len(self._stability),
            "historyEntries": sum(len(h) for h in self._history.values()),
            "statusBreakdown": {
                status.value: len(self.get_health_by_status(status))
                for status in HealthStatus
            },
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
health_repository = HealthRepository()
