"""
Simulation Service — thin orchestrator on top of the replay engine.

Responsibilities:
  * Snapshot live counts BEFORE the run so the response can prove isolation.
  * Apply `clear_first` (sim-only deletes; never live).
  * Call `run_replay`.
  * Build the response payload (matches `ReplayResponse`).
  * Expose a stats helper used by GET /stats.

Rules:
  * Never mutates live data.
  * Never raises to the route layer (returns ok=False with notes on failure).
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from .replay_engine import run_replay
from .simulation_repository import SimulationRepository, get_simulation_repository
from .types import (
    DEFAULT_MAX_STEPS,
    DEFAULT_MIN_HORIZON_CANDLES,
    MAX_REPLAY_STEPS,
    ReplayRequest,
    ReplayResponse,
    SIM_DEBUG_COLLECTION,
    SIM_HISTORY_COLLECTION,
    SIMULATION_BUILDER_VERSION,
    SIMULATION_VERSION,
    SimStats,
)

LIVE_HISTORY_COLLECTION = "ta_prediction_history"
LIVE_DEBUG_COLLECTION = "ta_prediction_debug"


def _live_counts(db: Any) -> Dict[str, int]:
    out = {"history": 0, "debug": 0}
    if db is None:
        return out
    try:
        out["history"] = int(db[LIVE_HISTORY_COLLECTION].count_documents({}))
    except Exception:
        pass
    try:
        out["debug"] = int(db[LIVE_DEBUG_COLLECTION].count_documents({}))
    except Exception:
        pass
    return out


async def execute_replay(req: ReplayRequest) -> ReplayResponse:
    sim_repo = get_simulation_repository()
    db = sim_repo.db

    live_before = _live_counts(db)
    cleared_count = 0
    if req.clear_first:
        cleared = sim_repo.clear_for(req.symbol, req.tf)
        cleared_count = int(cleared.get("history_deleted", 0)) + int(
            cleared.get("debug_deleted", 0)
        )

    t0 = time.perf_counter()
    notes = []
    try:
        result = await run_replay(
            symbol=req.symbol,
            tf=req.tf,
            start_index=int(req.start_candle_index),
            end_index=int(req.end_candle_index),
            max_steps=int(req.max_steps),
            candles_limit=int(req.candles_limit),
            min_horizon=int(req.min_horizon),
            market_regime=req.market_regime,
            sim_repo=sim_repo,
        )
    except Exception as e:
        result = {
            "historical_candles_fetched": 0,
            "steps": [],
            "steps_attempted": 0,
            "steps_persisted": 0,
            "steps_skipped_insufficient_horizon": 0,
            "steps_skipped_no_anchor": 0,
            "steps_errored": 0,
            "notes": [f"replay_error:{type(e).__name__}:{str(e)[:160]}"],
        }
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    notes.extend(result.get("notes") or [])

    live_after = _live_counts(db)
    sim_history_total = sim_repo.count_history()
    sim_debug_total = sim_repo.count_debug()

    return ReplayResponse(
        ok=True,
        symbol=req.symbol.upper(),
        tf=req.tf.upper(),
        requested_start=int(req.start_candle_index),
        requested_end=int(req.end_candle_index),
        requested_max_steps=int(req.max_steps),
        historical_candles_fetched=int(result.get("historical_candles_fetched", 0)),
        cleared_first=bool(req.clear_first),
        cleared_count=int(cleared_count),
        steps_attempted=int(result.get("steps_attempted", 0)),
        steps_persisted=int(result.get("steps_persisted", 0)),
        steps_skipped_insufficient_horizon=int(
            result.get("steps_skipped_insufficient_horizon", 0)
        ),
        steps_skipped_no_anchor=int(result.get("steps_skipped_no_anchor", 0)),
        steps_errored=int(result.get("steps_errored", 0)),
        sim_history_total_after=int(sim_history_total),
        sim_debug_total_after=int(sim_debug_total),
        live_history_total_before=int(live_before.get("history", 0)),
        live_history_total_after=int(live_after.get("history", 0)),
        live_debug_total_before=int(live_before.get("debug", 0)),
        live_debug_total_after=int(live_after.get("debug", 0)),
        elapsed_ms=elapsed_ms,
        steps=result.get("steps") or [],
        notes=notes,
    )


def compute_sim_stats() -> SimStats:
    sim_repo = get_simulation_repository()
    db = sim_repo.db
    live = _live_counts(db)
    return SimStats(
        sim_history_count=sim_repo.count_history(),
        sim_debug_count=sim_repo.count_debug(),
        sim_history_by_symbol_tf=sim_repo.history_breakdown(),
        sim_debug_by_error_type=sim_repo.debug_breakdown(),
        last_simulation_at=sim_repo.last_simulation_at(),
        live_history_count=int(live.get("history", 0)),
        live_debug_count=int(live.get("debug", 0)),
    )
