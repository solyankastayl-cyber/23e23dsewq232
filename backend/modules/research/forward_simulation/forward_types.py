"""
Forward Simulation Types
========================

Core types for Forward Simulation (PHASE 2.3)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class SimulationStatus(str, Enum):
    """Status of simulation run"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TradeDirection(str, Enum):
    """Trade direction"""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, Enum):
    """Trade status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED = "STOPPED"
    TARGET_HIT = "TARGET_HIT"


class MarketScenario(str, Enum):
    """Pre-defined market scenarios"""
    BTC_2017_BULL = "BTC_2017_BULL"
    BTC_2018_BEAR = "BTC_2018_BEAR"
    BTC_2020_CRASH = "BTC_2020_CRASH"
    BTC_2021_BULL = "BTC_2021_BULL"
    BTC_2022_BEAR = "BTC_2022_BEAR"
    ETH_2021_DEFI = "ETH_2021_DEFI"
    CUSTOM = "CUSTOM"


# ===========================================
# Configuration
# ===========================================

@dataclass
class SimulationConfig:
    """Configuration for forward simulation"""
    # Market settings
    symbol: str = "BTC"
    timeframe: str = "4h"
    scenario: MarketScenario = MarketScenario.CUSTOM
    
    # Date range (for custom scenario)
    start_date: str = "2023-01-01"
    end_date: str = "2023-12-31"
    
    # Capital settings
    initial_capital: float = 10000.0
    risk_per_trade_pct: float = 1.0
    max_position_size_pct: float = 10.0
    
    # Execution settings
    slippage_pct: float = 0.05  # 0.05%
    commission_pct: float = 0.1  # 0.1%
    
    # Strategy settings
    strategies: List[str] = field(default_factory=lambda: [
        "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"
    ])
    use_strategy_selection: bool = True
    
    # Simulation settings
    candle_count: int = 500  # Number of candles to simulate
    replay_speed: int = 0   # 0 = instant, >0 = ms delay per candle
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "scenario": self.scenario.value,
            "dateRange": {
                "start": self.start_date,
                "end": self.end_date
            },
            "capital": {
                "initial": self.initial_capital,
                "riskPerTrade": self.risk_per_trade_pct,
                "maxPositionSize": self.max_position_size_pct
            },
            "execution": {
                "slippage": self.slippage_pct,
                "commission": self.commission_pct
            },
            "strategies": self.strategies,
            "useStrategySelection": self.use_strategy_selection,
            "candleCount": self.candle_count
        }


# ===========================================
# Market Data Types
# ===========================================

@dataclass
class Candle:
    """OHLCV candle data"""
    timestamp: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": round(self.open, 8),
            "high": round(self.high, 8),
            "low": round(self.low, 8),
            "close": round(self.close, 8),
            "volume": round(self.volume, 2)
        }


# ===========================================
# Trade Types
# ===========================================

@dataclass
class SimulatedTrade:
    """A simulated trade"""
    trade_id: str = ""
    symbol: str = ""
    timeframe: str = ""
    
    # Strategy info
    strategy: str = ""
    regime: str = ""
    execution_style: str = ""
    
    # Trade details
    direction: TradeDirection = TradeDirection.LONG
    status: TradeStatus = TradeStatus.OPEN
    
    # Prices
    entry_price: float = 0.0
    exit_price: float = 0.0
    stop_price: float = 0.0
    target_price: float = 0.0
    
    # Size and risk
    position_size: float = 0.0
    risk_amount: float = 0.0
    
    # Results
    pnl: float = 0.0
    pnl_pct: float = 0.0
    r_multiple: float = 0.0
    
    # Costs
    slippage_cost: float = 0.0
    commission_cost: float = 0.0
    total_cost: float = 0.0
    
    # Timing
    entry_bar: int = 0
    exit_bar: int = 0
    duration_bars: int = 0
    
    opened_at: int = 0
    closed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": self.trade_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy,
            "regime": self.regime,
            "executionStyle": self.execution_style,
            "direction": self.direction.value,
            "status": self.status.value,
            "prices": {
                "entry": round(self.entry_price, 8),
                "exit": round(self.exit_price, 8),
                "stop": round(self.stop_price, 8),
                "target": round(self.target_price, 8)
            },
            "size": {
                "position": round(self.position_size, 8),
                "risk": round(self.risk_amount, 2)
            },
            "results": {
                "pnl": round(self.pnl, 2),
                "pnlPct": round(self.pnl_pct, 4),
                "rMultiple": round(self.r_multiple, 2)
            },
            "costs": {
                "slippage": round(self.slippage_cost, 4),
                "commission": round(self.commission_cost, 4),
                "total": round(self.total_cost, 4)
            },
            "timing": {
                "entryBar": self.entry_bar,
                "exitBar": self.exit_bar,
                "durationBars": self.duration_bars,
                "openedAt": self.opened_at,
                "closedAt": self.closed_at
            }
        }


# ===========================================
# Equity Curve
# ===========================================

@dataclass
class EquityPoint:
    """Single point on equity curve"""
    bar: int = 0
    timestamp: int = 0
    equity: float = 0.0
    drawdown: float = 0.0
    drawdown_pct: float = 0.0
    open_positions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar": self.bar,
            "timestamp": self.timestamp,
            "equity": round(self.equity, 2),
            "drawdown": round(self.drawdown, 2),
            "drawdownPct": round(self.drawdown_pct, 4),
            "openPositions": self.open_positions
        }


@dataclass
class EquityCurve:
    """Complete equity curve"""
    points: List[EquityPoint] = field(default_factory=list)
    
    # Summary stats
    starting_equity: float = 0.0
    ending_equity: float = 0.0
    peak_equity: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points[-100:]],  # Last 100 points
            "summary": {
                "startingEquity": round(self.starting_equity, 2),
                "endingEquity": round(self.ending_equity, 2),
                "peakEquity": round(self.peak_equity, 2),
                "maxDrawdown": round(self.max_drawdown, 2),
                "maxDrawdownPct": round(self.max_drawdown_pct, 4),
                "totalReturn": round(self.ending_equity - self.starting_equity, 2),
                "totalReturnPct": round((self.ending_equity / self.starting_equity - 1) * 100, 2) if self.starting_equity > 0 else 0
            }
        }


# ===========================================
# Forward Metrics
# ===========================================

@dataclass
class ForwardMetrics:
    """Performance metrics from forward simulation"""
    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Rates
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Returns
    total_return: float = 0.0
    total_return_pct: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Trade metrics
    average_trade: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    avg_r_multiple: float = 0.0
    
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Duration
    avg_duration_bars: float = 0.0
    avg_winner_duration: float = 0.0
    avg_loser_duration: float = 0.0
    
    # Costs
    total_slippage: float = 0.0
    total_commission: float = 0.0
    total_costs: float = 0.0
    
    # Strategy breakdown
    strategy_contribution: Dict[str, float] = field(default_factory=dict)
    regime_performance: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trades": {
                "total": self.total_trades,
                "winners": self.winning_trades,
                "losers": self.losing_trades,
                "winRate": round(self.win_rate, 4)
            },
            "performance": {
                "profitFactor": round(self.profit_factor, 2),
                "expectancy": round(self.expectancy, 4),
                "totalReturn": round(self.total_return, 2),
                "totalReturnPct": round(self.total_return_pct, 2)
            },
            "risk": {
                "maxDrawdown": round(self.max_drawdown, 2),
                "maxDrawdownPct": round(self.max_drawdown_pct, 4),
                "sharpeRatio": round(self.sharpe_ratio, 2),
                "sortinoRatio": round(self.sortino_ratio, 2)
            },
            "tradeMetrics": {
                "averageTrade": round(self.average_trade, 2),
                "averageWin": round(self.average_win, 2),
                "averageLoss": round(self.average_loss, 2),
                "avgRMultiple": round(self.avg_r_multiple, 2),
                "largestWin": round(self.largest_win, 2),
                "largestLoss": round(self.largest_loss, 2)
            },
            "duration": {
                "avgBars": round(self.avg_duration_bars, 1),
                "avgWinnerBars": round(self.avg_winner_duration, 1),
                "avgLoserBars": round(self.avg_loser_duration, 1)
            },
            "costs": {
                "totalSlippage": round(self.total_slippage, 2),
                "totalCommission": round(self.total_commission, 2),
                "totalCosts": round(self.total_costs, 2)
            },
            "breakdown": {
                "byStrategy": self.strategy_contribution,
                "byRegime": self.regime_performance
            }
        }


# ===========================================
# Simulation Run
# ===========================================

@dataclass
class SimulationRun:
    """Complete forward simulation run"""
    run_id: str = ""
    status: SimulationStatus = SimulationStatus.PENDING
    config: SimulationConfig = field(default_factory=SimulationConfig)
    
    # Progress
    current_bar: int = 0
    total_bars: int = 0
    progress_pct: float = 0.0
    
    # Results
    trades: List[SimulatedTrade] = field(default_factory=list)
    equity_curve: EquityCurve = field(default_factory=EquityCurve)
    metrics: ForwardMetrics = field(default_factory=ForwardMetrics)
    
    # Timing
    started_at: int = 0
    completed_at: int = 0
    duration_ms: int = 0
    
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "runId": self.run_id,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "progress": {
                "currentBar": self.current_bar,
                "totalBars": self.total_bars,
                "progressPct": round(self.progress_pct, 1)
            },
            "tradesCount": len(self.trades),
            "recentTrades": [t.to_dict() for t in self.trades[-10:]],
            "equityCurve": self.equity_curve.to_dict(),
            "metrics": self.metrics.to_dict(),
            "timing": {
                "startedAt": self.started_at,
                "completedAt": self.completed_at,
                "durationMs": self.duration_ms
            },
            "error": self.error
        }
