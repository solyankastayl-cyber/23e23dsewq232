"""
Scheduler Engine

PHASE 41.1 — Production Infrastructure

Periodic task scheduler for trading system operations.
Uses asyncio tasks (no Redis dependency in preview).
"""

import asyncio
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ScheduledTask(BaseModel):
    task_id: str
    name: str
    interval_seconds: int
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    avg_duration_ms: float = 0.0


class SchedulerStatus(BaseModel):
    running: bool = False
    task_count: int = 0
    tasks: List[ScheduledTask] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0


class SchedulerEngine:
    """
    Production scheduler for periodic tasks.
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._started_at: Optional[datetime] = None
        self._async_tasks: Dict[str, asyncio.Task] = {}

        self._init_default_tasks()

    def _init_default_tasks(self):
        """Register default periodic tasks."""
        defaults = [
            ("circuit_breaker_check", "Circuit Breaker Check", 5),
            ("risk_budget_recompute", "Risk Budget Recompute", 30),
            ("dashboard_state_refresh", "Dashboard State Refresh", 10),
            ("alerts_check", "Alerts Check", 15),
            ("regime_update", "Regime Update", 60),
            ("fractal_recompute", "Fractal Recompute", 60),
            ("reflexivity_update", "Reflexivity Update", 60),
            ("memory_update", "Memory Update", 60),
        ]

        for task_id, name, interval in defaults:
            self._tasks[task_id] = ScheduledTask(
                task_id=task_id,
                name=name,
                interval_seconds=interval,
            )

        # Register handlers
        self._handlers["circuit_breaker_check"] = self._run_circuit_breaker_check
        self._handlers["risk_budget_recompute"] = self._run_risk_budget_recompute
        self._handlers["dashboard_state_refresh"] = self._run_dashboard_refresh
        self._handlers["alerts_check"] = self._run_alerts_check

    # ═══════════════════════════════════════════════════════════
    # Task Management
    # ═══════════════════════════════════════════════════════════

    def register_task(self, task_id: str, name: str, interval: int, handler: Callable):
        self._tasks[task_id] = ScheduledTask(
            task_id=task_id, name=name, interval_seconds=interval
        )
        self._handlers[task_id] = handler

    def enable_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            return True
        return False

    def get_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks.values())

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    # ═══════════════════════════════════════════════════════════
    # Start / Stop
    # ═══════════════════════════════════════════════════════════

    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        self._running = True
        self._started_at = datetime.now(timezone.utc)

        for task_id, task in self._tasks.items():
            if task.enabled and task_id in self._handlers:
                self._async_tasks[task_id] = asyncio.create_task(
                    self._task_loop(task_id)
                )

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        for t in self._async_tasks.values():
            t.cancel()
        self._async_tasks.clear()

    async def _task_loop(self, task_id: str):
        """Run a single task in a loop."""
        task = self._tasks[task_id]
        handler = self._handlers.get(task_id)

        while self._running and task.enabled:
            try:
                start = datetime.now(timezone.utc)

                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()

                duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                task.run_count += 1
                task.last_run = datetime.now(timezone.utc)
                task.avg_duration_ms = (
                    (task.avg_duration_ms * (task.run_count - 1) + duration_ms) / task.run_count
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                task.error_count += 1
                task.last_error = str(e)

            await asyncio.sleep(task.interval_seconds)

    # ═══════════════════════════════════════════════════════════
    # Run Single Task
    # ═══════════════════════════════════════════════════════════

    async def run_task(self, task_id: str) -> Dict[str, Any]:
        """Manually run a single task."""
        if task_id not in self._tasks:
            return {"success": False, "error": f"Task {task_id} not found"}

        handler = self._handlers.get(task_id)
        if not handler:
            return {"success": False, "error": f"No handler for task {task_id}"}

        try:
            start = datetime.now(timezone.utc)
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

            task = self._tasks[task_id]
            task.run_count += 1
            task.last_run = datetime.now(timezone.utc)

            return {"success": True, "task_id": task_id, "duration_ms": duration_ms}
        except Exception as e:
            self._tasks[task_id].error_count += 1
            self._tasks[task_id].last_error = str(e)
            return {"success": False, "task_id": task_id, "error": str(e)}

    # ═══════════════════════════════════════════════════════════
    # Status
    # ═══════════════════════════════════════════════════════════

    def get_status(self) -> SchedulerStatus:
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now(timezone.utc) - self._started_at).total_seconds()

        return SchedulerStatus(
            running=self._running,
            task_count=len(self._tasks),
            tasks=list(self._tasks.values()),
            started_at=self._started_at,
            uptime_seconds=uptime,
        )

    # ═══════════════════════════════════════════════════════════
    # Default Task Handlers
    # ═══════════════════════════════════════════════════════════

    def _run_circuit_breaker_check(self):
        try:
            from modules.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
            cb.run_checks()
        except Exception:
            pass

    def _run_risk_budget_recompute(self):
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            engine.get_portfolio_risk_budget()
        except Exception:
            pass

    def _run_dashboard_refresh(self):
        try:
            from modules.control_dashboard import get_dashboard_engine
            engine = get_dashboard_engine()
            engine.build_multi_dashboard()
        except Exception:
            pass

    def _run_alerts_check(self):
        try:
            from modules.control_dashboard import get_alerts_engine
            engine = get_alerts_engine()
            engine.run_all_checks()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_scheduler: Optional[SchedulerEngine] = None


def get_scheduler() -> SchedulerEngine:
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerEngine()
    return _scheduler
