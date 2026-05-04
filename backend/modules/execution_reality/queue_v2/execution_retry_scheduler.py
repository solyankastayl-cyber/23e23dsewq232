"""
Execution Retry Scheduler (P1.3.2)
===================================

Retry queue processor: retry_wait → queued transitions.
"""

import logging
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ExecutionRetryScheduler:
    """
    Retry scheduler для execution queue.
    
    Responsibilities:
    - Find jobs in retry_wait with nextRetryAt <= now
    - Transition them back to queued
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, interval_seconds: int = 10):
        """
        Args:
            db: MongoDB database
            interval_seconds: Scheduler polling interval (default 10s)
        """
        self.collection = db["execution_jobs"]
        self.interval_seconds = interval_seconds
        
        # Control
        self._scheduler_task = None
        self._running = False
        
        logger.info(f"✅ ExecutionRetryScheduler initialized: interval={interval_seconds}s")
    
    async def start(self):
        """Start retry scheduler loop."""
        if self._running:
            logger.warning("[RetryScheduler] Already running")
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("🔄 [RetryScheduler] Started")
    
    async def stop(self):
        """Stop retry scheduler loop."""
        if not self._running:
            return
        
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ [RetryScheduler] Stopped")
    
    async def _scheduler_loop(self):
        """Background scheduler loop."""
        try:
            while self._running:
                await asyncio.sleep(self.interval_seconds)
                
                if not self._running:
                    break
                
                await self._process_retries()
        
        except asyncio.CancelledError:
            logger.debug("[RetryScheduler] Loop cancelled")
        except Exception as e:
            logger.error(f"[RetryScheduler] Loop error: {e}", exc_info=True)
    
    async def _process_retries(self):
        """Process retry_wait jobs ready for retry AND reclaim zombie leased jobs."""
        try:
            now = datetime.now(timezone.utc)
            
            # 1. Retry transition: retry_wait → queued
            result = await self.collection.update_many(
                {
                    "status": "retry_wait",
                    "nextRetryAt": {"$lte": now}
                },
                {
                    "$set": {
                        "status": "queued",
                        "nextRetryAt": None,
                        "updatedAt": now
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(
                    f"🔄 [RetryScheduler] Transitioned {result.modified_count} jobs: "
                    f"retry_wait → queued"
                )
            
            # 2. P1.3.2B: Reclaim zombie leased jobs (expired lease)
            reclaim_result = await self.collection.update_many(
                {
                    "status": "leased",
                    "leaseExpiresAt": {"$lt": now}
                },
                {
                    "$set": {
                        "status": "queued",
                        "leaseOwner": None,
                        "leaseExpiresAt": None,
                        "leaseToken": None,
                        "updatedAt": now
                    }
                }
            )
            
            if reclaim_result.modified_count > 0:
                logger.warning(
                    f"⚠️ [P1.3.2B Reclaim] Reclaimed {reclaim_result.modified_count} zombie jobs: "
                    f"leased (expired) → queued"
                )
        
        except Exception as e:
            logger.error(f"[RetryScheduler] Process error: {e}", exc_info=True)
