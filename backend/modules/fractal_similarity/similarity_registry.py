"""
Fractal Similarity Registry

PHASE 32.2 — MongoDB persistence for similarity patterns and analyses.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import get_database

from .similarity_types import (
    HistoricalPattern,
    SimilarityAnalysis,
    SimilarityMatch,
    WINDOW_SIZES,
)


# ══════════════════════════════════════════════════════════════
# Collection Names
# ══════════════════════════════════════════════════════════════

PATTERNS_COLLECTION = "fractal_similarity_patterns"
ANALYSES_COLLECTION = "fractal_similarity_analyses"


# ══════════════════════════════════════════════════════════════
# Similarity Registry
# ══════════════════════════════════════════════════════════════

class SimilarityRegistry:
    """
    MongoDB registry for fractal similarity data.
    """
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Get database connection."""
        if self._db is None:
            self._db = get_database()
        return self._db
    
    @property
    def patterns_collection(self):
        """Get patterns collection."""
        return self.db[PATTERNS_COLLECTION]
    
    @property
    def analyses_collection(self):
        """Get analyses collection."""
        return self.db[ANALYSES_COLLECTION]
    
    # ═══════════════════════════════════════════════════════════
    # Pattern Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_pattern(self, pattern: HistoricalPattern) -> str:
        """Save historical pattern to database."""
        doc = pattern.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        
        # Remove _id if present
        doc.pop("_id", None)
        
        result = self.patterns_collection.insert_one(doc)
        return pattern.pattern_id
    
    def get_patterns(
        self,
        symbol: str,
        window_size: Optional[int] = None,
        limit: int = 100,
    ) -> List[HistoricalPattern]:
        """Get patterns for symbol."""
        query = {"symbol": symbol.upper()}
        
        if window_size:
            query["window_size"] = window_size
        
        docs = self.patterns_collection.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return [HistoricalPattern(**doc) for doc in docs]
    
    def get_pattern_count(self, symbol: str) -> Dict[int, int]:
        """Get pattern count by window size."""
        pipeline = [
            {"$match": {"symbol": symbol.upper()}},
            {"$group": {"_id": "$window_size", "count": {"$sum": 1}}},
        ]
        
        results = list(self.patterns_collection.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results}
    
    def delete_old_patterns(
        self,
        symbol: str,
        keep_count: int = 1000,
    ) -> int:
        """Delete oldest patterns keeping only keep_count."""
        # Get IDs to keep
        keep_docs = list(self.patterns_collection.find(
            {"symbol": symbol.upper()},
            {"pattern_id": 1}
        ).sort("created_at", -1).limit(keep_count))
        
        keep_ids = [d["pattern_id"] for d in keep_docs]
        
        # Delete others
        result = self.patterns_collection.delete_many({
            "symbol": symbol.upper(),
            "pattern_id": {"$nin": keep_ids}
        })
        
        return result.deleted_count
    
    # ═══════════════════════════════════════════════════════════
    # Analysis Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_analysis(self, analysis: SimilarityAnalysis) -> str:
        """Save similarity analysis to database."""
        doc = analysis.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        
        # Convert nested models
        if doc.get("current_vector"):
            doc["current_vector"] = analysis.current_vector.model_dump()
        
        doc["matches"] = [m.model_dump() for m in analysis.matches]
        doc["top_matches"] = [m.model_dump() for m in analysis.top_matches]
        
        # Remove _id if present
        doc.pop("_id", None)
        
        result = self.analyses_collection.insert_one(doc)
        return str(result.inserted_id)
    
    def get_latest_analysis(
        self,
        symbol: str,
    ) -> Optional[SimilarityAnalysis]:
        """Get latest analysis for symbol."""
        doc = self.analyses_collection.find_one(
            {"symbol": symbol.upper()},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if doc:
            return SimilarityAnalysis(**doc)
        return None
    
    def get_analysis_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[SimilarityAnalysis]:
        """Get analysis history for symbol."""
        docs = self.analyses_collection.find(
            {"symbol": symbol.upper()},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return [SimilarityAnalysis(**doc) for doc in docs]
    
    def get_analysis_stats(self, symbol: str) -> Dict:
        """Get analysis statistics for symbol."""
        pipeline = [
            {"$match": {"symbol": symbol.upper()}},
            {"$group": {
                "_id": "$symbol",
                "total_analyses": {"$sum": 1},
                "avg_matches": {"$avg": "$matches_found"},
                "avg_success_rate": {"$avg": "$historical_success_rate"},
                "avg_confidence": {"$avg": "$similarity_confidence"},
                "avg_best_similarity": {"$avg": "$best_similarity"},
            }},
        ]
        
        results = list(self.analyses_collection.aggregate(pipeline))
        
        if results:
            r = results[0]
            return {
                "symbol": symbol.upper(),
                "total_analyses": r.get("total_analyses", 0),
                "avg_matches": round(r.get("avg_matches", 0), 2),
                "avg_success_rate": round(r.get("avg_success_rate", 0), 4),
                "avg_confidence": round(r.get("avg_confidence", 0), 4),
                "avg_best_similarity": round(r.get("avg_best_similarity", 0), 4),
            }
        
        return {
            "symbol": symbol.upper(),
            "total_analyses": 0,
            "avg_matches": 0,
            "avg_success_rate": 0,
            "avg_confidence": 0,
            "avg_best_similarity": 0,
        }
    
    # ═══════════════════════════════════════════════════════════
    # Index Management
    # ═══════════════════════════════════════════════════════════
    
    def ensure_indexes(self) -> None:
        """Create indexes for collections."""
        # Patterns indexes
        self.patterns_collection.create_index([("symbol", 1), ("window_size", 1)])
        self.patterns_collection.create_index([("created_at", -1)])
        self.patterns_collection.create_index([("pattern_id", 1)], unique=True)
        
        # Analyses indexes
        self.analyses_collection.create_index([("symbol", 1)])
        self.analyses_collection.create_index([("created_at", -1)])


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_similarity_registry: Optional[SimilarityRegistry] = None


def get_similarity_registry() -> SimilarityRegistry:
    """Get singleton instance of SimilarityRegistry."""
    global _similarity_registry
    if _similarity_registry is None:
        _similarity_registry = SimilarityRegistry()
    return _similarity_registry
