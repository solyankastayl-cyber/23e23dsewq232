"""
Queue Models (P1.1)
==================

Unified queue item schema and priority definitions.
"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid


# Action types with semantic meaning
ActionType = Literal[
    "OPEN_ORDER",       # New position entry
    "CLOSE_POSITION",   # Position close
    "REDUCE_POSITION",  # Partial position close
    "CANCEL_ORDER",     # Cancel pending order
    "UPDATE_ORDER",     # Modify existing order
]

# Queue item statuses
QueueStatus = Literal[
    "QUEUED",           # Waiting in queue
    "PROCESSING",       # Being processed by worker
    "DONE",             # Successfully completed
    "RETRYING",         # Failed, scheduled for retry
    "FAILED_DLQ",       # Moved to Dead Letter Queue
]

# DLQ failure classifications
DLQClassification = Literal[
    "retry_exhausted",  # Max retries exceeded
    "non_retryable",    # Deterministic reject (business rule)
    "malformed",        # Invalid payload
    "unknown_error",    # Unexpected error
]


class QueueItem(BaseModel):
    """
    Canonical queue item schema.
    
    This schema is designed to be Redis-compatible for future migration,
    but currently used with in-memory priority queue.
    """
    queue_item_id: str
    trace_id: Optional[str]  # P0.7.1: Causal graph trace
    client_order_id: str
    priority: int  # 0 = highest, 2 = lowest
    action_type: ActionType
    payload: Dict[str, Any]
    attempt: int = 0
    max_attempts: int = 3
    next_retry_at: Optional[datetime] = None
    status: QueueStatus = "QUEUED"
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        action_type: ActionType,
        payload: Dict[str, Any],
        client_order_id: str,
        trace_id: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> "QueueItem":
        """Create a new queue item with auto-generated ID and priority."""
        if priority is None:
            priority = get_action_priority(action_type)
        
        return cls(
            queue_item_id=str(uuid.uuid4()),
            trace_id=trace_id,
            client_order_id=client_order_id,
            priority=priority,
            action_type=action_type,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )


class DLQItem(BaseModel):
    """Dead Letter Queue item (persisted in Mongo)."""
    queue_item_id: str
    trace_id: Optional[str]
    client_order_id: str
    strategy_id: Optional[str]
    action_type: ActionType
    payload: Dict[str, Any]
    attempts: int
    final_error: str
    failed_at: datetime
    classification: DLQClassification


# Priority mapping (lower number = higher priority)
ACTION_PRIORITY_MAP: Dict[ActionType, int] = {
    # P0: Critical (CLOSE, REDUCE, CANCEL)
    "CLOSE_POSITION": 0,
    "REDUCE_POSITION": 0,
    "CANCEL_ORDER": 0,
    
    # P1: Protective orders / modifications
    "UPDATE_ORDER": 1,
    
    # P2: New entries (lowest priority)
    "OPEN_ORDER": 2,
}


def get_action_priority(action_type: ActionType) -> int:
    """Get priority level for action type."""
    return ACTION_PRIORITY_MAP.get(action_type, 2)  # default to lowest


class QueueMetrics(BaseModel):
    """Queue observability metrics."""
    queue_depth: int
    processing_count: int
    retry_count: int
    dlq_count: int
    avg_wait_ms: float
    avg_processing_ms: float
    workers_active: int
    workers_total: int
    last_error: Optional[str] = None
    timestamp: datetime
