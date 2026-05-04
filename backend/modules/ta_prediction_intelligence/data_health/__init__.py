"""
Data Health Layer — read-only quality monitor for the TA prediction stack.

HARD CONTRACT:
    DATA HEALTH MAY:
        * read ta_prediction_history
        * read ta_prediction_debug
        * read ta_prediction_dataset
        * read ta_prediction_temporal_buffer
        * read ta_prediction_calibration_stats
        * read FEATURE_SCHEMA_HASH constant (read-only import)

    DATA HEALTH MUST NOT:
        * mutate any source collection
        * alter pipeline
        * influence prediction / decision / dataset / debug taxonomy
        * trigger outcome evaluation, calibration, or buffer flushes

The layer composes a single trust score and a status
(`healthy | degraded | broken`) so the operator never has to read raw
Mongo to know whether the pipeline is shippable.
"""
from .types import (
    Severity,
    IssueCode,
    Status,
    Recommendation,
    HealthIssue,
    DATA_HEALTH_VERSION,
)
from .trust_score import (
    compute_trust_score,
    derive_status,
    derive_recommendation,
    TRUST_HEALTHY_MIN,
    TRUST_DEGRADED_MIN,
)
from .health_service import compute_health_report

__all__ = [
    "Severity",
    "IssueCode",
    "Status",
    "Recommendation",
    "HealthIssue",
    "DATA_HEALTH_VERSION",
    "compute_trust_score",
    "derive_status",
    "derive_recommendation",
    "TRUST_HEALTHY_MIN",
    "TRUST_DEGRADED_MIN",
    "compute_health_report",
]
