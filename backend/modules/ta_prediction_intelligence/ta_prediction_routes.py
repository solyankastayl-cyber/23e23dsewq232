"""
FastAPI router for ta_prediction_intelligence.

Exposed once explicitly registered in `server.py` (read-only analytical
service; no participation in combined_analysis / meta_pipeline / shadow flow).

Step 7 additions:
  * GET  /history                 — recent predictions + outcomes
  * GET  /calibration             — aggregated calibration stats per bucket
  * GET  /calibration/diagnostics — full reliability snapshot (all groups)
  * POST /calibration/rebuild     — trigger recomputation from history
  * GET  /outcome_worker/status   — background evaluator health
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .live_adapter import fetch_live_context
from .ta_prediction_service import TAPredictionService
from .types import TAPredictionSetup

router = APIRouter(
    prefix="/api/ta-prediction-intelligence",
    tags=["ta-prediction-intelligence"],
)

_service = TAPredictionService()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models (HTTP boundary). Keep them tight: only what the dataclass
# already defines, plus an optional market_regime envelope.
# ─────────────────────────────────────────────────────────────────────────────


class FromSetupPayload(BaseModel):
    symbol: str = Field(..., description="Trading pair, e.g. BTCUSDT")
    timeframe: Optional[str] = Field(None, description="Timeframe, e.g. 1H")
    tf: Optional[str] = Field(None, description="Alias of timeframe")
    setup: Dict[str, Any] = Field(default_factory=dict)
    market_regime: Optional[str] = Field(
        None, description="trend | range | compression | high_volatility"
    )
    persist: bool = Field(False, description="Persist prediction to history")


class TypedSetupModel(BaseModel):
    """HTTP-side mirror of TAPredictionSetup dataclass."""
    symbol: str
    timeframe: str
    price: float

    direction: str = "neutral"
    confidence: float = 0.0
    strength: float = 0.0

    trend_strength: float = 0.0
    structure_state: str = "range"

    rsi: Optional[float] = None
    macd_hist: Optional[float] = None

    support: Optional[float] = None
    resistance: Optional[float] = None

    atr_pct: Optional[float] = None
    volatility_state: str = "normal"

    patterns: List[Dict[str, Any]] = Field(default_factory=list)

    compression: bool = False
    expansion: bool = False


class FromTypedPayload(BaseModel):
    setup: TypedSetupModel
    market_regime: Optional[str] = Field(
        None, description="trend | range | compression | high_volatility"
    )
    persist: bool = Field(False, description="Persist prediction to history")


# ─────────────────────────────────────────────────────────────────────────────
# Core Step 1-6 routes (unchanged contract, just now also emit Step 7 fields).
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "module": "ta_prediction_intelligence",
        "engines": ["structure", "pattern", "momentum", "level_zone", "volatility"],
        "entry_points": ["/from-setup", "/from-typed", "/live"],
        "step7_entry_points": [
            "/history",
            "/calibration",
            "/calibration/diagnostics",
            "/calibration/rebuild",
            "/outcome_worker/status",
        ],
        "wired_to_meta": False,
    }


@router.get("/live")
async def live_context(
    symbol: str = Query(..., description="Trading pair, e.g. BTCUSDT"),
    tf: Optional[str] = Query(None, description="Timeframe alias"),
    timeframe: Optional[str] = Query(None, description="Timeframe, e.g. 4H"),
    candles_limit: int = Query(200, ge=20, le=1000),
    market_regime: Optional[str] = Query(
        None, description="Optional regime hint: trend | range | compression | high_volatility"
    ),
) -> Dict[str, Any]:
    """
    Full live pipeline. Always persists via Step 7 repository.
    Response includes: contributions, scenarios_original, scenarios_adjustment,
    scenarios_pre_calibration, scenarios, scenarios_calibration, prediction_id.
    """
    tf_resolved = tf or timeframe or ""
    return await fetch_live_context(
        symbol=symbol,
        timeframe=tf_resolved,
        candles_limit=candles_limit,
        market_regime=market_regime,
    )


@router.post("/from-setup")
def build_from_setup(payload: FromSetupPayload) -> Dict[str, Any]:
    timeframe = payload.timeframe or payload.tf or ""
    return _service.build_from_setup(
        symbol=payload.symbol,
        timeframe=timeframe,
        setup=payload.setup,
        market_regime=payload.market_regime,
        persist=bool(payload.persist),
    )


@router.post("/from-typed")
def build_from_typed(payload: FromTypedPayload) -> Dict[str, Any]:
    """
    Canonical typed entry point. Recommended for external API consumers.
    """
    typed = TAPredictionSetup(**payload.setup.model_dump())
    return _service.build_from_typed_setup(
        setup=typed,
        market_regime=payload.market_regime,
        persist=bool(payload.persist),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 routes — history, calibration, outcome worker
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/history")
def get_history(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    state: Optional[str] = Query(
        None, description="pending | evaluated | expired | error"
    ),
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    from .repository import get_repository
    repo = get_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="repository_unavailable")
    rows = repo.get_recent_predictions(
        symbol=symbol, timeframe=tf, state=state, limit=limit
    )
    counts = repo.count_by_state()
    return {"ok": True, "count": len(rows), "state_counts": counts, "items": rows}


@router.get("/calibration")
def get_calibration(
    group_by: str = Query(
        "interaction_type",
        description=(
            "interaction_type | dominant_engine | symbol_tf | symbol_tf_interaction"
        ),
    ),
    refresh: bool = Query(False, description="Force reload from Mongo"),
) -> Dict[str, Any]:
    allowed = {"interaction_type", "dominant_engine", "symbol_tf", "symbol_tf_interaction"}
    if group_by not in allowed:
        raise HTTPException(status_code=400, detail=f"group_by must be one of {sorted(allowed)}")
    from .calibration.calibration_store import get_stats_by_group
    stats = get_stats_by_group(force_refresh=refresh)
    return {
        "ok": True,
        "group_by": group_by,
        "buckets": stats.get(group_by, []),
        "total_buckets": len(stats.get(group_by, [])),
    }


@router.get("/calibration/diagnostics")
def calibration_diagnostics(refresh: bool = Query(False)) -> Dict[str, Any]:
    from .calibration.calibration_store import get_stats_by_group
    from .repository import get_repository
    stats = get_stats_by_group(force_refresh=refresh)
    repo = get_repository()
    counts = repo.count_by_state() if repo else {}
    # Summary: total buckets per group, best brier per group, largest bucket per group.
    summary: Dict[str, Any] = {}
    for g, buckets in stats.items():
        if not buckets:
            summary[g] = {"buckets": 0, "largest_n": 0, "best_brier": None}
            continue
        largest = max(int(b.get("n", 0)) for b in buckets)
        best_brier = min(
            (float(b.get("brier_score", 1.0) or 1.0) for b in buckets), default=None
        )
        summary[g] = {
            "buckets": len(buckets),
            "largest_n": largest,
            "best_brier": round(best_brier, 6) if best_brier is not None else None,
        }
    return {
        "ok": True,
        "state_counts": counts,
        "summary": summary,
        "stats_by_group": stats,
    }


@router.post("/calibration/rebuild")
def calibration_rebuild() -> Dict[str, Any]:
    from .calibration.calibration_store import rebuild_from_history
    result = rebuild_from_history()
    return {"ok": bool(result.get("ok", False)), **result}


@router.get("/outcome_worker/status")
def outcome_worker_status() -> Dict[str, Any]:
    from .evaluation import get_outcome_worker
    from .repository import get_repository
    worker = get_outcome_worker()
    repo = get_repository()
    return {
        "ok": True,
        "worker": worker.status(),
        "state_counts": repo.count_by_state() if repo else {},
    }
