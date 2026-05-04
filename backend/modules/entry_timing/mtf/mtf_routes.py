"""
PHASE 4.7 — MTF Routes

API endpoints for Multi-Timeframe Entry Timing.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .htf_analyzer import get_htf_analyzer
from .ltf_refinement_engine import get_ltf_engine
from .mtf_alignment_engine import get_mtf_alignment_engine
from .mtf_decision_engine import get_mtf_decision_engine, MTF_ENTRY_MODES


router = APIRouter(prefix="/api/entry-timing/mtf", tags=["mtf-timing"])


# === Request Models ===

class StructureInput(BaseModel):
    market_phase: str = "trend"
    hh_count: int = 0
    hl_count: int = 0
    lh_count: int = 0
    ll_count: int = 0
    bos: int = 0
    choch: int = 0
    range_score: float = 0.0
    compression_score: float = 0.0
    retest_completed: bool = False
    acceptance: bool = False
    micro_phase: str = "chop"


class TrendInput(BaseModel):
    trend_bias: float = 0.0
    ema_stack: str = "mixed"
    price_vs_ema200: str = "at"


class MomentumInput(BaseModel):
    momentum_bias: float = 0.0
    rsi_state: str = "neutral"
    macd_state: str = "neutral"
    impulse_strength: float = 0.5
    momentum_exhausted: bool = False
    breakout_strength: float = 0.5


class QualityInput(BaseModel):
    setup_quality: float = 0.5
    noise_score: float = 0.2
    conflict_score: float = 0.2


class TriggerInput(BaseModel):
    entry_level: float = 0.0
    close_above_trigger: bool = False
    trigger_touched: bool = False
    trigger_rejected: bool = False


class VolatilityInput(BaseModel):
    volatility_state: str = "normal"
    extension_atr: float = 0.5
    wick_rejection: bool = False


class HTFInput(BaseModel):
    structure: StructureInput
    trend: TrendInput
    momentum: MomentumInput
    quality: QualityInput


class LTFInput(BaseModel):
    structure: StructureInput
    trigger: TriggerInput
    momentum: MomentumInput
    volatility: VolatilityInput
    quality: QualityInput


class MTFInput(BaseModel):
    direction: str
    confidence: float = 0.5


class FullMTFInput(BaseModel):
    htf: HTFInput
    mtf: MTFInput
    ltf: LTFInput


# === Endpoints ===

@router.get("/health")
async def mtf_health():
    """Health check for MTF layer."""
    htf = get_htf_analyzer()
    ltf = get_ltf_engine()
    decision = get_mtf_decision_engine()
    
    return {
        "ok": True,
        "module": "mtf_entry_timing",
        "version": "4.7",
        "components": {
            "htf_analyzer": htf.health_check()["ok"],
            "ltf_engine": ltf.health_check()["ok"],
            "decision_engine": decision.health_check()["ok"]
        },
        "modes_count": len(MTF_ENTRY_MODES),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/htf/analyze")
async def analyze_htf(data: HTFInput):
    """Analyze HTF (Higher Timeframe) context."""
    analyzer = get_htf_analyzer()
    
    input_dict = {
        "structure": data.structure.dict(),
        "trend": data.trend.dict(),
        "momentum": data.momentum.dict(),
        "quality": data.quality.dict()
    }
    
    result = analyzer.analyze(input_dict)
    
    return {"ok": True, **result}


@router.post("/ltf/analyze")
async def analyze_ltf(data: LTFInput):
    """Analyze LTF (Lower Timeframe) for entry timing."""
    engine = get_ltf_engine()
    
    input_dict = {
        "structure": data.structure.dict(),
        "trigger": data.trigger.dict(),
        "momentum": data.momentum.dict(),
        "volatility": data.volatility.dict(),
        "quality": data.quality.dict()
    }
    
    result = engine.analyze(input_dict)
    
    return {"ok": True, **result}


@router.post("/decide")
async def mtf_decide(data: FullMTFInput):
    """
    Make full MTF entry decision.
    
    Combines HTF + MTF + LTF into final entry mode.
    """
    engine = get_mtf_decision_engine()
    
    htf_dict = {
        "structure": data.htf.structure.dict(),
        "trend": data.htf.trend.dict(),
        "momentum": data.htf.momentum.dict(),
        "quality": data.htf.quality.dict()
    }
    
    ltf_dict = {
        "structure": data.ltf.structure.dict(),
        "trigger": data.ltf.trigger.dict(),
        "momentum": data.ltf.momentum.dict(),
        "volatility": data.ltf.volatility.dict(),
        "quality": data.ltf.quality.dict()
    }
    
    mtf_dict = data.mtf.dict()
    
    result = engine.decide(htf_dict, mtf_dict, ltf_dict)
    
    return {"ok": True, **result}


@router.post("/decide/mock/{scenario}")
async def mtf_decide_mock(scenario: str):
    """
    Run MTF decision with mock data.
    
    Scenarios: aligned, htf_conflict, ltf_conflict, wait_confirmation
    """
    engine = get_mtf_decision_engine()
    result = engine.decide_with_mock(scenario)
    
    return {"ok": True, **result}


@router.get("/modes")
async def get_modes():
    """Get all available MTF entry modes."""
    engine = get_mtf_decision_engine()
    
    return {
        "ok": True,
        "modes": engine.get_available_modes(),
        "count": len(MTF_ENTRY_MODES),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get MTF decision statistics."""
    engine = get_mtf_decision_engine()
    stats = engine.get_stats()
    
    return {"ok": True, **stats, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent MTF decision history."""
    engine = get_mtf_decision_engine()
    history = engine.get_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# === Simulation Endpoints ===

@router.get("/simulate/scenarios")
async def list_scenarios():
    """List available simulation scenarios."""
    return {
        "ok": True,
        "scenarios": [
            {"name": "aligned", "description": "Full MTF alignment - bullish HTF, long MTF, aligned LTF"},
            {"name": "htf_conflict", "description": "HTF conflict - bearish HTF vs long MTF"},
            {"name": "ltf_conflict", "description": "LTF conflict - good HTF/MTF but bad LTF timing"},
            {"name": "wait_confirmation", "description": "Needs LTF confirmation - neutral LTF"}
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/simulate/all")
async def simulate_all():
    """Run all simulation scenarios."""
    engine = get_mtf_decision_engine()
    
    results = {}
    for scenario in ["aligned", "htf_conflict", "ltf_conflict", "wait_confirmation"]:
        results[scenario] = engine.decide_with_mock(scenario)
    
    return {
        "ok": True,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
