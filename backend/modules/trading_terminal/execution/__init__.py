"""
Execution Module for Trading Terminal
=====================================

Provides execution lifecycle management:
- ExecutionIntent: bridge between decision and order
- OrderState: order lifecycle tracking  
- ExecutionStateEngine: main orchestrator
- Execution Routes: API endpoints
"""

from .execution_models import (
    ExecutionIntent,
    OrderState,
    ExecutionStatusSummary,
    ExecutionState,
    utc_now,
)
from .order_state_machine import OrderStateMachine
from .execution_repository import ExecutionRepository, get_execution_repository
from .execution_state_engine import ExecutionStateEngine, get_execution_engine
from .execution_routes import router as execution_router

__all__ = [
    # Models
    "ExecutionIntent",
    "OrderState",
    "ExecutionStatusSummary",
    "ExecutionState",
    "utc_now",
    
    # State Machine
    "OrderStateMachine",
    
    # Repository
    "ExecutionRepository",
    "get_execution_repository",
    
    # Engine
    "ExecutionStateEngine",
    "get_execution_engine",
    
    # Router
    "execution_router",
]
