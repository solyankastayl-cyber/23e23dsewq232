"""
Scanner Engine

Continuous market scanning system for prediction at scale.

Architecture:
    Asset Registry → Scan Planner → Job Queue → Workers → Storage → Ranking

NOT realtime, but batch processing:
- 4H: every 5-10 min
- 1D: every 30-60 min
"""

from .types import ScanJob, AssetRegistryItem, JobType, JobStatus
from .asset_registry import AssetRegistry, get_asset_registry
from .job_queue import JobQueue, get_job_queue
from .scan_planner import ScanPlanner, get_scan_planner
from .ta_worker import TAWorker
from .prediction_scan_worker import PredictionScanWorker
from .ranking import PredictionRanking, compute_prediction_score, is_prediction_publishable
from .scheduler import ScannerScheduler, get_scanner_scheduler

__all__ = [
    # Types
    "ScanJob",
    "AssetRegistryItem",
    "JobType",
    "JobStatus",
    # Registry
    "AssetRegistry",
    "get_asset_registry",
    # Queue
    "JobQueue",
    "get_job_queue",
    # Planner
    "ScanPlanner",
    "get_scan_planner",
    # Workers
    "TAWorker",
    "PredictionScanWorker",
    # Ranking
    "PredictionRanking",
    "compute_prediction_score",
    "is_prediction_publishable",
    # Scheduler
    "ScannerScheduler",
    "get_scanner_scheduler",
]
