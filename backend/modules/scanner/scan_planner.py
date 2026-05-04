"""
Scan Planner

Creates jobs for scanning the asset universe.
"""

from typing import List, Optional
from .types import ScanJob, SCAN_TIMEFRAMES, PRIORITY_HIGH, PRIORITY_NORMAL, DEFAULT_ASSET_LIMIT
from .asset_registry import AssetRegistry, get_asset_registry
from .job_queue import JobQueue, get_job_queue


class ScanPlanner:
    """
    Plans scanning jobs for the asset universe.
    
    Workflow:
    1. Get active assets from registry
    2. For each asset + timeframe combination
    3. Create ta_scan job (priority high)
    4. Create prediction_build job (priority normal)
    """
    
    def __init__(self, registry: AssetRegistry = None, queue: JobQueue = None):
        self.registry = registry or get_asset_registry()
        self.queue = queue or get_job_queue()
    
    def enqueue_universe_scan(
        self, 
        limit: int = DEFAULT_ASSET_LIMIT,
        timeframes: List[str] = None
    ) -> dict:
        """
        Enqueue scanning jobs for entire asset universe.
        
        Args:
            limit: Number of top assets to scan
            timeframes: Timeframes to scan (default: 4H, 1D)
        
        Returns:
            Summary of jobs enqueued
        """
        timeframes = timeframes or SCAN_TIMEFRAMES
        
        assets = self.registry.get_active_assets(limit=limit)
        
        summary = {
            "assets_scanned": len(assets),
            "timeframes": timeframes,
            "ta_jobs": 0,
            "prediction_jobs": 0,
        }
        
        for asset in assets:
            for tf in timeframes:
                # TA scan job (higher priority - must run first)
                ta_job = ScanJob.make(
                    job_type="ta_scan",
                    symbol=asset.symbol,
                    timeframe=tf,
                    priority=PRIORITY_HIGH,
                )
                if self.queue.enqueue(ta_job):
                    summary["ta_jobs"] += 1
                
                # Prediction build job (lower priority - runs after TA)
                pred_job = ScanJob.make(
                    job_type="prediction_build",
                    symbol=asset.symbol,
                    timeframe=tf,
                    priority=PRIORITY_NORMAL,
                )
                if self.queue.enqueue(pred_job):
                    summary["prediction_jobs"] += 1
        
        return summary
    
    def enqueue_single_asset(
        self, 
        symbol: str, 
        timeframes: List[str] = None
    ) -> dict:
        """
        Enqueue scan jobs for a single asset.
        
        Args:
            symbol: Asset symbol (e.g., "BTC")
            timeframes: Timeframes to scan
        
        Returns:
            Summary of jobs enqueued
        """
        timeframes = timeframes or SCAN_TIMEFRAMES
        
        summary = {
            "symbol": symbol,
            "timeframes": timeframes,
            "ta_jobs": 0,
            "prediction_jobs": 0,
        }
        
        for tf in timeframes:
            ta_job = ScanJob.make(
                job_type="ta_scan",
                symbol=symbol,
                timeframe=tf,
                priority=PRIORITY_HIGH,
            )
            if self.queue.enqueue(ta_job):
                summary["ta_jobs"] += 1
            
            pred_job = ScanJob.make(
                job_type="prediction_build",
                symbol=symbol,
                timeframe=tf,
                priority=PRIORITY_NORMAL,
            )
            if self.queue.enqueue(pred_job):
                summary["prediction_jobs"] += 1
        
        return summary
    
    def enqueue_evaluation_jobs(self) -> int:
        """
        Enqueue evaluation jobs for pending predictions.
        
        Returns:
            Number of jobs enqueued
        """
        # This is handled by a separate evaluation worker
        # that processes pending predictions directly
        return 0


# Singleton
_planner: Optional[ScanPlanner] = None


def get_scan_planner() -> ScanPlanner:
    """Get singleton scan planner."""
    global _planner
    if _planner is None:
        _planner = ScanPlanner()
    return _planner
