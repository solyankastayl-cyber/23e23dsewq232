"""
PHASE 18.3 — Meta Portfolio Module
==================================
Meta Portfolio Aggregator.

Combines:
- Portfolio Intelligence
- Portfolio Constraints

Into a single unified portfolio management layer.

Pipeline position:
Signal → Portfolio Intelligence → Portfolio Constraints → Meta Portfolio → Trading Decision
"""

from modules.portfolio.meta_portfolio.meta_portfolio_engine import (
    get_meta_portfolio_engine,
    MetaPortfolioEngine,
)
from modules.portfolio.meta_portfolio.meta_portfolio_types import (
    MetaPortfolioState,
    PortfolioState,
)

__all__ = [
    "get_meta_portfolio_engine",
    "MetaPortfolioEngine",
    "MetaPortfolioState",
    "PortfolioState",
]
