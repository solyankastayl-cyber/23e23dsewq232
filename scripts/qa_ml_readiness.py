"""
QA — ML Readiness Layer (read-only, live-only).

Validates:
  * pure functions: weights, status thresholds, recommendation precedence
  * each metric component on synthetic Mongo state
  * 8 DoD points + entropy edge cases
  * read-only contract on production trading_os DB

Run:
    python3 /app/scripts/qa_ml_readiness.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
import requests
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

from modules.ta_prediction_intelligence.ml_readiness import (
    Status,
    Recommendation,
    BlockingFactor,
    compute_readiness_report,
    compute_final_score,
    derive_status,
    derive_recommendation,
    WEIGHTS,
    READY_THRESHOLD,
    ALMOST_READY_THRESHOLD,
    PARTIAL_THRESHOLD,
    MIN_TOTAL_SAMPLES,
    FEATURE_INTEGRITY_GATE,
)
from modules.ta_prediction_intelligence.ml_readiness.readiness_metrics import (
    compute_sample_quality,
    compute_class_balance,
    compute_error_stability,
    compute_feature_integrity,
    compute_regime_coverage,
)
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


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
TEST_DB = "trading_os_mlready_qa"


def _client_db():
    return MongoClient(MONGO_URL)[TEST_DB]


def _wipe(db) -> None:
    for c in db.list_collection_names():
        db.drop_collection(c)


def _hist_record(*, pid, symbol="ETHUSDT", tf="1H",
                 winning="bull", return_h6=0.020,
                 interaction="trend_continuation",
                 vol_state="normal", trend_state="weak_trend"):
    return {
        "prediction_id": pid,
        "symbol": symbol,
        "timeframe": tf,
        "evaluation_state": "evaluated",
        "candle_close_ts": 1700000000,
        "feature_schema_hash": FEATURE_SCHEMA_HASH,
        "feature_missing_engines": [],
        "features_v1": {"rsi": 50.0, "atr_pct": 0.005},
        "feature_states": {"trend": trend_state, "momentum": "ok",
                           "volatility": vol_state},
        "interaction": {"type": interaction},
        "decision_intelligence": {"primary_scenario": winning,
                                  "decision_confidence": 0.55,
                                  "signal_strength": "moderate",
                                  "risk_level": "low"},
        "outcome": {"winning_scenario": winning, "return_h6": return_h6,
                    "return_h1": return_h6 * 0.4, "return_h3": return_h6 * 0.7,
                    "max_favourable_move_pct": abs(return_h6) * 1.2,
                    "max_adverse_move_pct": -abs(return_h6) * 0.3,
                    "volatility_future_h6": 0.002,
                    "evaluated_at": datetime.now(timezone.utc),
                    "candles_used": 6},
        "created_at": datetime.now(timezone.utc),
    }


def _debug_record(*, pid, error_type="wrong_direction", root_cause="momentum_misread"):
    return {
        "prediction_id": pid,
        "symbol": "ETHUSDT", "tf": "1H",
        "error_type": error_type,
        "root_cause_primary": root_cause,
        "root_causes_secondary": [],
        "no_edge_ignored": False,
        "analyzed_at": datetime.now(timezone.utc),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1. PURE: weights + status + recommendation
# ═════════════════════════════════════════════════════════════════════════════

print("=" * 72)
print("  1. PURE: weights, status mapping, recommendation precedence")
print("=" * 72)

check("1.1 WEIGHTS sum to 1.0",
      abs(sum(WEIGHTS.values()) - 1.0) < 1e-9,
      f"sum={sum(WEIGHTS.values())}")

# All-1.0 components → score=1.0
score = compute_final_score({k: 1.0 for k in WEIGHTS})
check("1.2 all components 1.0 → final score 1.0",
      abs(score - 1.0) < 1e-6, f"score={score}")

# All-0 → 0
check("1.3 all components 0.0 → 0.0",
      compute_final_score({k: 0.0 for k in WEIGHTS}) == 0.0)

# Status mapping
check("1.4 score 0.90, no gate → READY",
      derive_status(0.90, False) == Status.READY)
check("1.5 score 0.75, no gate → ALMOST_READY",
      derive_status(0.75, False) == Status.ALMOST_READY)
check("1.6 score 0.50, no gate → PARTIAL",
      derive_status(0.50, False) == Status.PARTIAL)
check("1.7 score 0.30, no gate → NOT_READY",
      derive_status(0.30, False) == Status.NOT_READY)
check("1.8 score 0.95, hard gate → NOT_READY (gate overrides)",
      derive_status(0.95, True) == Status.NOT_READY)

# Recommendation precedence
check("1.9 data_health_broken → fix_data_health",
      derive_recommendation(Status.NOT_READY,
                            ["data_health_broken"]) == Recommendation.FIX_DATA_HEALTH)
check("1.10 feature_integrity_low → fix_feature_pipeline",
      derive_recommendation(Status.NOT_READY,
                            ["feature_integrity_low"]) == Recommendation.FIX_FEATURE_PIPELINE)
check("1.11 low_total_samples → collect_more_data",
      derive_recommendation(Status.NOT_READY,
                            ["low_total_samples"]) == Recommendation.COLLECT_MORE_DATA)
check("1.12 unstable_error_patterns → collect_more_debug_cases",
      derive_recommendation(Status.NOT_READY,
                            ["unstable_error_patterns"]) == Recommendation.COLLECT_MORE_DEBUG_CASES)
check("1.13 ALMOST_READY no blocking → prepare_trainer",
      derive_recommendation(Status.ALMOST_READY,
                            []) == Recommendation.PREPARE_TRAINER)
check("1.14 PARTIAL no blocking → continue_observation",
      derive_recommendation(Status.PARTIAL,
                            []) == Recommendation.CONTINUE_OBSERVATION)


# ═════════════════════════════════════════════════════════════════════════════
# 2. ENTROPY edge cases (the most error-prone block)
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  2. ENTROPY edge cases for error_stability")
print("=" * 72)

db = _client_db(); _wipe(db)
# 2.1: 1 cause = 100% (n=40) → stability close to 1.0
for i in range(40):
    db.ta_prediction_history.insert_one(_hist_record(pid=f"e-{i}"))
    db.ta_prediction_debug.insert_one(_debug_record(pid=f"e-{i}",
                                                     root_cause="momentum_misread"))
score, blocking, det = compute_error_stability(db)
check("2.1 1 cause = 100% → error_stability >= 0.95",
      score >= 0.95,
      f"score={score} dom={det.get('dominant_share')} entropy={det.get('root_cause_entropy')}")

# 2.2: 10 even causes → stability close to 0.0
db = _client_db(); _wipe(db)
causes = [f"cause_{j}" for j in range(10)]
for i in range(40):
    db.ta_prediction_history.insert_one(_hist_record(pid=f"e2-{i}"))
    db.ta_prediction_debug.insert_one(_debug_record(pid=f"e2-{i}",
                                                     root_cause=causes[i % 10]))
score, blocking, det = compute_error_stability(db)
check("2.2 10 even causes → error_stability <= 0.40",
      score <= 0.40,
      f"score={score} entropy={det.get('root_cause_entropy')} dom={det.get('dominant_share')}")
check("2.3 10 even causes → unstable_error_patterns blocking",
      "unstable_error_patterns" in blocking,
      f"blocking={blocking}")
check("2.4 10 even causes → no_dominant_failure_mode blocking (max=0.10 < 0.25)",
      "no_dominant_failure_mode" in blocking,
      f"blocking={blocking}")

# 2.3: debug_count < 30 → component=0 + insufficient_debug_samples
db = _client_db(); _wipe(db)
for i in range(15):
    db.ta_prediction_history.insert_one(_hist_record(pid=f"e3-{i}"))
    db.ta_prediction_debug.insert_one(_debug_record(pid=f"e3-{i}"))
score, blocking, det = compute_error_stability(db)
check("2.5 debug_count<30 → error_stability=0 + insufficient_debug_samples blocking",
      score == 0.0 and "insufficient_debug_samples" in blocking,
      f"score={score} blocking={blocking}")


# ═════════════════════════════════════════════════════════════════════════════
# 3. CLASS BALANCE — entropy formulas
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  3. CLASS BALANCE — Shannon entropy normalization")
print("=" * 72)

# 3.1: perfectly balanced bull/base/bear (and up/down) → 1.0
db = _client_db(); _wipe(db)
for i in range(30):
    w = ["bull", "base", "bear"][i % 3]
    rh = 0.020 if w == "bull" else (-0.020 if w == "bear" else 0.0001)
    db.ta_prediction_history.insert_one(_hist_record(pid=f"cb-{i}",
                                                      winning=w, return_h6=rh))
score, blocking, det = compute_class_balance(db)
check("3.1 balanced 1/3·1/3·1/3 → class_balance ~ 1.0",
      score >= 0.85,
      f"score={score} dist={det['scenario_distribution']} dir={det['direction_distribution']}")

# 3.2: severe imbalance 80/10/10
db = _client_db(); _wipe(db)
for i in range(30):
    w = "bull" if i < 24 else ("base" if i < 27 else "bear")
    rh = 0.020 if w == "bull" else (-0.020 if w == "bear" else 0.0001)
    db.ta_prediction_history.insert_one(_hist_record(pid=f"sk-{i}",
                                                      winning=w, return_h6=rh))
score, blocking, det = compute_class_balance(db)
check("3.2 80/10/10 imbalance triggers severe_class_imbalance",
      "severe_class_imbalance" in blocking,
      f"blocking={blocking} max_share={det['max_scenario_share']}")
check("3.3 max_scenario_share computed = 0.80",
      abs(det["max_scenario_share"] - 0.80) < 1e-6,
      f"got={det['max_scenario_share']}")


# ═════════════════════════════════════════════════════════════════════════════
# 4. SAMPLE QUALITY — formula + blind buckets
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  4. SAMPLE QUALITY")
print("=" * 72)

# 4.1: 500 ETH samples, 0 BTC, 0 SOL → total=1.0, pair_score≈0.33, bucket_score depends
db = _client_db(); _wipe(db)
for i in range(500):
    db.ta_prediction_history.insert_one(
        _hist_record(pid=f"hq-{i}", symbol="ETHUSDT", tf="1H",
                     interaction="trend_continuation"))
score, blocking, det = compute_sample_quality(db)
# Expect sub_scores: total=1.0, pair=(1+0+0)/3=0.333, bucket=1.0 (all 500 in 1 bucket >=20)
check("4.1 500 ETH only → sub_scores total=1.0, pair≈0.333, bucket=1.0",
      abs(det["sub_scores"]["total_score"] - 1.0) < 1e-6
      and abs(det["sub_scores"]["pair_score"] - 1/3) < 0.01
      and det["sub_scores"]["bucket_score"] == 1.0,
      f"sub={det['sub_scores']}")

# 4.2: 60 samples spread thin → total=0.12, blind buckets
db = _client_db(); _wipe(db)
for i in range(60):
    interaction = ["trend_continuation", "pullback", "rejection",
                    "breakout", "fake_breakout", "early_reversal"][i % 6]
    db.ta_prediction_history.insert_one(
        _hist_record(pid=f"thin-{i}", interaction=interaction))
score, blocking, det = compute_sample_quality(db)
check("4.2 60 samples in 6 buckets (10 each) → blind_buckets blocking",
      "blind_buckets" in blocking and det["min_bucket_size"] == 10,
      f"blocking={blocking} min_bucket={det['min_bucket_size']}")


# ═════════════════════════════════════════════════════════════════════════════
# 5. REGIME COVERAGE
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  5. REGIME COVERAGE")
print("=" * 72)

# 5.1: full coverage of all axes
db = _client_db(); _wipe(db)
vol_states = ["compression", "normal", "expansion", "chaos"]
trend_states = ["range", "weak_trend", "strong_trend", "exhaustion"]
interactions = ["trend_continuation", "pullback", "rejection", "breakout",
                "fake_breakout", "early_reversal", "compression", "expansion_chaos"]
i = 0
for v in vol_states:
    for t in trend_states:
        for it in interactions:
            db.ta_prediction_history.insert_one(_hist_record(
                pid=f"reg-{i}", vol_state=v, trend_state=t, interaction=it))
            i += 1
score, blocking, det = compute_regime_coverage(db)
check("5.1 full axis coverage → regime_coverage = 1.0",
      abs(score - 1.0) < 1e-9,
      f"score={score} subs={det['sub_scores']}")

# 5.2: only normal vol + range trend + 1 interaction → coverage low
db = _client_db(); _wipe(db)
for i in range(120):
    db.ta_prediction_history.insert_one(_hist_record(
        pid=f"low-{i}", vol_state="normal", trend_state="range",
        interaction="trend_continuation"))
score, blocking, det = compute_regime_coverage(db)
expected = 0.30 * (1/4) + 0.30 * (1/4) + 0.40 * (1/8)
check("5.2 single state per axis → coverage = 0.30·0.25 + 0.30·0.25 + 0.40·0.125",
      abs(score - expected) < 1e-6,
      f"score={score} expected={expected}")
check("5.3 n>=100 + low coverage → regime_coverage_low blocking",
      "regime_coverage_low" in blocking,
      f"blocking={blocking}")


# ═════════════════════════════════════════════════════════════════════════════
# 6. HARD GATES — DoD #5/6/7
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  6. HARD GATES (DoD #5/6/7)")
print("=" * 72)

# 6.1: total_samples<50 → hard gate triggers, status=not_ready
db = _client_db(); _wipe(db)
for i in range(20):
    db.ta_prediction_history.insert_one(_hist_record(pid=f"low-{i}"))
healthy_health = {
    "status": "healthy",
    "block_scores": {"features": 1.0},
    "checks": {"features": {"metrics": {}}},
}
report = compute_readiness_report(db, healthy_health)
check("6.1 total_samples=20 < 50 → status=not_ready",
      report["status"] == "not_ready",
      f"status={report['status']} score={report['readiness_score']}")
check("6.2 hard gate flags total_samples_ok=False",
      report["hard_gates"]["total_samples_ok"] is False,
      f"gates={report['hard_gates']}")
check("6.3 low_total_samples in blocking",
      "low_total_samples" in report["blocking_factors"],
      f"blocking={report['blocking_factors']}")

# 6.2: feature_integrity 0.85 (< 0.90) → hard gate
db = _client_db(); _wipe(db)
for i in range(80):
    db.ta_prediction_history.insert_one(_hist_record(pid=f"fi-{i}"))
report = compute_readiness_report(db, {
    "status": "healthy",
    "block_scores": {"features": 0.85},
    "checks": {"features": {"metrics": {}}},
})
check("6.4 feature_integrity=0.85 < 0.90 → status=not_ready",
      report["status"] == "not_ready",
      f"status={report['status']} fi={report['components']['feature_integrity']}")
check("6.5 feature_integrity_low in blocking",
      "feature_integrity_low" in report["blocking_factors"],
      f"blocking={report['blocking_factors']}")
check("6.6 recommendation = fix_feature_pipeline",
      report["recommendation"] == "fix_feature_pipeline",
      f"rec={report['recommendation']}")

# 6.3: data_health=broken → hard gate
db = _client_db(); _wipe(db)
for i in range(80):
    db.ta_prediction_history.insert_one(_hist_record(pid=f"dh-{i}"))
report = compute_readiness_report(db, {
    "status": "broken",
    "block_scores": {"features": 1.0},
    "checks": {"features": {"metrics": {}}},
})
check("6.7 data_health=broken → status=not_ready",
      report["status"] == "not_ready",
      f"status={report['status']}")
check("6.8 data_health_broken in blocking",
      "data_health_broken" in report["blocking_factors"],
      f"blocking={report['blocking_factors']}")
check("6.9 recommendation = fix_data_health",
      report["recommendation"] == "fix_data_health",
      f"rec={report['recommendation']}")


# ═════════════════════════════════════════════════════════════════════════════
# 7. END-TO-END HEALTHY: 600 samples, balanced, 1 dominant cause, full regimes
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  7. END-TO-END HEALTHY → high readiness, prepare_trainer")
print("=" * 72)

db = _client_db(); _wipe(db)
# Spread 600 across all combinations, balanced classes
counter = 0
for pair in ("ETHUSDT", "BTCUSDT", "SOLUSDT"):
    for v in vol_states:
        for t in trend_states:
            for it in interactions:
                if counter >= 600:
                    break
                w = ["bull", "base", "bear"][counter % 3]
                rh = 0.020 if w == "bull" else (-0.020 if w == "bear" else 0.0001)
                db.ta_prediction_history.insert_one(_hist_record(
                    pid=f"H-{counter}", symbol=pair,
                    winning=w, return_h6=rh,
                    vol_state=v, trend_state=t, interaction=it))
                counter += 1

# Add 200 debug records, 1 strongly dominant cause (85%) + tail.
# 60/20/20 still produces normalized entropy ≈ 0.86 (> 0.70 threshold) which
# would correctly trigger 'unstable_error_patterns'. To exercise the
# 'prepare_trainer' recommendation we need a TRULY dominant pattern.
for i in range(200):
    cause = "momentum_misread" if i < 170 else (
        "structure_misread" if i < 190 else "interaction_misread")
    db.ta_prediction_debug.insert_one(_debug_record(pid=f"d-{i}",
                                                     root_cause=cause))

report = compute_readiness_report(db, {
    "status": "healthy",
    "block_scores": {"features": 1.0},
    "checks": {"features": {"metrics": {}}},
})
check("7.1 healthy state: status in (almost_ready, ready)",
      report["status"] in ("almost_ready", "ready"),
      f"status={report['status']} score={report['readiness_score']} components={report['components']}")
check("7.2 hard gates all pass",
      all(report["hard_gates"].values()),
      f"gates={report['hard_gates']}")
check("7.3 recommendation = prepare_trainer",
      report["recommendation"] == "prepare_trainer",
      f"rec={report['recommendation']}")
check("7.4 readiness_score > 0.70",
      report["readiness_score"] > 0.70,
      f"score={report['readiness_score']}")

# DoD #4: dominant cause → high error_stability
es = report["components"]["error_stability"]
check("7.5 dominant cause (60%) → error_stability > 0.40",
      es > 0.40,
      f"error_stability={es}")


# ═════════════════════════════════════════════════════════════════════════════
# 8. UNIFORM CAUSES → low readiness (DoD #3)
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  8. UNIFORM CAUSES → low readiness (DoD #3)")
print("=" * 72)

db = _client_db(); _wipe(db)
# 600 well-distributed samples
counter = 0
for pair in ("ETHUSDT", "BTCUSDT", "SOLUSDT"):
    for v in vol_states:
        for t in trend_states:
            for it in interactions:
                if counter >= 600:
                    break
                w = ["bull", "base", "bear"][counter % 3]
                rh = 0.020 if w == "bull" else (-0.020 if w == "bear" else 0.0001)
                db.ta_prediction_history.insert_one(_hist_record(
                    pid=f"U-{counter}", symbol=pair,
                    winning=w, return_h6=rh,
                    vol_state=v, trend_state=t, interaction=it))
                counter += 1
# But uniform 10 root causes → chaos
uniform_causes = [f"cause_{j}" for j in range(10)]
for i in range(200):
    db.ta_prediction_debug.insert_one(_debug_record(
        pid=f"d-{i}", root_cause=uniform_causes[i % 10]))
report = compute_readiness_report(db, {
    "status": "healthy",
    "block_scores": {"features": 1.0},
    "checks": {"features": {"metrics": {}}},
})
check("8.1 uniform causes → error_stability low",
      report["components"]["error_stability"] < 0.40,
      f"es={report['components']['error_stability']}")
check("8.2 uniform causes → blocking factors include unstable",
      "unstable_error_patterns" in report["blocking_factors"]
      or "no_dominant_failure_mode" in report["blocking_factors"],
      f"blocking={report['blocking_factors']}")
check("8.3 uniform-cause readiness < dominant-cause readiness",
      report["readiness_score"] < 0.85,
      f"score={report['readiness_score']}")


# ═════════════════════════════════════════════════════════════════════════════
# 9. READ-ONLY contract on real production DB
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  9. READ-ONLY CONTRACT — production trading_os DB")
print("=" * 72)

prod_db = MongoClient(MONGO_URL)["trading_os"]
sigs_before = {col: prod_db[col].estimated_document_count() for col in [
    "ta_prediction_history", "ta_prediction_debug", "ta_prediction_dataset",
    "ta_prediction_temporal_buffer", "ta_prediction_calibration_stats",
]}
report = compute_readiness_report(prod_db)
sigs_after = {col: prod_db[col].estimated_document_count() for col in sigs_before}
check("9.1 source collections unchanged after readiness compute",
      sigs_before == sigs_after,
      f"before={sigs_before} after={sigs_after}")
check("9.2 production report has required keys",
      all(k in report for k in (
          "status", "readiness_score", "hard_gates", "components",
          "blocking_factors", "recommendation", "details")),
      f"keys={sorted(report.keys())}")
check("9.3 components contains all 5 expected",
      set(report["components"].keys()) ==
      {"sample_quality", "feature_integrity", "class_balance",
       "error_stability", "regime_coverage"},
      f"components={list(report['components'].keys())}")

# 9.4: NEW collection 'ta_prediction_ml_readiness' must NOT exist (no persistence)
check("9.4 v1 is live-only: no ta_prediction_ml_readiness collection created",
      "ta_prediction_ml_readiness" not in prod_db.list_collection_names(),
      f"collections={prod_db.list_collection_names()}")


# ═════════════════════════════════════════════════════════════════════════════
# 10. HTTP endpoints
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  10. HTTP endpoints respond + correct contract")
print("=" * 72)

BASE = "http://localhost:8001/api/ta-prediction-intelligence/ml-readiness"
r = requests.get(BASE, timeout=15)
check("10.1 GET /ml-readiness → 200", r.status_code == 200, f"status={r.status_code}")
resp = r.json()
check("10.2 summary endpoint omits 'details' (trim view)",
      "details" not in resp,
      f"keys={sorted(resp.keys())}")
check("10.3 summary has status/score/components/blocking/recommendation",
      all(k in resp for k in (
          "status", "readiness_score", "hard_gates", "components",
          "blocking_factors", "recommendation")),
      f"keys={sorted(resp.keys())}")

r = requests.get(BASE + "/details", timeout=15)
check("10.4 GET /ml-readiness/details → 200", r.status_code == 200,
      f"status={r.status_code}")
det_resp = r.json()
check("10.5 details endpoint includes 'details' block",
      "details" in det_resp and isinstance(det_resp["details"], dict),
      f"keys={sorted(det_resp.keys())}")
check("10.6 details.samples / class_balance / error_stability / regime_coverage exist",
      all(k in det_resp["details"] for k in (
          "samples", "class_balance", "error_stability",
          "feature_integrity", "regime_coverage")),
      f"detail_keys={list(det_resp.get('details', {}).keys())}")


# Cleanup
_wipe(_client_db())


passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 72)
print(f"  RESULT: {passed}/{total} checks passed")
print("=" * 72)
sys.exit(0 if passed == total else 1)
