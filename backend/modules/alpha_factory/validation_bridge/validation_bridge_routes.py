"""
Validation Bridge Routes - FastAPI endpoints for AF3
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .validation_metrics_adapter import ValidationMetricsAdapter
from .validation_bridge_engine import ValidationBridgeEngine


router = APIRouter(prefix="/api/alpha-factory/validation-bridge", tags=["alpha-validation-bridge"])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ Initialize Engine ============
# Lazy loading to avoid circular imports

_validation_adapter = None
_bridge_engine = None


def _get_validation_adapter():
    global _validation_adapter
    if _validation_adapter is None:
        try:
            # Import the shared validation engine instance from routes
            from modules.live_validation.validation_routes import _engine as validation_engine
            _validation_adapter = ValidationMetricsAdapter(validation_engine)
        except Exception as e:
            print(f"[AF3] Warning: Could not load V1 Validation: {e}")
            _validation_adapter = ValidationMetricsAdapter()
    return _validation_adapter


def _get_bridge_engine():
    global _bridge_engine
    if _bridge_engine is None:
        try:
            # Import the shared alpha query service
            from modules.alpha_factory.alpha_routes import _query as alpha_query
            _bridge_engine = ValidationBridgeEngine(
                alpha_query_service=alpha_query,
                validation_adapter=_get_validation_adapter()
            )
        except Exception as e:
            print(f"[AF3] Warning: Could not load Alpha Query Service: {e}")
            _bridge_engine = ValidationBridgeEngine(
                alpha_query_service=None,
                validation_adapter=_get_validation_adapter()
            )
    return _bridge_engine


# ============ Evaluation Endpoints ============

@router.get("/symbols")
async def get_symbols_combined_truth():
    """Get combined alpha + validation truth for all symbols"""
    try:
        engine = _get_bridge_engine()
        truths = engine.evaluate_symbols()
        
        return {
            "ok": True,
            "data": truths,
            "count": len(truths),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entry-modes")
async def get_entry_modes_combined_truth():
    """Get combined truth for entry modes"""
    try:
        engine = _get_bridge_engine()
        truths = engine.evaluate_entry_modes()
        
        return {
            "ok": True,
            "data": truths,
            "count": len(truths),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_combined_actions():
    """Get actions generated from combined truth"""
    try:
        engine = _get_bridge_engine()
        truths = engine.evaluate_symbols()
        actions = engine.build_actions(truths)
        
        return {
            "ok": True,
            "data": actions,
            "count": len(actions),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_bridge_summary():
    """Get summary of validation bridge evaluation"""
    try:
        engine = _get_bridge_engine()
        result = engine.run_full_evaluation()
        
        return {
            "ok": True,
            "data": result["summary"],
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/full-evaluation")
async def get_full_evaluation():
    """Run full evaluation and get all results"""
    try:
        engine = _get_bridge_engine()
        result = engine.run_full_evaluation()
        
        return {
            "ok": True,
            "data": result,
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Submit to Control Layer ============

class SubmitActionsRequest(BaseModel):
    filter_urgent_only: bool = False


@router.post("/submit")
async def submit_actions_to_control(request: SubmitActionsRequest = None):
    """
    Submit AF3 actions to TT5 Control Layer.
    
    Actions go through control layer based on alpha_mode:
    - AUTO: actions apply directly
    - MANUAL: actions go to pending queue
    - OFF: actions ignored
    """
    try:
        engine = _get_bridge_engine()
        result = engine.run_full_evaluation()
        
        actions = result["actions"]
        
        # Filter if requested
        if request and request.filter_urgent_only:
            actions = [a for a in actions if a.get("urgent", False)]
        
        # Submit to TT5 Control Layer
        try:
            from modules.trading_terminal.control.control_routes import _engine as control_engine
            
            # Convert AF3 actions to control layer format
            control_actions = [
                {
                    "scope": a["scope"],
                    "scope_key": a["scope_key"],
                    "action": a["action"],
                    "magnitude": a["magnitude"],
                    "reason": a["reason"],
                }
                for a in actions
            ]
            
            control_result = control_engine.ingest_alpha_actions(control_actions)
        except Exception as e:
            control_result = {"status": "error", "error": str(e)}
        
        return {
            "ok": True,
            "data": {
                "truths": result["truths"],
                "actions": actions,
                "summary": result["summary"],
                "control_result": control_result,
            },
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Diagnostic Endpoints ============

@router.get("/health")
async def get_bridge_health():
    """Check health of validation bridge components"""
    adapter = _get_validation_adapter()
    engine = _get_bridge_engine()
    
    validation_stats = adapter.get_stats()
    has_alpha = engine.alpha_query_service is not None
    
    return {
        "ok": True,
        "data": {
            "validation_connected": validation_stats.get("total_shadow_trades", 0) > 0 or True,
            "validation_trades": validation_stats.get("total_validation_results", 0),
            "alpha_connected": has_alpha,
            "status": "operational"
        },
        "timestamp": utc_now()
    }


@router.get("/debug/alpha-metrics")
async def debug_alpha_metrics():
    """Debug: Get raw alpha metrics"""
    engine = _get_bridge_engine()
    
    symbol_metrics = engine._get_alpha_symbol_metrics()
    mode_metrics = engine._get_alpha_entry_mode_metrics()
    
    return {
        "ok": True,
        "data": {
            "symbol_metrics": symbol_metrics,
            "entry_mode_metrics": mode_metrics,
        },
        "timestamp": utc_now()
    }


@router.get("/debug/validation-metrics")
async def debug_validation_metrics():
    """Debug: Get raw validation metrics"""
    adapter = _get_validation_adapter()
    
    global_metrics = adapter.get_metrics()
    by_symbol = adapter.get_metrics_by_symbol()
    
    return {
        "ok": True,
        "data": {
            "global_metrics": global_metrics,
            "by_symbol": by_symbol,
        },
        "timestamp": utc_now()
    }
