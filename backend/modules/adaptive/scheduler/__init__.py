"""
PHASE 3.4 — Adaptive Scheduler

Makes the system autonomous with scheduled jobs:
- Daily: calibration → actions → apply → snapshot
- Hourly: performance monitoring → auto-rollback
- Weekly: full recalibration → reset degraded assets

Modules:
- scheduler_config: Configuration and intervals
- job_runner: Individual job execution
- adaptive_scheduler: Main orchestrator
"""

from .adaptive_scheduler import AdaptiveScheduler, get_scheduler
from .scheduler_config import SchedulerConfig, DEFAULT_SCHEDULER_CONFIG
from .job_runner import JobRunner, JobType, JobResult

__all__ = [
    "AdaptiveScheduler",
    "get_scheduler",
    "SchedulerConfig",
    "DEFAULT_SCHEDULER_CONFIG",
    "JobRunner",
    "JobType",
    "JobResult",
]
