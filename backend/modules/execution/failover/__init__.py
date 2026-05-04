"""
PHASE 4.4 — Failover Engine
===========================

Защита системы от инфраструктурных рисков:
- Exchange Health Monitor: API availability, latency, error rate
- Latency Monitor: latency tracking and alerts
- Rate Limit Monitor: rate limit tracking
- Connection Guard: WebSocket/REST connection monitoring
- Failover Engine: decision making for system status

System Status Modes:
- NORMAL: всё работает
- DEGRADED: reduce trading frequency, limit new positions
- FAILOVER: pause trading, close risky positions, switch exchange
- EMERGENCY: freeze execution, cancel orders, secure positions
"""

from .failover_types import (
    SystemStatus,
    ExchangeStatus,
    LatencyGrade,
    ConnectionState,
    FailoverAction,
    FailoverEventType,
    ExchangeHealthMetrics,
    LatencySnapshot,
    RateLimitStatus,
    ConnectionStatus,
    FailoverEvent,
    FailoverState,
    FailoverConfig,
    FailoverHistoryQuery
)
from .exchange_health_monitor import ExchangeHealthMonitor
from .latency_monitor import LatencyMonitor
from .rate_limit_monitor import RateLimitMonitor
from .connection_guard import ConnectionGuard
from .failover_engine import FailoverEngine
from .failover_repository import FailoverRepository

__all__ = [
    # Status enums
    "SystemStatus",
    "ExchangeStatus",
    "LatencyGrade",
    "ConnectionState",
    "FailoverAction",
    "FailoverEventType",
    # Data models
    "ExchangeHealthMetrics",
    "LatencySnapshot",
    "RateLimitStatus",
    "ConnectionStatus",
    "FailoverEvent",
    "FailoverState",
    "FailoverConfig",
    "FailoverHistoryQuery",
    # Monitors
    "ExchangeHealthMonitor",
    "LatencyMonitor",
    "RateLimitMonitor",
    "ConnectionGuard",
    # Engine
    "FailoverEngine",
    "FailoverRepository"
]
