"""
SEC3 Connection Safety Types
============================

Data structures for exchange connection monitoring and safety.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class ConnectionStatus(str, Enum):
    """Exchange connection status"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNSTABLE = "UNSTABLE"
    QUARANTINED = "QUARANTINED"
    UNKNOWN = "UNKNOWN"


class IncidentType(str, Enum):
    """Types of connection incidents"""
    OUTAGE = "OUTAGE"
    LATENCY_SPIKE = "LATENCY_SPIKE"
    WS_DESYNC = "WS_DESYNC"
    RATE_LIMIT = "RATE_LIMIT"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    AUTH_ERROR = "AUTH_ERROR"
    FLAPPING = "FLAPPING"
    TIMEOUT = "TIMEOUT"


class IncidentSeverity(str, Enum):
    """Incident severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    """Types of safety actions"""
    ALERT = "ALERT"
    DEGRADE_MODE = "DEGRADE_MODE"
    FREEZE_ORDERS = "FREEZE_ORDERS"
    QUARANTINE = "QUARANTINE"
    RESTORE = "RESTORE"
    FAILOVER = "FAILOVER"


@dataclass
class APIEndpointHealth:
    """Health status of a specific API endpoint"""
    endpoint: str = ""
    status: str = "OK"  # OK, DEGRADED, FAILED
    latency_ms: float = 0.0
    last_success: Optional[int] = None
    last_error: Optional[str] = None
    error_count: int = 0
    success_rate: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "status": self.status,
            "latencyMs": round(self.latency_ms, 2),
            "lastSuccess": self.last_success,
            "lastError": self.last_error,
            "errorCount": self.error_count,
            "successRate": round(self.success_rate, 4)
        }


@dataclass
class WebSocketHealth:
    """WebSocket connection health"""
    connected: bool = False
    heartbeat_ok: bool = True
    last_message_at: Optional[int] = None
    message_lag_ms: int = 0
    sequence_gaps: int = 0
    reconnect_count: int = 0
    data_freshness: str = "FRESH"  # FRESH, STALE, DEAD
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "heartbeatOk": self.heartbeat_ok,
            "lastMessageAt": self.last_message_at,
            "messageLagMs": self.message_lag_ms,
            "sequenceGaps": self.sequence_gaps,
            "reconnectCount": self.reconnect_count,
            "dataFreshness": self.data_freshness
        }


@dataclass
class RateLimitStatus:
    """Rate limit monitoring"""
    requests_in_window: int = 0
    window_size_sec: int = 60
    limit: int = 1200
    remaining: int = 1200
    pressure: float = 0.0  # 0-1, higher = closer to limit
    throttled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requestsInWindow": self.requests_in_window,
            "windowSizeSec": self.window_size_sec,
            "limit": self.limit,
            "remaining": self.remaining,
            "pressure": round(self.pressure, 4),
            "throttled": self.throttled
        }


@dataclass
class ExchangeConnectionHealth:
    """
    Complete connection health for an exchange.
    Main entity for SEC3.
    """
    exchange: str = ""
    connection_id: str = field(default_factory=lambda: f"conn_{uuid.uuid4().hex[:8]}")
    
    # Overall status
    status: ConnectionStatus = ConnectionStatus.HEALTHY
    
    # API health
    api_status: str = "HEALTHY"  # HEALTHY, DEGRADED, FAILED
    api_endpoints: List[APIEndpointHealth] = field(default_factory=list)
    
    # WebSocket health
    ws_status: str = "HEALTHY"  # HEALTHY, DEGRADED, DISCONNECTED
    ws_health: Optional[WebSocketHealth] = None
    
    # Latency metrics
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    timeout_count: int = 0
    
    # Error metrics
    error_rate: float = 0.0
    error_count_1h: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[int] = None
    
    # Rate limiting
    rate_limit: Optional[RateLimitStatus] = None
    rate_limit_pressure: float = 0.0
    
    # State flags
    degraded: bool = False
    quarantined: bool = False
    frozen: bool = False
    
    # Computed score
    health_score: float = 1.0  # 0-1, higher = healthier
    
    # Timestamps
    checked_at: int = field(default_factory=lambda: int(time.time() * 1000))
    quarantined_at: Optional[int] = None
    degraded_at: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "connectionId": self.connection_id,
            "status": self.status.value,
            "api": {
                "status": self.api_status,
                "endpoints": [e.to_dict() for e in self.api_endpoints]
            },
            "websocket": {
                "status": self.ws_status,
                "health": self.ws_health.to_dict() if self.ws_health else None
            },
            "latency": {
                "avgMs": round(self.avg_latency_ms, 2),
                "p95Ms": round(self.p95_latency_ms, 2),
                "maxMs": round(self.max_latency_ms, 2),
                "timeoutCount": self.timeout_count
            },
            "errors": {
                "rate": round(self.error_rate, 4),
                "count1h": self.error_count_1h,
                "lastError": self.last_error,
                "lastErrorAt": self.last_error_at
            },
            "rateLimit": self.rate_limit.to_dict() if self.rate_limit else None,
            "rateLimitPressure": round(self.rate_limit_pressure, 4),
            "flags": {
                "degraded": self.degraded,
                "quarantined": self.quarantined,
                "frozen": self.frozen
            },
            "healthScore": round(self.health_score, 4),
            "checkedAt": self.checked_at,
            "quarantinedAt": self.quarantined_at,
            "degradedAt": self.degraded_at
        }


@dataclass
class ConnectionIncident:
    """
    Record of a connection incident.
    """
    incident_id: str = field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:12]}")
    
    exchange: str = ""
    incident_type: IncidentType = IncidentType.LATENCY_SPIKE
    severity: IncidentSeverity = IncidentSeverity.WARNING
    
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[int] = None
    resolution_note: str = ""
    
    # Actions taken
    actions_taken: List[str] = field(default_factory=list)
    
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "incidentId": self.incident_id,
            "exchange": self.exchange,
            "type": self.incident_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "resolved": self.resolved,
            "resolvedAt": self.resolved_at,
            "resolutionNote": self.resolution_note,
            "actionsTaken": self.actions_taken,
            "createdAt": self.created_at
        }


@dataclass
class ConnectionAction:
    """
    Record of a safety action taken.
    """
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:12]}")
    
    exchange: str = ""
    action_type: ActionType = ActionType.ALERT
    
    reason: str = ""
    triggered_by: str = ""  # AUTOMATIC, MANUAL
    incident_id: Optional[str] = None
    
    # Execution
    executed: bool = True
    execution_error: Optional[str] = None
    
    # Reversal
    reverted: bool = False
    reverted_at: Optional[int] = None
    
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "actionId": self.action_id,
            "exchange": self.exchange,
            "type": self.action_type.value,
            "reason": self.reason,
            "triggeredBy": self.triggered_by,
            "incidentId": self.incident_id,
            "executed": self.executed,
            "executionError": self.execution_error,
            "reverted": self.reverted,
            "revertedAt": self.reverted_at,
            "createdAt": self.created_at
        }


@dataclass
class ConnectionSafetySummary:
    """
    Summary of all exchange connections.
    """
    total_exchanges: int = 0
    healthy_count: int = 0
    degraded_count: int = 0
    quarantined_count: int = 0
    
    active_incidents: int = 0
    recent_actions: int = 0
    
    overall_health: str = "HEALTHY"  # HEALTHY, WARNING, DEGRADED, CRITICAL
    
    exchanges: List[Dict[str, Any]] = field(default_factory=list)
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalExchanges": self.total_exchanges,
            "healthyCount": self.healthy_count,
            "degradedCount": self.degraded_count,
            "quarantinedCount": self.quarantined_count,
            "activeIncidents": self.active_incidents,
            "recentActions": self.recent_actions,
            "overallHealth": self.overall_health,
            "exchanges": self.exchanges,
            "computedAt": self.computed_at
        }
