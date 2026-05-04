"""
TT4 - History & Forensics
=========================
Trade lifecycle tracking, classification, and analytics for learning loop.

Components:
- TradeRecord: Full trade lifecycle data
- TradeBuilderEngine: Creates TradeRecord from closed positions
- TradeClassifier: WIN/LOSS/BE classification, diagnostics
- TradeAnalyticsEngine: Performance metrics (win rate, PF, expectancy)
"""

from .forensics_routes import router

__all__ = ["router"]
