"""
Execution Queue Ops Endpoints (P1.3.1)
=======================================

Операционные endpoints для мониторинга shadow integration.

Endpoints:
- GET /ops/execution-jobs/recent - последние jobs
- GET /ops/execution-jobs/by-trace/{traceId} - jobs по trace_id
- GET /ops/execution-jobs/stats - статистика по статусам
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/execution-jobs", tags=["P1.3.1 Execution Jobs Ops"])


@router.get("/recent")
async def get_recent_jobs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None)
):
    """
    Get recent execution jobs.
    
    Args:
        limit: Number of jobs to return (max 100)
        status: Filter by status (optional)
    
    Returns:
        List of recent jobs
    """
    # Get repo from app state
    repo = getattr(request.app.state, "execution_queue_repo", None)
    
    if not repo:
        raise HTTPException(
            status_code=503,
            detail="ExecutionQueueRepository not initialized"
        )
    
    try:
        # Build query
        query = {}
        if status:
            query["status"] = status
        
        # Find recent jobs
        cursor = repo.collection.find(query).sort("createdAt", -1).limit(limit)
        jobs = await cursor.to_list(length=limit)
        
        return {
            "ok": True,
            "data": {
                "jobs": jobs,
                "count": len(jobs),
                "filter": {"status": status} if status else {}
            }
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1 Ops] Recent jobs error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/by-trace/{trace_id}")
async def get_jobs_by_trace(trace_id: str, request: Request):
    """
    Get all execution jobs by trace_id.
    
    Useful for debugging specific decision traces.
    
    Args:
        trace_id: Causal trace ID
    
    Returns:
        List of jobs with matching trace_id
    """
    # Get repo from app state
    repo = getattr(request.app.state, "execution_queue_repo", None)
    
    if not repo:
        raise HTTPException(
            status_code=503,
            detail="ExecutionQueueRepository not initialized"
        )
    
    try:
        # Find jobs by trace_id
        cursor = repo.collection.find({"traceId": trace_id}).sort("createdAt", 1)
        jobs = await cursor.to_list(length=100)
        
        return {
            "ok": True,
            "data": {
                "traceId": trace_id,
                "jobs": jobs,
                "count": len(jobs)
            }
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1 Ops] Jobs by trace error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/stats")
async def get_job_stats(request: Request, hours: int = Query(default=24, ge=1, le=168)):
    """
    Get execution job statistics for the last N hours.
    
    Args:
        hours: Time window in hours (max 168 = 1 week)
    
    Returns:
        Statistics by status, priority, symbol
    """
    # Get repo from app state
    repo = getattr(request.app.state, "execution_queue_repo", None)
    
    if not repo:
        raise HTTPException(
            status_code=503,
            detail="ExecutionQueueRepository not initialized"
        )
    
    try:
        # Time window
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Count by status
        status_pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        
        status_counts = {
            doc["_id"]: doc["count"]
            async for doc in repo.collection.aggregate(status_pipeline)
        }
        
        # Count by priority
        priority_pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
        ]
        
        priority_counts = {
            doc["_id"]: doc["count"]
            async for doc in repo.collection.aggregate(priority_pipeline)
        }
        
        # Count by symbol
        symbol_pipeline = [
            {"$match": {"createdAt": {"$gte": since}}},
            {"$group": {"_id": "$symbol", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        symbol_counts = {
            doc["_id"]: doc["count"]
            async for doc in repo.collection.aggregate(symbol_pipeline)
        }
        
        # Total count
        total_count = await repo.collection.count_documents({"createdAt": {"$gte": since}})
        
        return {
            "ok": True,
            "data": {
                "timeWindow": f"{hours}h",
                "since": since.isoformat(),
                "total": total_count,
                "byStatus": status_counts,
                "byPriority": priority_counts,
                "topSymbols": symbol_counts
            }
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1 Ops] Job stats error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }
