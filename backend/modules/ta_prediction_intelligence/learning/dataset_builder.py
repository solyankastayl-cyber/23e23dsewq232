"""
Dataset Builder (Step 10) — pure read-only transformer.

Consumes evaluated predictions (Step 7 outcome worker) that have a
features_v1 attached (Step 8) and produces ML-ready samples:

    {
      "sample_id": <sha256 hex>,
      "prediction_id": <str>,
      "symbol": <str>,
      "tf": <str>,
      "feature_version": "v1",
      "feature_hash": <sha256 hex>,
      "feature_schema_hash": <sha256 hex>,
      "X": { 82 canonical features },
      "y": {
        "direction_h1": 0|1,
        "direction_h3": 0|1,
        "direction_h6": 0|1,
        "return_h1":  float,
        "return_h3":  float,
        "return_h6":  float,
        "max_favourable_h6": float,
        "max_adverse_h6":    float,
        "volatility_future_h6": float,
        "winning_scenario":  "bull"|"base"|"bear"
      },
      "sample_weight": float,
      "meta": {
        "feature_states": {...},
        "feature_missing_engines": [...],
        "volatility_proxied": bool,   # True when volatility_future_h6 is derived from range (legacy records)
        "created_at": <iso>,
        "evaluated_at": <iso>,
      }
    }

Hard rules (locked):
  * only records with evaluation_state == "evaluated" are considered
  * missing features_v1 -> skip (reason="no_features_v1")
  * missing outcome fields (returns or winner) -> skip ("incomplete_outcome")
  * schema_hash mismatch -> skip ("schema_mismatch")
  * deterministic sample_id = sha256(prediction_id + feature_version)
  * NO synthetic y, NO random, NO mutation of source records
  * NO model calls, NO training
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .feature_hash import sha256_hex
from .feature_schema import FEATURE_SCHEMA_HASH, FEATURE_VERSION, coerce_to_schema

SKIP_NO_FEATURES = "no_features_v1"
SKIP_INCOMPLETE_OUTCOME = "incomplete_outcome"
SKIP_SCHEMA_MISMATCH = "schema_mismatch"
SKIP_BAD_STATE = "not_evaluated"
SKIP_MALFORMED = "malformed"

DATASET_VERSION = "v1"
DATASET_BUILDER_VERSION = "1.0.0"


def build_sample_id(prediction_id: str, feature_version: str) -> str:
    """Deterministic, unique per (prediction_id, feature_version).

    Using a stable prefix guards against accidental collisions with other
    sha256 usages in the codebase.
    """
    return sha256_hex(f"ta_dataset_sample|{feature_version}|{prediction_id}")


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except (TypeError, ValueError):
        return None


def _direction(ret: Optional[float]) -> Optional[int]:
    if ret is None:
        return None
    return 1 if ret > 0 else 0


def _volatility_weight(volatility_state_code: Any) -> float:
    """Down-weight noisy regimes.

    state codes (from feature_schema):
      0=compression -> 0.9
      1=normal      -> 1.0
      2=expansion   -> 1.0
      3=chaos       -> 0.7
    """
    try:
        c = int(volatility_state_code)
    except (TypeError, ValueError):
        return 1.0
    return {0: 0.9, 1: 1.0, 2: 1.0, 3: 0.7}.get(c, 1.0)


def _completeness_weight(missing_engines: Any) -> float:
    try:
        n = len(missing_engines or [])
    except TypeError:
        return 1.0
    w = 1.0 - 0.10 * n
    if w < 0.40:
        w = 0.40
    if w > 1.00:
        w = 1.00
    return w


def compute_sample_weight(
    features_v1: Dict[str, Any],
    missing_engines: Any,
) -> float:
    vw = _volatility_weight((features_v1 or {}).get("volatility_state"))
    cw = _completeness_weight(missing_engines)
    return round(vw * cw, 4)


def _extract_y(outcome: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Return (y_dict, volatility_proxied_flag).

    Returns (None, _) if outcome is incomplete (missing returns or winner).
    When outcome lacks volatility_future_h6 (legacy records), substitute the
    peak-to-trough range from max_favourable/max_adverse and set
    volatility_proxied=True. NOT synthetic — it is an honest coarser volatility
    measure directly from evaluated market data.
    """
    if not outcome:
        return None, False
    r1 = _safe_float(outcome.get("return_h1"))
    r3 = _safe_float(outcome.get("return_h3"))
    r6 = _safe_float(outcome.get("return_h6"))
    mfe = _safe_float(outcome.get("max_favourable_move_pct"))
    mae = _safe_float(outcome.get("max_adverse_move_pct"))
    winner = (outcome.get("winning_scenario") or "").lower()
    if r1 is None or r3 is None or r6 is None or winner not in ("bull", "base", "bear"):
        return None, False

    vol = _safe_float(outcome.get("volatility_future_h6"))
    proxied = False
    if vol is None:
        if mfe is not None and mae is not None:
            vol = round(max(0.0, float(mfe) - float(mae)), 8)
            proxied = True
        else:
            return None, False

    y = {
        "direction_h1": _direction(r1),
        "direction_h3": _direction(r3),
        "direction_h6": _direction(r6),
        "return_h1": round(r1, 8),
        "return_h3": round(r3, 8),
        "return_h6": round(r6, 8),
        "max_favourable_h6": round(mfe, 8) if mfe is not None else 0.0,
        "max_adverse_h6": round(mae, 8) if mae is not None else 0.0,
        "volatility_future_h6": round(vol, 8),
        "winning_scenario": winner,
    }
    return y, proxied


