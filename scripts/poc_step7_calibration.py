#!/usr/bin/env python3
"""
Step 7 POC: end-to-end verification of TA Prediction Intelligence
          history calibration / ML-ready layer.

Runs:
  1. Unit math checks (calibration_engine: brier / hit-rate / Wilson)
  2. Unit invariant checks (scenario_calibration_adjuster: caps, floor/ceil,
     renormalise, no-op on insufficient samples)
  3. Outcome worker evaluate_prediction_with_candles() on synthetic candles
     for bull / base / bear scenarios
  4. Live HTTP smoke: /health, /live, /outcome_worker/status,
                       /calibration/rebuild, /calibration

Exit code 0 on all PASS, 1 otherwise.
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
import urllib.parse

sys.path.insert(0, "/app/backend")

from modules.ta_prediction_intelligence.calibration.calibration_engine import (  # noqa: E402
    aggregate_calibration,
    rebuild_all,
    _wilson_interval,
)
from modules.ta_prediction_intelligence.scenarios.scenario_calibration_adjuster import (  # noqa: E402
    apply_calibration_adjustment,
    MIN_SAMPLES,
    PER_DELTA_CAP,
    TOTAL_DELTA_CAP,
    PROB_FLOOR,
    PROB_CEIL,
)
from modules.ta_prediction_intelligence.evaluation.ta_prediction_outcome_worker import (  # noqa: E402
    evaluate_prediction_with_candles,
    resolve_winning_scenario,
)

BACKEND = "http://localhost:8001"


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ════════════════════════════════════════════════════════════════════════════
# 1. Calibration engine math
# ════════════════════════════════════════════════════════════════════════════


def test_calibration_engine_math():
    print("\n[test] calibration_engine math")
    # Build 30 synthetic records: all predict p(bull)=0.8, and 24 actually bullish.
    records = []
    for i in range(30):
        outcome = {"winning_scenario": "bull" if i < 24 else "bear"}
        records.append({
            "symbol": "ETHUSDT",
            "timeframe": "1H",
            "interaction": {"type": "breakout"},
            "dominant_engine": "momentum",
            "scenarios_interaction_adjusted": [
                {"name": "bull", "probability": 0.8},
                {"name": "base", "probability": 0.1},
                {"name": "bear", "probability": 0.1},
            ],
            "outcome": outcome,
        })
    buckets = aggregate_calibration(records, group_by="interaction_type")
    assert len(buckets) == 1, "one bucket expected"
    b = buckets[0]
    _assert(b["bucket_key"] == "breakout", "bucket key")
    _assert(b["n"] == 30, "n=30")
    _assert(abs(b["hit_rate"]["bull"] - 24 / 30) < 1e-6, "hit rate bull")
    _assert(abs(b["avg_predicted"]["bull"] - 0.8) < 1e-6, "avg predicted bull")
    # Brier: sum( (p - y)^2 )/n across 3 classes. For each record:
    # bull: p=0.8, y=1 if bull else 0; base: p=0.1, y=0; bear: p=0.1, y=0 if bull else 1.
    expected_brier_bull_case = (0.8 - 1) ** 2 + (0.1 - 0) ** 2 + (0.1 - 0) ** 2
    expected_brier_bear_case = (0.8 - 0) ** 2 + (0.1 - 0) ** 2 + (0.1 - 1) ** 2
    expected_brier = (24 * expected_brier_bull_case + 6 * expected_brier_bear_case) / 30
    _assert(abs(b["brier_score"] - expected_brier) < 1e-5, f"brier expected {expected_brier}")
    lo, hi = b["wilson_lower"]["bull"], b["wilson_upper"]["bull"]
    _assert(0 <= lo < 24 / 30 < hi <= 1, "wilson bull bounds")
    print("  ✅ n, hit_rate, avg_predicted, brier, wilson all correct")


def test_wilson_edge_cases():
    print("\n[test] Wilson CI edge cases")
    lo, hi = _wilson_interval(0, 0)
    _assert(lo == 0.0 and hi == 0.0, "n=0 returns zeros")
    lo, hi = _wilson_interval(5, 5)
    _assert(0.4 < lo <= hi <= 1.0, "all-hits bounded")
    lo, hi = _wilson_interval(0, 5)
    _assert(0.0 <= lo <= hi < 0.6, "zero-hits bounded")
    print("  ✅")


# ════════════════════════════════════════════════════════════════════════════
# 2. Calibration adjuster invariants
# ════════════════════════════════════════════════════════════════════════════


def test_adjuster_skips_when_insufficient():
    print("\n[test] adjuster skips when n < MIN_SAMPLES")
    scenarios = [
        {"name": "bull", "probability": 0.5},
        {"name": "base", "probability": 0.3},
        {"name": "bear", "probability": 0.2},
    ]
    stats = {
        "interaction_type": [
            {"bucket_key": "breakout", "n": 10, "calibration_gap": {"bull": 0.5, "base": 0, "bear": -0.5}}
        ]
    }
    new_s, meta = apply_calibration_adjustment(
        scenarios, {"symbol": "ETH", "timeframe": "1H", "interaction_type": "breakout"}, stats
    )
    _assert(meta["applied"] is False, "should not apply")
    _assert(meta["reason"] == "insufficient_samples", f"reason={meta['reason']}")
    probs = [s["probability"] for s in new_s]
    _assert(probs == [0.5, 0.3, 0.2], "probabilities unchanged")
    print("  ✅")


def test_adjuster_applies_and_invariants():
    print("\n[test] adjuster applies when n>=30 and respects invariants")
    scenarios = [
        {"name": "bull", "probability": 0.5},
        {"name": "base", "probability": 0.3},
        {"name": "bear", "probability": 0.2},
    ]
    # gap says bull historically 0.12 underpredicted, bear 0.07 overpredicted.
    stats = {
        "interaction_type": [
            {
                "bucket_key": "breakout",
                "n": 40,
                "calibration_gap": {"bull": 0.12, "base": -0.05, "bear": -0.07},
                "hit_rate": {"bull": 0.62, "base": 0.25, "bear": 0.13},
                "avg_predicted": {"bull": 0.5, "base": 0.3, "bear": 0.2},
                "brier_score": 0.3,
            }
        ]
    }
    new_s, meta = apply_calibration_adjustment(
        scenarios, {"symbol": "ETH", "timeframe": "1H", "interaction_type": "breakout"}, stats
    )
    _assert(meta["applied"] is True, "should apply")
    _assert(meta["bucket_n"] == 40, "bucket n")
    # Invariant: probabilities sum to 1.0
    total = sum(s["probability"] for s in new_s)
    _assert(abs(total - 1.0) < 1e-4, f"probs sum = {total}")
    # Per-scenario probability bounded (floor/ceil). The final `calibration_delta`
    # is computed AFTER renormalisation and can slightly exceed PER_DELTA_CAP;
    # the cap applies to the RAW pre-renorm deltas exposed via meta.raw_deltas.
    for s in new_s:
        _assert(PROB_FLOOR - 1e-6 <= s["probability"] <= PROB_CEIL + 1e-6, f"floor/ceil violated: {s}")
        _assert(s["calibrated"] is True, "calibrated flag")
    for k, v in meta["raw_deltas"].items():
        _assert(abs(v) <= PER_DELTA_CAP + 1e-6, f"raw delta cap violated: {k}={v}")
    # bull should have gone UP (positive gap)
    bull = next(s for s in new_s if s["name"] == "bull")
    _assert(bull["calibration_delta"] > 0, "bull delta positive")
    bear = next(s for s in new_s if s["name"] == "bear")
    _assert(bear["calibration_delta"] < 0, "bear delta negative")
    print(f"  ✅ applied, bull+{bull['calibration_delta']:+.4f}, bear{bear['calibration_delta']:+.4f}, sum={total:.6f}")


def test_adjuster_caps_extreme_deltas():
    print("\n[test] adjuster caps extreme calibration_gap")
    scenarios = [
        {"name": "bull", "probability": 0.5},
        {"name": "base", "probability": 0.3},
        {"name": "bear", "probability": 0.2},
    ]
    stats = {
        "interaction_type": [
            {
                "bucket_key": "breakout",
                "n": 100,
                "calibration_gap": {"bull": 0.9, "base": -0.45, "bear": -0.45},
                "hit_rate": {"bull": 1.0, "base": 0, "bear": 0},
                "avg_predicted": {"bull": 0.5, "base": 0.3, "bear": 0.2},
            }
        ]
    }
    new_s, meta = apply_calibration_adjustment(
        scenarios, {"symbol": "ETH", "timeframe": "1H", "interaction_type": "breakout"}, stats
    )
    _assert(meta["applied"] is True, "applied")
    total_abs = sum(abs(meta["raw_deltas"][k]) for k in ("bull", "base", "bear"))
    _assert(total_abs <= TOTAL_DELTA_CAP + 1e-6, f"total cap violated: {total_abs}")
    probs = [s["probability"] for s in new_s]
    _assert(abs(sum(probs) - 1.0) < 1e-6, "still sums to 1")
    for s in new_s:
        _assert(s["probability"] <= PROB_CEIL + 1e-6, f"ceil violated: {s}")
    print(f"  ✅ total |Δ|={total_abs:.4f} <= cap {TOTAL_DELTA_CAP}")


# ════════════════════════════════════════════════════════════════════════════
# 3. Outcome worker evaluate() logic
# ════════════════════════════════════════════════════════════════════════════


def _synthetic_candles(base_ts: int, prices: list, step_ms: int = 3_600_000):
    """Build candle dicts starting at base_ts, each with identical hi/lo/close."""
    out = []
    for i, p in enumerate(prices):
        out.append({
            "close_time": base_ts + i * step_ms,
            "open": p,
            "high": p,
            "low": p,
            "close": p,
        })
    return out


def test_outcome_bullish():
    print("\n[test] outcome worker bullish move")
    entry_ts = 1_000_000
    entry_price = 100.0
    prices = [entry_price] + [101, 102, 103, 104, 105, 106]
    candles = _synthetic_candles(entry_ts - 3_600_000, prices)
    record = {
        "symbol": "ETHUSDT",
        "timeframe": "1H",
        "entry_price": entry_price,
        "candle_close_ts": candles[0]["close_time"],
        "scenarios_interaction_adjusted": [
            {"name": "bull", "probability": 0.5, "target_price": 105.0, "invalidation_price": 95.0},
            {"name": "base", "probability": 0.3},
            {"name": "bear", "probability": 0.2, "target_price": 95.0, "invalidation_price": 105.0},
        ],
    }
    out = evaluate_prediction_with_candles(record, candles)
    _assert(out is not None, "outcome produced")
    _assert(out["winning_scenario"] == "bull", f"bull, got {out['winning_scenario']}")
    _assert(abs(out["return_h6"] - 0.06) < 1e-6, f"h6 return = {out['return_h6']}")
    _assert(out["max_favourable_move_pct"] > 0, "mfe > 0")
    _assert(out["candles_used"] == 6, "6 candles used")
    print(f"  ✅ bull, h6={out['return_h6']}, mfe={out['max_favourable_move_pct']}")


def test_outcome_not_ready():
    print("\n[test] outcome worker waits for N candles")
    entry_price = 100.0
    prices = [entry_price, 101, 102]  # only 2 future candles
    candles = _synthetic_candles(0, prices)
    record = {
        "entry_price": entry_price,
        "candle_close_ts": candles[0]["close_time"],
        "scenarios_interaction_adjusted": [],
    }
    out = evaluate_prediction_with_candles(record, candles)
    _assert(out is None, f"should not be ready, got {out}")
    print("  ✅")


def test_outcome_base_and_resolve_winner():
    print("\n[test] outcome base (flat) + resolve_winning_scenario default")
    prices = [100.0, 100.01, 100.02, 99.98, 100.0, 100.05, 99.9]
    candles = _synthetic_candles(1_000_000, prices)
    record = {
        "entry_price": 100.0,
        "candle_close_ts": candles[0]["close_time"],
        "scenarios_interaction_adjusted": [],
    }
    out = evaluate_prediction_with_candles(record, candles)
    _assert(out is not None, "outcome produced")
    _assert(out["winning_scenario"] == "base", f"expected base, got {out}")
    print(f"  ✅ base, h6={out['return_h6']}")


# ════════════════════════════════════════════════════════════════════════════
# 4. Live HTTP smoke
# ════════════════════════════════════════════════════════════════════════════


def _http_get(path: str, timeout: float = 20):
    req = urllib.request.Request(BACKEND + path)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def _http_post(path: str, body: dict = None, timeout: float = 20):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        BACKEND + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def test_http_health():
    print("\n[test] HTTP /health")
    st, body = _http_get("/api/ta-prediction-intelligence/health")
    _assert(st == 200, "status 200")
    _assert(body["ok"] is True, "ok")
    _assert("/outcome_worker/status" in (body.get("step7_entry_points") or []), "step7 endpoints exposed")
    print("  ✅ step7 endpoints exposed")


def test_http_live_and_persistence():
    print("\n[test] HTTP /live ETHUSDT 1H (also persists)")
    st, body = _http_get("/api/ta-prediction-intelligence/live?symbol=ETHUSDT&tf=1H")
    _assert(st == 200, "200")
    _assert("scenarios" in body and body["scenarios"], "scenarios present")
    _assert("scenarios_adjustment" in body, "step6 meta present")
    _assert("scenarios_calibration" in body, "step7 meta present")
    _assert("scenarios_pre_calibration" in body, "pre-calibration snapshot present")
    pid = body.get("prediction_id")
    _assert(pid is not None, f"prediction_id present, got {pid}")
    cal = body["scenarios_calibration"]
    print(f"  ✅ bias={body.get('bias')}, conf={body.get('confidence')}, pid={pid}, "
          f"cal_applied={cal.get('applied')}, reason={cal.get('reason')}")


def test_http_calibration_rebuild_and_read():
    print("\n[test] HTTP /calibration/rebuild + /calibration + /calibration/diagnostics")
    st, body = _http_post("/api/ta-prediction-intelligence/calibration/rebuild")
    _assert(st == 200, "200")
    _assert(body["ok"] is True, f"rebuild ok: {body}")
    print(f"  ✅ rebuilt from {body.get('source_records')} records, buckets={body.get('buckets_per_group')}")

    st, body = _http_get("/api/ta-prediction-intelligence/calibration?group_by=interaction_type")
    _assert(st == 200, "200")
    _assert("buckets" in body, "buckets key")
    print(f"  ✅ /calibration returned {body.get('total_buckets')} buckets")

    st, body = _http_get("/api/ta-prediction-intelligence/calibration/diagnostics")
    _assert(st == 200, "200")
    _assert("stats_by_group" in body and "summary" in body, "shape")
    print(f"  ✅ /diagnostics summary={body.get('summary')}")


def test_http_worker_status_and_history():
    print("\n[test] HTTP /outcome_worker/status + /history")
    st, body = _http_get("/api/ta-prediction-intelligence/outcome_worker/status")
    _assert(st == 200, "200")
    _assert(body["worker"]["running"] is True, "worker running")
    print(f"  ✅ worker running, ticks={body['worker']['ticks']}, evaluated={body['worker']['evaluated']}")

    st, body = _http_get("/api/ta-prediction-intelligence/history?limit=5")
    _assert(st == 200, "200")
    _assert("items" in body, "items key")
    print(f"  ✅ history count={body.get('count')}, states={body.get('state_counts')}")


# ════════════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════════════

TESTS = [
    test_calibration_engine_math,
    test_wilson_edge_cases,
    test_adjuster_skips_when_insufficient,
    test_adjuster_applies_and_invariants,
    test_adjuster_caps_extreme_deltas,
    test_outcome_bullish,
    test_outcome_not_ready,
    test_outcome_base_and_resolve_winner,
    test_http_health,
    test_http_live_and_persistence,
    test_http_calibration_rebuild_and_read,
    test_http_worker_status_and_history,
]


def main():
    failures = []
    for fn in TESTS:
        try:
            fn()
        except Exception as e:
            failures.append(f"{fn.__name__}: {type(e).__name__}: {e}")
            print(f"  ❌ {fn.__name__}: {type(e).__name__}: {e}")
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED {len(failures)} / {len(TESTS)}")
        for f in failures:
            print(" -", f)
        return 1
    print(f"ALL {len(TESTS)} TESTS PASS ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
