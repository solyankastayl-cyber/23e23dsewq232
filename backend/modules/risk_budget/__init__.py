"""
Risk Budget Engine Module

PHASE 38.5 — Risk Budget Engine

Professional fund approach to risk allocation:
- Distribute RISK, not capital
- Volatility targeting: position_size = risk_budget / asset_volatility
- Risk contribution: weight * volatility * correlation_adjustment

Integration points:
- Portfolio Manager
- Execution Brain
- Capital Allocation Engine
"""

from .risk_budget_types import (
    RiskBudget,
    PositionRisk,
    PortfolioRiskBudget,
    RiskBudgetAllocationRequest,
    VolatilityTargetRequest,
    VolatilityTargetResponse,
    RiskContributionResult,
    RiskRebalanceResult,
    RiskBudgetHistoryEntry,
    DEFAULT_RISK_BUDGETS,
    PORTFOLIO_RISK_LIMITS,
    VOLATILITY_PARAMS,
    RISK_CONTRIBUTION_LIMITS,
)

from .risk_budget_engine import (
    RiskBudgetEngine,
    get_risk_budget_engine,
)

from .risk_budget_registry import (
    RiskBudgetRegistry,
    get_risk_budget_registry,
)

from .risk_budget_routes import router as risk_budget_router

__all__ = [
    # Types
    "RiskBudget",
    "PositionRisk",
    "PortfolioRiskBudget",
    "RiskBudgetAllocationRequest",
    "VolatilityTargetRequest",
    "VolatilityTargetResponse",
    "RiskContributionResult",
    "RiskRebalanceResult",
    "RiskBudgetHistoryEntry",
    # Constants
    "DEFAULT_RISK_BUDGETS",
    "PORTFOLIO_RISK_LIMITS",
    "VOLATILITY_PARAMS",
    "RISK_CONTRIBUTION_LIMITS",
    # Engine
    "RiskBudgetEngine",
    "get_risk_budget_engine",
    # Registry
    "RiskBudgetRegistry",
    "get_risk_budget_registry",
    # Router
    "risk_budget_router",
]