def build_sample(
    record: Dict[str, Any],
    *,
    expected_schema_hash: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Build one sample from a prediction record.

    Returns (sample_dict, None) on success, or (None, skip_reason) on skip.
    """
    if not isinstance(record, dict):
        return None, SKIP_MALFORMED
    if str(record.get("evaluation_state") or "") != "evaluated":
        return None, SKIP_BAD_STATE

    prediction_id = record.get("prediction_id")
    if not prediction_id:
        return None, SKIP_MALFORMED

    features_v1 = record.get("features_v1")
    if not isinstance(features_v1, dict) or not features_v1:
        return None, SKIP_NO_FEATURES

    # Schema hash gate.
    expected = expected_schema_hash or FEATURE_SCHEMA_HASH
    record_schema = record.get("feature_schema_hash")
    if record_schema and record_schema != expected:
        return None, SKIP_SCHEMA_MISMATCH

    # Outcome gate.
    y, vol_proxied = _extract_y(record.get("outcome") or {})
    if y is None:
        return None, SKIP_INCOMPLETE_OUTCOME

    # Coerce features to schema so downstream trainers see a stable vector.
    # This is a NO-OP for features already produced by the v1 builder, but
    # defensively protects against schema drift.
    X = coerce_to_schema(features_v1)

    sample_id = build_sample_id(prediction_id, FEATURE_VERSION)

    sample = {
        "sample_id": sample_id,
        "prediction_id": prediction_id,
        "symbol": (record.get("symbol") or "").upper(),
        "tf": (record.get("timeframe") or "").upper(),
        "feature_version": FEATURE_VERSION,
        "feature_hash": record.get("feature_hash"),
        "feature_schema_hash": record_schema or expected,
        "X": X,
        "y": y,
        "sample_weight": compute_sample_weight(
            features_v1, record.get("feature_missing_engines")
        ),
        "dataset_version": DATASET_VERSION,
        "dataset_builder_version": DATASET_BUILDER_VERSION,
        "meta": {
            "feature_states": record.get("feature_states"),
            "feature_missing_engines": record.get("feature_missing_engines") or [],
            "volatility_proxied": bool(vol_proxied),
            "created_at": record.get("created_at"),
            "evaluated_at": record.get("evaluated_at"),
        },
    }
    return sample, None


def build_dataset(
    records: Iterable[Dict[str, Any]],
    *,
    expected_schema_hash: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Apply build_sample over an iterable. Returns (samples, skip_counts).

    Duplicates by sample_id are de-duped (first occurrence wins).
    """
    samples: List[Dict[str, Any]] = []
    seen: set = set()
    skip_counts: Dict[str, int] = {}

    for r in records or []:
        s, skip = build_sample(r, expected_schema_hash=expected_schema_hash)
        if skip is not None:
            skip_counts[skip] = skip_counts.get(skip, 0) + 1
            continue
        if s["sample_id"] in seen:
            skip_counts["duplicate_sample_id"] = skip_counts.get("duplicate_sample_id", 0) + 1
            continue
        seen.add(s["sample_id"])
        samples.append(s)
    return samples, skip_counts


def compute_stats(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate dataset stats for /dataset/stats endpoint."""
    if not samples:
        return {
            "total": 0,
            "by_pair": {},
            "winning_scenarios": {"bull": 0, "base": 0, "bear": 0},
            "direction_balance": {},
            "avg_return_h6": None,
            "avg_abs_return_h6": None,
            "avg_sample_weight": None,
            "volatility_proxied_share": None,
        }
    by_pair: Dict[str, int] = {}
    winners = {"bull": 0, "base": 0, "bear": 0}
    dirs = {"h1": [0, 0], "h3": [0, 0], "h6": [0, 0]}
    rets = []
    abs_rets = []
    weights = []
    vol_proxied = 0
    for s in samples:
        key = f"{s.get('symbol')}_{s.get('tf')}"
        by_pair[key] = by_pair.get(key, 0) + 1
        w = (s.get("y") or {}).get("winning_scenario")
        if w in winners:
            winners[w] += 1
        for horizon in ("h1", "h3", "h6"):
            d = (s.get("y") or {}).get(f"direction_{horizon}")
            if d in (0, 1):
                dirs[horizon][int(d)] += 1
        r6 = (s.get("y") or {}).get("return_h6")
        if isinstance(r6, (int, float)):
            rets.append(float(r6))
            abs_rets.append(abs(float(r6)))
        weights.append(float(s.get("sample_weight") or 1.0))
        if ((s.get("meta") or {}).get("volatility_proxied")):
            vol_proxied += 1
    n = len(samples)
    return {
        "total": n,
        "by_pair": by_pair,
        "winning_scenarios": winners,
        "direction_balance": {
            h: {"down": dirs[h][0], "up": dirs[h][1]} for h in dirs
        },
        "avg_return_h6": round(sum(rets) / len(rets), 8) if rets else None,
        "avg_abs_return_h6": round(sum(abs_rets) / len(abs_rets), 8) if abs_rets else None,
        "avg_sample_weight": round(sum(weights) / len(weights), 4) if weights else None,
        "volatility_proxied_share": round(vol_proxied / n, 4) if n else None,
    }


# ────────────────────────────────────────────────────────────────────────────
# Storage helpers (optional). Dataset rebuild persists samples for
# convenience, deduped by unique sample_id. The collection is never read by
# the live pipeline — it is there for the trainer (Step 11+) when we get to it.
# ────────────────────────────────────────────────────────────────────────────

COL_DATASET = "ta_prediction_dataset"


def _ensure_dataset_indexes(db) -> None:
    try:
        col = db[COL_DATASET]
        col.create_index([("sample_id", 1)], unique=True, name="uniq_sample_id")
        col.create_index(
            [("symbol", 1), ("tf", 1), ("dataset_version", 1)],
            name="by_pair_version",
        )
    except Exception:
        pass


def persist_samples(db, samples: List[Dict[str, Any]]) -> Dict[str, int]:
    """Upsert samples by sample_id. Returns counts."""
    if db is None or not samples:
        return {"written": 0, "failed": 0, "skipped": 0}
    _ensure_dataset_indexes(db)
    col = db[COL_DATASET]
    written = 0
    failed = 0
    now = datetime.now(timezone.utc)
    for s in samples:
        try:
            col.update_one(
                {"sample_id": s["sample_id"]},
                {"$set": {**s, "persisted_at": now}},
                upsert=True,
            )
            written += 1
        except Exception:
            failed += 1
    return {"written": written, "failed": failed, "skipped": 0}


def read_samples_from_mongo(
    db,
    *,
    symbol: Optional[str] = None,
    tf: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    if db is None:
        return []
    q: Dict[str, Any] = {"dataset_version": DATASET_VERSION}
    if symbol:
        q["symbol"] = symbol.upper()
    if tf:
        q["tf"] = tf.upper()
    try:
        cur = db[COL_DATASET].find(q, {"_id": 0}).sort("persisted_at", -1).limit(limit)
        return list(cur)
    except Exception:
        return []


def count_samples_in_mongo(db) -> int:
    if db is None:
        return 0
    try:
        return int(db[COL_DATASET].count_documents({"dataset_version": DATASET_VERSION}))
    except Exception:
        return 0
