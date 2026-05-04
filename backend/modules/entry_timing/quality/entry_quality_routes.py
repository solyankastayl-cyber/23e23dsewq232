"""
PHASE 4.4 — Entry Quality Routes

API endpoints for entry quality scoring.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .entry_quality_engine import get_entry_quality_engine


router = APIRouter(prefix="/api/entry-timing/quality", tags=["entry-quality"])


class PredictionInput(BaseModel):
    direction: str
    confidence: float = 0.5


class SetupInput(BaseModel):
    entry: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    rr: Optional[float] = None


class EntryModeInput(BaseModel):
    entry_mode: str
    reason: Optional[str] = None


class ExecutionStrategyInput(BaseModel):
    execution_strategy: str
    valid: bool = True


class ContextInput(BaseModel):
    trigger_level: Optional[float] = None
    extension_atr: Optional[float] = None
    close_confirmation: Optional[bool] = None
    retest_completed: Optional[bool] = None
    ltf_alignment: Optional[str] = None
    volatility_state: Optional[str] = None
    structure_acceptance: Optional[bool] = None
    expected_slippage_bps: Optional[float] = None


class EvaluateInput(BaseModel):
    prediction: PredictionInput
    setup: SetupInput
    entry_mode: Optional[EntryModeInput] = None
    execution_strategy: Optional[ExecutionStrategyInput] = None
    context: ContextInput


@router.get("/health")
async def entry_quality_health():
    """Health check for entry quality module."""
    engine = get_entry_quality_engine()
    return engine.health_check()


@router.post("/evaluate")
async def evaluate_entry_quality(data: EvaluateInput):
    """
    Evaluate entry quality score.
    
    Returns score 0-1, grade A-F, factors breakdown, and recommendations.
    """
    engine = get_entry_quality_engine()
    
    input_dict = {
        "prediction": data.prediction.dict(),
        "setup": data.setup.dict(),
        "entry_mode": data.entry_mode.dict() if data.entry_mode else {},
        "execution_strategy": data.execution_strategy.dict() if data.execution_strategy else {},
        "context": {k: v for k, v in data.context.dict().items() if v is not None}
    }
    
    result = engine.evaluate(input_dict)
    
    return {
        "ok": True,
        **result
    }


@router.get("/factors")
async def get_factors():
    """Get information about all quality factors."""
    engine = get_entry_quality_engine()
    factors = engine.get_factors_info()
    
    return {
        "ok": True,
        **factors,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent quality evaluation history."""
    engine = get_entry_quality_engine()
    history = engine.get_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
