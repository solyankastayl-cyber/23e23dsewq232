"""
Strategy Control Repository (TR5)
=================================

Database operations for strategy control events.
"""

import threading
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import os

from .control_types import StrategyControlEvent, ControlAction


class ControlRepository:
    """
    Repository for strategy control data.
    
    Handles:
    - Control state persistence
    - Event logging
    - History queries
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
        self._events: List[StrategyControlEvent] = []
        self._state_history: List[Dict[str, Any]] = []
        
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
                self._db.strategy_control_events.create_index("timestamp")
                self._db.strategy_control_events.create_index("action")
                self._db.strategy_control_state.create_index("updated_at")
                
                print("[ControlRepository] MongoDB connected")
            else:
                print("[ControlRepository] Using in-memory storage")
        except Exception as e:
            print(f"[ControlRepository] MongoDB init failed: {e}, using in-memory")
            self._use_mongo = False
    
    # ===========================================
    # Event Operations
    # ===========================================
    
    def save_event(self, event: StrategyControlEvent) -> bool:
        """Save control event"""
        try:
            if self._use_mongo and self._db is not None:
                doc = event.to_dict()
                doc["_id"] = event.event_id
                self._db.strategy_control_events.insert_one(doc)
            else:
                self._events.append(event)
                if len(self._events) > 1000:
                    self._events = self._events[-1000:]
            return True
        except Exception as e:
            print(f"[ControlRepository] save_event error: {e}")
            return False
    
    def get_events(
        self,
        limit: int = 100,
        action: Optional[ControlAction] = None,
        actor: Optional[str] = None
    ) -> List[StrategyControlEvent]:
        """Get control events with optional filters"""
        try:
            if self._use_mongo and self._db is not None:
                query = {}
                if action:
                    query["action"] = action.value
                if actor:
                    query["actor"] = actor
                
                cursor = self._db.strategy_control_events.find(
                    query,
                    {"_id": 0}
                ).sort("timestamp", -1).limit(limit)
                
                events = []
                for doc in cursor:
                    events.append(self._doc_to_event(doc))
                return events
            else:
                events = self._events
                if action:
                    events = [e for e in events if e.action == action]
                if actor:
                    events = [e for e in events if e.actor == actor]
                return list(reversed(events[-limit:]))
        except Exception as e:
            print(f"[ControlRepository] get_events error: {e}")
            return []
    
    def get_event_by_id(self, event_id: str) -> Optional[StrategyControlEvent]:
        """Get event by ID"""
        try:
            if self._use_mongo and self._db is not None:
                doc = self._db.strategy_control_events.find_one(
                    {"event_id": event_id},
                    {"_id": 0}
                )
                if doc:
                    return self._doc_to_event(doc)
                return None
            else:
                for e in self._events:
                    if e.event_id == event_id:
                        return e
                return None
        except Exception as e:
            print(f"[ControlRepository] get_event_by_id error: {e}")
            return None
    
    def get_events_by_action(
        self,
        action: ControlAction,
        limit: int = 50
    ) -> List[StrategyControlEvent]:
        """Get events by action type"""
        return self.get_events(limit=limit, action=action)
    
    def get_recent_kill_switch_events(self, limit: int = 10) -> List[StrategyControlEvent]:
        """Get recent kill switch events"""
        try:
            if self._use_mongo and self._db is not None:
                cursor = self._db.strategy_control_events.find(
                    {"action": {"$in": [
                        ControlAction.SOFT_KILL_SWITCH.value,
                        ControlAction.HARD_KILL_SWITCH.value,
                        ControlAction.KILL_SWITCH_RESET.value
                    ]}},
                    {"_id": 0}
                ).sort("timestamp", -1).limit(limit)
                
                return [self._doc_to_event(doc) for doc in cursor]
            else:
                kill_events = [
                    e for e in self._events 
                    if e.action in [
                        ControlAction.SOFT_KILL_SWITCH,
                        ControlAction.HARD_KILL_SWITCH,
                        ControlAction.KILL_SWITCH_RESET
                    ]
                ]
                return list(reversed(kill_events[-limit:]))
        except Exception as e:
            print(f"[ControlRepository] get_recent_kill_switch_events error: {e}")
            return []
    
    # ===========================================
    # State Operations
    # ===========================================
    
    def save_state(self, state_dict: Dict[str, Any]) -> bool:
        """Save control state snapshot"""
        try:
            if self._use_mongo and self._db is not None:
                state_dict["saved_at"] = datetime.now(timezone.utc)
                self._db.strategy_control_state.insert_one(state_dict)
            else:
                self._state_history.append(state_dict)
                if len(self._state_history) > 500:
                    self._state_history = self._state_history[-500:]
            return True
        except Exception as e:
            print(f"[ControlRepository] save_state error: {e}")
            return False
    
    def get_state_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get state history"""
        try:
            if self._use_mongo and self._db is not None:
                cursor = self._db.strategy_control_state.find(
                    {},
                    {"_id": 0}
                ).sort("saved_at", -1).limit(limit)
                return list(cursor)
            else:
                return list(reversed(self._state_history[-limit:]))
        except Exception as e:
            print(f"[ControlRepository] get_state_history error: {e}")
            return []
    
    # ===========================================
    # Helper Methods
    # ===========================================
    
    def _doc_to_event(self, doc: Dict[str, Any]) -> StrategyControlEvent:
        """Convert MongoDB doc to StrategyControlEvent"""
        from .control_types import ActorType
        
        return StrategyControlEvent(
            event_id=doc.get("event_id", ""),
            action=ControlAction(doc.get("action", "PROFILE_SWITCH")),
            actor=doc.get("actor", "system"),
            actor_type=ActorType(doc.get("actor_type", "ADMIN")),
            reason=doc.get("reason", ""),
            details=doc.get("details", {}),
            previous_state=doc.get("state_change", {}).get("previous", {}),
            new_state=doc.get("state_change", {}).get("new", {}),
            success=doc.get("success", True),
            error_message=doc.get("error_message", ""),
            timestamp=datetime.fromisoformat(doc["timestamp"]) if doc.get("timestamp") else datetime.now(timezone.utc)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        try:
            if self._use_mongo and self._db is not None:
                events_count = self._db.strategy_control_events.count_documents({})
                states_count = self._db.strategy_control_state.count_documents({})
            else:
                events_count = len(self._events)
                states_count = len(self._state_history)
            
            return {
                "events_count": events_count,
                "states_count": states_count,
                "storage": "mongodb" if self._use_mongo else "memory"
            }
        except Exception as e:
            return {"error": str(e)}


# Global singleton
control_repository = ControlRepository()
