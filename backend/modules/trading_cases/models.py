"""
TradingCase Models

The core unit of trading decisions.
Links Decision → Orders → Fills → PnL → Portfolio.
"""

from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime


class TradingCase(BaseModel):
    """
    Main trading case model.
    
    Represents a single trading decision lifecycle.
    """
    
    # Identity
    case_id: str
    
    # Instrument
    symbol: str  # "BTCUSDT"
    exchange: str  # "paper", "binance_testnet", "bybit_demo"
    
    # Direction & Status
    side: Literal["LONG", "SHORT"]
    status: Literal["ACTIVE", "CLOSED", "CANCELLED"]
    
    # Strategy
    strategy: str  # "mean_reversion", "trend_following", etc.
    trading_tf: str  # "4H", "1D", etc.
    
    # Execution
    entry_price: float  # initial entry price
    avg_entry_price: float  # average across all fills
    current_price: float  # current mark price
    
    qty: float  # position quantity
    size_usd: float  # position size in USD
    
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    
    # PnL
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    trade_count: int = 0  # number of fills
    
    # Timestamps
    opened_at: datetime
    closed_at: Optional[datetime] = None
    
    # Logic & Intelligence
    thesis: str  # current thesis
    thesis_history: List[dict] = []  # thesis changes over time
    switch_reason: Optional[str] = None  # if switched from another strategy
    
    # Execution data
    fills: List[dict] = []  # list of fill IDs or fill objects
    order_ids: List[str] = []  # associated order IDs
    
    # Metadata
    decision_id: Optional[str] = None  # link to allocator decision
    experiment_id: str = "baseline_btc"  # STEP 1.5.4: Experiment isolation
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            float: lambda v: round(v, 8)
        }


class CaseCreateRequest(BaseModel):
    """Request to create a new trading case."""
    symbol: str
    side: Literal["LONG", "SHORT"]
    strategy: str
    trading_tf: str
    entry_price: float
    qty: float
    size_usd: float
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    thesis: str
    decision_id: Optional[str] = None
    experiment_id: str = "baseline_btc"  # STEP 1.5.4: Experiment isolation with safe default


class CaseUpdateRequest(BaseModel):
    """Request to update a trading case."""
    current_price: Optional[float] = None
    thesis: Optional[str] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None


class CaseCloseRequest(BaseModel):
    """Request to close a trading case."""
    close_reason: str  # "STOP_HIT", "TARGET_HIT", "MANUAL", "SWITCH"
    close_price: float
