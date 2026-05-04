"""
PHASE 4.1 - Order State Engine
==============================

Execution hardening: Order lifecycle management.

Modules:
- order_state_machine.py - State machine for order lifecycle
- order_tracker.py - Order tracking and management
- order_repository.py - Data persistence
- order_events.py - Execution events
- order_routes.py - API endpoints

Order Flow:
NEW -> SUBMITTED -> ACCEPTED -> PARTIAL_FILL -> FILLED
                            -> REJECTED
                            -> CANCELLED
                            -> FAILED
"""

from .order_state_machine import OrderStateMachine, order_state_machine
from .order_tracker import OrderTracker, order_tracker
from .order_events import OrderEventEmitter, order_event_emitter
from .order_repository import order_repository

__all__ = [
    "OrderStateMachine",
    "order_state_machine",
    "OrderTracker",
    "order_tracker",
    "OrderEventEmitter",
    "order_event_emitter",
    "order_repository"
]
