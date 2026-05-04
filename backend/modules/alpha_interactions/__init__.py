"""
PHASE 16 — Alpha Interaction Layer
====================================
Analyzes signal interactions: reinforcement, conflict, synergy, cancellation.

PHASE 16.1: Foundation Engine
PHASE 16.2: Reinforcement Patterns
PHASE 16.3: Conflict Patterns
PHASE 16.4: Synergy Engine
PHASE 16.5: Cancellation Engine
PHASE 16.6: Interaction Aggregator
"""

from .alpha_interaction_types import (
    InteractionState,
    AlphaInteractionState,
)

from .alpha_interaction_engine import (
    AlphaInteractionEngine,
    get_alpha_interaction_engine,
)

from .reinforcement_patterns import (
    ReinforcementPattern,
    ReinforcementPatternState,
)

from .reinforcement_patterns_engine import (
    ReinforcementPatternsEngine,
    get_reinforcement_patterns_engine,
)

from .conflict_patterns import (
    ConflictPattern,
    ConflictSeverity,
    ConflictPatternState,
)

from .conflict_patterns_engine import (
    ConflictPatternsEngine,
    get_conflict_patterns_engine,
)

from .synergy_patterns import (
    SynergyPattern,
    SynergyState,
)

from .synergy_engine import (
    SynergyEngine,
    get_synergy_engine,
)

from .cancellation_patterns import (
    CancellationPattern,
    CancellationState,
)

from .cancellation_engine import (
    CancellationEngine,
    get_cancellation_engine,
)

# PHASE 16.6: Interaction Aggregator
from .interaction_aggregator import (
    InteractionAggregator,
    AlphaInteractionAggregate,
    AggregateInteractionState,
    ExecutionModifier,
    get_interaction_aggregator,
)
