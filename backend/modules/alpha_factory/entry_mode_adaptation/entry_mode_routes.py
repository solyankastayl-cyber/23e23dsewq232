"""
Entry Mode Adaptation Routes - FastAPI endpoints for AF4
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from .entry_mode_adaptation_engine import EntryModeAdaptationEngine
from .entry_mode_query_service import EntryModeQueryService


router = APIRouter(prefix="/api/alpha-factory/entry-modes", tags=["alpha-entry-modes"])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ Initialize Engine ============
_engine = EntryModeAdaptationEngine()
_query = EntryModeQueryService()


def _load_validation_data():
    """Load shadow trades and validation results from V1 validation layer."""
    try:
        from modules.live_validation.validation_routes import _engine as validation_engine
        from modules.live_validation.validation_routes import _repo as validation_repo
        
        shadow_trades = validation_repo.list_shadow_trades(limit=500)
        validation_results = validation_repo.list_validation_results(limit=500)
        
        return shadow_trades, validation_results
    except Exception as e:
        print(f"[AF4] Warning: Could not load validation data: {e}")
        return [], []


# ============ Run Endpoints ============

@router.post("/run")
async def run_entry_mode_adaptation():
    """Run AF4 entry mode adaptation cycle."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        return {
            "ok": True,
            "data": result,
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_entry_mode_metrics():
    """Get metrics per entry mode (without running full evaluation)."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        metrics = _engine.run_metrics_only(shadow_trades, validation_results)
        
        return {
            "ok": True,
            "data": metrics,
            "count": len(metrics),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluations")
async def get_entry_mode_evaluations():
    """Get current evaluations and verdicts."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        return {
            "ok": True,
            "data": result["evaluations"],
            "summary": result["summary"],
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_entry_mode_actions():
    """Get generated actions (without submitting)."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        urgent_actions = _query.get_urgent_actions(result["actions"])
        
        return {
            "ok": True,
            "data": result["actions"],
            "urgent_count": len(urgent_actions),
            "summary": result["summary"],
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_entry_mode_summary():
    """Get summary of entry mode evaluations."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        return {
            "ok": True,
            "data": result["summary"],
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Submit Endpoints ============

class SubmitRequest(BaseModel):
    urgent_only: bool = False


@router.post("/submit")
async def submit_entry_mode_actions(request: SubmitRequest = None):
    """
    Submit AF4 actions to TT5 Control Layer.
    """
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        actions = result["actions"]
        
        # Filter if urgent only
        if request and request.urgent_only:
            actions = _query.get_urgent_actions(actions)
        
        # Submit to TT5 Control Layer
        try:
            from modules.trading_terminal.control.control_routes import _engine as control_engine
            
            control_result = control_engine.ingest_alpha_actions(actions)
        except Exception as e:
            control_result = {"status": "error", "error": str(e)}
        
        return {
            "ok": True,
            "data": {
                "metrics": result["metrics"],
                "evaluations": result["evaluations"],
                "actions": actions,
                "summary": result["summary"],
                "control_result": control_result,
            },
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Query Endpoints ============

@router.get("/broken")
async def get_broken_entry_modes():
    """Get list of broken entry modes."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        broken = _query.get_broken_modes(result["evaluations"])
        
        return {
            "ok": True,
            "data": broken,
            "count": len(broken),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strong")
async def get_strong_entry_modes():
    """Get list of strong entry modes."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        result = _engine.run(shadow_trades, validation_results)
        
        strong = _query.get_strong_modes(result["evaluations"])
        
        return {
            "ok": True,
            "data": strong,
            "count": len(strong),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Health Endpoint ============

@router.get("/health")
async def get_af4_health():
    """Check AF4 health and data availability."""
    try:
        shadow_trades, validation_results = _load_validation_data()
        
        return {
            "ok": True,
            "data": {
                "shadow_trades_available": len(shadow_trades),
                "validation_results_available": len(validation_results),
                "status": "operational" if len(validation_results) > 0 else "no_data"
            },
            "timestamp": utc_now()
        }
    except Exception as e:
        return {
            "ok": False,
            "data": {"status": "error", "error": str(e)},
            "timestamp": utc_now()
        }
