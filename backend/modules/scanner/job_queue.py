"""
Job Queue

MongoDB-based job queue for scanning tasks.
No Kafka/RabbitMQ needed at this scale.
"""

import time
from typing import List, Optional, Dict
from .types import ScanJob, JobType, JobStatus


class JobQueue:
    """
    MongoDB-based job queue.
    
    Collections used:
    - scan_jobs: job queue with status tracking
    """
    
    def __init__(self, db=None):
        self.db = db
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def enqueue(self, job: ScanJob) -> bool:
        """
        Add job to queue.
        
        Args:
            job: Job to enqueue
        
        Returns:
            Success status
        """
        if self.db is None:
            return False
        
        try:
            # Check if similar job already queued
            existing = self.db.scan_jobs.find_one({
                "symbol": job.symbol,
                "timeframe": job.timeframe,
                "job_type": job.job_type,
                "status": {"$in": ["queued", "running"]},
            })
            
            if existing:
                # Skip duplicate
                return True
            
            self.db.scan_jobs.insert_one(job.to_dict())
            return True
        except Exception as e:
            print(f"[JobQueue] Enqueue error: {e}")
            return False
    
    def claim_next(self, job_type: Optional[JobType] = None) -> Optional[ScanJob]:
        """
        Claim next available job.
        
        Uses atomic find_one_and_update to prevent race conditions.
        
        Args:
            job_type: Optional filter by job type
        
        Returns:
            Claimed job or None
        """
        if self.db is None:
            return None
        
        try:
            query = {"status": "queued"}
            if job_type:
                query["job_type"] = job_type
            
            doc = self.db.scan_jobs.find_one_and_update(
                query,
                {
                    "$set": {
                        "status": "running",
                        "started_at": int(time.time())
                    }
                },
                sort=[("priority", -1), ("created_at", 1)],
                return_document=True  # Return updated document
            )
            
            if doc:
                return ScanJob.from_dict(doc)
            return None
        except Exception as e:
            print(f"[JobQueue] Claim error: {e}")
            return None
    
    def mark_done(self, job_id: str) -> bool:
        """Mark job as completed."""
        if self.db is None:
            return False
        
        try:
            self.db.scan_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"status": "done", "finished_at": int(time.time())}}
            )
            return True
        except Exception:
            return False
    
    def mark_failed(self, job_id: str, error: str) -> bool:
        """Mark job as failed with error message."""
        if self.db is None:
            return False
        
        try:
            self.db.scan_jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "finished_at": int(time.time()),
                        "error": error
                    }
                }
            )
            return True
        except Exception:
            return False
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        if self.db is None:
            return {"queued": 0, "running": 0, "done": 0, "failed": 0}
        
        try:
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            results = list(self.db.scan_jobs.aggregate(pipeline))
            
            stats = {"queued": 0, "running": 0, "done": 0, "failed": 0}
            for r in results:
                if r["_id"] in stats:
                    stats[r["_id"]] = r["count"]
            
            return stats
        except Exception:
            return {"queued": 0, "running": 0, "done": 0, "failed": 0}
    
    def get_pending_jobs(self, limit: int = 50) -> List[ScanJob]:
        """Get pending (queued) jobs."""
        if self.db is None:
            return []
        
        try:
            cursor = self.db.scan_jobs.find(
                {"status": "queued"}
            ).sort([("priority", -1), ("created_at", 1)]).limit(limit)
            
            return [ScanJob.from_dict(doc) for doc in cursor]
        except Exception:
            return []
    
    def clear_stale_jobs(self, max_age_seconds: int = 3600) -> int:
        """
        Clear jobs stuck in 'running' state for too long.
        
        Args:
            max_age_seconds: Max age before considering job stale
        
        Returns:
            Number of jobs cleared
        """
        if self.db is None:
            return 0
        
        try:
            cutoff = int(time.time()) - max_age_seconds
            
            result = self.db.scan_jobs.update_many(
                {
                    "status": "running",
                    "started_at": {"$lt": cutoff}
                },
                {
                    "$set": {
                        "status": "failed",
                        "finished_at": int(time.time()),
                        "error": "Stale job timeout"
                    }
                }
            )
            return result.modified_count
        except Exception:
            return 0
    
    def cleanup_old_jobs(self, max_age_days: int = 7) -> int:
        """
        Delete old completed/failed jobs.
        
        Args:
            max_age_days: Max age in days before deletion
        
        Returns:
            Number of jobs deleted
        """
        if self.db is None:
            return 0
        
        try:
            cutoff = int(time.time()) - (max_age_days * 86400)
            
            result = self.db.scan_jobs.delete_many({
                "status": {"$in": ["done", "failed"]},
                "finished_at": {"$lt": cutoff}
            })
            return result.deleted_count
        except Exception:
            return 0


# Singleton
_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get singleton job queue."""
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue
