"""
Cohort builder — joins ta_prediction_debug ↔ ta_prediction_history (in-memory),
buckets each record into the 6 single-axis cohorts.

Read-only on Mongo (find()).

A “joined record” carries:
    prediction_id
    error_type, root_cause_primary, no_edge_ignored,
    confidence_bucket, signal_strength, interaction_type,
    primary_scenario, decision_bias,                  ← from history.decision_intelligence
    volatility_state, trend_state,                    ← from history.feature_states
    symbol, tf, candle_close_ts, analyzed_at, evaluated_at, created_at

Bucket keys (lowercased, ‘unknown’ fallback):
    symbol_tf        : f"{symbol}_{tf}"
    interaction_type : interaction.type
    signal_strength  : decision.signal_strength
    decision_bias    : decision.decision_bias
    volatility_state : feature_states.volatility
    trend_state      : feature_states.trend
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from .concentration import build_distribution, compute_hhi, compute_top_share
from .stability import compute_stability
from .types import (
    AXES,
    MIN_COHORT,
    NON_ERROR_TYPES,
)

DEBUG_COL = "ta_prediction_debug"
HISTORY_COL = "ta_prediction_history"


def _norm(v: Any) -> str:
    s = str(v or "").strip().lower()
    return s if s else "unknown"


def _is_error(record: Dict[str, Any]) -> bool:
    return (record.get("error_type") or "") not in NON_ERROR_TYPES


def _join_records(db: Any) -> List[Dict[str, Any]]:
    """Read both collections and produce joined records.

    Live-only, no caching. Designed for cohorts up to a few thousand records;
    when ML scales we can switch to an aggregation pipeline.
    """
    if db is None:
        return []
    debug_records = list(db[DEBUG_COL].find({}, {
        "_id": 0,
        "prediction_id": 1, "symbol": 1, "tf": 1, "candle_close_ts": 1,
        "error_type": 1, "root_cause_primary": 1, "no_edge_ignored": 1,
        "signal_strength": 1, "interaction_type": 1,
        "primary_scenario": 1, "confidence_bucket": 1,
        "analyzed_at": 1, "return_h6": 1,
    }))
    if not debug_records:
        return []
    pids = [r["prediction_id"] for r in debug_records if r.get("prediction_id")]
    history_by_pid: Dict[str, Dict[str, Any]] = {}
    if pids:
        cursor = db[HISTORY_COL].find(
            {"prediction_id": {"$in": pids}},
            {
                "_id": 0,
                "prediction_id": 1,
                "created_at": 1, "outcome.evaluated_at": 1,
                "decision_intelligence.decision_bias": 1,
                "feature_states.volatility": 1,
                "feature_states.trend": 1,
            },
        )
        for h in cursor:
            history_by_pid[h["prediction_id"]] = h

    joined: List[Dict[str, Any]] = []
    for d in debug_records:
        pid = d.get("prediction_id")
        h = history_by_pid.get(pid) or {}
        decision = h.get("decision_intelligence") or {}
        feature_states = h.get("feature_states") or {}
        outcome = h.get("outcome") or {}
        joined.append({
            "prediction_id": pid,
            "symbol": (d.get("symbol") or "").upper(),
            "tf": (d.get("tf") or "").upper(),
            "candle_close_ts": d.get("candle_close_ts"),
            "analyzed_at": d.get("analyzed_at"),
            "evaluated_at": outcome.get("evaluated_at"),
            "created_at": h.get("created_at"),
            "error_type": d.get("error_type"),
            "root_cause_primary": d.get("root_cause_primary"),
            "no_edge_ignored": bool(d.get("no_edge_ignored")),
            "signal_strength": d.get("signal_strength"),
            "interaction_type": d.get("interaction_type"),
            "primary_scenario": d.get("primary_scenario"),
            "confidence_bucket": d.get("confidence_bucket"),
            "decision_bias": decision.get("decision_bias"),
            "volatility_state": feature_states.get("volatility"),
            "trend_state": feature_states.get("trend"),
        })
    return joined


def _axis_label(record: Dict[str, Any], axis: str) -> str:
    if axis == "symbol_tf":
        sym = record.get("symbol") or ""
        tf = record.get("tf") or ""
        if not sym or not tf:
            return "unknown"
        return f"{sym}_{tf}"
    if axis == "interaction_type":
        return _norm(record.get("interaction_type"))
    if axis == "signal_strength":
        return _norm(record.get("signal_strength"))
    if axis == "decision_bias":
        return _norm(record.get("decision_bias"))
    if axis == "volatility_state":
        return _norm(record.get("volatility_state"))
    if axis == "trend_state":
        return _norm(record.get("trend_state"))
    return "unknown"


def _cohort_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure: build the locked cohort contract for a list of joined records."""
    n = len(records)
    error_records = [r for r in records if _is_error(r)]
    error_count = len(error_records)
    error_rate = round(error_count / n, 6) if n > 0 else 0.0

    distribution: Dict[str, int] = {}
    if error_count == 0:
        return {
            "n": n,
            "error_count": 0,
            "error_rate": 0.0,
            "top_cause": None,
            "top_cause_share": 0.0,
            "concentration": 0.0,
            "stability": 0.0,
            "actionable": False,
            "distribution": {},
        }
    distribution = build_distribution(
        (r.get("root_cause_primary") or "unknown_cause") for r in error_records
    )
    top_cause, top_share = compute_top_share(distribution)
    concentration = compute_hhi(distribution)
    stability = compute_stability(records, cohort_concentration=concentration)
    return {
        "n": n,
        "error_count": error_count,
        "error_rate": error_rate,
        "top_cause": top_cause or None,
        "top_cause_share": round(float(top_share), 6),
        "concentration": round(float(concentration), 6),
        "stability": round(float(stability), 6),
        # actionable filled by weakness_detector layer; mirror here for ergonomics
        "actionable": False,
        "distribution": distribution,
    }


def build_cohorts(joined: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Build per-axis cohort summaries.

    Returns:
        { axis: { cohort_label: cohort_summary, ... }, ... }

    The 'actionable' field is set to False here; weakness_detector flips it
    based on the locked four-condition rule.
    """
    by_axis: Dict[str, Dict[str, Dict[str, Any]]] = {a: {} for a in AXES}
    if not joined:
        return by_axis

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for rec in joined:
        for axis in AXES:
            label = _axis_label(rec, axis)
            grouped[(axis, label)].append(rec)

    for (axis, label), records in grouped.items():
        by_axis[axis][label] = _cohort_summary(records)

    return by_axis


def build_global(joined: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Global error distribution + concentration across all debug records."""
    error_records = [r for r in joined if _is_error(r)]
    distribution = build_distribution(
        (r.get("root_cause_primary") or "unknown_cause") for r in error_records
    )
    return {
        "total_debug_records": len(joined),
        "total_error_records": len(error_records),
        "concentration_global": compute_hhi(distribution),
        "global_distribution_top10": dict(
            sorted(distribution.items(), key=lambda kv: -kv[1])[:10]
        ),
    }


def load_joined_records(db: Any) -> List[Dict[str, Any]]:
    """Public helper for the service / tests."""
    return _join_records(db)
