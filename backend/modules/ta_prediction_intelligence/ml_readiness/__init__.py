"""
ML Readiness Layer — read-only.

Answers ONE question:
    “If I run the trainer right now, will the model learn or break?”

Not a function of sample_count alone. Combines five signal components
weighted per the locked spec, gated by data-health and feature integrity.

HARD CONTRACT (read-only, like Data Health):
    MAY:
        * read ta_prediction_history
        * read ta_prediction_dataset
        * read ta_prediction_debug
        * call compute_health_report() (which is itself read-only)
    MUST NOT:
        * mutate any source collection
        * persist its own collection (v1 is live-only)
        * influence prediction / decision / dataset / debug taxonomy
"""
from .types import (
    BlockingFactor,
    Recommendation,
    Status,
    DATA_HEALTH_BROKEN,
    EXPECTED_INTERACTION_TYPES,
    EXPECTED_TREND_STATES,
    EXPECTED_VOLATILITY_STATES,
    MIN_BUCKET_SIZE,
    MIN_DEBUG_SAMPLES,
    MIN_TOTAL_SAMPLES,
    SEVERE_CLASS_THRESHOLD,
    TARGET_TOTAL_SAMPLES,
    TRACKED_PAIRS,
    UNSTABLE_ENTROPY_THRESHOLD,
    NO_DOMINANT_THRESHOLD,
    REGIME_COVERAGE_BLOCKING_THRESHOLD,
    REGIME_COVERAGE_BLOCKING_MIN_TOTAL,
    FEATURE_INTEGRITY_GATE,
    WEIGHTS,
    READY_THRESHOLD,
    ALMOST_READY_THRESHOLD,
    PARTIAL_THRESHOLD,
    ML_READINESS_VERSION,
)
from .readiness_score import (
    compute_final_score,
    derive_status,
    derive_recommendation,
)
from .readiness_service import compute_readiness_report

__all__ = [
    "BlockingFactor",
    "Recommendation",
    "Status",
    "DATA_HEALTH_BROKEN",
    "EXPECTED_INTERACTION_TYPES",
    "EXPECTED_TREND_STATES",
    "EXPECTED_VOLATILITY_STATES",
    "MIN_BUCKET_SIZE",
    "MIN_DEBUG_SAMPLES",
    "MIN_TOTAL_SAMPLES",
    "SEVERE_CLASS_THRESHOLD",
    "TARGET_TOTAL_SAMPLES",
    "TRACKED_PAIRS",
    "UNSTABLE_ENTROPY_THRESHOLD",
    "NO_DOMINANT_THRESHOLD",
    "REGIME_COVERAGE_BLOCKING_THRESHOLD",
    "REGIME_COVERAGE_BLOCKING_MIN_TOTAL",
    "FEATURE_INTEGRITY_GATE",
    "WEIGHTS",
    "READY_THRESHOLD",
    "ALMOST_READY_THRESHOLD",
    "PARTIAL_THRESHOLD",
    "ML_READINESS_VERSION",
    "compute_final_score",
    "derive_status",
    "derive_recommendation",
    "compute_readiness_report",
]
