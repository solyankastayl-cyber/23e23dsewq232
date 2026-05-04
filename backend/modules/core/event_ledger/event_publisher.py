"""
Event Publisher
===============

Unified event publishing interface for all modules.

All modules should use this publisher to emit events,
ensuring consistent format and storage.
"""

import time
import uuid
import threading
from typing import Dict, Any, Optional, List, Callable
from collections import deque

from .ledger_types import (
    LedgerEvent,
    AggregateType,
    EventType,
    EventMetadata
)
from .ledger_repository import ledger_repository


class EventPublisher:
    """
    Centralized event publisher.
    
    Features:
    - Unified interface for all modules
    - Event buffering for batch writes
    - Subscriber support for projections
    - Thread-safe
    
    Usage:
    ```python
    from modules.core.event_ledger import publish_event
    
    publish_event(
        event_type="ORDER_CREATED",
        aggregate_type="ORDER",
        aggregate_id=order_id,
        payload={"symbol": "BTC", "side": "BUY"},
        source_module="execution"
    )
    ```
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
        
        # Event buffer for batch processing
        self._buffer: deque = deque(maxlen=1000)
        self._buffer_lock = threading.Lock()
        
        # Subscribers for projections
        self._subscribers: Dict[str, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        
        # Current correlation context (thread-local)
        self._correlation_context = threading.local()
        
        # Stats
        self._events_published = 0
        self._events_failed = 0
        
        self._initialized = True
        print("[EventPublisher] Initialized")
    
    def publish(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        source_module: str,
        metadata: Optional[EventMetadata] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None
    ) -> Optional[LedgerEvent]:
        """
        Publish an event to the ledger.
        
        Args:
            event_type: Type of event (e.g., "ORDER_CREATED")
            aggregate_type: Type of aggregate (e.g., "ORDER")
            aggregate_id: ID of the aggregate
            payload: Event data
            source_module: Module that generated the event
            metadata: Optional additional metadata
            correlation_id: Optional correlation ID (auto-generated if not provided)
            causation_id: Optional causation ID (previous event that caused this)
        
        Returns:
            Created LedgerEvent or None on failure
        """
        
        try:
            # Build metadata
            if not metadata:
                metadata = EventMetadata()
            
            # Use provided correlation ID or get from context
            if correlation_id:
                metadata.correlation_id = correlation_id
            elif not metadata.correlation_id:
                metadata.correlation_id = getattr(
                    self._correlation_context, 'id', None
                ) or f"corr_{uuid.uuid4().hex[:12]}"
            
            if causation_id:
                metadata.causation_id = causation_id
            
            # Create event
            event = LedgerEvent(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                source_module=source_module,
                metadata=metadata
            )
            
            # Persist to ledger
            success = ledger_repository.append(event)
            
            if success:
                self._events_published += 1
                
                # Notify subscribers
                self._notify_subscribers(event)
                
                return event
            else:
                self._events_failed += 1
                return None
            
        except Exception as e:
            print(f"[EventPublisher] Publish error: {e}")
            self._events_failed += 1
            return None
    
    def publish_batch(self, events: List[Dict[str, Any]]) -> int:
        """
        Publish multiple events at once.
        
        Args:
            events: List of event dictionaries with keys:
                    event_type, aggregate_type, aggregate_id, payload, source_module
        
        Returns:
            Number of events successfully published
        """
        
        ledger_events = []
        correlation_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        for e in events:
            metadata = EventMetadata(correlation_id=correlation_id)
            
            event = LedgerEvent(
                event_type=e.get("event_type", "SYSTEM_STARTED"),
                aggregate_type=e.get("aggregate_type", "SYSTEM"),
                aggregate_id=e.get("aggregate_id", ""),
                payload=e.get("payload", {}),
                source_module=e.get("source_module", "system"),
                metadata=metadata
            )
            ledger_events.append(event)
        
        count = ledger_repository.append_batch(ledger_events)
        
        # Notify subscribers for successful events
        for event in ledger_events[:count]:
            self._notify_subscribers(event)
        
        self._events_published += count
        return count
    
    # ===========================================
    # Correlation Context
    # ===========================================
    
    def set_correlation_context(self, correlation_id: str):
        """Set correlation ID for current thread/request"""
        self._correlation_context.id = correlation_id
    
    def get_correlation_context(self) -> Optional[str]:
        """Get current correlation ID"""
        return getattr(self._correlation_context, 'id', None)
    
    def clear_correlation_context(self):
        """Clear correlation context"""
        if hasattr(self._correlation_context, 'id'):
            del self._correlation_context.id
    
    # ===========================================
    # Subscribers (for projections)
    # ===========================================
    
    def subscribe(
        self,
        callback: Callable[[LedgerEvent], None],
        event_types: Optional[List[str]] = None
    ):
        """
        Subscribe to events.
        
        Args:
            callback: Function to call with each event
            event_types: Optional list of event types to filter.
                        If None, receives all events.
        """
        if event_types:
            for event_type in event_types:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(callback)
        else:
            self._global_subscribers.append(callback)
    
    def _notify_subscribers(self, event: LedgerEvent):
        """Notify all relevant subscribers"""
        # Type-specific subscribers
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[EventPublisher] Subscriber error: {e}")
        
        # Global subscribers
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventPublisher] Global subscriber error: {e}")
    
    # ===========================================
    # Stats
    # ===========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics"""
        return {
            "eventsPublished": self._events_published,
            "eventsFailed": self._events_failed,
            "subscribersByType": {k: len(v) for k, v in self._subscribers.items()},
            "globalSubscribers": len(self._global_subscribers)
        }


# Global publisher instance
event_publisher = EventPublisher()


# Convenience function for simple publishing
def publish_event(
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
    source_module: str,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Optional[LedgerEvent]:
    """
    Convenience function to publish an event.
    
    Example:
    ```python
    publish_event(
        event_type="ORDER_FILLED",
        aggregate_type="ORDER",
        aggregate_id="ord_123",
        payload={"symbol": "BTC", "price": 64200, "size": 0.25},
        source_module="execution"
    )
    ```
    """
    metadata = None
    if tags:
        metadata = EventMetadata(tags=tags)
    
    return event_publisher.publish(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        source_module=source_module,
        metadata=metadata,
        correlation_id=correlation_id,
        causation_id=causation_id
    )
