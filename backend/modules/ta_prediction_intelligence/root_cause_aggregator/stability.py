"""
Temporal stability — “does the same root cause dominate baseline AND recent?”

Algorithm (from spec):
    1. sort cohort by analyzed_at (asc)
    2. split into baseline = first half, recent = second half
    3. compute top_cause on the *error* sub-cohort of each half
    4. if top is the same in both halves → stability = 1.0
       else                                → stability = recent_top_share

If the cohort is too small to split (n < STABILITY_SPLIT_MIN), the function
falls back to `concentration` so we never pretend temporal stability we
haven't measured.

If there are no errors at all, stability = 0.0 (cohort is silent on root
causes).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .concentration import build_distribution, compute_top_share
from .types import NON_ERROR_TYPES, STABILITY_SPLIT_MIN


def _is_error(record: Dict[str, Any]) -> bool:
    return (record.get("error_type") or "") not in NON_ERROR_TYPES


def _record_cause(record: Dict[str, Any]) -> Optional[str]:
    cause = record.get("root_cause_primary")
    if not cause:
        return "unknown_cause"
    return str(cause)


def _sort_key(r: Dict[str, Any]):
    # analyzed_at → falls back to evaluated_at, then created_at, then prediction_id.
    return (
        r.get("analyzed_at") or r.get("evaluated_at") or r.get("created_at") or 0,
        r.get("prediction_id") or "",
    )


def compute_stability(
    cohort_records: List[Dict[str, Any]],
    *,
    cohort_concentration: float,
) -> float:
    """
    Pure. Inputs:
        cohort_records: ALL debug records in the cohort (incl. correct/underconf)
        cohort_concentration: HHI computed on the error distribution

    Returns stability ∈ [0, 1].
    """
    if not cohort_records:
        return 0.0

    # Pre-filter errors
    error_records = [r for r in cohort_records if _is_error(r)]
    if not error_records:
        return 0.0

    n = len(cohort_records)
    if n < STABILITY_SPLIT_MIN:
        # Spec: small cohort → fall back to concentration (don't fake temporal).
        return float(cohort_concentration)

    # Sort the FULL cohort by time and split halves on the full cohort,
    # then compute top_cause on the *error* sub-cohort of each half.
    sorted_full = sorted(cohort_records, key=_sort_key)
    half = len(sorted_full) // 2
    baseline = sorted_full[:half]
    recent = sorted_full[half:]

    baseline_errors = [r for r in baseline if _is_error(r)]
    recent_errors = [r for r in recent if _is_error(r)]

    if not baseline_errors or not recent_errors:
        # One half is silent on errors — stability collapses to concentration.
        return float(cohort_concentration)

    base_dist = build_distribution(_record_cause(r) for r in baseline_errors)
    recent_dist = build_distribution(_record_cause(r) for r in recent_errors)

    base_top, _ = compute_top_share(base_dist)
    recent_top, recent_top_share = compute_top_share(recent_dist)

    if base_top and recent_top and base_top == recent_top:
        return 1.0
    return float(recent_top_share)
