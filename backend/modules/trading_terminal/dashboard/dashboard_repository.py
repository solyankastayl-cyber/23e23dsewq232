"""
Dashboard Repository (TR6)
==========================

Database operations for dashboard snapshots and events.
"""

import threading
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import os

from .dashboard_types import DashboardSnapshot, DashboardEvent, DashboardEventType


class DashboardRepository:
    """
    Repository for dashboard data.
    
    Handles:
    - Snapshot storage
    - Event logging
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._db = None
        self._use_mongo = False
        
        # In-memory fallback
        self._snapshots: List[DashboardSnapshot] = []
        self._events: List[DashboardEvent] = []
        
        self._init_db()
        self._initialized = True
    
    def _init_db(self):
        """Initialize database connection"""
        try:
            mongo_url = os.environ.get("MONGO_URL")
            db_name = os.environ.get("DB_NAME", "ta_engine")
            
            if mongo_url:
                from pymongo import MongoClient
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._use_mongo = True
                
                # Create indexes
                self._db.dashboard_snapshots.create_index("created_at")
                self._db.dashboard_events.create_index("timestamp")
                self._db.dashboard_events.create_index("event_type")
                
                print("[DashboardRepository] MongoDB connected")
            else:
                print("[DashboardRepository] Using in-memory storage")
        except Exception as e:
            print(f"[DashboardRepository] MongoDB init failed: {e}, using in-memory")
            self._use_mongo = False
    
    # ===========================================
    # Snapshot Operations
    # ===========================================
    
    def save_snapshot(self, snapshot: DashboardSnapshot) -> bool:
        """Save dashboard snapshot"""
        try:
            if self._use_mongo and self._db is not None:
                doc = snapshot.to_dict()
                doc["_id"] = snapshot.snapshot_id
                self._db.dashboard_snapshots.insert_one(doc)
            else:
                self._snapshots.append(snapshot)
                if len(self._snapshots) > 500:
                    self._snapshots = self._snapshots[-500:]
            return True
        except Exception as e:
            print(f"[DashboardRepository] save_snapshot error: {e}")
            return False
    
    def get_snapshots(self, limit: int = 100) -> List[DashboardSnapshot]:
        """Get recent snapshots"""
        try:
            if self._use_mongo and self._db is not None:
                cursor = self._db.dashboard_snapshots.find(
                    {},
                    {"_id": 0}
                ).sort("created_at", -1).limit(limit)
                
                return [self._doc_to_snapshot(doc) for doc in cursor]
            else:
                return list(reversed(self._snapshots[-limit:]))
        except Exception as e:
            print(f"[DashboardRepository] get_snapshots error: {e}")
            return []
    
    def get_latest_snapshot(self) -> Optional[DashboardSnapshot]:
        """Get latest snapshot"""
        snapshots = self.get_snapshots(limit=1)
        return snapshots[0] if snapshots else None
    
    # ===========================================
    # Event Operations
    # ===========================================
    
    def save_event(self, event: DashboardEvent) -> bool:
        """Save dashboard event"""
        try:
            if self._use_mongo and self._db is not None:
                doc = event.to_dict()
                doc["_id"] = event.event_id
                self._db.dashboard_events.insert_one(doc)
            else:
                self._events.append(event)
                if len(self._events) > 1000:
                    self._events = self._events[-1000:]
            return True
        except Exception as e:
            print(f"[DashboardRepository] save_event error: {e}")
            return False
    
    def get_events(
        self,
        limit: int = 100,
        event_type: Optional[DashboardEventType] = None
    ) -> List[DashboardEvent]:
        """Get dashboard events"""
        try:
            if self._use_mongo and self._db is not None:
                query = {}
                if event_type:
                    query["event_type"] = event_type.value
                
                cursor = self._db.dashboard_events.find(
                    query,
                    {"_id": 0}
                ).sort("timestamp", -1).limit(limit)
                
                return [self._doc_to_event(doc) for doc in cursor]
            else:
                events = self._events
                if event_type:
                    events = [e for e in events if e.event_type == event_type]
                return list(reversed(events[-limit:]))
        except Exception as e:
            print(f"[DashboardRepository] get_events error: {e}")
            return []
    
    # ===========================================
    # Helper Methods
    # ===========================================
    
    def _doc_to_snapshot(self, doc: Dict[str, Any]) -> DashboardSnapshot:
        """Convert doc to DashboardSnapshot"""
        return DashboardSnapshot(
            snapshot_id=doc.get("snapshotId", ""),
            state=doc.get("state", {}),
            created_at=datetime.fromisoformat(doc["createdAt"]) if doc.get("createdAt") else datetime.now(timezone.utc)
        )
    
    def _doc_to_event(self, doc: Dict[str, Any]) -> DashboardEvent:
        """Convert doc to DashboardEvent"""
        return DashboardEvent(
            event_id=doc.get("eventId", ""),
            event_type=DashboardEventType(doc.get("eventType", "PORTFOLIO_UPDATED")),
            payload=doc.get("payload", {}),
            timestamp=datetime.fromisoformat(doc["timestamp"]) if doc.get("timestamp") else datetime.now(timezone.utc)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository stats"""
        try:
            if self._use_mongo and self._db is not None:
                snapshots_count = self._db.dashboard_snapshots.count_documents({})
                events_count = self._db.dashboard_events.count_documents({})
            else:
                snapshots_count = len(self._snapshots)
                events_count = len(self._events)
            
            return {
                "snapshots_count": snapshots_count,
                "events_count": events_count,
                "storage": "mongodb" if self._use_mongo else "memory"
            }
        except Exception as e:
            return {"error": str(e)}


# Global singleton
dashboard_repository = DashboardRepository()
