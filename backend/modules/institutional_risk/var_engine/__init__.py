"""
PHASE 22.1 — VaR Engine Module
==============================
Value at Risk Engine for Institutional Risk Fabric.

Components:
- var_types: Type definitions
- portfolio_var_engine: Portfolio VaR calculation
- expected_shortfall_engine: Expected Shortfall (CVaR)
- risk_state_engine: Risk state classification
- var_aggregator: Main aggregator
- var_routes: API endpoints
"""

from modules.institutional_risk.var_engine.var_types import (
    VaRState,
    VaRHistoryEntry,
    RiskState,
    RecommendedAction,
    RISK_STATE_THRESHOLDS,
    VOLATILITY_MULTIPLIERS,
    REGIME_MULTIPLIERS,
    RISK_STATE_MODIFIERS,
)

from modules.institutional_risk.var_engine.var_aggregator import (
    VaRAggregator,
    get_var_aggregator,
)

from modules.institutional_risk.var_engine.portfolio_var_engine import (
    PortfolioVaREngine,
    get_portfolio_var_engine,
)

from modules.institutional_risk.var_engine.expected_shortfall_engine import (
    ExpectedShortfallEngine,
    get_expected_shortfall_engine,
)

from modules.institutional_risk.var_engine.risk_state_engine import (
    RiskStateEngine,
    get_risk_state_engine,
)

__all__ = [
    # Types
    "VaRState",
    "VaRHistoryEntry",
    "RiskState",
    "RecommendedAction",
    "RISK_STATE_THRESHOLDS",
    "VOLATILITY_MULTIPLIERS",
    "REGIME_MULTIPLIERS",
    "RISK_STATE_MODIFIERS",
    # Aggregator
    "VaRAggregator",
    "get_var_aggregator",
    # Sub-engines
    "PortfolioVaREngine",
    "get_portfolio_var_engine",
    "ExpectedShortfallEngine",
    "get_expected_shortfall_engine",
    "RiskStateEngine",
    "get_risk_state_engine",
]
