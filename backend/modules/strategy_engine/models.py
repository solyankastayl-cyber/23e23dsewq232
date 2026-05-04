"""
Strategy Engine Models
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class Signal(BaseModel):
    """Trading signal (raw idea)."""
    signal_id: str
    symbol: str
    side: str  # BUY | SELL
    strategy: str
    timeframe: str
    confidence: float
    entry_price: float
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    thesis: str
    metadata: Dict[str, Any] = {}
    created_at: int


class Decision(BaseModel):
    """Signal after risk evaluation."""
    decision_id: str
    signal_id: str
    symbol: str
    side: str
    strategy: str
    timeframe: str
    approved: bool
    reject_reason: Optional[str] = None
    confidence: float
    risk_score: float
    position_size_usd: float
    order_type: str
    signal: Dict[str, Any]  # Original signal
    created_at: int


class StrategyState(BaseModel):
    """Strategy memory state."""
    symbol: str
    last_signal: Optional[str] = None  # BUY | SELL
    last_entry_price: Optional[float] = None
    last_trade_time: Optional[int] = None
    cooldown_until: Optional[int] = None
    consecutive_losses: int = 0
    updated_at: int
