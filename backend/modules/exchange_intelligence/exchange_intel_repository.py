"""
PHASE 13.8 — Exchange Intelligence Repository
===============================================
Data access layer for exchange intelligence engines.
Reads from exchange data collections + candles.
Writes computed signals to exchange_intelligence_signals.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, DESCENDING


class ExchangeIntelRepository:
    """MongoDB access for Exchange Intelligence."""

    def __init__(self):
        self.mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = os.environ.get("DB_NAME", "ta_engine")
        self._client: Optional[MongoClient] = None
        self._db = None

    def _get_db(self):
        if self._db is None:
            self._client = MongoClient(self.mongo_url)
            self._db = self._client[self.db_name]
            self._ensure_indexes()
        return self._db

    def _ensure_indexes(self):
        db = self._db
        db.exchange_intel_signals.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        db.exchange_intel_signals.create_index([("timestamp", DESCENDING)])
        db.exchange_intel_funding.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        db.exchange_intel_volume.create_index([("symbol", 1), ("timestamp", DESCENDING)])

    # ── Candle Data ──

    def get_candles(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        db = self._get_db()
        cursor = db.candles.find(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))

    def get_latest_candle(self, symbol: str, timeframe: str = "1d") -> Optional[Dict]:
        db = self._get_db()
        return db.candles.find_one(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0},
            sort=[("timestamp", DESCENDING)]
        )

    # ── Exchange Data (from TS exchange module) ──

    def get_funding_data(self, symbol: str, limit: int = 50) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_funding_context.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))

    def get_oi_data(self, symbol: str, limit: int = 50) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_oi_snapshots.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))

    def get_liquidation_data(self, symbol: str, limit: int = 200) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_liquidation_events.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))

    def get_orderflow_data(self, symbol: str, limit: int = 50) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_trade_flows.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))

    def get_symbol_snapshot(self, symbol: str) -> Optional[Dict]:
        db = self._get_db()
        return db.exchange_symbol_snapshots.find_one(
            {"symbol": symbol},
            {"_id": 0},
            sort=[("timestamp", DESCENDING)]
        )

    # ── Write Signals ──

    def save_exchange_context(self, context_dict: Dict) -> str:
        db = self._get_db()
        context_dict["saved_at"] = datetime.now(timezone.utc).isoformat()
        db.exchange_intel_signals.update_one(
            {"symbol": context_dict["symbol"]},
            {"$set": context_dict},
            upsert=True
        )
        return context_dict["symbol"]

    def get_latest_context(self, symbol: str) -> Optional[Dict]:
        db = self._get_db()
        return db.exchange_intel_signals.find_one(
            {"symbol": symbol},
            {"_id": 0},
            sort=[("timestamp", DESCENDING)]
        )

    def get_all_contexts(self) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_intel_signals.find(
            {},
            {"_id": 0}
        ).sort("timestamp", DESCENDING)
        return list(cursor)

    def save_funding_snapshot(self, snapshot: Dict):
        db = self._get_db()
        db.exchange_intel_funding.insert_one(snapshot)

    def save_volume_snapshot(self, snapshot: Dict):
        db = self._get_db()
        db.exchange_intel_volume.insert_one(snapshot)

    def get_funding_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_intel_funding.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))

    def get_volume_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        db = self._get_db()
        cursor = db.exchange_intel_volume.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(reversed(list(cursor)))
