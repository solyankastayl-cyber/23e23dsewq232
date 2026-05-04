"""
Portfolio Manager Module

PHASE 38 — Portfolio Manager

Multi-asset portfolio management:
- Exposure control (max 70% long/short)
- Position limits (max 10% single)
- Correlation control
- Capital rotation
- Portfolio risk management

Pipeline integration:
execution brain → portfolio manager → final execution
"""

from .portfolio_types import (
    PortfolioState,
    PortfolioPosition,
    PortfolioTarget,
    PortfolioRisk,
    ExposureState,
    CorrelationMatrix,
    RebalanceResult,
    PositionRequest,
    CapitalRotationRequest,
    PortfolioHistoryEntry,
    EXPOSURE_LIMITS,
    RISK_THRESHOLDS,
    MAX_SINGLE_POSITION,
    REBALANCE_THRESHOLD,
)
from .portfolio_engine import (
    PortfolioManagerEngine,
    get_portfolio_manager_engine,
)
from .portfolio_registry import (
    PortfolioRegistry,
    get_portfolio_registry,
)
from .portfolio_routes import router as portfolio_router

__all__ = [
    # Types
    "PortfolioState",
    "PortfolioPosition",
    "PortfolioTarget",
    "PortfolioRisk",
    "ExposureState",
    "CorrelationMatrix",
    "RebalanceResult",
    "PositionRequest",
    "CapitalRotationRequest",
    "PortfolioHistoryEntry",
    "EXPOSURE_LIMITS",
    "RISK_THRESHOLDS",
    "MAX_SINGLE_POSITION",
    "REBALANCE_THRESHOLD",
    # Engine
    "PortfolioManagerEngine",
    "get_portfolio_manager_engine",
    # Registry
    "PortfolioRegistry",
    "get_portfolio_registry",
    # Routes
    "portfolio_router",
]
