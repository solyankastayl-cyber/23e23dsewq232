"""
Locked typed primitives — enums, weights, thresholds, expected sets.

All constants here are LOCKED per spec. Touching any of them requires a
ML_READINESS_VERSION bump and a new QA run.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List

ML_READINESS_VERSION = "v1"
ML_READINESS_BUILDER_VERSION = "1.0.0"

# ─── Hard gate constants ─────────────────────────────────────────────────────
MIN_TOTAL_SAMPLES = 50                        # hard gate B: total<50 → not_ready
FEATURE_INTEGRITY_GATE = 0.90                 # hard gate C
DATA_HEALTH_BROKEN = "broken"                 # hard gate A

# ─── Sample-quality constants ──────────────────────────────────────────────────
TARGET_TOTAL_SAMPLES = 500                    # full credit when reached
MIN_BUCKET_SIZE = 20                          # below this → 'blind buckets'
TRACKED_PAIRS: List[str] = [
    "ETHUSDT_1H",
    "BTCUSDT_1H",
    "SOLUSDT_1H",
]

# ─── Class balance ──────────────────────────────────────────────────────────────────
SEVERE_CLASS_THRESHOLD = 0.70                 # any single class > this → imbalance flag

# ─── Error stability ───────────────────────────────────────────────────────────────
MIN_DEBUG_SAMPLES = 30                        # below this → component=0 + blocking
DOMINANCE_TARGET_SHARE = 0.40                 # dominant cause should be ≥ 40%
NO_DOMINANT_THRESHOLD = 0.25                  # blocking if max share < this
UNSTABLE_ENTROPY_THRESHOLD = 0.70             # blocking if normalized entropy > this

# ─── Regime coverage ───────────────────────────────────────────────────────────────
EXPECTED_VOLATILITY_STATES: List[str] = [
    "compression", "normal", "expansion", "chaos",
]
EXPECTED_TREND_STATES: List[str] = [
    "range", "weak_trend", "strong_trend", "exhaustion",
]
EXPECTED_INTERACTION_TYPES: List[str] = [
    "trend_continuation", "pullback", "rejection", "breakout",
    "fake_breakout", "early_reversal", "compression", "expansion_chaos",
]
REGIME_COVERAGE_BLOCKING_THRESHOLD = 0.35     # blocking if coverage < this AND total>=100
REGIME_COVERAGE_BLOCKING_MIN_TOTAL = 100

# ─── Weights & thresholds ──────────────────────────────────────────────────────────
WEIGHTS: Dict[str, float] = {
    "sample_quality":    0.30,
    "feature_integrity": 0.25,
    "class_balance":     0.15,
    "error_stability":   0.20,
    "regime_coverage":   0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"

READY_THRESHOLD = 0.85
ALMOST_READY_THRESHOLD = 0.70
PARTIAL_THRESHOLD = 0.40


class Status(str, Enum):
    NOT_READY = "not_ready"
    PARTIAL = "partial"
    ALMOST_READY = "almost_ready"
    READY = "ready"


class Recommendation(str, Enum):
    FIX_DATA_HEALTH = "fix_data_health"
    FIX_FEATURE_PIPELINE = "fix_feature_pipeline"
    COLLECT_MORE_DATA = "collect_more_data"
    COLLECT_MORE_DEBUG_CASES = "collect_more_debug_cases"
    PREPARE_TRAINER = "prepare_trainer"
    CONTINUE_OBSERVATION = "continue_observation"


class BlockingFactor(str, Enum):
    DATA_HEALTH_BROKEN = "data_health_broken"
    LOW_TOTAL_SAMPLES = "low_total_samples"
    BLIND_BUCKETS = "blind_buckets"
    SEVERE_CLASS_IMBALANCE = "severe_class_imbalance"
    INSUFFICIENT_DEBUG_SAMPLES = "insufficient_debug_samples"
    UNSTABLE_ERROR_PATTERNS = "unstable_error_patterns"
    NO_DOMINANT_FAILURE_MODE = "no_dominant_failure_mode"
    FEATURE_INTEGRITY_LOW = "feature_integrity_low"
    FEATURE_INTEGRITY_UNKNOWN = "feature_integrity_unknown"
    REGIME_COVERAGE_LOW = "regime_coverage_low"
