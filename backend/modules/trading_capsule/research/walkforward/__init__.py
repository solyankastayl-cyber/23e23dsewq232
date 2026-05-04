"""
Walk Forward Module (S2.6)
==========================

Walk Forward analysis for strategy robustness testing.

S2.6A - Window Generator:
- Generate train/test windows
- No look-ahead bias guarantee

S2.6B - WalkForward Engine:
- Manage WF experiment lifecycle
- Execute train/test simulations

S2.6C - Robustness Analyzer:
- Compare train vs test metrics
- Calculate degradation, stability
- Determine verdict
"""

from .walkforward_types import (
    WalkForwardExperiment,
    WalkForwardWindow,
    WalkForwardRun,
    WalkForwardStatus,
    WFRunStatus,
    WindowComparison,
    StrategyRobustness,
    WalkForwardResults,
    RobustnessVerdict
)

from .window_generator import (
    WindowGenerator,
    window_generator
)

from .walkforward_engine import (
    WalkForwardEngine,
    walkforward_engine
)

from .robustness_analyzer import (
    RobustnessAnalyzer,
    robustness_analyzer
)

from .walkforward_routes import router as walkforward_router


__all__ = [
    # Types
    "WalkForwardExperiment",
    "WalkForwardWindow",
    "WalkForwardRun",
    "WalkForwardStatus",
    "WFRunStatus",
    "WindowComparison",
    "StrategyRobustness",
    "WalkForwardResults",
    "RobustnessVerdict",
    
    # Window Generator (S2.6A)
    "WindowGenerator",
    "window_generator",
    
    # WalkForward Engine (S2.6B)
    "WalkForwardEngine",
    "walkforward_engine",
    
    # Robustness Analyzer (S2.6C)
    "RobustnessAnalyzer",
    "robustness_analyzer",
    
    # Routes
    "walkforward_router"
]


print("[WalkForward] Module loaded - S2.6A/S2.6B/S2.6C Ready")
