"""
Trust score = weighted average of block scores (each in [0, 1]).

Weights are LOCKED. Status mapping is also locked:
    HEALTHY  : trust >= 0.75 AND no critical issue
    DEGRADED : trust >= 0.45 OR only warnings exist
    BROKEN   : critical issue exists OR trust < 0.45

Recommendation:
    BROKEN          → fix_pipeline
    HEALTHY + n<100 evaluated  → collect_more_data
    HEALTHY + n>=100           → safe_to_train_later
    DEGRADED                   → hold
"""
from __future__ import annotations

from typing import Any, Dict, Iterable

from .types import (
    HealthIssue,
    Recommendation,
    Severity,
    Status,
)

TRUST_HEALTHY_MIN = 0.75
TRUST_DEGRADED_MIN = 0.45

# Block weights (sum = 1.0)
_BLOCK_WEIGHTS: Dict[str, float] = {
    "pipeline": 0.35,
    "features": 0.25,
    "outcomes": 0.20,
    "debug":    0.10,
    "drift":    0.10,
}


def compute_trust_score(block_scores: Dict[str, float]) -> float:
    total_w = 0.0
    acc = 0.0
    for block, w in _BLOCK_WEIGHTS.items():
        score = block_scores.get(block)
        if score is None:
            continue
        try:
            acc += float(score) * w
            total_w += w
        except (TypeError, ValueError):
            continue
    if total_w <= 0:
        return 0.0
    return round(acc / total_w, 4)


def _has_critical(issues: Iterable[HealthIssue]) -> bool:
    return any(i.severity == Severity.CRITICAL for i in issues)


def derive_status(
    trust_score: float, issues: Iterable[HealthIssue]
) -> Status:
    issues = list(issues)
    if _has_critical(issues):
        return Status.BROKEN
    if trust_score < TRUST_DEGRADED_MIN:
        return Status.BROKEN
    if trust_score >= TRUST_HEALTHY_MIN:
        return Status.HEALTHY
    return Status.DEGRADED


def derive_recommendation(
    status: Status, evaluated_count: int
) -> Recommendation:
    if status == Status.BROKEN:
        return Recommendation.FIX_PIPELINE
    if status == Status.HEALTHY:
        if evaluated_count < 100:
            return Recommendation.COLLECT_MORE_DATA
        return Recommendation.SAFE_TO_TRAIN_LATER
    return Recommendation.HOLD
