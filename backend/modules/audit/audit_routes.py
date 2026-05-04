"""Audit Routes - P0.7

API endpoints for audit trail queries.
Provides access to decision, execution, strategy, and learning history.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])

# Глобальный audit_controller (будет проинициализирован в server.py)
_audit_controller = None


def set_audit_controller(controller):
    """Set global audit controller instance"""
    global _audit_controller
    _audit_controller = controller
    logger.info("✅ Audit controller registered in routes")


@router.get("/decisions")
async def get_decisions(limit: int = 50, symbol: Optional[str] = None):
    """
    Get decision audit trail.
    
    Returns every FinalGate decision with:
    - Raw decision
    - Enforced decision
    - Reason chain
    - Portfolio/Meta/Health context
    
    Args:
        limit: Max records (default 50)
        symbol: Filter by symbol (optional)
    
    Returns:
        List of decision audit records
    """
    if not _audit_controller:
        raise HTTPException(status_code=503, detail="Audit controller not initialized")
    
    try:
        records = await _audit_controller.decision.list(limit=limit, symbol=symbol)
        return {
            "ok": True,
            "count": len(records),
            "decisions": records
        }
    except Exception as e:
        logger.error(f"Error fetching decision audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution")
async def get_execution(limit: int = 100, symbol: Optional[str] = None):
    """
    Get execution audit trail.
    
    Returns every execution event:
    - ORDER_SUBMIT_REQUESTED
    - ORDER_ACKNOWLEDGED
    - ORDER_REJECTED
    - ORDER_FILL_RECORDED
    - RECONCILIATION_MISMATCH
    
    Args:
        limit: Max records (default 100)
        symbol: Filter by symbol (optional)
    
    Returns:
        List of execution audit records
    """
    if not _audit_controller:
        raise HTTPException(status_code=503, detail="Audit controller not initialized")
    
    try:
        records = await _audit_controller.execution.list(limit=limit, symbol=symbol)
        return {
            "ok": True,
            "count": len(records),
            "execution_events": records
        }
    except Exception as e:
        logger.error(f"Error fetching execution audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategy_actions(limit: int = 50, strategy_id: Optional[str] = None):
    """
    Get strategy action audit trail.
    
    Returns every meta-level strategy action:
    - DISABLE_STRATEGY
    - CAP_STRATEGY
    - BOOST_STRATEGY
    - REDUCE_STRATEGY
    
    Args:
        limit: Max records (default 50)
        strategy_id: Filter by strategy (optional)
    
    Returns:
        List of strategy action audit records
    """
    if not _audit_controller:
        raise HTTPException(status_code=503, detail="Audit controller not initialized")
    
    try:
        records = await _audit_controller.strategy.list(limit=limit, strategy_id=strategy_id)
        return {
            "ok": True,
            "count": len(records),
            "strategy_actions": records
        }
    except Exception as e:
        logger.error(f"Error fetching strategy action audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning")
async def get_learning(limit: int = 50):
    """
    Get learning audit trail.
    
    Returns every AF6 learning cycle:
    - Metrics snapshot
    - Actions generated
    - Actions applied
    
    Args:
        limit: Max records (default 50)
    
    Returns:
        List of learning audit records
    """
    if not _audit_controller:
        raise HTTPException(status_code=503, detail="Audit controller not initialized")
    
    try:
        records = await _audit_controller.learning.list(limit=limit)
        return {
            "ok": True,
            "count": len(records),
            "learning_cycles": records
        }
    except Exception as e:
        logger.error(f"Error fetching learning audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary():
    """
    Get audit summary statistics.
    
    Returns counts for all audit types.
    """
    if not _audit_controller:
        raise HTTPException(status_code=503, detail="Audit controller not initialized")
    
    try:
        summary = await _audit_controller.get_summary()
        return {
            "ok": True,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error fetching audit summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """
    P0.7+: Get complete causal graph for a trace_id.
    
    Aggregates decision → execution → strategy → learning → errors.
    
    This endpoint answers:
    1. What was the raw decision?
    2. What modified it?
    3. What went to execution?
    4. What happened on exchange?
    5. What learning action resulted?
    6. How did meta state change?
    7. What were the latencies?
    8. Were there errors?
    
    Args:
        trace_id: Trace identifier (UUID)
    
    Returns:
        Complete causal trace with all stages
    """
    if not _audit_controller:
        raise HTTPException(status_code=503, detail="Audit controller not initialized")
    
    try:
        # Aggregate all audit streams for this trace
        decision = await _audit_controller.decision.get_by_trace_id(trace_id)
        execution_events = await _audit_controller.execution.get_by_trace_id(trace_id)
        strategy_actions = await _audit_controller.strategy.get_by_trace_id(trace_id)
        learning = await _audit_controller.learning.get_by_trace_id(trace_id)
        
        # Calculate latency summary
        latency_summary = {}
        if decision and execution_events:
            try:
                decision_ts = decision.get("timestamp")
                first_submit = next(
                    (e for e in execution_events if "SUBMIT" in e.get("event_type", "")), 
                    None
                )
                if first_submit and decision_ts:
                    from datetime import datetime
                    if isinstance(decision_ts, str):
                        decision_ts = datetime.fromisoformat(decision_ts.replace("Z", "+00:00"))
                    submit_ts = first_submit.get("timestamp")
                    if isinstance(submit_ts, str):
                        submit_ts = datetime.fromisoformat(submit_ts.replace("Z", "+00:00"))
                    
                    decision_to_submit_ms = (submit_ts - decision_ts).total_seconds() * 1000
                    latency_summary["decision_to_submit_ms"] = round(decision_to_submit_ms, 2)
            except Exception as e:
                logger.warning(f"Could not calculate latency: {e}")
        
        return {
            "ok": True,
            "trace_id": trace_id,
            "found": decision is not None or len(execution_events) > 0,
            "decision": decision,
            "execution_events": execution_events,
            "strategy_actions": strategy_actions,
            "learning": learning,
            "latency": latency_summary,
            "errors": []  # TODO: error trace logging (Step 3)
        }
    
    except Exception as e:
        logger.error(f"Error fetching trace {trace_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
