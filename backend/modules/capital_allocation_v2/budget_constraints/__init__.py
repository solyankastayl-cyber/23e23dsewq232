"""
PHASE 21.2 — Capital Budget Constraints Module
==============================================
Budget constraints for Capital Allocation Engine v2.

Components:
- capital_budget_types: Type definitions
- sleeve_limit_engine: Sleeve-level limits
- reserve_capital_engine: Reserve capital management
- dry_powder_engine: Dry powder allocation
- emergency_cut_engine: Emergency capital cuts
- regime_throttle_engine: Regime-based throttling
- capital_budget_engine: Main orchestrator
- capital_budget_routes: API endpoints
"""

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    CapitalBudgetState,
    BudgetState,
    SleeveLimitState,
    DEFAULT_SLEEVE_LIMITS,
    RESERVE_CAPITAL_BY_REGIME,
    REGIME_THROTTLE,
    EMERGENCY_CUT_LEVELS,
    BUDGET_STATE_THRESHOLDS,
)

from modules.capital_allocation_v2.budget_constraints.capital_budget_engine import (
    CapitalBudgetEngine,
    get_capital_budget_engine,
)

from modules.capital_allocation_v2.budget_constraints.sleeve_limit_engine import (
    SleeveLimitEngine,
    get_sleeve_limit_engine,
)

from modules.capital_allocation_v2.budget_constraints.reserve_capital_engine import (
    ReserveCapitalEngine,
    get_reserve_capital_engine,
)

from modules.capital_allocation_v2.budget_constraints.dry_powder_engine import (
    DryPowderEngine,
    get_dry_powder_engine,
)

from modules.capital_allocation_v2.budget_constraints.emergency_cut_engine import (
    EmergencyCutEngine,
    get_emergency_cut_engine,
)

from modules.capital_allocation_v2.budget_constraints.regime_throttle_engine import (
    RegimeThrottleEngine,
    get_regime_throttle_engine,
)

__all__ = [
    # Types
    "CapitalBudgetState",
    "BudgetState",
    "SleeveLimitState",
    "DEFAULT_SLEEVE_LIMITS",
    "RESERVE_CAPITAL_BY_REGIME",
    "REGIME_THROTTLE",
    "EMERGENCY_CUT_LEVELS",
    "BUDGET_STATE_THRESHOLDS",
    # Main Engine
    "CapitalBudgetEngine",
    "get_capital_budget_engine",
    # Sub-engines
    "SleeveLimitEngine",
    "get_sleeve_limit_engine",
    "ReserveCapitalEngine",
    "get_reserve_capital_engine",
    "DryPowderEngine",
    "get_dry_powder_engine",
    "EmergencyCutEngine",
    "get_emergency_cut_engine",
    "RegimeThrottleEngine",
    "get_regime_throttle_engine",
]
