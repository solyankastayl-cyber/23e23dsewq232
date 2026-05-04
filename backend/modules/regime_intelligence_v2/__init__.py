"""
Regime Intelligence v2

Market regime detection for strategy allocation and execution.

Components:
- regime_types: Contracts and constants
- regime_detection_engine: Core detection logic
- regime_registry: History storage
- regime_routes: API endpoints
- strategy_regime_*: Strategy-regime mapping (PHASE 27.2)

Regime Types:
- TRENDING: Strong directional movement
- RANGING: Sideways consolidation
- VOLATILE: High volatility environment
- ILLIQUID: Low liquidity conditions
"""

from .regime_types import (
    MarketRegime,
    RegimeHistoryRecord,
    RegimeSummary,
    RegimeInputMetrics,
    RegimeType,
    ContextState,
    DominantDriver,
    TREND_STRONG_THRESHOLD,
    TREND_WEAK_THRESHOLD,
    VOLATILITY_LOW_THRESHOLD,
    VOLATILITY_MEDIUM_THRESHOLD,
    VOLATILITY_HIGH_THRESHOLD,
    LIQUIDITY_LOW_THRESHOLD,
)
from .regime_detection_engine import (
    RegimeDetectionEngine,
    get_regime_detection_engine,
)
from .regime_registry import (
    RegimeRegistry,
    get_regime_registry,
)
from .regime_routes import router as regime_router

# PHASE 27.2 — Strategy Regime Mapping
from .strategy_regime_types import (
    StrategyRegimeMapping,
    RegimeStrategySummary,
    StrategyRegimeHistoryRecord,
    StrategyType,
    MappingState,
    STRATEGY_LIST,
    SUITABILITY_RANGES,
    STATE_MODIFIERS,
    REGIME_STRATEGY_MATRIX,
)
from .strategy_regime_mapping_engine import (
    StrategyRegimeMappingEngine,
    get_strategy_regime_mapping_engine,
)
from .strategy_regime_registry import (
    StrategyRegimeRegistry,
    get_strategy_regime_registry,
)
from .strategy_regime_routes import router as strategy_regime_router

# PHASE 27.3 — Regime Transition Detector
from .regime_transition_types import (
    RegimeTransitionState,
    TransitionHistoryRecord,
    TransitionSummary,
    RegimeMetricSnapshot,
    TransitionState,
    NextRegimeCandidate,
    STABLE_THRESHOLD,
    EARLY_SHIFT_THRESHOLD,
    ACTIVE_TRANSITION_THRESHOLD,
    TRANSITION_MODIFIERS,
)
from .regime_transition_engine import (
    RegimeTransitionEngine,
    get_regime_transition_engine,
)
from .regime_transition_registry import (
    RegimeTransitionRegistry,
    get_regime_transition_registry,
)
from .regime_transition_routes import router as transition_router

# PHASE 27.4 — Regime Context (Unified)
from .regime_context_types import (
    RegimeContext,
    RegimeContextSummary,
)
from .regime_context_engine import (
    RegimeContextEngine,
    get_regime_context_engine,
)
from .regime_context_routes import router as context_router

__all__ = [
    # Types
    "MarketRegime",
    "RegimeHistoryRecord",
    "RegimeSummary",
    "RegimeInputMetrics",
    "RegimeType",
    "ContextState",
    "DominantDriver",
    # Constants
    "TREND_STRONG_THRESHOLD",
    "TREND_WEAK_THRESHOLD",
    "VOLATILITY_LOW_THRESHOLD",
    "VOLATILITY_MEDIUM_THRESHOLD",
    "VOLATILITY_HIGH_THRESHOLD",
    "LIQUIDITY_LOW_THRESHOLD",
    # Engine
    "RegimeDetectionEngine",
    "get_regime_detection_engine",
    # Registry
    "RegimeRegistry",
    "get_regime_registry",
    # Routes
    "regime_router",
    # Strategy Mapping Types
    "StrategyRegimeMapping",
    "RegimeStrategySummary",
    "StrategyRegimeHistoryRecord",
    "StrategyType",
    "MappingState",
    "STRATEGY_LIST",
    "SUITABILITY_RANGES",
    "STATE_MODIFIERS",
    "REGIME_STRATEGY_MATRIX",
    # Strategy Mapping Engine
    "StrategyRegimeMappingEngine",
    "get_strategy_regime_mapping_engine",
    # Strategy Registry
    "StrategyRegimeRegistry",
    "get_strategy_regime_registry",
    # Strategy Routes
    "strategy_regime_router",
    # Transition Types
    "RegimeTransitionState",
    "TransitionHistoryRecord",
    "TransitionSummary",
    "RegimeMetricSnapshot",
    "TransitionState",
    "NextRegimeCandidate",
    "STABLE_THRESHOLD",
    "EARLY_SHIFT_THRESHOLD",
    "ACTIVE_TRANSITION_THRESHOLD",
    "TRANSITION_MODIFIERS",
    # Transition Engine
    "RegimeTransitionEngine",
    "get_regime_transition_engine",
    # Transition Registry
    "RegimeTransitionRegistry",
    "get_regime_transition_registry",
    # Transition Routes
    "transition_router",
    # Context Types
    "RegimeContext",
    "RegimeContextSummary",
    # Context Engine
    "RegimeContextEngine",
    "get_regime_context_engine",
    # Context Routes
    "context_router",
]
