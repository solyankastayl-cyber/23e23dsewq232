"""
PHASE 20.4 — Research Loop Aggregator Module
============================================
Unified self-improving research loop.

Components:
- research_loop_types: Type definitions
- research_loop_engine: Main aggregator engine
- research_loop_registry: State history tracking
- research_loop_routes: API endpoints
"""

from modules.research_loop.aggregator.research_loop_types import (
    LoopState,
    LoopSignal,
    ResearchLoopState,
    ResearchLoopHistoryEntry,
    LOOP_STATE_THRESHOLDS,
    LOOP_MODIFIERS,
    LOOP_SCORE_WEIGHTS,
)

from modules.research_loop.aggregator.research_loop_engine import (
    ResearchLoopEngine,
    get_research_loop_engine,
)

from modules.research_loop.aggregator.research_loop_registry import (
    ResearchLoopRegistry,
    get_research_loop_registry,
)

__all__ = [
    # Types
    "LoopState",
    "LoopSignal",
    "ResearchLoopState",
    "ResearchLoopHistoryEntry",
    "LOOP_STATE_THRESHOLDS",
    "LOOP_MODIFIERS",
    "LOOP_SCORE_WEIGHTS",
    # Engine
    "ResearchLoopEngine",
    "get_research_loop_engine",
    # Registry
    "ResearchLoopRegistry",
    "get_research_loop_registry",
]
