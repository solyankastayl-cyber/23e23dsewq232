"""
OPS4 Capital Flow Types
=======================

Data structures for capital flow management and analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class FlowEventType(str, Enum):
    """Types of capital flow events"""
    CAPITAL_ALLOCATED = "CAPITAL_ALLOCATED"
    CAPITAL_RELEASED = "CAPITAL_RELEASED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_SCALED = "POSITION_SCALED"
    POSITION_REDUCED = "POSITION_REDUCED"
    POSITION_CLOSED = "POSITION_CLOSED"
    PNL_REALIZED = "PNL_REALIZED"
    MARGIN_CALL = "MARGIN_CALL"
    REBALANCE = "REBALANCE"


@dataclass
class CapitalState:
    """
    Current capital state of the portfolio.
    Main operational view for capital management.
    """
    
    # Balance
    total_equity: float = 0.0
    used_margin: float = 0.0
    free_margin: float = 0.0
    
    # PnL
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    
    # Exposure
    exposure_usd: float = 0.0
    exposure_pct: float = 0.0
    
    # Counts
    open_positions: int = 0
    active_strategies: int = 0
    
    # Timestamp
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalEquity": round(self.total_equity, 2),
            "usedMargin": round(self.used_margin, 2),
            "freeMargin": round(self.free_margin, 2),
            "unrealizedPnl": round(self.unrealized_pnl, 2),
            "realizedPnl": round(self.realized_pnl, 2),
            "totalPnl": round(self.total_pnl, 2),
            "exposureUsd": round(self.exposure_usd, 2),
            "exposurePct": round(self.exposure_pct, 4),
            "openPositions": self.open_positions,
            "activeStrategies": self.active_strategies,
            "computedAt": self.computed_at
        }


@dataclass
class StrategyAllocation:
    """
    Capital allocation for a specific strategy.
    """
    strategy_id: str = ""
    strategy_name: str = ""
    
    # Capital
    capital_allocated: float = 0.0
    capital_used: float = 0.0
    capital_available: float = 0.0
    utilization_pct: float = 0.0
    
    # PnL
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Positions
    open_positions: int = 0
    total_trades: int = 0
    win_rate: float = 0.0
    
    # Allocation percentage
    allocation_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "strategyName": self.strategy_name,
            "capital": {
                "allocated": round(self.capital_allocated, 2),
                "used": round(self.capital_used, 2),
                "available": round(self.capital_available, 2),
                "utilizationPct": round(self.utilization_pct, 4)
            },
            "pnl": {
                "unrealized": round(self.unrealized_pnl, 2),
                "realized": round(self.realized_pnl, 2),
                "total": round(self.total_pnl, 2),
                "pnlPct": round(self.pnl_pct, 4)
            },
            "positions": {
                "open": self.open_positions,
                "totalTrades": self.total_trades,
                "winRate": round(self.win_rate, 4)
            },
            "allocationPct": round(self.allocation_pct, 4)
        }


@dataclass
class ExposureView:
    """
    Exposure view for a single asset/symbol.
    """
    symbol: str = ""
    exposure_usd: float = 0.0
    exposure_pct: float = 0.0
    position_count: int = 0
    side: str = ""  # LONG / SHORT / MIXED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exposureUsd": round(self.exposure_usd, 2),
            "exposurePct": round(self.exposure_pct, 4),
            "positionCount": self.position_count,
            "side": self.side
        }


@dataclass
class ExposureBreakdown:
    """
    Complete exposure breakdown.
    """
    by_symbol: List[ExposureView] = field(default_factory=list)
    by_strategy: Dict[str, float] = field(default_factory=dict)
    by_exchange: Dict[str, float] = field(default_factory=dict)
    by_side: Dict[str, float] = field(default_factory=dict)  # LONG vs SHORT
    
    total_exposure_usd: float = 0.0
    long_exposure_usd: float = 0.0
    short_exposure_usd: float = 0.0
    net_exposure_usd: float = 0.0
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bySymbol": [e.to_dict() for e in self.by_symbol],
            "byStrategy": self.by_strategy,
            "byExchange": self.by_exchange,
            "bySide": self.by_side,
            "summary": {
                "totalExposureUsd": round(self.total_exposure_usd, 2),
                "longExposureUsd": round(self.long_exposure_usd, 2),
                "shortExposureUsd": round(self.short_exposure_usd, 2),
                "netExposureUsd": round(self.net_exposure_usd, 2)
            },
            "computedAt": self.computed_at
        }


@dataclass
class CapitalFlowEvent:
    """
    Single event in capital flow.
    """
    event_id: str = field(default_factory=lambda: f"flow_{uuid.uuid4().hex[:12]}")
    event_type: FlowEventType = FlowEventType.CAPITAL_ALLOCATED
    
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    
    # Amount
    amount: float = 0.0
    currency: str = "USD"
    
    # Context
    strategy_id: Optional[str] = None
    position_id: Optional[str] = None
    symbol: Optional[str] = None
    
    # Balance after event
    balance_after: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type.value,
            "timestamp": self.timestamp,
            "amount": round(self.amount, 2),
            "currency": self.currency,
            "context": {
                "strategyId": self.strategy_id,
                "positionId": self.position_id,
                "symbol": self.symbol
            },
            "balanceAfter": round(self.balance_after, 2),
            "metadata": self.metadata
        }


@dataclass
class CapitalTimeline:
    """
    Capital flow timeline.
    """
    events: List[CapitalFlowEvent] = field(default_factory=list)
    
    start_balance: float = 0.0
    end_balance: float = 0.0
    net_flow: float = 0.0
    
    period_start: int = 0
    period_end: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "summary": {
                "startBalance": round(self.start_balance, 2),
                "endBalance": round(self.end_balance, 2),
                "netFlow": round(self.net_flow, 2)
            },
            "period": {
                "start": self.period_start,
                "end": self.period_end
            }
        }


@dataclass
class RiskConcentration:
    """
    Risk concentration analysis.
    Shows where capital risk is concentrated.
    """
    
    # Largest positions
    largest_position_symbol: Optional[str] = None
    largest_position_exposure: float = 0.0
    largest_position_pct: float = 0.0
    
    # Largest strategy
    largest_strategy_id: Optional[str] = None
    largest_strategy_exposure: float = 0.0
    largest_strategy_pct: float = 0.0
    
    # Largest exchange
    largest_exchange: Optional[str] = None
    largest_exchange_exposure: float = 0.0
    largest_exchange_pct: float = 0.0
    
    # Concentration metrics
    herfindahl_index: float = 0.0  # 0-1, higher = more concentrated
    top_3_concentration: float = 0.0
    
    # Risk flags
    risk_flags: List[str] = field(default_factory=list)
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "largestPosition": {
                "symbol": self.largest_position_symbol,
                "exposureUsd": round(self.largest_position_exposure, 2),
                "exposurePct": round(self.largest_position_pct, 4)
            },
            "largestStrategy": {
                "strategyId": self.largest_strategy_id,
                "exposureUsd": round(self.largest_strategy_exposure, 2),
                "exposurePct": round(self.largest_strategy_pct, 4)
            },
            "largestExchange": {
                "exchange": self.largest_exchange,
                "exposureUsd": round(self.largest_exchange_exposure, 2),
                "exposurePct": round(self.largest_exchange_pct, 4)
            },
            "concentrationMetrics": {
                "herfindahlIndex": round(self.herfindahl_index, 4),
                "top3Concentration": round(self.top_3_concentration, 4)
            },
            "riskFlags": self.risk_flags,
            "computedAt": self.computed_at
        }


@dataclass
class CapitalEfficiency:
    """
    Capital efficiency metrics.
    """
    
    # Utilization
    capital_used_pct: float = 0.0
    capital_idle_pct: float = 0.0
    
    # Returns
    return_on_capital: float = 0.0
    pnl_per_trade: float = 0.0
    pnl_per_dollar_risked: float = 0.0
    
    # Turnover
    capital_turnover: float = 0.0  # Times capital is recycled
    avg_holding_period_hours: float = 0.0
    
    # Efficiency score (composite)
    efficiency_score: float = 0.0
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "utilization": {
                "capitalUsedPct": round(self.capital_used_pct, 4),
                "capitalIdlePct": round(self.capital_idle_pct, 4)
            },
            "returns": {
                "returnOnCapital": round(self.return_on_capital, 4),
                "pnlPerTrade": round(self.pnl_per_trade, 2),
                "pnlPerDollarRisked": round(self.pnl_per_dollar_risked, 4)
            },
            "turnover": {
                "capitalTurnover": round(self.capital_turnover, 2),
                "avgHoldingPeriodHours": round(self.avg_holding_period_hours, 1)
            },
            "efficiencyScore": round(self.efficiency_score, 4),
            "computedAt": self.computed_at
        }


@dataclass
class PortfolioMetrics:
    """
    Portfolio-level metrics.
    """
    
    # Returns
    total_return: float = 0.0
    daily_return: float = 0.0
    weekly_return: float = 0.0
    monthly_return: float = 0.0
    
    # Risk
    volatility: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Win/Loss
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    computed_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "returns": {
                "total": round(self.total_return, 4),
                "daily": round(self.daily_return, 4),
                "weekly": round(self.weekly_return, 4),
                "monthly": round(self.monthly_return, 4)
            },
            "risk": {
                "volatility": round(self.volatility, 4),
                "maxDrawdown": round(self.max_drawdown, 4),
                "currentDrawdown": round(self.current_drawdown, 4)
            },
            "riskAdjusted": {
                "sharpeRatio": round(self.sharpe_ratio, 4),
                "sortinoRatio": round(self.sortino_ratio, 4),
                "calmarRatio": round(self.calmar_ratio, 4)
            },
            "winLoss": {
                "winRate": round(self.win_rate, 4),
                "profitFactor": round(self.profit_factor, 4),
                "avgWin": round(self.avg_win, 2),
                "avgLoss": round(self.avg_loss, 2)
            },
            "computedAt": self.computed_at
        }
