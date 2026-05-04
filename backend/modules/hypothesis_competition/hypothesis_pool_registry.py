"""
Hypothesis Pool Registry

PHASE 30.1 — Persistent storage for hypothesis pools.

Collection: hypothesis_pool_history
"""

from typing import List, Optional, Dict
from datetime import datetime, timezone
import os

from pydantic import BaseModel
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from .hypothesis_pool_types import (
    HypothesisPool,
    HypothesisPoolItem,
    HypothesisPoolHistoryRecord,
    HypothesisPoolSummary,
)


# ══════════════════════════════════════════════════════════════
# Hypothesis Pool Registry
# ══════════════════════════════════════════════════════════════

class HypothesisPoolRegistry:
    """
    Registry for storing hypothesis pool history.
    
    Collection: hypothesis_pool_history
    """
    
    COLLECTION = "hypothesis_pool_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[HypothesisPoolHistoryRecord] = []
        self._use_cache = False if db is not None else None
    
    async def _get_db(self):
        """Get or create database connection."""
        if self._use_cache is True:
            return None
        
        if self._db is not None:
            return self._db
        
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        if mongo_url:
            if self._client is None:
                self._client = AsyncIOMotorClient(mongo_url)
            self._use_cache = False
            return self._client[db_name]
        
        self._use_cache = True
        return None
    
    # ═══════════════════════════════════════════════════════════
    # Write Operations
    # ═══════════════════════════════════════════════════════════
    
    async def store_pool(self, pool: HypothesisPool) -> HypothesisPoolHistoryRecord:
        """Store hypothesis pool in history."""
        record = HypothesisPoolHistoryRecord(
            symbol=pool.symbol,
            hypotheses=[h.model_dump() for h in pool.hypotheses],
            top_hypothesis=pool.top_hypothesis,
            pool_confidence=pool.pool_confidence,
            pool_reliability=pool.pool_reliability,
            pool_size=pool.pool_size,
            created_at=pool.created_at,
        )
        
        db = await self._get_db()
        if self._use_cache:
            self._cache.append(record)
        else:
            if db is not None:
                await db[self.COLLECTION].insert_one(record.model_dump())
        
        return record
    
    # ═══════════════════════════════════════════════════════════
    # Read Operations
    # ═══════════════════════════════════════════════════════════
    
    async def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[HypothesisPoolHistoryRecord]:
        """Get pool history for symbol."""
        db = await self._get_db()
        if self._use_cache:
            history = [r for r in self._cache if r.symbol == symbol]
            return sorted(history, key=lambda r: r.created_at, reverse=True)[:limit]
        
        if db is None:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"symbol": symbol}
        ).sort("created_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(HypothesisPoolHistoryRecord(**doc))
        
        return results
    
    async def get_latest(self, symbol: str) -> Optional[HypothesisPoolHistoryRecord]:
        """Get most recent pool for symbol."""
        history = await self.get_history(symbol, limit=1)
        return history[0] if history else None
    
    async def get_summary(self, symbol: str) -> HypothesisPoolSummary:
        """Get summary statistics for symbol."""
        history = await self.get_history(symbol, limit=500)
        
        if not history:
            return HypothesisPoolSummary(
                symbol=symbol,
                total_pools=0,
            )
        
        # Top hypothesis distribution
        top_counts: Dict[str, int] = {}
        for record in history:
            t = record.top_hypothesis
            top_counts[t] = top_counts.get(t, 0) + 1
        
        # Averages
        avg_size = sum(r.pool_size for r in history) / len(history)
        avg_conf = sum(r.pool_confidence for r in history) / len(history)
        avg_rel = sum(r.pool_reliability for r in history) / len(history)
        
        current = history[0] if history else None
        
        return HypothesisPoolSummary(
            symbol=symbol,
            total_pools=len(history),
            top_hypothesis_counts=top_counts,
            avg_pool_size=round(avg_size, 2),
            avg_pool_confidence=round(avg_conf, 4),
            avg_pool_reliability=round(avg_rel, 4),
            current_top_hypothesis=current.top_hypothesis if current else "NO_EDGE",
            current_pool_size=current.pool_size if current else 0,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear pool history (for testing)."""
        db = await self._get_db()
        if self._use_cache:
            if symbol:
                self._cache = [r for r in self._cache if r.symbol != symbol]
            else:
                self._cache.clear()
        else:
            if db is not None:
                if symbol:
                    await db[self.COLLECTION].delete_many({"symbol": symbol})
                else:
                    await db[self.COLLECTION].delete_many({})


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_pool_registry: Optional[HypothesisPoolRegistry] = None


def get_hypothesis_pool_registry() -> HypothesisPoolRegistry:
    """Get singleton instance of HypothesisPoolRegistry."""
    global _pool_registry
    if _pool_registry is None:
        _pool_registry = HypothesisPoolRegistry()
    return _pool_registry
