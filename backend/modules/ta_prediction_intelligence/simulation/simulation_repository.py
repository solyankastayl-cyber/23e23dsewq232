"""
Simulation Repository — owns isolated `_sim` Mongo collections.

Mirrors the shape of TAPredictionRepository / DebugRepository but writes
to:
    ta_prediction_history_sim
    ta_prediction_debug_sim

Guarantees:
  * NEVER reads from / writes to live collections.
  * Idempotent index creation.
  * upsert by prediction_id (re-running a step is safe).
  * `clear_for(symbol, tf)` removes ONLY sim records for that pair; never
    touches live data even when called with bogus arguments.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .types import (
    SIM_DEBUG_COLLECTION,
    SIM_HISTORY_COLLECTION,
    SimulationSource,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _json_safe(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for k, v in list(out.items()):
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


def _default_db():
    try:
        from core.database import get_database
        return get_database()
    except Exception:
        try:
            from pymongo import MongoClient
            url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            return MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        except Exception:
            return None


class SimulationRepository:
    """All sim writes / reads. Live collections are not addressable here."""

    def __init__(self, db: Any = None):
        self.db = db if db is not None else _default_db()
        self._ensure_indexes()

    # ── Indexes ──────────────────────────────────────────────────────────
    def _ensure_indexes(self) -> None:
        if self.db is None:
            return
        try:
            hcol = self.db[SIM_HISTORY_COLLECTION]
            hcol.create_index(
                [("prediction_id", 1)],
                unique=True,
                sparse=True,
                name="uniq_sim_prediction_id",
            )
            hcol.create_index(
                [("symbol", 1), ("timeframe", 1), ("candle_close_ts", -1)],
                name="by_symbol_tf_ts_sim",
            )
            hcol.create_index(
                [("evaluation_state", 1), ("candle_close_ts", 1)],
                name="by_state_ts_sim",
            )
        except Exception:
            pass
        try:
            dcol = self.db[SIM_DEBUG_COLLECTION]
            dcol.create_index(
                "prediction_id", name="uniq_sim_debug_prediction_id", unique=True
            )
            dcol.create_index(
                [("symbol", 1), ("tf", 1), ("error_type", 1)],
                name="by_symbol_tf_error_sim",
            )
            dcol.create_index(
                [("analyzed_at", -1)], name="by_analyzed_at_desc_sim"
            )
        except Exception:
            pass

    # ── Names (for QA / debugging) ───────────────────────────────────────
    @property
    def history_collection_name(self) -> str:
        return SIM_HISTORY_COLLECTION

    @property
    def debug_collection_name(self) -> str:
        return SIM_DEBUG_COLLECTION

    # ── Counts ───────────────────────────────────────────────────────────
    def count_history(self, **filt) -> int:
        if self.db is None:
            return 0
        try:
            return int(self.db[SIM_HISTORY_COLLECTION].count_documents(filt or {}))
        except Exception:
            return 0

    def count_debug(self, **filt) -> int:
        if self.db is None:
            return 0
        try:
            return int(self.db[SIM_DEBUG_COLLECTION].count_documents(filt or {}))
        except Exception:
            return 0

    def count_history_by_pair(self, symbol: str, tf: str) -> int:
        return self.count_history(symbol=symbol.upper(), timeframe=tf.upper())

    # ── Writes ───────────────────────────────────────────────────────────
    def write_prediction(
        self,
        *,
        symbol: str,
        timeframe: str,
        entry_price: Optional[float],
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
        prediction_id: Optional[str] = None,
        features_bundle: Optional[Dict[str, Any]] = None,
        temporal_context: Optional[Dict[str, Any]] = None,
        decision_context: Optional[Dict[str, Any]] = None,
        as_of_candle_index: Optional[int] = None,
        outcome: Optional[Dict[str, Any]] = None,
        evaluation_state: str = "pending",
    ) -> Optional[str]:
        if self.db is None:
            return None
        pid = prediction_id or f"sim-{uuid.uuid4().hex[:16]}"
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
            "source": SimulationSource.SIMULATION.value,
            "as_of_candle_index": as_of_candle_index,
            "evaluation_state": evaluation_state,
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }
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
        if outcome:
            doc["outcome"] = outcome
            doc["evaluation_state"] = "evaluated"
            doc["evaluated_at"] = _utcnow()
        try:
            self.db[SIM_HISTORY_COLLECTION].update_one(
                {"prediction_id": pid}, {"$set": doc}, upsert=True
            )
            return pid
        except Exception:
            return None

    # ── Reads ────────────────────────────────────────────────────────────
    def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        if self.db is None:
            return None
        try:
            row = self.db[SIM_HISTORY_COLLECTION].find_one(
                {"prediction_id": prediction_id}
            )
            return _json_safe(row)
        except Exception:
            return None

    def list_predictions(
        self,
        *,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        q: Dict[str, Any] = {}
        if symbol:
            q["symbol"] = symbol.upper()
        if timeframe:
            q["timeframe"] = timeframe.upper()
        try:
            cur = (
                self.db[SIM_HISTORY_COLLECTION]
                .find(q)
                .sort("created_at", -1)
                .limit(limit)
            )
            return [_json_safe(r) for r in cur]
        except Exception:
            return []

    def last_simulation_at(self) -> Optional[str]:
        if self.db is None:
            return None
        try:
            row = (
                self.db[SIM_HISTORY_COLLECTION]
                .find({}, {"_id": 0, "created_at": 1})
                .sort("created_at", -1)
                .limit(1)
            )
            for r in row:
                ts = r.get("created_at")
                if isinstance(ts, datetime):
                    return ts.isoformat()
                return str(ts) if ts else None
        except Exception:
            return None
        return None

    def history_breakdown(self) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        try:
            cursor = self.db[SIM_HISTORY_COLLECTION].aggregate([
                {"$group": {
                    "_id": {"symbol": "$symbol", "tf": "$timeframe"},
                    "count": {"$sum": 1},
                }},
                {"$sort": {"count": -1}},
                {"$limit": 100},
            ])
            return [
                {"symbol": r["_id"].get("symbol"), "tf": r["_id"].get("tf"), "count": int(r["count"])}
                for r in cursor
            ]
        except Exception:
            return []

    def debug_breakdown(self) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        try:
            cursor = self.db[SIM_DEBUG_COLLECTION].aggregate([
                {"$group": {
                    "_id": {"error_type": "$error_type"},
                    "count": {"$sum": 1},
                }},
                {"$sort": {"count": -1}},
                {"$limit": 50},
            ])
            return [
                {"error_type": r["_id"].get("error_type"), "count": int(r["count"])}
                for r in cursor
            ]
        except Exception:
            return []

    # ── Cleanup ──────────────────────────────────────────────────────────
    def clear_for(self, symbol: str, tf: str) -> Dict[str, int]:
        """Drop all sim records for (symbol, tf). NEVER touches live collections."""
        out = {"history_deleted": 0, "debug_deleted": 0}
        if self.db is None or not symbol or not tf:
            return out
        sym = symbol.upper()
        tfu = tf.upper()
        try:
            res = self.db[SIM_HISTORY_COLLECTION].delete_many({
                "symbol": sym, "timeframe": tfu
            })
            out["history_deleted"] = int(res.deleted_count or 0)
        except Exception:
            pass
        try:
            res = self.db[SIM_DEBUG_COLLECTION].delete_many({
                "symbol": sym, "tf": tfu
            })
            out["debug_deleted"] = int(res.deleted_count or 0)
        except Exception:
            pass
        return out

    def clear_all(self) -> Dict[str, int]:
        """Drop ALL sim records. Live collections untouched. QA-only."""
        out = {"history_deleted": 0, "debug_deleted": 0}
        if self.db is None:
            return out
        try:
            res = self.db[SIM_HISTORY_COLLECTION].delete_many({})
            out["history_deleted"] = int(res.deleted_count or 0)
        except Exception:
            pass
        try:
            res = self.db[SIM_DEBUG_COLLECTION].delete_many({})
            out["debug_deleted"] = int(res.deleted_count or 0)
        except Exception:
            pass
        return out


# Process-wide singleton ----------------------------------------------------
_sim_repo_singleton: Optional[SimulationRepository] = None


def get_simulation_repository() -> SimulationRepository:
    global _sim_repo_singleton
    if _sim_repo_singleton is None:
        _sim_repo_singleton = SimulationRepository()
    return _sim_repo_singleton
