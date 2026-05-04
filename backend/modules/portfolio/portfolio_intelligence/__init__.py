"""
PHASE 18.1 — Portfolio Intelligence Module
==========================================
Meta Portfolio Intelligence Layer.

Teaches the system to view the portfolio as a single risk object,
not individual trades.

Sub-modules:
- portfolio_exposure_engine: Net/Gross exposure calculations
- factor_exposure_engine: Factor concentration analysis
- cluster_exposure_engine: Asset cluster analysis
- portfolio_risk_engine: Risk state determination
- portfolio_intelligence_engine: Main aggregator
"""

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_engine import (
    get_portfolio_intelligence_engine,
    PortfolioIntelligenceEngine,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    PortfolioIntelligenceState,
    PortfolioRiskState,
    RecommendedAction,
    Position,
    PortfolioContext,
)

__all__ = [
    "get_portfolio_intelligence_engine",
    "PortfolioIntelligenceEngine",
    "PortfolioIntelligenceState",
    "PortfolioRiskState",
    "RecommendedAction",
    "Position",
    "PortfolioContext",
]
