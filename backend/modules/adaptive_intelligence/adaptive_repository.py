"""
PHASE 11 - Adaptive Intelligence Repository
=============================================
Storage for adaptive intelligence data.
Uses unified MongoDB connection from core.database.
"""

from typing import List, Dict
from datetime import datetime, timezone, timedelta

from core.database import MongoRepository, get_database

try:
    from pymongo import DESCENDING
    MONGO_OK = True
except ImportError:
    MONGO_OK = False


class AdaptiveRepository(MongoRepository):
    """Repository for adaptive intelligence data."""
    
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
            
            db.adaptive_snapshots.create_index([("timestamp", -1)])
            db.adaptive_changes.create_index([("timestamp", -1)])
            db.edge_decay_history.create_index([("strategy_id", 1), ("timestamp", -1)])
            db.performance_history.create_index([("strategy_id", 1), ("timestamp", -1)])
            print("[AdaptiveRepo] Indexes created")
        except Exception as e:
            print(f"[AdaptiveRepo] Index error: {e}")
    
    def save_snapshot(self, snapshot) -> bool:
        """Save adaptive snapshot."""
        if not self.connected:
            return False
        
        try:
            doc = snapshot.to_dict() if hasattr(snapshot, 'to_dict') else dict(snapshot)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "adaptive_snapshots")
        except Exception:
            return False
    
    def save_change_record(self, record) -> bool:
        """Save change record."""
        if not self.connected:
            return False
        
        try:
            doc = record.to_dict() if hasattr(record, 'to_dict') else dict(record)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "adaptive_changes")
        except Exception:
            return False
    
    def get_snapshot_history(self, hours_back: int = 24, limit: int = 50) -> List[Dict]:
        """Get snapshot history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"timestamp": {"$gte": cutoff.isoformat()}},
                collection="adaptive_snapshots",
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
                    "adaptive_snapshots": db.adaptive_snapshots.count_documents({}),
                    "adaptive_changes": db.adaptive_changes.count_documents({}),
                    "edge_decay_history": db.edge_decay_history.count_documents({}),
                    "performance_history": db.performance_history.count_documents({})
                }
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
