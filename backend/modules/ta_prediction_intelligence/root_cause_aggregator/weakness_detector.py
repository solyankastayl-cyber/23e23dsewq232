"""
Actionable weakness detector — the only place that decides if a cohort
becomes a "flag for the architect".

LOCKED rule (all four conditions, AND):
    cohort.n             >= 20
    cohort.error_rate    >= 0.50
    cohort.concentration >= 0.30
    cohort.stability     >= 0.70
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .types import (
    MIN_COHORT,
    MIN_CONCENTRATION,
    MIN_ERROR_RATE,
    MIN_STABILITY,
)


def is_actionable(cohort: Dict[str, Any]) -> bool:
    if not cohort:
        return False
    if cohort.get("top_cause") in (None, "", "unknown_cause"):
        return False
    return (
        int(cohort.get("n") or 0) >= MIN_COHORT
        and float(cohort.get("error_rate") or 0.0) >= MIN_ERROR_RATE
        and float(cohort.get("concentration") or 0.0) >= MIN_CONCENTRATION
        and float(cohort.get("stability") or 0.0) >= MIN_STABILITY
    )


def _suggested_action(axis: str, cohort_label: str, cause: str) -> str:
    return f"Investigate {cause} in {axis}={cohort_label}."


def build_weakness_record(
    axis: str, cohort_label: str, cohort: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Build the locked actionable_weakness contract or None if not actionable."""
    if not is_actionable(cohort):
        return None
    return {
        "axis": axis,
        "cohort": cohort_label,
        "n": cohort.get("n"),
        "error_rate": cohort.get("error_rate"),
        "top_cause": cohort.get("top_cause"),
        "top_cause_share": cohort.get("top_cause_share"),
        "concentration": cohort.get("concentration"),
        "stability": cohort.get("stability"),
        "rationale": "Root cause is concentrated and temporally stable.",
        "suggested_action": _suggested_action(
            axis, cohort_label, cohort.get("top_cause") or "unknown_cause"
        ),
    }


def collect_actionable(
    by_axis: Dict[str, Dict[str, Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Flatten by_axis into a ranked list of actionable weaknesses.

    Sort key: (concentration descending, error_rate descending, n descending,
    cohort label asc) — strongest signal first, ties broken deterministically.
    Also flips cohort.actionable=True in place.
    """
    out: List[Dict[str, Any]] = []
    for axis, cohorts in by_axis.items():
        for label, cohort in cohorts.items():
            wk = build_weakness_record(axis, label, cohort)
            if wk is not None:
                cohort["actionable"] = True
                out.append(wk)
    out.sort(
        key=lambda w: (
            -float(w.get("concentration") or 0.0),
            -float(w.get("error_rate") or 0.0),
            -int(w.get("n") or 0),
            str(w.get("axis") or ""),
            str(w.get("cohort") or ""),
        )
    )
    return out
