"""
Learning Routes - AF6

API endpoints for learning system.
Provides outcome registration and metrics access.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning", tags=["Real Learning Engine - AF6"])

_learning_engine = None
_outcome_engine = None


def init_learning(learning_engine, outcome_engine):
    """
    Initialize learning routes with engines.
    
    Args:
        learning_engine: RealLearningEngine instance
        outcome_engine: TradeOutcomeEngine instance
    """
    global _learning_engine, _outcome_engine
    _learning_engine = learning_engine
    _outcome_engine = outcome_engine
    logger.info("[LearningRoutes] Initialized learning API routes")


def get_learning_engine():
    """Get learning engine instance (P0.7 audit hook helper)"""
    return _learning_engine


class OutcomeRequest(BaseModel):
    """Outcome registration request model."""
    trade_id: str
    symbol: str
    timeframe: str
    entry_mode: str
    regime: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    mae: float = 0.0
    mfe: float = 0.0
    duration_sec: int = 0
    exit_reason: str = "MANUAL"
    wrong_early: bool = False


@router.post("/outcome")
async def register_outcome(request: OutcomeRequest):
    """
    Register a trade outcome.
    
    POST /api/learning/outcome
    """
    try:
        # Build outcome
        outcome = _outcome_engine.build(**request.dict())
        
        # Register and classify
        classified = _learning_engine.register_outcome(outcome)
        
        return {"ok": True, "outcome": classified}
    
    except Exception as e:
        logger.error(f"[LearningRoutes] Error registering outcome: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metrics")
async def get_metrics():
    """
    Run learning cycle and get metrics.
    
    GET /api/learning/metrics
    
    Returns full learning cycle result:
    - outcomes_count
    - metrics (by symbol/mode/regime)
    - actions (adaptive actions generated)
    - applied (actions applied to override registry)
    """
    try:
        result = _learning_engine.run_cycle()
        return result
    
    except Exception as e:
        logger.error(f"[LearningRoutes] Error computing metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outcomes")
async def get_outcomes():
    """
    List all registered outcomes.
    
    GET /api/learning/outcomes
    """
    try:
        outcomes = _learning_engine.registry.list_all()
        return {"outcomes": outcomes, "count": len(outcomes)}
    
    except Exception as e:
        logger.error(f"[LearningRoutes] Error listing outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary():
    """
    Get learning system summary.
    
    GET /api/learning/summary
    
    Returns compact summary for UI display.
    """
    try:
        summary = _learning_engine.get_summary()
        return summary
    
    except Exception as e:
        logger.error(f"[LearningRoutes] Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/test/trigger-learning-audit")
async def test_trigger_learning_audit(trace_id: str = None):
    """
    P0.7 TEST: Force trigger learning audit for verification.
    Creates test learning cycle data to verify audit logging.
    """
    import uuid
    from datetime import datetime, timezone
    
    try:
        if not _learning_engine:
            return {"ok": False, "error": "Learning engine not initialized"}
        
        if not _learning_engine.audit_controller:
            return {"ok": False, "error": "Audit controller not initialized"}
        
        # Generate trace_id if not provided
        test_trace_id = trace_id or f"test-learning-{uuid.uuid4()}"
        
        # Create test learning data
        test_metrics = {
            "overall": {
                "win_rate": 0.65,
                "avg_pnl": 125.0,
                "total_pnl": 500.0
            },
            "by_entry_mode": {
                "AGGRESSIVE": {"win_rate": 0.70},
                "PASSIVE": {"win_rate": 0.60}
            }
        }
        
        test_actions_generated = [
            {
                "type": "BOOST_STRATEGY",
                "strategy_id": "test_momentum_v1",
                "reason": "test_high_win_rate",
                "confidence": 0.85
            }
        ]
        
        test_actions_applied = {
            "alpha_actions": ["BOOST_STRATEGY"],
            "regime_actions": [],
            "total_count": 1
        }
        
        # Log to learning audit
        from modules.audit.audit_helper import run_audit_task
        run_audit_task(
            _learning_engine.audit_controller.learning.insert({
                "timestamp": datetime.now(timezone.utc),
                "trace_id": test_trace_id,
                "outcomes_count": 10,
                "metrics_snapshot": test_metrics,
                "actions_generated": test_actions_generated,
                "actions_applied": test_actions_applied
            }),
            context="test_learning_audit"
        )
        
        logger.info(f"[P0.7 TEST] Learning audit triggered | trace={test_trace_id}")
        
        return {
            "ok": True,
            "trace_id": test_trace_id,
            "message": "Learning audit test triggered successfully"
        }
    except Exception as e:
        logger.error(f"[LearningRoutes] Error in test trigger: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}
