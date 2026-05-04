"""
Paper Auto Runner API Routes
==============================

Phase 3.0B: API endpoints for controlled autonomy management.

Endpoints:
  GET  /api/auto-run/status       - Get current status
  POST /api/auto-run/pause        - Pause auto-runner
  POST /api/auto-run/resume       - Resume auto-runner
  POST /api/auto-run/enable       - Enable (clear auto_disabled)
  POST /api/auto-run/disable      - Disable (set auto_disabled)
  GET  /api/auto-run/audit        - Get recent audit logs
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import os

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/api/auto-run",
    tags=["Phase 3.0B - Auto Runner"]
)


def get_state(request: Request):
    """Get auto-runner state from app."""
    if not hasattr(request.app.state, 'paper_auto_runner_state'):
        raise HTTPException(
            status_code=503,
            detail="Auto-runner not initialized"
        )
    return request.app.state.paper_auto_runner_state


async def get_db():
    """Get MongoDB database."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        return db
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database not available: {e}")


@router.get("/status")
async def get_status(request: Request):
    """
    Get auto-runner status.
    
    Returns:
        {
            "ok": True,
            "status": {
                "paused": bool,
                "pause_reason": str | null,
                "auto_disabled": bool,
                "auto_disabled_reason": str | null,
                "last_run_at": str | null,
                "runs_last_hour": int
            }
        }
    """
    try:
        state = get_state(request)
        
        return {
            "ok": True,
            "status": state.get_status()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AutoRunAPI] Status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause(request: Request):
    """
    Pause auto-runner.
    
    Stops scheduler from executing runs.
    Can be resumed via /resume endpoint.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run paused"
        }
    """
    try:
        state = get_state(request)
        state.pause("manual")
        
        logger.info("[AutoRunAPI] Auto-runner paused manually")
        
        return {
            "ok": True,
            "message": "auto-run paused"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AutoRunAPI] Pause error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume(request: Request):
    """
    Resume auto-runner from paused state.
    
    Re-enables scheduler execution.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run resumed"
        }
    """
    try:
        state = get_state(request)
        state.resume()
        
        logger.info("[AutoRunAPI] Auto-runner resumed manually")
        
        return {
            "ok": True,
            "message": "auto-run resumed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AutoRunAPI] Resume error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable")
async def enable(request: Request):
    """
    Enable auto-runner from auto_disabled state.
    
    Clears hard safety auto_disabled flag.
    Use only after fixing underlying issue that caused auto-disable.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run enabled"
        }
    """
    try:
        state = get_state(request)
        state.enable()
        
        logger.warning("[AutoRunAPI] Auto-runner enabled (auto_disabled cleared)")
        
        return {
            "ok": True,
            "message": "auto-run enabled (auto_disabled cleared)"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AutoRunAPI] Enable error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable")
async def disable(request: Request):
    """
    Disable auto-runner (manual safety).
    
    Sets auto_disabled flag to block execution.
    More serious than pause - requires explicit /enable to clear.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run disabled"
        }
    """
    try:
        state = get_state(request)
        state.disable("manual")
        
        logger.warning("[AutoRunAPI] Auto-runner disabled manually")
        
        return {
            "ok": True,
            "message": "auto-run disabled (requires /enable to clear)"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AutoRunAPI] Disable error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit")
async def get_audit(limit: int = 50, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Get recent auto-run audit logs.
    
    Returns recent decisions (executed, skipped, errors).
    
    Args:
        limit: Max logs to return (default: 50)
    
    Returns:
        {
            "ok": True,
            "count": int,
            "logs": [
                {
                    "decision": "AUTO_RUN_EXECUTED" | "AUTO_RUN_SKIPPED" | "AUTO_RUN_ERROR",
                    "reason": str,
                    "timestamp": str,
                    ...
                }
            ]
        }
    """
    try:
        from .audit_logger import AuditLogger
        
        audit = AuditLogger(db)
        logs = await audit.get_recent_logs(
            experiment_id="market_dynamic",
            limit=limit
        )
        
        return {
            "ok": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"[AutoRunAPI] Audit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
