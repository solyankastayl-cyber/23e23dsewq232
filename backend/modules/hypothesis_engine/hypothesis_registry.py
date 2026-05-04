"""
Hypothesis Engine — Registry

PHASE 29.1 — Initial storage for market hypothesis history
PHASE 29.4 — Full Registry Engine with persistent storage, stats, and analytics

Collections:
- market_hypothesis_history: Main hypothesis storage
- market_hypothesis_outcomes: For future accuracy tracking (structure prepared)

This transforms Hypothesis Engine from signal generator into market learning system.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import os

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from .hypothesis_types import (
    MarketHypothesis,
    HypothesisHistoryRecord,
    HypothesisSummary,
)


# ══════════════════════════════════════════════════════════════
# PHASE 29.4 — Extended Types
# ══════════════════════════════════════════════════════════════

class HypothesisHistoryRecordExtended(BaseModel):
    """
    Extended history record with all PHASE 29.2/29.3 fields.
    """
    symbol: str
    hypothesis_type: str
    directional_bias: str
    
    # PHASE 29.2 scores
    structural_score: float = 0.0
    execution_score: float = 0.0
    conflict_score: float = 0.0
    
    # PHASE 29.3 conflict state
    conflict_state: str = "LOW_CONFLICT"
    
    confidence: float
    reliability: float
    execution_state: str
    
    # PHASE 29.4 — Price tracking for future outcome analysis
    price_at_creation: Optional[float] = None
    
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HypothesisStats(BaseModel):
    """
    Statistics for hypothesis history.
    """
    symbol: str
    total_hypotheses: int
    
    # Directional breakdown
    bullish: int = 0
    bearish: int = 0
    neutral: int = 0
    
    # Type breakdown
    bullish_continuation: int = 0
    bearish_continuation: int = 0
    breakout_forming: int = 0
    range_mean_reversion: int = 0
    no_edge: int = 0
    
    # Conflict breakdown
    low_conflict: int = 0
    moderate_conflict: int = 0
    high_conflict: int = 0
    
    # Execution state breakdown
    favorable: int = 0
    cautious: int = 0
    unfavorable: int = 0
    
    # Averages
    avg_confidence: float = 0.0
    avg_reliability: float = 0.0
    avg_structural_score: float = 0.0
    avg_execution_score: float = 0.0
    avg_conflict_score: float = 0.0
    
    # Recent trend
    recent_bias_trend: str = "NEUTRAL"


class HypothesisOutcome(BaseModel):
    """
    Outcome record for hypothesis accuracy tracking (PHASE 29.4 structure).
    Full implementation in future phase.
    """
    symbol: str
    hypothesis_id: str
    
    price_at_creation: float
    price_after_5m: Optional[float] = None
    price_after_15m: Optional[float] = None
    price_after_1h: Optional[float] = None
    price_after_4h: Optional[float] = None
    
    outcome_direction: str = "PENDING"  # CORRECT, INCORRECT, NEUTRAL, PENDING
    outcome_strength: float = 0.0
    
    evaluated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Hypothesis Registry — PHASE 29.4
# ══════════════════════════════════════════════════════════════

class HypothesisRegistry:
    """
    Registry for storing and analyzing market hypothesis history.
    
    PHASE 29.4 Features:
    - Full hypothesis storage with all scores
    - Price tracking for future outcome analysis
    - Statistics and analytics
    - Recent hypotheses across all symbols
    
    Collections:
    - market_hypothesis_history
    - market_hypothesis_outcomes (structure prepared)
    """

    COLLECTION = "market_hypothesis_history"
    OUTCOMES_COLLECTION = "market_hypothesis_outcomes"

    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[HypothesisHistoryRecordExtended] = []
        self._use_cache = False if db is not None else None

    async def _get_db(self):
        """Get or create database connection."""
        # If explicitly set to use cache, don't connect to DB
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

    async def store_hypothesis(
        self,
        hypothesis: MarketHypothesis,
        price_at_creation: Optional[float] = None,
    ) -> HypothesisHistoryRecordExtended:
        """
        Store hypothesis in history with all PHASE 29.2/29.3 fields.
        
        Args:
            hypothesis: MarketHypothesis to store
            price_at_creation: Current market price (for future outcome tracking)
        
        Returns:
            Extended history record
        """
        # Try to get current price from market data if not provided
        if price_at_creation is None:
            price_at_creation = await self._get_current_price(hypothesis.symbol)
        
        record = HypothesisHistoryRecordExtended(
            symbol=hypothesis.symbol,
            hypothesis_type=hypothesis.hypothesis_type,
            directional_bias=hypothesis.directional_bias,
            # PHASE 29.2 scores
            structural_score=hypothesis.structural_score,
            execution_score=hypothesis.execution_score,
            conflict_score=hypothesis.conflict_score,
            # PHASE 29.3 conflict state
            conflict_state=hypothesis.conflict_state,
            # Core scores
            confidence=hypothesis.confidence,
            reliability=hypothesis.reliability,
            execution_state=hypothesis.execution_state,
            # Price tracking
            price_at_creation=price_at_creation,
            reason=hypothesis.reason,
            created_at=datetime.now(timezone.utc),
        )

        db = await self._get_db()
        if self._use_cache:
            self._cache.append(record)
        else:
            if db is not None:
                await db[self.COLLECTION].insert_one(record.model_dump())

        return record

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Try to get current price from market data or candles."""
        try:
            db = await self._get_db()
            if db is None:
                return None
            
            # Try to get latest candle
            candle = await db["candles"].find_one(
                {"symbol": symbol},
                sort=[("timestamp", -1)]
            )
            if candle:
                return candle.get("close")
            
            return None
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════
    # Read Operations — History
    # ═══════════════════════════════════════════════════════════

    async def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[HypothesisHistoryRecordExtended]:
        """
        Get hypothesis history for symbol.
        
        Returns most recent hypotheses first.
        """
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
            results.append(HypothesisHistoryRecordExtended(**doc))

        return results

    async def get_symbol_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[HypothesisHistoryRecordExtended]:
        """Alias for get_history — more explicit naming."""
        return await self.get_history(symbol, limit)

    async def get_latest(
        self,
        symbol: str,
    ) -> Optional[HypothesisHistoryRecordExtended]:
        """Get most recent hypothesis for symbol."""
        history = await self.get_history(symbol, limit=1)
        return history[0] if history else None

    async def get_recent_hypotheses(
        self,
        limit: int = 100,
    ) -> List[HypothesisHistoryRecordExtended]:
        """
        Get recent hypotheses across ALL symbols.
        
        Useful for system-wide monitoring.
        """
        db = await self._get_db()
        if self._use_cache:
            sorted_cache = sorted(
                self._cache,
                key=lambda r: r.created_at,
                reverse=True
            )
            return sorted_cache[:limit]

        if db is None:
            return []

        cursor = db[self.COLLECTION].find().sort("created_at", -1).limit(limit)

        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(HypothesisHistoryRecordExtended(**doc))

        return results

    # ═══════════════════════════════════════════════════════════
    # Read Operations — Statistics
    # ═══════════════════════════════════════════════════════════

    async def get_hypothesis_stats(
        self,
        symbol: str,
        limit: int = 500,
    ) -> HypothesisStats:
        """
        Get comprehensive statistics for symbol.
        
        Analyzes hypothesis history and returns aggregated stats.
        """
        history = await self.get_history(symbol, limit=limit)

        if not history:
            return HypothesisStats(
                symbol=symbol,
                total_hypotheses=0,
            )

        # Directional breakdown
        bullish = len([r for r in history if r.directional_bias == "LONG"])
        bearish = len([r for r in history if r.directional_bias == "SHORT"])
        neutral = len([r for r in history if r.directional_bias == "NEUTRAL"])

        # Type breakdown
        type_counts = {
            "bullish_continuation": 0,
            "bearish_continuation": 0,
            "breakout_forming": 0,
            "range_mean_reversion": 0,
            "no_edge": 0,
        }
        type_mapping = {
            "BULLISH_CONTINUATION": "bullish_continuation",
            "BEARISH_CONTINUATION": "bearish_continuation",
            "BREAKOUT_FORMING": "breakout_forming",
            "RANGE_MEAN_REVERSION": "range_mean_reversion",
            "NO_EDGE": "no_edge",
        }
        for r in history:
            key = type_mapping.get(r.hypothesis_type)
            if key:
                type_counts[key] += 1

        # Conflict breakdown
        low_conflict = len([r for r in history if r.conflict_state == "LOW_CONFLICT"])
        moderate_conflict = len([r for r in history if r.conflict_state == "MODERATE_CONFLICT"])
        high_conflict = len([r for r in history if r.conflict_state == "HIGH_CONFLICT"])

        # Execution state breakdown
        favorable = len([r for r in history if r.execution_state == "FAVORABLE"])
        cautious = len([r for r in history if r.execution_state == "CAUTIOUS"])
        unfavorable = len([r for r in history if r.execution_state == "UNFAVORABLE"])

        # Averages
        avg_confidence = sum(r.confidence for r in history) / len(history)
        avg_reliability = sum(r.reliability for r in history) / len(history)
        avg_structural = sum(r.structural_score for r in history) / len(history)
        avg_execution = sum(r.execution_score for r in history) / len(history)
        avg_conflict = sum(r.conflict_score for r in history) / len(history)

        # Recent trend (last 10)
        recent = history[:10]
        recent_bullish = len([r for r in recent if r.directional_bias == "LONG"])
        recent_bearish = len([r for r in recent if r.directional_bias == "SHORT"])
        
        if recent_bullish > recent_bearish + 2:
            recent_trend = "BULLISH"
        elif recent_bearish > recent_bullish + 2:
            recent_trend = "BEARISH"
        else:
            recent_trend = "NEUTRAL"

        return HypothesisStats(
            symbol=symbol,
            total_hypotheses=len(history),
            bullish=bullish,
            bearish=bearish,
            neutral=neutral,
            bullish_continuation=type_counts["bullish_continuation"],
            bearish_continuation=type_counts["bearish_continuation"],
            breakout_forming=type_counts["breakout_forming"],
            range_mean_reversion=type_counts["range_mean_reversion"],
            no_edge=type_counts["no_edge"],
            low_conflict=low_conflict,
            moderate_conflict=moderate_conflict,
            high_conflict=high_conflict,
            favorable=favorable,
            cautious=cautious,
            unfavorable=unfavorable,
            avg_confidence=round(avg_confidence, 4),
            avg_reliability=round(avg_reliability, 4),
            avg_structural_score=round(avg_structural, 4),
            avg_execution_score=round(avg_execution, 4),
            avg_conflict_score=round(avg_conflict, 4),
            recent_bias_trend=recent_trend,
        )

    # ═══════════════════════════════════════════════════════════
    # Legacy Summary (for backward compatibility)
    # ═══════════════════════════════════════════════════════════

    async def get_summary(
        self,
        symbol: str,
    ) -> HypothesisSummary:
        """Get summary statistics for symbol (legacy format)."""
        history = await self.get_history(symbol, limit=100)

        if not history:
            return HypothesisSummary(
                symbol=symbol,
                total_records=0,
            )

        # Type counts
        type_map = {
            "BULLISH_CONTINUATION": 0,
            "BEARISH_CONTINUATION": 0,
            "BREAKOUT_FORMING": 0,
            "RANGE_MEAN_REVERSION": 0,
            "NO_EDGE": 0,
        }
        other_count = 0
        for r in history:
            if r.hypothesis_type in type_map:
                type_map[r.hypothesis_type] += 1
            else:
                other_count += 1

        # Bias counts
        long_c = len([r for r in history if r.directional_bias == "LONG"])
        short_c = len([r for r in history if r.directional_bias == "SHORT"])
        neutral_c = len([r for r in history if r.directional_bias == "NEUTRAL"])

        # Execution state counts
        favorable_c = len([r for r in history if r.execution_state == "FAVORABLE"])
        cautious_c = len([r for r in history if r.execution_state == "CAUTIOUS"])
        unfavorable_c = len([r for r in history if r.execution_state == "UNFAVORABLE"])

        # Averages
        avg_conf = sum(r.confidence for r in history) / len(history)
        avg_rel = sum(r.reliability for r in history) / len(history)

        return HypothesisSummary(
            symbol=symbol,
            total_records=len(history),
            bullish_continuation_count=type_map["BULLISH_CONTINUATION"],
            bearish_continuation_count=type_map["BEARISH_CONTINUATION"],
            breakout_forming_count=type_map["BREAKOUT_FORMING"],
            range_mean_reversion_count=type_map["RANGE_MEAN_REVERSION"],
            no_edge_count=type_map["NO_EDGE"],
            other_count=other_count,
            long_count=long_c,
            short_count=short_c,
            neutral_count=neutral_c,
            favorable_count=favorable_c,
            cautious_count=cautious_c,
            unfavorable_count=unfavorable_c,
            average_confidence=round(avg_conf, 4),
            average_reliability=round(avg_rel, 4),
            current_hypothesis=history[0].hypothesis_type,
            current_bias=history[0].directional_bias,
        )

    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════

    async def get_all_symbols(self) -> List[str]:
        """Get list of all symbols with hypothesis history."""
        db = await self._get_db()
        if self._use_cache:
            return list(set(r.symbol for r in self._cache))
        
        if db is None:
            return []
        
        symbols = await db[self.COLLECTION].distinct("symbol")
        return symbols

    async def get_total_count(self, symbol: Optional[str] = None) -> int:
        """Get total count of hypotheses."""
        db = await self._get_db()
        if self._use_cache:
            if symbol:
                return len([r for r in self._cache if r.symbol == symbol])
            return len(self._cache)
        
        if db is None:
            return 0
        
        query = {"symbol": symbol} if symbol else {}
        return await db[self.COLLECTION].count_documents(query)

    async def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear hypothesis history (for testing)."""
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

    async def ensure_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        db = await self._get_db()
        if db is not None:
            await db[self.COLLECTION].create_index([("symbol", 1), ("created_at", -1)])
            await db[self.COLLECTION].create_index([("created_at", -1)])
            await db[self.COLLECTION].create_index([("hypothesis_type", 1)])


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[HypothesisRegistry] = None


def get_hypothesis_registry() -> HypothesisRegistry:
    """Get singleton instance of HypothesisRegistry."""
    global _registry
    if _registry is None:
        _registry = HypothesisRegistry()
    return _registry
