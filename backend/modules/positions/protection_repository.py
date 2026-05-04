"""
Protection Repository
Sprint A7: Store TP/SL rules in DB
"""

from pymongo import ASCENDING
import time
import logging

logger = logging.getLogger(__name__)


class ProtectionRepository:
    """
    Repository for position_protection collection.
    
    Stores TP/SL rules that ProtectionWatcher monitors.
    """
    
    def __init__(self, db):
        self.col = db["position_protection"]
        
        # Create unique index on symbol
        try:
            self.col.create_index(
                [("symbol", ASCENDING)],
                unique=True,
                name="uniq_symbol_protection"
            )
        except Exception as e:
            logger.warning(f"[ProtectionRepo] Index creation skipped: {e}")
    
    async def upsert(self, symbol: str, data: dict):
        """
        Upsert protection rule for symbol.
        """
        await self.col.update_one(
            {"symbol": symbol},
            {
                "$set": {
                    **data,
                    "updated_at": int(time.time() * 1000)
                }
            },
            upsert=True
        )
        logger.info(f"[ProtectionRepo] Upserted protection for {symbol}")
    
    async def get(self, symbol: str):
        """
        Get protection rule for symbol.
        """
        doc = await self.col.find_one({"symbol": symbol})
        if doc:
            doc.pop("_id", None)
        return doc
    
    async def get_all_active(self):
        """
        Get all active protection rules.
        """
        cursor = self.col.find({"status": "ACTIVE"})
        docs = await cursor.to_list(length=100)
        for doc in docs:
            doc.pop("_id", None)
        return docs
    
    async def disable(self, symbol: str):
        """
        Disable protection rule (after trigger).
        """
        await self.col.update_one(
            {"symbol": symbol},
            {"$set": {"status": "INACTIVE"}}
        )
        logger.info(f"[ProtectionRepo] Disabled protection for {symbol}")
