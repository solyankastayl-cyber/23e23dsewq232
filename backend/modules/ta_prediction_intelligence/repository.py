"""
Mongo persistence for ta_prediction_intelligence.

Step 7 additions (history calibration / ML-ready layer):
  * TAPredictionRecord schema with full audit trail (engines + interaction +
    scenarios_original + scenarios_interaction_adjusted + scenarios_calibrated).
  * record_prediction / get_pending_predictions / update_prediction_outcome /
    get_recent_predictions helpers.
  * Mongo indexes: (symbol, tf, candle_close_ts), evaluation_state, unique prediction_id.
  * Back-compat: legacy save() / recent() retained for external callers.

Rules (locked):
  - No coupling to Meta, Trading, combined_analysis, shadow_logger.
  - Never raises on DB errors during non-critical writes.
  - Deterministic: caller provides prediction_id (uuid4 at adapter layer).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

COL_CONTEXTS = "ta_prediction_contexts"          # legacy (back-compat)
COL_PREDICTIONS = "ta_prediction_history"         # Step 7: rich audit records
COL_CALIBRATION = "ta_prediction_calibration_stats"

_STATE_PENDING = "pending"
_STATE_EVALUATED = "evaluated"
_STATE_EXPIRED = "expired"
_STATE_ERROR = "error"


def _utcnow():
    return datetime.now(timezone.utc)


def _json_safe(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mongo _id/datetime to JSON-safe types. Shallow copy."""
    if not doc:
        return doc
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for k, v in list(out.items()):
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


