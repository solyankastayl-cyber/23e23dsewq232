"""
Execution Queue v2 (P1.3)
=========================

Domain-specific execution queue layer (НОВАЯ коллекция, НЕ заменяет infra queue P1.1).

Архитектура:
- execution_jobs (Mongo) → execution-specific FSM + semantics
- ExecutionQueueWorker → lease/process/ack lifecycle
- ExecutionDispatchService → Decision → Job creation

Критическое отличие от P1.1:
- P1.1 = generic infra queue (любые tasks)
- P1.3 = domain execution queue (execution-specific state machine)

Feature Flag: USE_EXECUTION_QUEUE = true/false

Checkpoints (зафиксированы перед P1.3.1):
- ✅ Checkpoint 1: Allowed Transitions (FSM validator)
- ✅ Checkpoint 2: attemptCount semantics (increment on in_flight)
- ✅ Checkpoint 3: Zombie criteria (reclaim только leased)
- ✅ Checkpoint 4: Idempotency key (sparse unique index)
- ✅ Checkpoint 5: Audit event coverage
"""

from .execution_job_models import (
    ExecutionJob,
    ExecutionJobStatus,
    ExecutionJobPriority,
    get_priority_for_action
)
from .execution_queue_repository import ExecutionQueueRepository
from .execution_dispatch_service import ExecutionDispatchService
from .execution_queue_audit import (
    ExecutionQueueAuditLogger,
    get_execution_queue_audit_logger,
    set_execution_queue_audit_logger
)

__all__ = [
    "ExecutionJob",
    "ExecutionJobStatus",
    "ExecutionJobPriority",
    "get_priority_for_action",
    "ExecutionQueueRepository",
    "ExecutionDispatchService",
    "ExecutionQueueAuditLogger",
    "get_execution_queue_audit_logger",
    "set_execution_queue_audit_logger",
]
