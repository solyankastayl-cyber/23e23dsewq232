"""
Event Ledger Module
===================

Immutable, append-only event store for complete trading system audit trail.

Purpose:
- Full causality chain for every action
- State reconstruction capability
- Forensic analysis support
- Audit compliance
- Event replay for debugging

Events are:
- Immutable (no updates/deletes)
- Append-only
- Timestamped
- Typed
- Queryable by aggregate, type, module

Architecture:
```
Strategy  Execution  Risk  Security  Reconciliation
    ↓          ↓       ↓        ↓            ↓
              Event Publisher
                    ↓
               Event Ledger
                    ↓
            Projection Service
                    ↓
             Fast Read Models
```
"""

from .ledger_types import (
    LedgerEvent,
    AggregateType,
    EventType,
    EventMetadata
)
from .event_publisher import event_publisher, publish_event
from .ledger_service import ledger_service

__all__ = [
    'LedgerEvent',
    'AggregateType', 
    'EventType',
    'EventMetadata',
    'event_publisher',
    'publish_event',
    'ledger_service'
]
