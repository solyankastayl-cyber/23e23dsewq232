"""
QA — Data Health Layer (read-only).

Validates:
  * pure-function behaviour of trust_score / status / recommendation mapping
  * each block check on synthetic Mongo state (using a temporary db_name)
  * 6 DoD points from the architect:
    1. /data-health → status + trust_score
    2. issues explain healthy/degraded/broken
    3. 0 evaluated → degraded/broken (NOT fake healthy)
    4. schema mismatch caught
    5. incomplete outcome caught
    6. debug coverage counted only over evaluated
  * read-only contract: source collections untouched

Run:
    python3 /app/scripts/qa_data_health.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

from modules.ta_prediction_intelligence.data_health import (
    Status,
    Severity,
    Recommendation,
    compute_health_report,
    compute_trust_score,
    derive_status,
    derive_recommendation,
    TRUST_HEALTHY_MIN,
    TRUST_DEGRADED_MIN,
)
from modules.ta_prediction_intelligence.data_health.types import (
    HealthIssue,
    IssueCode,
)
from modules.ta_prediction_intelligence.data_health.health_checks import (
    pipeline_health,
    feature_health,
    outcome_health,
    debug_health,
)
from modules.ta_prediction_intelligence.data_health.drift_checks import drift_checks
from modules.ta_prediction_intelligence.learning.feature_schema import (
    FEATURE_SCHEMA_HASH,
)


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results: list = []


def check(name: str, ok: bool, detail: str = "", extra=None) -> None:
    results.append((name, ok))
    print(f"[{PASS if ok else FAIL}] {name}")
    if detail:
        print(f"        {detail}")
    if not ok and extra is not None:
        try:
            print(f"        observed: {json.dumps(extra, default=str, indent=2)[:600]}")
        except Exception:
            print(f"        observed: {extra}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — synthetic Mongo state (uses an isolated db_name)
# ─────────────────────────────────────────────────────────────────────────────

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
TEST_DB = "trading_os_health_qa"


def _client_db():
    return MongoClient(MONGO_URL)[TEST_DB]


def _wipe(db) -> None:
    for c in db.list_collection_names():
        db.drop_collection(c)


def _make_history_record(
    *,
    pid: str,
    state: str = "evaluated",
    schema_hash: str = None,
    missing_engines=None,
    feature_hash: str = None,
    outcome_complete: bool = True,
    decision_confidence: float = 0.55,
    rsi: float = 50.0,
    atr_pct: float = 0.005,
    conflict_ratio: float = 0.10,
    created_at: datetime = None,
):
    rec = {
        "prediction_id": pid,
        "symbol": "ETHUSDT",
        "timeframe": "1H",
        "evaluation_state": state,
        "candle_close_ts": 1700000000,
        "entry_price": 3000.0,
        "feature_version": "v1",
        "feature_schema_hash": schema_hash or FEATURE_SCHEMA_HASH,
        "feature_hash": feature_hash or f"hash-{pid}",
        "feature_missing_engines": missing_engines or [],
        "features_v1": {"rsi": rsi, "atr_pct": atr_pct, **{f"k{i}": float(i) for i in range(80)}},
        "feature_states": {"trend": "up", "momentum": "ok", "volatility": "normal"},
        "conflict_ratio": conflict_ratio,
        "bias": "bullish",
        "confidence": 0.55,
        "decision_intelligence": {
            "primary_scenario": "bull", "decision_confidence": decision_confidence,
            "signal_strength": "moderate", "risk_level": "low",
        },
        "interaction": {"type": "trend_continuation"},
        "contributions": [],
        "temporal_intelligence": {"ready": True, "regime_stability_score": 0.5},
        "created_at": created_at or datetime.now(timezone.utc),
    }
    if state == "evaluated":
        outcome = {
            "evaluated_at": datetime.now(timezone.utc),
            "candles_used": 6,
            "winning_scenario": "bull",
        }
        if outcome_complete:
            outcome.update({
                "return_h1": 0.005, "return_h3": 0.012, "return_h6": 0.018,
                "max_favourable_move_pct": 0.020,
                "max_adverse_move_pct": -0.003,
                "volatility_future_h6": 0.002,
            })
        else:
            outcome.update({
                "return_h1": None, "return_h3": None, "return_h6": None,
                "max_favourable_move_pct": None,
                "max_adverse_move_pct": None,
                "volatility_future_h6": 0.002,
            })
        rec["outcome"] = outcome
    return rec


# ═════════════════════════════════════════════════════════════════════════════
# 1. Pure: trust_score / status / recommendation mapping
# ═════════════════════════════════════════════════════════════════════════════

print("=" * 72)
print("  1. Pure mapping: trust_score / derive_status / recommendation")
print("=" * 72)

# Trust score: 0.5 average given equal weights
ts = compute_trust_score({"pipeline": 0.5, "features": 0.5,
                          "outcomes": 0.5, "debug": 0.5, "drift": 0.5})
check("1.1 weighted average of equal blocks = 0.5", abs(ts - 0.5) < 1e-6,
      f"ts={ts}")

# Healthy when no critical issue + score >= 0.75
status = derive_status(0.80, [])
check("1.2 status HEALTHY at score=0.80, no issues",
      status == Status.HEALTHY, f"status={status}")

# Degraded between 0.45 and 0.75
status = derive_status(0.55, [])
check("1.3 status DEGRADED at score=0.55, no issues",
      status == Status.DEGRADED, f"status={status}")

# Broken when score < 0.45
status = derive_status(0.30, [])
check("1.4 status BROKEN at score=0.30",
      status == Status.BROKEN, f"status={status}")

# Critical issue forces BROKEN even at high score
status = derive_status(
    0.95, [HealthIssue(IssueCode.NO_PREDICTIONS, Severity.CRITICAL, "x")]
)
check("1.5 critical issue at score=0.95 → still BROKEN",
      status == Status.BROKEN, f"status={status}")

# Recommendation
check("1.6 BROKEN → fix_pipeline",
      derive_recommendation(Status.BROKEN, 1000) == Recommendation.FIX_PIPELINE)
check("1.7 HEALTHY + n=50 → collect_more_data",
      derive_recommendation(Status.HEALTHY, 50) == Recommendation.COLLECT_MORE_DATA)
check("1.8 HEALTHY + n=600 → safe_to_train_later",
      derive_recommendation(Status.HEALTHY, 600) == Recommendation.SAFE_TO_TRAIN_LATER)
check("1.9 DEGRADED → hold",
      derive_recommendation(Status.DEGRADED, 100) == Recommendation.HOLD)


# ═════════════════════════════════════════════════════════════════════════════
# 2. Synthetic state: 0 evaluated → degraded/broken (NOT fake healthy)
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  2. SYNTHETIC: 0 evaluated, only pending → broken/degraded")
print("=" * 72)

db = _client_db()
_wipe(db)
old_ts = datetime.now(timezone.utc) - timedelta(hours=48)
for i in range(10):
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"pend-{i}", state="pending", created_at=old_ts,
    ))
report = compute_health_report(db)
check("2.1 status NOT healthy when 0 evaluated and pending exist",
      report["status"] != "healthy",
      f"status={report['status']} trust={report['trust_score']}")
check("2.2 EVALUATED_ZERO_BUT_PENDING issue is critical",
      any(i["code"] == "evaluated_zero_but_pending" and i["severity"] == "critical"
          for i in report["issues"]),
      f"issues={[i['code'] for i in report['issues']]}")
check("2.3 recommendation = fix_pipeline",
      report["recommendation"] == "fix_pipeline",
      f"rec={report['recommendation']}")


# ═════════════════════════════════════════════════════════════════════════════
# 3. Synthetic: schema mismatch caught
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  3. SYNTHETIC: feature_schema mismatch")
print("=" * 72)

db = _client_db()
_wipe(db)
for i in range(20):
    sh = "f0f0f0" + "a" * 58 if i < 5 else FEATURE_SCHEMA_HASH    # 25% mismatch (>5%)
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"ev-{i}", state="evaluated", schema_hash=sh,
    ))
fh = feature_health(db)
check("3.1 feature_schema_mismatch CRITICAL issue raised",
      any(i.code == IssueCode.FEATURE_SCHEMA_MISMATCH and i.severity == Severity.CRITICAL
          for i in fh.issues),
      f"issues={[i.code.value for i in fh.issues]}, mismatch_rate={fh.metrics.get('schema_mismatch_rate')}")
check("3.2 schema_match_rate computed correctly (~0.75)",
      abs(fh.metrics["schema_match_rate"] - 0.75) < 1e-6,
      f"rate={fh.metrics['schema_match_rate']}")


# ═════════════════════════════════════════════════════════════════════════════
# 4. Synthetic: incomplete outcomes caught
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  4. SYNTHETIC: incomplete outcome rate")
print("=" * 72)

db = _client_db()
_wipe(db)
for i in range(20):
    incomplete = (i < 5)                                       # 25% > 10%
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"out-{i}", state="evaluated", outcome_complete=not incomplete,
    ))
oh = outcome_health(db)
check("4.1 OUTCOME_INCOMPLETE_RATE_HIGH critical issue raised",
      any(i.code == IssueCode.OUTCOME_INCOMPLETE_RATE_HIGH and i.severity == Severity.CRITICAL
          for i in oh.issues),
      f"issues={[i.code.value for i in oh.issues]} rate={oh.metrics['incomplete_outcome_rate']}")
check("4.2 incomplete_outcome_rate ~ 0.25",
      abs(oh.metrics["incomplete_outcome_rate"] - 0.25) < 1e-6,
      f"rate={oh.metrics['incomplete_outcome_rate']}")


# ═════════════════════════════════════════════════════════════════════════════
# 5. Debug coverage counted only when evaluated >= 20
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  5. SYNTHETIC: debug coverage threshold")
print("=" * 72)

# 5a: only 10 evaluated → no critical even with 0 debug records
db = _client_db()
_wipe(db)
for i in range(10):
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"e-{i}", state="evaluated"))
dh = debug_health(db)
check("5.1 evaluated=10, debug=0 → no DEBUG_COVERAGE_LOW critical",
      not any(i.code == IssueCode.DEBUG_COVERAGE_LOW for i in dh.issues),
      f"issues={[i.code.value for i in dh.issues]} eval={dh.metrics['evaluated_records']}")

# 5b: 30 evaluated, 5 debug → coverage 16.7%, well below 50% → critical
db = _client_db()
_wipe(db)
for i in range(30):
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"e-{i}", state="evaluated"))
for i in range(5):
    db.ta_prediction_debug.insert_one({
        "prediction_id": f"e-{i}",
        "error_type": "correct",
        "root_cause_primary": None,
        "analyzed_at": datetime.now(timezone.utc),
    })
dh = debug_health(db)
check("5.2 evaluated=30, debug=5 → DEBUG_COVERAGE_LOW critical raised",
      any(i.code == IssueCode.DEBUG_COVERAGE_LOW and i.severity == Severity.CRITICAL
          for i in dh.issues),
      f"coverage={dh.metrics['debug_coverage_rate']} issues={[i.code.value for i in dh.issues]}")
check("5.3 debug_coverage_rate ~ 0.166",
      abs(dh.metrics["debug_coverage_rate"] - (5 / 30)) < 1e-3,
      f"got={dh.metrics['debug_coverage_rate']}")


# ═════════════════════════════════════════════════════════════════════════════
# 6. End-to-end: synthetic-healthy → status=healthy, recommendation correct
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  6. SYNTHETIC: full pipeline = HEALTHY")
print("=" * 72)

db = _client_db()
_wipe(db)
for i in range(150):
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"H-{i}", state="evaluated",
    ))
# Add matching debug records (full coverage)
for i in range(150):
    db.ta_prediction_debug.insert_one({
        "prediction_id": f"H-{i}",
        "error_type": "correct" if i % 2 == 0 else "underconfident",
        "root_cause_primary": None,
        "analyzed_at": datetime.now(timezone.utc),
    })
report = compute_health_report(db)
check("6.1 status == healthy",
      report["status"] == "healthy",
      f"status={report['status']} trust={report['trust_score']} issues={[i['code'] for i in report['issues']]}")
check("6.2 trust_score >= 0.75",
      report["trust_score"] >= 0.75,
      f"trust={report['trust_score']}")
check("6.3 no critical issues",
      not any(i["severity"] == "critical" for i in report["issues"]),
      f"issues={[(i['code'], i['severity']) for i in report['issues']]}")
check("6.4 recommendation = safe_to_train_later (n>=100)",
      report["recommendation"] == "safe_to_train_later",
      f"rec={report['recommendation']} eval={report['checks']['pipeline']['metrics']['evaluated_count']}")


# ═════════════════════════════════════════════════════════════════════════════
# 7. Drift detection
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  7. SYNTHETIC: drift detection")
print("=" * 72)

db = _client_db()
_wipe(db)
# 100 baseline records (RSI ~ 50)
for i in range(100):
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"B-{i}", state="evaluated", rsi=50.0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=24 + i),
    ))
# 50 recent records with RSI=80 → drift
for i in range(50):
    db.ta_prediction_history.insert_one(_make_history_record(
        pid=f"R-{i}", state="evaluated", rsi=80.0,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=i),
    ))
dr = drift_checks(db)
check("7.1 FEATURE_DRIFT_DETECTED issue raised on RSI shift",
      any(i.code == IssueCode.FEATURE_DRIFT_DETECTED for i in dr.issues),
      f"issues={[i.code.value for i in dr.issues]}")
check("7.2 drift summary includes recent_mean ~80, baseline ~50 for rsi",
      abs(dr.metrics["summary"]["rsi"]["recent_mean"] - 80.0) < 1.0
      and abs(dr.metrics["summary"]["rsi"]["baseline_mean"] - 50.0) < 1.0,
      f"rsi summary={dr.metrics['summary']['rsi']}")
check("7.3 drift_count >= 1",
      dr.metrics["drift_count"] >= 1, f"count={dr.metrics['drift_count']}")


# ═════════════════════════════════════════════════════════════════════════════
# 8. Read-only contract on the REAL trading_os DB
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  8. READ-ONLY CONTRACT — production trading_os DB")
print("=" * 72)

real_db = MongoClient(MONGO_URL)["trading_os"]
sigs_before = {
    col: real_db[col].estimated_document_count()
    for col in [
        "ta_prediction_history",
        "ta_prediction_debug",
        "ta_prediction_dataset",
        "ta_prediction_temporal_buffer",
        "ta_prediction_calibration_stats",
    ]
}
report = compute_health_report(real_db)
sigs_after = {
    col: real_db[col].estimated_document_count()
    for col in sigs_before
}
check("8.1 no source collection mutated by report computation",
      sigs_before == sigs_after,
      f"before={sigs_before} after={sigs_after}")

check("8.2 production report responds with status + trust_score",
      isinstance(report.get("trust_score"), (int, float))
      and report.get("status") in ("healthy", "degraded", "broken"),
      f"status={report['status']} trust={report['trust_score']}")

check("8.3 production report has 'checks' for all 5 blocks",
      set(report.get("checks", {}).keys()) ==
      {"pipeline", "features", "outcomes", "debug", "drift"},
      f"keys={list(report.get('checks', {}).keys())}")

check("8.4 production report includes recommendation",
      report.get("recommendation") in (
          "fix_pipeline", "collect_more_data", "safe_to_train_later", "hold"),
      f"rec={report.get('recommendation')}")


# ═════════════════════════════════════════════════════════════════════════════
# 9. HTTP endpoints (live)
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  9. HTTP — endpoints respond and contract")
print("=" * 72)

import requests
BASE = "http://localhost:8001/api/ta-prediction-intelligence/data-health"
for ep in ["", "/checks", "/drift"]:
    r = requests.get(BASE + ep, timeout=10)
    check(f"9.0 GET {BASE + ep} → 200", r.status_code == 200,
          f"status={r.status_code}")

# /data-health response surface
resp = requests.get(BASE, timeout=10).json()
check("9.1 /data-health has status + trust_score + recommendation",
      all(k in resp for k in ("status", "trust_score", "recommendation")),
      f"keys={sorted(resp.keys())}")
check("9.2 /data-health has 5 check blocks",
      set(resp.get("checks", {}).keys()) ==
      {"pipeline", "features", "outcomes", "debug", "drift"},
      f"blocks={list(resp.get('checks', {}).keys())}")


# Cleanup
_wipe(_client_db())


passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 72)
print(f"  RESULT: {passed}/{total} checks passed")
print("=" * 72)
sys.exit(0 if passed == total else 1)
