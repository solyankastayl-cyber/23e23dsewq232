"""
Root Cause Aggregator — detector for repeating systemic weaknesses.

Not a dashboard. Surfaces cohorts where ONE root cause dominates, the
domination is temporally stable, and the cohort has enough errors to
matter. These are the actionable weaknesses ML or a human should fix.

Live-only, read-only.

HARD CONTRACT:
    MAY:
        * read ta_prediction_debug
        * read ta_prediction_history
    MUST NOT:
        * write any collection
        * mutate debug / history / dataset / ML readiness / data health
        * alter taxonomy or any pipeline formula
"""
from .types import (
    AXES,
    Axis,
    AGGREGATOR_VERSION,
    AGGREGATOR_BUILDER_VERSION,
    MIN_COHORT,
    MIN_ERROR_RATE,
    MIN_CONCENTRATION,
    MIN_STABILITY,
    NON_ERROR_TYPES,
    STABILITY_SPLIT_MIN,
)
from .concentration import compute_hhi, compute_top_share
from .stability import compute_stability
from .weakness_detector import is_actionable, build_weakness_record
from .cohort_builder import build_cohorts, build_global
from .aggregator_service import compute_root_cause_report

__all__ = [
    "AXES",
    "Axis",
    "AGGREGATOR_VERSION",
    "AGGREGATOR_BUILDER_VERSION",
    "MIN_COHORT",
    "MIN_ERROR_RATE",
    "MIN_CONCENTRATION",
    "MIN_STABILITY",
    "NON_ERROR_TYPES",
    "STABILITY_SPLIT_MIN",
    "compute_hhi",
    "compute_top_share",
    "compute_stability",
    "is_actionable",
    "build_weakness_record",
    "build_cohorts",
    "build_global",
    "compute_root_cause_report",
]
