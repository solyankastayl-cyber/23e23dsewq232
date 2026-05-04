"""
TT4 - Trade Record Models
=========================
Full trade lifecycle record with decision, execution, micro, position, PnL, and diagnostics.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TradeRecord:
    """Complete trade lifecycle record"""
    trade_id: str

    # Symbol / Context
    symbol: str
    timeframe: str
    side: str  # LONG / SHORT

    # Decision context
    prediction_action: Optional[str]  # GO_FULL, GO_REDUCED, WAIT, SKIP
    prediction_direction: Optional[str]  # LONG, SHORT, NEUTRAL
    prediction_confidence: Optional[float]

    entry_mode: Optional[str]  # AGGRESSIVE, STANDARD, CONSERVATIVE
    execution_mode: Optional[str]  # PASSIVE_LIMIT, AGGRESSIVE_MARKET, etc.
    entry_quality: Optional[float]  # 0-1 score

    # Micro context at entry
    micro_score: Optional[float]
    micro_decision: Optional[str]  # favorable, hostile, neutral
    imbalance: Optional[float]

    # Execution / Position IDs
    intent_id: Optional[str]
    order_id: Optional[str]
    position_id: Optional[str]

    # Price levels
    planned_entry: Optional[float]
    actual_entry: Optional[float]
    exit_price: Optional[float]

    size: float
    stop: Optional[float]
    target: Optional[float]
    rr: Optional[float]

    # PnL / Result
    pnl: float
    pnl_pct: float
    result: str  # WIN / LOSS / BE
    exit_reason: Optional[str]  # TARGET, STOP, MANUAL, INVALIDATION, TIMEOUT

    # Diagnostics / Mistakes
    wrong_early: bool  # Entered too early
    late_entry: bool   # Entered too late
    mtf_conflict: bool  # Multi-timeframe conflict ignored
    
    # Additional diagnostics
    slippage: Optional[float]  # planned_entry - actual_entry
    missed_target: bool  # Price reached target but didn't close
    
    # Portfolio / Risk snapshot at entry
    portfolio_heat: Optional[float]
    risk_status: Optional[str]  # NORMAL, WARNING, CRITICAL

    # Timing
    entry_time: Optional[str]
    exit_time: Optional[str]
    duration_sec: int

    created_at: str

    def to_dict(self):
        return asdict(self)


@dataclass
class TradeAnalytics:
    """Aggregated trade performance metrics"""
    trades: int
    wins: int
    losses: int
    breakevens: int
    
    win_rate: float
    loss_rate: float
    be_rate: float
    
    gross_profit: float
    gross_loss: float
    net_pnl: float
    
    profit_factor: Optional[float]
    expectancy: float
    avg_rr: float
    avg_duration_sec: int
    
    # Diagnostic rates
    wrong_early_rate: float
    late_entry_rate: float
    mtf_conflict_rate: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TradeDistribution:
    """Trade distribution by result and exit reason"""
    by_result: dict  # {"WIN": 10, "LOSS": 5, "BE": 2}
    by_exit_reason: dict  # {"TARGET": 8, "STOP": 5, ...}
    by_symbol: dict  # {"BTCUSDT": 10, "ETHUSDT": 7}
    by_side: dict  # {"LONG": 12, "SHORT": 5}
    
    def to_dict(self):
        return asdict(self)
