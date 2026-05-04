"""
Data Health typed primitives — enums, dataclasses, locked constants.

These are the ONLY contract surface for issue codes / severity values.
Do not introduce new codes without bumping DATA_HEALTH_VERSION.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

DATA_HEALTH_VERSION = "v1"
DATA_HEALTH_BUILDER_VERSION = "1.0.0"

# Time horizons (seconds)
OLD_PENDING_AGE_SECONDS = 24 * 3600                # pending older than 24h is suspect
DRIFT_RECENT_WINDOW = 50                            # last N evaluated records form recent
DRIFT_BASELINE_WINDOW = 500                         # all evaluated up to this many
MIN_BASELINE_FOR_DRIFT = 30                         # below this we don't trust drift output

# Tolerance thresholds (locked)
THR_LOW_EVALUATED_RATIO = 0.10                      # warning if <10% evaluated
THR_OLD_PENDING_RATIO = 0.30                        # warning if >30% pending are stale
THR_FEATURE_SCHEMA_MISMATCH = 0.05                  # critical if >5% mismatch
THR_MISSING_ENGINES_RATE = 0.10                     # critical if >10% have missing engines
THR_OUTCOME_INCOMPLETE = 0.10                       # critical if >10% incomplete outcomes
THR_DEBUG_COVERAGE = 0.50                           # critical if <50% with eval_count>20
THR_DEBUG_COVERAGE_MIN_EVAL = 20                    # only enforce coverage above this
THR_VOL_PROXY_USAGE = 0.50                          # warning if >50% vol_future==0 (proxied)

# Drift sensitivity (relative change against baseline mean)
THR_DRIFT_RELATIVE = 0.30                           # >30% drift in either direction
THR_DRIFT_ABSOLUTE = 0.10                           # min absolute change to flag (anti-noise)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Status(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"


class Recommendation(str, Enum):
    FIX_PIPELINE = "fix_pipeline"                   # critical issues exist
    COLLECT_MORE_DATA = "collect_more_data"         # healthy but n too small
    SAFE_TO_TRAIN_LATER = "safe_to_train_later"     # healthy + sufficient data
    HOLD = "hold"                                   # degraded — wait & monitor


class IssueCode(str, Enum):
    # ── Pipeline
    NO_PREDICTIONS = "no_predictions"
    LOW_EVALUATED_RATIO = "low_evaluated_ratio"
    EVALUATED_ZERO_BUT_PENDING = "evaluated_zero_but_pending"
    HIGH_OLD_PENDING_RATIO = "high_old_pending_ratio"
    EVALUATION_LAG_HIGH = "evaluation_lag_high"
    OUTCOME_WORKER_STALE = "outcome_worker_stale"
    # ── Features
    FEATURE_SCHEMA_MISMATCH = "feature_schema_mismatch"
    MISSING_FEATURES_RATE_HIGH = "missing_features_rate_high"
    FEATURE_HASH_DUPLICATE_RATE_HIGH = "feature_hash_duplicate_rate_high"
    FEATURE_COMPLETENESS_LOW = "feature_completeness_low"
    # ── Outcomes
    OUTCOME_INCOMPLETE_RATE_HIGH = "outcome_incomplete_rate_high"
    VOLATILITY_PROXY_OVERUSE = "volatility_proxy_overuse"
    WINNING_SCENARIO_SKEWED = "winning_scenario_skewed"
    # ── Debug
    DEBUG_COVERAGE_LOW = "debug_coverage_low"
    OVERCONFIDENCE_RATE_HIGH = "overconfidence_rate_high"
    UNDERCONFIDENCE_RATE_HIGH = "underconfidence_rate_high"
    # ── Drift
    FEATURE_DRIFT_DETECTED = "feature_drift_detected"
    DECISION_CONF_DRIFT = "decision_conf_drift"
    CONFLICT_DRIFT = "conflict_drift"


@dataclass
class HealthIssue:
    code: IssueCode
    severity: Severity
    message: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "meta": self.meta,
        }


@dataclass
class CheckResult:
    """Per-block result — each health check returns one."""
    block: str                                   # 'pipeline' | 'features' | 'outcomes' | 'debug' | 'drift'
    score: float                                 # in [0, 1]; weight comes from trust_score module
    issues: list                                 # list[HealthIssue]
    metrics: Dict[str, Any]                      # raw numbers for the API
    sample_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block": self.block,
            "score": round(float(self.score), 4),
            "sample_size": self.sample_size,
            "metrics": self.metrics,
            "issues": [i.to_dict() for i in self.issues],
        }
