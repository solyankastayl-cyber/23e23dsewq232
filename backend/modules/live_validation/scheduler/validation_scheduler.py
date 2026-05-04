"""
Validation Scheduler
====================
Background thread scheduler for continuous adaptive loop.

Runs three jobs at different intervals:
1. Shadow trade creation (every 60s)
2. Validation execution (every 120s)  
3. Alpha cycle: AF3 + AF4 (every 300s)

Features:
- Thread-safe start/stop
- Error isolation (never crashes)
- Observability (last run timestamps, errors)
- Configurable intervals
"""

import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .scheduler_config import SCHEDULER_CONFIG
from .scheduler_jobs import SchedulerJobs


class ValidationScheduler:
    """Background scheduler for continuous validation and adaptation."""
    
    def __init__(self, jobs: SchedulerJobs):
        """
        Initialize scheduler with job executor.
        
        Args:
            jobs: SchedulerJobs instance with engine references
        """
        self.jobs = jobs
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Last run timestamps
        self.last_shadow_run = 0.0
        self.last_validation_run = 0.0
        self.last_alpha_run = 0.0
        
        # Last results
        self.last_shadow_result: Optional[Dict] = None
        self.last_validation_result: Optional[Dict] = None
        self.last_alpha_result: Optional[Dict] = None
        
        # Error tracking
        self.last_error: Optional[Dict] = None
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def start(self) -> Dict[str, Any]:
        """
        Start the scheduler loop.
        
        Idempotent - safe to call multiple times.
        
        Returns:
            Status dict
        """
        with self._lock:
            if self.running:
                return {"status": "already_running", "message": "Scheduler is already running"}
            
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True, name="ValidationScheduler")
            self.thread.start()
            
            print("[Scheduler] Validation Scheduler started")
            
            return {
                "status": "started",
                "message": "Scheduler started successfully",
                "config": {
                    "shadow_interval": SCHEDULER_CONFIG["shadow_creation_interval_sec"],
                    "validation_interval": SCHEDULER_CONFIG["validation_interval_sec"],
                    "alpha_interval": SCHEDULER_CONFIG["alpha_cycle_interval_sec"],
                }
            }
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop the scheduler loop.
        
        Returns:
            Status dict
        """
        with self._lock:
            if not self.running:
                return {"status": "not_running", "message": "Scheduler is not running"}
            
            self.running = False
            print("[Scheduler] Validation Scheduler stopping...")
            
            return {
                "status": "stopped",
                "message": "Scheduler stopped successfully"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status.
        
        Returns:
            Detailed status including last run times, results, and errors
        """
        return {
            "running": self.running,
            "config": {
                "shadow_interval_sec": SCHEDULER_CONFIG["shadow_creation_interval_sec"],
                "validation_interval_sec": SCHEDULER_CONFIG["validation_interval_sec"],
                "alpha_cycle_interval_sec": SCHEDULER_CONFIG["alpha_cycle_interval_sec"],
                "max_shadow_per_cycle": SCHEDULER_CONFIG["max_shadow_per_cycle"],
                "symbols_limit": SCHEDULER_CONFIG["symbols_limit"],
            },
            "last_runs": {
                "shadow_creation": datetime.fromtimestamp(self.last_shadow_run, tz=timezone.utc).isoformat() if self.last_shadow_run > 0 else None,
                "validation": datetime.fromtimestamp(self.last_validation_run, tz=timezone.utc).isoformat() if self.last_validation_run > 0 else None,
                "alpha_cycle": datetime.fromtimestamp(self.last_alpha_run, tz=timezone.utc).isoformat() if self.last_alpha_run > 0 else None,
            },
            "last_results": {
                "shadow_creation": self.last_shadow_result,
                "validation": self.last_validation_result,
                "alpha_cycle": self.last_alpha_result,
            },
            "stats": self.jobs.get_stats(),
            "last_error": self.last_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def _loop(self):
        """
        Main scheduler loop.
        
        Runs in background thread and executes jobs based on intervals.
        Never crashes - all errors are caught and logged.
        """
        print("[Scheduler] Loop started")
        
        while self.running:
            now = time.time()
            
            try:
                # Job 1: Shadow Creation
                if now - self.last_shadow_run >= SCHEDULER_CONFIG["shadow_creation_interval_sec"]:
                    if SCHEDULER_CONFIG.get("verbose_logging", False):
                        print(f"[Scheduler] Running shadow creation job...")
                    
                    result = self.jobs.run_shadow_creation()
                    self.last_shadow_result = result
                    self.last_shadow_run = now
                    
                    if result.get("ok"):
                        if SCHEDULER_CONFIG.get("verbose_logging", False):
                            print(f"[Scheduler] Shadow creation: {result.get('created', 0)} created")
                    else:
                        print(f"[Scheduler] Shadow creation error: {result.get('error')}")
                        self.last_error = {"job": "shadow_creation", "error": result.get("error"), "timestamp": datetime.now(timezone.utc).isoformat()}
                
                # Job 2: Validation
                if now - self.last_validation_run >= SCHEDULER_CONFIG["validation_interval_sec"]:
                    if SCHEDULER_CONFIG.get("verbose_logging", False):
                        print(f"[Scheduler] Running validation job...")
                    
                    result = self.jobs.run_validation()
                    self.last_validation_result = result
                    self.last_validation_run = now
                    
                    if result.get("ok"):
                        if SCHEDULER_CONFIG.get("verbose_logging", False):
                            print(f"[Scheduler] Validation: {result.get('validated', 0)} validated")
                    else:
                        print(f"[Scheduler] Validation error: {result.get('error')}")
                        self.last_error = {"job": "validation", "error": result.get("error"), "timestamp": datetime.now(timezone.utc).isoformat()}
                
                # Job 3: Alpha Cycle (AF3 + AF4)
                if now - self.last_alpha_run >= SCHEDULER_CONFIG["alpha_cycle_interval_sec"]:
                    print(f"[Scheduler] Running alpha cycle (AF3 + AF4)...")
                    
                    result = self.jobs.run_alpha_cycle()
                    self.last_alpha_result = result
                    self.last_alpha_run = now
                    
                    if result.get("ok"):
                        print(f"[Scheduler] Alpha cycle: AF3={result.get('af3_symbols', 0)} symbols, AF4={result.get('af4_entry_modes', 0)} modes, {result.get('total_actions', 0)} actions submitted")
                    else:
                        print(f"[Scheduler] Alpha cycle error: {result.get('error')}")
                        self.last_error = {"job": "alpha_cycle", "error": result.get("error"), "timestamp": datetime.now(timezone.utc).isoformat()}
            
            except Exception as e:
                print(f"[Scheduler] Unexpected error in loop: {e}")
                self.last_error = {"job": "loop", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Sleep for 1 second before next check
            time.sleep(1)
        
        print("[Scheduler] Loop stopped")
