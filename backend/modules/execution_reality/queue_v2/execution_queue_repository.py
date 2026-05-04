"""
Execution Queue Repository (P1.3)
==================================

Mongo-backed repository для `execution_jobs` коллекции.

Atomic Lease Mechanics:
- lease_next(): atomic find_and_modify с выставлением leaseOwner/leaseExpiresAt/leaseToken
- Все state transitions проверяют leaseToken (защита от race conditions)

Статусы FSM:
- queued → leased → in_flight → acked
- queued → leased → retry_wait (backoff) → queued
- queued → leased → failed_terminal → dead_letter
"""

import logging
import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from .execution_job_models import (
    ExecutionJob,
    ExecutionJobStatus,
    get_priority_for_action
)
from .execution_job_fsm import validate_transition

logger = logging.getLogger(__name__)


class ExecutionQueueRepository:
    """
    Execution Queue Repository (P1.3 domain-specific).
    
    Features:
    - Atomic lease with leaseToken verification
    - Priority-based ordering (execution-specific scale)
    - FSM-driven status transitions
    - Heartbeat zombie job recovery
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        lease_duration_seconds: int = 30,
        worker_id: Optional[str] = None,
        audit_logger=None  # ExecutionQueueAuditLogger (optional for P1.3.0)
    ):
        """
        Args:
            db: MongoDB database
            lease_duration_seconds: Lease timeout (default 30s)
            worker_id: Unique worker identifier
            audit_logger: ExecutionQueueAuditLogger instance (Checkpoint 5)
        """
        self.collection = db["execution_jobs"]
        self.lease_duration = timedelta(seconds=lease_duration_seconds)
        self.worker_id = worker_id or f"exec-worker-{uuid.uuid4().hex[:8]}"
        self.audit_logger = audit_logger  # Checkpoint 5: audit events
        
        logger.info(
            f"✅ ExecutionQueueRepository initialized "
            f"(worker_id={self.worker_id}, lease={lease_duration_seconds}s, "
            f"audit={'enabled' if audit_logger else 'disabled'})"
        )
    
    async def ensure_indexes(self):
        """Create required indexes for efficient queries."""
        # Unique jobId
        await self.collection.create_index("jobId", unique=True)
        
        # Checkpoint 4: Idempotency Key (unique index, NOT sparse)
        # Генерируем unique idempotencyKey для каждого job (не null)
        await self.collection.create_index(
            "idempotencyKey",
            unique=True
        )
        
        # Status queries
        await self.collection.create_index("status")
        
        # Lease expiry recovery (zombie jobs)
        await self.collection.create_index("leaseExpiresAt")
        
        # Retry scheduling
        await self.collection.create_index("nextRetryAt")
        
        # Trace ID lookup (P0.7 causal graph)
        await self.collection.create_index("traceId")
        
        # Compound index for lease_next (priority-based dequeue)
        # queued jobs first, sorted by priority (lower = higher), then createdAt
        await self.collection.create_index([
            ("status", ASCENDING),
            ("priority", ASCENDING),
            ("createdAt", ASCENDING),
            ("_id", ASCENDING)  # Deterministic tie-breaker
        ])
        
        logger.info("✅ Execution queue indexes created (P1.3 + Checkpoint 4 idempotency)")
    
    async def enqueue(
        self,
        symbol: str,
        exchange: str,
        action: str,
        payload: dict,
        trace_id: Optional[str] = None,
        job_id: Optional[str] = None,
        priority: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        confidence: float = 0.5
    ) -> dict:
        """
        Enqueue new execution job.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            action: Decision action (GO_FULL, WAIT_RETEST, etc.)
            payload: Execution intent payload
            trace_id: P0.7 causal graph trace ID
            job_id: Explicit job ID (generated if not provided)
            priority: Explicit priority (derived from action/confidence if not provided)
            idempotency_key: Unique key for idempotency (P1.4)
            confidence: Decision confidence (for priority calculation)
        
        Returns:
            {"accepted": bool, "jobId": str, "reason": str (if rejected)}
        """
        # Generate jobId if not provided
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        # Checkpoint 4: Generate idempotencyKey if not provided
        # ВСЕГДА генерируем unique key (не null)
        if idempotency_key is None:
            idempotency_key = f"exec-{job_id}"  # Default: use jobId
        
        # Determine priority
        if priority is None:
            priority = get_priority_for_action(action, confidence)
        
        # Create job document
        now = datetime.now(timezone.utc)
        job = ExecutionJob(
            jobId=job_id,
            traceId=trace_id,
            symbol=symbol,
            exchange=exchange,
            priority=priority,
            status="queued",
            payload=payload,
            idempotencyKey=idempotency_key,  # Always non-null
            createdAt=now,
            updatedAt=now
        )
        
        # Insert into Mongo (idempotency via unique jobId)
        try:
            await self.collection.insert_one(job.dict())
            
            logger.info(
                f"✅ [P1.3] Execution job enqueued: jobId={job_id}, "
                f"symbol={symbol}, action={action}, priority={priority}, "
                f"trace_id={trace_id}"
            )
            
            # Checkpoint 5: Audit event
            if self.audit_logger:
                await self.audit_logger.log_enqueued(
                    job_id=job_id,
                    trace_id=trace_id,
                    symbol=symbol,
                    priority=priority,
                    action=action
                )
            
            return {
                "accepted": True,
                "jobId": job_id,
                "traceId": trace_id,
                "priority": priority
            }
        
        except Exception as e:
            # Checkpoint 4: Duplicate key handling (jobId OR idempotencyKey)
            if "duplicate key" in str(e).lower():
                # Определяем, что именно задублировано
                if "jobId" in str(e):
                    logger.warning(
                        f"⚠️ [P1.3 Idempotency] Duplicate jobId rejected: {job_id}"
                    )
                    return {
                        "accepted": False,
                        "jobId": job_id,
                        "reason": f"Duplicate jobId: {job_id}"
                    }
                elif "idempotencyKey" in str(e):
                    logger.warning(
                        f"⚠️ [P1.3 Idempotency] Duplicate idempotencyKey rejected: {idempotency_key}"
                    )
                    return {
                        "accepted": False,
                        "jobId": job_id,
                        "reason": f"Duplicate idempotencyKey: {idempotency_key} (job already enqueued)"
                    }
                else:
                    logger.warning(
                        f"⚠️ [P1.3 Idempotency] Duplicate key (unknown field): {job_id}"
                    )
                    return {
                        "accepted": False,
                        "jobId": job_id,
                        "reason": "Duplicate key error"
                    }
            
            # Other errors
            logger.error(f"❌ [P1.3] Enqueue error: {e}", exc_info=True)
            return {
                "accepted": False,
                "jobId": job_id,
                "reason": str(e)
            }
    
    async def lease_next(self) -> Optional[ExecutionJob]:
        """
        Atomically lease next job with highest priority.
        
        FSM: queued → leased
        
        Picks up:
        - Jobs with status=queued (ready for processing)
        - Jobs with status=queued AND nextRetryAt <= now (retry ready)
        - Jobs with status=leased AND leaseExpiresAt < now (zombie recovery)
        
        Checkpoint 3: Zombie Criteria
        - Reclaim ТОЛЬКО leased jobs (lease expired, worker crashed before submit)
        - in_flight jobs НЕ reclaim-ятся (требуют reconcile с exchange в P1.4)
        - dead_letter и acked jobs финальные (никогда не reclaim-ятся)
        
        Returns:
            ExecutionJob or None if queue empty
        """
        now = datetime.now(timezone.utc)
        lease_expires_at = now + self.lease_duration
        lease_token = str(uuid.uuid4())  # Unique lease token for verification
        
        # Atomic find_one_and_update
        result = await self.collection.find_one_and_update(
            {
                "$or": [
                    # Queued jobs ready for processing
                    {
                        "status": "queued",
                        "$or": [
                            {"nextRetryAt": None},
                            {"nextRetryAt": {"$lte": now}}
                        ]
                    },
                    # Zombie jobs (lease expired)
                    {
                        "status": "leased",
                        "leaseExpiresAt": {"$lt": now}
                    }
                ]
            },
            {
                "$set": {
                    "status": "leased",
                    "leaseOwner": self.worker_id,
                    "leaseExpiresAt": lease_expires_at,
                    "leaseToken": lease_token,
                    "updatedAt": now,
                    "nextRetryAt": None  # Clear retry timestamp
                }
            },
            sort=[
                ("priority", ASCENDING),   # Lower priority number = higher priority
                ("createdAt", ASCENDING),  # FIFO within same priority
                ("_id", ASCENDING)         # Deterministic tie-breaker
            ],
            return_document=True
        )
        
        if result is None:
            return None
        
        job = ExecutionJob(**result)
        
        logger.info(
            f"🔄 [P1.3] Job leased: jobId={job.jobId}, symbol={job.symbol}, "
            f"priority={job.priority}, attempt={job.attemptCount}, "
            f"worker={self.worker_id}, leaseToken={lease_token[:8]}..."
        )
        
        # Checkpoint 5: Audit event
        if self.audit_logger:
            await self.audit_logger.log_leased(
                job_id=job.jobId,
                trace_id=job.traceId,
                worker_id=self.worker_id,
                lease_token=lease_token,
                attempt=job.attemptCount
            )
        
        return job
    
    async def mark_in_flight(self, job_id: str, lease_token: str) -> bool:
        """
        Mark job as in_flight (submit sent to exchange, waiting ACK/REJECT).
        
        FSM: leased → in_flight
        
        Args:
            job_id: Job identifier
            lease_token: Lease token for verification
        
        Returns:
            True if transition successful, False otherwise
        """
        # Checkpoint 1: FSM validation (pre-check)
        # Get current job to validate transition
        job_doc = await self.collection.find_one({"jobId": job_id})
        if not job_doc:
            logger.error(f"❌ [P1.3 FSM] Job not found: jobId={job_id}")
            return False
        
        current_status = job_doc.get("status")
        
        # Validate FSM transition
        try:
            validate_transition(current_status, "in_flight")
        except ValueError as e:
            logger.error(
                f"❌ [P1.3 FSM] Invalid transition blocked: {e}, jobId={job_id}"
            )
            return False
        
        now = datetime.now(timezone.utc)
        
        # Checkpoint 2: Increment attemptCount при реальной попытке submit
        # attemptCount увеличивается ПРИ ВХОДЕ в in_flight, а не при lease
        current_attempt = job_doc.get("attemptCount", 0)
        new_attempt = current_attempt + 1
        
        result = await self.collection.update_one(
            {
                "jobId": job_id,
                "leaseToken": lease_token,  # CRITICAL: verify lease ownership
                "status": "leased"  # FSM: only from leased
            },
            {
                "$set": {
                    "status": "in_flight",
                    "attemptCount": new_attempt,  # Increment on real submit attempt
                    "updatedAt": now
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(
                f"✅ [P1.3] Job → in_flight: jobId={job_id}, "
                f"attempt={new_attempt}"
            )
            return True
        else:
            logger.warning(
                f"⚠️ [P1.3] mark_in_flight failed: jobId={job_id} "
                f"(lease token mismatch or wrong status)"
            )
            return False
    
    async def mark_acked(self, job_id: str, lease_token: str) -> bool:
        """
        Mark job as acked (exchange acknowledged, final success state).
        
        FSM: in_flight → acked
        
        Args:
            job_id: Job identifier
            lease_token: Lease token for verification
        
        Returns:
            True if transition successful, False otherwise
        """
        # Checkpoint 1: FSM validation
        job_doc = await self.collection.find_one({"jobId": job_id})
        if not job_doc:
            logger.error(f"❌ [P1.3 FSM] Job not found: jobId={job_id}")
            return False
        
        current_status = job_doc.get("status")
        
        try:
            validate_transition(current_status, "acked")
        except ValueError as e:
            logger.error(f"❌ [P1.3 FSM] Invalid transition blocked: {e}, jobId={job_id}")
            return False
        
        now = datetime.now(timezone.utc)
        
        result = await self.collection.update_one(
            {
                "jobId": job_id,
                "leaseToken": lease_token,
                "status": "in_flight"  # FSM: only from in_flight
            },
            {
                "$set": {
                    "status": "acked",
                    "updatedAt": now,
                    # Clear lease
                    "leaseOwner": None,
                    "leaseExpiresAt": None,
                    "leaseToken": None
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ [P1.3] Job → acked: jobId={job_id}")
            
            # Checkpoint 5: Audit event
            if self.audit_logger:
                await self.audit_logger.log_acked(
                    job_id=job_id,
                    trace_id=job_doc.get("traceId")
                )
            
            return True
        else:
            logger.warning(
                f"⚠️ [P1.3] mark_acked failed: jobId={job_id} "
                f"(lease token mismatch or wrong status)"
            )
            return False
    
    async def mark_retry_wait(
        self,
        job_id: str,
        lease_token: str,
        error: str,
        backoff_seconds: float
    ) -> bool:
        """
        Mark job for retry with exponential backoff.
        
        FSM: leased/in_flight → retry_wait (if attempts < max) OR failed_terminal
        
        Args:
            job_id: Job identifier
            lease_token: Lease token for verification
            error: Error message
            backoff_seconds: Delay before next retry
        
        Returns:
            True if transition successful, False otherwise
        """
        now = datetime.now(timezone.utc)
        
        # Get current job to check attempts
        job_doc = await self.collection.find_one({"jobId": job_id})
        if not job_doc:
            logger.error(f"❌ [P1.3] Job not found: jobId={job_id}")
            return False
        
        job = ExecutionJob(**job_doc)
        
        # Checkpoint 2: НЕ инкрементируем attemptCount здесь
        # Инкремент уже произошёл в mark_in_flight при реальной попытке submit
        current_attempt = job.attemptCount
        
        # Determine final status
        if current_attempt < job.maxAttempts:
            # Return to retry_wait with scheduled retry
            new_status = "retry_wait"
            next_retry_at = now + timedelta(seconds=backoff_seconds)
            
            logger.warning(
                f"🔄 [P1.3] Job → retry_wait: jobId={job_id}, "
                f"attempt={current_attempt}/{job.maxAttempts}, "
                f"backoff={backoff_seconds}s, error={error}"
            )
        else:
            # Exhausted retries → failed_terminal
            new_status = "failed_terminal"
            next_retry_at = None
            
            logger.error(
                f"❌ [P1.3] Job → failed_terminal: jobId={job_id}, "
                f"attempt={current_attempt}, error={error}"
            )
        
        # Update job (НЕ меняем attemptCount — он уже корректный)
        result = await self.collection.update_one(
            {
                "jobId": job_id,
                "leaseToken": lease_token
            },
            {
                "$set": {
                    "status": new_status,
                    "lastError": error,
                    "nextRetryAt": next_retry_at,
                    "updatedAt": now,
                    # Clear lease
                    "leaseOwner": None,
                    "leaseExpiresAt": None,
                    "leaseToken": None
                }
            }
        )
        
        return result.modified_count > 0
    
    async def mark_failed_terminal(
        self,
        job_id: str,
        lease_token: str,
        error: str
    ) -> bool:
        """
        Mark job as permanently failed (no retry).
        
        FSM: any → failed_terminal
        
        Args:
            job_id: Job identifier
            lease_token: Lease token for verification
            error: Error message
        
        Returns:
            True if transition successful, False otherwise
        """
        now = datetime.now(timezone.utc)
        
        result = await self.collection.update_one(
            {
                "jobId": job_id,
                "leaseToken": lease_token
            },
            {
                "$set": {
                    "status": "failed_terminal",
                    "lastError": error,
                    "updatedAt": now,
                    # Clear lease
                    "leaseOwner": None,
                    "leaseExpiresAt": None,
                    "leaseToken": None
                }
            }
        )
        
        if result.modified_count > 0:
            logger.error(
                f"❌ [P1.3] Job → failed_terminal: jobId={job_id}, error={error}"
            )
            return True
        else:
            logger.warning(
                f"⚠️ [P1.3] mark_failed_terminal failed: jobId={job_id}"
            )
            return False
    
    async def move_to_dead_letter(
        self,
        job_id: str,
        lease_token: str,
        reason: str
    ) -> bool:
        """
        Move job to dead_letter (final state, requires manual intervention).
        
        FSM: failed_terminal → dead_letter
        
        Args:
            job_id: Job identifier
            lease_token: Lease token for verification (может быть None если уже failed)
            reason: Reason for DLQ move
        
        Returns:
            True if transition successful, False otherwise
        """
        now = datetime.now(timezone.utc)
        
        # Если lease_token is None, не проверяем его (job уже failed_terminal)
        query = {"jobId": job_id}
        if lease_token:
            query["leaseToken"] = lease_token
        
        result = await self.collection.update_one(
            query,
            {
                "$set": {
                    "status": "dead_letter",
                    "lastError": reason,
                    "updatedAt": now,
                    # Clear lease (на всякий случай)
                    "leaseOwner": None,
                    "leaseExpiresAt": None,
                    "leaseToken": None
                }
            }
        )
        
        if result.modified_count > 0:
            logger.error(
                f"❌ [P1.3] Job → dead_letter: jobId={job_id}, reason={reason}"
            )
            return True
        else:
            logger.warning(
                f"⚠️ [P1.3] move_to_dead_letter failed: jobId={job_id}"
            )
            return False
    
    async def get_metrics(self) -> dict:
        """Get queue metrics."""
        # Count by status
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        
        status_counts = {
            doc["_id"]: doc["count"]
            async for doc in self.collection.aggregate(pipeline)
        }
        
        # Count zombie jobs (expired leases)
        now = datetime.now(timezone.utc)
        zombie_count = await self.collection.count_documents({
            "status": "leased",
            "leaseExpiresAt": {"$lt": now}
        })
        
        return {
            "queued": status_counts.get("queued", 0),
            "leased": status_counts.get("leased", 0),
            "in_flight": status_counts.get("in_flight", 0),
            "acked": status_counts.get("acked", 0),
            "retry_wait": status_counts.get("retry_wait", 0),
            "failed_terminal": status_counts.get("failed_terminal", 0),
            "dead_letter": status_counts.get("dead_letter", 0),
            "zombie_jobs": zombie_count
        }
    
    async def get_job(self, job_id: str) -> Optional[ExecutionJob]:
        """Get job by ID."""
        doc = await self.collection.find_one({"jobId": job_id})
        if doc:
            return ExecutionJob(**doc)
        return None
