"""
PHASE 3.5.4 — Advanced Market Context Pack
==========================================

Расширенный рыночный контекст для усиления сигналов:
- Funding Context Engine
- Open Interest Context Engine
- Volatility Context Engine
- Macro Context Engine
- Volume Profile Engine
- Context Aggregator

Интеграция с:
- Alpha Engine
- Signal Ensemble
- Market Structure
- Strategy Selection
- Quality Score
- Dynamic Risk
"""

from .context_types import (
    FundingState,
    OIState,
    VolatilityRegime,
    MacroRegime,
    RiskEnvironment,
    VolumeProfileBias,
    FundingContext,
    OIContext,
    VolatilityContext,
    MacroContext,
    VolumeProfileContext,
    MarketContextSnapshot,
    ContextHistoryQuery
)
from .funding_context_engine import FundingContextEngine
from .oi_context_engine import OIContextEngine
from .volatility_context_engine import VolatilityContextEngine
from .macro_context_engine import MacroContextEngine
from .volume_profile_engine import VolumeProfileEngine
from .context_aggregator import ContextAggregator
from .context_repository import ContextRepository

__all__ = [
    # Types
    "FundingState",
    "OIState", 
    "VolatilityRegime",
    "MacroRegime",
    "RiskEnvironment",
    "VolumeProfileBias",
    "FundingContext",
    "OIContext",
    "VolatilityContext",
    "MacroContext",
    "VolumeProfileContext",
    "MarketContextSnapshot",
    "ContextHistoryQuery",
    # Engines
    "FundingContextEngine",
    "OIContextEngine",
    "VolatilityContextEngine",
    "MacroContextEngine",
    "VolumeProfileEngine",
    "ContextAggregator",
    "ContextRepository"
]
