"""
Liquidity Impact Registry

PHASE 37 Sublayer — Liquidity Impact Engine

MongoDB persistence for impact estimates.

Collection: liquidity_impact_estimates
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta

from .impact_types import LiquidityImpactEstimate, ImpactSummary


class ImpactRegistry:
    """MongoDB registry for liquidity impact estimates."""
    
    COLLECTION_NAME = "liquidity_impact_estimates"
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        if self._db is None:
            try:
                from core.database import get_database
                self._db = get_database()
            except Exception:
                pass
        return self._db
    
    @property
    def collection(self):
        if self.db is None:
            return None
        return self.db[self.COLLECTION_NAME]
    
    def save_estimate(self, estimate: LiquidityImpactEstimate) -> bool:
        """Save estimate to MongoDB."""
        if self.collection is None:
            return False
        
        try:
            doc = {
                "symbol": estimate.symbol,
                "intended_size_usd": estimate.intended_size_usd,
                "side": estimate.side,
                "expected_slippage_bps": estimate.expected_slippage_bps,
                "expected_market_impact_bps": estimate.expected_market_impact_bps,
                "expected_fill_quality": estimate.expected_fill_quality,
                "liquidity_bucket": estimate.liquidity_bucket,
                "impact_state": estimate.impact_state,
                "execution_recommendation": estimate.execution_recommendation,
                "size_modifier": estimate.size_modifier,
                "recorded_at": estimate.timestamp,
            }
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[ImpactRegistry] Save error: {e}")
            return False
    
    def get_history(self, symbol: str, limit: int = 100) -> List[dict]:
        """Get historical estimates."""
        if self.collection is None:
            return []
        
        try:
            docs = list(self.collection.find(
                {"symbol": symbol.upper()},
                {"_id": 0}
            ).sort("recorded_at", -1).limit(limit))
            return docs
        except Exception:
            return []
    
    def get_summary(self, symbol: str) -> Optional[dict]:
        """Get aggregated summary."""
        if self.collection is None:
            return None
        
        try:
            pipeline = [
                {"$match": {"symbol": symbol.upper()}},
                {"$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "avg_slippage": {"$avg": "$expected_slippage_bps"},
                    "avg_impact": {"$avg": "$expected_market_impact_bps"},
                    "avg_fill_quality": {"$avg": "$expected_fill_quality"},
                }}
            ]
            results = list(self.collection.aggregate(pipeline))
            return results[0] if results else None
        except Exception:
            return None
    
    def ensure_indexes(self) -> bool:
        if self.collection is None:
            return False
        try:
            self.collection.create_index([("symbol", 1), ("recorded_at", -1)])
            return True
        except Exception:
            return False


_impact_registry: Optional[ImpactRegistry] = None


def get_impact_registry() -> ImpactRegistry:
    global _impact_registry
    if _impact_registry is None:
        _impact_registry = ImpactRegistry()
    return _impact_registry
