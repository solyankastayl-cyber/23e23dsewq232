"""
Reconciliation Types
====================

Core types for PHASE 4.2 Execution Reconciliation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class DiscrepancyType(str, Enum):
    """Types of discrepancies"""
    # Position discrepancies
    GHOST_POSITION = "GHOST_POSITION"         # Exchange has position, system doesn't
    MISSING_POSITION = "MISSING_POSITION"     # System has position, exchange doesn't
    POSITION_SIZE_MISMATCH = "POSITION_SIZE_MISMATCH"   # Size differs
    POSITION_SIDE_MISMATCH = "POSITION_SIDE_MISMATCH"   # Side differs
    
    # Order discrepancies
    GHOST_ORDER = "GHOST_ORDER"               # Exchange has order, system doesn't
    MISSING_ORDER = "MISSING_ORDER"           # System has order, exchange doesn't
    ORDER_STATE_MISMATCH = "ORDER_STATE_MISMATCH"       # State differs
    ORDER_FILL_MISMATCH = "ORDER_FILL_MISMATCH"         # Fill amount differs
    
    # Balance discrepancies
    BALANCE_DRIFT = "BALANCE_DRIFT"           # Balance differs from expected
    MARGIN_MISMATCH = "MARGIN_MISMATCH"       # Margin differs


class DiscrepancySeverity(str, Enum):
    """Severity levels"""
    INFO = "INFO"           # Minor, informational
    WARNING = "WARNING"     # Should be monitored
    HIGH = "HIGH"           # Needs attention
    CRITICAL = "CRITICAL"   # Immediate action required


class ResolutionStrategy(str, Enum):
    """Resolution strategies"""
    SOFT_SYNC = "SOFT_SYNC"           # Update internal state only
    HARD_SYNC = "HARD_SYNC"           # Close positions, reset state
    ORDER_RECOVERY = "ORDER_RECOVERY" # Reconnect lost orders
    BALANCE_REFRESH = "BALANCE_REFRESH"  # Refresh balance from exchange
    MANUAL = "MANUAL"                 # Requires manual intervention
    IGNORE = "IGNORE"                 # Ignore (below threshold)


class ReconciliationStatus(str, Enum):
    """Reconciliation run status"""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"  # Some corrections failed


class ResolutionStatus(str, Enum):
    """Resolution status"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ===========================================
# Exchange State Types
# ===========================================

@dataclass
class ExchangePosition:
    """Position as reported by exchange"""
    symbol: str = ""
    side: str = ""  # LONG, SHORT
    size: float = 0.0
    entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    margin: float = 0.0
    leverage: int = 1
    liquidation_price: float = 0.0
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": round(self.size, 8),
            "entryPrice": round(self.entry_price, 8),
            "unrealizedPnl": round(self.unrealized_pnl, 2),
            "margin": round(self.margin, 2),
            "leverage": self.leverage,
            "liquidationPrice": round(self.liquidation_price, 8),
            "updatedAt": self.updated_at
        }


@dataclass
class ExchangeOrder:
    """Order as reported by exchange"""
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    status: str = ""
    quantity: float = 0.0
    filled_quantity: float = 0.0
    price: float = 0.0
    avg_fill_price: float = 0.0
    created_at: int = 0
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "orderId": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "status": self.status,
            "quantity": round(self.quantity, 8),
            "filledQuantity": round(self.filled_quantity, 8),
            "price": round(self.price, 8),
            "avgFillPrice": round(self.avg_fill_price, 8),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }


@dataclass
class ExchangeBalance:
    """Balance as reported by exchange"""
    asset: str = ""
    total: float = 0.0
    available: float = 0.0
    locked: float = 0.0
    unrealized_pnl: float = 0.0
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "total": round(self.total, 8),
            "available": round(self.available, 8),
            "locked": round(self.locked, 8),
            "unrealizedPnl": round(self.unrealized_pnl, 2),
            "updatedAt": self.updated_at
        }


@dataclass
class ExchangeState:
    """Complete exchange state snapshot"""
    exchange: str = ""
    positions: List[ExchangePosition] = field(default_factory=list)
    orders: List[ExchangeOrder] = field(default_factory=list)
    balances: List[ExchangeBalance] = field(default_factory=list)
    fetched_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "positions": [p.to_dict() for p in self.positions],
            "orders": [o.to_dict() for o in self.orders],
            "balances": [b.to_dict() for b in self.balances],
            "fetchedAt": self.fetched_at
        }


# ===========================================
# Internal State Types
# ===========================================

@dataclass
class InternalPosition:
    """Position as tracked by system"""
    position_id: str = ""
    symbol: str = ""
    side: str = ""
    size: float = 0.0
    entry_price: float = 0.0
    strategy_id: str = ""
    created_at: int = 0
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "size": round(self.size, 8),
            "entryPrice": round(self.entry_price, 8),
            "strategyId": self.strategy_id,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }


