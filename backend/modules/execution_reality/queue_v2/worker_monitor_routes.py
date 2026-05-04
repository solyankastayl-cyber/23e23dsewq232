"""
Worker Monitor Routes (P1.3.2)
===============================

Мониторинг worker runtime.
"""

import logging
from fastapi import APIRouter, HTTPException
from modules.execution_reality.queue_v2.execution_worker_manager import get_worker_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/worker", tags=["P1.3.2 Worker Monitor"])


@router.get("/stats")
async def get_worker_stats():
    """
    GET /ops/worker/stats
    
    Worker statistics.
    
    Returns:
        {
            "worker_count": int,
            "workers": [
                {
                    "worker_id": str,
                    "status": str,
                    "jobs_processed": int,
                    "current_job": str | null,
                    "last_heartbeat": str
                }
            ]
        }
    """
    try:
        manager = get_worker_manager()
        
        if not manager:
            raise HTTPException(status_code=503, detail="Worker manager not initialized")
        
        stats = await manager.get_worker_stats()
        
        return {
            "ok": True,
            **stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WorkerMonitor] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heartbeats")
async def get_all_heartbeats():
    """
    GET /ops/worker/heartbeats
    
    All worker heartbeats from DB.
    """
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        heartbeats = []
        async for doc in db["worker_heartbeats"].find().sort("lastHeartbeatAt", -1):
            heartbeats.append({
                "workerId": doc.get("workerId"),
                "status": doc.get("status"),
                "lastHeartbeatAt": doc.get("lastHeartbeatAt").isoformat() if doc.get("lastHeartbeatAt") else None,
                "currentJobId": doc.get("currentJobId"),
                "jobsProcessed": doc.get("jobsProcessed"),
                "startedAt": doc.get("startedAt").isoformat() if doc.get("startedAt") else None
            })
        
        client.close()
        
        return {
            "ok": True,
            "heartbeats": heartbeats
        }
    
    except Exception as e:
        logger.error(f"[WorkerMonitor] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
