"""
Lightweight drift detection — baseline (last DRIFT_BASELINE_WINDOW evaluated)
vs recent (last DRIFT_RECENT_WINDOW). No statistical tests; just relative
shift in means with a noise floor.

Covered keys:
    * features_v1.rsi
    * features_v1.atr_pct
    * conflict_ratio
    * decision_intelligence.decision_confidence
“Drift detected” only when:
    abs(recent_mean - baseline_mean) >= THR_DRIFT_ABSOLUTE_for_key
    AND abs(recent_mean - baseline_mean) / |baseline_mean + eps| >= THR_DRIFT_RELATIVE

Returns CheckResult with one HealthIssue per drifted metric.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional

from .types import (
    CheckResult,
    DRIFT_BASELINE_WINDOW,
    DRIFT_RECENT_WINDOW,
    HealthIssue,
    IssueCode,
    MIN_BASELINE_FOR_DRIFT,
    Severity,
    THR_DRIFT_ABSOLUTE,
    THR_DRIFT_RELATIVE,
)

HISTORY_COL = "ta_prediction_history"

# Per-key noise floor on absolute change (units of the variable).
# Tuned so we don't shout at <0.5% drift in normal RSI fluctuation.
_PER_KEY_NOISE_FLOOR: Dict[str, float] = {
    "rsi": 5.0,
    "atr_pct": 0.001,
    "conflict_ratio": 0.05,
    "decision_confidence": 0.05,
}


def _resolve(record: Dict[str, Any], path: str) -> Optional[float]:
    cur: Any = record
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    try:
        return float(cur)
    except (TypeError, ValueError):
        return None


def drift_checks(db: Any) -> CheckResult:
    issues: List[HealthIssue] = []
    if db is None:
        return CheckResult(
            block="drift", score=1.0,
            issues=[],
            metrics={"reason": "mongo_unavailable"},
            sample_size=0,
        )
    col = db[HISTORY_COL]
    cursor = col.find(
        {"evaluation_state": "evaluated"},
        {
            "features_v1.rsi": 1,
            "features_v1.atr_pct": 1,
            "conflict_ratio": 1,
            "decision_intelligence.decision_confidence": 1,
            "created_at": 1,
        },
    ).sort("created_at", -1).limit(int(DRIFT_BASELINE_WINDOW))

    keys = {
        "rsi": "features_v1.rsi",
        "atr_pct": "features_v1.atr_pct",
        "conflict_ratio": "conflict_ratio",
        "decision_confidence": "decision_intelligence.decision_confidence",
    }

    samples: Dict[str, List[float]] = {k: [] for k in keys}
    n = 0
    for r in cursor:
        n += 1
        for label, path in keys.items():
            v = _resolve(r, path)
            if v is None:
                continue
            samples[label].append(v)

    summary: Dict[str, Dict[str, Any]] = {}
    drift_count = 0
    for label, values in samples.items():
        # Recent = first N (cursor is desc, so first N are the freshest).
        if len(values) < MIN_BASELINE_FOR_DRIFT:
            summary[label] = {
                "n": len(values), "recent_mean": None, "baseline_mean": None,
                "abs_change": None, "relative_change": None, "drift": False,
                "reason": "insufficient_baseline",
            }
            continue
        recent_n = min(DRIFT_RECENT_WINDOW, len(values) // 2 or 1)
        recent = values[:recent_n]
        baseline = values[recent_n:]
        if not baseline:
            summary[label] = {
                "n": len(values), "recent_mean": None, "baseline_mean": None,
                "abs_change": None, "relative_change": None, "drift": False,
                "reason": "baseline_empty",
            }
            continue
        rm = mean(recent)
        bm = mean(baseline)
        abs_change = abs(rm - bm)
        rel = abs_change / (abs(bm) + 1e-9)
        floor = _PER_KEY_NOISE_FLOOR.get(label, THR_DRIFT_ABSOLUTE)
        is_drift = abs_change >= floor and rel >= THR_DRIFT_RELATIVE
        if is_drift:
            drift_count += 1
            code: IssueCode
            if label in ("rsi", "atr_pct"):
                code = IssueCode.FEATURE_DRIFT_DETECTED
            elif label == "conflict_ratio":
                code = IssueCode.CONFLICT_DRIFT
            else:
                code = IssueCode.DECISION_CONF_DRIFT
            issues.append(HealthIssue(
                code, Severity.WARNING,
                f"{label} drifted: recent={rm:.4f} baseline={bm:.4f} (Δ={abs_change:.4f}, rel={rel:.0%})",
                meta={
                    "label": label, "recent_mean": round(rm, 6),
                    "baseline_mean": round(bm, 6),
                    "abs_change": round(abs_change, 6),
                    "relative_change": round(rel, 4),
                },
            ))
        summary[label] = {
            "n": len(values),
            "recent_n": recent_n,
            "recent_mean": round(rm, 6),
            "baseline_mean": round(bm, 6),
            "abs_change": round(abs_change, 6),
            "relative_change": round(rel, 4),
            "drift": bool(is_drift),
        }

    if n < MIN_BASELINE_FOR_DRIFT:
        score = 1.0     # not enough data to fail; treat as healthy
    else:
        score = max(0.0, 1.0 - 0.20 * drift_count)

    return CheckResult(
        block="drift",
        score=score,
        issues=issues,
        sample_size=n,
        metrics={"summary": summary, "drift_count": drift_count},
    )
