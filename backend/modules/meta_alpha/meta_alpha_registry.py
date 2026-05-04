"""
Meta-Alpha Registry

PHASE 31.1 — MongoDB persistence for meta-alpha patterns.

Collection: meta_alpha_patterns
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import MongoRepository
from .meta_alpha_types import (
    MetaAlphaPattern,
    MetaAlphaSummary,
    MIN_META_OBSERVATIONS,
    STRONG_META_ALPHA_THRESHOLD,
    MODERATE_META_ALPHA_THRESHOLD,
)


class MetaAlphaRegistry(MongoRepository):
    """
    MongoDB registry for meta-alpha patterns.
    
    Stores pattern history for analysis and backtesting.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "meta_alpha_patterns"
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        if not self.connected:
            return
        
        self._create_index(
            [("symbol", 1), ("pattern_id", 1)],
            collection=self.collection_name,
        )
        self._create_index(
            [("symbol", 1), ("classification", 1)],
            collection=self.collection_name,
        )
        self._create_index(
            [("symbol", 1), ("meta_score", -1)],
            collection=self.collection_name,
        )
    
    def save_pattern(self, symbol: str, pattern: MetaAlphaPattern) -> bool:
        """Save or update meta-alpha pattern."""
        if not self.connected:
            return False
        
        doc = {
            "symbol": symbol.upper(),
            "pattern_id": pattern.pattern_id,
            "regime_type": pattern.regime_type,
            "hypothesis_type": pattern.hypothesis_type,
            "microstructure_state": pattern.microstructure_state,
            "observations": pattern.observations,
            "success_rate": pattern.success_rate,
            "avg_pnl": pattern.avg_pnl,
            "meta_score": pattern.meta_score,
            "classification": pattern.classification,
            "updated_at": datetime.now(timezone.utc),
        }
        
        col = self.collection()
        if col is None:
            return False
        
        try:
            col.update_one(
                {"symbol": symbol.upper(), "pattern_id": pattern.pattern_id},
                {"$set": doc},
                upsert=True,
            )
            return True
        except Exception:
            return False
    
    def save_patterns_batch(
        self,
        symbol: str,
        patterns: List[MetaAlphaPattern],
    ) -> int:
        """Save multiple patterns."""
        if not self.connected or not patterns:
            return 0
        
        saved = 0
        for p in patterns:
            if self.save_pattern(symbol, p):
                saved += 1
        return saved
    
    def get_patterns(self, symbol: str) -> List[Dict]:
        """Get all patterns for symbol."""
        if not self.connected:
            return []
        
        return self._find_many(
            {"symbol": symbol.upper()},
            sort=[("meta_score", -1)],
        )
    
    def get_strong_patterns(self, symbol: str) -> List[Dict]:
        """Get strong meta-alpha patterns."""
        if not self.connected:
            return []
        
        return self._find_many(
            {
                "symbol": symbol.upper(),
                "classification": "STRONG_META_ALPHA",
            },
            sort=[("meta_score", -1)],
        )
    
    def get_pattern_by_id(self, symbol: str, pattern_id: str) -> Optional[Dict]:
        """Get pattern by ID."""
        if not self.connected:
            return None
        
        docs = self._find_many(
            {"symbol": symbol.upper(), "pattern_id": pattern_id},
            limit=1,
        )
        return docs[0] if docs else None
    
    def get_summary(self, symbol: str) -> MetaAlphaSummary:
        """Get summary from stored patterns."""
        patterns = self.get_patterns(symbol)
        
        if not patterns:
            return MetaAlphaSummary(symbol=symbol.upper())
        
        valid = [p for p in patterns if p.get("observations", 0) >= MIN_META_OBSERVATIONS]
        
        strong = sum(1 for p in valid if p.get("classification") == "STRONG_META_ALPHA")
        moderate = sum(1 for p in valid if p.get("classification") == "MODERATE_META_ALPHA")
        weak = sum(1 for p in valid if p.get("classification") == "WEAK_PATTERN")
        
        total_obs = sum(p.get("observations", 0) for p in patterns)
        
        if valid:
            avg_score = sum(p.get("meta_score", 0) for p in valid) / len(valid)
            avg_sr = sum(p.get("success_rate", 0) for p in valid) / len(valid)
            avg_pnl = sum(p.get("avg_pnl", 0) for p in valid) / len(valid)
            
            best = max(valid, key=lambda p: p.get("meta_score", 0))
            best_desc = f"{best.get('regime_type')}+{best.get('hypothesis_type')}+{best.get('microstructure_state')}"
        else:
            avg_score = avg_sr = avg_pnl = 0.0
            best = None
            best_desc = ""
        
        return MetaAlphaSummary(
            symbol=symbol.upper(),
            total_patterns=len(patterns),
            valid_patterns=len(valid),
            strong_count=strong,
            moderate_count=moderate,
            weak_count=weak,
            avg_meta_score=round(avg_score, 4),
            avg_success_rate=round(avg_sr, 4),
            avg_pnl=round(avg_pnl, 4),
            best_pattern_id=best.get("pattern_id", "NONE") if best else "NONE",
            best_pattern_score=best.get("meta_score", 0.0) if best else 0.0,
            best_pattern_description=best_desc,
            total_observations=total_obs,
        )
    
    def count(self, symbol: Optional[str] = None) -> int:
        """Count patterns."""
        if not self.connected:
            return 0
        
        query = {"symbol": symbol.upper()} if symbol else {}
        return self._count(query)


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[MetaAlphaRegistry] = None


def get_meta_alpha_registry() -> MetaAlphaRegistry:
    """Get singleton instance of MetaAlphaRegistry."""
    global _registry
    if _registry is None:
        _registry = MetaAlphaRegistry()
    return _registry
