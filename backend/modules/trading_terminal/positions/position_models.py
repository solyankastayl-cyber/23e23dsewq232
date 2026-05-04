"""
Position Models for Trading Terminal
=====================================

Core data structures for position lifecycle:
- Position: main position object with PnL, health, etc.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class PositionStatus(str, Enum):
    OPENING = "OPENING"
    OPEN = "OPEN"
    SCALING = "SCALING"
    REDUCING = "REDUCING"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class PositionHealth(str, Enum):
    GOOD = "GOOD"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Position:
    """Main position object"""
    position_id: str
    symbol: str
    timeframe: str

    side: str  # LONG / SHORT
    status: str  # OPENING / OPEN / SCALING / REDUCING / CLOSING / CLOSED

    size: float
    entry_price: float
    mark_price: float

    unrealized_pnl: float
    pnl_pct: float

    stop: Optional[float]
    target: Optional[float]
    rr: Optional[float]

    entry_mode: str
    execution_mode: str
    micro_score_at_entry: float

    health: str  # GOOD / WARNING / CRITICAL
    age_sec: int

    order_id: Optional[str]
    intent_id: Optional[str]

    created_at: str
    updated_at: str
    closed_at: Optional[str] = None
    realized_pnl: Optional[float] = None
    close_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @property
    def is_open(self) -> bool:
        return self.status in {"OPENING", "OPEN", "SCALING", "REDUCING", "CLOSING"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
