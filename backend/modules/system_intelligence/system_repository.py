"""
PHASE 12 - System Intelligence Repository
==========================================
Storage for system intelligence data.
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


class SystemRepository(MongoRepository):
    """Repository for system intelligence data."""
    
    def __init__(self):
        super().__init__()
        self._init_collections()
    
    def _init_collections(self):
        """Initialize collection indexes."""
        if not self.connected:
            return
        
        try:
            db = self.db
            if db is not None:
                db.system_snapshots.create_index([("timestamp", -1)])
                db.system_decisions.create_index([("timestamp", -1)])
                db.market_states.create_index([("timestamp", -1)])
                db.health_snapshots.create_index([("timestamp", -1)])
                print("[SystemRepo] Indexes created")
        except Exception as e:
            print(f"[SystemRepo] Index creation error: {e}")
    
    def save_snapshot(self, snapshot) -> bool:
        """Save system snapshot."""
        if not self.connected:
            return False
        
        try:
            doc = snapshot.to_dict() if hasattr(snapshot, 'to_dict') else dict(snapshot)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "system_snapshots")
        except Exception as e:
            print(f"[SystemRepo] Save snapshot error: {e}")
            return False
    
    def save_decision(self, decision) -> bool:
        """Save system decision."""
        if not self.connected:
            return False
        
        try:
            doc = decision.to_dict() if hasattr(decision, 'to_dict') else dict(decision)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "system_decisions")
        except Exception as e:
            print(f"[SystemRepo] Save decision error: {e}")
            return False
    
    def get_snapshot_history(self, hours_back: int = 24, limit: int = 50) -> List[Dict]:
        """Get snapshot history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"timestamp": {"$gte": cutoff.isoformat()}},
                collection="system_snapshots",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_decision_history(self, hours_back: int = 168, limit: int = 100) -> List[Dict]:
        """Get decision history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"timestamp": {"$gte": cutoff.isoformat()}},
                collection="system_decisions",
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
                    "system_snapshots": db.system_snapshots.count_documents({}),
                    "system_decisions": db.system_decisions.count_documents({}),
                    "market_states": db.market_states.count_documents({}),
                    "health_snapshots": db.health_snapshots.count_documents({})
                }
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
