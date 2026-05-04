#!/usr/bin/env python3
"""
Step 10 POC: Dataset Builder end-to-end.

Covers:
  1. sample_id determinism (same prediction_id → same sample_id)
  2. build_sample skip reasons (bad state / no features / schema mismatch / incomplete outcome)
  3. multi-target y shape + correctness on synthetic evaluated record
  4. sample_weight math (volatility × completeness)
  5. build_dataset dedup + stats aggregation
  6. Mongo persist/read/count (uses live DB trading_os)
  7. HTTP smoke: /dataset/preview, /dataset/stats, /dataset/rebuild
  8. Regression: Step 6/7/8 still intact

Exit 0 on all PASS, 1 otherwise.
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


# ────────────────────────────────────────────────────────────────────────────
# 1. Determinism
# ────────────────────────────────────────────────────────────────────────────

def test_sample_id_determinism():
    print("\n[test] sample_id determinism")
    from modules.ta_prediction_intelligence.learning import build_sample_id
    a = build_sample_id("tap-abc123", "v1")
    b = build_sample_id("tap-abc123", "v1")
    c = build_sample_id("tap-abc123", "v2")
    d = build_sample_id("tap-xyz999", "v1")
    _assert(a == b, "same input → same id")
    _assert(a != c, "different version → different id")
    _assert(a != d, "different prediction_id → different id")
    _assert(len(a) == 64, "sha256 hex")
    print(f"  ✅ id={a[:16]}...")


# ────────────────────────────────────────────────────────────────────────────
# 2. Skip reasons
# ────────────────────────────────────────────────────────────────────────────

def test_skip_reasons():
    print("\n[test] build_sample returns explicit skip reasons")
    from modules.ta_prediction_intelligence.learning import build_sample

    pending = {"prediction_id": "p1", "evaluation_state": "pending"}
    _, skip = build_sample(pending)
    _assert(skip == "not_evaluated", f"expected not_evaluated, got {skip}")

    no_features = {"prediction_id": "p2", "evaluation_state": "evaluated"}
    _, skip = build_sample(no_features)
    _assert(skip == "no_features_v1", f"expected no_features_v1, got {skip}")

    schema_mismatch = {
        "prediction_id": "p3",
        "evaluation_state": "evaluated",
        "features_v1": {"trend_strength": 0.5},
        "feature_schema_hash": "bogus_hash_not_real",
        "outcome": {
            "return_h1": 0.001, "return_h3": 0.002, "return_h6": 0.003,
            "winning_scenario": "bull", "volatility_future_h6": 0.01,
        },
    }
    _, skip = build_sample(schema_mismatch)
    _assert(skip == "schema_mismatch", f"expected schema_mismatch, got {skip}")

    incomplete_outcome = {
        "prediction_id": "p4",
        "evaluation_state": "evaluated",
        "features_v1": {"trend_strength": 0.5},
        "outcome": {"return_h1": 0.001},  # missing r3/r6/winner
    }
    _, skip = build_sample(incomplete_outcome)
    _assert(skip == "incomplete_outcome", f"expected incomplete_outcome, got {skip}")
    print("  ✅ all 4 skip reasons enforced")


# ────────────────────────────────────────────────────────────────────────────
# 3. y shape + correctness
# ────────────────────────────────────────────────────────────────────────────

def _evaluated_record(prediction_id="tap-test-001",
                      symbol="ETHUSDT", tf="1H",
                      r1=0.0012, r3=0.0034, r6=0.0078,
                      mfe=0.0095, mae=-0.0021,
                      vol_future=0.0082,
                      winner="bull",
                      vol_state_code=1,
                      missing_engines=()):
    from modules.ta_prediction_intelligence.learning import (
        FEATURE_SCHEMA_HASH, coerce_to_schema,
    )
    X = coerce_to_schema({"trend_strength": 0.5, "rsi": 0.65, "volatility_state": vol_state_code})
    return {
        "prediction_id": prediction_id,
        "symbol": symbol,
        "timeframe": tf,
        "evaluation_state": "evaluated",
        "features_v1": X,
        "feature_schema_hash": FEATURE_SCHEMA_HASH,
        "feature_hash": "fake_feature_hash_abc",
        "feature_missing_engines": list(missing_engines),
        "feature_states": {"trend": "range", "momentum": "strong", "volatility": "normal"},
        "outcome": {
            "return_h1": r1, "return_h3": r3, "return_h6": r6,
            "max_favourable_move_pct": mfe, "max_adverse_move_pct": mae,
            "volatility_future_h6": vol_future,
            "winning_scenario": winner,
        },
    }


def test_y_shape_and_direction():
    print("\n[test] y contract + direction from sign of return")
    from modules.ta_prediction_intelligence.learning import build_sample
    rec = _evaluated_record(r1=-0.005, r3=0.01, r6=0.02)
    s, skip = build_sample(rec)
    _assert(skip is None, f"no skip: {skip}")
    y = s["y"]
    for k in ("direction_h1", "direction_h3", "direction_h6",
              "return_h1", "return_h3", "return_h6",
              "max_favourable_h6", "max_adverse_h6",
              "volatility_future_h6", "winning_scenario"):
        _assert(k in y, f"missing y key {k}")
    _assert(y["direction_h1"] == 0, "h1 negative → 0")
    _assert(y["direction_h3"] == 1, "h3 positive → 1")
    _assert(y["direction_h6"] == 1, "h6 positive → 1")
    _assert(y["winning_scenario"] == "bull", "winner pass-through")
    _assert(s["meta"]["volatility_proxied"] is False, "real volatility provided")
    print("  ✅ y shape + directions correct")


def test_y_volatility_proxied_when_missing():
    print("\n[test] y.volatility_future_h6 proxy for legacy records")
    from modules.ta_prediction_intelligence.learning import build_sample
    rec = _evaluated_record(vol_future=None, mfe=0.012, mae=-0.008)
    rec["outcome"].pop("volatility_future_h6", None)
    s, skip = build_sample(rec)
    _assert(skip is None, f"no skip: {skip}")
    _assert(s["meta"]["volatility_proxied"] is True, "proxy flag set")
    # proxy = mfe - mae
    _assert(abs(s["y"]["volatility_future_h6"] - 0.02) < 1e-6, f"proxy = {s['y']['volatility_future_h6']}")
    print("  ✅ proxy correctly used and flagged")


# ────────────────────────────────────────────────────────────────────────────
# 4. sample_weight
# ────────────────────────────────────────────────────────────────────────────

def test_sample_weight():
    print("\n[test] sample_weight = volatility × completeness")
    from modules.ta_prediction_intelligence.learning import compute_sample_weight
    # normal vol, no missing → 1.0 × 1.0 = 1.0
    w = compute_sample_weight({"volatility_state": 1}, [])
    _assert(abs(w - 1.0) < 1e-4, f"normal: {w}")
    # chaos + 2 missing → 0.7 × 0.8 = 0.56
    w = compute_sample_weight({"volatility_state": 3}, ["level_zone", "pattern"])
    _assert(abs(w - 0.56) < 1e-4, f"chaos×2missing: {w}")
    # all engines missing → floor 0.4
    w = compute_sample_weight({"volatility_state": 1},
                              ["a", "b", "c", "d", "e", "f", "g", "h"])
    _assert(abs(w - 0.4) < 1e-4, f"floor: {w}")
    print("  ✅ volatility × completeness with floor 0.4")


# ────────────────────────────────────────────────────────────────────────────
# 5. build_dataset dedup + stats
# ────────────────────────────────────────────────────────────────────────────

def test_build_dataset_dedup_and_stats():
    print("\n[test] build_dataset dedup + compute_stats")
    from modules.ta_prediction_intelligence.learning import (
        build_dataset, compute_dataset_stats,
    )
    r1 = _evaluated_record("tap-x1", winner="bull", r6=0.01)
    r2 = _evaluated_record("tap-x2", winner="bear", r6=-0.02)
    r3 = _evaluated_record("tap-x3", winner="base", r6=0.001)
    r1_dup = _evaluated_record("tap-x1", winner="bull", r6=0.01)  # same id
    r_pending = _evaluated_record("tap-x4")
    r_pending["evaluation_state"] = "pending"
    samples, skips = build_dataset([r1, r2, r3, r1_dup, r_pending])
    _assert(len(samples) == 3, f"3 unique samples, got {len(samples)}")
    _assert(skips.get("duplicate_sample_id") == 1, f"1 dup, got {skips}")
    _assert(skips.get("not_evaluated") == 1, f"1 pending skip, got {skips}")
    stats = compute_dataset_stats(samples)
    _assert(stats["total"] == 3, "total=3")
    _assert(stats["winning_scenarios"]["bull"] == 1, "bull=1")
    _assert(stats["winning_scenarios"]["bear"] == 1, "bear=1")
    _assert(stats["winning_scenarios"]["base"] == 1, "base=1")
    _assert(stats["by_pair"].get("ETHUSDT_1H") == 3, f"pair count: {stats['by_pair']}")
    print(f"  ✅ 3 unique, 1 dup, 1 pending skipped; stats balanced")


# ────────────────────────────────────────────────────────────────────────────
# 6. Mongo persist/read/count
# ────────────────────────────────────────────────────────────────────────────

def test_persist_and_read():
    print("\n[test] Mongo persist_samples + read_samples + count")
    import os
    from modules.ta_prediction_intelligence.learning import (
        build_dataset, persist_dataset_samples,
        read_dataset_samples, count_dataset_samples,
    )
    from pymongo import MongoClient
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client["trading_os"]

    # Clean test prefix to avoid collision with real data
    db["ta_prediction_dataset"].delete_many({"prediction_id": {"$regex": "^poc-step10-"}})
    recs = [_evaluated_record(f"poc-step10-{i}", r6=(i - 2) * 0.005, winner=("bull" if i > 2 else "bear"))
            for i in range(5)]
    samples, _ = build_dataset(recs)
    _assert(len(samples) == 5, "5 built")
    write = persist_dataset_samples(db, samples)
    _assert(write["written"] == 5, f"5 written: {write}")
    # idempotent upsert
    write2 = persist_dataset_samples(db, samples)
    _assert(write2["written"] == 5, "upsert again OK")
    total = count_dataset_samples(db)
    _assert(total >= 5, f"count>=5, got {total}")
    # read back
    back = read_dataset_samples(db, symbol="ETHUSDT", tf="1H", limit=10)
    ours = [s for s in back if str(s.get("prediction_id")).startswith("poc-step10-")]
    _assert(len(ours) == 5, f"read back 5, got {len(ours)}")
    # cleanup
    db["ta_prediction_dataset"].delete_many({"prediction_id": {"$regex": "^poc-step10-"}})
    print("  ✅ persist/read/count work end-to-end")


# ────────────────────────────────────────────────────────────────────────────
# 7. HTTP smoke
# ────────────────────────────────────────────────────────────────────────────

def _http_get(path):
    with urllib.request.urlopen(BACKEND + path, timeout=20) as r:
        return r.status, json.loads(r.read().decode())


def _http_post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(BACKEND + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read().decode())


def test_http_stats():
    print("\n[test] HTTP /dataset/stats")
    st, body = _http_get("/api/ta-prediction-intelligence/dataset/stats")
    _assert(st == 200, "200")
    _assert(body["ok"] is True, "ok")
    _assert(body["dataset_version"] == "v1", "v1")
    _assert(body["dataset_builder_version"] == "1.0.0", "builder v")
    _assert(body["min_samples_for_training"] == 500, "training gate")
    _assert("stats" in body, "stats key")
    _assert(len(body["feature_schema_hash"]) == 64, "schema hash")
    print(f"  ✅ records_scanned={body['records_scanned']}, samples_built={body['samples_built']}")


def test_http_preview():
    print("\n[test] HTTP /dataset/preview")
    st, body = _http_get("/api/ta-prediction-intelligence/dataset/preview?limit=5")
    _assert(st == 200, "200")
    _assert(body["ok"] is True, "ok")
    _assert(body["source"] == "history", "source default")
    _assert("samples" in body, "samples key")
    _assert("skip_counts" in body, "skip counts")
    print(f"  ✅ records={body['records_scanned']}, built={body['samples_built']}, preview={body['samples_previewed']}")


def test_http_rebuild():
    print("\n[test] HTTP POST /dataset/rebuild")
    st, body = _http_post("/api/ta-prediction-intelligence/dataset/rebuild")
    _assert(st == 200, "200")
    _assert(body["ok"] is True, "ok")
    _assert("persistence" in body, "persistence counts")
    print(f"  ✅ records_scanned={body['records_scanned']}, persistence={body['persistence']}")


def test_regression_live_still_works():
    print("\n[test] regression: /live still carries Step 6/7/8 fields")
    st, body = _http_get("/api/ta-prediction-intelligence/live?symbol=ETHUSDT&tf=1H")
    _assert(st == 200, "200")
    _assert("scenarios_adjustment" in body, "Step 6")
    _assert("scenarios_calibration" in body, "Step 7")
    _assert("prediction_id" in body, "Step 7 pid")
    _assert("_features_debug" in body, "Step 8 features meta")
    fd = body["_features_debug"]
    _assert(fd.get("feature_count") == 82, "82 features")
    print("  ✅ all previous steps intact")


TESTS = [
    test_sample_id_determinism,
    test_skip_reasons,
    test_y_shape_and_direction,
    test_y_volatility_proxied_when_missing,
    test_sample_weight,
    test_build_dataset_dedup_and_stats,
    test_persist_and_read,
    test_http_stats,
    test_http_preview,
    test_http_rebuild,
    test_regression_live_still_works,
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
