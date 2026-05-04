"""
Strategy Regime Mapping — Registry

Storage for strategy-regime mapping history in MongoDB.

Collection: strategy_regime_history
"""

from typing import List, Optional
from datetime import datetime
import os

from motor.motor_asyncio import AsyncIOMotorClient

from .strategy_regime_types import (
    StrategyRegimeMapping,
    StrategyRegimeHistoryRecord,
)


class StrategyRegimeRegistry:
    """
    Registry for storing strategy-regime mapping history.
    
    Collection: strategy_regime_history
    """
    
    COLLECTION = "strategy_regime_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[StrategyRegimeHistoryRecord] = []
        self._use_cache = db is None
    
    async def _get_db(self):
        """Get or create database connection."""
        if self._db is not None:
            return self._db
        
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        if mongo_url:
            if self._client is None:
                self._client = AsyncIOMotorClient(mongo_url)
            return self._client[db_name]
        
        self._use_cache = True
        return None
    
    # ═══════════════════════════════════════════════════════════
    # Write Operations
    # ═══════════════════════════════════════════════════════════
    
    async def store_mapping(
        self,
        mapping: StrategyRegimeMapping,
    ) -> StrategyRegimeHistoryRecord:
        """Store mapping in history."""
        record = StrategyRegimeHistoryRecord(
            strategy=mapping.strategy,
            regime_type=mapping.regime_type,
            suitability=mapping.suitability,
            state=mapping.state,
            confidence_modifier=mapping.confidence_modifier,
            capital_modifier=mapping.capital_modifier,
            timestamp=datetime.utcnow(),
        )
        
        if self._use_cache:
            self._cache.append(record)
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].insert_one(record.model_dump())
        
        return record
    
    async def store_mappings_bulk(
        self,
        mappings: List[StrategyRegimeMapping],
    ) -> List[StrategyRegimeHistoryRecord]:
        """Store multiple mappings."""
        records = []
        
        for mapping in mappings:
            record = await self.store_mapping(mapping)
            records.append(record)
        
        return records
    
    # ═══════════════════════════════════════════════════════════
    # Read Operations
    # ═══════════════════════════════════════════════════════════
    
    async def get_strategy_history(
        self,
        strategy: str,
        limit: int = 100,
    ) -> List[StrategyRegimeHistoryRecord]:
        """Get history for a specific strategy."""
        if self._use_cache:
            history = [r for r in self._cache if r.strategy == strategy]
            return sorted(history, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"strategy": strategy}
        ).sort("timestamp", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(StrategyRegimeHistoryRecord(**doc))
        
        return results
    
    async def get_regime_history(
        self,
        regime_type: str,
        limit: int = 100,
    ) -> List[StrategyRegimeHistoryRecord]:
        """Get history for a specific regime."""
        if self._use_cache:
            history = [r for r in self._cache if r.regime_type == regime_type]
            return sorted(history, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"regime_type": regime_type}
        ).sort("timestamp", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(StrategyRegimeHistoryRecord(**doc))
        
        return results
    
    async def get_all_history(
        self,
        limit: int = 500,
    ) -> List[StrategyRegimeHistoryRecord]:
        """Get all mapping history."""
        if self._use_cache:
            return sorted(
                self._cache,
                key=lambda r: r.timestamp,
                reverse=True
            )[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find().sort("timestamp", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(StrategyRegimeHistoryRecord(**doc))
        
        return results
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self) -> None:
        """Clear all mapping history (for testing)."""
        if self._use_cache:
            self._cache.clear()
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].delete_many({})


# Singleton
_registry: Optional[StrategyRegimeRegistry] = None


def get_strategy_regime_registry() -> StrategyRegimeRegistry:
    """Get singleton instance of StrategyRegimeRegistry."""
    global _registry
    if _registry is None:
        _registry = StrategyRegimeRegistry()
    return _registry
