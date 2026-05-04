"""
Execution Queue Audit Logger (P1.3 Checkpoint 5)
=================================================

Audit events для execution queue lifecycle.

Events:
- EXECUTION_JOB_ENQUEUED
- EXECUTION_JOB_LEASED
- EXECUTION_JOB_IN_FLIGHT
- EXECUTION_JOB_ACKED
- EXECUTION_JOB_RETRY_SCHEDULED
- EXECUTION_JOB_FAILED_TERMINAL
- EXECUTION_JOB_DEAD_LETTER
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ExecutionQueueAuditLogger:
    """
    Audit logger для execution queue events.
    
    Записывает события в коллекцию `execution_queue_audit`.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Args:
            db: MongoDB database
        """
        self.collection = db["execution_queue_audit"]
        logger.info("✅ ExecutionQueueAuditLogger initialized (P1.3 Checkpoint 5)")
    
    async def log_event(
        self,
        event_type: str,
        job_id: str,
        trace_id: Optional[str],
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log execution queue event.
        
        Args:
            event_type: Event type (ENQUEUED, LEASED, etc.)
            job_id: Job identifier
            trace_id: Causal trace ID (P0.7)
            status: Current job status
            metadata: Additional event metadata
        """
        event = {
            "eventType": event_type,
            "jobId": job_id,
            "traceId": trace_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {}
        }
        
        try:
            await self.collection.insert_one(event)
            logger.debug(
                f"[P1.3 Audit] {event_type}: jobId={job_id}, "
                f"status={status}, trace_id={trace_id}"
            )
        except Exception as e:
            logger.error(
                f"[P1.3 Audit] Failed to log event: {e}", exc_info=True
            )
    
    async def log_enqueued(
        self,
        job_id: str,
        trace_id: Optional[str],
        symbol: str,
        priority: int,
        action: str
    ):
        """Log EXECUTION_JOB_ENQUEUED event."""
        await self.log_event(
            event_type="EXECUTION_JOB_ENQUEUED",
            job_id=job_id,
            trace_id=trace_id,
            status="queued",
            metadata={
                "symbol": symbol,
                "priority": priority,
                "action": action
            }
        )
    
    async def log_leased(
        self,
        job_id: str,
        trace_id: Optional[str],
        worker_id: str,
        lease_token: str,
        attempt: int
    ):
        """Log EXECUTION_JOB_LEASED event."""
        await self.log_event(
            event_type="EXECUTION_JOB_LEASED",
            job_id=job_id,
            trace_id=trace_id,
            status="leased",
            metadata={
                "workerId": worker_id,
                "leaseToken": lease_token,
                "attempt": attempt
            }
        )
    
    async def log_in_flight(
        self,
        job_id: str,
        trace_id: Optional[str],
        attempt: int
    ):
        """Log EXECUTION_JOB_IN_FLIGHT event."""
        await self.log_event(
            event_type="EXECUTION_JOB_IN_FLIGHT",
            job_id=job_id,
            trace_id=trace_id,
            status="in_flight",
            metadata={
                "attempt": attempt
            }
        )
    
    async def log_acked(
        self,
        job_id: str,
        trace_id: Optional[str]
    ):
        """Log EXECUTION_JOB_ACKED event."""
        await self.log_event(
            event_type="EXECUTION_JOB_ACKED",
            job_id=job_id,
            trace_id=trace_id,
            status="acked",
            metadata={}
        )
    
    async def log_retry_scheduled(
        self,
        job_id: str,
        trace_id: Optional[str],
        attempt: int,
        max_attempts: int,
        backoff_seconds: float,
        error: str
    ):
        """Log EXECUTION_JOB_RETRY_SCHEDULED event."""
        await self.log_event(
            event_type="EXECUTION_JOB_RETRY_SCHEDULED",
            job_id=job_id,
            trace_id=trace_id,
            status="retry_wait",
            metadata={
                "attempt": attempt,
                "maxAttempts": max_attempts,
                "backoffSeconds": backoff_seconds,
                "error": error
            }
        )
    
    async def log_failed_terminal(
        self,
        job_id: str,
        trace_id: Optional[str],
        attempt: int,
        error: str
    ):
        """Log EXECUTION_JOB_FAILED_TERMINAL event."""
        await self.log_event(
            event_type="EXECUTION_JOB_FAILED_TERMINAL",
            job_id=job_id,
            trace_id=trace_id,
            status="failed_terminal",
            metadata={
                "attempt": attempt,
                "error": error
            }
        )
    
    async def log_dead_letter(
        self,
        job_id: str,
        trace_id: Optional[str],
        reason: str
    ):
        """Log EXECUTION_JOB_DEAD_LETTER event."""
        await self.log_event(
            event_type="EXECUTION_JOB_DEAD_LETTER",
            job_id=job_id,
            trace_id=trace_id,
            status="dead_letter",
            metadata={
                "reason": reason
            }
        )


# Global singleton (опционально)
_audit_logger: Optional[ExecutionQueueAuditLogger] = None


def get_execution_queue_audit_logger() -> Optional[ExecutionQueueAuditLogger]:
    """Get singleton ExecutionQueueAuditLogger."""
    global _audit_logger
    return _audit_logger


def set_execution_queue_audit_logger(logger_instance: ExecutionQueueAuditLogger):
    """Set singleton ExecutionQueueAuditLogger."""
    global _audit_logger
    _audit_logger = logger_instance
    logger.info("✅ ExecutionQueueAuditLogger singleton set")
