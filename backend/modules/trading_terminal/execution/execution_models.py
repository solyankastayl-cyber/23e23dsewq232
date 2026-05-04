"""
Execution Models for Trading Terminal
=====================================

Core data structures for execution lifecycle:
- ExecutionIntent: bridge between decision and order
- OrderState: order lifecycle tracking
- ExecutionStatusSummary: terminal state integration
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class ExecutionState(str, Enum):
    IDLE = "IDLE"
    WAITING_ENTRY = "WAITING_ENTRY"
    READY_TO_PLACE = "READY_TO_PLACE"
    ORDER_PLANNED = "ORDER_PLANNED"
    ORDER_PLACED = "ORDER_PLACED"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


@dataclass
class ExecutionIntent:
    """Bridge between decision and order"""
    intent_id: str
    symbol: str
    timeframe: str

    action: str
    direction: str

    entry_mode: str
    execution_mode: str

    planned_entry: Optional[float]
    planned_stop: Optional[float]
    planned_target: Optional[float]
    planned_rr: Optional[float]

    size_multiplier: float
    execution_confidence: float

    status: str
    reason: str

    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrderState:
    """Order lifecycle tracking"""
    order_id: str
    intent_id: str
    symbol: str
    side: str

    order_type: str
    status: str

    price: Optional[float]
    size: float
    filled_size: float
    remaining_size: float

    avg_fill_price: Optional[float]
    time_in_force: str

    placed_at: str
    updated_at: str

    cancel_reason: Optional[str] = None
    reject_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @property
    def filled_pct(self) -> float:
        if self.size <= 0:
            return 0.0
        return round(self.filled_size / self.size, 4)


@dataclass
class ExecutionStatusSummary:
    """Summary for terminal state integration"""
    execution_state: str
    intent_state: str

    order_present: bool
    position_open: bool

    order_id: Optional[str]
    filled_pct: float

    status_label: str
    status_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
