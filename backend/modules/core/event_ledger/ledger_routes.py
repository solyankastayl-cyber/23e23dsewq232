"""
Event Ledger Routes
===================

API endpoints for event ledger operations.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .ledger_service import ledger_service
from .ledger_types import EventType, AggregateType


router = APIRouter(prefix="/api/ledger", tags=["event-ledger"])


# ===========================================
# Request/Response Models
# ===========================================

class PublishEventRequest(BaseModel):
    """Request to publish a single event"""
    eventType: str = Field(..., description="Event type (e.g., ORDER_CREATED)")
    aggregateType: str = Field(..., description="Aggregate type (e.g., ORDER)")
    aggregateId: str = Field(..., description="Aggregate ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    sourceModule: str = Field(..., description="Source module")
    correlationId: Optional[str] = None
    causationId: Optional[str] = None
    tags: Optional[List[str]] = None


class PublishBatchRequest(BaseModel):
    """Request to publish multiple events"""
    events: List[Dict[str, Any]] = Field(..., description="List of events")


class QueryEventsRequest(BaseModel):
    """Request to query events"""
    aggregateType: Optional[str] = None
    aggregateId: Optional[str] = None
    eventType: Optional[str] = None
    sourceModule: Optional[str] = None
    fromTimestamp: Optional[int] = None
    toTimestamp: Optional[int] = None
    correlationId: Optional[str] = None
    limit: int = Field(default=100, le=500)
    offset: int = Field(default=0)
    order: str = Field(default="desc")


# ===========================================
# Health & Stats
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for event ledger"""
    return ledger_service.get_health()


@router.get("/stats")
async def get_stats():
    """Get ledger statistics"""
    stats = ledger_service.get_stats()
    return stats.to_dict()


@router.get("/publisher/stats")
async def get_publisher_stats():
    """Get publisher statistics"""
    return ledger_service.get_publisher_stats()


# ===========================================
# Publish Events
# ===========================================

