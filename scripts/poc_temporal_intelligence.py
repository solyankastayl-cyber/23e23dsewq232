#!/usr/bin/env python3
"""
Temporal Intelligence POC.

Unit + integration checks for:
  1. types.MIN_HISTORY + default dataclass
  2. trend_evolution / momentum_evolution / volatility_evolution thresholds
  3. regime_stats: stability / flip_frequency / duration
  4. count_persistence on trend_phase / momentum_state / interaction_type
  5. compute_transition_pressure: drivers/risks/pressures bounded [0..1]
  6. detect_sequence with INT-coded features (reverse map works)
  7. build_temporal_context: insufficient_history guard + ready path
  8. HTTP smoke: /live has temporal_intelligence with required keys
  9. Regression: Step 6/7/8/10 fields still intact
"""
from __future__ import annotations

import json
import sys
import urllib.request

sys.path.insert(0, "/app/backend")

BACKEND = "http://localhost:8001"


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _snap(features, ts=0):
    return {"ts": ts, "symbol": "X", "tf": "1H", "features": dict(features)}


# -----------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------

def test_types_defaults():
    print("\n[test] TemporalIntelligenceContext defaults")
    from modules.ta_prediction_intelligence.temporal_intelligence.types import (
        TemporalIntelligenceContext, MIN_HISTORY,
    )
    ctx = TemporalIntelligenceContext(symbol="ETHUSDT", timeframe="1H", window_size=0)
    d = ctx.to_dict()
    for k in ("symbol", "timeframe", "window_size", "trend_evolution",
              "momentum_evolution", "volatility_evolution",
              "regime_stability_score", "regime_flip_frequency", "regime_duration_bars",
              "trend_persistence", "momentum_persistence", "interaction_persistence",
              "reversal_pressure", "continuation_pressure", "instability_pressure",
              "detected_sequence", "sequence_confidence", "summary",
              "drivers", "risks", "min_history", "ready"):
        _assert(k in d, f"missing key {k}")
    _assert(d["ready"] is False, "ready False by default")
    _assert(d["min_history"] == MIN_HISTORY, "min_history stored")
    print(f"  ✅ all 22 keys present, MIN_HISTORY={MIN_HISTORY}")


# -----------------------------------------------------------------------
# State evolutions
# -----------------------------------------------------------------------

def test_trend_evolution():
    print("\n[test] trend_evolution thresholds")
    from modules.ta_prediction_intelligence.temporal_intelligence import trend_evolution
    # less than MIN_HISTORY → unknown
    _assert(trend_evolution([]) == "unknown", "empty → unknown")
    _assert(trend_evolution([_snap({"trend_strength": 0.5})] * 4) == "unknown", "<5 → unknown")
    # strengthening: recent avg > previous avg + 0.10
    hist = [_snap({"trend_strength": 0.0}) for _ in range(5)] + [
        _snap({"trend_strength": 0.3}), _snap({"trend_strength": 0.4}), _snap({"trend_strength": 0.5})
    ]
    _assert(trend_evolution(hist) == "strengthening", f"expected strengthening, got {trend_evolution(hist)}")
    # weakening
    hist = [_snap({"trend_strength": 0.6}) for _ in range(5)] + [
        _snap({"trend_strength": 0.3}), _snap({"trend_strength": 0.2}), _snap({"trend_strength": 0.1})
    ]
    _assert(trend_evolution(hist) == "weakening", f"weakening: {trend_evolution(hist)}")
    # reversing: sign flip both sides non-trivial
    hist = [_snap({"trend_strength": 0.6}) for _ in range(5)] + [
        _snap({"trend_strength": -0.3}), _snap({"trend_strength": -0.4}), _snap({"trend_strength": -0.5})
    ]
    _assert(trend_evolution(hist) == "reversing", f"reversing: {trend_evolution(hist)}")
    # flat
    hist = [_snap({"trend_strength": 0.05}) for _ in range(8)]
    _assert(trend_evolution(hist) == "flat", f"flat: {trend_evolution(hist)}")
    print("  ✅ strengthening / weakening / reversing / flat / unknown")


