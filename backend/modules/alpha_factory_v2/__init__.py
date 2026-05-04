"""
PHASE 26 — Alpha Factory v2

Scalable alpha factor generation system.

Pipeline:
1. Factor Discovery → Generate candidates
2. Alpha Scoring → Evaluate quality
3. Factor Survival → Natural selection
4. Alpha Registry → Store active alpha
5. Alpha Validation → Validate stability (PHASE 26.6)

This is the core of any quant platform.
"""

from .factor_types import (
    AlphaFactor,
    FactorCandidate,
    FactorCategory,
    FactorStatus,
    AlphaFactorSummary,
)
from .factor_discovery_engine import (
    FactorDiscoveryEngine,
    get_factor_discovery_engine,
)
from .alpha_scoring_engine import (
    AlphaScoringEngine,
    get_alpha_scoring_engine,
)
from .factor_survival_engine import (
    FactorSurvivalEngine,
    get_factor_survival_engine,
    SurvivalSummary,
)
from .alpha_registry import (
    AlphaRegistry,
    get_alpha_registry,
    RegistryAlphaFactor,
    AlphaFactorHistory,
    RegistrySummary,
)
from .alpha_factory_engine import (
    AlphaFactoryEngine,
    get_alpha_factory_engine,
    AlphaFactoryResult,
    AlphaFactoryStatus,
)
from .alpha_validation_engine import (
    AlphaValidationEngine,
    get_alpha_validation_engine,
    AlphaValidationReport,
)

__all__ = [
    "AlphaFactor",
    "FactorCandidate",
    "FactorCategory",
    "FactorStatus",
    "AlphaFactorSummary",
    "FactorDiscoveryEngine",
    "get_factor_discovery_engine",
    "AlphaScoringEngine",
    "get_alpha_scoring_engine",
    "FactorSurvivalEngine",
    "get_factor_survival_engine",
    "SurvivalSummary",
    "AlphaRegistry",
    "get_alpha_registry",
    "RegistryAlphaFactor",
    "AlphaFactorHistory",
    "RegistrySummary",
    "AlphaFactoryEngine",
    "get_alpha_factory_engine",
    "AlphaFactoryResult",
    "AlphaFactoryStatus",
    "AlphaValidationEngine",
    "get_alpha_validation_engine",
    "AlphaValidationReport",
]