@router.post("/events")
async def publish_event(request: PublishEventRequest):
    """
    Publish a single event to the ledger.
    
    Events are immutable once published.
    """
    event = ledger_service.publish(
        event_type=request.eventType,
        aggregate_type=request.aggregateType,
        aggregate_id=request.aggregateId,
        payload=request.payload,
        source_module=request.sourceModule,
        correlation_id=request.correlationId,
        causation_id=request.causationId,
        tags=request.tags
    )
    
    if event:
        return {
            "success": True,
            "event": event.to_dict()
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to publish event")


@router.post("/events/batch")
async def publish_batch(request: PublishBatchRequest):
    """
    Publish multiple events at once.
    
    All events will share a correlation ID.
    """
    count = ledger_service.publish_batch(request.events)
    return {
        "success": True,
        "publishedCount": count,
        "totalRequested": len(request.events)
    }


# ===========================================
# Query Events
# ===========================================

@router.get("/events")
async def get_events(
    aggregate_type: Optional[str] = Query(None),
    aggregate_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    source_module: Optional[str] = Query(None),
    from_timestamp: Optional[int] = Query(None),
    to_timestamp: Optional[int] = Query(None),
    correlation_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    order: str = Query("desc")
):
    """
    Query events with filters.
    
    All filters are optional. Returns paginated results.
    """
    stream = ledger_service.get_events(
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
    return stream.to_dict()


@router.post("/events/query")
async def query_events(request: QueryEventsRequest):
    """Query events with POST body (for complex queries)"""
    stream = ledger_service.get_events(
        aggregate_type=request.aggregateType,
        aggregate_id=request.aggregateId,
        event_type=request.eventType,
        source_module=request.sourceModule,
        from_timestamp=request.fromTimestamp,
        to_timestamp=request.toTimestamp,
        correlation_id=request.correlationId,
        limit=request.limit,
        offset=request.offset,
        order=request.order
    )
    return stream.to_dict()


@router.get("/events/recent")
async def get_recent_events(limit: int = Query(50, le=200)):
    """Get most recent events"""
    events = ledger_service.get_recent_events(limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get single event by ID"""
    event = ledger_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


# ===========================================
# Registry (MUST be before dynamic routes)
# ===========================================

@router.get("/registry/event-types")
async def get_event_types():
    """Get all supported event types"""
    return {
        "eventTypes": [
            {"id": e.value, "name": e.name}
            for e in EventType
        ]
    }


@router.get("/registry/aggregate-types")
async def get_aggregate_types():
    """Get all supported aggregate types"""
    return {
        "aggregateTypes": [
            {"id": a.value, "name": a.name}
            for a in AggregateType
        ]
    }


# ===========================================
# Type & Module Queries (MUST be before /{aggregate_type})
# ===========================================

@router.get("/type/{event_type}")
async def get_events_by_type(
    event_type: str,
    limit: int = Query(100, le=500)
):
    """Get events by type"""
    events = ledger_service.get_events_by_type(event_type, limit)
    return {
        "eventType": event_type,
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


@router.get("/module/{module}")
async def get_events_by_module(
    module: str,
    limit: int = Query(100, le=500)
):
    """Get events by source module"""
    events = ledger_service.get_events_by_module(module, limit)
    return {
        "module": module,
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


# ===========================================
# Aggregate Queries (generic - must be last)
# ===========================================

@router.get("/{aggregate_type}/{aggregate_id}")
async def get_aggregate_events(
    aggregate_type: str,
    aggregate_id: str,
    limit: int = Query(100, le=500)
):
    """
    Get all events for a specific aggregate.
    
    Example: /api/ledger/ORDER/ord_123
    """
    events = ledger_service.get_aggregate_events(aggregate_type, aggregate_id, limit)
    return {
        "aggregateType": aggregate_type,
        "aggregateId": aggregate_id,
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


# ===========================================
# Correlation & Causality
# ===========================================

@router.get("/correlation/{correlation_id}")
async def get_correlated_events(
    correlation_id: str,
    limit: int = Query(50, le=200)
):
    """
    Get all events with the same correlation ID.
    
    This shows the complete causality chain.
    """
    events = ledger_service.get_correlated_events(correlation_id, limit)
    return {
        "correlationId": correlation_id,
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "chain": _build_causality_chain(events)
    }


def _build_causality_chain(events) -> List[Dict]:
    """Build simplified causality chain"""
    return [
        {
            "sequence": e.sequence_number,
            "type": e.event_type.value if hasattr(e.event_type, 'value') else e.event_type,
            "aggregate": f"{e.aggregate_type}:{e.aggregate_id}",
            "time": e.created_at
        }
        for e in events
    ]


# ===========================================
# Replay
# ===========================================

@router.get("/replay")
async def replay_events(
    from_sequence: int = Query(0),
    limit: int = Query(100, le=1000)
):
    """
    Get events for replay starting from sequence number.
    
    Used for state reconstruction.
    """
    events = ledger_service.replay_events(from_sequence, limit)
    
    next_seq = events[-1].sequence_number if events else from_sequence
    
    return {
        "fromSequence": from_sequence,
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "nextSequence": next_seq + 1 if events else from_sequence,
        "hasMore": len(events) >= limit
    }


# ===========================================
# Projections
# ===========================================

@router.get("/projections")
async def get_all_projections():
    """Get summary of all projections"""
    return ledger_service.get_all_projections()


@router.get("/projections/{name}")
async def get_projection(name: str):
    """Get specific projection state"""
    proj = ledger_service.get_projection(name)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Projection '{name}' not found")
    return proj


@router.get("/projections/view/recent-events")
async def projection_recent_events(limit: int = Query(50, le=100)):
    """Get recent events from projection (fast read)"""
    return {
        "events": ledger_service.get_recent_events_summary(limit)
    }


@router.get("/projections/view/positions")
async def projection_positions():
    """Get current positions from projection"""
    return ledger_service.get_current_positions()


@router.get("/projections/view/orders")
async def projection_orders():
    """Get active orders from projection"""
    return ledger_service.get_active_orders()


@router.get("/projections/view/risk-alerts")
async def projection_risk_alerts():
    """Get risk alerts from projection"""
    return ledger_service.get_risk_alerts()


@router.get("/projections/view/strategy")
async def projection_strategy():
    """Get strategy state from projection"""
    return ledger_service.get_strategy_state()


@router.get("/projections/view/recon")
async def projection_recon():
    """Get reconciliation status from projection"""
    return ledger_service.get_recon_status()
