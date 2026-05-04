"""
PHASE 9 - Microstructure Repository
=====================================
Storage and retrieval for microstructure data.
Uses unified MongoDB connection from core.database.

Collections:
- order_flow_snapshots
- aggressor_history
- micro_imbalances
- timing_signals
- flow_pressure_history
- microstructure_snapshots
"""

from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from core.database import MongoRepository, get_database

try:
    from pymongo import DESCENDING
    MONGO_OK = True
except ImportError:
    MONGO_OK = False


class MicrostructureRepository(MongoRepository):
    """
    Repository for microstructure data storage.
    Uses singleton MongoDB connection.
    """
    
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
            
            # Order flow snapshots
            db.order_flow_snapshots.create_index([("symbol", 1), ("timestamp", -1)])
            
            # Aggressor history
            db.aggressor_history.create_index([("symbol", 1), ("timestamp", -1)])
            
            # Micro imbalances
            db.micro_imbalances.create_index([("symbol", 1), ("timestamp", -1)])
            
            # Timing signals
            db.timing_signals.create_index([("symbol", 1), ("timestamp", -1)])
            
            # Flow pressure
            db.flow_pressure_history.create_index([("symbol", 1), ("timestamp", -1)])
            
            # Unified snapshots
            db.microstructure_snapshots.create_index([("symbol", 1), ("timestamp", -1)])
            
            print("[MicrostructureRepo] Indexes created")
            
        except Exception as e:
            print(f"[MicrostructureRepo] Index creation failed: {e}")
    
    def save_order_flow(self, snapshot: Any) -> bool:
        """Save order flow snapshot."""
        if not self.connected:
            return False
        
        try:
            doc = snapshot.to_dict() if hasattr(snapshot, 'to_dict') else dict(snapshot)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "order_flow_snapshots")
        except Exception as e:
            print(f"[MicrostructureRepo] Failed to save order flow: {e}")
            return False
    
    def save_aggressor_analysis(self, analysis: Any) -> bool:
        """Save aggressor analysis."""
        if not self.connected:
            return False
        
        try:
            doc = analysis.to_dict() if hasattr(analysis, 'to_dict') else dict(analysis)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "aggressor_history")
        except Exception as e:
            print(f"[MicrostructureRepo] Failed to save aggressor: {e}")
            return False
    
    def save_micro_imbalance(self, imbalance: Any) -> bool:
        """Save micro imbalance."""
        if not self.connected:
            return False
        
        try:
            doc = imbalance.to_dict() if hasattr(imbalance, 'to_dict') else dict(imbalance)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "micro_imbalances")
        except Exception as e:
            print(f"[MicrostructureRepo] Failed to save imbalance: {e}")
            return False
    
    def save_timing_signal(self, timing: Any) -> bool:
        """Save execution timing signal."""
        if not self.connected:
            return False
        
        try:
            doc = timing.to_dict() if hasattr(timing, 'to_dict') else dict(timing)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "timing_signals")
        except Exception as e:
            print(f"[MicrostructureRepo] Failed to save timing: {e}")
            return False
    
    def save_flow_pressure(self, pressure: Any) -> bool:
        """Save flow pressure analysis."""
        if not self.connected:
            return False
        
        try:
            doc = pressure.to_dict() if hasattr(pressure, 'to_dict') else dict(pressure)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "flow_pressure_history")
        except Exception as e:
            print(f"[MicrostructureRepo] Failed to save pressure: {e}")
            return False
    
    def save_unified_snapshot(self, snapshot: Any) -> bool:
        """Save unified microstructure snapshot."""
        if not self.connected:
            return False
        
        try:
            doc = snapshot.to_dict() if hasattr(snapshot, 'to_dict') else dict(snapshot)
            doc["_saved_at"] = datetime.now(timezone.utc)
            return self._insert_one(doc, "microstructure_snapshots")
        except Exception as e:
            print(f"[MicrostructureRepo] Failed to save snapshot: {e}")
            return False
    
    def get_order_flow_history(
        self,
        symbol: str,
        hours_back: int = 1,
        limit: int = 100
    ) -> List[Dict]:
        """Get order flow history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"symbol": symbol, "timestamp": {"$gte": cutoff.isoformat()}},
                collection="order_flow_snapshots",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_aggressor_history(
        self,
        symbol: str,
        hours_back: int = 1,
        limit: int = 100
    ) -> List[Dict]:
        """Get aggressor analysis history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"symbol": symbol, "timestamp": {"$gte": cutoff.isoformat()}},
                collection="aggressor_history",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_snapshot_history(
        self,
        symbol: str,
        hours_back: int = 24,
        limit: int = 50
    ) -> List[Dict]:
        """Get unified snapshot history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"symbol": symbol, "timestamp": {"$gte": cutoff.isoformat()}},
                collection="microstructure_snapshots",
                sort=[("timestamp", DESCENDING)],
                limit=limit
            )
        except Exception:
            return []
    
    def get_timing_signals(
        self,
        symbol: str,
        hours_back: int = 1,
        limit: int = 50
    ) -> List[Dict]:
        """Get timing signal history."""
        if not self.connected:
            return []
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            return self._find_many(
                {"symbol": symbol, "timestamp": {"$gte": cutoff.isoformat()}},
                collection="timing_signals",
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
                    "order_flow_snapshots": db.order_flow_snapshots.count_documents({}),
                    "aggressor_history": db.aggressor_history.count_documents({}),
                    "micro_imbalances": db.micro_imbalances.count_documents({}),
                    "timing_signals": db.timing_signals.count_documents({}),
                    "flow_pressure_history": db.flow_pressure_history.count_documents({}),
                    "microstructure_snapshots": db.microstructure_snapshots.count_documents({})
                }
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
    
    def cleanup_old_data(self, days: int = 7) -> Dict:
        """Clean up old data."""
        if not self.connected:
            return {"success": False, "reason": "No database connection"}
        
        try:
            db = self.db
            if db is None:
                return {"success": False, "reason": "No database"}
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            results = {}
            collections = [
                "order_flow_snapshots",
                "aggressor_history",
                "micro_imbalances",
                "timing_signals",
                "flow_pressure_history",
                "microstructure_snapshots"
            ]
            
            for coll in collections:
                result = db[coll].delete_many({"timestamp": {"$lt": cutoff_str}})
                results[coll] = result.deleted_count
            
            return {"success": True, "cutoff": cutoff_str, "deleted": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
