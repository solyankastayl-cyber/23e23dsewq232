"""
Debug service — orchestrator that:

    record (history + outcome + decision)
        ↓
    classify_error()      → primary error_type
    attribute_root_causes() → primary + secondary + engine attribution
        ↓
    debug_record (matches the locked contract)
        ↓
    repository.upsert  (own collection)

Pure for everything that doesn't touch Mongo. The repository call is the
only side-effect, and it is idempotent (upsert by prediction_id).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .taxonomy import (
    DEBUG_BUILDER_VERSION,
    DEBUG_VERSION,
    ErrorType,
    OVERCONFIDENT_THRESHOLD,
    UNDERCONFIDENT_THRESHOLD,
    classify_error,
)
from .root_cause import attribute_root_causes


def _confidence_bucket(c: float) -> str:
    """5 fixed buckets so cross-cohort comparison is deterministic."""
    try:
        v = float(c)
    except (TypeError, ValueError):
        return "unknown"
    if v < UNDERCONFIDENT_THRESHOLD:
        return "low"
    if v < 0.55:
        return "medium_low"
    if v < OVERCONFIDENT_THRESHOLD:
        return "medium"
    if v < 0.80:
        return "high"
    return "very_high"


def build_debug_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pure — produce a debug record for an evaluated prediction.
    Returns None if the record is not evaluable yet (no outcome, etc.).
    """
    if record.get("evaluation_state") != "evaluated":
        return None
    outcome = record.get("outcome") or {}
    if outcome.get("return_h6") is None or outcome.get("winning_scenario") is None:
        return None

    error_type, cls_meta = classify_error(record)
    causes = attribute_root_causes(record, error_type, cls_meta)
    decision = record.get("decision_intelligence") or {}

    debug_record: Dict[str, Any] = {
        "prediction_id": record.get("prediction_id"),
        "symbol": (record.get("symbol") or "").upper(),
        "tf": (record.get("timeframe") or "").upper(),
        "candle_close_ts": record.get("candle_close_ts"),
        "entry_price": record.get("entry_price"),
        # Taxonomy
        "error_type": error_type.value,
        "correct_direction": bool(cls_meta.get("correct_direction")),
        "scenario_correct": bool(cls_meta.get("scenario_correct")),
        "signal_strength": cls_meta.get("signal_strength"),
        "primary_scenario": cls_meta.get("primary_scenario"),
        "winning_scenario": cls_meta.get("winning_scenario"),
        "interaction_type": str(
            (record.get("interaction") or {}).get("type") or ""
        ).lower() or None,
        "decision_confidence": cls_meta.get("decision_confidence"),
        "confidence_bucket": _confidence_bucket(cls_meta.get("decision_confidence") or 0.0),
        # Outcome facts
        "return_h1": outcome.get("return_h1"),
        "return_h3": outcome.get("return_h3"),
        "return_h6": outcome.get("return_h6"),
        "max_favourable_move_pct": outcome.get("max_favourable_move_pct"),
        "max_adverse_move_pct": outcome.get("max_adverse_move_pct"),
        "volatility_future_h6": outcome.get("volatility_future_h6"),
        "conflict_ratio": cls_meta.get("conflict_ratio"),
        "risk_level": (decision.get("risk_level") or "").lower() or None,
        # Root cause
        "root_cause_primary": causes.get("primary_cause"),
        "root_causes_secondary": causes.get("secondary_causes") or [],
        "engine_attribution": causes.get("engine_attribution") or [],
        "notes": causes.get("notes") or [],
        # Meta
        "debug_version": DEBUG_VERSION,
        "debug_builder_version": DEBUG_BUILDER_VERSION,
        "thresholds": cls_meta.get("thresholds"),
        "no_edge_ignored": bool(cls_meta.get("no_edge_ignored")),
        "analyzed_at": datetime.now(timezone.utc),
    }
    return debug_record


def analyze_record(
    record: Dict[str, Any],
    *,
    debug_repo: Any = None,
) -> Optional[Dict[str, Any]]:
    """Build + persist (upsert by prediction_id). Returns the record or None.

    `debug_repo` overrides the singleton (used by Simulation Engine to write
    into the isolated `ta_prediction_debug_sim` collection).
    """
    dbg = build_debug_record(record)
    if dbg is None:
        return None
    try:
        if debug_repo is None:
            from .repository import get_debug_repository
            debug_repo = get_debug_repository()
        if debug_repo is not None:
            debug_repo.upsert(dbg)
    except Exception:
        pass
    return dbg


def analyze_many(
    records: List[Dict[str, Any]],
    *,
    debug_repo: Any = None,
) -> Dict[str, int]:
    out = {"analyzed": 0, "skipped": 0}
    for r in records:
        if analyze_record(r, debug_repo=debug_repo) is not None:
            out["analyzed"] += 1
        else:
            out["skipped"] += 1
    return out
