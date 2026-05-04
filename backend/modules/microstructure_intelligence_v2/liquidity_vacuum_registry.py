"""
Liquidity Vacuum Detector — Registry

PHASE 28.2 — Storage for liquidity vacuum history in MongoDB.

Collection: liquidity_vacuum_history
"""

from typing import List, Optional
from datetime import datetime
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from .liquidity_vacuum_types import (
    LiquidityVacuumState,
    LiquidityVacuumHistoryRecord,
    LiquidityVacuumSummary,
)


class LiquidityVacuumRegistry:
    """
    Registry for storing liquidity vacuum history.
    
    Collection: liquidity_vacuum_history
    """
    
    COLLECTION = "liquidity_vacuum_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[LiquidityVacuumHistoryRecord] = []
        self._use_cache = False if db is not None else None
    
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
    
    async def store_vacuum_state(
        self,
        state: LiquidityVacuumState,
    ) -> LiquidityVacuumHistoryRecord:
        """Store vacuum state in history."""
        record = LiquidityVacuumHistoryRecord(
            symbol=state.symbol,
            vacuum_direction=state.vacuum_direction,
            vacuum_probability=state.vacuum_probability,
            vacuum_size_bps=state.vacuum_size_bps,
            nearest_liquidity_wall_distance=state.nearest_liquidity_wall_distance,
            orderbook_gap_score=state.orderbook_gap_score,
            liquidity_state=state.liquidity_state,
            confidence=state.confidence,
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
    ) -> List[LiquidityVacuumHistoryRecord]:
        """Get vacuum history for symbol."""
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
            results.append(LiquidityVacuumHistoryRecord(**doc))
        
        return results
    
    async def get_latest(
        self,
        symbol: str,
    ) -> Optional[LiquidityVacuumHistoryRecord]:
        """Get most recent vacuum state for symbol."""
        history = await self.get_history(symbol, limit=1)
        return history[0] if history else None
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(
        self,
        symbol: str,
    ) -> LiquidityVacuumSummary:
        """Get summary statistics for symbol."""
        history = await self.get_history(symbol, limit=100)
        
        if not history:
            return LiquidityVacuumSummary(
                symbol=symbol,
                total_records=0,
                up_count=0,
                down_count=0,
                none_count=0,
                normal_count=0,
                thin_zone_count=0,
                vacuum_count=0,
                average_vacuum_probability=0.0,
                average_vacuum_size_bps=0.0,
                average_wall_distance=0.0,
                average_gap_score=0.0,
                average_confidence=0.0,
                current_state="NORMAL",
                current_direction="NONE",
            )
        
        # Direction counts
        up = len([r for r in history if r.vacuum_direction == "UP"])
        down = len([r for r in history if r.vacuum_direction == "DOWN"])
        none = len([r for r in history if r.vacuum_direction == "NONE"])
        
        # State counts
        normal = len([r for r in history if r.liquidity_state == "NORMAL"])
        thin = len([r for r in history if r.liquidity_state == "THIN_ZONE"])
        vacuum = len([r for r in history if r.liquidity_state == "VACUUM"])
        
        # Averages
        avg_prob = sum(r.vacuum_probability for r in history) / len(history)
        avg_size = sum(r.vacuum_size_bps for r in history) / len(history)
        avg_wall = sum(r.nearest_liquidity_wall_distance for r in history) / len(history)
        avg_gap = sum(r.orderbook_gap_score for r in history) / len(history)
        avg_conf = sum(r.confidence for r in history) / len(history)
        
        return LiquidityVacuumSummary(
            symbol=symbol,
            total_records=len(history),
            up_count=up,
            down_count=down,
            none_count=none,
            normal_count=normal,
            thin_zone_count=thin,
            vacuum_count=vacuum,
            average_vacuum_probability=round(avg_prob, 4),
            average_vacuum_size_bps=round(avg_size, 2),
            average_wall_distance=round(avg_wall, 2),
            average_gap_score=round(avg_gap, 2),
            average_confidence=round(avg_conf, 4),
            current_state=history[0].liquidity_state,
            current_direction=history[0].vacuum_direction,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear vacuum history (for testing)."""
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


# Singleton
_registry: Optional[LiquidityVacuumRegistry] = None


def get_liquidity_vacuum_registry() -> LiquidityVacuumRegistry:
    """Get singleton instance of LiquidityVacuumRegistry."""
    global _registry
    if _registry is None:
        _registry = LiquidityVacuumRegistry()
    return _registry
