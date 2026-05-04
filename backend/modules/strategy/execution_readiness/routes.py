"""
Readiness API Routes
=====================

Phase 2.9: Independent API layer for execution readiness gating.

ARCHITECTURE NOTE:
  This router is DECOUPLED from experiments router.
  Readiness is gating logic - it must be stable and independent.

Endpoints:
  GET /api/readiness  - Get execution readiness state
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import os

logger = logging.getLogger(__name__)

# Independent router
router = APIRouter(
    prefix="/api/readiness",
    tags=["Phase 2.9 - Readiness"]
)


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


@router.get("")
async def get_readiness(
    experiment_id: str = "market_dynamic",
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get execution readiness state.
    
    Evaluates health status and applies gating rules to determine
    if system is ready for paper execution.
    
    Args:
        experiment_id: Experiment ID (default: market_dynamic)
    
    Returns:
        {
            "ok": True,
            "state": "ready" | "limited" | "blocked",
            "reason": str,
            "health_status": str,
            "gates": {...}
        }
    
    States:
      - ready: All gates pass → execution allowed
      - limited: Warnings present → execution with caution
      - blocked: Critical issues → execution blocked
    """
    try:
        from modules.strategy.execution_readiness.execution_readiness_service import ExecutionReadinessService
        
        service = ExecutionReadinessService(db)
        readiness_data = await service.get_execution_readiness(experiment_id)
        
        return {
            "ok": True,
            **readiness_data
        }
    except Exception as e:
        logger.error(f"[ReadinessAPI] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
