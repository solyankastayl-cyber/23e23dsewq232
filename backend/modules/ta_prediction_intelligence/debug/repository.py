"""
Debug Layer Mongo persistence (own collection, never touches history).

Collection: `ta_prediction_debug`

Indices:
    * uniq_prediction_id (prediction_id)        — debug record per prediction
    * by_symbol_tf_error  (symbol, tf, error_type)
    * by_state            (analyzed_at desc)    — recency queries

Upsert by prediction_id so re-runs after a taxonomy bump are idempotent.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEBUG_COLLECTION = "ta_prediction_debug"
DEBUG_COLLECTION_SIM = "ta_prediction_debug_sim"


class DebugRepository:
    def __init__(self, db: Any, collection_name: str = DEBUG_COLLECTION):
        self.db = db
        self.collection_name = collection_name or DEBUG_COLLECTION

    def _col(self):
        if self.db is None:
            return None
        try:
            col = self.db[self.collection_name]
            try:
                col.create_index("prediction_id", name="uniq_prediction_id", unique=True)
            except Exception:
                pass
            try:
                col.create_index(
                    [("symbol", 1), ("tf", 1), ("error_type", 1)],
                    name="by_symbol_tf_error",
                )
            except Exception:
                pass
            try:
                col.create_index(
                    [("analyzed_at", -1)], name="by_analyzed_at_desc"
                )
            except Exception:
                pass
            return col
        except Exception:
            return None

    # ── Read ──────────────────────────────────────────────────────────────
    def get(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        col = self._col()
        if col is None or not prediction_id:
            return None
        try:
            return col.find_one({"prediction_id": prediction_id}, {"_id": 0})
        except Exception:
            return None

    def list_recent(
        self,
        symbol: Optional[str] = None,
        tf: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        col = self._col()
        if col is None:
            return []
        q: Dict[str, Any] = {}
        if symbol:
            q["symbol"] = symbol.upper()
        if tf:
            q["tf"] = tf.upper()
        if error_type:
            q["error_type"] = error_type
        try:
            cursor = col.find(q, {"_id": 0}).sort("analyzed_at", -1).limit(int(limit))
            return list(cursor)
        except Exception:
            return []

    def list_for_metrics(
        self,
        symbol: Optional[str] = None,
        tf: Optional[str] = None,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        return self.list_recent(symbol=symbol, tf=tf, error_type=None, limit=limit)

    def count(self) -> int:
        col = self._col()
        if col is None:
            return 0
        try:
            return int(col.estimated_document_count())
        except Exception:
            return 0

    # ── Write ─────────────────────────────────────────────────────────────
    def upsert(self, debug_record: Dict[str, Any]) -> bool:
        col = self._col()
        if col is None or not debug_record.get("prediction_id"):
            return False
        debug_record = dict(debug_record)
        debug_record["analyzed_at"] = debug_record.get("analyzed_at") or datetime.now(
            timezone.utc
        )
        try:
            col.update_one(
                {"prediction_id": debug_record["prediction_id"]},
                {"$set": debug_record},
                upsert=True,
            )
            return True
        except Exception:
            return False

    def upsert_many(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        out = {"written": 0, "failed": 0}
        for r in records:
            if self.upsert(r):
                out["written"] += 1
            else:
                out["failed"] += 1
        return out


# ── Singleton ────────────────────────────────────────────────────────────
_repository_singleton: Optional[DebugRepository] = None


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


def init_debug_repository(db: Any = None) -> DebugRepository:
    global _repository_singleton
    _repository_singleton = DebugRepository(db if db is not None else _default_db())
    return _repository_singleton


def get_debug_repository() -> Optional[DebugRepository]:
    global _repository_singleton
    if _repository_singleton is None:
        try:
            _repository_singleton = DebugRepository(_default_db())
        except Exception:
            _repository_singleton = None
    return _repository_singleton
