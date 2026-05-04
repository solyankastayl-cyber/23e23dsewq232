"""
Connection Guard
================

Мониторинг и защита WebSocket соединений.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random

from .failover_types import (
    ConnectionState,
    ConnectionStatus,
    FailoverAction,
    FailoverEvent,
    FailoverEventType
)


class ConnectionGuard:
    """
    Guard для WebSocket и REST соединений.
    
    Отслеживает:
    - WebSocket disconnect
    - Heartbeat timeout
    - Network errors
    
    Автоматически:
    - Reconnect
    - Switch to REST fallback
    - Pause execution
    """
    
    def __init__(
        self,
        heartbeat_timeout_seconds: float = 30.0,
        max_reconnect_attempts: int = 5,
        reconnect_delay_seconds: float = 1.0
    ):
        self.heartbeat_timeout = heartbeat_timeout_seconds
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay_seconds
        
        # Per-exchange, per-connection tracking
        self._connections: Dict[str, Dict[str, ConnectionStatus]] = {}
        self._events: List[FailoverEvent] = []
    
    def register_connection(
        self,
        exchange: str,
        connection_type: str = "websocket"
    ) -> ConnectionStatus:
        """Зарегистрировать новое соединение"""
        now = datetime.utcnow()
        exchange = exchange.upper()
        
        if exchange not in self._connections:
            self._connections[exchange] = {}
        
        status = ConnectionStatus(
            exchange=exchange,
            connection_type=connection_type,
            state=ConnectionState.CONNECTED,
            connected_since=now,
            last_heartbeat=now,
            reconnect_attempts=0
        )
        
        self._connections[exchange][connection_type] = status
        return status
    
    def record_heartbeat(
        self,
        exchange: str,
        connection_type: str = "websocket",
        latency_ms: float = 0.0
    ) -> ConnectionStatus:
        """Записать heartbeat"""
        exchange = exchange.upper()
        now = datetime.utcnow()
        
        # Initialize if needed
        if exchange not in self._connections:
            return self.register_connection(exchange, connection_type)
        if connection_type not in self._connections[exchange]:
            return self.register_connection(exchange, connection_type)
        
        status = self._connections[exchange][connection_type]
        status.last_heartbeat = now
        status.latency_ms = latency_ms
        
        # If was reconnecting, mark as connected
        if status.state == ConnectionState.RECONNECTING:
            status.state = ConnectionState.CONNECTED
            status.connected_since = now
            status.reconnect_attempts = 0
            
            self._record_event(
                FailoverEventType.CONNECTION_RESTORED,
                exchange,
                f"{connection_type} connection restored"
            )
        
        return status
    
    def record_disconnect(
        self,
        exchange: str,
        connection_type: str = "websocket",
        reason: Optional[str] = None
    ) -> ConnectionStatus:
        """Записать отключение"""
        exchange = exchange.upper()
        
        # Initialize if needed
        if exchange not in self._connections:
            self._connections[exchange] = {}
        if connection_type not in self._connections[exchange]:
            self.register_connection(exchange, connection_type)
        
        status = self._connections[exchange][connection_type]
        status.state = ConnectionState.DISCONNECTED
        status.last_disconnect_reason = reason
        status.reconnect_attempts += 1
        
        self._record_event(
            FailoverEventType.CONNECTION_LOST,
            exchange,
            f"{connection_type} disconnected: {reason}",
            severity="WARNING"
        )
        
        return status
    
    def record_reconnect_attempt(
        self,
        exchange: str,
        connection_type: str = "websocket",
        success: bool = False
    ) -> ConnectionStatus:
        """Записать попытку переподключения"""
        exchange = exchange.upper()
        
        if exchange not in self._connections or connection_type not in self._connections[exchange]:
            return self.register_connection(exchange, connection_type)
        
        status = self._connections[exchange][connection_type]
        
        if success:
            status.state = ConnectionState.CONNECTED
            status.connected_since = datetime.utcnow()
            status.last_heartbeat = datetime.utcnow()
            status.reconnect_attempts = 0
            
            self._record_event(
                FailoverEventType.CONNECTION_RESTORED,
                exchange,
                f"{connection_type} reconnected successfully"
            )
        else:
            status.reconnect_attempts += 1
            
            if status.reconnect_attempts >= self.max_reconnect_attempts:
                status.state = ConnectionState.FAILED
                self._record_event(
                    FailoverEventType.CONNECTION_LOST,
                    exchange,
                    f"{connection_type} failed after {status.reconnect_attempts} attempts",
                    severity="CRITICAL"
                )
            else:
                status.state = ConnectionState.RECONNECTING
        
        return status
    
    def check_health(self, exchange: str) -> Dict[str, Any]:
        """Проверить здоровье соединений"""
        exchange = exchange.upper()
        now = datetime.utcnow()
        
        if exchange not in self._connections:
            # Simulate healthy connection
            return self._mock_health(exchange)
        
        results = {}
        overall_healthy = True
        actions = []
        
        for conn_type, status in self._connections[exchange].items():
            # Check heartbeat timeout
            is_timed_out = False
            if status.last_heartbeat:
                time_since_heartbeat = (now - status.last_heartbeat).total_seconds()
                is_timed_out = time_since_heartbeat > self.heartbeat_timeout
            
            is_healthy = (
                status.state == ConnectionState.CONNECTED and
                not is_timed_out
            )
            
            if not is_healthy:
                overall_healthy = False
                if is_timed_out:
                    actions.append(f"Reconnect {conn_type}")
                if status.state == ConnectionState.FAILED:
                    actions.append(f"Use REST fallback for {conn_type}")
            
            results[conn_type] = {
                "state": status.state.value,
                "healthy": is_healthy,
                "last_heartbeat": status.last_heartbeat.isoformat() if status.last_heartbeat else None,
                "latency_ms": status.latency_ms,
                "reconnect_attempts": status.reconnect_attempts,
                "is_timed_out": is_timed_out
            }
        
        return {
            "exchange": exchange,
            "overall_healthy": overall_healthy,
            "connections": results,
            "recommended_actions": actions,
            "should_use_fallback": not overall_healthy
        }
    
    def get_status(
        self,
        exchange: str,
        connection_type: str = "websocket"
    ) -> Optional[ConnectionStatus]:
        """Получить статус соединения"""
        exchange = exchange.upper()
        
        if exchange in self._connections and connection_type in self._connections[exchange]:
            return self._connections[exchange][connection_type]
        return None
    
    def get_all_status(self) -> Dict[str, Dict[str, ConnectionStatus]]:
        """Получить все статусы"""
        return self._connections
    
    def get_recommended_action(self, exchange: str) -> FailoverAction:
        """Получить рекомендуемое действие"""
        health = self.check_health(exchange)
        
        if health["overall_healthy"]:
            return FailoverAction.NONE
        
        # Check connection states
        all_failed = True
        any_reconnecting = False
        
        for conn_info in health.get("connections", {}).values():
            if conn_info.get("state") != ConnectionState.FAILED.value:
                all_failed = False
            if conn_info.get("state") == ConnectionState.RECONNECTING.value:
                any_reconnecting = True
        
        if all_failed:
            return FailoverAction.SWITCH_EXCHANGE
        elif any_reconnecting:
            return FailoverAction.THROTTLE_REQUESTS
        else:
            return FailoverAction.LIMIT_NEW_ORDERS
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить недавние события"""
        return [
            {
                "event_type": e.event_type.value,
                "exchange": e.exchange,
                "message": e.message,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat()
            }
            for e in self._events[-limit:]
        ]
    
    def _record_event(
        self,
        event_type: FailoverEventType,
        exchange: str,
        message: str,
        severity: str = "INFO"
    ) -> None:
        """Записать событие"""
        event = FailoverEvent(
            id=f"conn_{datetime.utcnow().timestamp()}",
            event_type=event_type,
            exchange=exchange,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow()
        )
        self._events.append(event)
        
        # Keep only recent events
        if len(self._events) > 1000:
            self._events = self._events[-500:]
    
    def _mock_health(self, exchange: str) -> Dict[str, Any]:
        """Mock здоровье для тестирования"""
        return {
            "exchange": exchange,
            "overall_healthy": True,
            "connections": {
                "websocket": {
                    "state": "CONNECTED",
                    "healthy": True,
                    "last_heartbeat": datetime.utcnow().isoformat(),
                    "latency_ms": random.uniform(10, 50),
                    "reconnect_attempts": 0,
                    "is_timed_out": False
                },
                "rest": {
                    "state": "CONNECTED",
                    "healthy": True,
                    "last_heartbeat": datetime.utcnow().isoformat(),
                    "latency_ms": random.uniform(50, 150),
                    "reconnect_attempts": 0,
                    "is_timed_out": False
                }
            },
            "recommended_actions": [],
            "should_use_fallback": False
        }
