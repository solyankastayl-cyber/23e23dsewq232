"""
PHASE 20.1 — Failure Pattern Module
===================================
"""

from modules.research_loop.failure_patterns.failure_pattern_types import (
    FailurePattern,
    FailurePatternSummary,
    TradeRecord,
    TradeOutcome,
    PatternSeverity,
    SEVERITY_THRESHOLDS,
)
from modules.research_loop.failure_patterns.failure_pattern_registry import (
    FailurePatternRegistry,
    get_failure_pattern_registry,
    PATTERN_TEMPLATES,
)
from modules.research_loop.failure_patterns.failure_pattern_engine import (
    FailurePatternEngine,
    get_failure_pattern_engine,
)

__all__ = [
    "FailurePattern",
    "FailurePatternSummary",
    "TradeRecord",
    "TradeOutcome",
    "PatternSeverity",
    "SEVERITY_THRESHOLDS",
    "FailurePatternRegistry",
    "get_failure_pattern_registry",
    "PATTERN_TEMPLATES",
    "FailurePatternEngine",
    "get_failure_pattern_engine",
]
