"""
Event Ledger Service
====================

Main service for event ledger operations.
Combines repository, publisher, and projections.
"""

import time
import threading
from typing import Dict, List, Any, Optional

from .ledger_types import (
    LedgerEvent,
    EventQuery,
    EventStream,
    LedgerStats,
    AggregateType,
    EventType,
    EventMetadata
)
from .ledger_repository import ledger_repository
from .event_publisher import event_publisher, publish_event
from .projection_service import projection_service


class LedgerService:
    """
    Main ledger service providing unified access to:
    - Event publishing
    - Event querying
    - Projections
    - Statistics
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
        
        self._initialized = True
        print("[LedgerService] Initialized (Event Ledger)")
    
    # ===========================================
    # Publishing
    # ===========================================
    
    def publish(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        source_module: str,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[LedgerEvent]:
        """Publish event to ledger"""
        return publish_event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            source_module=source_module,
            correlation_id=correlation_id,
            causation_id=causation_id,
            tags=tags
        )
    
    def publish_batch(self, events: List[Dict[str, Any]]) -> int:
        """Publish multiple events"""
        return event_publisher.publish_batch(events)
    
    # ===========================================
    # Querying
    # ===========================================
    
    def get_event(self, event_id: str) -> Optional[LedgerEvent]:
        """Get single event by ID"""
        return ledger_repository.get_by_id(event_id)
    
    def get_events(
        self,
        aggregate_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        source_module: Optional[str] = None,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc"
    ) -> EventStream:
        """Query events with filters"""
        query = EventQuery(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            source_module=source_module,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            correlation_id=correlation_id,
            limit=limit,
            offset=offset,
            order=order
        )
        return ledger_repository.query(query)
    
    def get_aggregate_events(
        self,
        aggregate_type: str,
        aggregate_id: str,
        limit: int = 100
    ) -> List[LedgerEvent]:
        """Get all events for an aggregate"""
        return ledger_repository.get_aggregate_events(aggregate_type, aggregate_id, limit)
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[LedgerEvent]:
        """Get events by type"""
        return ledger_repository.get_events_by_type(event_type, limit)
    
    def get_events_by_module(self, module: str, limit: int = 100) -> List[LedgerEvent]:
        """Get events by source module"""
        return ledger_repository.get_events_by_module(module, limit)
    
    def get_recent_events(self, limit: int = 50) -> List[LedgerEvent]:
        """Get most recent events"""
        return ledger_repository.get_recent_events(limit)
    
    def get_correlated_events(self, correlation_id: str, limit: int = 50) -> List[LedgerEvent]:
        """Get all events with same correlation ID (causality chain)"""
        return ledger_repository.get_correlated_events(correlation_id, limit)
    
    def replay_events(self, from_sequence: int, limit: int = 1000) -> List[LedgerEvent]:
        """Get events for replay (from sequence forward)"""
        return ledger_repository.get_events_since(from_sequence, limit)
    
    # ===========================================
    # Projections
    # ===========================================
    
    def get_projection(self, name: str) -> Optional[Dict[str, Any]]:
        """Get projection state"""
        return projection_service.get_projection(name)
    
    def get_all_projections(self) -> Dict[str, Any]:
        """Get all projection summaries"""
        return projection_service.get_all_projections()
    
    # Convenience projection accessors
    
    def get_recent_events_summary(self, limit: int = 50) -> List[Dict]:
        """Get recent events from projection (fast read)"""
        return projection_service.get_recent_events(limit)
    
    def get_current_positions(self) -> Dict[str, Any]:
        """Get current positions from projection"""
        return projection_service.get_current_positions()
    
    def get_active_orders(self) -> Dict[str, Any]:
        """Get active orders from projection"""
        return projection_service.get_active_orders()
    
    def get_risk_alerts(self) -> Dict[str, Any]:
        """Get risk alerts from projection"""
        return projection_service.get_risk_alerts()
    
    def get_strategy_state(self) -> Dict[str, Any]:
        """Get strategy state from projection"""
        return projection_service.get_strategy_state()
    
    def get_recon_status(self) -> Dict[str, Any]:
        """Get reconciliation status from projection"""
        return projection_service.get_recon_status()
    
    # ===========================================
    # Statistics
    # ===========================================
    
    def get_stats(self) -> LedgerStats:
        """Get ledger statistics"""
        return ledger_repository.get_stats()
    
    def get_publisher_stats(self) -> Dict[str, Any]:
        """Get publisher statistics"""
        return event_publisher.get_stats()
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        stats = self.get_stats()
        pub_stats = self.get_publisher_stats()
        
        return {
            "module": "Event Ledger",
            "status": "healthy",
            "totalEvents": stats.total_events,
            "lastSequence": stats.last_sequence,
            "eventsPublished": pub_stats.get("eventsPublished", 0),
            "eventsFailed": pub_stats.get("eventsFailed", 0),
            "projections": len(self.get_all_projections()),
            "aggregateTypes": list(stats.events_by_aggregate.keys()),
            "eventTypes": len(stats.events_by_type),
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Correlation Context
    # ===========================================
    
    def start_correlation(self, correlation_id: Optional[str] = None) -> str:
        """Start a new correlation context"""
        import uuid
        corr_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        event_publisher.set_correlation_context(corr_id)
        return corr_id
    
    def end_correlation(self):
        """End current correlation context"""
        event_publisher.clear_correlation_context()
    
    def get_current_correlation(self) -> Optional[str]:
        """Get current correlation ID"""
        return event_publisher.get_correlation_context()


# Global service instance
ledger_service = LedgerService()