def test_momentum_evolution():
    print("\n[test] momentum_evolution")
    from modules.ta_prediction_intelligence.temporal_intelligence import momentum_evolution
    # accelerating
    hist = [_snap({"macd_slope_5": 0.05}) for _ in range(5)] + [
        _snap({"macd_slope_5": 0.30}), _snap({"macd_slope_5": 0.40}), _snap({"macd_slope_5": 0.50})
    ]
    _assert(momentum_evolution(hist) == "accelerating", f"accel: {momentum_evolution(hist)}")
    # decelerating
    hist = [_snap({"macd_slope_5": 0.50}) for _ in range(5)] + [
        _snap({"macd_slope_5": 0.20}), _snap({"macd_slope_5": 0.15}), _snap({"macd_slope_5": 0.10})
    ]
    _assert(momentum_evolution(hist) == "decelerating", f"decel: {momentum_evolution(hist)}")
    print("  ✅ accelerating / decelerating")


def test_volatility_evolution():
    print("\n[test] volatility_evolution")
    from modules.ta_prediction_intelligence.temporal_intelligence import volatility_evolution
    hist = [_snap({"atr_pct": 0.02}) for _ in range(5)] + [
        _snap({"atr_pct": 0.04}), _snap({"atr_pct": 0.05}), _snap({"atr_pct": 0.06})
    ]
    _assert(volatility_evolution(hist) == "expanding", f"exp: {volatility_evolution(hist)}")
    hist = [_snap({"atr_pct": 0.05}) for _ in range(5)] + [
        _snap({"atr_pct": 0.02}), _snap({"atr_pct": 0.015}), _snap({"atr_pct": 0.01})
    ]
    _assert(volatility_evolution(hist) == "compressing", f"compr: {volatility_evolution(hist)}")
    print("  ✅ expanding / compressing")


# -----------------------------------------------------------------------
# Regime + persistence
# -----------------------------------------------------------------------

def test_regime_stats():
    print("\n[test] regime_stats")
    from modules.ta_prediction_intelligence.temporal_intelligence import regime_stats
    # steady normal regime
    hist = [_snap({"volatility_state": 1}) for _ in range(10)]
    r = regime_stats(hist)
    _assert(r["regime_stability_score"] == 1.0, "stable=1.0")
    _assert(r["regime_flip_frequency"] == 0.0, "no flips")
    _assert(r["regime_duration_bars"] == 10, "all 10 bars in current")
    # alternating
    hist = [_snap({"volatility_state": i % 2}) for i in range(10)]
    r = regime_stats(hist)
    _assert(r["regime_flip_frequency"] == 1.0, "alternating → 1.0")
    _assert(r["regime_stability_score"] == 0.0, "unstable")
    _assert(r["regime_duration_bars"] == 1, "latest state duration = 1")
    print("  ✅")


def test_persistence():
    print("\n[test] count_persistence")
    from modules.ta_prediction_intelligence.temporal_intelligence import count_persistence
    hist = [_snap({"trend_phase": 0}) for _ in range(5)] + [_snap({"trend_phase": 2}) for _ in range(3)]
    _assert(count_persistence(hist, "trend_phase") == 3, "3 consecutive trend_phase=2")
    hist = [_snap({"interaction_type": 3}) for _ in range(7)]
    _assert(count_persistence(hist, "interaction_type") == 7, "7 consecutive")
    _assert(count_persistence([], "trend_phase") == 0, "empty → 0")
    print("  ✅")


# -----------------------------------------------------------------------
# Transition pressure
# -----------------------------------------------------------------------

