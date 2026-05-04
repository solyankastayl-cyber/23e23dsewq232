"""
Scenario × Calibration Adjuster (Step 7)
=========================================

Pure post-processing layer that takes:

    1) scenarios ALREADY produced by scenario_interaction_adjuster (Step 6)
       — i.e. probabilities reflect the interaction layer's interpretation.

    2) calibration stats (produced by calibration_engine.aggregate_calibration)
       for the relevant bucket(s).

…and returns a NEW scenarios list with probabilities adjusted to reflect
historical hit-rate vs average-predicted gaps.

ARCHITECTURAL CONTRACT (locked):
--------------------------------
* DOES NOT touch engines, aggregator, conflict_resolver, scenario_builder,
  interaction rules, or the Step-6 interaction adjuster.
* DOES NOT mutate input scenarios. Returns new dicts.
* Honest: if no bucket has `n >= MIN_SAMPLES`, returns scenarios AS-IS
  with `meta.applied=false` and a clear reason.
* Bounded:
    - per-scenario |delta| <= PER_DELTA_CAP (0.08)
    - sum |delta|       <= TOTAL_DELTA_CAP (0.20)
    - floor/ceil         in [PROB_FLOOR (0.02) .. PROB_CEIL (0.92)]
    - re-normalised to sum=1.0
* Deterministic: no random, no ML — pure table lookup + linear map.
* The calibration delta uses `calibration_gap = hit_rate - avg_predicted`
  from the stats bucket, which is already produced deterministically by the
  calibration engine on historical records.

Bucket resolution ladder (most specific → most general):
    1. symbol_tf_interaction (e.g. "ETHUSDT:1H:pullback")
    2. symbol_tf             (e.g. "ETHUSDT:1H")
    3. interaction_type      (e.g. "pullback")
First bucket with `n >= MIN_SAMPLES` wins.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

MIN_SAMPLES = 30
PER_DELTA_CAP = 0.08
TOTAL_DELTA_CAP = 0.20
PROB_FLOOR = 0.02
PROB_CEIL = 0.92

_SCENARIOS = ("bull", "base", "bear")


def _clip(x: float, lo: float, hi: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return lo
    return lo if v < lo else (hi if v > hi else v)


def _find_bucket(
    stats_by_group: Dict[str, List[Dict[str, Any]]],
    context: Dict[str, Any],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    symbol = (context.get("symbol") or "").upper()
    tf = (context.get("timeframe") or "").upper()
    itype = str(context.get("interaction_type") or "")

    ladder: List[Tuple[str, str]] = []
    if symbol and tf and itype and itype != "__none__":
        ladder.append(("symbol_tf_interaction", f"{symbol}:{tf}:{itype}"))
    if symbol and tf:
        ladder.append(("symbol_tf", f"{symbol}:{tf}"))
    if itype and itype != "__none__":
        ladder.append(("interaction_type", itype))

    for group_by, key in ladder:
        buckets = stats_by_group.get(group_by) or []
        for b in buckets:
            if str(b.get("bucket_key")) == key and int(b.get("n", 0)) >= MIN_SAMPLES:
                return (group_by, b)
    return None


def _cap_total(deltas: Dict[str, float]) -> Dict[str, float]:
    total_abs = sum(abs(v) for v in deltas.values())
    if total_abs <= TOTAL_DELTA_CAP or total_abs <= 0:
        return deltas
    factor = TOTAL_DELTA_CAP / total_abs
    return {k: v * factor for k, v in deltas.items()}


def apply_calibration_adjustment(
    scenarios: List[Dict[str, Any]],
    context: Dict[str, Any],
    stats_by_group: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns (new_scenarios, meta_dict).

    new_scenarios: list of fresh dicts. When calibration applies, each carries
      - probability          : final, renormalised probability (0..1)
      - pre_calibration_probability: pre-calibration value
      - calibration_delta    : final - pre
      - calibrated           : True
    When NOT applied, scenarios are returned with calibrated=False and
    pre_calibration_probability == probability (no change).

    meta_dict keys:
      - applied (bool)
      - reason (str)                      # explanation on skip / when applied
      - group_by (str|None)               # which bucket dimension was used
      - bucket_key (str|None)
      - bucket_n (int)                    # sample size
      - hit_rate (dict|None)
      - avg_predicted (dict|None)
      - calibration_gap (dict|None)
      - brier_score (float|None)
      - per_delta_cap / total_delta_cap / prob_floor / prob_ceil
      - raw_deltas (dict|None)
      - explanation (str)
    """
    # Defensive copies
    base_list: List[Dict[str, Any]] = [dict(s) for s in (scenarios or [])]
    meta_common = {
        "per_delta_cap": PER_DELTA_CAP,
        "total_delta_cap": TOTAL_DELTA_CAP,
        "prob_floor": PROB_FLOOR,
        "prob_ceil": PROB_CEIL,
        "min_samples": MIN_SAMPLES,
    }

    def _tag_unchanged(reason: str, group_by=None, bucket_key=None, bucket_n=0):
        for s in base_list:
            s.setdefault("pre_calibration_probability", s.get("probability"))
            s.setdefault("calibration_delta", 0.0)
            s.setdefault("calibrated", False)
        meta = {
            "applied": False,
            "reason": reason,
            "group_by": group_by,
            "bucket_key": bucket_key,
            "bucket_n": int(bucket_n),
            "hit_rate": None,
            "avg_predicted": None,
            "calibration_gap": None,
            "brier_score": None,
            "raw_deltas": None,
            "explanation": reason,
            **meta_common,
        }
        return base_list, meta

    if not base_list:
        return _tag_unchanged("scenarios_empty")
    if not stats_by_group:
        return _tag_unchanged("no_calibration_stats_available")

    found = _find_bucket(stats_by_group or {}, context or {})
    if not found:
        return _tag_unchanged("insufficient_samples")

    group_by, bucket = found
    bucket_n = int(bucket.get("n", 0))
    calibration_gap = bucket.get("calibration_gap") or {}

    # Build per-scenario deltas, clamped per-scenario by PER_DELTA_CAP.
    deltas: Dict[str, float] = {}
    for s in _SCENARIOS:
        try:
            d = float(calibration_gap.get(s, 0.0) or 0.0)
        except (TypeError, ValueError):
            d = 0.0
        deltas[s] = max(-PER_DELTA_CAP, min(PER_DELTA_CAP, d))
    deltas = _cap_total(deltas)

    # Zero-impact fast path.
    if all(abs(v) <= 1e-9 for v in deltas.values()):
        return _tag_unchanged(
            "calibration_gap_negligible",
            group_by=group_by,
            bucket_key=bucket.get("bucket_key"),
            bucket_n=bucket_n,
        )

    # Apply deltas additively over the pre-calibration probabilities, clip,
    # then renormalise.
    originals: Dict[str, float] = {}
    for s in base_list:
        name = str(s.get("name") or "").lower()
        if name not in _SCENARIOS:
            continue
        try:
            originals[name] = float(s.get("probability") or 0.0)
        except (TypeError, ValueError):
            originals[name] = 0.0

    adjusted: Dict[str, float] = {}
    for name, p in originals.items():
        v = p + deltas.get(name, 0.0)
        v = _clip(v, PROB_FLOOR, PROB_CEIL)
        adjusted[name] = v

    total = sum(adjusted.values())
    if total <= 0:
        return _tag_unchanged(
            "degenerate_total_after_clip",
            group_by=group_by,
            bucket_key=bucket.get("bucket_key"),
            bucket_n=bucket_n,
        )
    normed = {k: v / total for k, v in adjusted.items()}

    for s in base_list:
        name = str(s.get("name") or "").lower()
        if name not in originals:
            s.setdefault("pre_calibration_probability", s.get("probability"))
            s.setdefault("calibration_delta", 0.0)
            s.setdefault("calibrated", False)
            continue
        original = originals[name]
        new_p = normed.get(name, original)
        s["pre_calibration_probability"] = round(original, 6)
        s["probability"] = round(new_p, 6)
        s["calibration_delta"] = round(new_p - original, 6)
        s["calibrated"] = True

    meta = {
        "applied": True,
        "reason": f"applied from {group_by}={bucket.get('bucket_key')} (n={bucket_n})",
        "group_by": group_by,
        "bucket_key": bucket.get("bucket_key"),
        "bucket_n": bucket_n,
        "hit_rate": bucket.get("hit_rate"),
        "avg_predicted": bucket.get("avg_predicted"),
        "calibration_gap": bucket.get("calibration_gap"),
        "brier_score": bucket.get("brier_score"),
        "raw_deltas": {k: round(v, 6) for k, v in deltas.items()},
        "explanation": _explain(group_by, bucket.get("bucket_key"), bucket_n, deltas),
        **meta_common,
    }
    return base_list, meta


def _explain(
    group_by: Optional[str],
    bucket_key: Optional[Any],
    bucket_n: int,
    deltas: Dict[str, float],
) -> str:
    if not group_by:
        return ""
    ups = [k for k, v in deltas.items() if v > 0]
    downs = [k for k, v in deltas.items() if v < 0]
    parts: List[str] = []
    if ups:
        parts.append("↑ " + ",".join(ups))
    if downs:
        parts.append("↓ " + ",".join(downs))
    shape = "; ".join(parts) or "no-op"
    return (
        f"Calibrated from {group_by}={bucket_key} with n={bucket_n} historical "
        f"cases ({shape})."
    )
