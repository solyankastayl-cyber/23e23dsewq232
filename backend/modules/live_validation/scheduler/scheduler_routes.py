"""
Scheduler Routes
=================
FastAPI endpoints for V2 Validation Scheduler control.

Endpoints:
- POST /api/validation/scheduler/start - Start the scheduler
- POST /api/validation/scheduler/stop - Stop the scheduler
- GET /api/validation/scheduler/status - Get scheduler status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from .validation_scheduler import ValidationScheduler


router = APIRouter(prefix="/api/validation/scheduler", tags=["validation-scheduler"])


# Global scheduler instance (initialized in server.py)
_scheduler: Optional[ValidationScheduler] = None


def init_scheduler(scheduler: ValidationScheduler):
    """
    Initialize the global scheduler instance.
    
    Called from server.py during startup.
    
    Args:
        scheduler: ValidationScheduler instance
    """
    global _scheduler
    _scheduler = scheduler
    print("[Scheduler Routes] Scheduler routes initialized")


def get_scheduler() -> ValidationScheduler:
    """Get the global scheduler instance."""
    if _scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized. Server may still be starting up."
        )
    return _scheduler


# ============ Control Endpoints ============

@router.post("/start")
async def start_scheduler():
    """
    Start the validation scheduler.
    
    Starts the background thread that runs:
    - Shadow trade creation (every 60s)
    - Validation execution (every 120s)
    - Alpha cycles: AF3 + AF4 (every 300s)
    
    Returns:
        Status and configuration
    """
    try:
        scheduler = get_scheduler()
        result = scheduler.start()
        
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """
    Stop the validation scheduler.
    
    Stops the background thread gracefully.
    
    Returns:
        Status confirmation
    """
    try:
        scheduler = get_scheduler()
        result = scheduler.stop()
        
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scheduler_status():
    """
    Get current scheduler status.
    
    Returns detailed information:
    - Running state
    - Configuration (intervals, limits)
    - Last run timestamps for each job
    - Last results for each job
    - Job execution statistics
    - Last error (if any)
    
    Returns:
        Comprehensive scheduler status
    """
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        
        return {
            "ok": True,
            "data": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Configuration Endpoints ============

class UpdateConfigRequest(BaseModel):
    shadow_creation_interval_sec: Optional[int] = None
    validation_interval_sec: Optional[int] = None
    alpha_cycle_interval_sec: Optional[int] = None
    max_shadow_per_cycle: Optional[int] = None
    symbols_limit: Optional[int] = None
    verbose_logging: Optional[bool] = None


@router.post("/config/update")
async def update_scheduler_config(request: UpdateConfigRequest):
    """
    Update scheduler configuration.
    
    Note: Changes take effect on next scheduler cycle.
    Restart scheduler for immediate effect.
    
    Args:
        request: Configuration updates
    
    Returns:
        Updated configuration
    """
    try:
        from .scheduler_config import SCHEDULER_CONFIG, update_config
        
        # Build updates dict from request
        updates = {}
        if request.shadow_creation_interval_sec is not None:
            updates["shadow_creation_interval_sec"] = request.shadow_creation_interval_sec
        if request.validation_interval_sec is not None:
            updates["validation_interval_sec"] = request.validation_interval_sec
        if request.alpha_cycle_interval_sec is not None:
            updates["alpha_cycle_interval_sec"] = request.alpha_cycle_interval_sec
        if request.max_shadow_per_cycle is not None:
            updates["max_shadow_per_cycle"] = request.max_shadow_per_cycle
        if request.symbols_limit is not None:
            updates["symbols_limit"] = request.symbols_limit
        if request.verbose_logging is not None:
            updates["verbose_logging"] = request.verbose_logging
        
        # Update configuration
        update_config(updates)
        
        return {
            "ok": True,
            "data": {
                "updated_keys": list(updates.keys()),
                "current_config": SCHEDULER_CONFIG.copy()
            },
            "message": "Configuration updated. Restart scheduler for immediate effect.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_scheduler_config():
    """
    Get current scheduler configuration.
    
    Returns:
        Current configuration
    """
    try:
        from .scheduler_config import get_config
        
        return {
            "ok": True,
            "data": get_config(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Health Endpoint ============

@router.get("/health")
async def get_scheduler_health():
    """
    Check scheduler health.
    
    Returns:
        Health status and basic info
    """
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        
        return {
            "ok": True,
            "data": {
                "status": "operational" if scheduler else "not_initialized",
                "running": status.get("running", False),
                "last_error": status.get("last_error"),
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        return {
            "ok": False,
            "data": {"status": "not_initialized"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
