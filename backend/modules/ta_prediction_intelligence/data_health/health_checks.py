"""
Four core health checks (each pure on its inputs):

    pipeline_health(db)   → CheckResult
    feature_health(db)    → CheckResult
    outcome_health(db)    → CheckResult
    debug_health(db)      → CheckResult

All DB access is read-only (find / count_documents / aggregate). The block
scores are normalised to [0, 1] so trust_score.compute_trust_score can mix
them with constant weights.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

from .types import (
    CheckResult,
    HealthIssue,
    IssueCode,
    OLD_PENDING_AGE_SECONDS,
    Severity,
    THR_DEBUG_COVERAGE,
    THR_DEBUG_COVERAGE_MIN_EVAL,
    THR_FEATURE_SCHEMA_MISMATCH,
    THR_LOW_EVALUATED_RATIO,
    THR_MISSING_ENGINES_RATE,
    THR_OLD_PENDING_RATIO,
    THR_OUTCOME_INCOMPLETE,
    THR_VOL_PROXY_USAGE,
)

# Read-only import of the canonical schema hash. Permitted by the spec.
try:
    from modules.ta_prediction_intelligence.learning.feature_schema import (
        FEATURE_SCHEMA_HASH,
        FEATURE_VERSION,
    )
except Exception:
    FEATURE_SCHEMA_HASH = None
    FEATURE_VERSION = None

HISTORY_COL = "ta_prediction_history"
DEBUG_COL = "ta_prediction_debug"


def _safe_div(num: float, den: float) -> Optional[float]:
    if den <= 0:
        return None
    return num / den


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ══ 1. PIPELINE ═══════════════════════════════════════════════════════════════════
def pipeline_health(db: Any) -> CheckResult:
    issues: List[HealthIssue] = []
    if db is None:
        return CheckResult(
            block="pipeline", score=0.0,
            issues=[HealthIssue(IssueCode.NO_PREDICTIONS, Severity.CRITICAL,
                                "mongo unavailable")],
            metrics={}, sample_size=0,
        )
    col = db[HISTORY_COL]
    total = int(col.estimated_document_count())
    pending = int(col.count_documents({"evaluation_state": "pending"}))
    evaluated = int(col.count_documents({"evaluation_state": "evaluated"}))
    error_state = int(col.count_documents({"evaluation_state": "error"}))
    expired = int(col.count_documents({"evaluation_state": "expired"}))

    cutoff = _now_utc() - timedelta(seconds=OLD_PENDING_AGE_SECONDS)
    old_pending = int(col.count_documents({
        "evaluation_state": "pending",
        "created_at": {"$lt": cutoff},
    }))

    # Evaluation lag (created_at → outcome.evaluated_at) over recent evaluated
    lag_minutes_samples: List[float] = []
    for r in col.find(
        {"evaluation_state": "evaluated"},
        {"created_at": 1, "outcome.evaluated_at": 1},
    ).sort("outcome.evaluated_at", -1).limit(50):
        ca = r.get("created_at")
        ev = (r.get("outcome") or {}).get("evaluated_at")
        try:
            if isinstance(ca, datetime) and isinstance(ev, datetime):
                ca_aware = ca if ca.tzinfo else ca.replace(tzinfo=timezone.utc)
                ev_aware = ev if ev.tzinfo else ev.replace(tzinfo=timezone.utc)
                lag_minutes_samples.append(
                    max(0.0, (ev_aware - ca_aware).total_seconds() / 60.0)
                )
        except Exception:
            continue
    avg_lag = round(mean(lag_minutes_samples), 2) if lag_minutes_samples else None

    evaluated_ratio = _safe_div(evaluated, max(total, 1))
    old_pending_ratio = _safe_div(old_pending, max(pending, 1)) or 0.0

    # Issues
    if total == 0:
        issues.append(HealthIssue(
            IssueCode.NO_PREDICTIONS, Severity.CRITICAL,
            "no predictions in ta_prediction_history yet",
        ))
    if evaluated == 0 and pending > 0:
        issues.append(HealthIssue(
            IssueCode.EVALUATED_ZERO_BUT_PENDING, Severity.CRITICAL,
            f"{pending} pending but 0 evaluated — outcome worker stuck",
            meta={"pending": pending, "old_pending": old_pending},
        ))
    elif evaluated_ratio is not None and evaluated_ratio < THR_LOW_EVALUATED_RATIO and total >= 20:
        issues.append(HealthIssue(
            IssueCode.LOW_EVALUATED_RATIO, Severity.WARNING,
            f"only {evaluated_ratio:.1%} of predictions evaluated",
            meta={"evaluated": evaluated, "total": total},
        ))
    if old_pending_ratio > THR_OLD_PENDING_RATIO and pending > 5:
        issues.append(HealthIssue(
            IssueCode.HIGH_OLD_PENDING_RATIO, Severity.WARNING,
            f"{old_pending_ratio:.0%} of pending records are >{int(OLD_PENDING_AGE_SECONDS/3600)}h old",
            meta={"old_pending": old_pending, "pending": pending},
        ))
    if avg_lag is not None and avg_lag > 12 * 60:           # > 12h is suspect
        issues.append(HealthIssue(
            IssueCode.EVALUATION_LAG_HIGH, Severity.WARNING,
            f"average pred→eval lag is {avg_lag/60:.1f}h",
            meta={"avg_lag_minutes": avg_lag},
        ))

    # Score — closer to 1.0 the better.
    # Penalise on (1 - evaluated_ratio) AND old_pending_ratio.
    if total == 0:
        score = 0.0
    else:
        s_eval = float(evaluated_ratio if evaluated_ratio is not None else 0.0)
        s_old = max(0.0, 1.0 - old_pending_ratio)
        score = 0.7 * min(1.0, s_eval / max(THR_LOW_EVALUATED_RATIO, 1e-6)) * (1 if s_eval >= THR_LOW_EVALUATED_RATIO else s_eval/THR_LOW_EVALUATED_RATIO) * 0 + 0.7 * min(1.0, s_eval * 5) + 0.3 * s_old  # noqa: E501
        # Simplify: clamp evaluated ratio scaled to 5x the warn threshold for the bulk of the score
        score = max(0.0, min(1.0, 0.7 * min(1.0, s_eval / 0.5) + 0.3 * s_old))
        if total < 5:
            # Be lenient for cold start; cap the upside.
            score = min(score, 0.65)

    return CheckResult(
        block="pipeline",
        score=score,
        issues=issues,
        sample_size=total,
        metrics={
            "total_predictions": total,
            "pending_count": pending,
            "evaluated_count": evaluated,
            "error_count": error_state,
            "expired_count": expired,
            "evaluated_ratio": round(evaluated_ratio or 0.0, 4),
            "old_pending_count": old_pending,
            "old_pending_ratio": round(old_pending_ratio, 4),
            "avg_evaluation_lag_minutes": avg_lag,
        },
    )


# ══ 2. FEATURES ══════════════════════════════════════════════════════════════════
def feature_health(db: Any, *, recent_window: int = 500) -> CheckResult:
    issues: List[HealthIssue] = []
    if db is None:
        return CheckResult(
            block="features", score=0.0,
            issues=[HealthIssue(IssueCode.NO_PREDICTIONS, Severity.CRITICAL, "mongo unavailable")],
            metrics={}, sample_size=0,
        )
    col = db[HISTORY_COL]
    cursor = col.find(
        {"feature_schema_hash": {"$exists": True}},
        {"feature_schema_hash": 1, "feature_missing_engines": 1,
         "feature_hash": 1, "features_v1": 1, "feature_states": 1},
    ).sort("created_at", -1).limit(int(recent_window))
    n = 0
    schema_match = 0
    missing_engines_count = 0
    feature_hashes: List[str] = []
    completeness_total = 0
    completeness_filled = 0
    for r in cursor:
        n += 1
        sh = r.get("feature_schema_hash")
        if FEATURE_SCHEMA_HASH and sh == FEATURE_SCHEMA_HASH:
            schema_match += 1
        miss = r.get("feature_missing_engines") or []
        if isinstance(miss, list) and len(miss) > 0:
            missing_engines_count += 1
        fhash = r.get("feature_hash")
        if fhash:
            feature_hashes.append(str(fhash))
        fv = r.get("features_v1") or {}
        if isinstance(fv, dict):
            completeness_total += len(fv)
            for v in fv.values():
                if v is None:
                    continue
                completeness_filled += 1

    schema_mismatch_rate = 1.0 - (schema_match / n) if n else 0.0
    missing_rate = (missing_engines_count / n) if n else 0.0
    duplicate_count = 0
    if feature_hashes:
        seen: Dict[str, int] = {}
        for h in feature_hashes:
            seen[h] = seen.get(h, 0) + 1
        # “duplicates” = hashes appearing >1; we count surplus copies.
        duplicate_count = sum(c - 1 for c in seen.values() if c > 1)
    duplicate_rate = (duplicate_count / n) if n else 0.0
    completeness = (
        completeness_filled / completeness_total if completeness_total else None
    )

    if n == 0:
        issues.append(HealthIssue(
            IssueCode.NO_PREDICTIONS, Severity.WARNING,
            "no records with feature_schema_hash yet",
        ))
    elif schema_mismatch_rate > THR_FEATURE_SCHEMA_MISMATCH:
        issues.append(HealthIssue(
            IssueCode.FEATURE_SCHEMA_MISMATCH, Severity.CRITICAL,
            f"{schema_mismatch_rate:.1%} of recent records have a different schema_hash than current",
            meta={"current_schema_hash": FEATURE_SCHEMA_HASH,
                  "matched": schema_match, "total": n},
        ))
    if missing_rate > THR_MISSING_ENGINES_RATE:
        issues.append(HealthIssue(
            IssueCode.MISSING_FEATURES_RATE_HIGH, Severity.CRITICAL,
            f"{missing_rate:.1%} of recent records had missing engines",
            meta={"missing_count": missing_engines_count, "total": n},
        ))
    if completeness is not None and completeness < 0.95:
        issues.append(HealthIssue(
            IssueCode.FEATURE_COMPLETENESS_LOW, Severity.WARNING,
            f"feature completeness is {completeness:.1%}",
            meta={"completeness": completeness},
        ))

    if n == 0:
        score = 0.0
    else:
        score = max(0.0, min(1.0,
                            (1 - schema_mismatch_rate) * 0.55
                            + (1 - min(1.0, missing_rate / 0.20)) * 0.25
                            + (completeness or 0.95) * 0.20))

    return CheckResult(
        block="features",
        score=score,
        issues=issues,
        sample_size=n,
        metrics={
            "feature_version": FEATURE_VERSION,
            "current_schema_hash": FEATURE_SCHEMA_HASH,
            "schema_match_rate": round(1 - schema_mismatch_rate, 4),
            "schema_mismatch_rate": round(schema_mismatch_rate, 4),
            "missing_engines_rate": round(missing_rate, 4),
            "feature_hash_duplicate_rate": round(duplicate_rate, 4),
            "feature_completeness": round(completeness, 4) if completeness is not None else None,
        },
    )


# ══ 3. OUTCOMES ═════════════════════════════════════════════════════════════════
def outcome_health(db: Any, *, recent_window: int = 500) -> CheckResult:
    issues: List[HealthIssue] = []
    if db is None:
        return CheckResult(
            block="outcomes", score=0.0,
            issues=[HealthIssue(IssueCode.NO_PREDICTIONS, Severity.CRITICAL, "mongo unavailable")],
            metrics={}, sample_size=0,
        )
    col = db[HISTORY_COL]
    cursor = col.find(
        {"evaluation_state": "evaluated"},
        {"outcome": 1},
    ).sort("outcome.evaluated_at", -1).limit(int(recent_window))
    n = 0
    incomplete = 0
    vol_proxy = 0
    win_counts = {"bull": 0, "base": 0, "bear": 0, "unknown": 0}
    return_h6: List[float] = []
    for r in cursor:
        n += 1
        outcome = r.get("outcome") or {}
        rh6 = outcome.get("return_h6")
        winning = (outcome.get("winning_scenario") or "unknown").lower()
        win_counts[winning] = win_counts.get(winning, 0) + 1
        if rh6 is None or outcome.get("max_favourable_move_pct") is None or outcome.get("max_adverse_move_pct") is None:
            incomplete += 1
        try:
            if outcome.get("volatility_future_h6") in (None, 0, 0.0):
                vol_proxy += 1
        except Exception:
            vol_proxy += 1
        try:
            if rh6 is not None:
                return_h6.append(float(rh6))
        except (TypeError, ValueError):
            pass

    incomplete_rate = (incomplete / n) if n else 0.0
    vol_proxy_rate = (vol_proxy / n) if n else 0.0
    largest_share = max(win_counts.values()) / n if n else 0.0
    return_h6_stats = {
        "min": round(min(return_h6), 6) if return_h6 else None,
        "max": round(max(return_h6), 6) if return_h6 else None,
        "mean": round(mean(return_h6), 6) if return_h6 else None,
        "abs_mean": round(mean(abs(x) for x in return_h6), 6) if return_h6 else None,
        "n": len(return_h6),
    }

    if incomplete_rate > THR_OUTCOME_INCOMPLETE:
        issues.append(HealthIssue(
            IssueCode.OUTCOME_INCOMPLETE_RATE_HIGH, Severity.CRITICAL,
            f"{incomplete_rate:.1%} of evaluated outcomes are incomplete",
            meta={"incomplete": incomplete, "total": n},
        ))
    if vol_proxy_rate > THR_VOL_PROXY_USAGE and n >= 10:
        issues.append(HealthIssue(
            IssueCode.VOLATILITY_PROXY_OVERUSE, Severity.WARNING,
            f"{vol_proxy_rate:.1%} of outcomes have null/zero volatility_future_h6",
            meta={"proxied": vol_proxy, "total": n},
        ))
    if n >= 30 and largest_share > 0.85:
        winning_label = max(win_counts.keys(), key=lambda k: win_counts[k])
        issues.append(HealthIssue(
            IssueCode.WINNING_SCENARIO_SKEWED, Severity.WARNING,
            f"winning_scenario distribution skewed: {winning_label} = {largest_share:.0%}",
            meta={"distribution": win_counts},
        ))

    if n == 0:
        score = 0.0
    else:
        score = max(0.0, min(1.0,
                            (1 - incomplete_rate) * 0.6
                            + (1 - min(1.0, vol_proxy_rate / 0.80)) * 0.3
                            + (1 - max(0, largest_share - 0.85) / 0.15) * 0.1))

    return CheckResult(
        block="outcomes",
        score=score,
        issues=issues,
        sample_size=n,
        metrics={
            "evaluated_sampled": n,
            "incomplete_outcome_rate": round(incomplete_rate, 4),
            "volatility_proxied_rate": round(vol_proxy_rate, 4),
            "winning_scenario_distribution": win_counts,
            "return_h6": return_h6_stats,
        },
    )


# ══ 4. DEBUG ══════════════════════════════════════════════════════════════════════
def debug_health(db: Any) -> CheckResult:
    issues: List[HealthIssue] = []
    if db is None:
        return CheckResult(block="debug", score=0.0, issues=[], metrics={}, sample_size=0)
    hist = db[HISTORY_COL]
    debug = db[DEBUG_COL]
    n_eval = int(hist.count_documents({"evaluation_state": "evaluated"}))
    n_debug = int(debug.estimated_document_count())
    coverage = (n_debug / n_eval) if n_eval > 0 else 0.0

    # Top error types and root causes (read-only aggregation)
    error_top: List[Dict[str, Any]] = []
    causes_top: List[Dict[str, Any]] = []
    overconf = 0
    underconf = 0
    debug_count_for_rates = 0
    if n_debug > 0:
        try:
            err_counts: Dict[str, int] = {}
            cause_counts: Dict[str, int] = {}
            for r in debug.find({}, {"error_type": 1, "root_cause_primary": 1}):
                debug_count_for_rates += 1
                et = r.get("error_type") or "unknown"
                err_counts[et] = err_counts.get(et, 0) + 1
                if et == "overconfident":
                    overconf += 1
                if et == "underconfident":
                    underconf += 1
                rc = r.get("root_cause_primary")
                if rc:
                    cause_counts[rc] = cause_counts.get(rc, 0) + 1
            error_top = [
                {"error_type": k, "count": v}
                for k, v in sorted(err_counts.items(), key=lambda kv: -kv[1])[:10]
            ]
            causes_top = [
                {"cause": k, "count": v}
                for k, v in sorted(cause_counts.items(), key=lambda kv: -kv[1])[:10]
            ]
        except Exception:
            pass

    if n_eval >= THR_DEBUG_COVERAGE_MIN_EVAL and coverage < THR_DEBUG_COVERAGE:
        issues.append(HealthIssue(
            IssueCode.DEBUG_COVERAGE_LOW, Severity.CRITICAL,
            f"debug coverage is {coverage:.1%} of evaluated predictions",
            meta={"debug": n_debug, "evaluated": n_eval},
        ))
    overconf_rate = (overconf / debug_count_for_rates) if debug_count_for_rates else 0.0
    underconf_rate = (underconf / debug_count_for_rates) if debug_count_for_rates else 0.0
    if overconf_rate > 0.50 and debug_count_for_rates >= 20:
        issues.append(HealthIssue(
            IssueCode.OVERCONFIDENCE_RATE_HIGH, Severity.WARNING,
            f"overconfidence rate is {overconf_rate:.1%} (>50%)",
            meta={"rate": overconf_rate},
        ))
    if underconf_rate > 0.50 and debug_count_for_rates >= 20:
        issues.append(HealthIssue(
            IssueCode.UNDERCONFIDENCE_RATE_HIGH, Severity.WARNING,
            f"underconfidence rate is {underconf_rate:.1%} (>50%)",
            meta={"rate": underconf_rate},
        ))

    score = float(min(1.0, coverage)) if n_eval > 0 else 0.0
    return CheckResult(
        block="debug",
        score=score,
        issues=issues,
        sample_size=n_debug,
        metrics={
            "debug_records": n_debug,
            "evaluated_records": n_eval,
            "debug_coverage_rate": round(coverage, 4),
            "overconfidence_rate": round(overconf_rate, 4),
            "underconfidence_rate": round(underconf_rate, 4),
            "top_error_types": error_top,
            "top_root_causes": causes_top,
        },
    )
