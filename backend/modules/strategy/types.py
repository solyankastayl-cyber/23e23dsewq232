"""Strategy Types — Signal & Strategy Stats Models

Week 4: Strategy Allocator V2
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Signal:
    """Trading signal from strategy."""
    symbol: str
    side: str  # "LONG" / "SHORT"
    confidence: float  # 0..1
    stop_distance: float  # % (0.01 = 1%)
    source: str  # strategy name
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None


@dataclass
class StrategyStats:
    """Strategy performance statistics."""
    name: str
    win_rate: float  # 0..1
    avg_return: float  # %
    sharpe: float
    drawdown: float  # %
    recent_pnl: float  # last N trades
    total_trades: int = 0
    active_positions: int = 0
