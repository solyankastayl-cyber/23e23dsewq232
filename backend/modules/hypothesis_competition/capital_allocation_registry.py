"""
Capital Allocation Registry

PHASE 30.3 — MongoDB persistence for capital allocations.

Collection: hypothesis_capital_allocations
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import MongoRepository
from .capital_allocation_types import (
    HypothesisCapitalAllocation,
    CapitalAllocationSummary,
)


class CapitalAllocationRegistry(MongoRepository):
    """
    MongoDB registry for capital allocations.
    
    Stores allocation history for analysis and backtesting.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "hypothesis_capital_allocations"
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        if not self.connected:
            return
        
        self._create_index(
            [("symbol", 1), ("created_at", -1)],
            collection=self.collection_name,
        )
    
    def save_allocation(self, allocation: HypothesisCapitalAllocation) -> bool:
        """Save capital allocation to MongoDB."""
        if not self.connected:
            return False
        
        doc = {
            "symbol": allocation.symbol,
            "allocations": [
                {
                    "hypothesis_type": a.hypothesis_type,
                    "directional_bias": a.directional_bias,
                    "ranking_score": a.ranking_score,
                    "capital_weight": a.capital_weight,
                    "capital_percent": a.capital_percent,
                    "execution_state": a.execution_state,
                    "confidence": a.confidence,
                    "reliability": a.reliability,
                }
                for a in allocation.allocations
            ],
            "total_allocated": allocation.total_allocated,
            "portfolio_confidence": allocation.portfolio_confidence,
            "portfolio_reliability": allocation.portfolio_reliability,
            "total_hypotheses_input": allocation.total_hypotheses_input,
            "hypotheses_removed_unfavorable": allocation.hypotheses_removed_unfavorable,
            "hypotheses_removed_min_threshold": allocation.hypotheses_removed_min_threshold,
            "directional_cap_applied": allocation.directional_cap_applied,
            "neutral_cap_applied": allocation.neutral_cap_applied,
            "created_at": allocation.created_at,
        }
        
        return self._insert_one(doc)
    
    def get_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get allocation history for symbol."""
        if not self.connected:
            return []
        
        docs = self._find_many(
            {"symbol": symbol.upper()},
            sort=[("created_at", -1)],
            limit=limit,
        )
        
        return docs
    
    def get_latest(self, symbol: str) -> Optional[Dict]:
        """Get latest allocation for symbol."""
        if not self.connected:
            return None
        
        docs = self._find_many(
            {"symbol": symbol.upper()},
            sort=[("created_at", -1)],
            limit=1,
        )
        
        return docs[0] if docs else None
    
    def get_summary(self, symbol: str) -> CapitalAllocationSummary:
        """Get allocation summary from history."""
        history = self.get_history(symbol, limit=100)
        
        if not history:
            return CapitalAllocationSummary(
                symbol=symbol.upper(),
                total_allocations=0,
            )
        
        total = len(history)
        
        # Calculate averages
        avg_long = 0.0
        avg_short = 0.0
        avg_neutral = 0.0
        avg_confidence = 0.0
        avg_reliability = 0.0
        total_hypothesis_count = 0
        
        for alloc in history:
            allocations = alloc.get("allocations", [])
            total_hypothesis_count += len(allocations)
            
            for a in allocations:
                bias = a.get("directional_bias", "NEUTRAL")
                weight = a.get("capital_weight", 0)
                
                if bias == "LONG":
                    avg_long += weight
                elif bias == "SHORT":
                    avg_short += weight
                else:
                    avg_neutral += weight
            
            avg_confidence += alloc.get("portfolio_confidence", 0)
            avg_reliability += alloc.get("portfolio_reliability", 0)
        
        # Current state
        current = history[0] if history else {}
        current_allocations = current.get("allocations", [])
        current_count = len(current_allocations)
        current_top = current_allocations[0].get("hypothesis_type", "NONE") if current_allocations else "NONE"
        
        return CapitalAllocationSummary(
            symbol=symbol.upper(),
            total_allocations=total,
            avg_long_exposure=round(avg_long / total, 4),
            avg_short_exposure=round(avg_short / total, 4),
            avg_neutral_exposure=round(avg_neutral / total, 4),
            avg_portfolio_confidence=round(avg_confidence / total, 4),
            avg_portfolio_reliability=round(avg_reliability / total, 4),
            avg_hypothesis_count=round(total_hypothesis_count / total, 2),
            current_allocation_count=current_count,
            current_top_hypothesis=current_top,
        )
    
    def count(self, symbol: Optional[str] = None) -> int:
        """Count allocations."""
        if not self.connected:
            return 0
        
        query = {"symbol": symbol.upper()} if symbol else {}
        return self._count(query)


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[CapitalAllocationRegistry] = None


def get_capital_allocation_registry() -> CapitalAllocationRegistry:
    """Get singleton instance of CapitalAllocationRegistry."""
    global _registry
    if _registry is None:
        _registry = CapitalAllocationRegistry()
    return _registry
