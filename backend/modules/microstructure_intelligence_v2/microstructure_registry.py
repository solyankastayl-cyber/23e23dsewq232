"""
Microstructure Intelligence v2 — Registry

Storage for microstructure snapshot history in MongoDB.

Collection: microstructure_snapshot_history
"""

from typing import List, Optional
from datetime import datetime
import os
from collections import Counter

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from .microstructure_types import (
    MicrostructureSnapshot,
    MicrostructureHistoryRecord,
    MicrostructureSummary,
)


class MicrostructureRegistry:
    """
    Registry for storing microstructure snapshot history.
    
    Collection: microstructure_snapshot_history
    """
    
    COLLECTION = "microstructure_snapshot_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[MicrostructureHistoryRecord] = []
        self._use_cache = False if db is not None else None  # None = undetermined
    
    async def _get_db(self):
        """Get or create database connection."""
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
    
    async def store_snapshot(
        self,
        snapshot: MicrostructureSnapshot,
    ) -> MicrostructureHistoryRecord:
        """Store snapshot in history."""
        record = MicrostructureHistoryRecord(
            symbol=snapshot.symbol,
            spread_bps=snapshot.spread_bps,
            depth_score=snapshot.depth_score,
            imbalance_score=snapshot.imbalance_score,
            liquidation_pressure=snapshot.liquidation_pressure,
            funding_pressure=snapshot.funding_pressure,
            oi_pressure=snapshot.oi_pressure,
            liquidity_state=snapshot.liquidity_state,
            pressure_state=snapshot.pressure_state,
            microstructure_state=snapshot.microstructure_state,
            confidence=snapshot.confidence,
            recorded_at=datetime.utcnow(),
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
    ) -> List[MicrostructureHistoryRecord]:
        """Get snapshot history for symbol."""
        db = await self._get_db()
        if self._use_cache:
            history = [r for r in self._cache if r.symbol == symbol]
            return sorted(history, key=lambda r: r.recorded_at, reverse=True)[:limit]
        
        if db is None:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"symbol": symbol}
        ).sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(MicrostructureHistoryRecord(**doc))
        
        return results
    
    async def get_latest(
        self,
        symbol: str,
    ) -> Optional[MicrostructureHistoryRecord]:
        """Get most recent snapshot for symbol."""
        history = await self.get_history(symbol, limit=1)
        return history[0] if history else None
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(
        self,
        symbol: str,
    ) -> MicrostructureSummary:
        """Get summary statistics for symbol."""
        history = await self.get_history(symbol, limit=100)
        
        if not history:
            return MicrostructureSummary(
                symbol=symbol,
                total_records=0,
                deep_count=0,
                normal_count=0,
                thin_count=0,
                buy_pressure_count=0,
                sell_pressure_count=0,
                balanced_count=0,
                supportive_count=0,
                neutral_count=0,
                fragile_count=0,
                stressed_count=0,
                average_spread_bps=0.0,
                average_depth_score=0.0,
                average_confidence=0.0,
                current_state="NEUTRAL",
            )
        
        # Count liquidity states
        deep = len([r for r in history if r.liquidity_state == "DEEP"])
        normal = len([r for r in history if r.liquidity_state == "NORMAL"])
        thin = len([r for r in history if r.liquidity_state == "THIN"])
        
        # Count pressure states
        buy = len([r for r in history if r.pressure_state == "BUY_PRESSURE"])
        sell = len([r for r in history if r.pressure_state == "SELL_PRESSURE"])
        balanced = len([r for r in history if r.pressure_state == "BALANCED"])
        
        # Count microstructure states
        supportive = len([r for r in history if r.microstructure_state == "SUPPORTIVE"])
        neutral = len([r for r in history if r.microstructure_state == "NEUTRAL"])
        fragile = len([r for r in history if r.microstructure_state == "FRAGILE"])
        stressed = len([r for r in history if r.microstructure_state == "STRESSED"])
        
        # Averages
        avg_spread = sum(r.spread_bps for r in history) / len(history)
        avg_depth = sum(r.depth_score for r in history) / len(history)
        avg_conf = sum(r.confidence for r in history) / len(history)
        
        return MicrostructureSummary(
            symbol=symbol,
            total_records=len(history),
            deep_count=deep,
            normal_count=normal,
            thin_count=thin,
            buy_pressure_count=buy,
            sell_pressure_count=sell,
            balanced_count=balanced,
            supportive_count=supportive,
            neutral_count=neutral,
            fragile_count=fragile,
            stressed_count=stressed,
            average_spread_bps=round(avg_spread, 2),
            average_depth_score=round(avg_depth, 4),
            average_confidence=round(avg_conf, 4),
            current_state=history[0].microstructure_state,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear snapshot history (for testing)."""
        db = await self._get_db()
        if self._use_cache:
            if symbol:
                self._cache = [r for r in self._cache if r.symbol != symbol]
            else:
                self._cache.clear()
        else:
            if db:
                if symbol:
                    await db[self.COLLECTION].delete_many({"symbol": symbol})
                else:
                    await db[self.COLLECTION].delete_many({})


# Singleton
_registry: Optional[MicrostructureRegistry] = None


def get_microstructure_registry() -> MicrostructureRegistry:
    """Get singleton instance of MicrostructureRegistry."""
    global _registry
    if _registry is None:
        _registry = MicrostructureRegistry()
    return _registry
