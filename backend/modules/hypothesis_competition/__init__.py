"""
Hypothesis Competition

PHASE 30.1 — Hypothesis Pool Engine
PHASE 30.2 — Hypothesis Ranking Engine
PHASE 30.3 — Capital Allocation Engine
PHASE 30.4 — Outcome Tracking Engine
PHASE 30.5 — Adaptive Weight Engine

Transforms system from single-hypothesis to multi-hypothesis mode
with diversification logic, capital allocation, self-learning, and adaptive weights.
"""

from .hypothesis_pool_engine import (
    HypothesisPoolEngine,
    get_hypothesis_pool_engine,
)
from .hypothesis_ranking_engine import (
    HypothesisRankingEngine,
    get_hypothesis_ranking_engine,
    RankedHypothesisPool,
)
from .capital_allocation_engine import (
    CapitalAllocationEngine,
    get_capital_allocation_engine,
)
from .outcome_tracking_engine import (
    OutcomeTrackingEngine,
    get_outcome_tracking_engine,
)
from .adaptive_weight_engine import (
    AdaptiveWeightEngine,
    get_adaptive_weight_engine,
)
from .hypothesis_pool_registry import (
    HypothesisPoolRegistry,
    get_hypothesis_pool_registry,
)
from .capital_allocation_registry import (
    CapitalAllocationRegistry,
    get_capital_allocation_registry,
)
from .outcome_tracking_registry import (
    OutcomeTrackingRegistry,
    get_outcome_tracking_registry,
)
from .adaptive_weight_registry import (
    AdaptiveWeightRegistry,
    get_adaptive_weight_registry,
)
from .hypothesis_pool_routes import router as hypothesis_pool_router
from .hypothesis_ranking_routes import router as hypothesis_ranking_router
from .capital_allocation_routes import router as capital_allocation_router
from .outcome_tracking_routes import router as outcome_tracking_router
from .adaptive_weight_routes import router as adaptive_weight_router
from .hypothesis_pool_types import (
    HypothesisPoolItem,
    HypothesisPool,
    HypothesisPoolSummary,
    HypothesisPoolHistoryRecord,
    CONFIDENCE_THRESHOLD,
    RELIABILITY_THRESHOLD,
    MAX_POOL_SIZE,
)
from .capital_allocation_types import (
    HypothesisAllocation,
    HypothesisCapitalAllocation,
    CapitalAllocationSummary,
    EXECUTION_STATE_MODIFIERS,
    MAX_DIRECTIONAL_EXPOSURE,
    MAX_NEUTRAL_ALLOCATION,
    MIN_ALLOCATION_THRESHOLD,
)
from .outcome_tracking_types import (
    HypothesisOutcome,
    HypothesisPerformance,
    SymbolOutcomeSummary,
    EVALUATION_HORIZONS,
    SUCCESS_TOLERANCE,
    NEUTRAL_VOLATILITY_THRESHOLD,
)
from .adaptive_weight_types import (
    HypothesisAdaptiveWeight,
    AdaptiveWeightSummary,
    MIN_OBSERVATIONS,
    SUCCESS_MODIFIER_MIN,
    SUCCESS_MODIFIER_MAX,
    COMBINED_MODIFIER_MIN,
    COMBINED_MODIFIER_MAX,
)

__all__ = [
    # Pool Engine
    "HypothesisPoolEngine",
    "get_hypothesis_pool_engine",
    # Ranking Engine
    "HypothesisRankingEngine",
    "get_hypothesis_ranking_engine",
    "RankedHypothesisPool",
    # Capital Allocation Engine
    "CapitalAllocationEngine",
    "get_capital_allocation_engine",
    # Outcome Tracking Engine
    "OutcomeTrackingEngine",
    "get_outcome_tracking_engine",
    # Adaptive Weight Engine
    "AdaptiveWeightEngine",
    "get_adaptive_weight_engine",
    # Registries
    "HypothesisPoolRegistry",
    "get_hypothesis_pool_registry",
    "CapitalAllocationRegistry",
    "get_capital_allocation_registry",
    "OutcomeTrackingRegistry",
    "get_outcome_tracking_registry",
    "AdaptiveWeightRegistry",
    "get_adaptive_weight_registry",
    # Routers
    "hypothesis_pool_router",
    "hypothesis_ranking_router",
    "capital_allocation_router",
    "outcome_tracking_router",
    "adaptive_weight_router",
    # Pool Types
    "HypothesisPoolItem",
    "HypothesisPool",
    "HypothesisPoolSummary",
    "HypothesisPoolHistoryRecord",
    "CONFIDENCE_THRESHOLD",
    "RELIABILITY_THRESHOLD",
    "MAX_POOL_SIZE",
    # Allocation Types
    "HypothesisAllocation",
    "HypothesisCapitalAllocation",
    "CapitalAllocationSummary",
    "EXECUTION_STATE_MODIFIERS",
    "MAX_DIRECTIONAL_EXPOSURE",
    "MAX_NEUTRAL_ALLOCATION",
    "MIN_ALLOCATION_THRESHOLD",
    # Outcome Types
    "HypothesisOutcome",
    "HypothesisPerformance",
    "SymbolOutcomeSummary",
    "EVALUATION_HORIZONS",
    "SUCCESS_TOLERANCE",
    "NEUTRAL_VOLATILITY_THRESHOLD",
    # Adaptive Weight Types
    "HypothesisAdaptiveWeight",
    "AdaptiveWeightSummary",
    "MIN_OBSERVATIONS",
    "SUCCESS_MODIFIER_MIN",
    "SUCCESS_MODIFIER_MAX",
    "COMBINED_MODIFIER_MIN",
    "COMBINED_MODIFIER_MAX",
]
