"""
Auto Safety Repository
======================
Sprint A4: Config + State persistence
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from pymongo import ASCENDING, DESCENDING


class AutoSafetyRepository:
    def __init__(self, db):
        self.db = db
        self.config_col = db.auto_safety_config
        self.state_col = db.auto_safety_state
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.config_col.create_index([("config_id", ASCENDING)], unique=True)
        self.state_col.create_index([("state_id", ASCENDING)], unique=True)
        self.state_col.create_index([("updated_at", DESCENDING)])

    async def get_or_create_config(self, defaults: Dict[str, Any]) -> Dict[str, Any]:
        doc = await self.config_col.find_one({"config_id": "main"})
        if doc:
            doc.pop("_id", None)
            return doc

        payload = {"config_id": "main", **defaults, "updated_at": int(time.time() * 1000)}
        await self.config_col.insert_one(payload)
        return payload

    async def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        patch["updated_at"] = int(time.time() * 1000)
        await self.config_col.update_one(
            {"config_id": "main"},
            {"$set": patch},
            upsert=True,
        )
        doc = await self.config_col.find_one({"config_id": "main"})
        doc.pop("_id", None)
        return doc

    async def get_or_create_state(self) -> Dict[str, Any]:
        doc = await self.state_col.find_one({"state_id": "main"})
        if doc:
            doc.pop("_id", None)
            return doc

        payload = {
            "state_id": "main",
            "trades_last_hour": 0,
            "concurrent_positions": 0,
            "capital_deployed_pct": 0.0,
            "daily_pnl_usd": 0.0,
            "consecutive_losses": 0,
            "last_block_reason": None,
            "updated_at": int(time.time() * 1000),
        }
        await self.state_col.insert_one(payload)
        return payload

    async def update_state(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        patch["updated_at"] = int(time.time() * 1000)
        await self.state_col.update_one(
            {"state_id": "main"},
            {"$set": patch},
            upsert=True,
        )
        doc = await self.state_col.find_one({"state_id": "main"})
        doc.pop("_id", None)
        return doc
