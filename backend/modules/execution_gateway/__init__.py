"""
Execution Gateway Module

PHASE 39 — Execution Gateway Layer

Unified execution pipeline from Execution Brain to Exchange.

Flow:
1. ExecutionRequest (from Execution Brain)
2. Safety Gate (Risk Budget + Portfolio + Liquidity checks)
3. Exchange Routing (symbol → exchange)
4. Order Execution (Paper/Live/Approval)
5. Fill Processing (from Exchange)
6. Portfolio Update (to Portfolio Manager)

Modes:
- PAPER: Simulated fills for testing
- LIVE: Real exchange orders
- APPROVAL: Requires human approval (Decision Support)
"""

from .gateway_types import (
    ExecutionMode,
    ExecutionRequest,
    ExecutionOrder,
    ExecutionFill,
    ExecutionResult,
    SafetyGateResult,
    SafetyCheckResult,
    SafetyCheckType,
    PortfolioUpdateEvent,
    ApprovalRequest,
    ExchangeRouteConfig,
    GatewayConfig,
    OrderSide,
    OrderType,
    OrderStatus,
)

from .gateway_engine import (
    ExecutionGatewayEngine,
    get_execution_gateway,
)

from .gateway_repository import (
    GatewayRepository,
    get_gateway_repository,
)

from .gateway_routes import router as gateway_router

__all__ = [
    # Types
    "ExecutionMode",
    "ExecutionRequest",
    "ExecutionOrder",
    "ExecutionFill",
    "ExecutionResult",
    "SafetyGateResult",
    "SafetyCheckResult",
    "SafetyCheckType",
    "PortfolioUpdateEvent",
    "ApprovalRequest",
    "ExchangeRouteConfig",
    "GatewayConfig",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    # Engine
    "ExecutionGatewayEngine",
    "get_execution_gateway",
    # Repository
    "GatewayRepository",
    "get_gateway_repository",
    # Router
    "gateway_router",
]
