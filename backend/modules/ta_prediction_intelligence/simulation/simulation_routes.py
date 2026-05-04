"""
HTTP routes for the Simulation Engine.

    POST /api/ta-prediction-intelligence/simulation/replay
    GET  /api/ta-prediction-intelligence/simulation/stats
    POST /api/ta-prediction-intelligence/simulation/clear   (admin/QA escape
                                                              hatch — sim-only)

All responses are JSON-serialisable Pydantic models.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .simulation_service import compute_sim_stats, execute_replay
from .simulation_repository import get_simulation_repository
from .types import (
    MAX_REPLAY_STEPS,
    ReplayRequest,
    ReplayResponse,
    SimStats,
    SIMULATION_VERSION,
)

router = APIRouter(
    prefix="/api/ta-prediction-intelligence/simulation",
    tags=["ta-prediction-intelligence-simulation"],
)


class ClearRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    tf: str = Field(..., min_length=1)
    confirm: bool = Field(default=False)


@router.post("/replay", response_model=ReplayResponse)
async def replay(req: ReplayRequest) -> ReplayResponse:
    if req.start_candle_index > req.end_candle_index:
        raise HTTPException(
            status_code=400,
            detail="start_candle_index must be <= end_candle_index",
        )
    if req.max_steps > MAX_REPLAY_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"max_steps capped at {MAX_REPLAY_STEPS}",
        )
    return await execute_replay(req)


@router.get("/stats", response_model=SimStats)
def stats() -> SimStats:
    return compute_sim_stats()


@router.post("/clear")
def clear(req: ClearRequest) -> Dict[str, Any]:
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm must be true to delete simulation rows",
        )
    repo = get_simulation_repository()
    cleared = repo.clear_for(req.symbol, req.tf)
    return {
        "ok": True,
        "simulation_version": SIMULATION_VERSION,
        "symbol": req.symbol.upper(),
        "tf": req.tf.upper(),
        "cleared": cleared,
    }
