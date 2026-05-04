"""
Failover Types
==============

Типы данных для Failover Engine.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SystemStatus(str, Enum):
    """Статус системы"""
    NORMAL = "NORMAL"           # Всё работает нормально
    DEGRADED = "DEGRADED"       # Деградация производительности
    FAILOVER = "FAILOVER"       # Активный failover режим
    EMERGENCY = "EMERGENCY"     # Экстренная остановка


class ExchangeStatus(str, Enum):
    """Статус биржи"""
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


class LatencyGrade(str, Enum):
    """Оценка латентности"""
    EXCELLENT = "EXCELLENT"    # < 50ms
    GOOD = "GOOD"              # 50-100ms
    NORMAL = "NORMAL"          # 100-200ms
    DEGRADED = "DEGRADED"      # 200-500ms
    POOR = "POOR"              # 500-800ms
    CRITICAL = "CRITICAL"      # > 800ms


class ConnectionState(str, Enum):
    """Состояние соединения"""
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"
    FAILED = "FAILED"


class FailoverAction(str, Enum):
    """Действия failover"""
    NONE = "NONE"
    THROTTLE_REQUESTS = "THROTTLE_REQUESTS"
    LIMIT_NEW_ORDERS = "LIMIT_NEW_ORDERS"
    REDUCE_POSITION_SIZE = "REDUCE_POSITION_SIZE"
    PAUSE_NEW_POSITIONS = "PAUSE_NEW_POSITIONS"
    CLOSE_RISKY_POSITIONS = "CLOSE_RISKY_POSITIONS"
    SWITCH_EXCHANGE = "SWITCH_EXCHANGE"
    CANCEL_PENDING_ORDERS = "CANCEL_PENDING_ORDERS"
    FREEZE_EXECUTION = "FREEZE_EXECUTION"
    SECURE_POSITIONS = "SECURE_POSITIONS"


class FailoverEventType(str, Enum):
    """Тип события failover"""
    STATUS_CHANGE = "STATUS_CHANGE"
    LATENCY_SPIKE = "LATENCY_SPIKE"
    ERROR_SPIKE = "ERROR_SPIKE"
    RATE_LIMIT_BREACH = "RATE_LIMIT_BREACH"
    CONNECTION_LOST = "CONNECTION_LOST"
    CONNECTION_RESTORED = "CONNECTION_RESTORED"
    EXCHANGE_OUTAGE = "EXCHANGE_OUTAGE"
    EXCHANGE_RESTORED = "EXCHANGE_RESTORED"
    ACTION_TRIGGERED = "ACTION_TRIGGERED"


# ============================================
# Exchange Health
# ============================================

class ExchangeHealthMetrics(BaseModel):
    """Метрики здоровья биржи"""
    exchange: str
    status: ExchangeStatus = ExchangeStatus.UNKNOWN
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Latency
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    latency_grade: LatencyGrade = LatencyGrade.NORMAL
    
    # Error rates
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    error_count_1m: int = 0
    success_count_1m: int = 0
    
    # API status
    api_available: bool = True
    websocket_connected: bool = True
    last_successful_request: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Rate limits
    rate_limit_remaining: int = Field(default=1200, description="Remaining requests")
    rate_limit_reset_at: Optional[datetime] = None
    rate_limit_approaching: bool = False
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LatencySnapshot(BaseModel):
    """Снимок латентности"""
    exchange: str
    endpoint: str = "general"
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_timeout: bool = False
    error: Optional[str] = None


class RateLimitStatus(BaseModel):
    """Статус rate limit"""
    exchange: str
    limit_type: str = Field(default="requests", description="requests/orders/weight")
    limit_value: int = 1200
    used_value: int = 0
    remaining: int = 1200
    reset_at: Optional[datetime] = None
    window_seconds: int = 60
    utilization_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    is_approaching_limit: bool = False
    is_exceeded: bool = False


class ConnectionStatus(BaseModel):
    """Статус соединения"""
    exchange: str
    connection_type: str = Field(default="websocket", description="websocket/rest")
    state: ConnectionState = ConnectionState.CONNECTED
    connected_since: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    reconnect_attempts: int = 0
    last_disconnect_reason: Optional[str] = None
    latency_ms: float = 0.0


# ============================================
# Failover Events
# ============================================

class FailoverEvent(BaseModel):
    """Событие failover"""
    id: str = ""
    event_type: FailoverEventType
    exchange: Optional[str] = None
    
    previous_status: Optional[SystemStatus] = None
    new_status: Optional[SystemStatus] = None
    
    action_triggered: Optional[FailoverAction] = None
    severity: str = Field(default="INFO", description="INFO/WARNING/CRITICAL")
    
    details: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Failover State
# ============================================

class FailoverState(BaseModel):
    """Полное состояние failover системы"""
    system_status: SystemStatus = SystemStatus.NORMAL
    
    # Exchange states
    exchanges: Dict[str, ExchangeHealthMetrics] = Field(default_factory=dict)
    primary_exchange: str = "BINANCE"
    fallback_exchange: Optional[str] = "BYBIT"
    
    # Active actions
    active_actions: List[FailoverAction] = Field(default_factory=list)
    
    # Thresholds
    throttle_factor: float = Field(default=1.0, ge=0.0, le=1.0, description="1.0 = no throttle")
    position_size_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    new_positions_allowed: bool = True
    execution_paused: bool = False
    
    # Counts
    recent_errors: int = 0
    recent_timeouts: int = 0
    active_failover_exchanges: List[str] = Field(default_factory=list)
    
    # Timestamps
    last_status_change: Optional[datetime] = None
    failover_started_at: Optional[datetime] = None
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FailoverConfig(BaseModel):
    """Конфигурация failover"""
    # Latency thresholds
    latency_normal_ms: float = 200.0
    latency_degraded_ms: float = 500.0
    latency_critical_ms: float = 800.0
    
    # Error rate thresholds
    error_rate_warning: float = 0.05  # 5%
    error_rate_critical: float = 0.15  # 15%
    
    # Rate limit thresholds
    rate_limit_warning_pct: float = 70.0
    rate_limit_critical_pct: float = 90.0
    
    # Timeouts
    api_timeout_ms: float = 5000.0
    websocket_heartbeat_timeout_ms: float = 30000.0
    
    # Recovery
    auto_recovery_enabled: bool = True
    recovery_check_interval_seconds: int = 30
    min_recovery_health_score: float = 0.8


class FailoverHistoryQuery(BaseModel):
    """Запрос истории failover"""
    exchange: Optional[str] = None
    event_type: Optional[FailoverEventType] = None
    severity: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
