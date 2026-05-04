"""
Regime Transition Detector — Registry

Storage for transition history in MongoDB.

Collection: regime_transition_history
"""

from typing import List, Optional, Dict
from datetime import datetime
import os
from collections import Counter

from motor.motor_asyncio import AsyncIOMotorClient

from .regime_transition_types import (
    RegimeTransitionState,
    TransitionHistoryRecord,
    TransitionSummary,
)


class RegimeTransitionRegistry:
    """
    Registry for storing transition history.
    
    Collection: regime_transition_history
    """
    
    COLLECTION = "regime_transition_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[TransitionHistoryRecord] = []
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
    
    async def store_transition(
        self,
        transition: RegimeTransitionState,
    ) -> TransitionHistoryRecord:
        """Store transition in history."""
        record = TransitionHistoryRecord(
            current_regime=transition.current_regime,
            next_regime_candidate=transition.next_regime_candidate,
            transition_probability=transition.transition_probability,
            transition_state=transition.transition_state,
            trigger_factors=transition.trigger_factors,
            symbol=transition.symbol,
            timeframe=transition.timeframe,
            recorded_at=datetime.utcnow(),
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
    ) -> List[TransitionHistoryRecord]:
        """Get transition history for symbol/timeframe."""
        if self._use_cache:
            history = [
                r for r in self._cache
                if r.symbol == symbol and r.timeframe == timeframe
            ]
            return sorted(history, key=lambda r: r.recorded_at, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"symbol": symbol, "timeframe": timeframe}
        ).sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(TransitionHistoryRecord(**doc))
        
        return results
    
    async def get_all_history(
        self,
        limit: int = 500,
    ) -> List[TransitionHistoryRecord]:
        """Get all transition history."""
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
            results.append(TransitionHistoryRecord(**doc))
        
        return results
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> TransitionSummary:
        """Get transition summary statistics."""
        history = await self.get_history(symbol, timeframe, limit=100)
        
        if not history:
            return TransitionSummary(
                total_records=0,
                stable_count=0,
                early_shift_count=0,
                active_transition_count=0,
                unstable_count=0,
                current_state="STABLE",
                average_probability=0.0,
                most_common_trigger="none",
                transition_frequency=0.0,
            )
        
        # Count by state
        stable = len([r for r in history if r.transition_state == "STABLE"])
        early_shift = len([r for r in history if r.transition_state == "EARLY_SHIFT"])
        active_trans = len([r for r in history if r.transition_state == "ACTIVE_TRANSITION"])
        unstable = len([r for r in history if r.transition_state == "UNSTABLE"])
        
        # Current state
        current = history[0].transition_state if history else "STABLE"
        
        # Average probability
        avg_prob = sum(r.transition_probability for r in history) / len(history)
        
        # Most common trigger
        all_triggers = []
        for r in history:
            all_triggers.extend(r.trigger_factors)
        
        if all_triggers:
            trigger_counts = Counter(all_triggers)
            most_common = trigger_counts.most_common(1)[0][0]
        else:
            most_common = "none"
        
        # Transition frequency (how often not STABLE)
        non_stable = early_shift + active_trans + unstable
        frequency = non_stable / len(history) if history else 0.0
        
        return TransitionSummary(
            total_records=len(history),
            stable_count=stable,
            early_shift_count=early_shift,
            active_transition_count=active_trans,
            unstable_count=unstable,
            current_state=current,
            average_probability=round(avg_prob, 4),
            most_common_trigger=most_common,
            transition_frequency=round(frequency, 4),
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self) -> None:
        """Clear all transition history (for testing)."""
        if self._use_cache:
            self._cache.clear()
        else:
            db = await self._get_db()
            if db:
                await db[self.COLLECTION].delete_many({})


# Singleton
_registry: Optional[RegimeTransitionRegistry] = None


def get_regime_transition_registry() -> RegimeTransitionRegistry:
    """Get singleton instance of RegimeTransitionRegistry."""
    global _registry
    if _registry is None:
        _registry = RegimeTransitionRegistry()
    return _registry
