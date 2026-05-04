"""
PHASE 3.4 — Scheduler Configuration

Defines intervals, limits, and behavior for adaptive scheduler.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SchedulerConfig:
    """
    Configuration for adaptive scheduler.
    
    Controls timing, behavior, and safety limits.
    """
    
    # === Job Intervals ===
    calibration_interval_hours: int = 24
    apply_interval_hours: int = 24
    health_check_interval_minutes: int = 60
    snapshot_interval_hours: int = 24
    weekly_recalibration_day: int = 0  # Monday = 0
    
    # === Execution Limits ===
    max_parallel_jobs: int = 1
    job_timeout_minutes: int = 30
    max_retries: int = 3
    retry_delay_minutes: int = 5
    
    # === Auto Features ===
    auto_apply_enabled: bool = True
    auto_rollback_enabled: bool = True
    auto_snapshot_enabled: bool = True
    
    # === Safety ===
    min_trades_for_calibration: int = 50
    performance_check_enabled: bool = True
    emergency_stop_on_critical: bool = True
    
    # === Notification ===
    log_all_jobs: bool = True
    notify_on_rollback: bool = True
    notify_on_error: bool = True
    
    # === Working Hours (optional) ===
    working_hours_only: bool = False
    working_start_hour: int = 8
    working_end_hour: int = 22
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "calibration_interval_hours": self.calibration_interval_hours,
            "apply_interval_hours": self.apply_interval_hours,
            "health_check_interval_minutes": self.health_check_interval_minutes,
            "snapshot_interval_hours": self.snapshot_interval_hours,
            "weekly_recalibration_day": self.weekly_recalibration_day,
            "max_parallel_jobs": self.max_parallel_jobs,
            "job_timeout_minutes": self.job_timeout_minutes,
            "max_retries": self.max_retries,
            "retry_delay_minutes": self.retry_delay_minutes,
            "auto_apply_enabled": self.auto_apply_enabled,
            "auto_rollback_enabled": self.auto_rollback_enabled,
            "auto_snapshot_enabled": self.auto_snapshot_enabled,
            "min_trades_for_calibration": self.min_trades_for_calibration,
            "performance_check_enabled": self.performance_check_enabled,
            "emergency_stop_on_critical": self.emergency_stop_on_critical,
            "log_all_jobs": self.log_all_jobs,
            "notify_on_rollback": self.notify_on_rollback,
            "notify_on_error": self.notify_on_error,
            "working_hours_only": self.working_hours_only,
            "working_start_hour": self.working_start_hour,
            "working_end_hour": self.working_end_hour
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SchedulerConfig":
        """Create from dictionary."""
        return cls(
            calibration_interval_hours=data.get("calibration_interval_hours", 24),
            apply_interval_hours=data.get("apply_interval_hours", 24),
            health_check_interval_minutes=data.get("health_check_interval_minutes", 60),
            snapshot_interval_hours=data.get("snapshot_interval_hours", 24),
            weekly_recalibration_day=data.get("weekly_recalibration_day", 0),
            max_parallel_jobs=data.get("max_parallel_jobs", 1),
            job_timeout_minutes=data.get("job_timeout_minutes", 30),
            max_retries=data.get("max_retries", 3),
            retry_delay_minutes=data.get("retry_delay_minutes", 5),
            auto_apply_enabled=data.get("auto_apply_enabled", True),
            auto_rollback_enabled=data.get("auto_rollback_enabled", True),
            auto_snapshot_enabled=data.get("auto_snapshot_enabled", True),
            min_trades_for_calibration=data.get("min_trades_for_calibration", 50),
            performance_check_enabled=data.get("performance_check_enabled", True),
            emergency_stop_on_critical=data.get("emergency_stop_on_critical", True),
            log_all_jobs=data.get("log_all_jobs", True),
            notify_on_rollback=data.get("notify_on_rollback", True),
            notify_on_error=data.get("notify_on_error", True),
            working_hours_only=data.get("working_hours_only", False),
            working_start_hour=data.get("working_start_hour", 8),
            working_end_hour=data.get("working_end_hour", 22)
        )


# Default configuration
DEFAULT_SCHEDULER_CONFIG = SchedulerConfig()

# Aggressive - more frequent updates (for testing)
AGGRESSIVE_SCHEDULER_CONFIG = SchedulerConfig(
    calibration_interval_hours=6,
    apply_interval_hours=6,
    health_check_interval_minutes=15,
    snapshot_interval_hours=6
)

# Conservative - less frequent updates (for production)
CONSERVATIVE_SCHEDULER_CONFIG = SchedulerConfig(
    calibration_interval_hours=48,
    apply_interval_hours=48,
    health_check_interval_minutes=120,
    snapshot_interval_hours=48,
    auto_apply_enabled=False  # Manual approval required
)
