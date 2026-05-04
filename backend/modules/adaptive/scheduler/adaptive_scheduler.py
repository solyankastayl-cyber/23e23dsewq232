"""
PHASE 3.4 — Adaptive Scheduler

Main scheduler orchestrator.
Runs background jobs on schedule.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from threading import Thread, Event
from dataclasses import dataclass
import time

from .scheduler_config import SchedulerConfig, DEFAULT_SCHEDULER_CONFIG
from .job_runner import JobRunner, JobType, JobResult


@dataclass
class SchedulerStatus:
    """Current scheduler status."""
    running: bool
    started_at: Optional[str]
    jobs_executed: int
    last_job_type: Optional[str]
    last_job_time: Optional[str]
    next_daily: Optional[str]
    next_hourly: Optional[str]
    config: Dict


class AdaptiveScheduler:
    """
    Main scheduler for adaptive layer.
    
    Runs in background thread with configurable intervals.
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or DEFAULT_SCHEDULER_CONFIG
        self.job_runner = JobRunner()
        
        self._running = False
        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        
        self._started_at: Optional[datetime] = None
        self._jobs_executed = 0
        self._last_job_type: Optional[str] = None
        self._last_job_time: Optional[datetime] = None
        
        self._last_daily: Optional[datetime] = None
        self._last_hourly: Optional[datetime] = None
        self._last_weekly: Optional[datetime] = None
    
    def start(self) -> bool:
        """Start the scheduler."""
        if self._running:
            return False
        
        self._running = True
        self._stop_event.clear()
        self._started_at = datetime.now(timezone.utc)
        
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        print(f"[Scheduler] Started at {self._started_at.isoformat()}")
        
        return True
    
    def stop(self) -> bool:
        """Stop the scheduler."""
        if not self._running:
            return False
        
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        print(f"[Scheduler] Stopped. Jobs executed: {self._jobs_executed}")
        
        return True
    
    def run_once(self, job_type: str = "daily") -> JobResult:
        """Run a specific job once (manual trigger)."""
        job_type_map = {
            "daily": JobType.DAILY_CALIBRATION,
            "hourly": JobType.HOURLY_HEALTH_CHECK,
            "weekly": JobType.WEEKLY_RECALIBRATION,
            "snapshot": JobType.SNAPSHOT,
            "performance": JobType.PERFORMANCE_CHECK,
            "rollback_check": JobType.AUTO_ROLLBACK_CHECK
        }
        
        jt = job_type_map.get(job_type, JobType.DAILY_CALIBRATION)
        
        result = self.job_runner.run(jt, use_mock=True)
        
        self._jobs_executed += 1
        self._last_job_type = jt.value
        self._last_job_time = datetime.now(timezone.utc)
        
        return result
    
    def get_status(self) -> SchedulerStatus:
        """Get current scheduler status."""
        now = datetime.now(timezone.utc)
        
        # Calculate next job times
        next_daily = None
        next_hourly = None
        
        if self._last_daily:
            next_daily = self._last_daily + timedelta(hours=self.config.calibration_interval_hours)
        
        if self._last_hourly:
            next_hourly = self._last_hourly + timedelta(minutes=self.config.health_check_interval_minutes)
        
        return SchedulerStatus(
            running=self._running,
            started_at=self._started_at.isoformat() if self._started_at else None,
            jobs_executed=self._jobs_executed,
            last_job_type=self._last_job_type,
            last_job_time=self._last_job_time.isoformat() if self._last_job_time else None,
            next_daily=next_daily.isoformat() if next_daily else None,
            next_hourly=next_hourly.isoformat() if next_hourly else None,
            config=self.config.to_dict()
        )
    
    def update_config(self, new_config: Dict):
        """Update scheduler configuration."""
        self.config = SchedulerConfig.from_dict(new_config)
    
    def get_job_history(self, limit: int = 20) -> List[Dict]:
        """Get job execution history."""
        return self.job_runner.get_history(limit)
    
    def _run_loop(self):
        """Main scheduler loop."""
        print("[Scheduler] Loop started")
        
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            
            # Check if within working hours (if enabled)
            if self.config.working_hours_only:
                if not (self.config.working_start_hour <= now.hour < self.config.working_end_hour):
                    self._stop_event.wait(60)  # Check every minute
                    continue
            
            # Check and run daily job
            if self._should_run_daily(now):
                self._run_job(JobType.DAILY_CALIBRATION)
                self._last_daily = now
            
            # Check and run hourly job
            if self._should_run_hourly(now):
                self._run_job(JobType.HOURLY_HEALTH_CHECK)
                self._last_hourly = now
            
            # Check and run weekly job
            if self._should_run_weekly(now):
                self._run_job(JobType.WEEKLY_RECALIBRATION)
                self._last_weekly = now
            
            # Sleep for a bit before next check
            self._stop_event.wait(60)  # Check every minute
        
        print("[Scheduler] Loop stopped")
    
    def _should_run_daily(self, now: datetime) -> bool:
        """Check if daily job should run."""
        if not self.config.auto_apply_enabled:
            return False
        
        if self._last_daily is None:
            return True
        
        interval = timedelta(hours=self.config.calibration_interval_hours)
        return now - self._last_daily >= interval
    
    def _should_run_hourly(self, now: datetime) -> bool:
        """Check if hourly job should run."""
        if self._last_hourly is None:
            return True
        
        interval = timedelta(minutes=self.config.health_check_interval_minutes)
        return now - self._last_hourly >= interval
    
    def _should_run_weekly(self, now: datetime) -> bool:
        """Check if weekly job should run."""
        if self._last_weekly is None:
            # Only run on configured day
            return now.weekday() == self.config.weekly_recalibration_day
        
        # Check if a week has passed
        return now - self._last_weekly >= timedelta(days=7)
    
    def _run_job(self, job_type: JobType):
        """Run a job and handle errors."""
        print(f"[Scheduler] Running job: {job_type.value}")
        
        try:
            # Use mock data for automated runs (real data in production)
            result = self.job_runner.run(job_type, use_mock=True)
            
            self._jobs_executed += 1
            self._last_job_type = job_type.value
            self._last_job_time = datetime.now(timezone.utc)
            
            if self.config.log_all_jobs:
                print(f"[Scheduler] Job {job_type.value} completed: {result.status.value}")
            
            # Handle rollback notification
            if result.result and result.result.get("status") == "rollback_triggered":
                if self.config.notify_on_rollback:
                    print(f"[Scheduler] ALERT: Auto-rollback triggered!")
            
        except Exception as e:
            print(f"[Scheduler] Job {job_type.value} failed: {e}")
            
            if self.config.notify_on_error:
                print(f"[Scheduler] ERROR: {str(e)}")
            
            if self.config.emergency_stop_on_critical:
                print("[Scheduler] Emergency stop activated")
                self._running = False


# Singleton instance
_scheduler: Optional[AdaptiveScheduler] = None


def get_scheduler() -> AdaptiveScheduler:
    """Get singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AdaptiveScheduler()
    return _scheduler
