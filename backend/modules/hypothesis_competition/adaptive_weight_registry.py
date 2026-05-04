"""
Adaptive Weight Registry

PHASE 30.5 — MongoDB persistence for adaptive weights.

Collection: hypothesis_adaptive_weights
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import MongoRepository
from .adaptive_weight_types import (
    HypothesisAdaptiveWeight,
    AdaptiveWeightSummary,
)


class AdaptiveWeightRegistry(MongoRepository):
    """
    MongoDB registry for adaptive weights.
    
    Stores weight history for analysis and auditing.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "hypothesis_adaptive_weights"
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        if not self.connected:
            return
        
        self._create_index(
            [("symbol", 1), ("hypothesis_type", 1)],
            collection=self.collection_name,
        )
        self._create_index(
            [("symbol", 1), ("updated_at", -1)],
            collection=self.collection_name,
        )
    
    def save_weight(self, symbol: str, weight: HypothesisAdaptiveWeight) -> bool:
        """Save or update adaptive weight."""
        if not self.connected:
            return False
        
        doc = {
            "symbol": symbol.upper(),
            "hypothesis_type": weight.hypothesis_type,
            "success_rate": weight.success_rate,
            "avg_pnl": weight.avg_pnl,
            "success_modifier": weight.success_modifier,
            "pnl_modifier": weight.pnl_modifier,
            "adaptive_modifier": weight.adaptive_modifier,
            "final_weight": weight.final_weight,
            "observations": weight.observations,
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Upsert - update if exists, insert if not
        col = self.collection()
        if col is None:
            return False
        
        try:
            col.update_one(
                {
                    "symbol": symbol.upper(),
                    "hypothesis_type": weight.hypothesis_type,
                },
                {"$set": doc},
                upsert=True,
            )
            return True
        except Exception:
            return False
    
    def save_weights_batch(
        self,
        symbol: str,
        weights: List[HypothesisAdaptiveWeight],
    ) -> int:
        """Save multiple weights."""
        if not self.connected or not weights:
            return 0
        
        saved = 0
        for w in weights:
            if self.save_weight(symbol, w):
                saved += 1
        return saved
    
    def get_weights(self, symbol: str) -> List[Dict]:
        """Get all weights for a symbol."""
        if not self.connected:
            return []
        
        return self._find_many(
            {"symbol": symbol.upper()},
            sort=[("adaptive_modifier", -1)],
        )
    
    def get_weight(self, symbol: str, hypothesis_type: str) -> Optional[Dict]:
        """Get weight for specific hypothesis type."""
        if not self.connected:
            return None
        
        docs = self._find_many(
            {
                "symbol": symbol.upper(),
                "hypothesis_type": hypothesis_type,
            },
            limit=1,
        )
        
        return docs[0] if docs else None
    
    def get_summary(self, symbol: str) -> AdaptiveWeightSummary:
        """Get summary from stored weights."""
        weights = self.get_weights(symbol)
        
        if not weights:
            return AdaptiveWeightSummary(symbol=symbol.upper())
        
        modifiers = [w.get("adaptive_modifier", 1.0) for w in weights]
        total_obs = sum(w.get("observations", 0) for w in weights)
        
        boosted = sum(1 for m in modifiers if m > 1.0)
        penalized = sum(1 for m in modifiers if m < 1.0)
        neutral = sum(1 for m in modifiers if m == 1.0)
        
        best = max(weights, key=lambda w: w.get("adaptive_modifier", 1.0))
        worst = min(weights, key=lambda w: w.get("adaptive_modifier", 1.0))
        
        return AdaptiveWeightSummary(
            symbol=symbol.upper(),
            total_hypothesis_types=len(weights),
            total_observations=total_obs,
            avg_adaptive_modifier=round(sum(modifiers) / len(modifiers), 4),
            max_adaptive_modifier=round(max(modifiers), 4),
            min_adaptive_modifier=round(min(modifiers), 4),
            boosted_count=boosted,
            penalized_count=penalized,
            neutral_count=neutral,
            best_hypothesis=best.get("hypothesis_type", "NONE"),
            best_modifier=best.get("adaptive_modifier", 1.0),
            worst_hypothesis=worst.get("hypothesis_type", "NONE"),
            worst_modifier=worst.get("adaptive_modifier", 1.0),
        )
    
    def count(self, symbol: Optional[str] = None) -> int:
        """Count weights."""
        if not self.connected:
            return 0
        
        query = {"symbol": symbol.upper()} if symbol else {}
        return self._count(query)


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[AdaptiveWeightRegistry] = None


def get_adaptive_weight_registry() -> AdaptiveWeightRegistry:
    """Get singleton instance of AdaptiveWeightRegistry."""
    global _registry
    if _registry is None:
        _registry = AdaptiveWeightRegistry()
    return _registry
