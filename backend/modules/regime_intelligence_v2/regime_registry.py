"""
Regime Intelligence v2 — Registry

Storage for regime history in MongoDB.

Collection: market_regime_history
"""

from typing import List, Optional
from datetime import datetime
import os

from motor.motor_asyncio import AsyncIOMotorClient

from .regime_types import (
    MarketRegime,
    RegimeHistoryRecord,
    RegimeSummary,
    RegimeType,
)


class RegimeRegistry:
    """
    Registry for storing regime history.
    
    Collection: market_regime_history
    """
    
    COLLECTION = "market_regime_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[RegimeHistoryRecord] = []
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
    
    async def store_regime(
        self,
        regime: MarketRegime,
    ) -> RegimeHistoryRecord:
        """Store regime in history."""
        record = RegimeHistoryRecord(
            regime_type=regime.regime_type,
            confidence=regime.regime_confidence,
            trend_strength=regime.trend_strength,
            volatility=regime.volatility_level,
            liquidity=regime.liquidity_level,
            dominant_driver=regime.dominant_driver,
            context_state=regime.context_state,
            symbol=regime.symbol,
            timeframe=regime.timeframe,
            timestamp=datetime.utcnow(),
        )
        
        if self._use_cache:
            self._cache.append(record)
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].insert_one(record.model_dump())
        
        return record
    
    # ═══════════════════════════════════════════════════════════
    # Read Operations
    # ═══════════════════════════════════════════════════════════
    
    async def get_history(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
        limit: int = 100,
    ) -> List[RegimeHistoryRecord]:
        """Get regime history for symbol/timeframe."""
        if self._use_cache:
            history = [
                r for r in self._cache
                if r.symbol == symbol and r.timeframe == timeframe
            ]
            return sorted(history, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"symbol": symbol, "timeframe": timeframe}
        ).sort("timestamp", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RegimeHistoryRecord(**doc))
        
        return results
    
    async def get_all_history(
        self,
        limit: int = 500,
    ) -> List[RegimeHistoryRecord]:
        """Get all regime history."""
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
            results.append(RegimeHistoryRecord(**doc))
        
        return results
    
    async def get_latest(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> Optional[RegimeHistoryRecord]:
        """Get most recent regime for symbol/timeframe."""
        history = await self.get_history(symbol, timeframe, limit=1)
        return history[0] if history else None
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> RegimeSummary:
        """Get regime summary statistics."""
        history = await self.get_history(symbol, timeframe, limit=100)
        
        if not history:
            return RegimeSummary(
                total_records=0,
                trending_count=0,
                ranging_count=0,
                volatile_count=0,
                illiquid_count=0,
                current_regime="RANGING",
                average_confidence=0.0,
                dominant_regime="RANGING",
                regime_stability=0.0,
            )
        
        # Count by type
        trending = len([r for r in history if r.regime_type == "TRENDING"])
        ranging = len([r for r in history if r.regime_type == "RANGING"])
        volatile = len([r for r in history if r.regime_type == "VOLATILE"])
        illiquid = len([r for r in history if r.regime_type == "ILLIQUID"])
        
        # Current
        current = history[0].regime_type if history else "RANGING"
        
        # Average confidence
        avg_conf = sum(r.confidence for r in history) / len(history)
        
        # Dominant regime
        counts = {
            "TRENDING": trending,
            "RANGING": ranging,
            "VOLATILE": volatile,
            "ILLIQUID": illiquid,
        }
        dominant = max(counts, key=counts.get)
        
        # Stability (how often regime stays same as previous)
        stability = 0.0
        if len(history) > 1:
            same_count = sum(
                1 for i in range(1, len(history))
                if history[i].regime_type == history[i-1].regime_type
            )
            stability = same_count / (len(history) - 1)
        
        return RegimeSummary(
            total_records=len(history),
            trending_count=trending,
            ranging_count=ranging,
            volatile_count=volatile,
            illiquid_count=illiquid,
            current_regime=current,
            average_confidence=round(avg_conf, 4),
            dominant_regime=dominant,
            regime_stability=round(stability, 4),
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self) -> None:
        """Clear all regime history (for testing)."""
        if self._use_cache:
            self._cache.clear()
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].delete_many({})


# Singleton
_registry: Optional[RegimeRegistry] = None


def get_regime_registry() -> RegimeRegistry:
    """Get singleton instance of RegimeRegistry."""
    global _registry
    if _registry is None:
        _registry = RegimeRegistry()
    return _registry
