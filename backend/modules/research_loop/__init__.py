"""
Research Loop Module
====================

Phase 9.33 - Automated research cycle engine.
Phase 20.1 - Failure Pattern Engine.
"""

from .types import (
    LoopConfig, LoopCycleResult, LoopState, LoopEvent, LoopMetrics,
    LoopPhase, LoopMode, LoopStatus
)
from .engine import research_loop_engine, ResearchLoopEngine
from .routes import router

# PHASE 20.1 - Failure Patterns
from .failure_patterns import (
    FailurePattern,
    FailurePatternSummary,
    TradeRecord,
    TradeOutcome,
    PatternSeverity,
    get_failure_pattern_engine,
)

__all__ = [
    "LoopConfig",
    "LoopCycleResult",
    "LoopState",
    "LoopEvent",
    "LoopMetrics",
    "LoopPhase",
    "LoopMode",
    "LoopStatus",
    "research_loop_engine",
    "ResearchLoopEngine",
    "router",
    # PHASE 20.1
    "FailurePattern",
    "FailurePatternSummary",
    "TradeRecord",
    "TradeOutcome",
    "PatternSeverity",
    "get_failure_pattern_engine",
]
