"""
Hypothesis Engine

PHASE 29.1 — Hypothesis Contract + Core Engine
PHASE 29.2 — Hypothesis Scoring Engine
PHASE 29.3 — Hypothesis Conflict Resolver
PHASE 29.4 — Hypothesis Registry / History

Generates market hypotheses from intelligence layers:
- AlphaFactory
- RegimeContext
- MicrostructureContext
- MacroFractalContext

Scoring components (29.2):
- structural_score: idea quality
- execution_score: execution safety
- conflict_score: layer disagreement

Conflict Resolution (29.3):
- conflict_state: LOW/MODERATE/HIGH classification
- Automatic confidence/reliability adjustment
- Execution state downgrade on high conflict

Registry / History (29.4):
- Persistent MongoDB storage
- Full hypothesis history tracking
- Statistics and analytics
- Price tracking for outcome analysis
"""

from .hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)
from .hypothesis_scoring_engine import (
    HypothesisScoringEngine,
    get_hypothesis_scoring_engine,
)
from .hypothesis_conflict_resolver import (
    HypothesisConflictResolver,
    get_hypothesis_conflict_resolver,
    ConflictState,
    ConflictResolutionResult,
)
from .hypothesis_registry import (
    HypothesisRegistry,
    get_hypothesis_registry,
    HypothesisHistoryRecordExtended,
    HypothesisStats,
    HypothesisOutcome,
)
from .hypothesis_routes import router as hypothesis_router
from .hypothesis_types import (
    MarketHypothesis,
    HypothesisCandidate,
    HypothesisInputLayers,
    HypothesisHistoryRecord,
    HypothesisSummary,
)

__all__ = [
    "HypothesisEngine",
    "get_hypothesis_engine",
    "HypothesisScoringEngine",
    "get_hypothesis_scoring_engine",
    "HypothesisConflictResolver",
    "get_hypothesis_conflict_resolver",
    "ConflictState",
    "ConflictResolutionResult",
    "HypothesisRegistry",
    "get_hypothesis_registry",
    "HypothesisHistoryRecordExtended",
    "HypothesisStats",
    "HypothesisOutcome",
    "hypothesis_router",
    "MarketHypothesis",
    "HypothesisCandidate",
    "HypothesisInputLayers",
    "HypothesisHistoryRecord",
    "HypothesisSummary",
]
