"""
QA — Debug Layer (read-only interpretation).

Two-part validation:

1. PURE: synthesise records covering all 8 ErrorType branches and all 6
   root-cause priorities. Validate taxonomy.classify_error() and
   root_cause.attribute_root_causes().

2. ENDPOINTS: backdate-trick on real history, force outcome evaluation,
   trigger /debug/rebuild, then verify /debug/stats has Tier 1/2/3 keys
   populated and /debug/case/{pid} returns the analysed case.

Run:
    python3 /app/scripts/qa_debug_layer.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import asyncio
import requests

sys.path.insert(0, "/app/backend")

from modules.ta_prediction_intelligence.debug import (
    ErrorType,
    classify_error,
    attribute_root_causes,
    build_debug_record,
    compute_metrics,
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
# Synthetic record builder
# ─────────────────────────────────────────────────────────────────────────────

def _record(
    *,
    pred_scenario: str = "bull",
    decision_confidence: float = 0.7,
    signal_strength: str = "moderate",
    risk_level: str = "low",
    primary_prob: float = 0.7,
    bias_aggregated: str = "bullish",
    interaction_type: str = "trend_continuation",
    contributions=None,
    temporal_ready: bool = True,
    continuation_pressure: float = 0.4,
    reversal_pressure: float = 0.2,
    instability_pressure: float = 0.1,
    conflict_ratio: float = 0.1,
    return_h1: float = 0.005,
    return_h6: float = 0.012,
    mfe: float = 0.015,
    mae: float = -0.003,
    volatility_h6: float = 0.002,
    winning_scenario: str = "bull",
    dominant_engine: str = "structure",
    pred_id: str = "test-pred",
):
    return {
        "prediction_id": pred_id,
        "symbol": "ETHUSDT",
        "timeframe": "1H",
        "candle_close_ts": 1700000000,
        "entry_price": 3000.0,
        "evaluation_state": "evaluated",
        "bias": bias_aggregated,
        "confidence": 0.55,
        "conflict_ratio": conflict_ratio,
        "dominant_engine": dominant_engine,
        "contributions": contributions or [
            {"engine": "structure", "bias": bias_aggregated, "confidence": 0.7, "quality": 0.8, "drivers": [], "risks": []},
            {"engine": "momentum", "bias": bias_aggregated, "confidence": 0.6, "quality": 0.7, "drivers": [], "risks": []},
        ],
        "interaction": {"type": interaction_type, "confidence": 0.6},
        "temporal_intelligence": {
            "ready": temporal_ready,
            "regime_stability_score": 0.5,
            "continuation_pressure": continuation_pressure,
            "reversal_pressure": reversal_pressure,
            "instability_pressure": instability_pressure,
            "regime_flip_frequency": 0.1,
            "detected_sequence": "",
        } if temporal_ready else {"ready": False},
        "decision_intelligence": {
            "primary_scenario": pred_scenario,
            "secondary_scenario": "base",
            "scenario_probability": primary_prob,
            "decision_confidence": decision_confidence,
            "decision_bias": "bullish" if pred_scenario == "bull" else ("bearish" if pred_scenario == "bear" else "neutral"),
            "signal_strength": signal_strength,
            "risk_level": risk_level,
            "alignment_score": 0.7,
            "temporal_score": 0.6,
        },
        "outcome": {
            "return_h1": return_h1,
            "return_h3": return_h6 * 0.7,
            "return_h6": return_h6,
            "max_favourable_move_pct": mfe,
            "max_adverse_move_pct": mae,
            "volatility_future_h6": volatility_h6,
            "winning_scenario": winning_scenario,
            "evaluated_at": "2026-01-01T00:00:00Z",
            "candles_used": 6,
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1. TAXONOMY — every ErrorType branch reachable + correct
# ═════════════════════════════════════════════════════════════════════════════

print("=" * 72)
print("  1. TAXONOMY — all 8 ErrorType branches")
print("=" * 72)

# 1.1 CORRECT
rec = _record(return_h6=0.020, winning_scenario="bull", decision_confidence=0.55)
et, _ = classify_error(rec)
check("1.1 CORRECT (bull predicted, bull won, decent move)",
      et == ErrorType.CORRECT, f"got={et.value}")

# 1.2 WRONG_DIRECTION (low confidence wrong)
rec = _record(return_h6=-0.020, winning_scenario="bear", decision_confidence=0.50,
              bias_aggregated="bullish",
              contributions=[{"engine": "structure", "bias": "bullish", "confidence": 0.6, "quality": 0.7}])
et, _ = classify_error(rec)
check("1.2 WRONG_DIRECTION (predicted bull, market bear, conf<0.65)",
      et == ErrorType.WRONG_DIRECTION, f"got={et.value}")

# 1.3 OVERCONFIDENT (high confidence wrong)
rec = _record(return_h6=-0.020, winning_scenario="bear", decision_confidence=0.78,
              bias_aggregated="bullish",
              contributions=[{"engine": "structure", "bias": "bullish", "confidence": 0.8, "quality": 0.9}])
et, _ = classify_error(rec)
check("1.3 OVERCONFIDENT (predicted bull conf=0.78, market bear)",
      et == ErrorType.OVERCONFIDENT, f"got={et.value}")

# 1.4 WRONG_SCENARIO (direction right, but winning scenario is base, not bull)
rec = _record(return_h6=0.0030, winning_scenario="base", decision_confidence=0.55)
et, _ = classify_error(rec)
check("1.4 WRONG_SCENARIO (bull predicted, direction +, but winning=base)",
      et == ErrorType.WRONG_SCENARIO, f"got={et.value}")

# 1.5 UNDERCONFIDENT (correct + scenario_correct + low confidence)
rec = _record(return_h6=0.020, winning_scenario="bull", decision_confidence=0.30)
et, _ = classify_error(rec)
check("1.5 UNDERCONFIDENT (correct bull, conf=0.30 < 0.40)",
      et == ErrorType.UNDERCONFIDENT, f"got={et.value}")

# 1.6 LOW_SIGNAL_NOISE (move below threshold)
rec = _record(return_h6=0.0005, winning_scenario="base", decision_confidence=0.55)
et, _ = classify_error(rec)
check("1.6 LOW_SIGNAL_NOISE (|return_h6|=0.05% < 0.10%)",
      et == ErrorType.LOW_SIGNAL_NOISE, f"got={et.value}")

# 1.6b LOW_SIGNAL_NOISE via signal_strength=no_edge regardless of move
rec = _record(return_h6=0.020, winning_scenario="bull",
              signal_strength="no_edge", decision_confidence=0.30)
et, meta = classify_error(rec)
check("1.6b LOW_SIGNAL_NOISE (no_edge ignored even with material move)",
      et == ErrorType.LOW_SIGNAL_NOISE and meta.get("no_edge_ignored") is True,
      f"got={et.value} meta_no_edge={meta.get('no_edge_ignored')}")

# 1.7 CHAOTIC_MARKET (high conflict + high vol)
rec = _record(return_h6=-0.015, winning_scenario="bear",
              conflict_ratio=0.55, volatility_h6=0.008)
et, _ = classify_error(rec)
check("1.7 CHAOTIC_MARKET (conflict=0.55, vol=0.008, bear wrong)",
      et == ErrorType.CHAOTIC_MARKET, f"got={et.value}")

# 1.8 TIMING_ERROR (h6 right, h1 hard against, MAE large)
rec = _record(return_h6=0.020, return_h1=-0.012, mae=-0.018,
              winning_scenario="bull", decision_confidence=0.60)
et, _ = classify_error(rec)
check("1.8 TIMING_ERROR (h1=-1.2%, h6=+2.0%, MAE=-1.8%)",
      et == ErrorType.TIMING_ERROR, f"got={et.value}")


# ═════════════════════════════════════════════════════════════════════════════
# 2. ROOT CAUSE — each priority must trigger correctly in isolation
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  2. ROOT CAUSE — 6 priority layers")
print("=" * 72)

# 2.1 interaction_misread: fake_breakout while market continued bullish
rec = _record(return_h6=0.015, winning_scenario="bull",
              interaction_type="fake_breakout", bias_aggregated="bullish",
              decision_confidence=0.55)
# NB: predicted=bull, market=bull \u2192 direction correct \u2192 CORRECT,
# so root_cause is empty. Use the case where prediction was bull but
# market was bear and interaction said "fake_breakout" (opposed to bias).
rec = _record(return_h6=-0.015, winning_scenario="bear",
              interaction_type="trend_continuation",  # said "continue bullish"
              bias_aggregated="bullish",
              decision_confidence=0.60,
              contributions=[
                  {"engine": "structure", "bias": "bullish", "confidence": 0.7, "quality": 0.8},
              ])
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
check("2.1 interaction_misread (trend_continuation in falling market)",
      "interaction_misread" in (causes.get("primary_cause"),) + tuple(causes.get("secondary_causes", [])),
      f"causes={[causes.get('primary_cause'), *causes.get('secondary_causes', [])]}")

# 2.2 engine attribution: structure bullish, market bear → structure_misread
rec = _record(return_h6=-0.015, winning_scenario="bear",
              interaction_type="compression",  # neutral, doesn't dominate
              bias_aggregated="bullish",
              decision_confidence=0.55,
              dominant_engine="structure",
              contributions=[
                  {"engine": "structure", "bias": "bullish", "confidence": 0.85, "quality": 0.9},
                  {"engine": "momentum",  "bias": "bullish", "confidence": 0.50, "quality": 0.5},
              ])
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
all_causes = [causes.get("primary_cause"), *causes.get("secondary_causes", [])]
check("2.2 structure_misread + structure_overweight (dominant misfired)",
      "structure_misread" in all_causes and "structure_overweight" in all_causes,
      f"causes={all_causes}")
check("2.2b engine_attribution sorted by weight (structure first)",
      causes["engine_attribution"][0]["engine"] == "structure",
      f"top={causes['engine_attribution'][0] if causes['engine_attribution'] else None}")

# 2.3 conflict_underestimated: conflict=0.45, decision_conf=0.70
rec = _record(return_h6=-0.015, winning_scenario="bear",
              interaction_type="compression",
              bias_aggregated="bullish",
              conflict_ratio=0.45, decision_confidence=0.70,
              contributions=[
                  {"engine": "structure", "bias": "bullish", "confidence": 0.6, "quality": 0.7},
              ])
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
all_causes = [causes.get("primary_cause"), *causes.get("secondary_causes", [])]
check("2.3 conflict_underestimated (conflict=0.45, conf=0.70)",
      "conflict_underestimated" in all_causes,
      f"causes={all_causes}")

# 2.4 temporal_trend_failure: cont=0.7 with bullish bias but bear market
rec = _record(return_h6=-0.015, winning_scenario="bear",
              interaction_type="compression",
              bias_aggregated="bullish",
              continuation_pressure=0.75, reversal_pressure=0.10,
              decision_confidence=0.55,
              contributions=[
                  {"engine": "structure", "bias": "bullish", "confidence": 0.6, "quality": 0.7},
              ])
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
all_causes = [causes.get("primary_cause"), *causes.get("secondary_causes", [])]
check("2.4 temporal_trend_failure (continuation=0.75, market reversed)",
      "temporal_trend_failure" in all_causes,
      f"causes={all_causes}")

# 2.5 false_reversal_signal: rev=0.7 but bull continued
rec = _record(return_h6=0.015, winning_scenario="bull",
              interaction_type="compression",
              bias_aggregated="bullish",
              continuation_pressure=0.10, reversal_pressure=0.75,
              decision_confidence=0.30,
              contributions=[
                  {"engine": "momentum", "bias": "bearish", "confidence": 0.6, "quality": 0.6},
              ])
et, meta = classify_error(rec)
# This is UNDERCONFIDENT (conf=0.30 < 0.40) but root_cause should still surface
# the false_reversal_signal as a structural note.
causes = attribute_root_causes(rec, et, meta)
all_causes = [causes.get("primary_cause"), *causes.get("secondary_causes", [])]
check("2.5 false_reversal_signal (rev=0.75 but bull held)",
      "false_reversal_signal" in all_causes,
      f"et={et.value} causes={all_causes}")

# 2.6 risk_underestimated: risk=low + MAE=-0.7%
rec = _record(return_h6=-0.015, winning_scenario="bear",
              interaction_type="compression",
              bias_aggregated="bullish",
              risk_level="low", mae=-0.007,
              decision_confidence=0.55,
              contributions=[
                  {"engine": "structure", "bias": "bullish", "confidence": 0.6, "quality": 0.7},
              ])
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
all_causes = [causes.get("primary_cause"), *causes.get("secondary_causes", [])]
check("2.6 risk_underestimated (risk=low, MAE=-0.7%)",
      "risk_underestimated" in all_causes,
      f"causes={all_causes}")

# 2.7 scenario_selection_error: predicted bull, market bull, but winning=base
rec = _record(return_h6=0.0025, winning_scenario="base",
              decision_confidence=0.55)
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
all_causes = [causes.get("primary_cause"), *causes.get("secondary_causes", [])]
check("2.7 scenario_selection_error (bull predicted, winning=base)",
      "scenario_selection_error" in all_causes and et == ErrorType.WRONG_SCENARIO,
      f"et={et.value} causes={all_causes}")

# 2.8 CORRECT prediction → empty cause list
rec = _record(return_h6=0.020, winning_scenario="bull", decision_confidence=0.55)
et, meta = classify_error(rec)
causes = attribute_root_causes(rec, et, meta)
check("2.8 CORRECT → primary_cause is None, secondary empty",
      causes["primary_cause"] is None and not causes["secondary_causes"],
      f"primary={causes['primary_cause']} secondary={causes['secondary_causes']}")


# ═════════════════════════════════════════════════════════════════════════════
# 3. METRICS — Tier 1/2/3 aggregation on a synthetic cohort
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  3. METRICS — Tier 1/2/3 on synthetic cohort")
print("=" * 72)

cohort = []
# 5 correct
for i in range(5):
    rec = _record(return_h6=0.020, winning_scenario="bull",
                  decision_confidence=0.55, pred_id=f"c{i}")
    cohort.append(build_debug_record(rec))
# 3 overconfident wrong
for i in range(3):
    rec = _record(return_h6=-0.020, winning_scenario="bear",
                  decision_confidence=0.78,
                  bias_aggregated="bullish",
                  contributions=[{"engine": "structure", "bias": "bullish", "confidence": 0.8, "quality": 0.9}],
                  pred_id=f"oc{i}")
    cohort.append(build_debug_record(rec))
# 2 underconfident correct
for i in range(2):
    rec = _record(return_h6=0.020, winning_scenario="bull",
                  decision_confidence=0.30, pred_id=f"un{i}")
    cohort.append(build_debug_record(rec))
# 2 noise (no_edge_ignored)
for i in range(2):
    rec = _record(return_h6=0.020, winning_scenario="bull",
                  signal_strength="no_edge", pred_id=f"ne{i}")
    cohort.append(build_debug_record(rec))

cohort = [c for c in cohort if c]
m = compute_metrics(cohort)

check("3.1 sample sizes correct",
      m["sample_size"]["total"] == 12 and m["sample_size"]["actionable"] == 10
      and m["sample_size"]["no_edge_ignored"] == 2,
      f"sizes={m['sample_size']}")

# Direction accuracy = 7 correct / 10 actionable = 0.70
check("3.2 direction_accuracy = 0.70",
      abs(m["tier1"]["direction_accuracy"] - 0.70) < 1e-6,
      f"got={m['tier1']['direction_accuracy']}")

# Overconfidence rate = 3/10 = 0.30
check("3.3 overconfidence_rate = 0.30",
      abs(m["tier1"]["overconfidence_rate"] - 0.30) < 1e-6,
      f"got={m['tier1']['overconfidence_rate']}")

# Underconfidence rate = 2/10 = 0.20
check("3.4 underconfidence_rate = 0.20",
      abs(m["tier1"]["underconfidence_rate"] - 0.20) < 1e-6,
      f"got={m['tier1']['underconfidence_rate']}")

# error_distribution must include LOW_SIGNAL_NOISE (the no_edge cohort)
check("3.5 error_distribution includes LOW_SIGNAL_NOISE",
      "low_signal_noise" in m["tier2"]["error_distribution"],
      f"keys={list(m['tier2']['error_distribution'].keys())}")

# Tier 3 keys present
check("3.6 tier3 by_signal_strength populated",
      "moderate" in m["tier3"]["by_signal_strength"],
      f"keys={list(m['tier3']['by_signal_strength'].keys())}")

# Math invariant: shares sum to 1.0 (allow 4-decimal rounding tolerance,
# every share is round(_,4) so the sum can drift by up to len(items) × 0.5e-4)
total_share = sum(v["share"] for v in m["tier2"]["error_distribution"].values())
check("3.7 error_distribution shares sum to 1.0 (within rounding)",
      abs(total_share - 1.0) < 1e-3,
      f"sum={total_share}")


# ═════════════════════════════════════════════════════════════════════════════
# 4. ENDPOINTS — backdate-evaluate-rebuild → /debug/stats has data
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  4. ENDPOINTS — live integration on real Mongo")
print("=" * 72)

BASE = "http://localhost:8001/api/ta-prediction-intelligence"

# 4.1 Schema endpoints respond 200
for ep in ["/debug/preview?limit=5", "/debug/stats"]:
    r = requests.get(BASE + ep, timeout=10)
    check(f"4.0 GET {ep} → 200", r.status_code == 200, f"status={r.status_code}")

# 4.2 Trigger pipeline + backdate to force evaluation
async def setup_evaluated():
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))["trading_os"]
    # 3 fresh predictions
    pids = []
    for sym in ["ETHUSDT", "BTCUSDT", "ETHUSDT"]:
        d = requests.get(BASE + "/live", params={"symbol": sym, "tf": "1H"}, timeout=15).json()
        pid = d.get("prediction_id")
        if pid:
            pids.append(pid)
    # Backdate so worker can evaluate them now
    backdated = int(time.time()) - 10 * 3600
    db.ta_prediction_history.update_many(
        {"prediction_id": {"$in": pids}},
        {"$set": {"candle_close_ts": backdated}},
    )
    # Run worker tick
    from modules.ta_prediction_intelligence.evaluation.ta_prediction_outcome_worker import (
        get_outcome_worker,
    )
    worker = get_outcome_worker()
    await worker._tick()
    return pids, db

pids, db = asyncio.run(setup_evaluated())
evaluated_n = db.ta_prediction_history.count_documents({"evaluation_state": "evaluated"})
check("4.1 backend produced ≥ 1 evaluated prediction", evaluated_n >= 1,
      f"evaluated_count={evaluated_n}")

# 4.3 /debug/rebuild scans evaluated history
r = requests.post(BASE + "/debug/rebuild", params={"limit": 100}, timeout=30)
rebuild_payload = r.json()
check("4.2 POST /debug/rebuild → ok",
      r.status_code == 200 and rebuild_payload.get("ok") is True,
      f"resp={rebuild_payload}")
check("4.3 rebuild analyzed ≥ 1 record",
      rebuild_payload.get("analyzed", 0) >= 1,
      f"analyzed={rebuild_payload.get('analyzed')} skipped={rebuild_payload.get('skipped')}")

# 4.4 /debug/preview returns at least one item
r = requests.get(BASE + "/debug/preview", params={"limit": 10}, timeout=10).json()
check("4.4 GET /debug/preview returns ≥ 1 item",
      r.get("count", 0) >= 1,
      f"count={r.get('count')} items_first={r.get('items', [{}])[0] if r.get('items') else None}")

# 4.5 /debug/stats has populated tiers
r = requests.get(BASE + "/debug/stats", timeout=10).json()
sz = r.get("sample_size", {})
check("4.5 /debug/stats sample_size.total ≥ 1",
      sz.get("total", 0) >= 1, f"sample_size={sz}")
t1 = r.get("tier1", {})
check("4.6 /debug/stats Tier 1 has all 6 metric keys",
      all(k in t1 for k in (
          "direction_accuracy", "scenario_accuracy",
          "high_confidence_accuracy", "low_confidence_accuracy",
          "overconfidence_rate", "underconfidence_rate"
      )),
      f"tier1_keys={sorted(t1.keys())}")
t2 = r.get("tier2", {})
check("4.7 /debug/stats Tier 2 has error_distribution + root_causes_top",
      "error_distribution" in t2 and "root_causes_top" in t2,
      f"tier2_keys={sorted(t2.keys())}")
t3 = r.get("tier3", {})
check("4.8 /debug/stats Tier 3 has by_signal_strength + by_interaction_type",
      "by_signal_strength" in t3 and "by_interaction_type" in t3,
      f"tier3_keys={sorted(t3.keys())}")

# 4.6 /debug/case/{pid} works for a known evaluated pid
known_pid = None
for p in pids:
    rec = db.ta_prediction_history.find_one({"prediction_id": p})
    if rec and rec.get("evaluation_state") == "evaluated":
        known_pid = p
        break
if known_pid:
    r = requests.get(BASE + f"/debug/case/{known_pid}", timeout=10).json()
    check("4.9 /debug/case/{pid} returns persisted record",
          r.get("ok") is True and r.get("source") == "persisted"
          and r.get("record", {}).get("prediction_id") == known_pid,
          f"source={r.get('source')} pid_match={r.get('record', {}).get('prediction_id')}")
else:
    print("        (skipped 4.9 — no evaluated prediction in this run)")


# ═════════════════════════════════════════════════════════════════════════════
# 5. READ-ONLY CONTRACT — Mongo state of "no leaks into protected layers"
# ═════════════════════════════════════════════════════════════════════════════

print()
print("=" * 72)
print("  5. READ-ONLY CONTRACT — protected layers untouched")
print("=" * 72)

from pymongo import MongoClient
db_check = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))["trading_os"]

# Sample evaluated history record — debug must NOT have added new keys
sample = db_check.ta_prediction_history.find_one({"evaluation_state": "evaluated"})
if sample:
    forbidden_keys = {
        "error_type", "root_cause_primary", "root_causes_secondary",
        "engine_attribution", "debug_version", "debug_builder_version",
    }
    leaked = forbidden_keys & set(sample.keys())
    check("5.1 ta_prediction_history records carry NO debug-layer keys",
          len(leaked) == 0, f"leaked_keys={sorted(leaked)}")

# Debug records sit in their own collection
n_debug = db_check["ta_prediction_debug"].estimated_document_count()
check("5.2 ta_prediction_debug collection populated",
      n_debug >= 1, f"count={n_debug}")

# Calibration / temporal_buffer / dataset collections untouched by debug
for col in ("ta_prediction_calibration_stats", "ta_prediction_temporal_buffer",
            "ta_prediction_dataset"):
    sample = db_check[col].find_one({}) or {}
    leaks = {"error_type", "root_cause_primary"} & set(sample.keys())
    check(f"5.3 {col}: no debug keys",
          len(leaks) == 0, f"leaked={leaks}")


# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════

passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 72)
print(f"  RESULT: {passed}/{total} checks passed")
print("=" * 72)
sys.exit(0 if passed == total else 1)
