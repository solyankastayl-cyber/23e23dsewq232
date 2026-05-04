"""
Safety Types (SEC1)
===================

Type definitions for Execution Safety Layer.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class SafetyDecision(Enum):
    """Safety validation decision"""
    ALLOW = "ALLOW"         # Order proceeds
    BLOCK = "BLOCK"         # Order blocked
    WARN = "WARN"           # Order proceeds with warning
    QUARANTINE = "QUARANTINE"  # Exchange/symbol quarantined


class SafetyGuardType(Enum):
    """Types of safety guards"""
    DUPLICATE = "DUPLICATE"
    POSITION = "POSITION"
    RATE = "RATE"
    STALE = "STALE"
    EXCHANGE_SYNC = "EXCHANGE_SYNC"


class SafetyEventType(Enum):
    """Safety event types for logging"""
    ORDER_BLOCKED_DUPLICATE = "ORDER_BLOCKED_DUPLICATE"
    ORDER_BLOCKED_RATE_LIMIT = "ORDER_BLOCKED_RATE_LIMIT"
    ORDER_BLOCKED_POSITION_LIMIT = "ORDER_BLOCKED_POSITION_LIMIT"
    STALE_ORDER_DETECTED = "STALE_ORDER_DETECTED"
    EXCHANGE_DESYNC = "EXCHANGE_DESYNC"
    SYMBOL_QUARANTINED = "SYMBOL_QUARANTINED"
    EXCHANGE_QUARANTINED = "EXCHANGE_QUARANTINED"
    GUARD_WARNING = "GUARD_WARNING"
    CONFIG_UPDATED = "CONFIG_UPDATED"


# ===========================================
# Configuration Types
# ===========================================

@dataclass
class DuplicateGuardConfig:
    """Duplicate order detection config"""
    enabled: bool = True
    window_seconds: int = 5
    check_price_tolerance_pct: float = 0.1
    check_size_tolerance_pct: float = 0.01
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "windowSeconds": self.window_seconds,
            "priceTolerance": self.check_price_tolerance_pct,
            "sizeTolerance": self.check_size_tolerance_pct
        }


@dataclass
class PositionGuardConfig:
    """Position limit config"""
    enabled: bool = True
    max_position_size_usd: float = 100000.0
    max_leverage: float = 10.0
    max_scaling_depth: int = 3
    allow_direction_conflict: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "maxPositionSizeUsd": self.max_position_size_usd,
            "maxLeverage": self.max_leverage,
            "maxScalingDepth": self.max_scaling_depth,
            "allowDirectionConflict": self.allow_direction_conflict
        }


@dataclass
class RateGuardConfig:
    """Rate limiting config"""
    enabled: bool = True
    max_orders_per_minute: int = 10
    max_orders_per_symbol_per_minute: int = 5
    max_orders_per_strategy_per_minute: int = 8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "maxOrdersPerMinute": self.max_orders_per_minute,
            "maxOrdersPerSymbol": self.max_orders_per_symbol_per_minute,
            "maxOrdersPerStrategy": self.max_orders_per_strategy_per_minute
        }


@dataclass
class StaleOrderConfig:
    """Stale order detection config"""
    enabled: bool = True
    stale_threshold_minutes: int = 30
    auto_cancel_stale: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "staleThresholdMinutes": self.stale_threshold_minutes,
            "autoCancelStale": self.auto_cancel_stale
        }


@dataclass
class ExchangeSyncConfig:
    """Exchange sync validation config"""
    enabled: bool = True
    position_tolerance_pct: float = 0.01
    balance_tolerance_pct: float = 0.005
    sync_interval_seconds: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "positionTolerance": self.position_tolerance_pct,
            "balanceTolerance": self.balance_tolerance_pct,
            "syncIntervalSeconds": self.sync_interval_seconds
        }


@dataclass
class SafetyConfig:
    """Complete safety configuration"""
    duplicate: DuplicateGuardConfig = field(default_factory=DuplicateGuardConfig)
    position: PositionGuardConfig = field(default_factory=PositionGuardConfig)
    rate: RateGuardConfig = field(default_factory=RateGuardConfig)
    stale: StaleOrderConfig = field(default_factory=StaleOrderConfig)
    exchange_sync: ExchangeSyncConfig = field(default_factory=ExchangeSyncConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "duplicate": self.duplicate.to_dict(),
            "position": self.position.to_dict(),
            "rate": self.rate.to_dict(),
            "stale": self.stale.to_dict(),
            "exchangeSync": self.exchange_sync.to_dict()
        }


# ===========================================
# Request/Response Types
# ===========================================

@dataclass
class OrderValidationRequest:
    """Request to validate an order"""
    order_id: str = field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:8]}")
    symbol: str = ""
    side: str = ""  # BUY / SELL
    order_type: str = ""  # MARKET / LIMIT
    size: float = 0.0
    price: Optional[float] = None
    strategy_id: Optional[str] = None
    exchange: str = "binance"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "orderId": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "orderType": self.order_type,
            "size": self.size,
            "price": self.price,
            "strategyId": self.strategy_id,
            "exchange": self.exchange,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class SafetyDecisionResult:
    """Result of safety validation"""
    decision: SafetyDecision = SafetyDecision.ALLOW
    reason: str = ""
    guard: Optional[SafetyGuardType] = None
    order_id: str = ""
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "guard": self.guard.value if self.guard else None,
            "orderId": self.order_id,
            "warnings": self.warnings,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class SafetyEvent:
    """Safety event for logging/audit"""
    event_id: str = field(default_factory=lambda: f"sevt_{uuid.uuid4().hex[:8]}")
    event_type: SafetyEventType = SafetyEventType.GUARD_WARNING
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    guard: Optional[SafetyGuardType] = None
    decision: Optional[SafetyDecision] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type.value,
            "orderId": self.order_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "guard": self.guard.value if self.guard else None,
            "decision": self.decision.value if self.decision else None,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# State Types
# ===========================================

@dataclass
class QuarantineState:
    """Quarantine state for symbol/exchange"""
    quarantine_id: str = field(default_factory=lambda: f"qrtn_{uuid.uuid4().hex[:6]}")
    target_type: str = ""  # SYMBOL or EXCHANGE
    target: str = ""       # symbol or exchange name
    reason: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "quarantineId": self.quarantine_id,
            "targetType": self.target_type,
            "target": self.target,
            "reason": self.reason,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "active": self.active
        }


@dataclass
class SafetyStats:
    """Safety statistics"""
    total_validations: int = 0
    blocked_orders: int = 0
    warnings_issued: int = 0
    duplicate_blocks: int = 0
    rate_limit_blocks: int = 0
    position_limit_blocks: int = 0
    stale_orders_detected: int = 0
    exchange_desyncs: int = 0
    active_quarantines: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalValidations": self.total_validations,
            "blockedOrders": self.blocked_orders,
            "warningsIssued": self.warnings_issued,
            "duplicateBlocks": self.duplicate_blocks,
            "rateLimitBlocks": self.rate_limit_blocks,
            "positionLimitBlocks": self.position_limit_blocks,
            "staleOrdersDetected": self.stale_orders_detected,
            "exchangeDesyncs": self.exchange_desyncs,
            "activeQuarantines": self.active_quarantines
        }
