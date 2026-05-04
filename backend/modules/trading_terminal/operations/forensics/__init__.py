"""OPS3 Trade Forensics Module"""

from .forensics_types import (
    TradeForensicsReport,
    DecisionTrace,
    MarketContextSnapshot,
    StrategyDiagnosticsSnapshot,
    RootCause,
    BlockAnalysis,
    ForensicsTimeline,
    StrategyBehaviorAnalysis
)
from .forensics_service import forensics_service

__all__ = [
    'TradeForensicsReport',
    'DecisionTrace',
    'MarketContextSnapshot',
    'StrategyDiagnosticsSnapshot',
    'RootCause',
    'BlockAnalysis',
    'ForensicsTimeline',
    'StrategyBehaviorAnalysis',
    'forensics_service'
]
