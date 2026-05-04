"""
PHASE 4.1 — Wrong Early Routes

API endpoints for wrong early diagnostic engine:
- POST /api/entry-timing/wrong-early/analyze — Analyze single trade
- POST /api/entry-timing/wrong-early/analyze-batch — Analyze multiple trades
- GET /api/entry-timing/wrong-early/summary — Get summary statistics
- GET /api/entry-timing/wrong-early/records — Get raw records
- GET /api/entry-timing/wrong-early/reason/{reason} — Get details for specific reason
- GET /api/entry-timing/wrong-early/taxonomy — Get classification taxonomy
- POST /api/entry-timing/wrong-early/simulate — Generate simulated data for testing
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .wrong_early_engine import get_wrong_early_engine
from .wrong_early_taxonomy import WRONG_EARLY_REASONS


router = APIRouter(prefix="/api/entry-timing/wrong-early", tags=["wrong-early"])


# === Request Models ===

class PredictionInput(BaseModel):
    direction: str
    confidence: float = 0.5
    tradeable: bool = True


class SetupInput(BaseModel):
    entry: float
    stop_loss: float
    target: float
    execution_type: str = "BREAKOUT"


class ExecutionResultInput(BaseModel):
    filled: bool = True
    entry_price: float
    outcome: str = "SL"
    pnl: float = 0.0
    wrong_early: bool = True


class ContextInput(BaseModel):
    close_above_trigger: Optional[bool] = None
    close_below_trigger: Optional[bool] = None
    retest_completed: Optional[bool] = None
    extension_at_entry_atr: Optional[float] = None
    ltf_alignment: Optional[str] = None
    volatility_state: Optional[str] = None
    volatility_value: Optional[float] = None
    structure_acceptance: Optional[bool] = None
    exhaustion_confirmed: Optional[bool] = None
    liquidity_sweep_resolved: Optional[bool] = None
    pullback_completed: Optional[bool] = None
    reset_completed: Optional[bool] = None
    reversal_candidate: Optional[bool] = None
    trigger_touched: Optional[bool] = None
    trigger_accepted: Optional[bool] = None
    entered_before_close: Optional[bool] = None
    market_extending: Optional[bool] = None
    momentum_exhausted: Optional[bool] = None


class AnalyzeInput(BaseModel):
    symbol: str
    timeframe: str = "4H"
    prediction: PredictionInput
    setup: SetupInput
    execution_result: ExecutionResultInput
    context: ContextInput


# === Endpoints ===

@router.get("/health")
async def wrong_early_health():
    """Health check for wrong early diagnostic module."""
    engine = get_wrong_early_engine()
    return engine.health_check()


@router.post("/analyze")
async def analyze_trade(data: AnalyzeInput):
    """
    Analyze a single trade for wrong early classification.
    
    Returns the reason why the entry was early and actionable details.
    """
    engine = get_wrong_early_engine()
    
    # Convert Pydantic model to dict
    input_dict = {
        "symbol": data.symbol,
        "timeframe": data.timeframe,
        "prediction": data.prediction.dict(),
        "setup": data.setup.dict(),
        "execution_result": data.execution_result.dict(),
        "context": {k: v for k, v in data.context.dict().items() if v is not None}
    }
    
    result = engine.analyze(input_dict)
    
    return {
        "ok": True,
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/analyze-batch")
async def analyze_batch(trades: List[AnalyzeInput]):
    """Analyze multiple trades in batch."""
    engine = get_wrong_early_engine()
    
    results = []
    for trade in trades:
        input_dict = {
            "symbol": trade.symbol,
            "timeframe": trade.timeframe,
            "prediction": trade.prediction.dict(),
            "setup": trade.setup.dict(),
            "execution_result": trade.execution_result.dict(),
            "context": {k: v for k, v in trade.context.dict().items() if v is not None}
        }
        results.append(engine.analyze(input_dict))
    
    return {
        "ok": True,
        "analyzed": len(results),
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/summary")
async def get_summary(limit: int = Query(500, ge=10, le=2000)):
    """
    Get comprehensive summary of all wrong early records.
    
    Includes:
    - Distribution by reason
    - Top issues with suggested fixes
    - Actionable insights
    """
    engine = get_wrong_early_engine()
    summary = engine.get_summary(limit)
    
    return {
        "ok": True,
        **summary
    }


@router.get("/records")
async def get_records(
    limit: int = Query(100, ge=1, le=500),
    reason: Optional[str] = None,
    symbol: Optional[str] = None
):
    """Get raw wrong early records with optional filtering."""
    engine = get_wrong_early_engine()
    
    if reason:
        if reason not in WRONG_EARLY_REASONS:
            raise HTTPException(status_code=400, detail=f"Invalid reason: {reason}")
        records = engine.get_records_by_reason(reason, limit)
    elif symbol:
        records = engine.get_records_by_symbol(symbol, limit)
    else:
        records = engine.get_records(limit)
    
    return {
        "ok": True,
        "records": records,
        "count": len(records),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/reason/{reason}")
async def get_reason_details(reason: str):
    """Get detailed analysis for a specific wrong early reason."""
    if reason not in WRONG_EARLY_REASONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reason: {reason}. Valid reasons: {WRONG_EARLY_REASONS}"
        )
    
    engine = get_wrong_early_engine()
    details = engine.get_reason_details(reason)
    
    return {
        "ok": True,
        **details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/summary/by-symbol")
async def get_summary_by_symbol():
    """Get summary broken down by symbol."""
    engine = get_wrong_early_engine()
    summary = engine.get_summary_by_symbol()
    
    return {
        "ok": True,
        "by_symbol": summary,
        "symbols_count": len(summary),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/summary/by-timeframe")
async def get_summary_by_timeframe():
    """Get summary broken down by timeframe."""
    engine = get_wrong_early_engine()
    summary = engine.get_summary_by_timeframe()
    
    return {
        "ok": True,
        "by_timeframe": summary,
        "timeframes_count": len(summary),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/taxonomy")
async def get_taxonomy():
    """Get the full wrong early classification taxonomy."""
    engine = get_wrong_early_engine()
    taxonomy = engine.get_taxonomy()
    
    return {
        "ok": True,
        **taxonomy,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/simulate")
async def simulate_analysis(count: int = Query(50, ge=10, le=200)):
    """
    Generate and analyze simulated wrong early trades for testing.
    
    Useful for:
    - Testing the diagnostic engine
    - Demonstrating classification
    - Populating initial data
    """
    engine = get_wrong_early_engine()
    result = engine.simulate_analysis(count)
    
    return {
        "ok": True,
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.delete("/records")
async def clear_records():
    """Clear all records (for testing/reset)."""
    engine = get_wrong_early_engine()
    engine.repository.clear()
    
    return {
        "ok": True,
        "message": "All records cleared",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
