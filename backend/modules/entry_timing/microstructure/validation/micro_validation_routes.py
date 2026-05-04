"""
PHASE 4.8.2 — Micro Validation Routes

API endpoints for running microstructure A/B validation.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone
from pydantic import BaseModel

from .micro_backtest_runner import get_micro_backtest_runner


router = APIRouter(
    prefix="/api/entry-timing/microstructure/validate",
    tags=["microstructure-validation"],
)


class ValidationRunInput(BaseModel):
    n_trades: int = 200
    seed: int = 42


@router.get("/health")
async def validation_health():
    """Health check for microstructure validation."""
    runner = get_micro_backtest_runner()
    return runner.health_check()


@router.post("/run")
async def run_validation(params: ValidationRunInput):
    """
    Run full A/B microstructure validation.

    Compares Base (no micro) vs Micro (with filter) on identical trade set.
    """
    runner = get_micro_backtest_runner()
    result = runner.run(n_trades=params.n_trades, seed=params.seed)

    return {"ok": True, **result}


@router.get("/latest")
async def get_latest():
    """Get latest validation result."""
    runner = get_micro_backtest_runner()
    latest = runner.get_latest()

    if latest is None:
        return {"ok": False, "message": "No validation run yet"}

    return {"ok": True, **latest}


@router.get("/history")
async def get_history():
    """Get validation run history."""
    runner = get_micro_backtest_runner()
    history = runner.get_history()

    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
