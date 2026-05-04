"""
Event Ledger Repository
=======================

MongoDB storage for immutable event ledger.
Append-only - no updates or deletes.
"""

import os
import time
import threading
from typing import Dict, List, Optional, Any

from .ledger_types import (
    LedgerEvent,
    EventQuery,
    EventStream,
    LedgerStats,
    AggregateType,
    EventType
)

# MongoDB connection
try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception as e:
    print(f"[LedgerRepository] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class LedgerRepository:
    """
    Append-only event storage.
    
    Collection: event_ledger
    - Immutable: no update/delete operations
    - Indexed for fast queries by aggregate, type, module
    - Sequence numbers for ordering
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
        
        self._sequence_lock = threading.Lock()
        self._last_sequence = 0
        
        if MONGO_AVAILABLE:
            self._ensure_indexes()
            self._load_last_sequence()
        
        self._initialized = True
        print("[LedgerRepository] Initialized (append-only mode)")
    
    def _ensure_indexes(self):
        """Create indexes for fast queries"""
        try:
            # Primary lookup indexes
            db.event_ledger.create_index([("sequence_number", ASCENDING)], unique=True)
            db.event_ledger.create_index([("event_id", ASCENDING)], unique=True)
            
            # Aggregate lookup (most common query)
            db.event_ledger.create_index([
                ("aggregate_type", ASCENDING),
                ("aggregate_id", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            # Event type queries
            db.event_ledger.create_index([
                ("event_type", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            # Module queries
            db.event_ledger.create_index([
                ("source_module", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            # Time-based queries
            db.event_ledger.create_index([("created_at", DESCENDING)])
            
            # Correlation queries
            db.event_ledger.create_index([("metadata.correlation_id", ASCENDING)])
            
            print("[LedgerRepository] Indexes created")
        except Exception as e:
            print(f"[LedgerRepository] Index creation error: {e}")
    
    def _load_last_sequence(self):
        """Load the last sequence number from DB"""
        try:
            last = db.event_ledger.find_one(
                {},
                {"sequence_number": 1},
                sort=[("sequence_number", DESCENDING)]
            )
            self._last_sequence = last.get("sequence_number", 0) if last else 0
        except Exception as e:
            print(f"[LedgerRepository] Load sequence error: {e}")
            self._last_sequence = 0
    
    def _next_sequence(self) -> int:
        """Get next sequence number (thread-safe)"""
        with self._sequence_lock:
            self._last_sequence += 1
            return self._last_sequence
    
    # ===========================================
    # WRITE OPERATIONS (Append-only)
    # ===========================================
    
    def append(self, event: LedgerEvent) -> bool:
        """
        Append event to ledger.
        
        This is the ONLY write operation - no updates/deletes.
        """
        if not MONGO_AVAILABLE:
            return False
        
        try:
            # Assign sequence number
            event.sequence_number = self._next_sequence()
            
            # Convert to document
            doc = {
                "event_id": event.event_id,
                "event_type": event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
                "aggregate_type": event.aggregate_type.value if isinstance(event.aggregate_type, AggregateType) else event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "payload": event.payload,
                "source_module": event.source_module,
                "created_at": event.created_at,
                "version": event.version,
                "sequence_number": event.sequence_number,
                "metadata": event.metadata.to_dict() if event.metadata else None
            }
            
            db.event_ledger.insert_one(doc)
            return True
            
        except Exception as e:
            print(f"[LedgerRepository] Append error: {e}")
            # Rollback sequence on failure
            with self._sequence_lock:
                self._last_sequence -= 1
            return False
    
    def append_batch(self, events: List[LedgerEvent]) -> int:
        """
        Append multiple events atomically.
        
        Returns number of events successfully appended.
        """
        if not MONGO_AVAILABLE or not events:
            return 0
        
        try:
            docs = []
            for event in events:
                event.sequence_number = self._next_sequence()
                docs.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
                    "aggregate_type": event.aggregate_type.value if isinstance(event.aggregate_type, AggregateType) else event.aggregate_type,
                    "aggregate_id": event.aggregate_id,
                    "payload": event.payload,
                    "source_module": event.source_module,
                    "created_at": event.created_at,
                    "version": event.version,
                    "sequence_number": event.sequence_number,
                    "metadata": event.metadata.to_dict() if event.metadata else None
                })
            
            result = db.event_ledger.insert_many(docs, ordered=False)
            return len(result.inserted_ids)
            
        except Exception as e:
            print(f"[LedgerRepository] Batch append error: {e}")
            return 0
    
    # ===========================================
    # READ OPERATIONS
    # ===========================================
    
    def get_by_id(self, event_id: str) -> Optional[LedgerEvent]:
        """Get single event by ID"""
        if not MONGO_AVAILABLE:
            return None
        
        try:
            doc = db.event_ledger.find_one({"event_id": event_id})
            if doc:
                return self._doc_to_event(doc)
            return None
        except Exception as e:
            print(f"[LedgerRepository] Get by ID error: {e}")
            return None
    
    def get_by_sequence(self, sequence: int) -> Optional[LedgerEvent]:
        """Get event by sequence number"""
        if not MONGO_AVAILABLE:
            return None
        
        try:
            doc = db.event_ledger.find_one({"sequence_number": sequence})
            if doc:
                return self._doc_to_event(doc)
            return None
        except Exception as e:
            print(f"[LedgerRepository] Get by sequence error: {e}")
            return None
    
    def query(self, q: EventQuery) -> EventStream:
        """
        Query events with filters.
        
        Returns paginated event stream.
        """
        if not MONGO_AVAILABLE:
            return EventStream()
        
        try:
            # Build filter
            filter_doc = {}
            
            if q.aggregate_type:
                filter_doc["aggregate_type"] = q.aggregate_type
            if q.aggregate_id:
                filter_doc["aggregate_id"] = q.aggregate_id
            if q.event_type:
                filter_doc["event_type"] = q.event_type
            if q.source_module:
                filter_doc["source_module"] = q.source_module
            if q.correlation_id:
                filter_doc["metadata.correlation_id"] = q.correlation_id
            
            # Time range
            if q.from_timestamp or q.to_timestamp:
                time_filter = {}
                if q.from_timestamp:
                    time_filter["$gte"] = q.from_timestamp
                if q.to_timestamp:
                    time_filter["$lte"] = q.to_timestamp
                filter_doc["created_at"] = time_filter
            
            # Sequence range
            if q.from_sequence or q.to_sequence:
                seq_filter = {}
                if q.from_sequence:
                    seq_filter["$gte"] = q.from_sequence
                if q.to_sequence:
                    seq_filter["$lte"] = q.to_sequence
                filter_doc["sequence_number"] = seq_filter
            
            # Tags
            if q.tags:
                filter_doc["metadata.tags"] = {"$all": q.tags}
            
            # Sort direction
            sort_dir = DESCENDING if q.order == "desc" else ASCENDING
            
            # Count total
            total = db.event_ledger.count_documents(filter_doc)
            
            # Fetch events
            cursor = db.event_ledger.find(filter_doc).sort(
                "sequence_number", sort_dir
            ).skip(q.offset).limit(q.limit + 1)
            
            events = []
            has_more = False
            next_seq = 0
            
            for i, doc in enumerate(cursor):
                if i >= q.limit:
                    has_more = True
                    break
                event = self._doc_to_event(doc)
                events.append(event)
                next_seq = event.sequence_number
            
            return EventStream(
                events=events,
                total_count=total,
                has_more=has_more,
                next_sequence=next_seq
            )
            
        except Exception as e:
            print(f"[LedgerRepository] Query error: {e}")
            return EventStream()
    
    def get_aggregate_events(
        self,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 100
    ) -> List[LedgerEvent]:
        """Get all events for a specific aggregate"""
        q = EventQuery(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            limit=limit,
            order="asc"
        )
        stream = self.query(q)
        return stream.events
    
    def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> List[LedgerEvent]:
        """Get events by type"""
        q = EventQuery(event_type=event_type, limit=limit)
        stream = self.query(q)
        return stream.events
    
    def get_events_by_module(
        self,
        module: str,
        limit: int = 100
    ) -> List[LedgerEvent]:
        """Get events by source module"""
        q = EventQuery(source_module=module, limit=limit)
        stream = self.query(q)
        return stream.events
    
    def get_recent_events(self, limit: int = 50) -> List[LedgerEvent]:
        """Get most recent events"""
        q = EventQuery(limit=limit, order="desc")
        stream = self.query(q)
        return stream.events
    
    def get_events_since(
        self,
        from_sequence: int,
        limit: int = 100
    ) -> List[LedgerEvent]:
        """Get events since a sequence number (for replay)"""
        q = EventQuery(from_sequence=from_sequence, limit=limit, order="asc")
        stream = self.query(q)
        return stream.events
    
    def get_correlated_events(
        self,
        correlation_id: str,
        limit: int = 50
    ) -> List[LedgerEvent]:
        """Get all events with same correlation ID"""
        q = EventQuery(correlation_id=correlation_id, limit=limit, order="asc")
        stream = self.query(q)
        return stream.events
    
    # ===========================================
    # STATISTICS
    # ===========================================
    
    def get_stats(self) -> LedgerStats:
        """Get ledger statistics"""
        if not MONGO_AVAILABLE:
            return LedgerStats()
        
        try:
            stats = LedgerStats()
            
            # Total count
            stats.total_events = db.event_ledger.count_documents({})
            stats.last_sequence = self._last_sequence
            
            # Events by type
            pipeline = [
                {"$group": {"_id": "$event_type", "count": {"$sum": 1}}}
            ]
            for r in db.event_ledger.aggregate(pipeline):
                stats.events_by_type[r["_id"]] = r["count"]
            
            # Events by aggregate
            pipeline = [
                {"$group": {"_id": "$aggregate_type", "count": {"$sum": 1}}}
            ]
            for r in db.event_ledger.aggregate(pipeline):
                stats.events_by_aggregate[r["_id"]] = r["count"]
            
            # Events by module
            pipeline = [
                {"$group": {"_id": "$source_module", "count": {"$sum": 1}}}
            ]
            for r in db.event_ledger.aggregate(pipeline):
                stats.events_by_module[r["_id"]] = r["count"]
            
            # Oldest event
            oldest = db.event_ledger.find_one(
                {},
                {"created_at": 1},
                sort=[("sequence_number", ASCENDING)]
            )
            if oldest:
                stats.oldest_event_at = oldest.get("created_at", 0)
            
            # Newest event
            newest = db.event_ledger.find_one(
                {},
                {"created_at": 1},
                sort=[("sequence_number", DESCENDING)]
            )
            if newest:
                stats.newest_event_at = newest.get("created_at", 0)
            
            return stats
            
        except Exception as e:
            print(f"[LedgerRepository] Stats error: {e}")
            return LedgerStats()
    
    # ===========================================
    # HELPERS
    # ===========================================
    
    def _doc_to_event(self, doc: Dict) -> LedgerEvent:
        """Convert MongoDB doc to LedgerEvent"""
        from .ledger_types import EventMetadata
        
        metadata = None
        if doc.get("metadata"):
            m = doc["metadata"]
            metadata = EventMetadata(
                correlation_id=m.get("correlationId", m.get("correlation_id", "")),
                causation_id=m.get("causationId", m.get("causation_id", "")),
                user_id=m.get("userId", m.get("user_id", "")),
                ip_address=m.get("ipAddress", m.get("ip_address", "")),
                session_id=m.get("sessionId", m.get("session_id", "")),
                tags=m.get("tags", [])
            )
        
        return LedgerEvent(
            event_id=doc.get("event_id", ""),
            event_type=doc.get("event_type", "SYSTEM_STARTED"),
            aggregate_type=doc.get("aggregate_type", "SYSTEM"),
            aggregate_id=doc.get("aggregate_id", ""),
            payload=doc.get("payload", {}),
            source_module=doc.get("source_module", "system"),
            created_at=doc.get("created_at", 0),
            version=doc.get("version", 1),
            sequence_number=doc.get("sequence_number", 0),
            metadata=metadata
        )


# Global repository instance
ledger_repository = LedgerRepository()
