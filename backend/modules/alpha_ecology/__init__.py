"""
PHASE 15 — Alpha Ecology Layer (COMPLETE)
==========================================
Signal lifecycle analysis for institutional-grade trading.

Modules:
- alpha_decay_engine: Signal performance degradation tracking (15.1)
- alpha_crowding_engine: Market crowding detection (15.2)
- alpha_correlation_engine: Signal correlation analysis (15.3)
- alpha_redundancy_engine: Signal redundancy detection (15.4)
- alpha_survival_engine: Cross-regime signal survival (15.5)
- alpha_ecology_engine: Unified ecology aggregator (15.6)

Key Principle:
    Alpha Ecology does NOT create signals.
    It modifies risk based on signal health.
"""

from modules.alpha_ecology.alpha_decay_engine import (
    get_alpha_decay_engine,
    AlphaDecayEngine,
)
from modules.alpha_ecology.alpha_crowding_engine import (
    get_alpha_crowding_engine,
    AlphaCrowdingEngine,
)
from modules.alpha_ecology.alpha_correlation_engine import (
    get_alpha_correlation_engine,
    AlphaCorrelationEngine,
)
from modules.alpha_ecology.alpha_redundancy_engine import (
    get_alpha_redundancy_engine,
    AlphaRedundancyEngine,
)
from modules.alpha_ecology.alpha_survival_engine import (
    get_alpha_survival_engine,
    AlphaSurvivalEngine,
)
from modules.alpha_ecology.alpha_ecology_engine import (
    get_alpha_ecology_engine,
    AlphaEcologyEngine,
    EcologyState,
)
from modules.alpha_ecology.alpha_ecology_types import (
    DecayState,
    CrowdingState,
    CorrelationState,
    RedundancyState,
    SurvivalState,
    SignalDecayResult,
)

__all__ = [
    # Engines
    "get_alpha_decay_engine",
    "AlphaDecayEngine",
    "get_alpha_crowding_engine",
    "AlphaCrowdingEngine",
    "get_alpha_correlation_engine",
    "AlphaCorrelationEngine",
    "get_alpha_redundancy_engine",
    "AlphaRedundancyEngine",
    "get_alpha_survival_engine",
    "AlphaSurvivalEngine",
    "get_alpha_ecology_engine",
    "AlphaEcologyEngine",
    # States
    "DecayState",
    "CrowdingState",
    "CorrelationState",
    "RedundancyState",
    "SurvivalState",
    "EcologyState",
    "SignalDecayResult",
]
