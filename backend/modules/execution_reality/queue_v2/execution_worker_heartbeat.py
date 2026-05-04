"""
Execution Worker Heartbeat (P1.3.2)
====================================

Heartbeat writer для worker lifecycle tracking.

Записывает heartbeat в worker_heartbeats коллекцию каждые 5s.
"""

import logging
import asyncio
from typing import Optional, Literal
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


WorkerStatus = Literal["starting", "healthy", "busy", "draining", "stopped"]


class WorkerHeartbeat(BaseModel):
    """
    Worker heartbeat document (Mongo: worker_heartbeats).
    """
    workerId: str
    status: WorkerStatus = "starting"
    lastHeartbeatAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    currentJobId: Optional[str] = None
    jobsProcessed: int = 0
    startedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


class ExecutionWorkerHeartbeatWriter:
    """
    Worker heartbeat writer.
    
    Responsibilities:
    - Write heartbeat every N seconds
    - Update worker status
    - Track current job
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        worker_id: str,
        interval_seconds: int = 5
    ):
        """
        Args:
            db: MongoDB database
            worker_id: Unique worker identifier
            interval_seconds: Heartbeat interval (default 5s)
        """
        self.collection = db["worker_heartbeats"]
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds
        
        # State
        self.status: WorkerStatus = "starting"
        self.current_job_id: Optional[str] = None
        self.jobs_processed: int = 0
        self.started_at = datetime.now(timezone.utc)
        
        # Control
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"✅ ExecutionWorkerHeartbeatWriter initialized: "
            f"worker_id={worker_id}, interval={interval_seconds}s"
        )
    
    async def ensure_indexes(self):
        """Create required indexes."""
        # Worker ID lookup (unique per worker)
        await self.collection.create_index("workerId", unique=True)
        
        # Status filtering
        await self.collection.create_index("status")
        
        # Heartbeat timestamp (для stale detection)
        await self.collection.create_index("lastHeartbeatAt")
        
        logger.info("✅ worker_heartbeats indexes created")
    
    async def start(self):
        """Start heartbeat loop."""
        if self._running:
            logger.warning(f"[Heartbeat] Already running: worker_id={self.worker_id}")
            return
        
        self._running = True
        self.status = "healthy"
        
        # Write initial heartbeat
        await self._write_heartbeat()
        
        # Start background loop
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"🔄 [Heartbeat] Started: worker_id={self.worker_id}")
    
    async def stop(self):
        """Stop heartbeat loop."""
        if not self._running:
            return
        
        self._running = False
        self.status = "stopped"
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Write final heartbeat
        await self._write_heartbeat()
        
        logger.info(f"⏹️ [Heartbeat] Stopped: worker_id={self.worker_id}")
    
    async def update_status(self, status: WorkerStatus):
        """Update worker status."""
        self.status = status
        await self._write_heartbeat()
        
        logger.debug(f"[Heartbeat] Status updated: {status}, worker_id={self.worker_id}")
    
    def set_current_job(self, job_id: Optional[str]):
        """Set current processing job."""
        self.current_job_id = job_id
        
        if job_id:
            logger.debug(f"[Heartbeat] Processing job: {job_id}, worker_id={self.worker_id}")
    
    def increment_jobs_processed(self):
        """Increment jobs processed counter."""
        self.jobs_processed += 1
    
    async def _heartbeat_loop(self):
        """Background heartbeat loop."""
        try:
            while self._running:
                await asyncio.sleep(self.interval_seconds)
                
                if not self._running:
                    break
                
                await self._write_heartbeat()
        
        except asyncio.CancelledError:
            logger.debug(f"[Heartbeat] Loop cancelled: worker_id={self.worker_id}")
        except Exception as e:
            logger.error(f"[Heartbeat] Loop error: {e}", exc_info=True)
    
    async def _write_heartbeat(self):
        """Write heartbeat to database (upsert)."""
        try:
            now = datetime.now(timezone.utc)
            
            heartbeat = WorkerHeartbeat(
                workerId=self.worker_id,
                status=self.status,
                lastHeartbeatAt=now,
                currentJobId=self.current_job_id,
                jobsProcessed=self.jobs_processed,
                startedAt=self.started_at
            )
            
            # Upsert heartbeat
            await self.collection.update_one(
                {"workerId": self.worker_id},
                {"$set": heartbeat.dict()},
                upsert=True
            )
            
            logger.debug(
                f"[Heartbeat] Written: worker_id={self.worker_id}, "
                f"status={self.status}, jobs_processed={self.jobs_processed}"
            )
        
        except Exception as e:
            logger.error(f"[Heartbeat] Write error: {e}", exc_info=True)
    
    async def get_heartbeat(self) -> Optional[WorkerHeartbeat]:
        """Get current heartbeat from database."""
        doc = await self.collection.find_one({"workerId": self.worker_id})
        if doc:
            return WorkerHeartbeat(**doc)
        return None
