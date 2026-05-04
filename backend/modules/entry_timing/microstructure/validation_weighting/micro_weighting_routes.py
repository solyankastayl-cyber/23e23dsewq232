"""
PHASE 4.8.4 — Micro Weighting Validation Routes

API endpoints for A/B/C validation: Base vs Filter vs Weighting.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from pydantic import BaseModel

from .micro_weighting_ab_runner import get_weighting_ab_runner


router = APIRouter(
    prefix="/api/entry-timing/microstructure/weighting/validate",
    tags=["microstructure-weighting-validation"],
)


class ABCValidationInput(BaseModel):
    n_trades: int = 200
    seed: int = 42


@router.get("/health")
async def weighting_validation_health():
    """Health check for A/B/C validation."""
    runner = get_weighting_ab_runner()
    return runner.health_check()


@router.post("/run")
async def run_abc_validation(params: ABCValidationInput):
    """
    Run A/B/C validation: Base vs Filter vs Weighting.

    Same trade dataset, same execution engine.
    Returns metrics, comparison, impact, and verdict.
    """
    runner = get_weighting_ab_runner()
    result = runner.run(n_trades=params.n_trades, seed=params.seed)

    return {"ok": True, **result}


@router.get("/latest")
async def get_latest():
    """Get latest A/B/C validation result."""
    runner = get_weighting_ab_runner()
    latest = runner.get_latest()

    if latest is None:
        return {"ok": False, "message": "No validation run yet"}

    return {"ok": True, **latest}


@router.get("/history")
async def get_history():
    """Get validation run history."""
    runner = get_weighting_ab_runner()
    history = runner.get_history()

    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
