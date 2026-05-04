"""
PHASE 4.2 — Entry Mode Routes

API endpoints for entry mode selection:
- POST /api/entry-timing/mode/select — Select entry mode for trade
- GET /api/entry-timing/mode/types — Get all entry mode types
- GET /api/entry-timing/mode/recommend/{reason} — Get mode for wrong early reason
- POST /api/entry-timing/mode/sync-diagnostics — Sync with Phase 4.1
- GET /api/entry-timing/mode/stats — Get selection statistics
- POST /api/entry-timing/mode/simulate/{scenario} — Run simulation
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .entry_mode_engine import get_entry_mode_engine
from .entry_mode_types import ENTRY_MODES


router = APIRouter(prefix="/api/entry-timing/mode", tags=["entry-mode"])


# === Request Models ===

class PredictionInput(BaseModel):
    direction: str
    confidence: float = 0.5
    tradeable: bool = True


class SetupInput(BaseModel):
    entry: float
    type: str = "BREAKOUT"
    stop_loss: Optional[float] = None
    target: Optional[float] = None


class ContextInput(BaseModel):
    extension_atr: Optional[float] = None
    ltf_alignment: Optional[str] = None
    close_confirmation: Optional[bool] = None
    volatility_state: Optional[str] = None
    structure_acceptance: Optional[bool] = None
    retest_available: Optional[bool] = None
    breakout_strength: Optional[float] = None
    liquidity_sweep_active: Optional[bool] = None
    liquidity_sweep_resolved: Optional[bool] = None


class DiagnosticsInput(BaseModel):
    top_wrong_early_reasons: List[str] = []


class ModeSelectInput(BaseModel):
    prediction: PredictionInput
    setup: SetupInput
    context: ContextInput
    diagnostics: Optional[DiagnosticsInput] = None


# === Endpoints ===

@router.get("/health")
async def mode_selector_health():
    """Health check for entry mode selector module."""
    engine = get_entry_mode_engine()
    return engine.health_check()


@router.post("/select")
async def select_entry_mode(data: ModeSelectInput):
    """
    Select entry mode for a trade.
    
    Returns the recommended entry mode with reasoning.
    Does NOT modify the direction or signal - only timing.
    """
    engine = get_entry_mode_engine()
    
    # Convert to dict
    input_dict = {
        "prediction": data.prediction.dict(),
        "setup": data.setup.dict(),
        "context": {k: v for k, v in data.context.dict().items() if v is not None},
        "diagnostics": data.diagnostics.dict() if data.diagnostics else {"top_wrong_early_reasons": []}
    }
    
    result = engine.select(input_dict)
    
    return {
        "ok": True,
        **result
    }


@router.post("/select-batch")
async def select_batch(trades: List[ModeSelectInput]):
    """Select entry modes for multiple trades."""
    engine = get_entry_mode_engine()
    
    results = []
    for trade in trades:
        input_dict = {
            "prediction": trade.prediction.dict(),
            "setup": trade.setup.dict(),
            "context": {k: v for k, v in trade.context.dict().items() if v is not None},
            "diagnostics": trade.diagnostics.dict() if trade.diagnostics else {"top_wrong_early_reasons": []}
        }
        results.append(engine.select(input_dict))
    
    return {
        "ok": True,
        "count": len(results),
        "results": results
    }


@router.get("/types")
async def get_mode_types():
    """Get all available entry mode types with descriptions."""
    engine = get_entry_mode_engine()
    types = engine.get_mode_types()
    
    return {
        "ok": True,
        **types,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/recommend/{reason}")
async def get_recommendation(reason: str = Path(..., description="Wrong early reason")):
    """Get recommended entry mode to prevent a specific wrong early reason."""
    engine = get_entry_mode_engine()
    recommendation = engine.get_recommendation_for_reason(reason)
    
    return {
        "ok": True,
        **recommendation,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/sync-diagnostics")
async def sync_diagnostics():
    """
    Sync with Phase 4.1 diagnostics to update selection rules.
    
    This enables self-correction based on actual wrong early patterns.
    """
    engine = get_entry_mode_engine()
    result = engine.sync_with_diagnostics()
    
    return {
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get statistics on recent mode selections."""
    engine = get_entry_mode_engine()
    stats = engine.get_selection_stats()
    
    return {
        "ok": True,
        **stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent selection history."""
    engine = get_entry_mode_engine()
    history = engine.get_selection_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/simulate/{scenario}")
async def simulate_scenario(
    scenario: str = Path(..., description="Scenario name: high_extension, ltf_conflict, breakout_no_close, strong_setup, hostile_volatility")
):
    """
    Run a simulated scenario to test mode selection.
    
    Available scenarios:
    - high_extension: Price extended too far from trigger
    - ltf_conflict: Lower timeframe shows conflicting signal
    - breakout_no_close: Breakout without candle close confirmation
    - strong_setup: Strong aligned setup (should enter now)
    - hostile_volatility: Extreme volatility conditions
    """
    engine = get_entry_mode_engine()
    result = engine.simulate_scenario(scenario)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "ok": True,
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/scenarios")
async def list_scenarios():
    """List all available simulation scenarios."""
    return {
        "ok": True,
        "scenarios": [
            {"name": "high_extension", "description": "Price extended too far from trigger (>1.5 ATR)"},
            {"name": "ltf_conflict", "description": "Lower timeframe shows conflicting signal"},
            {"name": "breakout_no_close", "description": "Breakout without candle close confirmation"},
            {"name": "strong_setup", "description": "Strong aligned setup - should enter immediately"},
            {"name": "hostile_volatility", "description": "Extreme volatility conditions"}
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.delete("/history")
async def clear_history():
    """Clear selection history (for testing)."""
    engine = get_entry_mode_engine()
    engine.clear_history()
    
    return {
        "ok": True,
        "message": "Selection history cleared",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# === Integration with Wrong Early Diagnostic ===

@router.get("/coverage")
async def get_coverage():
    """
    Check how many wrong early reasons are covered by mode selection rules.
    
    This is important for acceptance criteria (>70% coverage).
    """
    from ..diagnostics.wrong_early_taxonomy import WRONG_EARLY_REASONS
    
    engine = get_entry_mode_engine()
    
    covered = []
    not_covered = []
    
    for reason in WRONG_EARLY_REASONS:
        mode = engine.selector.get_mode_for_reason(reason)
        if mode != "ENTER_NOW":  # If it suggests a different mode, it's covered
            covered.append({"reason": reason, "prevents_with": mode})
        else:
            not_covered.append(reason)
    
    coverage_rate = len(covered) / len(WRONG_EARLY_REASONS) if WRONG_EARLY_REASONS else 0
    
    return {
        "ok": True,
        "total_reasons": len(WRONG_EARLY_REASONS),
        "covered": len(covered),
        "not_covered": len(not_covered),
        "coverage_rate": round(coverage_rate * 100, 1),
        "covered_details": covered,
        "not_covered_reasons": not_covered,
        "meets_criteria": coverage_rate >= 0.70,  # 70% threshold
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
