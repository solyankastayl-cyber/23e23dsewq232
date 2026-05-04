"""
Event Ledger Types
==================

Data structures for immutable event storage.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class AggregateType(str, Enum):
    """Types of aggregates that generate events"""
    ORDER = "ORDER"
    POSITION = "POSITION"
    TRADE = "TRADE"
    STRATEGY = "STRATEGY"
    PROFILE = "PROFILE"
    ACCOUNT = "ACCOUNT"
    RISK = "RISK"
    RECONCILIATION = "RECONCILIATION"
    REGIME = "REGIME"
    SYSTEM = "SYSTEM"


class EventType(str, Enum):
    """All supported event types"""
    
    # Strategy Events
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
    STRATEGY_DECISION_MADE = "STRATEGY_DECISION_MADE"
    STRATEGY_BLOCKED = "STRATEGY_BLOCKED"
    STRATEGY_SELECTED = "STRATEGY_SELECTED"
    
    # Profile Events
    PROFILE_SWITCHED = "PROFILE_SWITCHED"
    CONFIG_SWITCHED = "CONFIG_SWITCHED"
    CONFIG_UPDATED = "CONFIG_UPDATED"
    
    # Order Events
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_VALIDATED = "ORDER_VALIDATED"
    ORDER_BLOCKED = "ORDER_BLOCKED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    
    # Position Events
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_SCALED = "POSITION_SCALED"
    POSITION_REDUCED = "POSITION_REDUCED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_LIQUIDATED = "POSITION_LIQUIDATED"
    
    # Trade Events
    TRADE_OPENED = "TRADE_OPENED"
    TRADE_CLOSED = "TRADE_CLOSED"
    TRADE_UPDATED = "TRADE_UPDATED"
    
    # Risk Events
    RISK_ALERT_RAISED = "RISK_ALERT_RAISED"
    RISK_ALERT_CLEARED = "RISK_ALERT_CLEARED"
    RISK_LEVEL_CHANGED = "RISK_LEVEL_CHANGED"
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"
    KILL_SWITCH_RESET = "KILL_SWITCH_RESET"
    SAFETY_BLOCK_TRIGGERED = "SAFETY_BLOCK_TRIGGERED"
    
    # Reconciliation Events
    RECON_RUN_STARTED = "RECON_RUN_STARTED"
    RECON_RUN_COMPLETED = "RECON_RUN_COMPLETED"
    RECON_MISMATCH_DETECTED = "RECON_MISMATCH_DETECTED"
    RECON_MISMATCH_RESOLVED = "RECON_MISMATCH_RESOLVED"
    SYMBOL_FROZEN = "SYMBOL_FROZEN"
    SYMBOL_UNFROZEN = "SYMBOL_UNFROZEN"
    EXCHANGE_QUARANTINED = "EXCHANGE_QUARANTINED"
    EXCHANGE_RESTORED = "EXCHANGE_RESTORED"
    
    # Regime Events
    REGIME_CHANGED = "REGIME_CHANGED"
    REGIME_TRANSITION_DETECTED = "REGIME_TRANSITION_DETECTED"
    
    # System Events
    SYSTEM_STARTED = "SYSTEM_STARTED"
    SYSTEM_STOPPED = "SYSTEM_STOPPED"
    MODULE_INITIALIZED = "MODULE_INITIALIZED"
    MODULE_ERROR = "MODULE_ERROR"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"


class SourceModule(str, Enum):
    """Modules that can publish events"""
    STRATEGY = "strategy"
    EXECUTION = "execution"
    RISK = "risk"
    SECURITY = "security"
    RECONCILIATION = "reconciliation"
    REGIME = "regime"
    TERMINAL = "terminal"
    BROKER = "broker"
    SYSTEM = "system"


@dataclass
class EventMetadata:
    """Additional metadata for events"""
    correlation_id: str = ""      # Links related events
    causation_id: str = ""        # What event caused this
    user_id: str = ""             # If user-initiated
    ip_address: str = ""          # Source IP
    session_id: str = ""          # Session context
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlationId": self.correlation_id,
            "causationId": self.causation_id,
            "userId": self.user_id,
            "ipAddress": self.ip_address,
            "sessionId": self.session_id,
            "tags": self.tags
        }


@dataclass
class LedgerEvent:
    """
    Immutable event record.
    
    Once written, events cannot be modified or deleted.
    """
    
    # Unique event identifier
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    
    # Event classification
    event_type: EventType = EventType.SYSTEM_STARTED
    aggregate_type: AggregateType = AggregateType.SYSTEM
    aggregate_id: str = ""  # ID of the entity this event relates to
    
    # Event data (immutable after creation)
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Source information
    source_module: str = "system"
    
    # Timing (immutable)
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    # Version for optimistic concurrency
    version: int = 1
    
    # Optional metadata
    metadata: Optional[EventMetadata] = None
    
    # Sequence number (assigned by ledger)
    sequence_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage"""
        return {
            "eventId": self.event_id,
            "eventType": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "aggregateType": self.aggregate_type.value if isinstance(self.aggregate_type, AggregateType) else self.aggregate_type,
            "aggregateId": self.aggregate_id,
            "payload": self.payload,
            "sourceModule": self.source_module,
            "createdAt": self.created_at,
            "version": self.version,
            "sequenceNumber": self.sequence_number,
            "metadata": self.metadata.to_dict() if self.metadata else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEvent":
        """Create from dictionary"""
        metadata = None
        if data.get("metadata"):
            m = data["metadata"]
            metadata = EventMetadata(
                correlation_id=m.get("correlationId", ""),
                causation_id=m.get("causationId", ""),
                user_id=m.get("userId", ""),
                ip_address=m.get("ipAddress", ""),
                session_id=m.get("sessionId", ""),
                tags=m.get("tags", [])
            )
        
        return cls(
            event_id=data.get("eventId", data.get("event_id", "")),
            event_type=data.get("eventType", data.get("event_type", "SYSTEM_STARTED")),
            aggregate_type=data.get("aggregateType", data.get("aggregate_type", "SYSTEM")),
            aggregate_id=data.get("aggregateId", data.get("aggregate_id", "")),
            payload=data.get("payload", {}),
            source_module=data.get("sourceModule", data.get("source_module", "system")),
            created_at=data.get("createdAt", data.get("created_at", 0)),
            version=data.get("version", 1),
            sequence_number=data.get("sequenceNumber", data.get("sequence_number", 0)),
            metadata=metadata
        )


@dataclass
class EventQuery:
    """Query parameters for event search"""
    aggregate_type: Optional[str] = None
    aggregate_id: Optional[str] = None
    event_type: Optional[str] = None
    source_module: Optional[str] = None
    from_timestamp: Optional[int] = None
    to_timestamp: Optional[int] = None
    from_sequence: Optional[int] = None
    to_sequence: Optional[int] = None
    correlation_id: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0
    order: str = "desc"  # "asc" or "desc"


@dataclass
class EventStream:
    """Result of event query"""
    events: List[LedgerEvent] = field(default_factory=list)
    total_count: int = 0
    has_more: bool = False
    next_sequence: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "totalCount": self.total_count,
            "hasMore": self.has_more,
            "nextSequence": self.next_sequence
        }


@dataclass
class LedgerStats:
    """Statistics about the event ledger"""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_aggregate: Dict[str, int] = field(default_factory=dict)
    events_by_module: Dict[str, int] = field(default_factory=dict)
    oldest_event_at: int = 0
    newest_event_at: int = 0
    last_sequence: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalEvents": self.total_events,
            "eventsByType": self.events_by_type,
            "eventsByAggregate": self.events_by_aggregate,
            "eventsByModule": self.events_by_module,
            "oldestEventAt": self.oldest_event_at,
            "newestEventAt": self.newest_event_at,
            "lastSequence": self.last_sequence
        }
