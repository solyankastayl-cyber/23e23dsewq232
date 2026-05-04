"""
TT3 - Portfolio & Risk Console
==============================
Complete portfolio visibility and risk management layer for the trading terminal.

Components:
- PortfolioEngine: equity, capital allocation, PnL
- ExposureEngine: symbol/direction exposure breakdown
- RiskConsoleEngine: heat, drawdown, guardrails, kill switch
"""

from .portfolio_risk_routes import router

__all__ = ["router"]
