"""
Outcome Tracking Registry

PHASE 30.4 — MongoDB persistence for hypothesis outcomes.

Collection: hypothesis_outcomes
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import MongoRepository
from .outcome_tracking_types import (
    HypothesisOutcome,
    HypothesisPerformance,
    SymbolOutcomeSummary,
    EVALUATION_HORIZONS,
)


class OutcomeTrackingRegistry(MongoRepository):
    """
    MongoDB registry for hypothesis outcomes.
    
    Stores outcome history for analysis and system learning.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "hypothesis_outcomes"
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        if not self.connected:
            return
        
        self._create_index(
            [("symbol", 1), ("evaluated_at", -1)],
            collection=self.collection_name,
        )
        self._create_index(
            [("symbol", 1), ("hypothesis_type", 1)],
            collection=self.collection_name,
        )
        self._create_index(
            [("symbol", 1), ("horizon_minutes", 1)],
            collection=self.collection_name,
        )
    
    def save_outcome(self, outcome: HypothesisOutcome) -> bool:
        """Save hypothesis outcome to MongoDB."""
        if not self.connected:
            return False
        
        doc = {
            "symbol": outcome.symbol,
            "hypothesis_type": outcome.hypothesis_type,
            "directional_bias": outcome.directional_bias,
            "price_at_creation": outcome.price_at_creation,
            "evaluation_price": outcome.evaluation_price,
            "horizon_minutes": outcome.horizon_minutes,
            "expected_direction": outcome.expected_direction,
            "actual_direction": outcome.actual_direction,
            "pnl_percent": outcome.pnl_percent,
            "success": outcome.success,
            "confidence": outcome.confidence,
            "reliability": outcome.reliability,
            "capital_weight": outcome.capital_weight,
            "created_at": outcome.created_at,
            "evaluated_at": outcome.evaluated_at,
        }
        
        return self._insert_one(doc)
    
    def save_outcomes_batch(self, outcomes: List[HypothesisOutcome]) -> int:
        """Save multiple outcomes."""
        if not self.connected or not outcomes:
            return 0
        
        docs = [
            {
                "symbol": o.symbol,
                "hypothesis_type": o.hypothesis_type,
                "directional_bias": o.directional_bias,
                "price_at_creation": o.price_at_creation,
                "evaluation_price": o.evaluation_price,
                "horizon_minutes": o.horizon_minutes,
                "expected_direction": o.expected_direction,
                "actual_direction": o.actual_direction,
                "pnl_percent": o.pnl_percent,
                "success": o.success,
                "confidence": o.confidence,
                "reliability": o.reliability,
                "capital_weight": o.capital_weight,
                "created_at": o.created_at,
                "evaluated_at": o.evaluated_at,
            }
            for o in outcomes
        ]
        
        return self._insert_many(docs)
    
    def get_outcomes(
        self,
        symbol: str,
        limit: int = 100,
        hypothesis_type: Optional[str] = None,
        horizon: Optional[int] = None,
    ) -> List[Dict]:
        """Get outcomes with optional filters."""
        if not self.connected:
            return []
        
        query = {"symbol": symbol.upper()}
        if hypothesis_type:
            query["hypothesis_type"] = hypothesis_type
        if horizon:
            query["horizon_minutes"] = horizon
        
        return self._find_many(
            query,
            sort=[("evaluated_at", -1)],
            limit=limit,
        )
    
    def get_performance(
        self,
        symbol: str,
        hypothesis_type: Optional[str] = None,
    ) -> List[HypothesisPerformance]:
        """Calculate performance from stored outcomes."""
        if not self.connected:
            return []
        
        # Build aggregation pipeline
        match = {"symbol": symbol.upper()}
        if hypothesis_type:
            match["hypothesis_type"] = hypothesis_type
        
        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$hypothesis_type",
                "total_predictions": {"$sum": 1},
                "successes": {"$sum": {"$cond": ["$success", 1, 0]}},
                "total_pnl": {"$sum": "$pnl_percent"},
                "total_confidence": {"$sum": "$confidence"},
                "total_reliability": {"$sum": "$reliability"},
            }},
        ]
        
        col = self.collection()
        if col is None:
            return []
        
        try:
            results = list(col.aggregate(pipeline))
        except Exception:
            return []
        
        performances = []
        for r in results:
            total = r["total_predictions"]
            if total == 0:
                continue
            
            perf = HypothesisPerformance(
                hypothesis_type=r["_id"],
                total_predictions=total,
                success_rate=round(r["successes"] / total, 4),
                avg_pnl=round(r["total_pnl"] / total, 4),
                avg_confidence=round(r["total_confidence"] / total, 4),
                avg_reliability=round(r["total_reliability"] / total, 4),
            )
            performances.append(perf)
        
        return sorted(performances, key=lambda p: p.success_rate, reverse=True)
    
    def get_summary(self, symbol: str) -> SymbolOutcomeSummary:
        """Get aggregated summary from stored outcomes."""
        if not self.connected:
            return SymbolOutcomeSummary(symbol=symbol.upper())
        
        col = self.collection()
        if col is None:
            return SymbolOutcomeSummary(symbol=symbol.upper())
        
        try:
            # Overall stats
            total = col.count_documents({"symbol": symbol.upper()})
            if total == 0:
                return SymbolOutcomeSummary(symbol=symbol.upper())
            
            successes = col.count_documents({"symbol": symbol.upper(), "success": True})
            
            # By direction
            long_total = col.count_documents({"symbol": symbol.upper(), "directional_bias": "LONG"})
            long_success = col.count_documents({"symbol": symbol.upper(), "directional_bias": "LONG", "success": True})
            
            short_total = col.count_documents({"symbol": symbol.upper(), "directional_bias": "SHORT"})
            short_success = col.count_documents({"symbol": symbol.upper(), "directional_bias": "SHORT", "success": True})
            
            neutral_total = col.count_documents({"symbol": symbol.upper(), "directional_bias": "NEUTRAL"})
            neutral_success = col.count_documents({"symbol": symbol.upper(), "directional_bias": "NEUTRAL", "success": True})
            
            # Avg PnL
            pnl_pipeline = [
                {"$match": {"symbol": symbol.upper()}},
                {"$group": {"_id": None, "avg_pnl": {"$avg": "$pnl_percent"}}},
            ]
            pnl_result = list(col.aggregate(pnl_pipeline))
            avg_pnl = pnl_result[0]["avg_pnl"] if pnl_result else 0.0
            
            # Performance for best/worst
            performances = self.get_performance(symbol)
            best_perf = performances[0] if performances else None
            worst_perf = performances[-1] if performances else None
            
            return SymbolOutcomeSummary(
                symbol=symbol.upper(),
                total_outcomes=total,
                overall_success_rate=round(successes / total, 4),
                overall_avg_pnl=round(avg_pnl, 4),
                long_success_rate=round(long_success / long_total, 4) if long_total else 0.0,
                short_success_rate=round(short_success / short_total, 4) if short_total else 0.0,
                neutral_success_rate=round(neutral_success / neutral_total, 4) if neutral_total else 0.0,
                best_hypothesis_type=best_perf.hypothesis_type if best_perf else "NONE",
                best_success_rate=best_perf.success_rate if best_perf else 0.0,
                worst_hypothesis_type=worst_perf.hypothesis_type if worst_perf else "NONE",
                worst_success_rate=worst_perf.success_rate if worst_perf else 0.0,
            )
        except Exception:
            return SymbolOutcomeSummary(symbol=symbol.upper())
    
    def count(self, symbol: Optional[str] = None) -> int:
        """Count outcomes."""
        if not self.connected:
            return 0
        
        query = {"symbol": symbol.upper()} if symbol else {}
        return self._count(query)


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[OutcomeTrackingRegistry] = None


def get_outcome_tracking_registry() -> OutcomeTrackingRegistry:
    """Get singleton instance of OutcomeTrackingRegistry."""
    global _registry
    if _registry is None:
        _registry = OutcomeTrackingRegistry()
    return _registry
