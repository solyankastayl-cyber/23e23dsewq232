"""
Execution Job Models (P1.3)
============================

Domain-specific execution job schema для `execution_jobs` коллекции.

Статусы (строгий FSM):
- queued → leased → in_flight → acked
- queued → leased → retry_wait → queued (повтор после backoff)
- queued → leased → failed_terminal
- failed_terminal → dead_letter (финал)

Atomic Lease Safety:
- leaseOwner + leaseExpiresAt + leaseToken (uuid)
- Все переходы статусов требуют проверки leaseToken
"""

from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


# Execution Job Status (строгий enum)
ExecutionJobStatus = Literal[
    "queued",           # Готов к lease (новый или после retry_wait)
    "leased",           # Зарезервирован воркером, но ещё не в процессе
    "in_flight",        # Submit отправлен на биржу, ждём ACK/REJECT
    "acked",            # Успешно принят биржей (финальное состояние)
    "retry_wait",       # Ожидает retry (с backoff timestamp)
    "failed_terminal",  # Перманентный фейл (exhausted retries)
    "dead_letter",      # Перемещён в DLQ (финальное состояние)
]


# Execution-Specific Priority Scale (из последней дискуссии)
class ExecutionJobPriority:
    """
    Execution-specific priority scale.
    
    100 = FORCE EXIT / LIQUIDATION PROTECTION
    90  = STOP LOSS
    80  = PRIMARY ENTRY
    70  = TAKE PROFIT
    60  = SCALE IN/OUT
    40  = LOW CONFIDENCE
    20  = EXPERIMENTAL
    """
    LIQUIDATION_PROTECTION = 100
    STOP_LOSS = 90
    PRIMARY_ENTRY = 80
    TAKE_PROFIT = 70
    SCALE_IN_OUT = 60
    LOW_CONFIDENCE = 40
    EXPERIMENTAL = 20


def get_priority_for_action(action: str, confidence: float = 0.5) -> int:
    """
    Determine priority based on action type and confidence.
    
    Args:
        action: Decision action (GO_FULL, GO_AGGRESSIVE, WAIT_RETEST, etc.)
        confidence: Decision confidence (0.0-1.0)
    
    Returns:
        Priority value (lower number = higher priority)
    """
    # STOP_LOSS всегда высший приоритет
    if "STOP" in action.upper() or "EXIT" in action.upper():
        return ExecutionJobPriority.STOP_LOSS
    
    # TAKE_PROFIT
    if "PROFIT" in action.upper() or "TARGET" in action.upper():
        return ExecutionJobPriority.TAKE_PROFIT
    
    # Primary entries (GO_FULL, GO_AGGRESSIVE с высоким confidence)
    if action in ["GO_FULL", "GO_AGGRESSIVE"] and confidence >= 0.7:
        return ExecutionJobPriority.PRIMARY_ENTRY
    
    # Scale in/out (WAIT_RETEST, GO_NORMAL)
    if action in ["WAIT_RETEST", "GO_NORMAL"]:
        return ExecutionJobPriority.SCALE_IN_OUT
    
    # Low confidence
    if confidence < 0.5:
        return ExecutionJobPriority.LOW_CONFIDENCE
    
    # Experimental (WAIT, нет чёткого сигнала)
    if action == "WAIT":
        return ExecutionJobPriority.EXPERIMENTAL
    
    # Default: primary entry
    return ExecutionJobPriority.PRIMARY_ENTRY


class ExecutionJob(BaseModel):
    """
    Execution Job document (Mongo: execution_jobs).
    
    P1.3 Schema (минимум для MVP):
    - jobId, traceId (causal graph)
    - symbol, exchange
    - priority (execution-specific)
    - status (FSM: queued → leased → in_flight → acked)
    - lease mechanics (owner, expires, token)
    - retry mechanics (attempt, max, backoff)
    - idempotencyKey (для P1.4 расширения)
    """
    # Identity
    jobId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    traceId: Optional[str] = None  # P0.7: causal graph linkage
    
    # Execution context
    symbol: str
    exchange: str = "binance"
    
    # Priority & Status
    priority: int = ExecutionJobPriority.PRIMARY_ENTRY
    status: ExecutionJobStatus = "queued"
    
    # Lease Mechanics (atomic safety)
    leaseOwner: Optional[str] = None       # Worker ID holding lease
    leaseExpiresAt: Optional[datetime] = None  # Lease expiration timestamp
    leaseToken: Optional[str] = None       # UUID for lease verification
    
    # Retry Mechanics
    attemptCount: int = 0
    maxAttempts: int = 3
    nextRetryAt: Optional[datetime] = None  # Scheduled retry timestamp (if retry_wait)
    
    # Idempotency (для P1.4)
    idempotencyKey: Optional[str] = None   # client_order_id или другой unique key
    
    # Payload (execution intent)
    payload: dict  # Содержит: action, side, qty, price, stop, target, etc.
    
    # Metadata
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lastError: Optional[str] = None
    
    class Config:
        use_enum_values = True
