"""
Reflexivity Registry

PHASE 35 — Market Reflexivity Engine

MongoDB persistence layer for reflexivity states.

Collections:
- market_reflexivity_states: Historical reflexivity snapshots
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .reflexivity_types import (
    ReflexivityState,
    ReflexivityHistory,
    ReflexivitySummary,
)


# ══════════════════════════════════════════════════════════════
# Reflexivity Registry
# ══════════════════════════════════════════════════════════════

class ReflexivityRegistry:
    """
    MongoDB registry for reflexivity states.
    
    Provides persistence and query capabilities.
    """
    
    COLLECTION_NAME = "market_reflexivity_states"
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Get database connection."""
        if self._db is None:
            try:
                from core.database import get_database
                self._db = get_database()
            except Exception:
                pass
        return self._db
    
    @property
    def collection(self):
        """Get collection."""
        if self.db is None:
            return None
        return self.db[self.COLLECTION_NAME]
    
    # ═══════════════════════════════════════════════════════════
    # 1. Write Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_state(self, state: ReflexivityState) -> bool:
        """Save reflexivity state to MongoDB."""
        if self.collection is None:
            return False
        
        try:
            doc = {
                "symbol": state.symbol,
                "sentiment_state": state.sentiment_state,
                "crowd_positioning": state.crowd_positioning,
                "reflexivity_score": state.reflexivity_score,
                "feedback_direction": state.feedback_direction,
                "strength": state.strength,
                "confidence": state.confidence,
                "sentiment_score": state.sentiment_score,
                "positioning_score": state.positioning_score,
                "trend_acceleration_score": state.trend_acceleration_score,
                "volatility_expansion_score": state.volatility_expansion_score,
                "reason": state.reason,
                "recorded_at": state.timestamp,
            }
            
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[ReflexivityRegistry] Save error: {e}")
            return False
    
    def save_states_batch(self, states: List[ReflexivityState]) -> int:
        """Save multiple states in batch."""
        if self.collection is None or not states:
            return 0
        
        try:
            docs = []
            for state in states:
                docs.append({
                    "symbol": state.symbol,
                    "sentiment_state": state.sentiment_state,
                    "crowd_positioning": state.crowd_positioning,
                    "reflexivity_score": state.reflexivity_score,
                    "feedback_direction": state.feedback_direction,
                    "strength": state.strength,
                    "confidence": state.confidence,
                    "sentiment_score": state.sentiment_score,
                    "positioning_score": state.positioning_score,
                    "trend_acceleration_score": state.trend_acceleration_score,
                    "volatility_expansion_score": state.volatility_expansion_score,
                    "reason": state.reason,
                    "recorded_at": state.timestamp,
                })
            
            result = self.collection.insert_many(docs)
            return len(result.inserted_ids)
        except Exception as e:
            print(f"[ReflexivityRegistry] Batch save error: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════
    # 2. Read Operations
    # ═══════════════════════════════════════════════════════════
    
    def get_latest_state(self, symbol: str) -> Optional[ReflexivityState]:
        """Get most recent reflexivity state for symbol."""
        if self.collection is None:
            return None
        
        try:
            doc = self.collection.find_one(
                {"symbol": symbol.upper()},
                {"_id": 0},
                sort=[("recorded_at", -1)]
            )
            
            if doc:
                return self._doc_to_state(doc)
            return None
        except Exception as e:
            print(f"[ReflexivityRegistry] Get latest error: {e}")
            return None
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
        hours_back: Optional[int] = None,
    ) -> List[ReflexivityHistory]:
        """Get historical reflexivity records."""
        if self.collection is None:
            return []
        
        try:
            query = {"symbol": symbol.upper()}
            
            if hours_back:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                query["recorded_at"] = {"$gte": cutoff}
            
            docs = list(self.collection.find(
                query,
                {"_id": 0}
            ).sort("recorded_at", -1).limit(limit))
            
            return [self._doc_to_history(d) for d in docs]
        except Exception as e:
            print(f"[ReflexivityRegistry] Get history error: {e}")
            return []
    
    def get_by_direction(
        self,
        symbol: str,
        direction: str,
        limit: int = 50,
    ) -> List[ReflexivityHistory]:
        """Get records by feedback direction."""
        if self.collection is None:
            return []
        
        try:
            docs = list(self.collection.find(
                {"symbol": symbol.upper(), "feedback_direction": direction},
                {"_id": 0}
            ).sort("recorded_at", -1).limit(limit))
            
            return [self._doc_to_history(d) for d in docs]
        except Exception as e:
            print(f"[ReflexivityRegistry] Get by direction error: {e}")
            return []
    
    def get_by_strength(
        self,
        symbol: str,
        strength: str,
        limit: int = 50,
    ) -> List[ReflexivityHistory]:
        """Get records by strength level."""
        if self.collection is None:
            return []
        
        try:
            docs = list(self.collection.find(
                {"symbol": symbol.upper(), "strength": strength},
                {"_id": 0}
            ).sort("recorded_at", -1).limit(limit))
            
            return [self._doc_to_history(d) for d in docs]
        except Exception as e:
            print(f"[ReflexivityRegistry] Get by strength error: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════
    # 3. Aggregation Operations
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> Optional[ReflexivitySummary]:
        """Get aggregated summary for symbol."""
        if self.collection is None:
            return None
        
        try:
            symbol = symbol.upper()
            
            # Get total count
            total = self.collection.count_documents({"symbol": symbol})
            if total == 0:
                return ReflexivitySummary(symbol=symbol)
            
            # Get latest
            latest = self.get_latest_state(symbol)
            
            # Aggregation pipeline for stats
            pipeline = [
                {"$match": {"symbol": symbol}},
                {"$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$reflexivity_score"},
                    "positive_count": {
                        "$sum": {"$cond": [{"$eq": ["$feedback_direction", "POSITIVE"]}, 1, 0]}
                    },
                    "negative_count": {
                        "$sum": {"$cond": [{"$eq": ["$feedback_direction", "NEGATIVE"]}, 1, 0]}
                    },
                    "strong_count": {
                        "$sum": {"$cond": [{"$eq": ["$strength", "STRONG"]}, 1, 0]}
                    },
                    "moderate_count": {
                        "$sum": {"$cond": [{"$eq": ["$strength", "MODERATE"]}, 1, 0]}
                    },
                }}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            if not results:
                return ReflexivitySummary(symbol=symbol)
            
            stats = results[0]
            
            # Recent average
            recent_docs = list(self.collection.find(
                {"symbol": symbol},
                {"reflexivity_score": 1}
            ).sort("recorded_at", -1).limit(24))
            
            recent_avg = sum(d.get("reflexivity_score", 0) for d in recent_docs) / len(recent_docs) if recent_docs else 0.0
            
            return ReflexivitySummary(
                symbol=symbol,
                current_score=latest.reflexivity_score if latest else 0.0,
                current_direction=latest.feedback_direction if latest else "NEUTRAL",
                current_strength=latest.strength if latest else "WEAK",
                total_records=total,
                avg_score=round(stats.get("avg_score", 0), 4),
                positive_feedback_count=stats.get("positive_count", 0),
                negative_feedback_count=stats.get("negative_count", 0),
                neutral_count=total - stats.get("positive_count", 0) - stats.get("negative_count", 0),
                strong_reflexivity_count=stats.get("strong_count", 0),
                moderate_reflexivity_count=stats.get("moderate_count", 0),
                weak_reflexivity_count=total - stats.get("strong_count", 0) - stats.get("moderate_count", 0),
                recent_avg_score=round(recent_avg, 4),
                last_updated=datetime.now(timezone.utc),
            )
        except Exception as e:
            print(f"[ReflexivityRegistry] Get summary error: {e}")
            return ReflexivitySummary(symbol=symbol)
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols with reflexivity data."""
        if self.collection is None:
            return []
        
        try:
            return self.collection.distinct("symbol")
        except Exception:
            return []
    
    # ═══════════════════════════════════════════════════════════
    # 4. Maintenance Operations
    # ═══════════════════════════════════════════════════════════
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """Remove records older than specified days."""
        if self.collection is None:
            return 0
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            result = self.collection.delete_many({"recorded_at": {"$lt": cutoff}})
            return result.deleted_count
        except Exception as e:
            print(f"[ReflexivityRegistry] Cleanup error: {e}")
            return 0
    
    def ensure_indexes(self) -> bool:
        """Create indexes for efficient queries."""
        if self.collection is None:
            return False
        
        try:
            self.collection.create_index([("symbol", 1), ("recorded_at", -1)])
            self.collection.create_index([("symbol", 1), ("feedback_direction", 1)])
            self.collection.create_index([("symbol", 1), ("strength", 1)])
            return True
        except Exception as e:
            print(f"[ReflexivityRegistry] Index error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════
    # 5. Conversion Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _doc_to_state(self, doc: dict) -> ReflexivityState:
        """Convert MongoDB document to ReflexivityState."""
        return ReflexivityState(
            symbol=doc.get("symbol", ""),
            sentiment_state=doc.get("sentiment_state", "NEUTRAL"),
            crowd_positioning=doc.get("crowd_positioning", 0.0),
            reflexivity_score=doc.get("reflexivity_score", 0.0),
            feedback_direction=doc.get("feedback_direction", "NEUTRAL"),
            strength=doc.get("strength", "WEAK"),
            confidence=doc.get("confidence", 0.0),
            sentiment_score=doc.get("sentiment_score", 0.0),
            positioning_score=doc.get("positioning_score", 0.0),
            trend_acceleration_score=doc.get("trend_acceleration_score", 0.0),
            volatility_expansion_score=doc.get("volatility_expansion_score", 0.0),
            reason=doc.get("reason", ""),
            timestamp=doc.get("recorded_at", datetime.now(timezone.utc)),
        )
    
    def _doc_to_history(self, doc: dict) -> ReflexivityHistory:
        """Convert MongoDB document to ReflexivityHistory."""
        return ReflexivityHistory(
            symbol=doc.get("symbol", ""),
            reflexivity_score=doc.get("reflexivity_score", 0.0),
            feedback_direction=doc.get("feedback_direction", "NEUTRAL"),
            sentiment_state=doc.get("sentiment_state", "NEUTRAL"),
            crowd_positioning=doc.get("crowd_positioning", 0.0),
            confidence=doc.get("confidence", 0.0),
            recorded_at=doc.get("recorded_at", datetime.now(timezone.utc)),
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_reflexivity_registry: Optional[ReflexivityRegistry] = None


def get_reflexivity_registry() -> ReflexivityRegistry:
    """Get singleton instance of ReflexivityRegistry."""
    global _reflexivity_registry
    if _reflexivity_registry is None:
        _reflexivity_registry = ReflexivityRegistry()
    return _reflexivity_registry
