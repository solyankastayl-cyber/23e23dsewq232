"""
Liquidity Impact Engine Module

PHASE 37 Sublayer — Liquidity Impact Engine

Evaluates market impact of intended trades:
- What happens to the market if we execute this order?
- Slippage estimation
- Market impact calculation
- Execution recommendations

Pipeline position:
decision → execution brain → liquidity impact → final order plan → execution
"""

from .impact_types import (
    LiquidityImpactEstimate,
    LiquidityBucket,
    ImpactState,
    ExecutionRecommendation,
    ImpactSummary,
    SLIPPAGE_THRESHOLDS,
    IMPACT_MODIFIERS,
)
from .impact_engine import (
    LiquidityImpactEngine,
    get_liquidity_impact_engine,
)
from .impact_registry import (
    ImpactRegistry,
    get_impact_registry,
)
from .impact_routes import router as impact_router

__all__ = [
    # Types
    "LiquidityImpactEstimate",
    "LiquidityBucket",
    "ImpactState",
    "ExecutionRecommendation",
    "ImpactSummary",
    "SLIPPAGE_THRESHOLDS",
    "IMPACT_MODIFIERS",
    # Engine
    "LiquidityImpactEngine",
    "get_liquidity_impact_engine",
    # Registry
    "ImpactRegistry",
    "get_impact_registry",
    # Routes
    "impact_router",
]
