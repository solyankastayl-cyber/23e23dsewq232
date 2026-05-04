"""
PHASE 3.4 — Scheduler Routes

API endpoints for scheduler control:
- POST /api/adaptive/scheduler/start — Start scheduler
- POST /api/adaptive/scheduler/stop — Stop scheduler
- GET /api/adaptive/scheduler/status — Get scheduler status
- POST /api/adaptive/scheduler/run-once — Run single job
- GET /api/adaptive/scheduler/history — Get job history
- GET /api/adaptive/scheduler/config — Get config
- POST /api/adaptive/scheduler/config — Update config
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel

from .adaptive_scheduler import get_scheduler
from .job_runner import JobType


router = APIRouter(prefix="/api/adaptive/scheduler", tags=["scheduler"])


class ConfigUpdate(BaseModel):
    """Scheduler config update."""
    calibration_interval_hours: Optional[int] = None
    apply_interval_hours: Optional[int] = None
    health_check_interval_minutes: Optional[int] = None
    auto_apply_enabled: Optional[bool] = None
    auto_rollback_enabled: Optional[bool] = None
    working_hours_only: Optional[bool] = None


@router.get("/health")
async def scheduler_health():
    """Health check for scheduler module."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    return {
        "ok": True,
        "module": "scheduler",
        "version": "3.4",
        "running": status.running,
        "jobs_executed": status.jobs_executed,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/start")
async def start_scheduler():
    """Start the adaptive scheduler."""
    scheduler = get_scheduler()
    
    if scheduler._running:
        return {
            "ok": False,
            "error": "Scheduler already running",
            "status": _status_to_dict(scheduler.get_status())
        }
    
    success = scheduler.start()
    
    return {
        "ok": success,
        "message": "Scheduler started" if success else "Failed to start",
        "status": _status_to_dict(scheduler.get_status())
    }


@router.post("/stop")
async def stop_scheduler():
    """Stop the adaptive scheduler."""
    scheduler = get_scheduler()
    
    if not scheduler._running:
        return {
            "ok": False,
            "error": "Scheduler not running",
            "status": _status_to_dict(scheduler.get_status())
        }
    
    success = scheduler.stop()
    
    return {
        "ok": success,
        "message": "Scheduler stopped" if success else "Failed to stop",
        "status": _status_to_dict(scheduler.get_status())
    }


@router.get("/status")
async def get_scheduler_status():
    """Get current scheduler status."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    return {
        "ok": True,
        **_status_to_dict(status),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/run-once")
async def run_once(
    job_type: str = Query("daily", enum=["daily", "hourly", "weekly", "snapshot", "performance", "rollback_check"])
):
    """Run a specific job once (manual trigger)."""
    scheduler = get_scheduler()
    
    result = scheduler.run_once(job_type)
    
    return {
        "ok": result.status.value == "success",
        "job_type": result.job_type.value,
        "status": result.status.value,
        "duration_seconds": result.duration_seconds,
        "result": result.result,
        "error": result.error,
        "started_at": result.started_at,
        "finished_at": result.finished_at
    }


@router.get("/history")
async def get_job_history(limit: int = Query(20, ge=1, le=100)):
    """Get job execution history."""
    scheduler = get_scheduler()
    history = scheduler.get_job_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "total_jobs_executed": scheduler._jobs_executed
    }


@router.get("/config")
async def get_scheduler_config():
    """Get scheduler configuration."""
    scheduler = get_scheduler()
    
    return {
        "ok": True,
        "config": scheduler.config.to_dict(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/config")
async def update_scheduler_config(update: ConfigUpdate):
    """Update scheduler configuration."""
    scheduler = get_scheduler()
    
    # Get current config
    current = scheduler.config.to_dict()
    
    # Apply updates
    update_dict = update.dict(exclude_none=True)
    current.update(update_dict)
    
    # Apply new config
    scheduler.update_config(current)
    
    return {
        "ok": True,
        "config": scheduler.config.to_dict(),
        "updated_fields": list(update_dict.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/next-jobs")
async def get_next_jobs():
    """Get when next jobs will run."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    return {
        "ok": True,
        "scheduler_running": status.running,
        "next_daily": status.next_daily,
        "next_hourly": status.next_hourly,
        "last_job": {
            "type": status.last_job_type,
            "time": status.last_job_time
        }
    }


# Full pipeline endpoint
@router.post("/run-full-cycle")
async def run_full_cycle(
    use_mock: bool = Query(True, description="Use mock data"),
    include_snapshot: bool = Query(True, description="Create snapshots"),
    include_rollback_check: bool = Query(True, description="Check for rollback")
):
    """
    Run a full adaptive cycle manually.
    
    This is the complete pipeline:
    1. Daily calibration (calibration → policy → apply)
    2. Snapshot (if enabled)
    3. Performance check
    4. Auto-rollback check (if enabled)
    """
    scheduler = get_scheduler()
    results = {}
    
    # Run daily calibration
    daily_result = scheduler.run_once("daily")
    results["daily_calibration"] = {
        "status": daily_result.status.value,
        "result": daily_result.result,
        "error": daily_result.error
    }
    
    # Snapshot if enabled
    if include_snapshot:
        snapshot_result = scheduler.run_once("snapshot")
        results["snapshot"] = {
            "status": snapshot_result.status.value,
            "result": snapshot_result.result
        }
    
    # Performance check
    perf_result = scheduler.run_once("performance")
    results["performance_check"] = {
        "status": perf_result.status.value,
        "result": perf_result.result
    }
    
    # Rollback check if enabled
    if include_rollback_check:
        rollback_result = scheduler.run_once("rollback_check")
        results["rollback_check"] = {
            "status": rollback_result.status.value,
            "result": rollback_result.result
        }
    
    # Overall status
    all_success = all(
        r.get("status") == "success" 
        for r in results.values()
    )
    
    return {
        "ok": all_success,
        "cycle_complete": True,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _status_to_dict(status) -> Dict:
    """Convert SchedulerStatus to dict."""
    return {
        "running": status.running,
        "started_at": status.started_at,
        "jobs_executed": status.jobs_executed,
        "last_job_type": status.last_job_type,
        "last_job_time": status.last_job_time,
        "next_daily": status.next_daily,
        "next_hourly": status.next_hourly,
        "config": status.config
    }
