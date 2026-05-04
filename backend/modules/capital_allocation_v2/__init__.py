"""
PHASE 21.1 — Capital Allocation v2 Module
=========================================
System-wide capital routing engine.

Components:
- capital_allocation_types: Type definitions
- strategy_capital_engine: Strategy-level allocation
- factor_capital_engine: Factor-level allocation
- asset_capital_engine: Asset-level allocation
- cluster_capital_engine: Cluster-level allocation
- capital_router_engine: Main orchestrator
- capital_allocation_routes: API endpoints
"""

from modules.capital_allocation_v2.capital_allocation_types import (
    CapitalAllocationState,
    DominantRoute,
    RoutingRegime,
    AllocationSlice,
    StrategyAllocationInput,
    FactorAllocationInput,
    ALLOCATION_CONFIDENCE_THRESHOLDS,
    ALLOCATION_MODIFIERS,
    ALLOCATION_CONFIDENCE_WEIGHTS,
)

from modules.capital_allocation_v2.capital_router_engine import (
    CapitalRouterEngine,
    get_capital_router_engine,
)

from modules.capital_allocation_v2.strategy_capital_engine import (
    StrategyCapitalEngine,
    get_strategy_capital_engine,
)

from modules.capital_allocation_v2.factor_capital_engine import (
    FactorCapitalEngine,
    get_factor_capital_engine,
)

from modules.capital_allocation_v2.asset_capital_engine import (
    AssetCapitalEngine,
    get_asset_capital_engine,
)

from modules.capital_allocation_v2.cluster_capital_engine import (
    ClusterCapitalEngine,
    get_cluster_capital_engine,
)

__all__ = [
    # Types
    "CapitalAllocationState",
    "DominantRoute",
    "RoutingRegime",
    "AllocationSlice",
    "StrategyAllocationInput",
    "FactorAllocationInput",
    "ALLOCATION_CONFIDENCE_THRESHOLDS",
    "ALLOCATION_MODIFIERS",
    "ALLOCATION_CONFIDENCE_WEIGHTS",
    # Router Engine
    "CapitalRouterEngine",
    "get_capital_router_engine",
    # Sub-engines
    "StrategyCapitalEngine",
    "get_strategy_capital_engine",
    "FactorCapitalEngine",
    "get_factor_capital_engine",
    "AssetCapitalEngine",
    "get_asset_capital_engine",
    "ClusterCapitalEngine",
    "get_cluster_capital_engine",
]
