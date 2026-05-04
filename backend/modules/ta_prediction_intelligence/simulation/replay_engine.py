"""
Replay Engine — sequential, deterministic, no-lookahead simulation runner.

For each candle index i in [start, end] (capped by max_steps):

    1. visible = historical_candles[: i + 1]
    2. context = await live_adapter.fetch_live_context(
           symbol, tf,
           historical_candles=historical_candles,
           as_of_candle_index=i,
           source="simulation",
           persist_predictions=False,        # <— critical: never write to live repo
       )
    3. Compute outcome IN-PLACE using future_window(historical_candles, i, h6)
       through `evaluate_prediction_with_candles` from the existing worker
       (zero chart_data calls).
    4. Write everything to ta_prediction_history_sim through SimulationRepository.
    5. Build the debug record via `build_debug_record` and upsert into
       ta_prediction_debug_sim through a SECOND DebugRepository instance
       wired to the sim collection.

Isolation contract:
  * Live collections (`ta_prediction_history`, `ta_prediction_debug`) are
    never touched. We snapshot live counts before the loop and assert at
    the end (in QA) that they are unchanged.
  * Process-wide `temporal_buffer` is snapshot-and-restored around the run,
    and Mongo flushes are disabled for the duration so the replay never
    pollutes the live temporal buffer collection.
"""
from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from .no_lookahead import pick_evaluation_outcome, slice_visible
from .simulation_repository import SimulationRepository
from .types import (
    DEFAULT_MIN_HORIZON_CANDLES,
    ReplayStepResult,
    SimulationSource,
)


# ── temporal_buffer isolation helpers ──────────────────────────────────────────
@contextlib.contextmanager
def _isolated_temporal_buffer():
    """Snapshot/restore process-wide HybridTemporalBuffer state and disable
    Mongo flushes for the duration. After the with-block the buffer is
    bit-for-bit what it was before (same deques, same pending, same db_provider).
    """
    try:
        from modules.ta_prediction_intelligence.learning.temporal_buffer import (
            get_temporal_buffer,
        )
    except Exception:
        # If the buffer is not available we just no-op — simulation can still
        # run; feature_builder will simply skip prev_bar lookups.
        yield
        return
    buf = get_temporal_buffer()
    saved_buffers = {
        k: deque(list(v), maxlen=v.maxlen) for k, v in buf.buffers.items()
    }
    saved_pending = {k: list(v) for k, v in buf._pending.items()}
    saved_push_count = dict(buf.push_count)
    saved_loaded = set(buf._loaded_from_mongo)
    saved_db_provider = buf._db_provider
    # Disable Mongo writes for the duration: any internal _db() call returns None.
    buf._db_provider = lambda: None
    try:
        yield
    finally:
        # Restore in-memory state.
        buf.buffers = saved_buffers
        buf._pending = saved_pending
        buf.push_count = saved_push_count
        buf._loaded_from_mongo = saved_loaded
        buf._db_provider = saved_db_provider


def _candle_close_ts_safe(c: Dict[str, Any], tf: str) -> Optional[int]:
    try:
        from modules.ta_prediction_intelligence.live_adapter import (
            _candle_close_ts_seconds,
        )
        return _candle_close_ts_seconds(c, tf)
    except Exception:
        return None


async def _fetch_historical_candles(
    symbol: str, tf: str, limit: int
) -> List[Dict[str, Any]]:
    """Pull raw historical candles via chart_data_service.

    Note: this happens ONCE before the replay loop. Inside the loop we never
    call chart_data again so there is no lookahead through the live tape.
    """
    try:
        from modules.research_analytics.chart_data import get_chart_data_service
    except Exception:
        return []
    try:
        svc = get_chart_data_service()
        chart_data = await svc.get_chart_data(
            symbol=symbol.upper(), timeframe=tf.upper(), limit=int(limit)
        )
        raw = getattr(chart_data, "candles", None) or []
        out: List[Dict[str, Any]] = []
        for c in raw:
            if hasattr(c, "model_dump"):
                out.append(c.model_dump())
            elif isinstance(c, dict):
                out.append(dict(c))
        return out
    except Exception:
        return []


