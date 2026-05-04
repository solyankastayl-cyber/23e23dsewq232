"""
Execution Brain Module

PHASE 37 — Execution Brain

Intelligent execution layer connecting:
- Decision
- Risk
- Capital
- Execution

Pipeline position:
decision → execution brain → liquidity impact → final order → execution
"""

from .execution_types import (
    ExecutionPlan,
    ExecutionType,
    RiskLevel,
    RISK_MODIFIERS,
    STOP_MULTIPLIERS,
)
from .execution_engine import (
    ExecutionBrainEngine,
    get_execution_brain_engine,
)
from .execution_router import (
    ExecutionRouter,
    get_execution_router,
)
from .execution_registry import (
    ExecutionRegistry,
    get_execution_registry,
)
from .execution_routes import router as execution_router

__all__ = [
    # Types
    "ExecutionPlan",
    "ExecutionType",
    "RiskLevel",
    "RISK_MODIFIERS",
    "STOP_MULTIPLIERS",
    # Engine
    "ExecutionBrainEngine",
    "get_execution_brain_engine",
    # Router
    "ExecutionRouter",
    "get_execution_router",
    # Registry
    "ExecutionRegistry",
    "get_execution_registry",
    # API Router
    "execution_router",
]
