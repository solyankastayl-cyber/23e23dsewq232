"""Signal Models — Trading Signal Schema"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TradingSignal:
    """Trading signal with all necessary metadata."""
    
    symbol: str
    timeframe: str
    direction: str      # LONG / SHORT
    strategy: str
    confidence: float   # 0..1
    entry: float
    stop: float
    target: float
    reason: str
    asset_vol: float = 0.02
    metadata: Optional[dict] = None
