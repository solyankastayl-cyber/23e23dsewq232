"""
Persistent Queue Repository (P1.1B)
====================================

Mongo-backed durable queue with atomic dequeue and lease-based locking.

Architecture:
- Mongo = source of truth
- Atomic find_one_and_update for dequeue
- Lease timeout for worker crash recovery
- No explicit boot restore needed (dequeue picks up expired leases)
"""

import logging
import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from .persistent_queue_models import (
    PersistentQueueTask,
    TaskType,
    TaskStatus,
    get_task_priority
)

logger = logging.getLogger(__name__)


class PersistentQueueRepository:
    """
    Durable queue backed by MongoDB.
    
    Features:
    - Atomic dequeue with lease-based locking
    - Automatic recovery of expired leases
    - Priority-based ordering
    - Idempotency via unique task_id
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        lease_duration_seconds: int = 30,
        worker_id: Optional[str] = None
    ):
        """
        Args:
            db: MongoDB database
            lease_duration_seconds: How long worker holds exclusive lock
            worker_id: Unique worker identifier (generated if not provided)
        """
        self.collection = db["order_queue"]
        self.lease_duration = timedelta(seconds=lease_duration_seconds)
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        
        logger.info(
            f"✅ PersistentQueueRepository initialized "
            f"(worker_id={self.worker_id}, lease={lease_duration_seconds}s)"
        )
    
    async def ensure_indexes(self):
        """Create required indexes for efficient queries."""
        # Unique task_id
        await self.collection.create_index("task_id", unique=True)
        
        # Status queries
        await self.collection.create_index("status")
        
        # Compound index for dequeue (status + priority + created_at + _id)
        # P1.1C: Added _id for deterministic ordering
        await self.collection.create_index([
            ("status", ASCENDING),
            ("priority", ASCENDING),
            ("created_at", ASCENDING),
            ("_id", ASCENDING)  # P1.1C: Deterministic tie-breaker
        ])
        
        # Lease expiry recovery
        await self.collection.create_index("lease_expires_at")
        
        # P1.1C: Retry scheduling
        await self.collection.create_index("next_retry_at")
        
        # Trace ID lookup
        await self.collection.create_index("trace_id")
        
        logger.info("✅ Persistent queue indexes created (P1.1C)")
    
    async def enqueue(
        self,
        task_type: TaskType,
        payload: dict,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None,
        priority: Optional[int] = None
    ) -> dict:
        """
        Enqueue a new task.
        
        Args:
            task_type: Type of task
            payload: Task-specific data
            trace_id: Causal graph trace ID
            task_id: Explicit task ID (generated if not provided)
            priority: Explicit priority (derived from type if not provided)
        
        Returns:
            {"accepted": bool, "task_id": str, "reason": str (if rejected)}
        """
        # Generate task_id if not provided
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        # Determine priority
        if priority is None:
            priority = get_task_priority(task_type)
        
        # Create task document
        now = datetime.now(timezone.utc)
        task = PersistentQueueTask(
            task_id=task_id,
            trace_id=trace_id,
            type=task_type,
            status="PENDING",
            priority=priority,
            payload=payload,
            attempt=0,
            created_at=now,
            updated_at=now
        )
        
        # Insert into Mongo (idempotency via unique task_id)
        try:
            await self.collection.insert_one(task.dict())
            
            logger.info(
                f"✅ Task enqueued: task_id={task_id}, type={task_type}, "
                f"priority={priority}, trace_id={trace_id}"
            )
            
            return {
                "accepted": True,
                "task_id": task_id
            }
        
        except Exception as e:
            # Duplicate task_id
            if "duplicate key" in str(e).lower():
                logger.warning(
                    f"⚠️ Duplicate task rejected: task_id={task_id}"
                )
                return {
                    "accepted": False,
                    "task_id": task_id,
                    "reason": f"Duplicate task_id: {task_id}"
                }
            
            # Other errors
            logger.error(f"❌ Enqueue error: {e}", exc_info=True)
            return {
                "accepted": False,
                "task_id": task_id,
                "reason": str(e)
            }
    
    async def dequeue(self) -> Optional[PersistentQueueTask]:
        """
        Atomically dequeue next task with lease-based locking.
        
        P1.1C Updates:
        - Respects next_retry_at (only dequeue if retry time has passed)
        - Priority ordering with _id tie-breaker (deterministic)
        
        Picks up:
        - PENDING tasks ready for processing (by priority, created_at, _id)
        - PENDING tasks with expired retry delay (next_retry_at <= now)
        - PROCESSING tasks with expired leases (worker crash recovery)
        
        Returns:
            PersistentQueueTask or None if queue empty
        """
        now = datetime.now(timezone.utc)
        lease_expires_at = now + self.lease_duration
        
        # Atomic find_one_and_update
        # Filter: 
        #   (PENDING AND (no retry scheduled OR retry time passed))
        #   OR (PROCESSING AND lease expired)
        result = await self.collection.find_one_and_update(
            {
                "$or": [
                    {
                        "status": "PENDING",
                        "$or": [
                            {"next_retry_at": None},
                            {"next_retry_at": {"$lte": now}}
                        ]
                    },
                    {
                        "status": "PROCESSING",
                        "lease_expires_at": {"$lt": now}
                    }
                ]
            },
            {
                "$set": {
                    "status": "PROCESSING",
                    "lock_owner": self.worker_id,
                    "locked_at": now,
                    "lease_expires_at": lease_expires_at,
                    "updated_at": now,
                    "next_retry_at": None  # Clear retry timestamp
                }
            },
            sort=[
                ("priority", ASCENDING),
                ("created_at", ASCENDING),
                ("_id", ASCENDING)  # P1.1C: Deterministic tie-breaker
            ],
            return_document=True
        )
        
        if result is None:
            return None
        
        task = PersistentQueueTask(**result)
        
        logger.info(
            f"🔄 Task dequeued: task_id={task.task_id}, type={task.type}, "
            f"priority={task.priority}, attempt={task.attempt}, worker={self.worker_id}"
        )
        
        return task
    
    async def mark_done(self, task_id: str) -> None:
        """Mark task as successfully completed."""
        now = datetime.now(timezone.utc)
        
        result = await self.collection.update_one(
            {
                "task_id": task_id,
                "lock_owner": self.worker_id  # Only owner can mark done
            },
            {
                "$set": {
                    "status": "DONE",
                    "updated_at": now,
                    "locked_at": None,
                    "lock_owner": None,
                    "lease_expires_at": None
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Task completed: task_id={task_id}")
        else:
            logger.warning(
                f"⚠️ mark_done failed: task_id={task_id} "
                f"(not owned by {self.worker_id})"
            )
    
    async def mark_failed(
        self,
        task_id: str,
        error: str,
        retry: bool = False,
        backoff_seconds: float = 0.0
    ) -> None:
        """
        Mark task as failed with optional retry.
        
        P1.1C Updates:
        - Exponential backoff via next_retry_at
        - Returns to PENDING with scheduled retry time
        
        Args:
            task_id: Task identifier
            error: Error message
            retry: If True, return to PENDING with backoff
            backoff_seconds: Delay before next retry (exponential)
        """
        now = datetime.now(timezone.utc)
        
        # Get current task to check attempts
        task_doc = await self.collection.find_one({"task_id": task_id})
        if not task_doc:
            logger.error(f"❌ Task not found: task_id={task_id}")
            return
        
        task = PersistentQueueTask(**task_doc)
        
        # Increment attempt
        new_attempt = task.attempt + 1
        
        # Determine final status and retry scheduling
        if retry and new_attempt < task.max_attempts:
            # Return to PENDING with retry delay
            new_status = "PENDING"
            next_retry_at = now + timedelta(seconds=backoff_seconds)
            
            logger.warning(
                f"🔄 Task retry scheduled: task_id={task_id}, "
                f"attempt={new_attempt}/{task.max_attempts}, "
                f"backoff={backoff_seconds}s, "
                f"next_retry_at={next_retry_at}, "
                f"error={error}"
            )
        else:
            # Exhausted retries or non-retryable
            new_status = "FAILED"
            next_retry_at = None
            
            logger.error(
                f"❌ Task failed permanently: task_id={task_id}, "
                f"attempt={new_attempt}, error={error}"
            )
        
        # Update task
        await self.collection.update_one(
            {
                "task_id": task_id,
                "lock_owner": self.worker_id
            },
            {
                "$set": {
                    "status": new_status,
                    "attempt": new_attempt,
                    "last_error": error,
                    "updated_at": now,
                    "locked_at": None,
                    "lock_owner": None,
                    "lease_expires_at": None,
                    "next_retry_at": next_retry_at  # P1.1C: Exponential backoff
                }
            }
        )
    
    async def get_metrics(self) -> dict:
        """Get queue metrics."""
        # Count by status
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        
        status_counts = {doc["_id"]: doc["count"] async for doc in self.collection.aggregate(pipeline)}
        
        # Count expired leases (zombie tasks)
        now = datetime.now(timezone.utc)
        expired_leases = await self.collection.count_documents({
            "status": "PROCESSING",
            "lease_expires_at": {"$lt": now}
        })
        
        return {
            "pending": status_counts.get("PENDING", 0),
            "processing": status_counts.get("PROCESSING", 0),
            "done": status_counts.get("DONE", 0),
            "failed": status_counts.get("FAILED", 0),
            "expired_leases": expired_leases
        }
    
    async def get_task(self, task_id: str) -> Optional[PersistentQueueTask]:
        """Get task by ID."""
        doc = await self.collection.find_one({"task_id": task_id})
        if doc:
            return PersistentQueueTask(**doc)
        return None
