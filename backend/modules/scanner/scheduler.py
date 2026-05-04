"""
Scanner Scheduler

Main orchestrator for the scanning system.
Runs in batch mode, not realtime.
"""

import time
import asyncio
from typing import Dict, Callable, Optional, Any
from datetime import datetime, timezone

from .scan_planner import ScanPlanner, get_scan_planner
from .ta_worker import TAWorker, get_ta_worker
from .prediction_scan_worker import PredictionScanWorker, get_prediction_scan_worker
from .job_queue import get_job_queue
from .asset_registry import get_asset_registry


class ScannerScheduler:
    """
    Main scheduler for scanning operations.
    
    Batch processing:
    - 4H: every 5-10 minutes
    - 1D: every 30-60 minutes
    
    NOT realtime.
    """
    
    def __init__(
        self,
        planner: ScanPlanner = None,
        ta_worker: TAWorker = None,
        prediction_worker: PredictionScanWorker = None,
    ):
        self.planner = planner or get_scan_planner()
        self.ta_worker = ta_worker or get_ta_worker()
        self.prediction_worker = prediction_worker or get_prediction_scan_worker()
        
        self._last_4h_scan = 0
        self._last_1d_scan = 0
        self._last_cleanup = 0
        
        # Intervals in seconds
        self.interval_4h = 600  # 10 minutes
        self.interval_1d = 1800  # 30 minutes
        self.interval_cleanup = 3600  # 1 hour
    
    def tick(
        self,
        build_ta_fn: Callable[[str, str], Dict],
        build_prediction_fn: Callable[[Dict], Dict],
        asset_limit: int = 100,
    ) -> Dict:
        """
        Single tick of the scheduler.
        
        Call this periodically (e.g., every minute).
        
        Args:
            build_ta_fn: Function(symbol, timeframe) -> ta_payload
            build_prediction_fn: Function(ta_payload) -> prediction_payload
            asset_limit: Number of assets to scan
        
        Returns:
            Summary of work done
        """
        now = int(time.time())
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ta_jobs_processed": 0,
            "prediction_jobs_processed": 0,
            "cleanup_done": False,
        }
        
        # ─────────────────────────────────────────────────────────
        # 1. Check if scan needed
        # ─────────────────────────────────────────────────────────
        needs_4h_scan = (now - self._last_4h_scan) >= self.interval_4h
        needs_1d_scan = (now - self._last_1d_scan) >= self.interval_1d
        needs_cleanup = (now - self._last_cleanup) >= self.interval_cleanup
        
        # ─────────────────────────────────────────────────────────
        # 2. Enqueue new scan jobs if needed
        # ─────────────────────────────────────────────────────────
        if needs_4h_scan:
            self.planner.enqueue_universe_scan(
                limit=asset_limit,
                timeframes=["4H"]
            )
            self._last_4h_scan = now
            summary["enqueued_4h"] = True
        
        if needs_1d_scan:
            self.planner.enqueue_universe_scan(
                limit=asset_limit,
                timeframes=["1D"]
            )
            self._last_1d_scan = now
            summary["enqueued_1d"] = True
        
        # ─────────────────────────────────────────────────────────
        # 3. Process TA jobs (burst)
        # ─────────────────────────────────────────────────────────
        summary["ta_jobs_processed"] = self.ta_worker.run_batch(
            build_ta_fn,
            max_jobs=20
        )
        
        # ─────────────────────────────────────────────────────────
        # 4. Process prediction jobs (burst)
        # ─────────────────────────────────────────────────────────
        summary["prediction_jobs_processed"] = self.prediction_worker.run_batch(
            build_prediction_fn,
            max_jobs=20
        )
        
        # ─────────────────────────────────────────────────────────
        # 5. Cleanup if needed
        # ─────────────────────────────────────────────────────────
        if needs_cleanup:
            queue = get_job_queue()
            queue.clear_stale_jobs()
            queue.cleanup_old_jobs()
            self._last_cleanup = now
            summary["cleanup_done"] = True
        
        return summary
    
    def run_full_scan(
        self,
        build_ta_fn: Callable[[str, str], Dict],
        build_prediction_fn: Callable[[Dict], Dict],
        asset_limit: int = 100,
        timeframes: list = None,
    ) -> Dict:
        """
        Run a complete scan of the universe.
        
        Useful for initial population or manual refresh.
        
        Args:
            build_ta_fn: Function(symbol, timeframe) -> ta_payload
            build_prediction_fn: Function(ta_payload) -> prediction_payload
            asset_limit: Number of assets to scan
            timeframes: Timeframes to scan
        
        Returns:
            Summary of work done
        """
        timeframes = timeframes or ["4H", "1D"]
        
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assets_scanned": asset_limit,
            "timeframes": timeframes,
            "ta_jobs_enqueued": 0,
            "prediction_jobs_enqueued": 0,
            "ta_jobs_processed": 0,
            "prediction_jobs_processed": 0,
        }
        
        # Enqueue all jobs
        enqueue_result = self.planner.enqueue_universe_scan(
            limit=asset_limit,
            timeframes=timeframes
        )
        summary["ta_jobs_enqueued"] = enqueue_result["ta_jobs"]
        summary["prediction_jobs_enqueued"] = enqueue_result["prediction_jobs"]
        
        # Process all TA jobs
        while True:
            processed = self.ta_worker.run_batch(build_ta_fn, max_jobs=50)
            summary["ta_jobs_processed"] += processed
            if processed == 0:
                break
        
        # Process all prediction jobs
        while True:
            processed = self.prediction_worker.run_batch(build_prediction_fn, max_jobs=50)
            summary["prediction_jobs_processed"] += processed
            if processed == 0:
                break
        
        return summary
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        queue = get_job_queue()
        registry = get_asset_registry()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_4h_scan": self._last_4h_scan,
            "last_1d_scan": self._last_1d_scan,
            "last_cleanup": self._last_cleanup,
            "queue_stats": queue.get_queue_stats(),
            "registry_stats": registry.get_stats(),
            "intervals": {
                "4h_interval_sec": self.interval_4h,
                "1d_interval_sec": self.interval_1d,
                "cleanup_interval_sec": self.interval_cleanup,
            }
        }


# Singleton
_scheduler: Optional[ScannerScheduler] = None


def get_scanner_scheduler() -> ScannerScheduler:
    """Get singleton scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ScannerScheduler()
    return _scheduler
