"""
Portfolio & Risk Models for Trading Terminal
=============================================

Core data structures for portfolio and risk management:
- PortfolioSummary: equity, capital, exposure
- ExposureBreakdown: by symbol and direction
- RiskSummary: heat, drawdown, guardrails
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from enum import Enum


class RiskStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    KILL_SWITCH = "KILL_SWITCH"


@dataclass
class ExposureBySymbol:
    """Exposure for a single symbol"""
    symbol: str
    exposure: float
    notional: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExposureBreakdown:
    """Complete exposure breakdown"""
    by_symbol: List[ExposureBySymbol]
    by_direction: Dict[str, float]
    total_long: float = 0.0
    total_short: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "by_symbol": [x.to_dict() for x in self.by_symbol],
            "by_direction": self.by_direction,
            "total_long": self.total_long,
            "total_short": self.total_short,
        }


@dataclass
class PortfolioSummary:
    """Portfolio state summary"""
    equity: float
    free_capital: float
    used_capital: float

    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float

    gross_exposure: float
    net_exposure: float

    open_positions: int
    open_orders: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskSummary:
    """Risk state summary"""
    heat: float
    daily_drawdown: float
    max_drawdown: float
    status: str

    kill_switch: bool
    can_open_new: bool
    
    active_guardrails: List[str] = field(default_factory=list)
    block_reasons: List[str] = field(default_factory=list)
    risk_alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
