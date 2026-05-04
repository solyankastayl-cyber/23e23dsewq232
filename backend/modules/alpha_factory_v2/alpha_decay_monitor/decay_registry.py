"""
Alpha Decay Monitor — Registry

Storage for decay history in MongoDB.

Collection: alpha_decay_history
"""

from typing import List, Optional
from datetime import datetime
import os

from motor.motor_asyncio import AsyncIOMotorClient

from .decay_types import DecayHistoryRecord, AlphaDecayState


class AlphaDecayRegistry:
    """
    Registry for storing decay history.
    
    Collection: alpha_decay_history
    """
    
    COLLECTION = "alpha_decay_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[DecayHistoryRecord] = []
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
    
    async def store_decay_state(
        self,
        state: AlphaDecayState,
    ) -> DecayHistoryRecord:
        """Store decay state in history."""
        record = DecayHistoryRecord(
            factor_id=state.factor_id,
            previous_alpha_score=state.previous_alpha_score,
            current_alpha_score=state.current_alpha_score,
            alpha_drift=state.alpha_drift,
            decay_rate=state.decay_rate,
            decay_state=state.decay_state,
            recorded_at=datetime.utcnow(),
        )
        
        if self._use_cache:
            self._cache.append(record)
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].insert_one(record.model_dump())
        
        return record
    
    async def store_decay_states_bulk(
        self,
        states: List[AlphaDecayState],
    ) -> List[DecayHistoryRecord]:
        """Store multiple decay states."""
        records = []
        
        for state in states:
            record = await self.store_decay_state(state)
            records.append(record)
        
        return records
    
    # ═══════════════════════════════════════════════════════════
    # Read Operations
    # ═══════════════════════════════════════════════════════════
    
    async def get_factor_history(
        self,
        factor_id: str,
        limit: int = 100,
    ) -> List[DecayHistoryRecord]:
        """Get decay history for a factor."""
        if self._use_cache:
            history = [r for r in self._cache if r.factor_id == factor_id]
            return sorted(history, key=lambda r: r.recorded_at, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"factor_id": factor_id}
        ).sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(DecayHistoryRecord(**doc))
        
        return results
    
    async def get_all_history(
        self,
        limit: int = 500,
    ) -> List[DecayHistoryRecord]:
        """Get all decay history records."""
        if self._use_cache:
            return sorted(
                self._cache,
                key=lambda r: r.recorded_at,
                reverse=True
            )[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find().sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(DecayHistoryRecord(**doc))
        
        return results
    
    async def get_critical_history(
        self,
        limit: int = 100,
    ) -> List[DecayHistoryRecord]:
        """Get history of CRITICAL decay events."""
        if self._use_cache:
            critical = [r for r in self._cache if r.decay_state == "CRITICAL"]
            return sorted(critical, key=lambda r: r.recorded_at, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"decay_state": "CRITICAL"}
        ).sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(DecayHistoryRecord(**doc))
        
        return results
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self) -> None:
        """Clear all decay history (for testing)."""
        if self._use_cache:
            self._cache.clear()
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].delete_many({})


# Singleton
_registry: Optional[AlphaDecayRegistry] = None


def get_alpha_decay_registry() -> AlphaDecayRegistry:
    """Get singleton instance of AlphaDecayRegistry."""
    global _registry
    if _registry is None:
        _registry = AlphaDecayRegistry()
    return _registry
