"""
Execution Registry

PHASE 37 — Execution Brain

MongoDB persistence for execution plans.

Collection: execution_plans
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta

from .execution_types import ExecutionPlan, ExecutionSummary


class ExecutionRegistry:
    """MongoDB registry for execution plans."""
    
    COLLECTION_NAME = "execution_plans"
    
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
    
    def save_plan(self, plan: ExecutionPlan) -> bool:
        """Save execution plan to MongoDB."""
        if self.collection is None:
            return False
        
        try:
            doc = {
                "symbol": plan.symbol,
                "strategy": plan.strategy,
                "hypothesis_type": plan.hypothesis_type,
                "direction": plan.direction,
                "position_size_usd": plan.position_size_usd,
                "position_size_adjusted": plan.position_size_adjusted,
                "entry_price": plan.entry_price,
                "stop_loss": plan.stop_loss,
                "take_profit": plan.take_profit,
                "risk_level": plan.risk_level,
                "risk_reward_ratio": plan.risk_reward_ratio,
                "execution_type": plan.execution_type,
                "confidence": plan.confidence,
                "reliability": plan.reliability,
                "status": plan.status,
                "blocked_reason": plan.blocked_reason,
                "impact_adjusted": plan.impact_adjusted,
                "size_reduction_pct": plan.size_reduction_pct,
                "reason": plan.reason,
                "recorded_at": plan.timestamp,
            }
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[ExecutionRegistry] Save error: {e}")
            return False
    
    def get_active_plan(self, symbol: str) -> Optional[dict]:
        """Get most recent active plan."""
        if self.collection is None:
            return None
        
        try:
            doc = self.collection.find_one(
                {"symbol": symbol.upper(), "status": {"$in": ["PENDING", "APPROVED"]}},
                {"_id": 0},
                sort=[("recorded_at", -1)]
            )
            return doc
        except Exception:
            return None
    
    def get_history(self, symbol: str, limit: int = 100) -> List[dict]:
        """Get historical plans."""
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
    
    def update_status(self, symbol: str, status: str) -> bool:
        """Update status of most recent plan."""
        if self.collection is None:
            return False
        
        try:
            result = self.collection.update_one(
                {"symbol": symbol.upper()},
                {"$set": {"status": status}},
                sort=[("recorded_at", -1)]
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def ensure_indexes(self) -> bool:
        if self.collection is None:
            return False
        try:
            self.collection.create_index([("symbol", 1), ("recorded_at", -1)])
            self.collection.create_index([("symbol", 1), ("status", 1)])
            return True
        except Exception:
            return False


_execution_registry: Optional[ExecutionRegistry] = None


def get_execution_registry() -> ExecutionRegistry:
    global _execution_registry
    if _execution_registry is None:
        _execution_registry = ExecutionRegistry()
    return _execution_registry
