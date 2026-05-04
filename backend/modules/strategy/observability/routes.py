"""
Health API Routes
==================

Phase 2.8: Independent API layer for system health monitoring.

ARCHITECTURE NOTE:
  This router is DECOUPLED from experiments router.
  Health is observability - it must be stable and independent.

Endpoints:
  GET /api/health  - Get system health status
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
import os

logger = logging.getLogger(__name__)

# Independent router
router = APIRouter(
    prefix="/api/health",
    tags=["Phase 2.8 - Health"]
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
async def get_health(
    experiment_id: str = "market_dynamic",
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get system health status.
    
    Monitors for degradation, jitter, and bias in the discovery system.
    
    Args:
        experiment_id: Experiment ID (default: market_dynamic)
    
    Returns:
        {
            "ok": True,
            "health_status": "healthy" | "degraded" | "unhealthy",
            "active_alerts": [
                {
                    "type": str,
                    "severity": "info" | "warning" | "critical",
                    "message": str,
                    "context": {...}
                }
            ]
        }
    """
    try:
        from modules.strategy.observability.health_service import HealthService
        
        service = HealthService(db)
        health_data = await service.get_system_health(experiment_id)
        
        return {
            "ok": True,
            **health_data
        }
    except Exception as e:
        logger.error(f"[HealthAPI] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
