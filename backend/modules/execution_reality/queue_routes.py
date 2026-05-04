"""
Queue Routes (P1.1)
===================

API endpoints for queue observability.
"""

from fastapi import APIRouter, Query, Request
from typing import List
from datetime import datetime, timezone
from .queue.queue_models import QueueMetrics, DLQItem

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/metrics", response_model=QueueMetrics)
async def get_queue_metrics(request: Request):
    """
    Get current queue metrics (P1.1B: persistent queue).
    
    Returns:
        - queue_depth: Tasks in PENDING status
        - processing_count: Tasks in PROCESSING status
        - retry_count: (deprecated, always 0 for persistent queue)
        - dlq_count: Tasks in Dead Letter Queue
        - avg_wait_ms: Average wait time (placeholder)
        - avg_processing_ms: Average processing time (placeholder)
        - workers_active: Active workers
        - workers_total: Total workers
    """
    # Access controller from app state
    if not hasattr(request.app.state, 'execution_reality_controller'):
        return QueueMetrics(
            queue_depth=0,
            processing_count=0,
            retry_count=0,
            dlq_count=0,
            avg_wait_ms=0.0,
            avg_processing_ms=0.0,
            workers_active=0,
            workers_total=0,
            timestamp=datetime.now(timezone.utc)
        )
    
    controller = request.app.state.execution_reality_controller
    
    if not controller.persistent_queue:
        return QueueMetrics(
            queue_depth=0,
            processing_count=0,
            retry_count=0,
            dlq_count=0,
            avg_wait_ms=0.0,
            avg_processing_ms=0.0,
            workers_active=0,
            workers_total=0,
            timestamp=datetime.now(timezone.utc)
        )
    
    # Get metrics from persistent queue
    queue_metrics = await controller.persistent_queue.get_metrics()
    
    # Update DLQ count from repository
    dlq_count = 0
    if controller.dlq_repository:
        dlq_count = await controller.dlq_repository.count()
    
    # Get worker counts from worker pool
    workers_active = 0
    workers_total = 0
    if hasattr(request.app.state, 'worker_pool'):
        worker_pool = request.app.state.worker_pool
        workers_active = worker_pool.get_active_workers_count()
        workers_total = worker_pool.get_total_workers_count()
    
    return QueueMetrics(
        queue_depth=queue_metrics.get("pending", 0),
        processing_count=queue_metrics.get("processing", 0),
        retry_count=0,  # Not applicable for persistent queue (retry = return to PENDING)
        dlq_count=dlq_count,
        avg_wait_ms=0.0,  # TODO: implement latency tracking (P1.3)
        avg_processing_ms=0.0,  # TODO: implement latency tracking (P1.3)
        workers_active=workers_active,
        workers_total=workers_total,
        timestamp=datetime.now(timezone.utc),
        last_error=None
    )


@router.get("/dlq", response_model=List[DLQItem])
async def get_dlq_items(
    request: Request,
    limit: int = Query(default=100, le=1000, description="Max items to return")
):
    """
    Get Dead Letter Queue items.
    
    Args:
        limit: Maximum number of items to return (max 1000)
    
    Returns:
        List of failed queue items with error details
    """
    if not hasattr(request.app.state, 'execution_reality_controller'):
        return []
    
    controller = request.app.state.execution_reality_controller
    
    if not controller.dlq_repository:
        return []
    
    dlq_items = await controller.dlq_repository.list_recent(limit=limit)
    
    return dlq_items


@router.get("/dlq/by-trace/{trace_id}", response_model=List[DLQItem])
async def get_dlq_by_trace(request: Request, trace_id: str):
    """
    Get DLQ items by trace_id.
    
    Useful for debugging specific decision traces.
    """
    if not hasattr(request.app.state, 'execution_reality_controller'):
        return []
    
    controller = request.app.state.execution_reality_controller
    
    if not controller.dlq_repository:
        return []
    
    dlq_items = await controller.dlq_repository.get_by_trace_id(trace_id)
    
    return dlq_items
