"""
Portfolio Accounts Module - PHASE 5.4
=====================================

Unified portfolio state aggregation across multiple exchanges.
"""

from .account_types import (
    PortfolioAccount,
    PortfolioBalance,
    PortfolioPosition,
    PortfolioState,
    MarginInfo,
    ExposureInfo
)
from .account_aggregator import get_account_aggregator
from .balance_aggregator import get_balance_aggregator
from .position_aggregator import get_position_aggregator
from .margin_engine import get_margin_engine
from .portfolio_state_builder import get_portfolio_state_builder

__all__ = [
    "PortfolioAccount",
    "PortfolioBalance",
    "PortfolioPosition",
    "PortfolioState",
    "MarginInfo",
    "ExposureInfo",
    "get_account_aggregator",
    "get_balance_aggregator",
    "get_position_aggregator",
    "get_margin_engine",
    "get_portfolio_state_builder"
]
