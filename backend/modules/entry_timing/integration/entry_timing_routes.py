"""
PHASE 4.5 + 4.8.1 — Entry Timing Integration Routes

API endpoints for the unified Entry Timing Stack
with MTF and Microstructure support.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .entry_timing_integration import get_entry_timing_integration


router = APIRouter(prefix="/api/entry-timing/integration", tags=["entry-timing-integration"])


class PredictionInput(BaseModel):
    direction: str
    confidence: float = 0.5
    tradeable: bool = True


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
    reason: Optional[str] = None
    legs: List[Dict] = []


class EntryQualityInput(BaseModel):
    entry_quality_score: float
    entry_quality_grade: str
    reasons: List[str] = []


class MTFContextInput(BaseModel):
    decision: str = ""
    confidence: float = 0.5


class MicroContextInput(BaseModel):
    entry_permission: bool = True
    microstructure_score: float = 0.5
    liquidity_risk: float = 0.2
    sweep_risk: float = 0.2
    absorption_detected: bool = False
    imbalance: str = "neutral"
    decision: str = "ENTER_NOW"
    reasons: List[str] = []


class ContextInput(BaseModel):
    trigger_level: Optional[float] = None
    extension_atr: Optional[float] = None
    close_confirmation: Optional[bool] = None
    retest_completed: Optional[bool] = None
    ltf_alignment: Optional[str] = None
    volatility_state: Optional[str] = None
    structure_acceptance: Optional[bool] = None


class DiagnosticsInput(BaseModel):
    top_wrong_early_reasons: List[str] = []


class EvaluateInput(BaseModel):
    prediction: PredictionInput
    setup: SetupInput
    entry_mode: EntryModeInput
    execution_strategy: ExecutionStrategyInput
    entry_quality: EntryQualityInput
    mtf: Optional[MTFContextInput] = None
    microstructure: Optional[MicroContextInput] = None


class FullPipelineInput(BaseModel):
    prediction: PredictionInput
    setup: SetupInput
    context: ContextInput
    diagnostics: Optional[DiagnosticsInput] = None
    mtf: Optional[MTFContextInput] = None
    microstructure: Optional[MicroContextInput] = None


@router.get("/health")
async def integration_health():
    """Health check for entry timing integration."""
    engine = get_entry_timing_integration()
    return engine.health_check()


@router.post("/evaluate")
async def evaluate_integration(data: EvaluateInput):
    """
    Evaluate final entry decision from pre-computed components.

    Now supports optional MTF and Microstructure context.
    """
    engine = get_entry_timing_integration()

    input_dict = {
        "prediction": data.prediction.dict(),
        "setup": data.setup.dict(),
        "entry_mode": data.entry_mode.dict(),
        "execution_strategy": data.execution_strategy.dict(),
        "entry_quality": data.entry_quality.dict(),
        "mtf": data.mtf.dict() if data.mtf else {},
        "microstructure": data.microstructure.dict() if data.microstructure else {},
    }

    result = engine.evaluate(input_dict)

    return {"ok": True, **result}


@router.post("/full-pipeline")
async def evaluate_full_pipeline(data: FullPipelineInput):
    """
    Run full Entry Timing Stack pipeline with optional MTF + Microstructure.
    """
    engine = get_entry_timing_integration()

    input_dict = {
        "prediction": data.prediction.dict(),
        "setup": data.setup.dict(),
        "context": {k: v for k, v in data.context.dict().items() if v is not None},
        "diagnostics": data.diagnostics.dict() if data.diagnostics else {},
        "mtf": data.mtf.dict() if data.mtf else {},
        "microstructure": data.microstructure.dict() if data.microstructure else {},
    }

    result = engine.evaluate_full_pipeline(input_dict)

    return {"ok": True, **result}


@router.get("/decisions")
async def get_decision_types():
    """Get all final decision types (now includes micro-aware decisions)."""
    engine = get_entry_timing_integration()
    types = engine.get_decision_types()

    return {
        "ok": True,
        **types,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stats")
async def get_stats():
    """Get decision statistics."""
    engine = get_entry_timing_integration()
    stats = engine.get_stats()

    return {"ok": True, **stats, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent decision history."""
    engine = get_entry_timing_integration()
    history = engine.get_history(limit)

    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
