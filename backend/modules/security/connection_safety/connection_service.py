"""
SEC3 Connection Safety Service
==============================

Main service for exchange connection safety monitoring.

Protects the system from:
- Exchange outages
- Latency spikes
- WebSocket desyncs
- Rate limit pressure
- Partial API failures
"""

import os
import time
import threading
import random
from typing import Dict, List, Optional, Any

from .connection_types import (
    ExchangeConnectionHealth,
    ConnectionIncident,
    ConnectionAction,
    ConnectionSafetySummary,
    ConnectionStatus,
    IncidentType,
    IncidentSeverity,
    ActionType,
    APIEndpointHealth,
    WebSocketHealth,
    RateLimitStatus
)

# MongoDB connection
try:
    from pymongo import MongoClient, DESCENDING
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception as e:
    print(f"[ConnectionSafetyService] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class ConnectionSafetyService:
    """
    Main service for SEC3 Connection Safety.
    
    Monitors and protects exchange connections.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Thresholds
    LATENCY_WARNING_MS = 500
    LATENCY_HIGH_MS = 1000
    LATENCY_CRITICAL_MS = 2000
    ERROR_RATE_WARNING = 0.05
    ERROR_RATE_HIGH = 0.15
    RATE_LIMIT_WARNING = 0.7
    RATE_LIMIT_HIGH = 0.9
    WS_STALE_SEC = 30
    WS_DEAD_SEC = 60
    
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
        
        # Exchange health cache
        self._health_cache: Dict[str, ExchangeConnectionHealth] = {}
        self._incidents: List[ConnectionIncident] = []
        self._actions: List[ConnectionAction] = []
        
        # Supported exchanges
        self._exchanges = ["binance", "bybit", "hyperliquid"]
        
        # Initialize health for all exchanges
        self._initialize_exchanges()
        
        self._initialized = True
        print("[ConnectionSafetyService] Initialized (SEC3)")
    
    def _initialize_exchanges(self):
        """Initialize health tracking for exchanges"""
        for exchange in self._exchanges:
            self._health_cache[exchange] = self._generate_mock_health(exchange)
    
    # ===========================================
    # Health Monitoring
    # ===========================================
    
    def get_all_health(self) -> List[ExchangeConnectionHealth]:
        """
        Get health status for all exchanges.
        """
        return list(self._health_cache.values())
    
    def get_exchange_health(self, exchange: str) -> Optional[ExchangeConnectionHealth]:
        """
        Get health status for specific exchange.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower in self._health_cache:
            # Refresh mock data
            self._health_cache[exchange_lower] = self._generate_mock_health(exchange_lower)
            return self._health_cache[exchange_lower]
        
        return None
    
    def check_health(self, exchange: str) -> ExchangeConnectionHealth:
        """
        Perform health check for an exchange.
        """
        exchange_lower = exchange.lower()
        health = self._generate_mock_health(exchange_lower)
        
        # Analyze and create incidents if needed
        self._analyze_health(health)
        
        self._health_cache[exchange_lower] = health
        return health
    
    def _analyze_health(self, health: ExchangeConnectionHealth):
        """Analyze health and create incidents if needed"""
        
        # Check latency
        if health.avg_latency_ms > self.LATENCY_CRITICAL_MS:
            self._create_incident(
                exchange=health.exchange,
                incident_type=IncidentType.LATENCY_SPIKE,
                severity=IncidentSeverity.CRITICAL,
                message=f"Critical latency spike: {health.avg_latency_ms}ms"
            )
        elif health.avg_latency_ms > self.LATENCY_HIGH_MS:
            self._create_incident(
                exchange=health.exchange,
                incident_type=IncidentType.LATENCY_SPIKE,
                severity=IncidentSeverity.HIGH,
                message=f"High latency: {health.avg_latency_ms}ms"
            )
        
        # Check error rate
        if health.error_rate > self.ERROR_RATE_HIGH:
            self._create_incident(
                exchange=health.exchange,
                incident_type=IncidentType.PARTIAL_FAILURE,
                severity=IncidentSeverity.HIGH,
                message=f"High error rate: {health.error_rate:.2%}"
            )
        
        # Check rate limit
        if health.rate_limit_pressure > self.RATE_LIMIT_HIGH:
            self._create_incident(
                exchange=health.exchange,
                incident_type=IncidentType.RATE_LIMIT,
                severity=IncidentSeverity.WARNING,
                message=f"Rate limit pressure: {health.rate_limit_pressure:.2%}"
            )
    
    def get_summary(self) -> ConnectionSafetySummary:
        """
        Get summary of all connections.
        """
        healths = self.get_all_health()
        
        healthy = sum(1 for h in healths if h.status == ConnectionStatus.HEALTHY)
        degraded = sum(1 for h in healths if h.status == ConnectionStatus.DEGRADED)
        quarantined = sum(1 for h in healths if h.status == ConnectionStatus.QUARANTINED)
        
        active_incidents = sum(1 for i in self._incidents if not i.resolved)
        recent_actions = sum(1 for a in self._actions if time.time() * 1000 - a.created_at < 3600000)
        
        # Determine overall health
        if quarantined > 0:
            overall = "CRITICAL"
        elif degraded > 0:
            overall = "DEGRADED"
        elif active_incidents > 0:
            overall = "WARNING"
        else:
            overall = "HEALTHY"
        
        return ConnectionSafetySummary(
            total_exchanges=len(healths),
            healthy_count=healthy,
            degraded_count=degraded,
            quarantined_count=quarantined,
            active_incidents=active_incidents,
            recent_actions=recent_actions,
            overall_health=overall,
            exchanges=[{
                "exchange": h.exchange,
                "status": h.status.value,
                "healthScore": round(h.health_score, 4)
            } for h in healths]
        )
    
    # ===========================================
    # Incidents
    # ===========================================
    
    def get_incidents(
        self,
        exchange: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 50
    ) -> List[ConnectionIncident]:
        """
        Get connection incidents.
        """
        incidents = self._incidents
        
        if exchange:
            incidents = [i for i in incidents if i.exchange.lower() == exchange.lower()]
        
        if resolved is not None:
            incidents = [i for i in incidents if i.resolved == resolved]
        
        # Sort by created_at desc
        incidents = sorted(incidents, key=lambda x: x.created_at, reverse=True)
        
        return incidents[:limit]
    
    def _create_incident(
        self,
        exchange: str,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        message: str,
        details: Optional[Dict] = None
    ) -> ConnectionIncident:
        """Create a new incident"""
        
        # Check for duplicate recent incident
        recent_cutoff = time.time() * 1000 - 60000  # 1 minute
        for inc in self._incidents:
            if (
                inc.exchange.lower() == exchange.lower() and
                inc.incident_type == incident_type and
                inc.created_at > recent_cutoff and
                not inc.resolved
            ):
                # Update existing instead of creating new
                return inc
        
        incident = ConnectionIncident(
            exchange=exchange,
            incident_type=incident_type,
            severity=severity,
            message=message,
            details=details or {}
        )
        
        self._incidents.append(incident)
        
        # Auto-actions based on severity
        if severity == IncidentSeverity.CRITICAL:
            self.quarantine_exchange(exchange, f"Auto-quarantine: {message}")
        elif severity == IncidentSeverity.HIGH:
            self.degrade_exchange(exchange, f"Auto-degrade: {message}")
        
        return incident
    
    def resolve_incident(self, incident_id: str, note: str = "") -> bool:
        """
        Resolve an incident.
        """
        for inc in self._incidents:
            if inc.incident_id == incident_id:
                inc.resolved = True
                inc.resolved_at = int(time.time() * 1000)
                inc.resolution_note = note
                return True
        return False
    
    # ===========================================
    # Actions
    # ===========================================
    
    def get_actions(
        self,
        exchange: Optional[str] = None,
        limit: int = 50
    ) -> List[ConnectionAction]:
        """
        Get safety actions.
        """
        actions = self._actions
        
        if exchange:
            actions = [a for a in actions if a.exchange.lower() == exchange.lower()]
        
        actions = sorted(actions, key=lambda x: x.created_at, reverse=True)
        
        return actions[:limit]
    
    def _create_action(
        self,
        exchange: str,
        action_type: ActionType,
        reason: str,
        triggered_by: str = "AUTOMATIC",
        incident_id: Optional[str] = None
    ) -> ConnectionAction:
        """Create a safety action"""
        
        action = ConnectionAction(
            exchange=exchange,
            action_type=action_type,
            reason=reason,
            triggered_by=triggered_by,
            incident_id=incident_id
        )
        
        self._actions.append(action)
        return action
    
    # ===========================================
    # Safety Actions
    # ===========================================
    
    def degrade_exchange(self, exchange: str, reason: str) -> ConnectionAction:
        """
        Put exchange in degraded mode.
        Allows: reads, reduce-only, no new entries
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower in self._health_cache:
            health = self._health_cache[exchange_lower]
            health.degraded = True
            health.degraded_at = int(time.time() * 1000)
            health.status = ConnectionStatus.DEGRADED
        
        action = self._create_action(
            exchange=exchange_lower,
            action_type=ActionType.DEGRADE_MODE,
            reason=reason,
            triggered_by="MANUAL"
        )
        
        return action
    
    def quarantine_exchange(self, exchange: str, reason: str) -> ConnectionAction:
        """
        Quarantine exchange - exclude from all trading.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower in self._health_cache:
            health = self._health_cache[exchange_lower]
            health.quarantined = True
            health.quarantined_at = int(time.time() * 1000)
            health.status = ConnectionStatus.QUARANTINED
        
        action = self._create_action(
            exchange=exchange_lower,
            action_type=ActionType.QUARANTINE,
            reason=reason,
            triggered_by="MANUAL"
        )
        
        return action
    
    def restore_exchange(self, exchange: str, reason: str) -> ConnectionAction:
        """
        Restore exchange from degraded/quarantine state.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower in self._health_cache:
            health = self._health_cache[exchange_lower]
            health.degraded = False
            health.quarantined = False
            health.frozen = False
            health.degraded_at = None
            health.quarantined_at = None
            health.status = ConnectionStatus.HEALTHY
        
        action = self._create_action(
            exchange=exchange_lower,
            action_type=ActionType.RESTORE,
            reason=reason,
            triggered_by="MANUAL"
        )
        
        return action
    
    def freeze_orders(self, exchange: str, reason: str) -> ConnectionAction:
        """
        Freeze all new orders on exchange.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower in self._health_cache:
            health = self._health_cache[exchange_lower]
            health.frozen = True
        
        action = self._create_action(
            exchange=exchange_lower,
            action_type=ActionType.FREEZE_ORDERS,
            reason=reason,
            triggered_by="MANUAL"
        )
        
        return action
    
    # ===========================================
    # Checks
    # ===========================================
    
    def is_exchange_tradeable(self, exchange: str) -> bool:
        """
        Check if exchange is available for trading.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower not in self._health_cache:
            return False
        
        health = self._health_cache[exchange_lower]
        return not health.quarantined and not health.frozen
    
    def is_exchange_degraded(self, exchange: str) -> bool:
        """
        Check if exchange is in degraded mode.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower not in self._health_cache:
            return False
        
        return self._health_cache[exchange_lower].degraded
    
    def can_open_positions(self, exchange: str) -> bool:
        """
        Check if new positions can be opened on exchange.
        """
        exchange_lower = exchange.lower()
        
        if exchange_lower not in self._health_cache:
            return False
        
        health = self._health_cache[exchange_lower]
        return not health.quarantined and not health.frozen and not health.degraded
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "SEC3 Connection Safety",
            "status": "healthy",
            "version": "1.0.0",
            "exchangesMonitored": len(self._exchanges),
            "activeIncidents": sum(1 for i in self._incidents if not i.resolved),
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Mock Data Generation
    # ===========================================
    
    def _generate_mock_health(self, exchange: str) -> ExchangeConnectionHealth:
        """Generate mock health data for demo"""
        
        # Randomize some degradation for demo variety
        is_degraded = random.random() < 0.15
        is_quarantined = random.random() < 0.05
        
        # Base latency varies by exchange
        base_latency = {
            "binance": 80,
            "bybit": 120,
            "hyperliquid": 60
        }.get(exchange.lower(), 100)
        
        avg_latency = base_latency + random.uniform(-20, 80)
        if is_degraded:
            avg_latency *= 3
        
        error_rate = random.uniform(0, 0.03)
        if is_degraded:
            error_rate = random.uniform(0.1, 0.25)
        
        rate_pressure = random.uniform(0.1, 0.5)
        if is_degraded:
            rate_pressure = random.uniform(0.7, 0.95)
        
        # Determine status
        if is_quarantined:
            status = ConnectionStatus.QUARANTINED
        elif is_degraded:
            status = ConnectionStatus.DEGRADED
        else:
            status = ConnectionStatus.HEALTHY
        
        # Calculate health score
        health_score = 1.0
        health_score -= min(avg_latency / 2000, 0.3)
        health_score -= error_rate * 2
        health_score -= rate_pressure * 0.3
        if is_degraded:
            health_score -= 0.3
        if is_quarantined:
            health_score = 0.0
        health_score = max(0, health_score)
        
        # API endpoints
        endpoints = [
            APIEndpointHealth(
                endpoint="/api/v3/account",
                status="OK" if not is_degraded else "DEGRADED",
                latency_ms=avg_latency + random.uniform(-10, 30),
                success_rate=1.0 - error_rate
            ),
            APIEndpointHealth(
                endpoint="/api/v3/order",
                status="OK" if random.random() > 0.1 else "DEGRADED",
                latency_ms=avg_latency + random.uniform(-10, 50),
                success_rate=1.0 - error_rate * 1.5
            ),
            APIEndpointHealth(
                endpoint="/api/v3/openOrders",
                status="OK",
                latency_ms=avg_latency + random.uniform(-10, 20),
                success_rate=1.0 - error_rate * 0.5
            )
        ]
        
        # WebSocket health
        ws_health = WebSocketHealth(
            connected=not is_quarantined,
            heartbeat_ok=not is_degraded,
            last_message_at=int(time.time() * 1000) - random.randint(100, 5000),
            message_lag_ms=random.randint(10, 500) if not is_degraded else random.randint(1000, 5000),
            sequence_gaps=0 if not is_degraded else random.randint(1, 5),
            data_freshness="FRESH" if not is_degraded else "STALE"
        )
        
        # Rate limit
        rate_limit = RateLimitStatus(
            requests_in_window=int(rate_pressure * 1200),
            limit=1200,
            remaining=int((1 - rate_pressure) * 1200),
            pressure=rate_pressure,
            throttled=rate_pressure > 0.95
        )
        
        return ExchangeConnectionHealth(
            exchange=exchange.upper(),
            status=status,
            api_status="DEGRADED" if is_degraded else "HEALTHY",
            api_endpoints=endpoints,
            ws_status="DISCONNECTED" if is_quarantined else ("DEGRADED" if is_degraded else "HEALTHY"),
            ws_health=ws_health,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(avg_latency * 1.5, 2),
            max_latency_ms=round(avg_latency * 2.5, 2),
            timeout_count=random.randint(0, 3) if is_degraded else 0,
            error_rate=round(error_rate, 4),
            error_count_1h=int(error_rate * 100),
            rate_limit=rate_limit,
            rate_limit_pressure=round(rate_pressure, 4),
            degraded=is_degraded,
            quarantined=is_quarantined,
            health_score=round(health_score, 4),
            degraded_at=int(time.time() * 1000) if is_degraded else None,
            quarantined_at=int(time.time() * 1000) if is_quarantined else None
        )


# Global singleton
connection_safety_service = ConnectionSafetyService()