def _decision_intelligence_safe(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    di = result.get("decision_intelligence")
    if isinstance(di, dict):
        return di
    return None


async def run_replay(
    *,
    symbol: str,
    tf: str,
    start_index: int,
    end_index: int,
    max_steps: int,
    candles_limit: int,
    min_horizon: int = DEFAULT_MIN_HORIZON_CANDLES,
    market_regime: Optional[str] = None,
    sim_repo: Optional[SimulationRepository] = None,
) -> Dict[str, Any]:
    """Run the replay synchronously (one prediction per candle index).

    Returns a dict consumable by the route handler.
    """
    if sim_repo is None:
        from .simulation_repository import get_simulation_repository
        sim_repo = get_simulation_repository()

    # ---- Imports kept lazy so module import stays cheap. -------------------
    from modules.ta_prediction_intelligence.live_adapter import fetch_live_context
    from modules.ta_prediction_intelligence.debug.repository import (
        DebugRepository,
        DEBUG_COLLECTION_SIM,
    )
    from modules.ta_prediction_intelligence.debug.service import build_debug_record

    sim_debug_repo = DebugRepository(
        sim_repo.db, collection_name=DEBUG_COLLECTION_SIM
    )

    # ---- Pull candles ONCE, before the loop. -------------------------------
    historical = await _fetch_historical_candles(symbol, tf, candles_limit)
    n = len(historical)
    notes: List[str] = []
    if n == 0:
        return {
            "historical_candles_fetched": 0,
            "steps": [],
            "steps_attempted": 0,
            "steps_persisted": 0,
            "steps_skipped_insufficient_horizon": 0,
            "steps_skipped_no_anchor": 0,
            "steps_errored": 0,
            "notes": ["no_historical_candles"],
        }

    # Clamp indices to fetched range. End is inclusive.
    si = max(0, int(start_index))
    ei = min(int(end_index), n - 1)
    if si > ei:
        notes.append(
            f"start_index ({start_index}) > end_index ({end_index}) after clamp; nothing to do"
        )
        return {
            "historical_candles_fetched": n,
            "steps": [],
            "steps_attempted": 0,
            "steps_persisted": 0,
            "steps_skipped_insufficient_horizon": 0,
            "steps_skipped_no_anchor": 0,
            "steps_errored": 0,
            "notes": notes,
        }

    # max_steps is a hard cap on how many indices we visit.
    indices = list(range(si, ei + 1))[: int(max_steps)]
    if not indices:
        notes.append("empty_index_range")
        return {
            "historical_candles_fetched": n,
            "steps": [],
            "steps_attempted": 0,
            "steps_persisted": 0,
            "steps_skipped_insufficient_horizon": 0,
            "steps_skipped_no_anchor": 0,
            "steps_errored": 0,
            "notes": notes,
        }

    steps_persisted = 0
    steps_skipped_horizon = 0
    steps_skipped_no_anchor = 0
    steps_errored = 0
    step_results: List[ReplayStepResult] = []

    with _isolated_temporal_buffer():
        for i in indices:
            # Sanity slice (raises if anything is off; treat as error).
            try:
                visible = slice_visible(historical, i)
            except Exception as e:
                steps_errored += 1
                step_results.append(
                    ReplayStepResult(
                        candle_index=i,
                        status="error",
                        error=f"slice_error:{type(e).__name__}",
                    )
                )
                continue
            if len(visible) < 20:
                steps_skipped_no_anchor += 1
                step_results.append(
                    ReplayStepResult(
                        candle_index=i,
                        status="skipped_no_anchor",
                        error="insufficient_visible_candles",
                    )
                )
                continue

            # Build the prediction context with strict simulation flags.
            try:
                result = await fetch_live_context(
                    symbol=symbol,
                    timeframe=tf,
                    candles_limit=candles_limit,
                    market_regime=market_regime,
                    historical_candles=historical,
                    as_of_candle_index=i,
                    source="simulation",
                    persist_predictions=False,
                )
            except Exception as e:
                steps_errored += 1
                step_results.append(
                    ReplayStepResult(
                        candle_index=i,
                        status="error",
                        error=f"context_error:{type(e).__name__}",
                    )
                )
                continue

            live_block = (result or {}).get("_live") or {}
            anchor_close_ts = live_block.get("last_candle_close_ts")
            entry_price = live_block.get("last_close")
            features_meta = (result or {}).get("_features_debug") or {}
            feature_hash = features_meta.get("feature_hash")

            if anchor_close_ts is None or entry_price is None:
                steps_skipped_no_anchor += 1
                step_results.append(
                    ReplayStepResult(
                        candle_index=i,
                        status="skipped_no_anchor",
                        error="no_anchor_in_visible_window",
                    )
                )
                continue

            # Build a *record-shaped* dict so we can reuse the live evaluator
            # to compute outcome from purely historical bars.
            record = {
                "prediction_id": f"sim-{uuid.uuid4().hex[:16]}",
                "symbol": (symbol or "").upper(),
                "timeframe": (tf or "").upper(),
                "entry_price": float(entry_price),
                "candle_close_ts": int(anchor_close_ts),
                "bias": result.get("bias"),
                "confidence": result.get("confidence"),
                "conflict_ratio": result.get("conflict_ratio"),
                "dominant_engine": result.get("dominant_engine"),
                "contributions": result.get("contributions") or [],
                "interaction": result.get("interaction"),
                "scenarios_original": result.get("scenarios_original") or [],
                "scenarios_interaction_adjusted": result.get(
                    "scenarios_pre_calibration"
                ) or [],
                "scenarios_calibrated": result.get("scenarios") or [],
                "scenarios_adjustment_meta": result.get("scenarios_adjustment"),
                "scenarios_calibration_meta": result.get("scenarios_calibration"),
                "meta": {"_live": live_block},
                "feature_hash": feature_hash,
                "feature_states": features_meta.get("states"),
                "feature_version": features_meta.get("feature_version"),
                "feature_schema_hash": features_meta.get("feature_schema_hash"),
                "feature_missing_engines": features_meta.get("missing_engines"),
                "feature_latency_ms": features_meta.get("latency_ms"),
                "decision_intelligence": _decision_intelligence_safe(result),
                "temporal_intelligence": result.get("temporal_intelligence"),
                "source": SimulationSource.SIMULATION.value,
                "as_of_candle_index": i,
            }

            outcome, err = pick_evaluation_outcome(
                record, historical, i, min_horizon=min_horizon
            )
            if outcome is None:
                # Persist a pending sim record so the run is auditable, then
                # mark this step as skipped.
                pending_pid = sim_repo.write_prediction(
                    symbol=record["symbol"],
                    timeframe=record["timeframe"],
                    entry_price=record["entry_price"],
                    candle_close_ts=record["candle_close_ts"],
                    bias=record["bias"],
                    confidence=record["confidence"],
                    conflict_ratio=record["conflict_ratio"],
                    dominant_engine=record["dominant_engine"],
                    contributions=record["contributions"],
                    interaction=record["interaction"],
                    scenarios_original=record["scenarios_original"],
                    scenarios_interaction_adjusted=record["scenarios_interaction_adjusted"],
                    scenarios_calibrated=record["scenarios_calibrated"],
                    scenarios_adjustment_meta=record["scenarios_adjustment_meta"],
                    scenarios_calibration_meta=record["scenarios_calibration_meta"],
                    meta=record["meta"],
                    prediction_id=record["prediction_id"],
                    features_bundle={
                        "features": None,  # full vector lives nowhere in sim by design
                        "feature_version": record["feature_version"],
                        "feature_schema_hash": record["feature_schema_hash"],
                        "feature_hash": record["feature_hash"],
                        "builder_version": features_meta.get("builder_version"),
                        "states": record["feature_states"],
                        "ts": int(record["candle_close_ts"]),
                        "missing_engines": record["feature_missing_engines"],
                        "latency_ms": record["feature_latency_ms"],
                    },
                    temporal_context=record["temporal_intelligence"],
                    decision_context=record["decision_intelligence"],
                    as_of_candle_index=i,
                    outcome=None,
                    evaluation_state="pending",
                )
                steps_skipped_horizon += 1
                step_results.append(
                    ReplayStepResult(
                        candle_index=i,
                        candle_close_ts=record["candle_close_ts"],
                        status="skipped_insufficient_horizon",
                        prediction_id=pending_pid,
                        bias=record["bias"],
                        confidence=record["confidence"],
                        feature_hash=feature_hash,
                        error=err,
                    )
                )
                continue

            # Persist evaluated sim record.
            pid = sim_repo.write_prediction(
                symbol=record["symbol"],
                timeframe=record["timeframe"],
                entry_price=record["entry_price"],
                candle_close_ts=record["candle_close_ts"],
                bias=record["bias"],
                confidence=record["confidence"],
                conflict_ratio=record["conflict_ratio"],
                dominant_engine=record["dominant_engine"],
                contributions=record["contributions"],
                interaction=record["interaction"],
                scenarios_original=record["scenarios_original"],
                scenarios_interaction_adjusted=record["scenarios_interaction_adjusted"],
                scenarios_calibrated=record["scenarios_calibrated"],
                scenarios_adjustment_meta=record["scenarios_adjustment_meta"],
                scenarios_calibration_meta=record["scenarios_calibration_meta"],
                meta=record["meta"],
                prediction_id=record["prediction_id"],
                features_bundle={
                    "features": None,
                    "feature_version": record["feature_version"],
                    "feature_schema_hash": record["feature_schema_hash"],
                    "feature_hash": record["feature_hash"],
                    "builder_version": features_meta.get("builder_version"),
                    "states": record["feature_states"],
                    "ts": int(record["candle_close_ts"]),
                    "missing_engines": record["feature_missing_engines"],
                    "latency_ms": record["feature_latency_ms"],
                },
                temporal_context=record["temporal_intelligence"],
                decision_context=record["decision_intelligence"],
                as_of_candle_index=i,
                outcome=outcome,
                evaluation_state="evaluated",
            )

            # Build + upsert sim debug record using the SAME builder as live.
            evaluated_record = dict(record)
            evaluated_record["outcome"] = outcome
            evaluated_record["evaluation_state"] = "evaluated"
            dbg_record = build_debug_record(evaluated_record)
            error_type = None
            root_cause_primary = None
            if dbg_record is not None:
                # Stamp source so sim debug rows carry provenance.
                dbg_record["source"] = SimulationSource.SIMULATION.value
                dbg_record["as_of_candle_index"] = i
                try:
                    sim_debug_repo.upsert(dbg_record)
                except Exception:
                    pass
                error_type = dbg_record.get("error_type")
                root_cause_primary = dbg_record.get("root_cause_primary")

            steps_persisted += 1
            step_results.append(
                ReplayStepResult(
                    candle_index=i,
                    candle_close_ts=record["candle_close_ts"],
                    status="persisted",
                    prediction_id=pid,
                    bias=record["bias"],
                    confidence=record["confidence"],
                    feature_hash=feature_hash,
                    return_h6=outcome.get("return_h6"),
                    winning_scenario=outcome.get("winning_scenario"),
                    error_type=error_type,
                    root_cause_primary=root_cause_primary,
                )
            )

    return {
        "historical_candles_fetched": n,
        "steps": [s.model_dump() for s in step_results],
        "steps_attempted": len(indices),
        "steps_persisted": steps_persisted,
        "steps_skipped_insufficient_horizon": steps_skipped_horizon,
        "steps_skipped_no_anchor": steps_skipped_no_anchor,
        "steps_errored": steps_errored,
        "notes": notes,
    }
