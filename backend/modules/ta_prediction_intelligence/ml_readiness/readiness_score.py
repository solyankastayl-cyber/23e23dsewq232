"""
Final score, status mapping, and recommendation logic. Pure.

Final score:
    score = sum(weight * component_score for each of 5 components), clamped 0..1

Status thresholds (after hard gates):
    score >= 0.85 → ready
    score >= 0.70 → almost_ready
    score >= 0.40 → partial
    else            → not_ready

Hard gates override status to NOT_READY when triggered.

Recommendation precedence (first match wins):
    data_health_broken         → fix_data_health
    feature_integrity_low      → fix_feature_pipeline
    low_total_samples
        OR insufficient_debug_samples → collect_more_data
    unstable_error_patterns    → collect_more_debug_cases
    status in {ready, almost_ready} → prepare_trainer
    else                        → continue_observation
"""
from __future__ import annotations

from typing import Dict, List

from .types import (
    ALMOST_READY_THRESHOLD,
    BlockingFactor,
    PARTIAL_THRESHOLD,
    READY_THRESHOLD,
    Recommendation,
    Status,
    WEIGHTS,
)


def compute_final_score(components: Dict[str, float]) -> float:
    total = 0.0
    for k, w in WEIGHTS.items():
        v = components.get(k)
        if v is None:
            continue
        try:
            total += float(v) * w
        except (TypeError, ValueError):
            continue
    return round(max(0.0, min(1.0, total)), 4)


def derive_status(score: float, hard_gate_triggered: bool) -> Status:
    if hard_gate_triggered:
        return Status.NOT_READY
    if score >= READY_THRESHOLD:
        return Status.READY
    if score >= ALMOST_READY_THRESHOLD:
        return Status.ALMOST_READY
    if score >= PARTIAL_THRESHOLD:
        return Status.PARTIAL
    return Status.NOT_READY


def derive_recommendation(
    status: Status, blocking_factors: List[str]
) -> Recommendation:
    bf = set(blocking_factors)
    if BlockingFactor.DATA_HEALTH_BROKEN.value in bf:
        return Recommendation.FIX_DATA_HEALTH
    if (
        BlockingFactor.FEATURE_INTEGRITY_LOW.value in bf
        or BlockingFactor.FEATURE_INTEGRITY_UNKNOWN.value in bf
    ):
        return Recommendation.FIX_FEATURE_PIPELINE
    if (
        BlockingFactor.LOW_TOTAL_SAMPLES.value in bf
        or BlockingFactor.INSUFFICIENT_DEBUG_SAMPLES.value in bf
    ):
        return Recommendation.COLLECT_MORE_DATA
    if BlockingFactor.UNSTABLE_ERROR_PATTERNS.value in bf:
        return Recommendation.COLLECT_MORE_DEBUG_CASES
    if status in (Status.ALMOST_READY, Status.READY):
        return Recommendation.PREPARE_TRAINER
    return Recommendation.CONTINUE_OBSERVATION
