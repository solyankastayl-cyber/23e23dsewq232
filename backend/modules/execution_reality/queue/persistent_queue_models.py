"""
Persistent Queue Models (P1.1B)
================================

Mongo-backed durable queue with lease-based locking.
"""

from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel


# Task types
TaskType = Literal[
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "CLOSE_POSITION",
    "REDUCE_POSITION",
    "UPDATE_ORDER",
]

# Task status lifecycle
TaskStatus = Literal[
    "PENDING",      # Ready to be picked up
    "PROCESSING",   # Locked by worker
    "DONE",         # Successfully completed
    "FAILED",       # Failed after max retries
]


class PersistentQueueTask(BaseModel):
    """
    Persistent queue task document (Mongo-backed).
    
    Lifecycle:
    - PENDING → PROCESSING → DONE
    - PENDING → PROCESSING → FAILED
    - PROCESSING (lease expired) → PENDING (auto-recovery)
    
    P1.1C additions:
    - next_retry_at: scheduled retry timestamp (exponential backoff)
    """
    task_id: str                        # Unique task identifier
    trace_id: Optional[str]             # Causal graph trace ID
    type: TaskType                      # Task type
    status: TaskStatus                  # Current status
    priority: int                       # Lower = higher priority (0-999)
    payload: dict                       # Task-specific data
    attempt: int = 0                    # Current attempt number
    max_attempts: int = 3               # Max retry attempts
    created_at: datetime                # Task creation timestamp
    updated_at: datetime                # Last update timestamp
    locked_at: Optional[datetime] = None      # When locked by worker
    lock_owner: Optional[str] = None          # Worker ID that owns lock
    lease_expires_at: Optional[datetime] = None  # Lease expiration time
    last_error: Optional[str] = None    # Last error message
    next_retry_at: Optional[datetime] = None  # P1.1C: Scheduled retry timestamp


# Priority mapping (same as before)
TASK_TYPE_PRIORITY_MAP = {
    # P0: Critical (CLOSE, REDUCE, CANCEL)
    "CLOSE_POSITION": 0,
    "REDUCE_POSITION": 0,
    "CANCEL_ORDER": 0,
    
    # P1: Protective orders / modifications
    "UPDATE_ORDER": 100,
    
    # P2: New entries (lowest priority)
    "SUBMIT_ORDER": 200,
}


def get_task_priority(task_type: TaskType) -> int:
    """Get priority value for task type (lower = higher priority)."""
    return TASK_TYPE_PRIORITY_MAP.get(task_type, 200)
