"""
Locked contracts for the Simulation Engine.

All simulation IO MUST go through these types so isolation invariants are
enforceable at the boundary.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

SIMULATION_VERSION = "v1"
SIMULATION_BUILDER_VERSION = "1.0.0"

# ── Mongo collections (isolated; NEVER reuse live collection names) ───────
SIM_HISTORY_COLLECTION = "ta_prediction_history_sim"
SIM_DEBUG_COLLECTION = "ta_prediction_debug_sim"
SIM_TEMPORAL_COLLECTION = "ta_prediction_temporal_buffer_sim"  # reserved

# Hard cap so a buggy caller cannot blow the database.
MAX_REPLAY_STEPS = 1000
DEFAULT_MAX_STEPS = 200
DEFAULT_MIN_HORIZON_CANDLES = 6  # h6 — must match live evaluation worker


class SimulationSource(str, Enum):
    """`source` field stamped on every simulation record."""
    SIMULATION = "simulation"


class ReplayRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    tf: str = Field(..., min_length=1, description="Timeframe, e.g. 1H / 4H / 1D")
    start_candle_index: int = Field(..., ge=0)
    end_candle_index: int = Field(..., ge=0)
    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1, le=MAX_REPLAY_STEPS)
    clear_first: bool = Field(
        default=False,
        description="If true, drop ALL existing simulation records for (symbol, tf) before replay.",
    )
    candles_limit: int = Field(
        default=600,
        ge=50,
        le=5000,
        description="Number of historical candles to fetch from chart_data.",
    )
    min_horizon: int = Field(default=DEFAULT_MIN_HORIZON_CANDLES, ge=1, le=64)
    market_regime: Optional[str] = None


class ReplayStepResult(BaseModel):
    candle_index: int
    candle_close_ts: Optional[int] = None
    status: str  # "persisted" | "skipped_insufficient_horizon" | "skipped_no_anchor" | "error"
    prediction_id: Optional[str] = None
    bias: Optional[str] = None
    confidence: Optional[float] = None
    feature_hash: Optional[str] = None
    return_h6: Optional[float] = None
    winning_scenario: Optional[str] = None
    error_type: Optional[str] = None
    root_cause_primary: Optional[str] = None
    error: Optional[str] = None


class ReplayResponse(BaseModel):
    ok: bool
    simulation_version: str = SIMULATION_VERSION
    builder_version: str = SIMULATION_BUILDER_VERSION
    symbol: str
    tf: str
    requested_start: int
    requested_end: int
    requested_max_steps: int
    historical_candles_fetched: int
    cleared_first: bool
    cleared_count: int = 0
    steps_attempted: int
    steps_persisted: int
    steps_skipped_insufficient_horizon: int
    steps_skipped_no_anchor: int
    steps_errored: int
    sim_history_total_after: int
    sim_debug_total_after: int
    live_history_total_before: int
    live_history_total_after: int
    live_debug_total_before: int
    live_debug_total_after: int
    elapsed_ms: float
    steps: List[ReplayStepResult] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class SimStats(BaseModel):
    ok: bool = True
    simulation_version: str = SIMULATION_VERSION
    sim_history_count: int
    sim_debug_count: int
    sim_history_by_symbol_tf: List[Dict[str, Any]] = Field(default_factory=list)
    sim_debug_by_error_type: List[Dict[str, Any]] = Field(default_factory=list)
    last_simulation_at: Optional[str] = None
    live_history_count: int
    live_debug_count: int
