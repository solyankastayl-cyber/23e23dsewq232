"""
Trace Diagnostic Routes (P1.3.1D)
==================================

Эндпоинты для trace reconstruction и consistency analysis.

Endpoints:
- GET /ops/execution-trace/{traceId} - полный causal graph по trace_id
- GET /ops/execution-shadow/consistency - consistency metrics
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
import os

from modules.execution_reality.integration.execution_shadow_diff_repository import (
    get_execution_shadow_diff_repo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", tags=["P1.3.1D Trace Diagnostic"])


@router.get("/execution-trace/{trace_id}")
async def get_execution_trace(trace_id: str):
    """
    GET /ops/execution-trace/{traceId}
    
    Полный causal graph reconstruction:
    - Decision audit
    - Strategy audit  
    - Execution audit
    - Learning audit (если есть)
    - Queue jobs (если есть)
    - Shadow diff (если есть)
    - Summary (queueCreated, legacyExecuted, match, severity)
    
    Returns:
        {
            "trace_id": str,
            "summary": {...},
            "decision": {...} or null,
            "strategy": [...] or null,
            "execution": [...] or null,
            "learning": [...] or null,
            "queue_jobs": [...] or null,
            "shadow_diff": {...} or null
        }
    """
    try:
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        # 1. Decision Audit
        decision_doc = await db["decision_audit"].find_one({"traceId": trace_id})
        
        # 2. Strategy Audit (может быть несколько)
        strategy_docs = []
        async for doc in db["strategy_audit"].find({"traceId": trace_id}):
            strategy_docs.append({
                "source": doc.get("source"),
                "action": doc.get("action"),
                "timestamp": doc.get("timestamp")
            })
        
        # 3. Execution Audit (может быть несколько событий)
        execution_docs = []
        async for doc in db["execution_audit"].find({"traceId": trace_id}):
            # Извлекаем события из execution_events массива
            events = doc.get("execution_events", [])
            for event in events:
                execution_docs.append({
                    "event_type": event.get("event_type"),
                    "timestamp": event.get("timestamp"),
                    "payload": event.get("payload")
                })
        
        # 4. Learning Audit (если есть)
        learning_doc = await db["learning_audit"].find_one({"traceId": trace_id})
        
        # 5. Queue Jobs (execution_jobs)
        queue_jobs = []
        async for doc in db["execution_jobs"].find({"traceId": trace_id}):
            queue_jobs.append({
                "jobId": doc.get("jobId"),
                "status": doc.get("status"),
                "priority": doc.get("priority"),
                "attemptCount": doc.get("attemptCount"),
                "createdAt": doc.get("createdAt"),
                "updatedAt": doc.get("updatedAt")
            })
        
        # 6. Shadow Diff
        diff_repo = get_execution_shadow_diff_repo()
        shadow_diff = None
        
        if diff_repo:
            diff_doc = await diff_repo.get_by_trace_id(trace_id)
            if diff_doc:
                shadow_diff = {
                    "match": diff_doc.match,
                    "severity": diff_doc.severity,
                    "diff": diff_doc.diff,
                    "queueIntent": diff_doc.queueIntent.dict() if diff_doc.queueIntent else None,
                    "legacyIntent": diff_doc.legacyIntent.dict() if diff_doc.legacyIntent else None
                }
        
        # 7. Build Summary
        queue_created = len(queue_jobs) > 0
        legacy_executed = len(execution_docs) > 0
        match = shadow_diff.get("match") if shadow_diff else None
        severity = shadow_diff.get("severity") if shadow_diff else None
        
        summary = {
            "queueCreated": queue_created,
            "legacyExecuted": legacy_executed,
            "match": match,
            "severity": severity,
            "hasDecision": decision_doc is not None,
            "hasStrategy": len(strategy_docs) > 0,
            "hasExecution": legacy_executed,
            "hasLearning": learning_doc is not None
        }
        
        client.close()
        
        return {
            "ok": True,
            "trace_id": trace_id,
            "summary": summary,
            "decision": {
                "symbol": decision_doc.get("symbol"),
                "timeframe": decision_doc.get("timeframe"),
                "action": decision_doc.get("action"),
                "confidence": decision_doc.get("confidence"),
                "blocked": decision_doc.get("blocked"),
                "timestamp": decision_doc.get("timestamp")
            } if decision_doc else None,
            "strategy": strategy_docs if strategy_docs else None,
            "execution": execution_docs if execution_docs else None,
            "learning": {
                "outcome": learning_doc.get("outcome"),
                "timestamp": learning_doc.get("timestamp")
            } if learning_doc else None,
            "queue_jobs": queue_jobs if queue_jobs else None,
            "shadow_diff": shadow_diff
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1D Trace] Error fetching trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-shadow/consistency")
async def get_shadow_consistency(limit: int = 100):
    """
    GET /ops/execution-shadow/consistency?limit=100
    
    Consistency metrics для shadow integration.
    
    Args:
        limit: Количество последних diff-ов для анализа (default: 100)
    
    Returns:
        {
            "total": int,
            "match_rate": float,
            "mismatch_rate": float,
            "by_severity": {
                "CRITICAL": int,
                "HIGH": int,
                "MEDIUM": int,
                "LOW": int,
                "NONE": int
            },
            "top_fields": {
                "quantity": int,
                "price": int,
                ...
            }
        }
    """
    try:
        diff_repo = get_execution_shadow_diff_repo()
        
        if not diff_repo:
            raise HTTPException(
                status_code=503,
                detail="ExecutionShadowDiffRepository not initialized"
            )
        
        # Get consistency metrics
        metrics = await diff_repo.get_consistency_metrics(limit=limit)
        
        return {
            "ok": True,
            **metrics
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[P1.3.1D Consistency] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
