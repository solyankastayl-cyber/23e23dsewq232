"""
Strategy Visibility Repository
===============================
Sprint A3: Signal + Decision snapshot layers

Collections:
- strategy_live_signals: Snapshot (one doc per symbol, upsert)
- strategy_decisions_recent: Append-only decision log
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING


class StrategyVisibilityRepository:
    def __init__(self, db):
        self.db = db
        self.live_col = db.strategy_live_signals
        self.decisions_col = db.strategy_decisions_recent
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.live_col.create_index(
            [("symbol", ASCENDING)],
            unique=True,
            name="uniq_strategy_live_symbol",
        )
        self.live_col.create_index(
            [("updated_at", DESCENDING)],
            name="idx_strategy_live_updated_at",
        )

        self.decisions_col.create_index(
            [("created_at", DESCENDING)],
            name="idx_strategy_decisions_created_at",
        )
        self.decisions_col.create_index(
            [("symbol", ASCENDING), ("created_at", DESCENDING)],
            name="idx_strategy_decisions_symbol_created_at",
        )

    async def upsert_live_signal(self, signal_doc: Dict[str, Any]) -> None:
        """Upsert live signal snapshot (one per symbol)."""
        now_ms = int(time.time() * 1000)
        payload = signal_doc.copy()
        payload["updated_at"] = now_ms

        symbol = payload["symbol"]

        await self.live_col.update_one(
            {"symbol": symbol},
            {"$set": payload, "$setOnInsert": {"created_at": now_ms}},
            upsert=True,
        )

    async def insert_decision(self, decision_doc: Dict[str, Any]) -> None:
        """Insert decision into append-only log."""
        payload = decision_doc.copy()
        payload.setdefault("created_at", int(time.time() * 1000))
        await self.decisions_col.insert_one(payload)

    async def get_live_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get current live signals snapshot."""
        cursor = self.live_col.find({}).sort("updated_at", DESCENDING).limit(limit)
        docs = await cursor.to_list(length=limit)
        for d in docs:
            d.pop("_id", None)
        return docs

    async def get_recent_decisions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent decisions (append-only log)."""
        cursor = self.decisions_col.find({}).sort("created_at", DESCENDING).limit(limit)
        docs = await cursor.to_list(length=limit)
        for d in docs:
            d.pop("_id", None)
        return docs

    async def get_summary(self, since_ms: Optional[int] = None) -> Dict[str, int]:
        """Get strategy summary stats."""
        query = {}
        if since_ms is not None:
            query["created_at"] = {"$gte": since_ms}

        approved = await self.decisions_col.count_documents({**query, "status": "APPROVED"})
        rejected = await self.decisions_col.count_documents({**query, "status": "REJECTED"})
        pending = await self.decisions_col.count_documents({**query, "status": "PENDING"})
        executed = await self.decisions_col.count_documents({**query, "status": "EXECUTED"})

        live_count = await self.live_col.count_documents({})

        return {
            "live_signals": live_count,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "executed": executed,
        }
