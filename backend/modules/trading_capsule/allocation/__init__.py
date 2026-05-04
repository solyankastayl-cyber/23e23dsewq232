"""
Capital Allocation Module (S3)
==============================

Capital allocation for trading strategies.

S3.1 - Strategy Selection:
- Filter by ranking/robustness
- Reject OVERFIT/UNSTABLE
- Apply quality thresholds

S3.2 - Weight Allocation:
- Calculate allocation scores
- Normalize weights
- Apply caps

S3.3 - Allocation Engine:
- Build allocation plans
- Manage plan lifecycle
- Handle rebalancing
- Store snapshots
"""

from .allocation_types import (
    EligibleStrategy,
    StrategyAllocation,
    CapitalAllocationPlan,
    AllocationSnapshot,
    AllocationPolicy,
    AllocationStatus,
    SelectionReason,
    RebalancePreview
)

from .strategy_selector import (
    StrategySelector,
    strategy_selector
)

from .weight_allocator import (
    WeightAllocator,
    weight_allocator
)

from .allocation_engine import (
    AllocationEngine,
    allocation_engine
)

from .allocation_routes import router as allocation_router


__all__ = [
    # Types
    "EligibleStrategy",
    "StrategyAllocation",
    "CapitalAllocationPlan",
    "AllocationSnapshot",
    "AllocationPolicy",
    "AllocationStatus",
    "SelectionReason",
    "RebalancePreview",
    
    # Strategy Selector (S3.1)
    "StrategySelector",
    "strategy_selector",
    
    # Weight Allocator (S3.2)
    "WeightAllocator",
    "weight_allocator",
    
    # Allocation Engine (S3.3)
    "AllocationEngine",
    "allocation_engine",
    
    # Routes
    "allocation_router"
]


print("[Allocation] Module loaded - S3.1/S3.2/S3.3 Ready")
