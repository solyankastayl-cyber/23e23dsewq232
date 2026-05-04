"""
QA — Root-Cause Aggregator (read-only, live-only).

Validates 8 DoD points:

  1. HHI concentration: 1 cause=1.0, 10 even=0.10
  2. Temporal stability: same top across halves=1.0; flipped → recent_top_share
  3. Actionable requires ALL 4 conditions
  4. underconfident is NOT counted as error
  5. Only single-axis cohorts in v1
  6. Invalid axis returns ok=false + allowed list
  7. Read-only: source counts unchanged
  8. Routes return /root-causes, /root-causes/by/{axis}, /root-causes/weaknesses

Run:
    python3 /app/scripts/qa_root_cause_aggregator.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
import requests
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")

from modules.ta_prediction_intelligence.root_cause_aggregator import (
    AXES,
    Axis,
    MIN_COHORT,
    MIN_CONCENTRATION,
    MIN_ERROR_RATE,
    MIN_STABILITY,
    NON_ERROR_TYPES,
    STABILITY_SPLIT_MIN,
    compute_hhi,
    compute_top_share,
    compute_stability,
    is_actionable,
    build_weakness_record,
    build_cohorts,
    build_global,
    compute_root_cause_report,
)
from modules.ta_prediction_intelligence.root_cause_aggregator.cohort_builder import (
    load_joined_records,
)


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results: list = []


def check(name, ok, detail="", extra=None):
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
TEST_DB = "trading_os_rootcause_qa"


def _client_db():
    return MongoClient(MONGO_URL)[TEST_DB]


def _wipe(db):
    for c in db.list_collection_names():
        db.drop_collection(c)


def _debug(*, pid, error_type="wrong_direction", root_cause="momentum_misread",
           symbol="ETHUSDT", tf="1H", interaction="trend_continuation",
           signal_strength="moderate", primary="bull",
           analyzed_at=None, no_edge=False):
    return {
        "prediction_id": pid,
        "symbol": symbol, "tf": tf,
        "candle_close_ts": 1700000000,
        "error_type": error_type,
        "root_cause_primary": root_cause,
        "no_edge_ignored": no_edge,
        "signal_strength": signal_strength,
        "interaction_type": interaction,
        "primary_scenario": primary,
        "confidence_bucket": "medium",
        "analyzed_at": analyzed_at or datetime.now(timezone.utc),
    }


def _hist(*, pid, symbol="ETHUSDT", tf="1H", decision_bias="bullish",
          vol_state="normal", trend_state="weak_trend", created_at=None):
    return {
        "prediction_id": pid,
        "symbol": symbol, "timeframe": tf,
        "evaluation_state": "evaluated",
        "candle_close_ts": 1700000000,
        "decision_intelligence": {"decision_bias": decision_bias,
                                  "primary_scenario": "bull"},
        "feature_states": {"volatility": vol_state, "trend": trend_state},
        "created_at": created_at or datetime.now(timezone.utc),
        "outcome": {"evaluated_at": datetime.now(timezone.utc),
                    "winning_scenario": "bull"},
    }


# ═════════════════════════════════════════════════════════════════════════════
# DoD 1. HHI concentration
# ═════════════════════════════════════════════════════════════════════════════

print("=" * 72)
print("  DoD 1. HHI concentration")
print("=" * 72)

check("1.1 1 cause @ 100% → HHI = 1.0",
      compute_hhi({"a": 100}) == 1.0, f"got={compute_hhi({'a': 100})}")
check("1.2 10 even causes → HHI = 0.10",
      abs(compute_hhi({f"c{i}": 1 for i in range(10)}) - 0.10) < 1e-6,
      f"got={compute_hhi({f'c{i}': 1 for i in range(10)})}")
check("1.3 50/50 split → HHI = 0.50",
      compute_hhi({"a": 50, "b": 50}) == 0.50)
check("1.4 empty distribution → HHI = 0.0",
      compute_hhi({}) == 0.0)
top_cause, top_share = compute_top_share({"momentum_misread": 30, "structure_misread": 10})
check("1.5 top_share computed correctly",
      top_cause == "momentum_misread" and abs(top_share - 0.75) < 1e-6,
      f"top={top_cause} share={top_share}")


# ═════════════════════════════════════════════════════════════════════════════
# DoD 2. Temporal stability (split + same-vs-flipped)
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 2. Temporal stability")
print("=" * 72)

base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

# 2.1: 40 records, all errors with same cause → stability = 1.0
records = [
    _debug(pid=f"a-{i}", root_cause="momentum_misread",
           analyzed_at=base_ts + timedelta(minutes=i))
    for i in range(40)
]
hhi = compute_hhi({"momentum_misread": 40})
check("2.1 same top across halves → stability = 1.0",
      abs(compute_stability(records, cohort_concentration=hhi) - 1.0) < 1e-9,
      f"stability={compute_stability(records, cohort_concentration=hhi)}")

# 2.2: 20 first records cause=A, 20 last cause=B → flipped → stability = recent_top_share
records = []
for i in range(20):
    records.append(_debug(pid=f"a-{i}", root_cause="cause_A",
                          analyzed_at=base_ts + timedelta(minutes=i)))
for i in range(20):
    records.append(_debug(pid=f"b-{i}", root_cause="cause_B",
                          analyzed_at=base_ts + timedelta(minutes=20 + i)))
# half=20 → recent slice records[20:] (all B), recent_top_share=1.0
# But baseline top=cause_A, recent top=cause_B → DIFFERENT → return recent_top_share
hhi_flipped = compute_hhi({"cause_A": 20, "cause_B": 20})
stab = compute_stability(records, cohort_concentration=hhi_flipped)
check("2.2 flipped top → stability = recent_top_share (all-B half ⇒ 1.0)",
      abs(stab - 1.0) < 1e-9, f"stability={stab}")

# 2.3: half/half within recent → recent_top_share = 0.5
records = []
for i in range(20):
    records.append(_debug(pid=f"a-{i}", root_cause="cause_A",
                          analyzed_at=base_ts + timedelta(minutes=i)))
for i in range(10):
    records.append(_debug(pid=f"b-{i}", root_cause="cause_B",
                          analyzed_at=base_ts + timedelta(minutes=20 + i)))
for i in range(10):
    records.append(_debug(pid=f"c-{i}", root_cause="cause_C",
                          analyzed_at=base_ts + timedelta(minutes=30 + i)))
hhi3 = 0.50  # arbitrary
stab = compute_stability(records, cohort_concentration=hhi3)
# baseline_errors=20 (cause_A), recent_errors=20 (B+C 10+10)
# baseline top=A, recent top=B (or C, ties broken alphabetically: B)
# different → stability = recent_top_share = 0.50
check("2.3 flipped + 50/50 recent → stability = 0.5",
      abs(stab - 0.5) < 1e-9, f"stability={stab}")

# 2.4: cohort < STABILITY_SPLIT_MIN (40) → stability = concentration
records = [
    _debug(pid=f"a-{i}", root_cause="momentum_misread",
           analyzed_at=base_ts + timedelta(minutes=i))
    for i in range(20)
]
stab = compute_stability(records, cohort_concentration=0.55)
check("2.4 cohort<40 → stability falls back to concentration (0.55)",
      abs(stab - 0.55) < 1e-9, f"stability={stab}")

# 2.5: no errors at all → stability = 0
records = [
    _debug(pid=f"a-{i}", error_type="correct", root_cause=None,
           analyzed_at=base_ts + timedelta(minutes=i))
    for i in range(40)
]
stab = compute_stability(records, cohort_concentration=0.0)
check("2.5 no errors → stability = 0.0",
      stab == 0.0, f"stability={stab}")


# ═════════════════════════════════════════════════════════════════════════════
# DoD 3. Actionable requires all 4 conditions
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 3. Actionable requires all 4 conditions")
print("=" * 72)

base_cohort = {
    "n": 30, "error_count": 20, "error_rate": 0.667,
    "top_cause": "momentum_misread", "top_cause_share": 0.65,
    "concentration": 0.45, "stability": 0.85,
    "distribution": {"momentum_misread": 13, "structure_overweight": 4, "x": 3},
    "actionable": False,
}
check("3.1 all 4 conditions met → actionable=True",
      is_actionable(base_cohort) is True)
# Fail each condition individually
check("3.2 n<20 → False",
      is_actionable({**base_cohort, "n": 18}) is False)
check("3.3 error_rate<0.50 → False",
      is_actionable({**base_cohort, "error_rate": 0.49}) is False)
check("3.4 concentration<0.30 → False",
      is_actionable({**base_cohort, "concentration": 0.29}) is False)
check("3.5 stability<0.70 → False",
      is_actionable({**base_cohort, "stability": 0.69}) is False)
check("3.6 top_cause==unknown_cause → False",
      is_actionable({**base_cohort, "top_cause": "unknown_cause"}) is False)
check("3.7 build_weakness_record returns None when not actionable",
      build_weakness_record("symbol_tf", "ETHUSDT_1H",
                            {**base_cohort, "n": 10}) is None)
wk = build_weakness_record("symbol_tf", "ETHUSDT_1H", base_cohort)
check("3.8 actionable record carries axis/cohort/rationale/suggested_action",
      wk is not None
      and wk["axis"] == "symbol_tf" and wk["cohort"] == "ETHUSDT_1H"
      and "rationale" in wk and "suggested_action" in wk
      and "momentum_misread" in wk["suggested_action"]
      and "ETHUSDT_1H" in wk["suggested_action"],
      f"wk={wk}")


# ═════════════════════════════════════════════════════════════════════════════
# DoD 4. underconfident is NOT counted as error
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 4. underconfident NOT counted as error")
print("=" * 72)

records = [
    _debug(pid=f"e-{i}", error_type="wrong_direction", root_cause="momentum_misread",
           analyzed_at=base_ts + timedelta(minutes=i))
    for i in range(10)
] + [
    _debug(pid=f"u-{i}", error_type="underconfident", root_cause=None,
           analyzed_at=base_ts + timedelta(minutes=10 + i))
    for i in range(10)
] + [
    _debug(pid=f"c-{i}", error_type="correct", root_cause=None,
           analyzed_at=base_ts + timedelta(minutes=20 + i))
    for i in range(10)
]
db = _client_db(); _wipe(db)
for r in records:
    db.ta_prediction_debug.insert_one(r)
for r in records:
    db.ta_prediction_history.insert_one(_hist(pid=r["prediction_id"]))

joined = load_joined_records(db)
by_axis = build_cohorts(joined)
sym_cohorts = by_axis["symbol_tf"]
eth = sym_cohorts.get("ETHUSDT_1H", {})
check("4.1 cohort.n includes ALL records (30)",
      eth.get("n") == 30, f"n={eth.get('n')}")
check("4.2 error_count = 10 (wrong_direction only, NOT underconfident/correct)",
      eth.get("error_count") == 10,
      f"error_count={eth.get('error_count')}")
check("4.3 error_rate = 10/30",
      abs(eth.get("error_rate") - (10/30)) < 1e-6,
      f"got={eth.get('error_rate')}")


# ═════════════════════════════════════════════════════════════════════════════
# DoD 5. Only single-axis cohorts in v1
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 5. Only single-axis cohorts (no cross-axis)")
print("=" * 72)

check("5.1 AXES has exactly 6 entries",
      len(AXES) == 6, f"axes={AXES}")
check("5.2 by_axis has only the 6 declared axes",
      set(by_axis.keys()) == set(AXES),
      f"keys={set(by_axis.keys())}")
# No nested axis combinations
for axis, cohorts in by_axis.items():
    has_compound = any("|" in label or "×" in label or " AND " in label
                        for label in cohorts.keys())
    if has_compound:
        check(f"5.x axis={axis} contains compound label", False,
              f"labels={list(cohorts.keys())}")
        break
else:
    check("5.3 no compound axis labels exist anywhere", True)


# ═════════════════════════════════════════════════════════════════════════════
# DoD 6. Invalid axis returns ok=false + allowed list
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 6. Invalid axis HTTP behaviour")
print("=" * 72)

BASE = "http://localhost:8001/api/ta-prediction-intelligence/root-causes"
r = requests.get(BASE + "/by/banana", timeout=10)
body = r.json()
check("6.1 invalid axis → 400",
      r.status_code == 400, f"status={r.status_code} body={body}")
check("6.2 invalid axis → ok=false",
      body.get("ok") is False, f"body={body}")
check("6.3 invalid axis → error=invalid_axis",
      body.get("error") == "invalid_axis", f"body={body}")
check("6.4 invalid axis → allowed = AXES",
      body.get("allowed") == AXES, f"allowed={body.get('allowed')}")

# Valid axis responds 200
r = requests.get(BASE + "/by/symbol_tf", timeout=10).json()
check("6.5 valid axis → ok=true + cohorts dict",
      r.get("ok") is True and "cohorts" in r,
      f"keys={sorted(r.keys())}")


# ═════════════════════════════════════════════════════════════════════════════
# DoD 7. Read-only: source counts unchanged
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 7. Read-only contract — production trading_os DB")
print("=" * 72)

prod_db = MongoClient(MONGO_URL)["trading_os"]
sigs_before = {col: prod_db[col].estimated_document_count() for col in [
    "ta_prediction_history", "ta_prediction_debug",
    "ta_prediction_dataset", "ta_prediction_temporal_buffer",
    "ta_prediction_calibration_stats",
]}
report = compute_root_cause_report(prod_db)
sigs_after = {col: prod_db[col].estimated_document_count() for col in sigs_before}
check("7.1 source collections unchanged after compute",
      sigs_before == sigs_after,
      f"before={sigs_before} after={sigs_after}")
check("7.2 v1 is live-only: no ta_prediction_root_cause_aggregate collection",
      "ta_prediction_root_cause_aggregate" not in prod_db.list_collection_names())


# ═════════════════════════════════════════════════════════════════════════════
# DoD 8. Routes
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  DoD 8. Routes")
print("=" * 72)

# All 3 endpoints respond
for ep in ["", "/by/symbol_tf", "/weaknesses"]:
    r = requests.get(BASE + ep, timeout=15)
    check(f"8.0 GET {BASE + ep} → 200", r.status_code == 200,
          f"status={r.status_code}")

resp = requests.get(BASE, timeout=15).json()
check("8.1 /root-causes has by_axis + actionable_weaknesses + summary",
      all(k in resp for k in ("by_axis", "actionable_weaknesses", "summary")),
      f"keys={sorted(resp.keys())}")
check("8.2 /root-causes by_axis has all 6 axes",
      set(resp["by_axis"].keys()) == set(AXES),
      f"axes={list(resp['by_axis'].keys())}")
sm = resp["summary"]
check("8.3 summary has total_debug + total_error + actionable_count + concentration_global",
      all(k in sm for k in (
          "total_debug_records", "total_error_records",
          "actionable_count", "concentration_global", "min_cohort_size")),
      f"summary_keys={sorted(sm.keys())}")
check("8.4 summary.min_cohort_size == 20", sm["min_cohort_size"] == 20)


# ═════════════════════════════════════════════════════════════════════════════
# Bonus: full end-to-end actionable
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  Bonus. Full end-to-end actionable detection")
print("=" * 72)

db = _client_db(); _wipe(db)
# 50 records on ETHUSDT_1H, INTERLEAVED in time so the same root-cause
# distribution holds in both temporal halves (stability=1.0).
#   30 errors: momentum_misread  (60%)
#   10 errors: structure_misread (20%)
#   10 correct                    (20%)
# Distribute deterministically: every 5 records → 3 momentum, 1 structure, 1 correct
for i in range(50):
    pos = i % 5
    if pos < 3:
        et, rc = "wrong_direction", "momentum_misread"
    elif pos == 3:
        et, rc = "wrong_direction", "structure_misread"
    else:
        et, rc = "correct", None
    db.ta_prediction_debug.insert_one(_debug(
        pid=f"E-{i}", error_type=et, root_cause=rc,
        analyzed_at=base_ts + timedelta(minutes=i),
    ))
    db.ta_prediction_history.insert_one(_hist(pid=f"E-{i}"))

report = compute_root_cause_report(db)
eth = report["by_axis"]["symbol_tf"]["ETHUSDT_1H"]
check("B.1 cohort n=50, error_count=40",
      eth["n"] == 50 and eth["error_count"] == 40,
      f"cohort={eth}")
check("B.2 top_cause = momentum_misread, share = 0.75",
      eth["top_cause"] == "momentum_misread"
      and abs(eth["top_cause_share"] - 0.75) < 1e-6,
      f"top={eth['top_cause']} share={eth['top_cause_share']}")
expected_hhi = (30/40) ** 2 + (10/40) ** 2  # 0.5625 + 0.0625 = 0.625
check("B.3 concentration HHI ≈ 0.625",
      abs(eth["concentration"] - expected_hhi) < 1e-3,
      f"hhi={eth['concentration']} expected={expected_hhi}")
check("B.4 stability = 1.0 (same top across halves)",
      abs(eth["stability"] - 1.0) < 1e-6,
      f"stability={eth['stability']}")
check("B.5 actionable=True (all 4 conditions met)",
      eth["actionable"] is True,
      f"actionable={eth['actionable']}")
weaknesses = report["actionable_weaknesses"]
check("B.6 actionable_weaknesses contains symbol_tf=ETHUSDT_1H entry",
      any(w["axis"] == "symbol_tf" and w["cohort"] == "ETHUSDT_1H"
          and w["top_cause"] == "momentum_misread" for w in weaknesses),
      f"weaknesses={weaknesses}")
check("B.7 weakness rationale + suggested_action present",
      len(weaknesses) > 0
      and weaknesses[0].get("rationale")
      and "Investigate" in weaknesses[0].get("suggested_action", ""),
      f"first={weaknesses[0] if weaknesses else None}")


# Cleanup
_wipe(_client_db())


passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 72)
print(f"  RESULT: {passed}/{total} checks passed")
print("=" * 72)
sys.exit(0 if passed == total else 1)
