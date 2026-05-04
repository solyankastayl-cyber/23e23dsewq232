"""
Portfolio Simulation Module (S4.1/S4.2/S4.3)
=============================================

Portfolio simulation for multi-strategy capital management.

S4.1 - Core:
- PortfolioSimulation: Main simulation entity
- PortfolioStrategySlot: Individual strategy slot
- PortfolioState: Real-time portfolio state
- PortfolioSimulationService: Core business logic

S4.2 - Execution:
- PortfolioBroker: Multi-strategy broker
- SlotBroker: Per-slot broker adapter
- PortfolioOrder, PortfolioPosition, PortfolioTrade

S4.3 - Metrics:
- PortfolioMetrics: Aggregated portfolio metrics
- StrategyMetrics: Per-strategy metrics
- CorrelationMatrix: Strategy correlation
- EquityCurve: Portfolio equity over time
"""

# S4.1 - Core Types
from .portfolio_types import (
    PortfolioSimulation,
    PortfolioStrategySlot,
    PortfolioState,
    PortfolioSimulationStatus,
    SlotStatus
)

# S4.2 - Broker Types
from .portfolio_broker_types import (
    PortfolioOrder,
    PortfolioPosition,
    PortfolioTrade,
    ExecutionEvent,
    SlotExecutionSummary,
    OrderSide,
    OrderType,
    OrderStatus,
    TradeType,
    PositionSide
)

# S4.3 - Metrics Types
from .portfolio_metrics_types import (
    PortfolioMetrics,
    StrategyMetrics,
    CorrelationMatrix,
    EquityCurvePoint,
    RiskContribution
)

# Services
from .portfolio_simulation_service import portfolio_simulation_service
from .portfolio_state_service import portfolio_state_service
from .portfolio_broker_service import portfolio_broker_service
from .portfolio_metrics_service import portfolio_metrics_service
from .portfolio_repository import portfolio_repository

__all__ = [
    # S4.1 Types
    "PortfolioSimulation",
    "PortfolioStrategySlot",
    "PortfolioState",
    "PortfolioSimulationStatus",
    "SlotStatus",
    
    # S4.2 Types
    "PortfolioOrder",
    "PortfolioPosition",
    "PortfolioTrade",
    "ExecutionEvent",
    "SlotExecutionSummary",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "TradeType",
    "PositionSide",
    
    # S4.3 Types
    "PortfolioMetrics",
    "StrategyMetrics",
    "CorrelationMatrix",
    "EquityCurvePoint",
    "RiskContribution",
    
    # Services
    "portfolio_simulation_service",
    "portfolio_state_service",
    "portfolio_broker_service",
    "portfolio_metrics_service",
    "portfolio_repository"
]