@dataclass
class InternalBalance:
    """Balance as tracked by system"""
    asset: str = ""
    total: float = 0.0
    available: float = 0.0
    reserved: float = 0.0
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "total": round(self.total, 8),
            "available": round(self.available, 8),
            "reserved": round(self.reserved, 8),
            "updatedAt": self.updated_at
        }


# ===========================================
# Discrepancy
# ===========================================

@dataclass
class Discrepancy:
    """Detected discrepancy"""
    discrepancy_id: str = ""
    discrepancy_type: DiscrepancyType = DiscrepancyType.BALANCE_DRIFT
    severity: DiscrepancySeverity = DiscrepancySeverity.WARNING
    
    # Context
    exchange: str = ""
    symbol: str = ""
    
    # Values
    internal_value: Any = None
    exchange_value: Any = None
    difference: float = 0.0
    difference_pct: float = 0.0
    
    # Details
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Resolution
    resolution_strategy: ResolutionStrategy = ResolutionStrategy.SOFT_SYNC
    resolution_status: ResolutionStatus = ResolutionStatus.PENDING
    resolution_details: str = ""
    
    # Timestamps
    detected_at: int = 0
    resolved_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "discrepancyId": self.discrepancy_id,
            "type": self.discrepancy_type.value,
            "severity": self.severity.value,
            "context": {
                "exchange": self.exchange,
                "symbol": self.symbol
            },
            "values": {
                "internal": self.internal_value,
                "exchange": self.exchange_value,
                "difference": round(self.difference, 8) if isinstance(self.difference, (int, float)) else self.difference,
                "differencePct": round(self.difference_pct, 2)
            },
            "description": self.description,
            "details": self.details,
            "resolution": {
                "strategy": self.resolution_strategy.value,
                "status": self.resolution_status.value,
                "details": self.resolution_details
            },
            "timestamps": {
                "detectedAt": self.detected_at,
                "resolvedAt": self.resolved_at
            }
        }


# ===========================================
# Reconciliation Run
# ===========================================

@dataclass
class ReconciliationRun:
    """Complete reconciliation run"""
    run_id: str = ""
    exchange: str = ""
    status: ReconciliationStatus = ReconciliationStatus.RUNNING
    
    # Scope
    check_positions: bool = True
    check_orders: bool = True
    check_balances: bool = True
    
    # Results
    discrepancies: List[Discrepancy] = field(default_factory=list)
    discrepancies_detected: int = 0
    discrepancies_resolved: int = 0
    discrepancies_failed: int = 0
    
    # State snapshots
    exchange_state: Optional[ExchangeState] = None
    
    # Timing
    started_at: int = 0
    completed_at: int = 0
    duration_ms: int = 0
    
    # Error
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "exchange": self.exchange,
            "status": self.status.value,
            "scope": {
                "checkPositions": self.check_positions,
                "checkOrders": self.check_orders,
                "checkBalances": self.check_balances
            },
            "results": {
                "detected": self.discrepancies_detected,
                "resolved": self.discrepancies_resolved,
                "failed": self.discrepancies_failed,
                "discrepancies": [d.to_dict() for d in self.discrepancies]
            },
            "exchangeState": self.exchange_state.to_dict() if self.exchange_state else None,
            "timing": {
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
                "durationMs": self.duration_ms
            },
            "error": self.error if self.error else None
        }


# ===========================================
# Reconciliation Event
# ===========================================

@dataclass
class ReconciliationEvent:
    """Event in reconciliation ledger"""
    event_id: str = ""
    event_type: str = ""  # RECONCILIATION_STARTED, DISCREPANCY_DETECTED, etc.
    run_id: str = ""
    discrepancy_id: str = ""
    
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "runId": self.run_id,
            "discrepancyId": self.discrepancy_id,
            "details": self.details,
            "timestamp": self.timestamp
        }


# ===========================================
# Reconciliation Summary
# ===========================================

@dataclass
class ReconciliationSummary:
    """Summary of reconciliation state"""
    total_runs: int = 0
    last_run_at: int = 0
    last_run_status: str = ""
    
    total_discrepancies: int = 0
    pending_discrepancies: int = 0
    resolved_discrepancies: int = 0
    
    by_type: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "runs": {
                "total": self.total_runs,
                "lastAt": self.last_run_at,
                "lastStatus": self.last_run_status
            },
            "discrepancies": {
                "total": self.total_discrepancies,
                "pending": self.pending_discrepancies,
                "resolved": self.resolved_discrepancies
            },
            "breakdown": {
                "byType": self.by_type,
                "bySeverity": self.by_severity
            }
        }
