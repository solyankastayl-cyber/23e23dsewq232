"""
PHASE 25.1 — Macro Context Module

Macro Intelligence layer for trading system.
Independent from TA / Exchange / Fractal.

Provides:
- MacroContext with macro state classification
- USD, Equity, Liquidity bias computation
- Context state for system integration
"""

from .macro_context_types import (
    MacroInput,
    MacroContext,
    MacroContextSummary,
    MacroHealthStatus,
    MacroStateType,
    BiasType,
    LiquidityStateType,
    ContextStateType,
)
from .macro_context_adapter import (
    MacroContextAdapter,
    get_macro_adapter,
)
from .macro_context_engine import (
    MacroContextEngine,
    get_macro_context_engine,
)
from .macro_context_routes import router as macro_context_router

__all__ = [
    # Types
    "MacroInput",
    "MacroContext",
    "MacroContextSummary",
    "MacroHealthStatus",
    "MacroStateType",
    "BiasType",
    "LiquidityStateType",
    "ContextStateType",
    # Adapter
    "MacroContextAdapter",
    "get_macro_adapter",
    # Engine
    "MacroContextEngine",
    "get_macro_context_engine",
    # Routes
    "macro_context_router",
]
