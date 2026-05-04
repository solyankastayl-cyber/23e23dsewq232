"""
Execution Queue Routes (P1.3)
==============================

Endpoints для управления и мониторинга execution queue.

Тестовые endpoints:
- POST /ops/execution-queue/test-enqueue - тест создания job
- GET /ops/execution-queue/metrics - метрики очереди
- GET /ops/execution-queue/job/{jobId} - детали job
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/execution-queue", tags=["P1.3 Execution Queue"])


# ========================================
# Request Models
# ========================================

class TestEnqueueRequest(BaseModel):
    """Test enqueue request payload."""
    symbol: str
    action: str = "GO_FULL"
    confidence: float = 0.8
    trace_id: Optional[str] = None
    payload: dict = {}


# ========================================
# Test Endpoints
# ========================================

@router.post("/test-enqueue")
async def test_enqueue(request_body: TestEnqueueRequest, request: Request):
    """
    Test endpoint для создания execution job.
    
    Используется для проверки:
    - job создаётся в Mongo
    - trace_id корректно проходит
    - priority корректно вычисляется
    """
    # Get repo from app state
    repo = getattr(request.app.state, "execution_queue_repo", None)
    
    if not repo:
        raise HTTPException(
            status_code=503,
            detail="ExecutionQueueRepository not initialized"
        )
    
    try:
        result = await repo.enqueue(
            symbol=request_body.symbol,
            exchange="binance",
            action=request_body.action,
            payload=request_body.payload,
            trace_id=request_body.trace_id,
            confidence=request_body.confidence
        )
        
        return {
            "ok": True,
            "data": result,
            "message": "Job enqueued successfully" if result.get("accepted") else "Job rejected"
        }
    
    except Exception as e:
        logger.error(f"[P1.3 Test] Enqueue error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/metrics")
async def get_queue_metrics(request: Request):
    """
    Get execution queue metrics.
    
    Returns:
    - Counts by status (queued, leased, in_flight, acked, etc.)
    - Zombie jobs count (expired leases)
    """
    # Get repo from app state
    repo = getattr(request.app.state, "execution_queue_repo", None)
    
    if not repo:
        raise HTTPException(
            status_code=503,
            detail="ExecutionQueueRepository not initialized"
        )
    
    try:
        metrics = await repo.get_metrics()
        
        return {
            "ok": True,
            "data": metrics
        }
    
    except Exception as e:
        logger.error(f"[P1.3 Metrics] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/job/{job_id}")
async def get_job_details(job_id: str, request: Request):
    """
    Get execution job details by jobId.
    
    Returns:
    - Full job document from Mongo
    - Current status, lease info, payload, etc.
    """
    # Get repo from app state
    repo = getattr(request.app.state, "execution_queue_repo", None)
    
    if not repo:
        raise HTTPException(
            status_code=503,
            detail="ExecutionQueueRepository not initialized"
        )
    
    try:
        job = await repo.get_job(job_id)
        
        if not job:
            return {
                "ok": False,
                "error": f"Job not found: {job_id}"
            }
        
        return {
            "ok": True,
            "data": job.dict()
        }
    
    except Exception as e:
        logger.error(f"[P1.3 Job] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }
