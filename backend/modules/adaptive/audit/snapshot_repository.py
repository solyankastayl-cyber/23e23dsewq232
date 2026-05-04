"""
PHASE 3.3 — Snapshot Repository

Stores and retrieves snapshots from MongoDB.
Provides history and retrieval capabilities.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta


class SnapshotRepository:
    """
    Repository for adaptive state snapshots.
    
    Stores in MongoDB collection: adaptive_snapshots
    """
    
    def __init__(self, db=None, max_snapshots: int = 100):
        self.db = db
        self._ensure_db()
        self.max_snapshots = max_snapshots
        self._in_memory_cache: List[Dict] = []
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def save(self, snapshot: Dict) -> str:
        """
        Save snapshot to repository.
        
        Returns:
            Snapshot ID
        """
        # Add to in-memory cache
        self._in_memory_cache.append(snapshot)
        if len(self._in_memory_cache) > self.max_snapshots:
            self._in_memory_cache = self._in_memory_cache[-self.max_snapshots:]
        
        # Save to MongoDB
        if self.db is not None:
            try:
                result = self.db.adaptive_snapshots.insert_one(snapshot)
                snapshot_id = str(result.inserted_id)
                
                # Cleanup old snapshots
                self._cleanup_old_snapshots()
                
                return snapshot_id
            except Exception as e:
                print(f"[SnapshotRepository] Save error: {e}")
                return snapshot.get("hash", "memory_only")
        
        return snapshot.get("hash", "memory_only")
    
    def get_by_id(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot by ID."""
        if self.db is not None:
            try:
                from bson import ObjectId
                doc = self.db.adaptive_snapshots.find_one({"_id": ObjectId(snapshot_id)})
                if doc is not None:
                    doc["_id"] = str(doc["_id"])
                    return doc
            except Exception as e:
                print(f"[SnapshotRepository] Get error: {e}")
        
        # Try in-memory
        for snap in self._in_memory_cache:
            if snap.get("hash") == snapshot_id:
                return snap
        
        return None
    
    def get_by_hash(self, state_hash: str) -> Optional[Dict]:
        """Get snapshot by state hash."""
        if self.db is not None:
            try:
                doc = self.db.adaptive_snapshots.find_one(
                    {"hash": state_hash},
                    {"_id": 0}
                )
                return doc
            except Exception as e:
                print(f"[SnapshotRepository] Get by hash error: {e}")
        
        # Try in-memory
        for snap in self._in_memory_cache:
            if snap.get("hash") == state_hash:
                return snap
        
        return None
    
    def get_latest(self, count: int = 1) -> List[Dict]:
        """Get most recent snapshots."""
        if self.db is not None:
            try:
                docs = list(
                    self.db.adaptive_snapshots.find({}, {"_id": 0})
                    .sort("timestamp", -1)
                    .limit(count)
                )
                return docs
            except Exception as e:
                print(f"[SnapshotRepository] Get latest error: {e}")
        
        return self._in_memory_cache[-count:][::-1]
    
    def get_history(
        self,
        limit: int = 20,
        trigger: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get snapshot history.
        
        Args:
            limit: Max snapshots to return
            trigger: Filter by trigger type
            since: Only snapshots after this time
        """
        query = {}
        
        if trigger:
            query["trigger"] = trigger
        
        if since:
            query["timestamp"] = {"$gte": since.isoformat()}
        
        if self.db is not None:
            try:
                docs = list(
                    self.db.adaptive_snapshots.find(query, {"_id": 0, "state": 0})
                    .sort("timestamp", -1)
                    .limit(limit)
                )
                return docs
            except Exception as e:
                print(f"[SnapshotRepository] Get history error: {e}")
        
        # In-memory fallback
        result = []
        for snap in reversed(self._in_memory_cache):
            if trigger and snap.get("trigger") != trigger:
                continue
            if since and snap.get("timestamp", "") < since.isoformat():
                continue
            
            # Exclude full state from history listing
            result.append({
                k: v for k, v in snap.items() if k != "state"
            })
            
            if len(result) >= limit:
                break
        
        return result
    
    def get_previous(self, current_version: int) -> Optional[Dict]:
        """Get snapshot for previous version."""
        if self.db is not None:
            try:
                doc = self.db.adaptive_snapshots.find_one(
                    {"version": current_version - 1},
                    {"_id": 0}
                )
                return doc
            except Exception as e:
                print(f"[SnapshotRepository] Get previous error: {e}")
        
        # In-memory
        for snap in reversed(self._in_memory_cache):
            if snap.get("version") == current_version - 1:
                return snap
        
        return None
    
    def count(self) -> int:
        """Get total snapshot count."""
        if self.db is not None:
            try:
                return self.db.adaptive_snapshots.count_documents({})
            except Exception:
                pass
        return len(self._in_memory_cache)
    
    def _cleanup_old_snapshots(self):
        """Remove old snapshots beyond max limit."""
        if self.db is None:
            return
        
        try:
            count = self.db.adaptive_snapshots.count_documents({})
            if count > self.max_snapshots:
                # Get oldest snapshots to delete
                oldest = self.db.adaptive_snapshots.find().sort("timestamp", 1).limit(count - self.max_snapshots)
                ids = [doc["_id"] for doc in oldest]
                self.db.adaptive_snapshots.delete_many({"_id": {"$in": ids}})
        except Exception as e:
            print(f"[SnapshotRepository] Cleanup error: {e}")
    
    def clear(self):
        """Clear all snapshots (admin only)."""
        self._in_memory_cache = []
        
        if self.db is not None:
            try:
                self.db.adaptive_snapshots.delete_many({})
            except Exception as e:
                print(f"[SnapshotRepository] Clear error: {e}")
