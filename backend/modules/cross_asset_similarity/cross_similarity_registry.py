"""
Cross-Asset Similarity Registry

PHASE 32.4 — MongoDB persistence for cross-asset similarity data.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import get_database

from .cross_similarity_types import (
    CrossAssetMatch,
    CrossAssetAnalysis,
    CrossAssetSummary,
    ASSET_UNIVERSE,
)


# ══════════════════════════════════════════════════════════════
# Collection Names
# ══════════════════════════════════════════════════════════════

MATCHES_COLLECTION = "cross_asset_similarity_patterns"
ANALYSES_COLLECTION = "cross_asset_analyses"


# ══════════════════════════════════════════════════════════════
# Cross-Asset Similarity Registry
# ══════════════════════════════════════════════════════════════

class CrossAssetSimilarityRegistry:
    """
    MongoDB registry for cross-asset similarity data.
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
    def matches_collection(self):
        """Get matches collection."""
        return self.db[MATCHES_COLLECTION]
    
    @property
    def analyses_collection(self):
        """Get analyses collection."""
        return self.db[ANALYSES_COLLECTION]
    
    # ═══════════════════════════════════════════════════════════
    # Match Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_match(self, match: CrossAssetMatch) -> str:
        """Save cross-asset match to database."""
        doc = match.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        doc.pop("_id", None)
        
        result = self.matches_collection.insert_one(doc)
        return match.match_id
    
    def save_matches(self, matches: List[CrossAssetMatch]) -> int:
        """Save multiple matches."""
        if not matches:
            return 0
        
        docs = []
        for m in matches:
            doc = m.model_dump()
            doc["created_at"] = datetime.now(timezone.utc)
            doc.pop("_id", None)
            docs.append(doc)
        
        result = self.matches_collection.insert_many(docs)
        return len(result.inserted_ids)
    
    def get_matches_for_symbol(
        self,
        symbol: str,
        limit: int = 20,
    ) -> List[CrossAssetMatch]:
        """Get matches for a source symbol."""
        docs = self.matches_collection.find(
            {"source_symbol": symbol.upper()},
            {"_id": 0}
        ).sort("confidence", -1).limit(limit)
        
        return [CrossAssetMatch(**doc) for doc in docs]
    
    def get_matches_by_reference(
        self,
        source_symbol: str,
        reference_symbol: str,
        limit: int = 10,
    ) -> List[CrossAssetMatch]:
        """Get matches between specific asset pairs."""
        docs = self.matches_collection.find(
            {
                "source_symbol": source_symbol.upper(),
                "reference_symbol": reference_symbol.upper()
            },
            {"_id": 0}
        ).sort("confidence", -1).limit(limit)
        
        return [CrossAssetMatch(**doc) for doc in docs]
    
    # ═══════════════════════════════════════════════════════════
    # Analysis Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_analysis(self, analysis: CrossAssetAnalysis) -> str:
        """Save analysis to database."""
        doc = analysis.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        
        # Convert nested models
        if analysis.current_vector:
            doc["current_vector"] = analysis.current_vector.model_dump()
        doc["matches"] = [m.model_dump() for m in analysis.matches]
        if analysis.top_match:
            doc["top_match"] = analysis.top_match.model_dump()
        
        doc.pop("_id", None)
        
        result = self.analyses_collection.insert_one(doc)
        return str(result.inserted_id)
    
    def get_latest_analysis(
        self,
        symbol: str,
    ) -> Optional[CrossAssetAnalysis]:
        """Get latest analysis for symbol."""
        doc = self.analyses_collection.find_one(
            {"symbol": symbol.upper()},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if doc:
            return CrossAssetAnalysis(**doc)
        return None
    
    def get_analysis_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[CrossAssetAnalysis]:
        """Get analysis history."""
        docs = self.analyses_collection.find(
            {"symbol": symbol.upper()},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return [CrossAssetAnalysis(**doc) for doc in docs]
    
    def get_cross_asset_stats(self, symbol: str) -> Dict:
        """Get cross-asset statistics."""
        pipeline = [
            {"$match": {"symbol": symbol.upper()}},
            {"$unwind": "$matches"},
            {"$group": {
                "_id": "$matches.reference_symbol",
                "count": {"$sum": 1},
                "avg_similarity": {"$avg": "$matches.similarity_score"},
                "avg_confidence": {"$avg": "$matches.confidence"},
            }},
            {"$sort": {"avg_confidence": -1}},
        ]
        
        results = list(self.analyses_collection.aggregate(pipeline))
        
        stats = {}
        for r in results:
            stats[r["_id"]] = {
                "matches": r["count"],
                "avg_similarity": round(r["avg_similarity"], 4),
                "avg_confidence": round(r["avg_confidence"], 4),
            }
        
        return stats
    
    # ═══════════════════════════════════════════════════════════
    # Index Management
    # ═══════════════════════════════════════════════════════════
    
    def ensure_indexes(self) -> None:
        """Create indexes for collections."""
        # Matches indexes
        self.matches_collection.create_index([("source_symbol", 1), ("reference_symbol", 1)])
        self.matches_collection.create_index([("confidence", -1)])
        self.matches_collection.create_index([("created_at", -1)])
        self.matches_collection.create_index([("match_id", 1)], unique=True)
        
        # Analyses indexes
        self.analyses_collection.create_index([("symbol", 1)])
        self.analyses_collection.create_index([("created_at", -1)])


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_cross_similarity_registry: Optional[CrossAssetSimilarityRegistry] = None


def get_cross_similarity_registry() -> CrossAssetSimilarityRegistry:
    """Get singleton instance of CrossAssetSimilarityRegistry."""
    global _cross_similarity_registry
    if _cross_similarity_registry is None:
        _cross_similarity_registry = CrossAssetSimilarityRegistry()
    return _cross_similarity_registry
