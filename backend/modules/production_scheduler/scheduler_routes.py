"""
Scheduler Routes

PHASE 41.1 — Production Infrastructure

Endpoints:
- GET  /api/v1/scheduler/status       - Scheduler status
- GET  /api/v1/scheduler/tasks        - List tasks
- POST /api/v1/scheduler/start        - Start scheduler
- POST /api/v1/scheduler/stop         - Stop scheduler
- POST /api/v1/scheduler/run/{task}   - Run task manually
- POST /api/v1/scheduler/enable/{task}  - Enable task
- POST /api/v1/scheduler/disable/{task} - Disable task
- GET  /api/v1/scheduler/health       - Health check
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from .scheduler_engine import get_scheduler


router = APIRouter(prefix="/api/v1/scheduler", tags=["Production Scheduler"])


@router.get("/status")
async def get_status():
    """Get scheduler status."""
    try:
        sched = get_scheduler()
        s = sched.get_status()

        return {
            "status": "ok",
            "phase": "41",
            "scheduler": {
                "running": s.running,
                "task_count": s.task_count,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "uptime_seconds": s.uptime_seconds,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "interval_seconds": t.interval_seconds,
                        "enabled": t.enabled,
                        "run_count": t.run_count,
                        "error_count": t.error_count,
                        "last_run": t.last_run.isoformat() if t.last_run else None,
                        "avg_duration_ms": round(t.avg_duration_ms, 2),
                    }
                    for t in s.tasks
                ],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def get_tasks():
    """List all scheduled tasks."""
    try:
        sched = get_scheduler()
        tasks = sched.get_tasks()

        return {
            "status": "ok",
            "phase": "41",
            "count": len(tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "interval_seconds": t.interval_seconds,
                    "enabled": t.enabled,
                    "run_count": t.run_count,
                    "error_count": t.error_count,
                    "last_error": t.last_error,
                }
                for t in tasks
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler():
    """Start the scheduler."""
    try:
        sched = get_scheduler()
        await sched.start()
        return {"status": "ok", "phase": "41", "message": "Scheduler started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """Stop the scheduler."""
    try:
        sched = get_scheduler()
        await sched.stop()
        return {"status": "ok", "phase": "41", "message": "Scheduler stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{task_id}")
async def run_task(task_id: str):
    """Run a single task manually."""
    try:
        sched = get_scheduler()
        result = await sched.run_task(task_id)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))

        return {"status": "ok", "phase": "41", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable/{task_id}")
async def enable_task(task_id: str):
    """Enable a scheduled task."""
    try:
        sched = get_scheduler()
        success = sched.enable_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"status": "ok", "phase": "41", "task_id": task_id, "enabled": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable/{task_id}")
async def disable_task(task_id: str):
    """Disable a scheduled task."""
    try:
        sched = get_scheduler()
        success = sched.disable_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"status": "ok", "phase": "41", "task_id": task_id, "enabled": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def scheduler_health():
    """Scheduler health check."""
    try:
        sched = get_scheduler()
        s = sched.get_status()

        return {
            "status": "ok",
            "phase": "41",
            "module": "Production Scheduler",
            "running": s.running,
            "task_count": s.task_count,
            "endpoints": [
                "GET  /api/v1/scheduler/status",
                "GET  /api/v1/scheduler/tasks",
                "POST /api/v1/scheduler/start",
                "POST /api/v1/scheduler/stop",
                "POST /api/v1/scheduler/run/{task_id}",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
