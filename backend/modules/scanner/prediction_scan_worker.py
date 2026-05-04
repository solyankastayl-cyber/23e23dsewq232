"""
Prediction Scan Worker

Builds predictions from TA snapshots.
"""

import time
from typing import Dict, Optional, Callable, Any
from .types import ScanJob, PredictionSnapshot
from .job_queue import JobQueue, get_job_queue
from .ta_worker import TAWorker
from .ranking import enrich_prediction_with_score


class PredictionScanWorker:
    """
    Worker that processes prediction_build jobs.
    
    Workflow:
    1. Claim prediction_build job from queue
    2. Get latest TA snapshot
    3. Build prediction using provided function
    4. Enrich with score and publishability
    5. Save prediction snapshot
    6. Mark job done
    """
    
    def __init__(self, db=None, queue: JobQueue = None, ta_worker: TAWorker = None):
        self.db = db
        self.queue = queue or get_job_queue()
        self.ta_worker = ta_worker or TAWorker(db)
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def save_prediction_snapshot(
        self, 
        symbol: str, 
        timeframe: str, 
        prediction_payload: Dict[str, Any]
    ) -> bool:
        """
        Save prediction snapshot, marking previous as non-latest.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe
            prediction_payload: Prediction output (already enriched with score)
        
        Returns:
            Success status
        """
        if self.db is None:
            return False
        
        try:
            # Mark previous as non-latest
            self.db.prediction_snapshots.update_many(
                {"symbol": symbol, "timeframe": timeframe, "latest": True},
                {"$set": {"latest": False}}
            )
            
            # Extract score and publishable from payload
            score = prediction_payload.get("score", 0)
            publishable = prediction_payload.get("publishable", False)
            valid = prediction_payload.get("valid", False)
            
            # Extract regime/model for P3/P4/P5 tracking
            regime = prediction_payload.get("regime", "unknown")
            model = prediction_payload.get("model", "unknown")
            
            # Insert new snapshot
            self.db.prediction_snapshots.insert_one({
                "symbol": symbol,
                "timeframe": timeframe,
                "created_at": int(time.time()),
                "latest": True,
                "prediction_payload": prediction_payload,
                # P3: Outcome tracking fields
                "status": "pending",
                "resolution": None,
                # P4/P5: Regime and model for calibration
                "regime": regime,
                "model": model,
                # Ranking
                "score": score,
                "publishable": publishable,
                "valid": valid,
            })
            return True
        except Exception as e:
            print(f"[PredictionScanWorker] Save error: {e}")
            return False
    
    def get_latest_prediction(
        self, 
        symbol: str, 
        timeframe: str
    ) -> Optional[Dict]:
        """Get latest prediction snapshot for symbol/timeframe."""
        if self.db is None:
            return None
        
        try:
            return self.db.prediction_snapshots.find_one(
                {"symbol": symbol, "timeframe": timeframe, "latest": True},
                {"_id": 0}
            )
        except Exception:
            return None
    
    def run_once(self, build_prediction_fn: Callable[[Dict], Dict]) -> bool:
        """
        Process one prediction_build job.
        
        Args:
            build_prediction_fn: Function(ta_payload) -> prediction_payload
        
        Returns:
            True if job processed, False if no job available
        """
        job = self.queue.claim_next(job_type="prediction_build")
        if not job:
            return False
        
        try:
            # Get latest TA snapshot
            ta_snap = self.ta_worker.get_latest_snapshot(job.symbol, job.timeframe)
            if not ta_snap:
                self.queue.mark_failed(job.job_id, "No TA snapshot found")
                return False
            
            # Build prediction
            prediction_payload = build_prediction_fn(ta_snap.get("ta_payload", {}))
            
            # Enrich with score
            enriched = enrich_prediction_with_score(prediction_payload)
            
            # Save snapshot
            self.save_prediction_snapshot(job.symbol, job.timeframe, enriched)
            
            # Mark done
            self.queue.mark_done(job.job_id)
            return True
        
        except Exception as e:
            self.queue.mark_failed(job.job_id, str(e))
            return False
    
    def run_batch(
        self, 
        build_prediction_fn: Callable[[Dict], Dict], 
        max_jobs: int = 20
    ) -> int:
        """
        Process multiple prediction_build jobs.
        
        Args:
            build_prediction_fn: Function(ta_payload) -> prediction_payload
            max_jobs: Maximum number of jobs to process
        
        Returns:
            Number of jobs processed
        """
        processed = 0
        for _ in range(max_jobs):
            if self.run_once(build_prediction_fn):
                processed += 1
            else:
                break  # No more jobs
        return processed
    
    def get_latest_predictions_batch(
        self, 
        limit: int = 50,
        publishable_only: bool = False,
        valid_only: bool = False
    ) -> list:
        """
        Get latest predictions across all assets.
        
        Args:
            limit: Maximum number to return
            publishable_only: Only return publishable predictions
            valid_only: Only return predictions that passed P2 filter
        
        Returns:
            List of prediction snapshots
        """
        if self.db is None:
            return []
        
        try:
            query = {"latest": True}
            if publishable_only:
                query["publishable"] = True
            if valid_only:
                query["prediction_payload.valid"] = True
            
            cursor = self.db.prediction_snapshots.find(
                query,
                {"_id": 0}
            ).sort("score", -1).limit(limit)
            
            return list(cursor)
        except Exception:
            return []
    
    def get_top_predictions(self, limit: int = 20) -> list:
        """Get top ranked valid predictions (Decision Engine filtered)."""
        return self.get_latest_predictions_batch(
            limit=limit,
            publishable_only=True,
            valid_only=True
        )


def get_prediction_scan_worker() -> PredictionScanWorker:
    """Create prediction worker instance."""
    return PredictionScanWorker()
