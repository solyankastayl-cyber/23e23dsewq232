"""
Liquidation Cascade Probability — Registry

PHASE 28.4 — Storage for liquidation cascade history in MongoDB.

Collection: liquidation_cascade_history
"""

from typing import List, Optional
from datetime import datetime
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from .liquidation_cascade_types import (
    LiquidationCascadeState,
    LiquidationCascadeHistoryRecord,
    LiquidationCascadeSummary,
)


class LiquidationCascadeRegistry:
    """
    Registry for storing liquidation cascade history.
    
    Collection: liquidation_cascade_history
    """
    
    COLLECTION = "liquidation_cascade_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[LiquidationCascadeHistoryRecord] = []
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
    
    async def store_cascade_state(
        self,
        state: LiquidationCascadeState,
    ) -> LiquidationCascadeHistoryRecord:
        """Store cascade state in history."""
        record = LiquidationCascadeHistoryRecord(
            symbol=state.symbol,
            cascade_direction=state.cascade_direction,
            cascade_probability=state.cascade_probability,
            liquidation_pressure=state.liquidation_pressure,
            vacuum_probability=state.vacuum_probability,
            sweep_probability=state.sweep_probability,
            cascade_severity=state.cascade_severity,
            cascade_state=state.cascade_state,
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
    ) -> List[LiquidationCascadeHistoryRecord]:
        """Get cascade history for symbol."""
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
            results.append(LiquidationCascadeHistoryRecord(**doc))
        
        return results
    
    async def get_latest(
        self,
        symbol: str,
    ) -> Optional[LiquidationCascadeHistoryRecord]:
        """Get most recent cascade state for symbol."""
        history = await self.get_history(symbol, limit=1)
        return history[0] if history else None
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(
        self,
        symbol: str,
    ) -> LiquidationCascadeSummary:
        """Get summary statistics for symbol."""
        history = await self.get_history(symbol, limit=100)
        
        if not history:
            return LiquidationCascadeSummary(
                symbol=symbol,
                total_records=0,
                up_count=0,
                down_count=0,
                none_count=0,
                low_count=0,
                medium_count=0,
                high_count=0,
                extreme_count=0,
                stable_count=0,
                building_count=0,
                active_count=0,
                critical_count=0,
                average_cascade_probability=0.0,
                average_liquidation_pressure=0.0,
                average_vacuum_probability=0.0,
                average_sweep_probability=0.0,
                average_confidence=0.0,
                current_state="STABLE",
                current_direction="NONE",
                current_severity="LOW",
            )
        
        # Direction counts
        up = len([r for r in history if r.cascade_direction == "UP"])
        down = len([r for r in history if r.cascade_direction == "DOWN"])
        none = len([r for r in history if r.cascade_direction == "NONE"])
        
        # Severity counts
        low = len([r for r in history if r.cascade_severity == "LOW"])
        medium = len([r for r in history if r.cascade_severity == "MEDIUM"])
        high = len([r for r in history if r.cascade_severity == "HIGH"])
        extreme = len([r for r in history if r.cascade_severity == "EXTREME"])
        
        # State counts
        stable = len([r for r in history if r.cascade_state == "STABLE"])
        building = len([r for r in history if r.cascade_state == "BUILDING"])
        active = len([r for r in history if r.cascade_state == "ACTIVE"])
        critical = len([r for r in history if r.cascade_state == "CRITICAL"])
        
        # Averages
        avg_prob = sum(r.cascade_probability for r in history) / len(history)
        avg_liq = sum(r.liquidation_pressure for r in history) / len(history)
        avg_vac = sum(r.vacuum_probability for r in history) / len(history)
        avg_sweep = sum(r.sweep_probability for r in history) / len(history)
        avg_conf = sum(r.confidence for r in history) / len(history)
        
        return LiquidationCascadeSummary(
            symbol=symbol,
            total_records=len(history),
            up_count=up,
            down_count=down,
            none_count=none,
            low_count=low,
            medium_count=medium,
            high_count=high,
            extreme_count=extreme,
            stable_count=stable,
            building_count=building,
            active_count=active,
            critical_count=critical,
            average_cascade_probability=round(avg_prob, 4),
            average_liquidation_pressure=round(avg_liq, 4),
            average_vacuum_probability=round(avg_vac, 4),
            average_sweep_probability=round(avg_sweep, 4),
            average_confidence=round(avg_conf, 4),
            current_state=history[0].cascade_state,
            current_direction=history[0].cascade_direction,
            current_severity=history[0].cascade_severity,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear cascade history (for testing)."""
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
_registry: Optional[LiquidationCascadeRegistry] = None


def get_liquidation_cascade_registry() -> LiquidationCascadeRegistry:
    """Get singleton instance of LiquidationCascadeRegistry."""
    global _registry
    if _registry is None:
        _registry = LiquidationCascadeRegistry()
    return _registry