def test_transition_pressure():
    print("\n[test] compute_transition_pressure drivers/risks and bounds")
    from modules.ta_prediction_intelligence.temporal_intelligence import compute_transition_pressure
    # insufficient history → all zeros
    p = compute_transition_pressure([_snap({})] * 3)
    _assert(p["reversal_pressure"] == 0.0, "insufficient → 0")
    _assert(p["drivers"] == [] and p["risks"] == [], "empty lists")
    # bearish divergence + exhaustion + expansion + misalignment + conflict
    latest = {
        "rsi_div_bear": 1, "exhaustion_flag": 1, "expansion_flag": 1,
        "structure_momentum_alignment": -0.8, "conflict_ratio": 0.6,
        "pattern_conflict_flag": 1, "structure_break_flag": 1,
    }
    hist = [_snap({}) for _ in range(5)] + [_snap(latest)]
    p = compute_transition_pressure(hist)
    _assert(0.0 <= p["reversal_pressure"] <= 1.0, f"reversal bounded: {p['reversal_pressure']}")
    _assert(0.0 <= p["continuation_pressure"] <= 1.0, "continuation bounded")
    _assert(0.0 <= p["instability_pressure"] <= 1.0, "instability bounded")
    _assert(p["reversal_pressure"] > 0.3, f"strong reversal signals → high: {p['reversal_pressure']}")
    _assert("bearish_divergence" in p["risks"], f"driver bearish_div: {p['risks']}")
    _assert("momentum_exhaustion" in p["risks"], "exhaustion risk")
    _assert("high_engine_conflict" in p["risks"], "conflict risk")
    print(f"  ✅ rev={p['reversal_pressure']}, cont={p['continuation_pressure']}, inst={p['instability_pressure']}")


# -----------------------------------------------------------------------
# Sequence detection
# -----------------------------------------------------------------------

def test_sequence_detection():
    print("\n[test] detect_sequence with INT-coded features")
    from modules.ta_prediction_intelligence.learning.feature_schema import (
        INTERACTION_TYPE_CODES, VOLATILITY_STATE_CODES,
    )
    from modules.ta_prediction_intelligence.temporal_intelligence import detect_sequence
    # Pattern 1: compression → breakout → pullback → trend_continuation
    codes = [
        INTERACTION_TYPE_CODES["compression"],
        INTERACTION_TYPE_CODES["breakout"],
        INTERACTION_TYPE_CODES["pullback"],
        INTERACTION_TYPE_CODES["trend_continuation"],
    ]
    hist = [_snap({"interaction_type": c, "volatility_state": 1}) for c in codes]
    name, conf = detect_sequence(hist)
    _assert(name == "compression_breakout_pullback_continuation", f"got {name}")
    _assert(conf >= 0.85, f"conf={conf}")
    # Pattern 4: sustained chaos (vol=3 ×3)
    chaos = VOLATILITY_STATE_CODES["chaos"]
    hist = [_snap({"interaction_type": 0, "volatility_state": 1}) for _ in range(3)] + \
           [_snap({"interaction_type": 0, "volatility_state": chaos}) for _ in range(3)]
    name, conf = detect_sequence(hist)
    _assert(name == "high_volatility_instability", f"chaos seq: {name}")
    # None / nothing matches
    hist = [_snap({"interaction_type": 0, "volatility_state": 1}) for _ in range(6)]
    name, conf = detect_sequence(hist)
    _assert(name is None and conf == 0.0, f"no match: {name} / {conf}")
    print("  ✅ 4-step sequence + chaos regime + null-case")


# -----------------------------------------------------------------------
# Orchestrator
# -----------------------------------------------------------------------

