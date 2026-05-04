"""
Execution Worker Manager (P1.3.2)
==================================

Lifecycle manager для execution queue workers.

P1.3.2 Phase 1: Single-worker только.
"""

import logging
import uuid
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from .execution_queue_repository import ExecutionQueueRepository
from .execution_worker_heartbeat import ExecutionWorkerHeartbeatWriter
from .execution_submit_simulator import ExecutionSubmitSimulator
from .execution_queue_worker import ExecutionQueueWorker
from .execution_retry_scheduler import ExecutionRetryScheduler
from .execution_worker_config import (
    ExecutionWorkerConfig,
    validate_phase2b_constraints  # P1.3.2B
)

logger = logging.getLogger(__name__)


class ExecutionWorkerManager:
    """
    Execution Worker Manager.
    
    Manages worker lifecycle: start, stop, drain, shutdown.
    
    P1.3.2 Phase 1: single-worker mode только.
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        queue_repo: ExecutionQueueRepository,
        config: ExecutionWorkerConfig,
        audit_logger=None,
        order_manager=None  # Sprint A2.3: для REAL execution
    ):
        """
        Args:
            db: MongoDB database
            queue_repo: ExecutionQueueRepository instance
            config: ExecutionWorkerConfig instance
            audit_logger: ExecutionQueueAuditLogger (optional)
            order_manager: OrderManager instance (required for REAL mode)
        """
        self.db = db
        self.queue_repo = queue_repo
        self.config = config
        self.audit_logger = audit_logger
        self.order_manager = order_manager  # Sprint A2.3
        
        # Validate P1.3.2B constraints
        validate_phase2b_constraints(config)
        
        # Workers
        self.workers: List[ExecutionQueueWorker] = []
        
        # Retry scheduler
        self.retry_scheduler: Optional[ExecutionRetryScheduler] = None
        
        # Submit simulator (DRY-RUN/PAPER с P1.3.2B retry testing)
        # PAPER mode: failure_rate=0 for clean testing
        self.submit_simulator = ExecutionSubmitSimulator(
            simulate_latency_ms=100,
            failure_rate=0.0  # Disabled for PAPER mode testing
        )
        
        logger.info(
            f"✅ ExecutionWorkerManager initialized: "
            f"worker_count={config.worker_count}, dry_run={config.dry_run}, "
            f"order_manager={'provided' if order_manager else 'None'}"
        )
    
    async def start(self):
        """
        Start all workers and retry scheduler.
        
        P1.3.2 Phase 1: single-worker только.
        """
        logger.info(f"🔄 [WorkerManager] Starting {self.config.worker_count} worker(s)...")
        
        # Start retry scheduler
        self.retry_scheduler = ExecutionRetryScheduler(
            db=self.db,
            interval_seconds=10
        )
        await self.retry_scheduler.start()
        
        # Create and start workers
        for i in range(self.config.worker_count):
            worker_id = f"exec-worker-{uuid.uuid4().hex[:8]}"
            
            # Create heartbeat writer
            heartbeat = ExecutionWorkerHeartbeatWriter(
                db=self.db,
                worker_id=worker_id,
                interval_seconds=self.config.heartbeat_interval_seconds
            )
            
            await heartbeat.ensure_indexes()
            
            # Create worker
            worker = ExecutionQueueWorker(
                queue_repo=self.queue_repo,
                heartbeat_writer=heartbeat,
                submit_simulator=self.submit_simulator,
                config=self.config,
                audit_logger=self.audit_logger,
                order_manager=self.order_manager  # Sprint A2.3: REAL mode support
            )
            
            # Start worker
            await worker.start()
            
            self.workers.append(worker)
            
            logger.info(f"✅ [WorkerManager] Worker started: {worker_id}")
        
        logger.info(f"✅ [WorkerManager] All workers started ({len(self.workers)} worker(s))")
    
    async def stop(self):
        """Stop all workers and retry scheduler (graceful shutdown)."""
        logger.info(f"⏹️ [WorkerManager] Stopping {len(self.workers)} worker(s)...")
        
        # Stop all workers (graceful drain)
        for worker in self.workers:
            await worker.stop()
        
        # Stop retry scheduler
        if self.retry_scheduler:
            await self.retry_scheduler.stop()
        
        logger.info("✅ [WorkerManager] All workers stopped")
    
    async def get_worker_stats(self) -> dict:
        """Get worker statistics."""
        stats = {
            "worker_count": len(self.workers),
            "workers": []
        }
        
        for worker in self.workers:
            heartbeat = await worker.heartbeat.get_heartbeat()
            if heartbeat:
                stats["workers"].append({
                    "worker_id": worker.worker_id,
                    "status": heartbeat.status,
                    "jobs_processed": heartbeat.jobsProcessed,
                    "current_job": heartbeat.currentJobId,
                    "last_heartbeat": heartbeat.lastHeartbeatAt.isoformat()
                })
        
        return stats


# Global singleton instance (опционально)
_worker_manager: Optional[ExecutionWorkerManager] = None


def get_worker_manager() -> Optional[ExecutionWorkerManager]:
    """Get singleton ExecutionWorkerManager instance."""
    global _worker_manager
    return _worker_manager


def set_worker_manager(manager: ExecutionWorkerManager):
    """Set singleton ExecutionWorkerManager instance."""
    global _worker_manager
    _worker_manager = manager
    logger.info("✅ ExecutionWorkerManager singleton set")
