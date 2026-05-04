"""
Calibration Engine (Step 7) — pure functions, deterministic statistics.

Groups historical predictions with outcomes by a dimension (interaction_type,
dominant_engine, scenario_name, or composite) and produces:
  * per-bucket hit-rate for each scenario (bull/base/bear)
  * avg predicted probability per scenario
  * Brier score (multi-class) per bucket
  * Wilson CI (95%) around hit-rates
  * sample size + coverage fields

No ML, no randomness, no I/O. Caller handles persistence.

Scenarios are treated as a 3-class system: {bull, base, bear}. The winning
scenario for each prediction is derived by the outcome worker and stored at
`prediction.outcome.winning_scenario`. If outcome is missing or invalid,
the record is skipped.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCENARIOS = ("bull", "base", "bear")


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _bucket_key_for_record(record: Dict[str, Any], group_by: str) -> Optional[str]:
    if group_by == "interaction_type":
        inter = record.get("interaction")
        if not inter:
            return "__none__"
        return str(inter.get("type") or "__none__")
    if group_by == "dominant_engine":
        return str(record.get("dominant_engine") or "__none__")
    if group_by == "symbol_tf":
        s = str(record.get("symbol") or "")
        t = str(record.get("timeframe") or "")
        return f"{s}:{t}" if s or t else "__none__"
    if group_by == "symbol_tf_interaction":
        s = str(record.get("symbol") or "")
        t = str(record.get("timeframe") or "")
        inter = record.get("interaction")
        it = str((inter or {}).get("type") or "__none__")
        return f"{s}:{t}:{it}"
    return None


def _get_scenarios_for_predicted(record: Dict[str, Any]) -> Dict[str, float]:
    """
    Pick the probability distribution we calibrate AGAINST. We use the
    interaction-adjusted scenarios (Step 6 output, i.e. PRE-calibration),
    because that is what the calibration layer transforms.
    Falls back to originals if missing.
    """
    scenarios = record.get("scenarios_interaction_adjusted") or record.get(
        "scenarios_original"
    ) or []
    probs = {s: 0.0 for s in SCENARIOS}
    for sc in scenarios:
        name = str(sc.get("name") or "").lower()
        if name in probs:
            probs[name] = _safe_float(sc.get("probability"), 0.0)
    return probs


def _one_hot_outcome(winner: Optional[str]) -> Dict[str, float]:
    winner = (winner or "").lower()
    out = {s: 0.0 for s in SCENARIOS}
    if winner in out:
        out[winner] = 1.0
    return out


def _wilson_interval(hits: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval (95% default). Returns (lower, upper)."""
    if n <= 0:
        return (0.0, 0.0)
    phat = hits / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (lo, hi)


def aggregate_calibration(
    records: Iterable[Dict[str, Any]],
    *,
    group_by: str = "interaction_type",
) -> List[Dict[str, Any]]:
    """
    Aggregate calibration metrics per bucket for group_by dimension.

    Returns a list of dicts, one per bucket:
      {
        bucket_key: str,
        n: int,
        hit_rate: {bull, base, bear},
        avg_predicted: {bull, base, bear},
        calibration_gap: {bull, base, bear},   # hit_rate - avg_predicted
        brier_score: float,
        wilson_lower: {bull, base, bear},
        wilson_upper: {bull, base, bear},
        winners: {bull, base, bear},            # absolute counts
      }
    """
    buckets: Dict[str, Dict[str, Any]] = {}

    for r in records or []:
        outcome = r.get("outcome") or {}
        winner = outcome.get("winning_scenario")
        if not winner:
            continue
        key = _bucket_key_for_record(r, group_by)
        if key is None:
            continue

        predicted = _get_scenarios_for_predicted(r)
        actual = _one_hot_outcome(winner)

        b = buckets.setdefault(
            key,
            {
                "n": 0,
                "sum_predicted": {s: 0.0 for s in SCENARIOS},
                "winners": {s: 0 for s in SCENARIOS},
                "brier_sum": 0.0,
            },
        )
        b["n"] += 1
        for s in SCENARIOS:
            b["sum_predicted"][s] += predicted.get(s, 0.0)
            b["winners"][s] += int(actual[s])
            diff = predicted.get(s, 0.0) - actual[s]
            b["brier_sum"] += diff * diff

    out: List[Dict[str, Any]] = []
    for key, b in buckets.items():
        n = int(b["n"])
        hit_rate = {s: (b["winners"][s] / n if n > 0 else 0.0) for s in SCENARIOS}
        avg_predicted = {
            s: (b["sum_predicted"][s] / n if n > 0 else 0.0) for s in SCENARIOS
        }
        calibration_gap = {
            s: round(hit_rate[s] - avg_predicted[s], 6) for s in SCENARIOS
        }
        brier = (b["brier_sum"] / n) if n > 0 else 0.0
        wilson_lower: Dict[str, float] = {}
        wilson_upper: Dict[str, float] = {}
        for s in SCENARIOS:
            lo, hi = _wilson_interval(b["winners"][s], n)
            wilson_lower[s] = round(lo, 6)
            wilson_upper[s] = round(hi, 6)
        out.append(
            {
                "bucket_key": key,
                "n": n,
                "hit_rate": {k: round(v, 6) for k, v in hit_rate.items()},
                "avg_predicted": {k: round(v, 6) for k, v in avg_predicted.items()},
                "calibration_gap": calibration_gap,
                "brier_score": round(brier, 6),
                "wilson_lower": wilson_lower,
                "wilson_upper": wilson_upper,
                "winners": dict(b["winners"]),
            }
        )
    # Stable ordering: largest bucket first
    out.sort(key=lambda d: d["n"], reverse=True)
    return out


def rebuild_all(records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Run aggregate_calibration for every canonical group_by dimension."""
    records_list = list(records or [])
    return {
        "interaction_type": aggregate_calibration(records_list, group_by="interaction_type"),
        "dominant_engine": aggregate_calibration(records_list, group_by="dominant_engine"),
        "symbol_tf": aggregate_calibration(records_list, group_by="symbol_tf"),
        "symbol_tf_interaction": aggregate_calibration(
            records_list, group_by="symbol_tf_interaction"
        ),
    }
