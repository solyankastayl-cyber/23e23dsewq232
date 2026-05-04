"""
Validation Models for Live Validation Layer (V1)
"""
from dataclasses import dataclass, asdict, field
from typing import Optional, List
from datetime import datetime


@dataclass
class ShadowTrade:
    """Shadow trade - virtual trade for validation"""
    shadow_id: str
    symbol: str
    timeframe: str
    
    decision_action: str  # GO_FULL, GO_REDUCED, WAIT, etc.
    direction: str  # LONG, SHORT, NEUTRAL
    
    planned_entry: Optional[float]
    planned_stop: Optional[float]
    planned_target: Optional[float]
    planned_rr: Optional[float]
    
    entry_mode: str  # ENTER_ON_CLOSE, ENTER_ON_BREAK, etc.
    execution_mode: str  # PASSIVE_LIMIT, MARKET, etc.
    
    created_at: str
    expires_at: Optional[str]
    
    status: str  # PENDING, ENTERED, TARGET_HIT, STOP_HIT, EXPIRED, CANCELLED
    
    # Additional context
    confidence: float = 0.0
    entry_timing_score: float = 0.0
    microstructure_score: float = 0.0
    risk_score: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of shadow trade validation against market"""
    shadow_id: str
    symbol: str
    
    result: str  # WIN, LOSS, EXPIRED, MISSED, OPEN
    actual_entry: Optional[float]
    actual_exit: Optional[float]
    
    target_hit: bool
    stop_hit: bool
    expired: bool
    
    pnl: float
    pnl_pct: float
    
    entry_reached: bool
    drift_bps: float  # Difference between planned and actual entry in basis points
    
    wrong_early: bool  # If stop hit before target opportunity
    validation_reason: str
    
    # Timing metrics
    time_to_entry_ms: Optional[int] = None
    time_in_trade_ms: Optional[int] = None
    
    validated_at: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ValidationMetrics:
    """Aggregated validation metrics"""
    trades: int
    win_rate: float
    profit_factor: Optional[float]
    expectancy: float
    
    stop_rate: float
    target_rate: float
    expired_rate: float
    missed_rate: float
    
    wrong_early_rate: float
    avg_drift_bps: float
    
    # Extended metrics
    avg_rr_achieved: float = 0.0
    avg_time_to_entry_ms: float = 0.0
    avg_time_in_trade_ms: float = 0.0
    
    # Breakdown by direction
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    
    # Breakdown by entry mode
    entry_mode_breakdown: dict = field(default_factory=dict)
    
    # Period info
    period_start: str = ""
    period_end: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass
class MarketCandle:
    """Simple candle for market path evaluation"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    def to_dict(self):
        return asdict(self)
