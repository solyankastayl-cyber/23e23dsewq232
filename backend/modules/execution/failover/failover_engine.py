"""
Failover Engine
===============

Главный движок принятия решений по failover.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from .failover_types import (
    SystemStatus,
    ExchangeStatus,
    FailoverAction,
    FailoverEvent,
    FailoverEventType,
    FailoverState,
    FailoverConfig,
    ExchangeHealthMetrics
)
from .exchange_health_monitor import ExchangeHealthMonitor
from .latency_monitor import LatencyMonitor
from .rate_limit_monitor import RateLimitMonitor
from .connection_guard import ConnectionGuard


class FailoverEngine:
    """
    Главный движок Failover.
    
    Принимает решения о режиме работы:
    - NORMAL: всё работает
    - DEGRADED: reduce trading frequency, limit new positions
    - FAILOVER: pause trading, close risky positions, switch exchange
    - EMERGENCY: freeze execution, cancel orders, secure positions
    """
    
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        
        # Initialize monitors
        self.health_monitor = ExchangeHealthMonitor()
        self.latency_monitor = LatencyMonitor(
            normal_threshold_ms=self.config.latency_normal_ms,
            degraded_threshold_ms=self.config.latency_degraded_ms,
            critical_threshold_ms=self.config.latency_critical_ms
        )
        self.rate_limit_monitor = RateLimitMonitor(
            warning_threshold_pct=self.config.rate_limit_warning_pct,
            critical_threshold_pct=self.config.rate_limit_critical_pct
        )
        self.connection_guard = ConnectionGuard(
            heartbeat_timeout_seconds=self.config.websocket_heartbeat_timeout_ms / 1000
        )
        
        # State
        self._state = FailoverState()
        self._events: List[FailoverEvent] = []
        self._last_evaluation: Optional[datetime] = None
    
    def evaluate(self, exchange: Optional[str] = None) -> FailoverState:
        """
        Оценить текущее состояние и принять решение.
        
        Returns:
            FailoverState с текущим статусом и действиями
        """
        now = datetime.utcnow()
        self._last_evaluation = now
        
        exchanges_to_check = [exchange] if exchange else ["BINANCE", "BYBIT", "OKX"]
        
        # Collect health data
        exchange_health: Dict[str, ExchangeHealthMetrics] = {}
        issues = []
        
        for ex in exchanges_to_check:
            # Simulate some requests if no data
            if ex not in self.health_monitor._latency_history:
                self.health_monitor.simulate_requests(ex)
            
            health = self.health_monitor.get_health(ex)
            exchange_health[ex] = health
            
            # Check for issues
            if health.status == ExchangeStatus.OFFLINE:
                issues.append(("CRITICAL", ex, "Exchange offline"))
            elif health.status == ExchangeStatus.DEGRADED:
                issues.append(("WARNING", ex, "Exchange degraded"))
            
            if health.error_rate > self.config.error_rate_critical:
                issues.append(("CRITICAL", ex, f"High error rate: {health.error_rate:.1%}"))
            elif health.error_rate > self.config.error_rate_warning:
                issues.append(("WARNING", ex, f"Elevated error rate: {health.error_rate:.1%}"))
            
            # Check rate limits
            rl_action = self.rate_limit_monitor.get_recommended_action(ex)
            if rl_action["severity"] == "CRITICAL":
                issues.append(("CRITICAL", ex, "Rate limit exceeded"))
            elif rl_action["severity"] == "WARNING":
                issues.append(("WARNING", ex, "Approaching rate limit"))
            
            # Check connections
            conn_health = self.connection_guard.check_health(ex)
            if not conn_health["overall_healthy"]:
                issues.append(("WARNING", ex, "Connection issues"))
        
        # Determine system status
        critical_count = sum(1 for i in issues if i[0] == "CRITICAL")
        warning_count = sum(1 for i in issues if i[0] == "WARNING")
        
        if critical_count >= 2:
            new_status = SystemStatus.EMERGENCY
        elif critical_count >= 1:
            new_status = SystemStatus.FAILOVER
        elif warning_count >= 2:
            new_status = SystemStatus.DEGRADED
        elif warning_count >= 1:
            new_status = SystemStatus.DEGRADED
        else:
            new_status = SystemStatus.NORMAL
        
        # Determine actions
        actions = self._determine_actions(new_status, issues, exchange_health)
        
        # Update state
        old_status = self._state.system_status
        
        self._state.system_status = new_status
        self._state.exchanges = exchange_health
        self._state.active_actions = actions
        self._state.updated_at = now
        
        # Calculate factors
        self._state.throttle_factor = self._calculate_throttle_factor(new_status, issues)
        self._state.position_size_factor = self._calculate_position_factor(new_status)
        self._state.new_positions_allowed = new_status in [SystemStatus.NORMAL, SystemStatus.DEGRADED]
        self._state.execution_paused = new_status == SystemStatus.EMERGENCY
        
        # Track status change
        if old_status != new_status:
            self._state.last_status_change = now
            self._record_event(
                FailoverEventType.STATUS_CHANGE,
                f"Status changed from {old_status.value} to {new_status.value}",
                severity="WARNING" if new_status in [SystemStatus.FAILOVER, SystemStatus.EMERGENCY] else "INFO",
                details={"old_status": old_status.value, "new_status": new_status.value}
            )
            
            if new_status in [SystemStatus.FAILOVER, SystemStatus.EMERGENCY]:
                self._state.failover_started_at = now
        
        # Count issues
        self._state.recent_errors = sum(
            h.error_count_1m for h in exchange_health.values()
        )
        
        # Track failover exchanges
        self._state.active_failover_exchanges = [
            ex for ex, h in exchange_health.items()
            if h.status in [ExchangeStatus.OFFLINE, ExchangeStatus.DEGRADED]
        ]
        
        return self._state
    
    def get_state(self) -> FailoverState:
        """Получить текущее состояние"""
        return self._state
    
    def get_system_status(self) -> Dict[str, Any]:
        """Получить системный статус в виде словаря для routing engine"""
        return {
            "system_status": self._state.system_status.value,
            "execution_paused": self._state.execution_paused,
            "new_positions_allowed": self._state.new_positions_allowed,
            "throttle_factor": self._state.throttle_factor,
            "position_size_factor": self._state.position_size_factor,
            "active_actions": [a.value for a in self._state.active_actions],
            "active_failover_exchanges": self._state.active_failover_exchanges,
            "recent_errors": self._state.recent_errors,
            "timestamp": self._state.updated_at.isoformat() if self._state.updated_at else None
        }
    
    def get_exchange_status(self, exchange: str) -> Dict[str, Any]:
        """Получить статус конкретной биржи"""
        health = self.health_monitor.get_health(exchange)
        latency = self.latency_monitor.get_stats(exchange)
        rate_limit = self.rate_limit_monitor.get_recommended_action(exchange)
        connection = self.connection_guard.check_health(exchange)
        
        return {
            "exchange": exchange,
            "health": {
                "status": health.status.value,
                "health_score": health.health_score,
                "latency_ms": health.avg_latency_ms,
                "error_rate": health.error_rate
            },
            "latency": latency,
            "rate_limit": rate_limit,
            "connection": connection,
            "recommended_action": self._get_exchange_action(health, rate_limit, connection)
        }
    
    def record_request(
        self,
        exchange: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Записать результат запроса во все мониторы"""
        # Health monitor
        self.health_monitor.record_request(exchange, latency_ms, success, error)
        
        # Latency monitor
        latency_result = self.latency_monitor.record(exchange, latency_ms)
        
        # Rate limit
        self.rate_limit_monitor.record_request(exchange)
        
        # Heartbeat for connection
        if success:
            self.connection_guard.record_heartbeat(exchange, "rest", latency_ms)
        
        # Check if spike
        if latency_result.get("is_spike"):
            self._record_event(
                FailoverEventType.LATENCY_SPIKE,
                f"Latency spike detected: {latency_ms:.0f}ms",
                exchange=exchange,
                severity="WARNING"
            )
        
        return latency_result
    
    def trigger_emergency(self, reason: str) -> FailoverState:
        """Принудительно активировать EMERGENCY режим"""
        self._state.system_status = SystemStatus.EMERGENCY
        self._state.execution_paused = True
        self._state.new_positions_allowed = False
        self._state.active_actions = [
            FailoverAction.FREEZE_EXECUTION,
            FailoverAction.CANCEL_PENDING_ORDERS,
            FailoverAction.SECURE_POSITIONS
        ]
        self._state.last_status_change = datetime.utcnow()
        self._state.failover_started_at = datetime.utcnow()
        
        self._record_event(
            FailoverEventType.STATUS_CHANGE,
            f"Emergency triggered: {reason}",
            severity="CRITICAL",
            details={"reason": reason}
        )
        
        return self._state
    
    def reset(self) -> FailoverState:
        """Сбросить в NORMAL режим"""
        self._state.system_status = SystemStatus.NORMAL
        self._state.execution_paused = False
        self._state.new_positions_allowed = True
        self._state.active_actions = []
        self._state.throttle_factor = 1.0
        self._state.position_size_factor = 1.0
        self._state.failover_started_at = None
        self._state.last_status_change = datetime.utcnow()
        
        self._record_event(
            FailoverEventType.STATUS_CHANGE,
            "System reset to NORMAL",
            severity="INFO"
        )
        
        return self._state
    
    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить недавние события"""
        events = self._events[-limit:]
        return [
            {
                "id": e.id,
                "event_type": e.event_type.value,
                "exchange": e.exchange,
                "message": e.message,
                "severity": e.severity,
                "action_triggered": e.action_triggered.value if e.action_triggered else None,
                "details": e.details,
                "timestamp": e.timestamp.isoformat()
            }
            for e in events
        ]
    
    def _determine_actions(
        self,
        status: SystemStatus,
        issues: List[tuple],
        health: Dict[str, ExchangeHealthMetrics]
    ) -> List[FailoverAction]:
        """Определить необходимые действия"""
        actions = []
        
        if status == SystemStatus.EMERGENCY:
            actions = [
                FailoverAction.FREEZE_EXECUTION,
                FailoverAction.CANCEL_PENDING_ORDERS,
                FailoverAction.SECURE_POSITIONS
            ]
        elif status == SystemStatus.FAILOVER:
            actions = [
                FailoverAction.PAUSE_NEW_POSITIONS,
                FailoverAction.CLOSE_RISKY_POSITIONS,
                FailoverAction.SWITCH_EXCHANGE
            ]
        elif status == SystemStatus.DEGRADED:
            actions = [
                FailoverAction.THROTTLE_REQUESTS,
                FailoverAction.LIMIT_NEW_ORDERS,
                FailoverAction.REDUCE_POSITION_SIZE
            ]
        
        return actions
    
    def _calculate_throttle_factor(
        self,
        status: SystemStatus,
        issues: List[tuple]
    ) -> float:
        """Рассчитать фактор throttling"""
        if status == SystemStatus.EMERGENCY:
            return 0.0
        elif status == SystemStatus.FAILOVER:
            return 0.2
        elif status == SystemStatus.DEGRADED:
            return 0.5
        return 1.0
    
    def _calculate_position_factor(self, status: SystemStatus) -> float:
        """Рассчитать фактор размера позиции"""
        if status == SystemStatus.EMERGENCY:
            return 0.0
        elif status == SystemStatus.FAILOVER:
            return 0.3
        elif status == SystemStatus.DEGRADED:
            return 0.7
        return 1.0
    
    def _get_exchange_action(
        self,
        health: ExchangeHealthMetrics,
        rate_limit: Dict[str, Any],
        connection: Dict[str, Any]
    ) -> str:
        """Получить рекомендуемое действие для биржи"""
        if health.status == ExchangeStatus.OFFLINE:
            return FailoverAction.SWITCH_EXCHANGE.value
        elif not connection.get("overall_healthy"):
            return FailoverAction.THROTTLE_REQUESTS.value
        elif rate_limit.get("severity") == "CRITICAL":
            return FailoverAction.PAUSE_NEW_POSITIONS.value
        elif health.status == ExchangeStatus.DEGRADED:
            return FailoverAction.LIMIT_NEW_ORDERS.value
        return FailoverAction.NONE.value
    
    def _record_event(
        self,
        event_type: FailoverEventType,
        message: str,
        exchange: Optional[str] = None,
        severity: str = "INFO",
        action: Optional[FailoverAction] = None,
        details: Optional[Dict] = None
    ) -> None:
        """Записать событие"""
        event = FailoverEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            exchange=exchange,
            message=message,
            severity=severity,
            action_triggered=action,
            details=details or {},
            timestamp=datetime.utcnow()
        )
        self._events.append(event)
        
        # Keep only recent events
        if len(self._events) > 1000:
            self._events = self._events[-500:]



# Global instance
_failover_engine = None


def get_failover_engine():
    """Get or create global failover engine instance"""
    global _failover_engine
    if _failover_engine is None:
        _failover_engine = FailoverEngine()
    return _failover_engine