class TAPredictionRepository:
    """
    Handles BOTH:
      * legacy ta_prediction_contexts writes (save / recent).
      * Step 7 prediction history (record_prediction / outcome lifecycle).
    """

    def __init__(self, db):
        self.db = db
        self.col = db[COL_CONTEXTS]
        self.col_pred = db[COL_PREDICTIONS]
        self.col_calib = db[COL_CALIBRATION]
        self._ensure_indexes()

    # ------------------------------------------------------------------
    # Index hygiene. Called on construction; idempotent.
    # ------------------------------------------------------------------
    def _ensure_indexes(self) -> None:
        try:
            self.col_pred.create_index(
                [("prediction_id", 1)], unique=True, sparse=True, name="uniq_prediction_id"
            )
            self.col_pred.create_index(
                [("symbol", 1), ("timeframe", 1), ("candle_close_ts", -1)],
                name="by_symbol_tf_ts",
            )
            self.col_pred.create_index(
                [("evaluation_state", 1), ("candle_close_ts", 1)],
                name="by_state_ts",
            )
            self.col_calib.create_index(
                [("group_by", 1), ("bucket_key", 1)],
                unique=True,
                name="uniq_bucket",
            )
        except Exception:
            # index creation must never break startup
            pass

    # ================================================================
    # LEGACY API (kept for back-compat)
    # ================================================================
    def save(self, context: Dict[str, Any]) -> str:
        doc = {
            **context,
            "created_at": _utcnow(),
        }
        result = self.col.insert_one(doc)
        return str(result.inserted_id)

    def recent(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if symbol:
            q["symbol"] = symbol
        if timeframe:
            q["timeframe"] = timeframe
        rows = list(self.col.find(q).sort("created_at", -1).limit(limit))
        return [_json_safe(r) for r in rows]

    # ================================================================
    # STEP 7 API (prediction history + outcome lifecycle)
    # ================================================================
    def record_prediction(
        self,
        *,
        symbol: str,
        timeframe: str,
        entry_price: float,
        candle_close_ts: Optional[int],
        bias: Optional[str],
        confidence: Optional[float],
        conflict_ratio: Optional[float],
        dominant_engine: Optional[str],
        contributions: List[Dict[str, Any]],
        interaction: Optional[Dict[str, Any]],
        scenarios_original: List[Dict[str, Any]],
        scenarios_interaction_adjusted: List[Dict[str, Any]],
        scenarios_calibrated: Optional[List[Dict[str, Any]]] = None,
        scenarios_adjustment_meta: Optional[Dict[str, Any]] = None,
        scenarios_calibration_meta: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
        source: str = "live",
        prediction_id: Optional[str] = None,
        features_bundle: Optional[Dict[str, Any]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
        decision_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Persist a prediction with full audit trail.

        Returns prediction_id on success, None on failure (never raises).
        Dedup strategy: unique prediction_id (sparse). Caller decides whether
        to produce a per-call uuid (no dedup) or a (symbol, tf, candle_close_ts)
        stable hash (dedup per bar).
        """
        pid = prediction_id or f"tap-{uuid.uuid4().hex[:16]}"
        doc: Dict[str, Any] = {
            "prediction_id": pid,
            "symbol": (symbol or "").upper(),
            "timeframe": (timeframe or "").upper(),
            "entry_price": float(entry_price) if entry_price is not None else None,
            "candle_close_ts": int(candle_close_ts) if candle_close_ts else None,
            "bias": bias,
            "confidence": float(confidence) if confidence is not None else None,
            "conflict_ratio": float(conflict_ratio) if conflict_ratio is not None else None,
            "dominant_engine": dominant_engine,
            "contributions": contributions or [],
            "interaction": interaction or None,
            "scenarios_original": scenarios_original or [],
            "scenarios_interaction_adjusted": scenarios_interaction_adjusted or [],
            "scenarios_calibrated": scenarios_calibrated or None,
            "scenarios_adjustment_meta": scenarios_adjustment_meta or None,
            "scenarios_calibration_meta": scenarios_calibration_meta or None,
            "meta": meta or {},
            "source": source,
            "evaluation_state": _STATE_PENDING,
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }
        # Step 8: attach feature bundle (v1) if present. Stored alongside
        # prediction so the dataset builder can retrieve X(t) at leisure.
        if features_bundle:
            doc["features_v1"] = features_bundle.get("features")
            doc["feature_version"] = features_bundle.get("feature_version")
            doc["feature_schema_hash"] = features_bundle.get("feature_schema_hash")
            doc["feature_hash"] = features_bundle.get("feature_hash")
            doc["feature_builder_version"] = features_bundle.get("builder_version")
            doc["feature_states"] = features_bundle.get("states")
            doc["feature_ts"] = features_bundle.get("ts")
            doc["feature_missing_engines"] = features_bundle.get("missing_engines")
            doc["feature_latency_ms"] = features_bundle.get("latency_ms")
        if temporal_context:
            doc["temporal_intelligence"] = temporal_context
        if decision_context:
            doc["decision_intelligence"] = decision_context
        try:
            self.col_pred.insert_one(doc)
            return pid
        except Exception:
            # duplicate prediction_id (re-log) or other DB issue — no-op
            return None

    def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        try:
            row = self.col_pred.find_one({"prediction_id": prediction_id})
            return _json_safe(row) if row else None
        except Exception:
            return None

    def get_pending_predictions(self, limit: int = 200) -> List[Dict[str, Any]]:
        try:
            cur = (
                self.col_pred.find({"evaluation_state": _STATE_PENDING})
                .sort("candle_close_ts", 1)
                .limit(limit)
            )
            return [_json_safe(r) for r in cur]
        except Exception:
            return []

    def update_prediction_outcome(
        self,
        prediction_id: str,
        *,
        outcome: Dict[str, Any],
        state: str = _STATE_EVALUATED,
    ) -> bool:
        try:
            res = self.col_pred.update_one(
                {"prediction_id": prediction_id},
                {
                    "$set": {
                        "outcome": outcome,
                        "evaluation_state": state,
                        "evaluated_at": _utcnow(),
                        "updated_at": _utcnow(),
                    }
                },
            )
            return res.matched_count > 0
        except Exception:
            return False

    def mark_prediction_error(self, prediction_id: str, error: str) -> bool:
        try:
            self.col_pred.update_one(
                {"prediction_id": prediction_id},
                {
                    "$set": {
                        "evaluation_state": _STATE_ERROR,
                        "error": str(error)[:500],
                        "updated_at": _utcnow(),
                    }
                },
            )
            return True
        except Exception:
            return False

    def get_recent_predictions(
        self,
        *,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if symbol:
            q["symbol"] = symbol.upper()
        if timeframe:
            q["timeframe"] = timeframe.upper()
        if state:
            q["evaluation_state"] = state
        try:
            cur = self.col_pred.find(q).sort("created_at", -1).limit(limit)
            return [_json_safe(r) for r in cur]
        except Exception:
            return []

    def get_evaluated_predictions(
        self,
        *,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {"evaluation_state": _STATE_EVALUATED}
        if symbol:
            q["symbol"] = symbol.upper()
        if timeframe:
            q["timeframe"] = timeframe.upper()
        try:
            cur = self.col_pred.find(q).sort("evaluated_at", -1).limit(limit)
            return [_json_safe(r) for r in cur]
        except Exception:
            return []

    def count_by_state(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for st in (_STATE_PENDING, _STATE_EVALUATED, _STATE_EXPIRED, _STATE_ERROR):
            try:
                counts[st] = int(self.col_pred.count_documents({"evaluation_state": st}))
            except Exception:
                counts[st] = 0
        return counts

    # ================================================================
    # Calibration stats persistence (rebuild-only; no hot mutation)
    # ================================================================
    def write_calibration_stats(self, group_by: str, buckets: List[Dict[str, Any]]) -> int:
        """
        Replace stats for a given group_by dimension. Idempotent per-bucket.
        Returns number of upserted buckets.
        """
        n = 0
        now = _utcnow()
        for b in buckets:
            key = b.get("bucket_key")
            if key is None:
                continue
            try:
                self.col_calib.update_one(
                    {"group_by": group_by, "bucket_key": key},
                    {"$set": {**b, "group_by": group_by, "updated_at": now}},
                    upsert=True,
                )
                n += 1
            except Exception:
                continue
        return n

    def get_calibration_stats(
        self,
        *,
        group_by: Optional[str] = None,
        bucket_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if group_by:
            q["group_by"] = group_by
        if bucket_key is not None:
            q["bucket_key"] = bucket_key
        try:
            cur = self.col_calib.find(q)
            return [_json_safe(r) for r in cur]
        except Exception:
            return []


# Convenience singleton ------------------------------------------------------
_repo_singleton: Optional[TAPredictionRepository] = None


def get_repository() -> Optional[TAPredictionRepository]:
    """Return a process-wide repository backed by core.database.get_database.

    Returns None on any failure (module must self-disable gracefully).
    """
    global _repo_singleton
    if _repo_singleton is not None:
        return _repo_singleton
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return None
        _repo_singleton = TAPredictionRepository(db)
        return _repo_singleton
    except Exception:
        return None
