"""
Meta Layer API Routes - ORCH-7
================================

API endpoints for meta-layer strategy management.
"""

from fastapi import APIRouter
from typing import Dict, Any
import logging

from .meta_controller import get_meta_controller
from .strategy_registry import get_strategy_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meta", tags=["Meta Layer - ORCH-7"])


@router.get("/strategies")
async def list_strategies():
    """List all registered strategies."""
    try:
        registry = get_strategy_registry()
        strategies = registry.list_all()
        
        return {
            "ok": True,
            "strategies": strategies,
            "count": len(strategies),
        }
    except Exception as e:
        logger.error(f"[MetaRoutes] Error listing strategies: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get specific strategy details."""
    try:
        registry = get_strategy_registry()
        strategy = registry.get(strategy_id)
        
        if not strategy:
            return {"ok": False, "error": f"Strategy {strategy_id} not found"}
        
        return {
            "ok": True,
            "strategy": strategy,
        }
    except Exception as e:
        logger.error(f"[MetaRoutes] Error getting strategy: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/strategies/{strategy_id}/enable")
async def enable_strategy(strategy_id: str):
    """Enable a strategy."""
    try:
        registry = get_strategy_registry()
        registry.enable(strategy_id)
        
        return {
            "ok": True,
            "strategy_id": strategy_id,
            "status": "enabled",
        }
    except Exception as e:
        logger.error(f"[MetaRoutes] Error enabling strategy: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/strategies/{strategy_id}/disable")
async def disable_strategy(strategy_id: str):
    """Disable a strategy."""
    try:
        registry = get_strategy_registry()
        registry.disable(strategy_id)
        
        return {
            "ok": True,
            "strategy_id": strategy_id,
            "status": "disabled",
        }
    except Exception as e:
        logger.error(f"[MetaRoutes] Error disabling strategy: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/state")
async def get_meta_state():
    """
    Get current meta-layer state.
    
    This is a READ-ONLY endpoint that shows current allocations
    WITHOUT affecting execution.
    """
    try:
        # For now, return mock data
        # In PHASE 3-4 this will be integrated with real metrics
        
        return {
            "ok": True,
            "meta": {
                "scores": [],
                "allocations": [],
                "actions": [],
                "total_capital": 0.0,
            },
            "note": "PHASE 1-2: Meta layer created but not yet integrated with execution"
        }
    except Exception as e:
        logger.error(f"[MetaRoutes] Error getting meta state: {e}")
        return {"ok": False, "error": str(e)}



@router.post("/test/trigger-strategy-audit")
async def test_trigger_strategy_audit(trace_id: str = None):
    """
    P0.7 TEST: Force trigger strategy audit for verification.
    Creates test strategy actions to verify audit logging.
    """
    import uuid
    from datetime import datetime, timezone
    
    try:
        controller = get_meta_controller()
        
        if not controller.audit_controller:
            return {"ok": False, "error": "Audit controller not initialized"}
        
        # Generate trace_id if not provided
        test_trace_id = trace_id or f"test-strategy-{uuid.uuid4()}"
        
        # Create test strategy actions
        test_actions = [
            {
                "strategy_id": "test_strategy_1",
                "type": "BOOST_STRATEGY",
                "reason": "test_trigger_verification",
                "confidence": 0.8,
                "source": "TEST_FORCE",
                "score": 0.75
            },
            {
                "strategy_id": "test_strategy_2",  
                "type": "REDUCE_STRATEGY",
                "reason": "test_trigger_verification",
                "confidence": 0.6,
                "source": "TEST_FORCE",
                "score": 0.45
            }
        ]
        
        # Log to strategy audit
        from modules.audit.audit_helper import run_audit_task
        for action in test_actions:
            run_audit_task(
                controller.audit_controller.strategy.insert({
                    "timestamp": datetime.now(timezone.utc),
                    "trace_id": test_trace_id,
                    "strategy_id": action["strategy_id"],
                    "action_type": action["type"],
                    "reason": action["reason"],
                    "confidence": action["confidence"],
                    "source": action["source"],
                    "score": action.get("score")
                }),
                context=f"test_strategy_audit_{action['strategy_id']}"
            )
        
        logger.info(f"[P0.7 TEST] Strategy audit triggered | trace={test_trace_id}")
        
        return {
            "ok": True,
            "trace_id": test_trace_id,
            "actions_triggered": len(test_actions),
            "message": "Strategy audit test triggered successfully"
        }
    except Exception as e:
        logger.error(f"[MetaRoutes] Error in test trigger: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}
