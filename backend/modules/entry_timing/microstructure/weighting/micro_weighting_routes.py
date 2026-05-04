"""
PHASE 4.8.3 — Micro Weighting Routes

API endpoints for microstructure weighting evaluation.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .micro_weighting_engine import get_micro_weighting_engine


router = APIRouter(
    prefix="/api/entry-timing/microstructure/weight",
    tags=["microstructure-weighting"],
)


class PredictionCtx(BaseModel):
    confidence: float = 0.5


class MicroCtx(BaseModel):
    entry_permission: bool = True
    microstructure_score: float = 0.5
    liquidity_risk: float = 0.2
    sweep_risk: float = 0.2
    absorption_detected: bool = False
    imbalance: str = "neutral"
    imbalance_supportive: bool = False
    decision: str = "ENTER_NOW"


class WeightingInput(BaseModel):
    prediction: PredictionCtx
    microstructure: MicroCtx


@router.get("/health")
async def weighting_health():
    """Health check for microstructure weighting."""
    engine = get_micro_weighting_engine()
    return engine.health_check()


@router.post("/evaluate")
async def evaluate_weighting(data: WeightingInput):
    """
    Compute microstructure weighting: size, confidence, execution modifiers.
    """
    engine = get_micro_weighting_engine()
    input_dict = {
        "prediction": data.prediction.dict(),
        "microstructure": data.microstructure.dict(),
    }
    result = engine.evaluate(input_dict)

    return {"ok": True, **result}


@router.get("/stats")
async def weighting_stats():
    """Get weighting statistics."""
    engine = get_micro_weighting_engine()
    stats = engine.get_stats()
    return {"ok": True, **stats, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/history")
async def weighting_history(limit: int = Query(50, ge=1, le=200)):
    """Get weighting history."""
    engine = get_micro_weighting_engine()
    history = engine.get_history(limit)
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
