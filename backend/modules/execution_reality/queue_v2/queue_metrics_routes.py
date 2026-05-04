"""
Execution Queue Metrics Routes (P1.3.2 Operational Correctness)
================================================================

Production-ready observability endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/execution-queue", tags=["P1.3.2 Queue Metrics"])


@router.get("/metrics")
async def get_queue_metrics():
    """
    GET /ops/execution-queue/metrics
    
    Production-ready queue metrics.
    
    Returns:
        {
            "queued": int,
            "leased": int,
            "in_flight": int,
            "acked": int,
            "retry_wait": int,
            "failed_terminal": int,
            "dead_letter": int,
            "total": int
        }
    """
    try:
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        # Aggregation pipeline
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        metrics = {
            "queued": 0,
            "leased": 0,
            "in_flight": 0,
            "acked": 0,
            "retry_wait": 0,
            "failed_terminal": 0,
            "dead_letter": 0
        }
        
        # Execute aggregation
        cursor = db["execution_jobs"].aggregate(pipeline)
        
        async for doc in cursor:
            status = doc.get("_id")
            count = doc.get("count", 0)
            
            if status in metrics:
                metrics[status] = count
        
        # Calculate total
        metrics["total"] = sum(metrics.values())
        
        client.close()
        
        return {
            "ok": True,
            **metrics
        }
    
    except Exception as e:
        logger.error(f"[QueueMetrics] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zombies")
async def get_zombie_jobs():
    """
    GET /ops/execution-queue/zombies
    
    Detect stuck jobs (zombie detection).
    
    P1.3.3: Enhanced in_flight suspicious detection.
    
    Returns:
        {
            "leased_expired": [...],
            "in_flight_suspicious": [...]
        }
    """
    try:
        from datetime import datetime, timezone, timedelta
        
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        now = datetime.now(timezone.utc)
        
        # 1. Leased jobs with expired lease
        leased_expired = []
        async for doc in db["execution_jobs"].find({
            "status": "leased",
            "leaseExpiresAt": {"$lt": now}
        }):
            leased_expired.append({
                "jobId": doc.get("jobId"),
                "symbol": doc.get("symbol"),
                "leaseOwner": doc.get("leaseOwner"),
                "leaseExpiresAt": doc.get("leaseExpiresAt").isoformat() if doc.get("leaseExpiresAt") else None,
                "attemptCount": doc.get("attemptCount")
            })
        
        # 2. P1.3.3: In-flight suspicious (stuck > max_in_flight_time)
        max_in_flight_time = timedelta(seconds=120)  # 2 minutes hard limit
        suspicious_threshold = now - max_in_flight_time
        
        in_flight_suspicious = []
        async for doc in db["execution_jobs"].find({
            "status": "in_flight",
            "updatedAt": {"$lt": suspicious_threshold}
        }):
            stuck_duration = (now - doc.get("updatedAt")).total_seconds()
            in_flight_suspicious.append({
                "jobId": doc.get("jobId"),
                "symbol": doc.get("symbol"),
                "leaseOwner": doc.get("leaseOwner"),
                "attemptCount": doc.get("attemptCount"),
                "stuckDuration": f"{stuck_duration:.0f}s",
                "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None
            })
        
        client.close()
        
        return {
            "ok": True,
            "leased_expired": leased_expired,
            "in_flight_suspicious": in_flight_suspicious,
            "zombie_count": len(leased_expired) + len(in_flight_suspicious)
        }
    
    except Exception as e:
        logger.error(f"[ZombieDetection] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-enqueue")
async def bulk_enqueue_test(n: int = 100):
    """
    POST /ops/execution-queue/bulk-enqueue?n=100
    
    Bulk enqueue test (stress test).
    
    Args:
        n: Number of jobs to enqueue (default 100)
    
    Returns:
        {
            "jobs_created": int,
            "trace_ids": [...]
        }
    """
    try:
        import uuid
        from modules.execution_reality.queue_v2.execution_dispatch_service import (
            get_execution_dispatch_service
        )
        
        dispatch_service = get_execution_dispatch_service()
        
        if not dispatch_service:
            raise HTTPException(
                status_code=503,
                detail="ExecutionDispatchService not initialized"
            )
        
        trace_ids = []
        jobs_created = 0
        
        for i in range(n):
            trace_id = str(uuid.uuid4())
            
            # Synthetic gate_result
            gate_result = {
                "blocked": False,
                "final_action": "GO_FULL",
                "decision_enforced": {
                    "action": "GO_FULL",
                    "direction": "LONG",
                    "confidence": 0.8
                },
                "size_multiplier": 1.0,
                "reason_chain": [f"bulk_test_{i}"]
            }
            
            # Synthetic execution_plan
            execution_plan = {
                "action": "GO_FULL",
                "side": "BUY",
                "size": 0.001,
                "entry": 65000 + (i * 10),  # Vary price slightly
                "stop": 64000,
                "target": 66000,
                "route_type": "paper",
                "account_id": "test_account"
            }
            
            # Dispatch
            result = await dispatch_service.dispatch(
                symbol=f"BTCUSDT",
                gate_result=gate_result,
                execution_plan=execution_plan,
                trace_id=trace_id
            )
            
            if result.get("dispatched"):
                jobs_created += 1
                trace_ids.append(trace_id)
        
        logger.info(
            f"✅ [BulkEnqueue] Created {jobs_created}/{n} jobs"
        )
        
        return {
            "ok": True,
            "requested": n,
            "jobs_created": jobs_created,
            "trace_ids": trace_ids[:10]  # Return first 10 for verification
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[BulkEnqueue] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-trail/{job_id}")
async def get_job_audit_trail(job_id: str):
    """
    GET /ops/execution-queue/audit-trail/{jobId}
    
    Get complete audit trail for a job.
    
    Returns:
        {
            "job_id": str,
            "events": [
                {
                    "event_type": str,
                    "timestamp": str,
                    "payload": {...}
                }
            ]
        }
    """
    try:
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        events = []
        
        # Find all audit events for this job
        async for doc in db["execution_queue_audit"].find(
            {"jobId": job_id}
        ).sort("createdAt", 1):
            events.append({
                "event_type": doc.get("eventType"),
                "timestamp": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
                "status": doc.get("status"),
                "metadata": doc.get("metadata")
            })
        
        client.close()
        
        return {
            "ok": True,
            "job_id": job_id,
            "events": events,
            "event_count": len(events)
        }
    
    except Exception as e:
        logger.error(f"[AuditTrail] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