def test_builder_guards_and_ready():
    print("\n[test] build_temporal_context guard + ready")
    from modules.ta_prediction_intelligence.temporal_intelligence import (
        build_temporal_context,
    )
    # insufficient → ready False
    ctx = build_temporal_context("ETHUSDT", "1H", [_snap({"trend_strength": 0.5})] * 3)
    d = ctx.to_dict()
    _assert(d["ready"] is False, "not ready")
    _assert(d["summary"] == "insufficient_history", f"summary: {d['summary']}")
    _assert(d["reversal_pressure"] == 0.0, "zero pressure on short history")
    # ready
    hist = [_snap({"trend_strength": 0.05, "atr_pct": 0.02, "volatility_state": 1,
                   "trend_phase": 0, "momentum_state": 1, "interaction_type": 0})
            for _ in range(10)]
    ctx = build_temporal_context("ETHUSDT", "1H", hist)
    d = ctx.to_dict()
    _assert(d["ready"] is True, "ready True")
    _assert(d["window_size"] == 10, f"window=10, got {d['window_size']}")
    _assert(d["trend_evolution"] != "unknown", "evolutions computed")
    print("  ✅ both guard + ready paths")


# -----------------------------------------------------------------------
# HTTP integration + regression
# -----------------------------------------------------------------------

def _http_get(path):
    with urllib.request.urlopen(BACKEND + path, timeout=20) as r:
        return r.status, json.loads(r.read().decode())


def test_http_live_has_temporal_intelligence():
    print("\n[test] HTTP /live carries temporal_intelligence")
    # warm buffer
    for _ in range(6):
        _http_get("/api/ta-prediction-intelligence/live?symbol=ETHUSDT&tf=1H")
    st, body = _http_get("/api/ta-prediction-intelligence/live?symbol=ETHUSDT&tf=1H")
    _assert(st == 200, "200")
    ti = body.get("temporal_intelligence")
    _assert(ti is not None, "temporal_intelligence present")
    for k in ("ready", "window_size", "trend_evolution", "momentum_evolution",
              "volatility_evolution", "regime_stability_score",
              "regime_flip_frequency", "regime_duration_bars",
              "trend_persistence", "momentum_persistence", "interaction_persistence",
              "reversal_pressure", "continuation_pressure", "instability_pressure",
              "detected_sequence", "sequence_confidence", "summary",
              "drivers", "risks", "min_history"):
        _assert(k in ti, f"missing temporal key {k}")
    _assert(ti["ready"] is True, f"ready after 6 calls: {ti.get('ready')}")
    _assert(ti["window_size"] >= 5, "window size ≥5 after warmup")
    print(f"  ✅ ready={ti['ready']}, window={ti['window_size']}, trend={ti['trend_evolution']}, summary={ti['summary']}")


def test_regression_step67810_intact():
    print("\n[test] regression: Step 6/7/8/10 fields intact after Temporal layer")
    st, body = _http_get("/api/ta-prediction-intelligence/live?symbol=ETHUSDT&tf=1H")
    _assert("scenarios_adjustment" in body, "Step 6 present")
    _assert("scenarios_calibration" in body, "Step 7 present")
    _assert("prediction_id" in body, "Step 7 pid")
    _assert("_features_debug" in body and body["_features_debug"]["feature_count"] == 82, "Step 8 82 features")
    # history record should carry temporal_intelligence now
    st, body = _http_get("/api/ta-prediction-intelligence/history?symbol=ETHUSDT&tf=1H&limit=1")
    _assert(st == 200, "200")
    items = body.get("items") or []
    if items:
        _assert("temporal_intelligence" in items[0] or "features_v1" in items[0], "history carries temporal+features")
    # dataset stats still works
    st, body = _http_get("/api/ta-prediction-intelligence/dataset/stats")
    _assert(st == 200 and body["ok"] is True, "dataset/stats OK")
    print("  ✅ all previous steps survive temporal addition")


TESTS = [
    test_types_defaults,
    test_trend_evolution,
    test_momentum_evolution,
    test_volatility_evolution,
    test_regime_stats,
    test_persistence,
    test_transition_pressure,
    test_sequence_detection,
    test_builder_guards_and_ready,
    test_http_live_has_temporal_intelligence,
    test_regression_step67810_intact,
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
