"""
PHASE 21.3 — Capital Allocation Aggregator Module
=================================================
Unified Capital Allocation Layer.

Components:
- capital_allocation_layer_types: Type definitions
- capital_allocation_aggregator: Main aggregator
- capital_allocation_registry: State history tracking
- capital_allocation_layer_routes: API endpoints
"""

from modules.capital_allocation_v2.aggregator.capital_allocation_layer_types import (
    CapitalAllocationLayerState,
    AllocationState,
    LayerHistoryEntry,
    ALLOCATION_STATE_THRESHOLDS,
)

from modules.capital_allocation_v2.aggregator.capital_allocation_aggregator import (
    CapitalAllocationAggregator,
    get_capital_allocation_aggregator,
)

from modules.capital_allocation_v2.aggregator.capital_allocation_registry import (
    CapitalAllocationRegistry,
    get_capital_allocation_registry,
)

__all__ = [
    # Types
    "CapitalAllocationLayerState",
    "AllocationState",
    "LayerHistoryEntry",
    "ALLOCATION_STATE_THRESHOLDS",
    # Aggregator
    "CapitalAllocationAggregator",
    "get_capital_allocation_aggregator",
    # Registry
    "CapitalAllocationRegistry",
    "get_capital_allocation_registry",
]
