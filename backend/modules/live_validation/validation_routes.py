"""
Live Validation Routes - FastAPI endpoints for validation layer
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .shadow_trade_repository import ShadowTradeRepository
from .validation_engine import ValidationEngine
from .validation_query_service import ValidationQueryService


router = APIRouter(prefix="/api/validation", tags=["validation"])

# Global instances
_repo = ShadowTradeRepository()
_engine = ValidationEngine(_repo)
_query = ValidationQueryService(_repo)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ Pydantic Models ============

class CreateShadowTradeRequest(BaseModel):
    terminal_state: dict


class CreateManualShadowTradeRequest(BaseModel):
    symbol: str
    direction: str  # LONG or SHORT
    planned_entry: float
    planned_stop: float
    planned_target: float
    timeframe: str = "4H"
    entry_mode: str = "ENTER_ON_CLOSE"
    decision_action: str = "GO_FULL"


class MarketCandle(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class EvaluateShadowTradeRequest(BaseModel):
    market_path: List[Dict[str, Any]]


class BatchEvaluateRequest(BaseModel):
    shadow_ids: List[str]
    market_paths: Dict[str, List[Dict[str, Any]]]


# ============ Shadow Trade Endpoints ============

@router.post("/shadow/create")
async def create_shadow_trade(request: CreateShadowTradeRequest):
    """Create a shadow trade from terminal state"""
    try:
        item = _engine.create_shadow_trade(request.terminal_state)
        return {
            "ok": True,
            "data": item,
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shadow/create-manual")
async def create_manual_shadow_trade(request: CreateManualShadowTradeRequest):
    """Create a shadow trade manually for testing"""
    try:
        item = _engine.create_shadow_trade_manual(
            symbol=request.symbol,
            direction=request.direction,
            planned_entry=request.planned_entry,
            planned_stop=request.planned_stop,
            planned_target=request.planned_target,
            timeframe=request.timeframe,
            entry_mode=request.entry_mode,
            decision_action=request.decision_action
        )
        return {
            "ok": True,
            "data": item,
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/shadow/recent")
async def get_recent_shadow_trades(symbol: Optional[str] = None, limit: int = 20):
    """Get recent shadow trades"""
    items = _query.get_recent_shadow_trades(symbol=symbol, limit=limit)
    return {
        "ok": True,
        "data": items,
        "count": len(items),
        "timestamp": utc_now()
    }


@router.get("/shadow/pending")
async def get_pending_shadow_trades():
    """Get all pending shadow trades"""
    items = _engine.get_pending_trades()
    return {
        "ok": True,
        "data": items,
        "count": len(items),
        "timestamp": utc_now()
    }


@router.get("/shadow/active")
async def get_active_shadow_trades():
    """Get all active (entered) shadow trades"""
    items = _engine.get_active_trades()
    return {
        "ok": True,
        "data": items,
        "count": len(items),
        "timestamp": utc_now()
    }


@router.get("/shadow/{shadow_id}")
async def get_shadow_trade(shadow_id: str):
    """Get a shadow trade by ID"""
    item = _engine.get_shadow_trade(shadow_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shadow trade not found")
    return {
        "ok": True,
        "data": item,
        "timestamp": utc_now()
    }


@router.post("/shadow/{shadow_id}/cancel")
async def cancel_shadow_trade(shadow_id: str):
    """Cancel a shadow trade"""
    item = _engine.cancel_shadow_trade(shadow_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shadow trade not found or already processed")
    return {
        "ok": True,
        "data": item,
        "timestamp": utc_now()
    }


# ============ Evaluation Endpoints ============

@router.post("/shadow/{shadow_id}/evaluate")
async def evaluate_shadow_trade(shadow_id: str, request: EvaluateShadowTradeRequest):
    """Evaluate a shadow trade against market path"""
    try:
        result = _engine.validate_shadow_trade(shadow_id, request.market_path)
        return {
            "ok": True,
            "data": result,
            "timestamp": utc_now()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shadow/evaluate-batch")
async def evaluate_batch(request: BatchEvaluateRequest):
    """Evaluate multiple shadow trades"""
    try:
        results = _engine.validate_batch(request.shadow_ids, request.market_paths)
        return {
            "ok": True,
            "data": results,
            "count": len(results),
            "timestamp": utc_now()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Results Endpoints ============

@router.get("/results/recent")
async def get_recent_results(symbol: Optional[str] = None, limit: int = 20):
    """Get recent validation results"""
    items = _query.get_recent_results(symbol=symbol, limit=limit)
    return {
        "ok": True,
        "data": items,
        "count": len(items),
        "timestamp": utc_now()
    }


@router.get("/results/{shadow_id}")
async def get_validation_result(shadow_id: str):
    """Get validation result for a shadow trade"""
    result = _engine.get_validation_result(shadow_id)
    if not result:
        raise HTTPException(status_code=404, detail="Validation result not found")
    return {
        "ok": True,
        "data": result,
        "timestamp": utc_now()
    }


# ============ Metrics Endpoints ============

@router.get("/metrics")
async def get_validation_metrics(symbol: Optional[str] = None):
    """Get aggregated validation metrics"""
    metrics = _engine.build_metrics(symbol=symbol)
    return {
        "ok": True,
        "data": metrics,
        "timestamp": utc_now()
    }


@router.get("/metrics/by-symbol")
async def get_metrics_by_symbol():
    """Get validation metrics breakdown by symbol"""
    breakdown = _engine.build_symbol_breakdown()
    return {
        "ok": True,
        "data": breakdown,
        "timestamp": utc_now()
    }


# ============ Summary Endpoints ============

@router.get("/summary")
async def get_validation_summary():
    """Get validation summary"""
    summary = _query.get_summary()
    return {
        "ok": True,
        "data": summary,
        "timestamp": utc_now()
    }


@router.get("/stats")
async def get_validation_stats():
    """Get validation statistics"""
    stats = _engine.get_stats()
    return {
        "ok": True,
        "data": stats,
        "timestamp": utc_now()
    }


@router.get("/combined/recent")
async def get_combined_recent(symbol: Optional[str] = None, limit: int = 20):
    """Get recent shadow trades with their validation results"""
    items = _query.get_combined_recent(symbol=symbol, limit=limit)
    return {
        "ok": True,
        "data": items,
        "count": len(items),
        "timestamp": utc_now()
    }


# ============ Admin Endpoints ============

@router.post("/reset")
async def reset_validation():
    """Reset all validation data"""
    _engine.reset()
    return {
        "ok": True,
        "message": "Validation data reset",
        "timestamp": utc_now()
    }
