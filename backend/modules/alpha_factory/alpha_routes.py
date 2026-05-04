"""
AF1 - Alpha Factory Routes
==========================
FastAPI router for Alpha Factory endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from .alpha_repository import AlphaRepository
from .alpha_factory_engine import AlphaFactoryEngine
from .alpha_query_service import AlphaQueryService


router = APIRouter(tags=["Alpha Factory"])

# Singleton instances
_repo = AlphaRepository()
_engine = AlphaFactoryEngine(_repo)
_query = AlphaQueryService(_repo)


# === Helper to load trades from TT4 ===

def _load_trades(symbol: Optional[str] = None) -> List[dict]:
    """Load trades from TT4 Forensics module"""
    try:
        from ..trading_terminal.forensics.forensics_routes import _repo as trades_repo
        items = trades_repo.list_all(symbol=symbol.upper() if symbol else None)
        return [x.to_dict() for x in items]
    except Exception as e:
        print(f"[AlphaFactory] Error loading trades: {e}")
        return []


# === Main Endpoints ===

@router.post("/api/alpha-factory/run")
async def run_alpha_factory(symbol: Optional[str] = Query(None)):
    """
    Run Alpha Factory analysis.
    
    Loads trades from TT4, computes metrics, evaluations, and generates actions.
    """
    try:
        trades = _load_trades(symbol=symbol)
        
        if not trades:
            return {
                "ok": True,
                "warning": "No trades found",
                "data": {
                    "metrics": {"symbol": [], "entry_mode": []},
                    "evaluations": {"symbol": [], "entry_mode": []},
                    "actions": [],
                    "trades_analyzed": 0,
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        result = _engine.run(trades, symbol=symbol)
        
        return {
            "ok": True,
            "data": result.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alpha-factory/summary")
async def get_alpha_summary():
    """Get Alpha Factory summary for dashboard"""
    try:
        summary = _engine.get_summary()
        
        return {
            "ok": True,
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Metrics Endpoints ===

@router.get("/api/alpha-factory/metrics/symbols")
async def get_symbol_metrics():
    """Get metrics for all symbols"""
    try:
        return {
            "ok": True,
            "data": _query.get_metrics("symbol"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alpha-factory/metrics/entry-modes")
async def get_entry_mode_metrics():
    """Get metrics for all entry modes"""
    try:
        return {
            "ok": True,
            "data": _query.get_metrics("entry_mode"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Evaluations Endpoints ===

@router.get("/api/alpha-factory/evaluations/symbols")
async def get_symbol_evaluations():
    """Get edge evaluations for all symbols"""
    try:
        return {
            "ok": True,
            "data": _query.get_evaluations("symbol"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alpha-factory/evaluations/entry-modes")
async def get_entry_mode_evaluations():
    """Get edge evaluations for all entry modes"""
    try:
        return {
            "ok": True,
            "data": _query.get_evaluations("entry_mode"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Actions Endpoints ===

@router.get("/api/alpha-factory/actions")
async def get_actions():
    """Get all generated actions"""
    try:
        return {
            "ok": True,
            "data": _query.get_actions(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alpha-factory/actions/pending")
async def get_pending_actions():
    """Get actions that need attention (not KEEP)"""
    try:
        return {
            "ok": True,
            "data": _query.get_pending_actions(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Recommendations ===

@router.get("/api/alpha-factory/recommendation/{scope}/{scope_key}")
async def get_recommendation(scope: str, scope_key: str):
    """Get specific recommendation for a scope/key"""
    try:
        result = _engine.get_recommendation(scope, scope_key.upper())
        
        if not result.get("found"):
            return {
                "ok": True,
                "warning": "Not found",
                "data": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/alpha-factory/symbol/{symbol}")
async def get_symbol_status(symbol: str):
    """Get Alpha Factory status for specific symbol"""
    try:
        status = _query.get_symbol_status(symbol.upper())
        
        return {
            "ok": True,
            "data": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Apply Actions (Bridge to Adaptive Layer) ===

@router.post("/api/alpha-factory/apply")
async def apply_actions():
    """
    Apply generated actions through Adaptive Layer.
    
    This bridges Alpha Factory → Adaptive Layer for actual system changes.
    """
    try:
        actions = _query.get_pending_actions()
        
        if not actions:
            return {
                "ok": True,
                "message": "No pending actions to apply",
                "applied": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Try to apply through Adaptive Layer
        try:
            from ..adaptive.action_application.action_application_engine import ActionApplicationEngine
            
            adaptive_engine = ActionApplicationEngine()
            
            # Convert Alpha actions to Adaptive format
            adaptive_actions = []
            for a in actions:
                adaptive_actions.append({
                    "type": a["action"],
                    "scope": a["scope"],
                    "target": a["scope_key"],
                    "magnitude": a["magnitude"],
                    "reason": a["reason"],
                    "source": "alpha_factory",
                    "priority": a["priority"],
                    "auto_apply": a["auto_apply"],
                })
            
            result = adaptive_engine.apply_batch(adaptive_actions)
            
            return {
                "ok": True,
                "message": "Actions applied through Adaptive Layer",
                "actions": actions,
                "adaptive_result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except ImportError:
            # Adaptive Layer not available - return actions for manual handling
            return {
                "ok": True,
                "warning": "Adaptive Layer not available",
                "message": "Actions generated but not applied",
                "actions": actions,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Terminal State Integration ===

@router.get("/api/alpha-factory/for-terminal-state")
async def get_for_terminal_state():
    """Get Alpha Factory data formatted for terminal state"""
    try:
        data = _query.format_for_terminal_state()
        
        return {
            "ok": True,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Reset (Dev/Test) ===

@router.post("/api/alpha-factory/reset")
async def reset_alpha_factory():
    """Reset Alpha Factory data"""
    try:
        _repo.clear()
        
        return {
            "ok": True,
            "message": "Alpha Factory reset",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Export service for orchestrator ===

def get_alpha_service():
    """Get Alpha Factory service for integration"""
    return {
        "repo": _repo,
        "engine": _engine,
        "query": _query,
    }
