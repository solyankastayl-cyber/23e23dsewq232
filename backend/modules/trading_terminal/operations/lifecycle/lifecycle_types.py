"""
OPS2 Lifecycle Types
====================

Data structures for position lifecycle tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class LifecyclePhase(str, Enum):
    """Position lifecycle phases"""
    ENTRY = "ENTRY"           # Signal → Decision → Order → Fill → Open
    ACTIVE = "ACTIVE"         # Position running
    ADJUSTMENT = "ADJUSTMENT" # Scale/Reduce/Hedge/Stop changes
    EXIT = "EXIT"             # Close order → Close fill
    CLOSED = "CLOSED"         # Position fully closed


class LifecycleEventType(str, Enum):
    """Types of lifecycle events"""
    # Entry phase
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
    DECISION_MADE = "DECISION_MADE"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_OPENED = "POSITION_OPENED"
    
    # Adjustment phase
    POSITION_SCALED = "POSITION_SCALED"
    POSITION_REDUCED = "POSITION_REDUCED"
    POSITION_HEDGED = "POSITION_HEDGED"
    STOP_UPDATED = "STOP_UPDATED"
    TP_UPDATED = "TP_UPDATED"
    
    # Exit phase
    CLOSE_ORDER_CREATED = "CLOSE_ORDER_CREATED"
    CLOSE_ORDER_FILLED = "CLOSE_ORDER_FILLED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_LIQUIDATED = "POSITION_LIQUIDATED"
    FORCED_CLOSE = "FORCED_CLOSE"


@dataclass
class LifecycleEvent:
    """
    Single event in position lifecycle.
    """
    event_id: str = ""
    event_type: str = ""
    phase: LifecyclePhase = LifecyclePhase.ACTIVE
    
    timestamp: int = 0
    
    # Price/size at event
    price: Optional[float] = None
    size: Optional[float] = None
    
    # PnL at event
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Duration since previous event (ms)
    duration_from_prev: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "phase": self.phase.value,
            "timestamp": self.timestamp,
            "price": self.price,
            "size": self.size,
            "pnl": round(self.pnl, 2) if self.pnl else None,
            "pnlPct": round(self.pnl_pct, 4) if self.pnl_pct else None,
            "metadata": self.metadata,
            "durationFromPrev": self.duration_from_prev
        }


@dataclass
class LifecycleStats:
    """
    Statistics for a position lifecycle.
    """
    position_id: str = ""
    
    # Duration
    total_duration_minutes: float = 0.0
    entry_duration_minutes: float = 0.0  # Signal to open
    active_duration_minutes: float = 0.0  # Open to close start
    exit_duration_minutes: float = 0.0  # Close start to close
    
    # Prices
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    avg_price: float = 0.0
    
    # MAE/MFE (Maximum Adverse/Favorable Excursion)
    mae: float = 0.0  # Maximum Adverse Excursion (worst loss)
    mae_pct: float = 0.0
    mae_timestamp: Optional[int] = None
    
    mfe: float = 0.0  # Maximum Favorable Excursion (best profit)
    mfe_pct: float = 0.0
    mfe_timestamp: Optional[int] = None
    
    # Final result
    realized_pnl: float = 0.0
    realized_pnl_pct: float = 0.0
    
    # Event counts
    total_events: int = 0
    scale_events: int = 0
    reduce_events: int = 0
    stop_updates: int = 0
    
    # Efficiency metrics
    capture_efficiency: float = 0.0  # realized_pnl / mfe (how much of max profit was captured)
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "totalDurationMinutes": round(self.total_duration_minutes, 1),
            "entryDurationMinutes": round(self.entry_duration_minutes, 1),
            "activeDurationMinutes": round(self.active_duration_minutes, 1),
            "exitDurationMinutes": round(self.exit_duration_minutes, 1),
            "entryPrice": self.entry_price,
            "exitPrice": self.exit_price,
            "avgPrice": self.avg_price,
            "mae": round(self.mae, 2),
            "maePct": round(self.mae_pct, 4),
            "maeTimestamp": self.mae_timestamp,
            "mfe": round(self.mfe, 2),
            "mfePct": round(self.mfe_pct, 4),
            "mfeTimestamp": self.mfe_timestamp,
            "realizedPnl": round(self.realized_pnl, 2),
            "realizedPnlPct": round(self.realized_pnl_pct, 4),
            "totalEvents": self.total_events,
            "scaleEvents": self.scale_events,
            "reduceEvents": self.reduce_events,
            "stopUpdates": self.stop_updates,
            "captureEfficiency": round(self.capture_efficiency, 4),
            "computedAt": self.computed_at
        }


@dataclass
class PositionLifecycle:
    """
    Complete lifecycle of a position.
    """
    position_id: str = ""
    symbol: str = ""
    exchange: str = ""
    side: str = ""
    
    # Ownership
    strategy_id: Optional[str] = None
    profile_id: Optional[str] = None
    
    # Timing
    opened_at: int = 0
    closed_at: Optional[int] = None
    
    # Current phase
    current_phase: LifecyclePhase = LifecyclePhase.ENTRY
    
    # Timeline
    events: List[LifecycleEvent] = field(default_factory=list)
    
    # Stats
    stats: Optional[LifecycleStats] = None
    
    # Price tracking for MAE/MFE
    price_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Is lifecycle complete?
    is_closed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side,
            "strategyId": self.strategy_id,
            "profileId": self.profile_id,
            "openedAt": self.opened_at,
            "closedAt": self.closed_at,
            "currentPhase": self.current_phase.value,
            "events": [e.to_dict() for e in self.events],
            "eventCount": len(self.events),
            "stats": self.stats.to_dict() if self.stats else None,
            "isClosed": self.is_closed
        }
    
    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get simplified timeline"""
        return [
            {
                "type": e.event_type,
                "phase": e.phase.value,
                "timestamp": e.timestamp,
                "price": e.price,
                "pnl": e.pnl
            }
            for e in self.events
        ]
