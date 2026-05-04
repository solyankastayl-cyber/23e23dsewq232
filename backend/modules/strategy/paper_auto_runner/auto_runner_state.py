"""
Auto Runner State
==================

Phase 3.0B: State management for controlled autonomy.

Tracks:
  - paused / resumed status
  - auto_disabled status (hard safety trigger)
  - last run timestamp
  - run history (for rate limiting)
  - pause/disable reasons (for audit)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)


class AutoRunnerState:
    """
    Manages auto-runner state and run history.
    
    Responsibilities:
      - Track paused/resumed state
      - Track auto_disabled state (hard safety)
      - Maintain run history for rate limiting
      - Provide pause/resume/enable/disable controls
    """
    
    def __init__(self):
        # Pause state (manual control)
        self.paused = False
        self.pause_reason: Optional[str] = None
        
        # Auto-disabled state (hard safety trigger)
        self.auto_disabled = False
        self.auto_disabled_reason: Optional[str] = None
        
        # Run tracking
        self.last_run_at: Optional[datetime] = None
        self.run_timestamps: List[datetime] = []
        
        logger.info("[AutoRunnerState] Initialized")
    
    def pause(self, reason: str = "manual"):
        """
        Pause auto-runner (manual control).
        
        Args:
            reason: Reason for pausing
        """
        self.paused = True
        self.pause_reason = reason
        logger.warning(f"[AutoRunnerState] PAUSED: {reason}")
    
    def resume(self):
        """Resume auto-runner from paused state."""
        self.paused = False
        self.pause_reason = None
        logger.info("[AutoRunnerState] RESUMED")
    
    def disable(self, reason: str):
        """
        Disable auto-runner (hard safety trigger).
        
        Args:
            reason: Reason for disabling (e.g., execution_quality_too_low)
        """
        self.auto_disabled = True
        self.auto_disabled_reason = reason
        logger.error(f"[AutoRunnerState] AUTO_DISABLED: {reason}")
    
    def enable(self):
        """Enable auto-runner from auto_disabled state."""
        self.auto_disabled = False
        self.auto_disabled_reason = None
        logger.info("[AutoRunnerState] ENABLED")
    
    def register_run(self, now: datetime):
        """
        Register successful run.
        
        Args:
            now: Run timestamp
        """
        self.last_run_at = now
        self.run_timestamps.append(now)
        self._prune_old(now)
        logger.info(f"[AutoRunnerState] Run registered at {now.isoformat()}")
    
    def runs_last_hour(self, now: datetime) -> int:
        """
        Get count of runs in last hour.
        
        Args:
            now: Current timestamp
        
        Returns:
            Number of runs in last hour
        """
        self._prune_old(now)
        return len(self.run_timestamps)
    
    def _prune_old(self, now: datetime):
        """
        Prune run timestamps older than 1 hour.
        
        Args:
            now: Current timestamp
        """
        cutoff = now - timedelta(hours=1)
        self.run_timestamps = [ts for ts in self.run_timestamps if ts >= cutoff]
    
    def get_status(self) -> dict:
        """
        Get current state status.
        
        Returns:
            Status dictionary
        """
        now = datetime.now(timezone.utc)
        
        return {
            "paused": self.paused,
            "pause_reason": self.pause_reason,
            "auto_disabled": self.auto_disabled,
            "auto_disabled_reason": self.auto_disabled_reason,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "runs_last_hour": self.runs_last_hour(now)
        }
