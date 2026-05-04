"""
TA Worker

Builds TA snapshots for assets.
"""

import time
from typing import Dict, Optional, Callable, Any
from .types import ScanJob, TASnapshot
from .job_queue import JobQueue, get_job_queue


class TAWorker:
    """
    Worker that processes ta_scan jobs.
    
    Workflow:
    1. Claim ta_scan job from queue
    2. Build TA using provided function
    3. Save TA snapshot
    4. Mark job done
    """
    
    def __init__(self, db=None, queue: JobQueue = None):
        self.db = db
        self.queue = queue or get_job_queue()
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def save_ta_snapshot(
        self, 
        symbol: str, 
        timeframe: str, 
        ta_payload: Dict[str, Any]
    ) -> bool:
        """
        Save TA snapshot, marking previous as non-latest.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe
            ta_payload: TA analysis output
        
        Returns:
            Success status
        """
        if self.db is None:
            return False
        
        try:
            # Mark previous as non-latest
            self.db.ta_snapshots.update_many(
                {"symbol": symbol, "timeframe": timeframe, "latest": True},
                {"$set": {"latest": False}}
            )
            
            # Insert new snapshot
            self.db.ta_snapshots.insert_one({
                "symbol": symbol,
                "timeframe": timeframe,
                "created_at": int(time.time()),
                "latest": True,
                "ta_payload": ta_payload,
            })
            return True
        except Exception as e:
            print(f"[TAWorker] Save error: {e}")
            return False
    
    def get_latest_snapshot(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Optional[Dict]:
        """Get latest TA snapshot for symbol/timeframe."""
        if self.db is None:
            return None
        
        try:
            return self.db.ta_snapshots.find_one(
                {"symbol": symbol, "timeframe": timeframe, "latest": True},
                {"_id": 0}
            )
        except Exception:
            return None
    
    def run_once(self, build_ta_fn: Callable[[str, str], Dict]) -> bool:
        """
        Process one ta_scan job.
        
        Args:
            build_ta_fn: Function(symbol, timeframe) -> ta_payload
        
        Returns:
            True if job processed, False if no job available
        """
        job = self.queue.claim_next(job_type="ta_scan")
        if not job:
            return False
        
        try:
            # Build TA
            ta_payload = build_ta_fn(job.symbol, job.timeframe)
            
            # Save snapshot
            self.save_ta_snapshot(job.symbol, job.timeframe, ta_payload)
            
            # Mark done
            self.queue.mark_done(job.job_id)
            return True
        
        except Exception as e:
            self.queue.mark_failed(job.job_id, str(e))
            return False
    
    def run_batch(
        self, 
        build_ta_fn: Callable[[str, str], Dict], 
        max_jobs: int = 20
    ) -> int:
        """
        Process multiple ta_scan jobs.
        
        Args:
            build_ta_fn: Function(symbol, timeframe) -> ta_payload
            max_jobs: Maximum number of jobs to process
        
        Returns:
            Number of jobs processed
        """
        processed = 0
        for _ in range(max_jobs):
            if self.run_once(build_ta_fn):
                processed += 1
            else:
                break  # No more jobs
        return processed


def get_ta_worker() -> TAWorker:
    """Create TA worker instance."""
    return TAWorker()
