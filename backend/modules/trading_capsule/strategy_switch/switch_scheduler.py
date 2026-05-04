"""
Switch Scheduler (STR3)
=======================

Scheduler for time-based strategy switches.

Features:
- Schedule evaluation loop
- Auto-revert scheduling
- Cron-like scheduling support
"""

import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
import uuid

from .switch_types import (
    SwitchPolicy,
    SwitchTriggerType,
    PolicyStatus,
    SwitchContext,
    ActiveProfileState
)
from .switch_policy_registry import get_policies_by_type, get_enabled_policies


class ScheduledTask:
    """A scheduled task for execution"""
    
    def __init__(
        self,
        task_id: str,
        execute_at: datetime,
        callback: Callable,
        args: tuple = (),
        kwargs: dict = None,
        description: str = ""
    ):
        self.task_id = task_id
        self.execute_at = execute_at
        self.callback = callback
        self.args = args
        self.kwargs = kwargs or {}
        self.description = description
        self.executed = False
        self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "execute_at": self.execute_at.isoformat() if self.execute_at else None,
            "description": self.description,
            "executed": self.executed,
            "created_at": self.created_at.isoformat()
        }


class SwitchScheduler:
    """
    Scheduler for strategy switches.
    
    Handles:
    - Schedule-based switches
    - Auto-revert scheduling
    - Periodic evaluation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Scheduled tasks
        self._tasks: Dict[str, ScheduledTask] = {}
        
        # Background thread
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callback for switch execution
        self._switch_callback: Optional[Callable] = None
        
        # Evaluation interval (seconds)
        self._eval_interval = 60  # Every minute
        
        self._initialized = True
        print("[SwitchScheduler] Initialized")
    
    # ===========================================
    # Scheduler Control
    # ===========================================
    
    def start(self, switch_callback: Callable) -> None:
        """
        Start the scheduler background thread.
        
        Args:
            switch_callback: Function to call when switch should happen
                             Signature: callback(target_profile: str, reason: str, policy_id: str)
        """
        if self._running:
            return
        
        self._switch_callback = switch_callback
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[SwitchScheduler] Started background scheduler")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[SwitchScheduler] Stopped")
    
    def _run_loop(self) -> None:
        """Background scheduler loop"""
        while self._running:
            try:
                # Execute due tasks
                self._execute_due_tasks()
                
                # Evaluate schedules
                self._evaluate_schedules()
                
            except Exception as e:
                print(f"[SwitchScheduler] Error in loop: {e}")
            
            time.sleep(self._eval_interval)
    
    # ===========================================
    # Task Management
    # ===========================================
    
    def schedule_task(
        self,
        execute_at: datetime,
        callback: Callable,
        args: tuple = (),
        kwargs: dict = None,
        description: str = ""
    ) -> str:
        """
        Schedule a task for future execution.
        
        Returns:
            Task ID
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        task = ScheduledTask(
            task_id=task_id,
            execute_at=execute_at,
            callback=callback,
            args=args,
            kwargs=kwargs or {},
            description=description
        )
        
        self._tasks[task_id] = task
        print(f"[SwitchScheduler] Scheduled task {task_id} for {execute_at.isoformat()}")
        
        return task_id
    
    def schedule_revert(
        self,
        revert_at: datetime,
        target_profile: str,
        reason: str = "Auto-revert"
    ) -> str:
        """
        Schedule an auto-revert to a profile.
        
        Returns:
            Task ID
        """
        if not self._switch_callback:
            print("[SwitchScheduler] No switch callback registered")
            return ""
        
        return self.schedule_task(
            execute_at=revert_at,
            callback=self._switch_callback,
            args=(target_profile, reason, "auto_revert"),
            description=f"Auto-revert to {target_profile}"
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            print(f"[SwitchScheduler] Cancelled task {task_id}")
            return True
        return False
    
    def _execute_due_tasks(self) -> None:
        """Execute tasks that are due"""
        now = datetime.now(timezone.utc)
        due_tasks = [
            t for t in self._tasks.values()
            if not t.executed and t.execute_at <= now
        ]
        
        for task in due_tasks:
            try:
                task.callback(*task.args, **task.kwargs)
                task.executed = True
                print(f"[SwitchScheduler] Executed task {task.task_id}: {task.description}")
            except Exception as e:
                print(f"[SwitchScheduler] Error executing task {task.task_id}: {e}")
        
        # Cleanup executed tasks older than 1 hour
        cutoff = now - timedelta(hours=1)
        self._tasks = {
            k: v for k, v in self._tasks.items()
            if not v.executed or v.execute_at > cutoff
        }
    
    # ===========================================
    # Schedule Evaluation
    # ===========================================
    
    def _evaluate_schedules(self) -> None:
        """Evaluate schedule-based policies"""
        if not self._switch_callback:
            return
        
        schedule_policies = get_policies_by_type(SwitchTriggerType.SCHEDULE)
        
        for policy in schedule_policies:
            if policy.status != PolicyStatus.ENABLED:
                continue
            
            if policy.schedule and policy.schedule.is_active():
                # Check cooldown
                if policy.last_triggered:
                    cooldown_delta = datetime.now(timezone.utc) - policy.last_triggered
                    if cooldown_delta.total_seconds() < policy.cooldown_minutes * 60:
                        continue
                
                # Trigger switch
                try:
                    self._switch_callback(
                        policy.target_profile,
                        f"Scheduled: {policy.name}",
                        policy.policy_id
                    )
                    policy.last_triggered = datetime.now(timezone.utc)
                except Exception as e:
                    print(f"[SwitchScheduler] Error executing schedule {policy.name}: {e}")
    
    # ===========================================
    # Queries
    # ===========================================
    
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get all pending (not executed) tasks"""
        return [t for t in self._tasks.values() if not t.executed]
    
    def get_next_scheduled_event(self) -> Optional[ScheduledTask]:
        """Get the next scheduled task"""
        pending = self.get_pending_tasks()
        if not pending:
            return None
        
        return min(pending, key=lambda t: t.execute_at)
    
    def get_active_schedules(self) -> List[Dict[str, Any]]:
        """Get currently active schedule policies"""
        schedule_policies = get_policies_by_type(SwitchTriggerType.SCHEDULE)
        
        active = []
        for policy in schedule_policies:
            if policy.status == PolicyStatus.ENABLED and policy.schedule:
                is_active = policy.schedule.is_active()
                active.append({
                    "policy_id": policy.policy_id,
                    "name": policy.name,
                    "target_profile": policy.target_profile,
                    "schedule": policy.schedule.to_dict(),
                    "is_currently_active": is_active
                })
        
        return active
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get scheduler health status"""
        pending = len(self.get_pending_tasks())
        next_task = self.get_next_scheduled_event()
        
        return {
            "service": "SwitchScheduler",
            "status": "healthy" if self._running else "stopped",
            "version": "str3",
            "running": self._running,
            "pending_tasks": pending,
            "next_execution": next_task.execute_at.isoformat() if next_task else None,
            "eval_interval_seconds": self._eval_interval
        }


# Global singleton
switch_scheduler = SwitchScheduler()
