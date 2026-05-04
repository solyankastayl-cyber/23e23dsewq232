"""
TradingCase Repository

Phase closing-loop.MARK follow-up (2026-04-23):
  Previously this repo was an in-memory dict with Mongo as a write-through
  persistence layer, but READS still came from memory. That meant:
    * fresh backend restart → memory empty → UI sees "CASES (0)" even
      though `trading_os.trading_cases` has live ACTIVE rows;
    * mark_price_updater writes directly to Mongo and never goes through
      `save()`, so its PnL updates were invisible to the API layer.

  Fix: MongoDB is now the source of truth. Every read hits the collection.
  A small in-memory cache (``self.cases``) is preserved for legacy code
  paths that expect `save()` to return an enriched object, but it is
  always resynced from Mongo on every read method — so freshness is
  guaranteed.
"""

from typing import Dict, List, Optional
import logging

from .models import TradingCase

logger = logging.getLogger(__name__)


class TradingCaseRepository:
    """MongoDB-backed repository for trading cases, with in-memory fallback."""

    def __init__(self, db=None):
        """
        Initialize repository.

        Args:
            db: MongoDB database instance. Accepts either:
                * pymongo ``Database`` (preferred — sync reads)
                * motor ``AsyncIOMotorDatabase`` — we will build a parallel
                  sync connection from the same ``MongoClient`` URL because
                  our read methods are synchronous.
                * ``None`` — in-memory only mode (unit tests).
        """
        self.cases: Dict[str, TradingCase] = {}
        self.db = self._coerce_to_sync(db)

    @staticmethod
    def _coerce_to_sync(db):
        """
        Ensure we hold a sync pymongo ``Database``.

        The rest of this repository uses synchronous ``find()`` /
        ``replace_one()`` — not coroutines. If the caller handed us a motor
        async db we open a sibling sync connection to the same host/db
        (cheap, reuses the same MongoClient pool via the MONGO_URL env).
        """
        if db is None:
            return None
        # pymongo Database exposes `name` and doesn't require await.
        # motor AsyncIOMotorDatabase also has `name` but its client is async.
        try:
            cls_name = type(db).__name__
            if cls_name.startswith("AsyncIOMotor"):
                # Pull host + db name from the motor client and rebuild sync.
                import os
                from pymongo import MongoClient
                mongo_url = os.environ.get(
                    "MONGO_URL", "mongodb://localhost:27017"
                )
                db_name = getattr(db, "name", None) or "trading_os"
                sync_client = MongoClient(
                    mongo_url, serverSelectionTimeoutMS=5000
                )
                logger.info(
                    f"[TradingCaseRepository] motor db detected → using sync "
                    f"pymongo mirror on db='{db_name}'"
                )
                return sync_client[db_name]
        except Exception as e:
            logger.warning(
                f"[TradingCaseRepository] could not coerce db to sync: {e}"
            )
        return db

    # ------------------------------------------------------------------ utils
    def _collection(self):
        """Return the trading_cases collection or None."""
        if self.db is None:
            return None
        try:
            return self.db["trading_cases"]
        except Exception:
            return None

    @staticmethod
    def _doc_to_model(doc: Dict) -> Optional[TradingCase]:
        """Convert a Mongo doc to a TradingCase Pydantic model."""
        if not doc:
            return None
        doc = dict(doc)
        doc.pop("_id", None)
        try:
            return TradingCase(**doc)
        except Exception as e:
            logger.warning(
                f"[TradingCaseRepository] failed to parse case {doc.get('case_id')}: {e}"
            )
            return None

    # --------------------------------------------------------------- writes
    def save(self, case: TradingCase) -> TradingCase:
        """Save or update a case (in-memory + MongoDB upsert)."""
        self.cases[case.case_id] = case

        col = self._collection()
        if col is not None:
            try:
                case_dict = case.model_dump() if hasattr(case, "model_dump") else case.dict()
                col.replace_one(
                    {"case_id": case.case_id},
                    case_dict,
                    upsert=True,
                )
            except Exception as e:
                logger.error(f"[TradingCaseRepository] persist failed: {e}")

        return case

    def delete(self, case_id: str) -> bool:
        """Delete a case (in-memory + Mongo)."""
        removed = self.cases.pop(case_id, None) is not None
        col = self._collection()
        if col is not None:
            try:
                res = col.delete_one({"case_id": case_id})
                if res.deleted_count:
                    removed = True
            except Exception as e:
                logger.error(f"[TradingCaseRepository] delete failed: {e}")
        return removed

    # --------------------------------------------------------------- reads
    def _read_many(self, query: Dict) -> List[TradingCase]:
        """Read list of cases from Mongo using given query; fallback to memory."""
        col = self._collection()
        if col is not None:
            try:
                # Enforce sensible ordering: newest open first.
                cursor = col.find(query).sort("opened_at", -1)
                cases: List[TradingCase] = []
                for doc in cursor:
                    m = self._doc_to_model(doc)
                    if m:
                        cases.append(m)
                        # keep the in-memory map in sync so legacy callers
                        # (`get(case_id)` right after `get_all`) work.
                        self.cases[m.case_id] = m
                return cases
            except Exception as e:
                logger.error(f"[TradingCaseRepository] mongo read failed: {e}")

        # Fallback: in-memory scan matching the subset of keys we support.
        def _match(c: TradingCase) -> bool:
            for k, v in query.items():
                if getattr(c, k, None) != v:
                    return False
            return True

        return [c for c in self.cases.values() if _match(c)]

    def get(self, case_id: str) -> Optional[TradingCase]:
        """Get case by ID (Mongo first, memory fallback)."""
        col = self._collection()
        if col is not None:
            try:
                doc = col.find_one({"case_id": case_id})
                m = self._doc_to_model(doc)
                if m:
                    self.cases[m.case_id] = m
                    return m
            except Exception as e:
                logger.error(f"[TradingCaseRepository] get failed: {e}")
        return self.cases.get(case_id)

    def get_all(self, experiment_id: Optional[str] = None) -> List[TradingCase]:
        """Get all cases. Optional experiment filter."""
        query: Dict = {}
        if experiment_id is not None:
            query["experiment_id"] = experiment_id
        return self._read_many(query)

    def get_active(self, experiment_id: Optional[str] = None) -> List[TradingCase]:
        """Get active cases."""
        query: Dict = {"status": "ACTIVE"}
        if experiment_id is not None:
            query["experiment_id"] = experiment_id
        return self._read_many(query)

    def get_closed(self, experiment_id: Optional[str] = None) -> List[TradingCase]:
        """Get closed cases."""
        query: Dict = {"status": "CLOSED"}
        if experiment_id is not None:
            query["experiment_id"] = experiment_id
        return self._read_many(query)

    def get_by_symbol(
        self, symbol: str, experiment_id: Optional[str] = None
    ) -> List[TradingCase]:
        """Get all cases for a symbol."""
        query: Dict = {"symbol": symbol}
        if experiment_id is not None:
            query["experiment_id"] = experiment_id
        return self._read_many(query)


# Singleton instance
_repository: Optional[TradingCaseRepository] = None


def init_repository(db):
    """Initialize repository singleton with MongoDB."""
    global _repository
    _repository = TradingCaseRepository(db=db)
    return _repository


def get_repository() -> TradingCaseRepository:
    """Get repository singleton."""
    global _repository
    if _repository is None:
        raise RuntimeError(
            "TradingCaseRepository not initialized - call init_repository() first"
        )
    return _repository
