"""
PHASE 4.3 — Execution Strategy Routes

API endpoints for execution strategy selection.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .entry_execution_strategy import get_execution_strategy_engine


router = APIRouter(prefix="/api/entry-timing/execution", tags=["execution-strategy"])


class PredictionInput(BaseModel):
    direction: str
    confidence: float = 0.5
    tradeable: bool = True


class SetupInput(BaseModel):
    entry: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None


class ContextInput(BaseModel):
    extension_atr: Optional[float] = None
    retest_level: Optional[float] = None
    volatility_state: Optional[str] = None


class EntryModeInput(BaseModel):
    entry_mode: str
    reason: Optional[str] = None


class SelectInput(BaseModel):
    entry_mode: EntryModeInput
    prediction: PredictionInput
    setup: SetupInput
    context: Optional[ContextInput] = None


@router.get("/health")
async def execution_strategy_health():
    """Health check for execution strategy module."""
    engine = get_execution_strategy_engine()
    return engine.health_check()


@router.post("/select")
async def select_execution_strategy(data: SelectInput):
    """
    Select execution strategy based on entry mode.
    
    Returns execution strategy with concrete order legs.
    """
    engine = get_execution_strategy_engine()
    
    input_dict = {
        "entry_mode": data.entry_mode.dict(),
        "prediction": data.prediction.dict(),
        "setup": data.setup.dict(),
        "context": data.context.dict() if data.context else {}
    }
    
    result = engine.select(input_dict)
    
    return {
        "ok": True,
        **result
    }


@router.get("/types")
async def get_strategy_types():
    """Get all execution strategy types."""
    engine = get_execution_strategy_engine()
    types = engine.get_strategy_types()
    
    return {
        "ok": True,
        **types,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent strategy selection history."""
    engine = get_execution_strategy_engine()
    history = engine.get_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
