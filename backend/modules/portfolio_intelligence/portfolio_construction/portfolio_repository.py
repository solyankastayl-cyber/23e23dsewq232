"""
PHASE 10 - Portfolio Construction Repository
=============================================
Storage and retrieval for portfolio data.
Uses unified MongoDB connection from core.database.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from core.database import MongoRepository, get_database

try:
    from pymongo import DESCENDING
    MONGO_OK = True
except ImportError:
    MONGO_OK = False


class PortfolioRepository(MongoRepository):
    """Repository for portfolio construction data."""
    
    def __init__(self):
        super().__init__()
        self._init_collections()
    
    def _init_collections(self):
        """Initialize collection indexes."""
        if not self.connected:
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            db.portfolio_states.create_index([("timestamp", -1)])
            db.allocations.create_index([("timestamp", -1)])
            db.rebalance_history.create_index([("timestamp", -1)])
            db.risk_parity_results.create_index([("timestamp", -1)])
            db.correlation_matrices.create_index([("timestamp", -1)])
            print("[PortfolioRepo] Indexes created")
        except Exception as e:
            print(f"[PortfolioRepo] Index error: {e}")
    
    def save_portfolio_state(self, state: Any) -> bool:
        """Save portfolio state."""
        if not self.connected:
            return False
        
        try:
            doc = state.to_dict() if hasattr(state, 'to_dict') else dict(state)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "portfolio_states")
        except Exception:
            return False
    
    def save_allocations(self, allocations: Dict) -> bool:
        """Save allocation results."""
        if not self.connected:
            return False
        
        try:
            doc = {
                "timestamp": datetime.now(timezone.utc),
                "allocations": {
                    sid: a.to_dict() if hasattr(a, 'to_dict') else dict(a)
                    for sid, a in allocations.items()
                },
                "_saved_at": datetime.now(timezone.utc)
            }
            return self._insert_one(doc, "allocations")
        except Exception:
            return False
    
    def save_rebalance(self, rebalance: Any) -> bool:
        """Save rebalance recommendation."""
        if not self.connected:
            return False
        
        try:
            doc = rebalance.to_dict() if hasattr(rebalance, 'to_dict') else dict(rebalance)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "rebalance_history")
        except Exception:
            return False
    
    def get_state_history(
        self,
        hours_back: int = 24,
        limit: int = 50
    ) -> List[Dict]:
        """Get portfolio state history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"timestamp": {"$gte": cutoff.isoformat()}},
                collection="portfolio_states",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_allocation_history(
        self,
        hours_back: int = 24,
        limit: int = 20
    ) -> List[Dict]:
        """Get allocation history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"timestamp": {"$gte": cutoff}},
                collection="allocations",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_rebalance_history(
        self,
        hours_back: int = 168,  # 1 week
        limit: int = 50
    ) -> List[Dict]:
        """Get rebalance history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"timestamp": {"$gte": cutoff.isoformat()}},
                collection="rebalance_history",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            db = self.db
            if db is None:
                return {"connected": False}
            
            return {
                "connected": True,
                "collections": {
                    "portfolio_states": db.portfolio_states.count_documents({}),
                    "allocations": db.allocations.count_documents({}),
                    "rebalance_history": db.rebalance_history.count_documents({}),
                    "risk_parity_results": db.risk_parity_results.count_documents({}),
                    "correlation_matrices": db.correlation_matrices.count_documents({})
                }
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
