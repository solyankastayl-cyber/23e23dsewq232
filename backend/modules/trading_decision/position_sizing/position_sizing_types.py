"""
PHASE 14.5 — Position Sizing Types
===================================
Position sizing contracts and enums.

This layer determines HOW MUCH to trade, not just whether to trade.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# SIZE BUCKET ENUM
# ══════════════════════════════════════════════════════════════

class SizeBucket(str, Enum):
    """Position size classification bucket."""
    NONE = "NONE"      # 0.00
    TINY = "TINY"      # 0.01 - 0.35
    SMALL = "SMALL"    # 0.35 - 0.70
    NORMAL = "NORMAL"  # 0.70 - 1.05
    LARGE = "LARGE"    # 1.05+


# ══════════════════════════════════════════════════════════════
# POSITION SIZING CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class PositionSizingDecision:
    """
    Final position sizing output.
    
    Determines exact position size based on multiple factors.
    
    PHASE 15.7: Added ecology_adjustment.
    """
    symbol: str
    timestamp: datetime
    
    # Base and adjustments
    base_risk: float  # e.g. 1.0%
    risk_multiplier: float  # 0.0 .. 1.5 from decision action
    volatility_adjustment: float  # 0.5 .. 1.2
    exchange_adjustment: float  # 0.5 .. 1.2
    market_adjustment: float  # 0.5 .. 1.2
    
    # PHASE 14.9: Dominance/Breadth adjustments
    dominance_adjustment: float  # 0.8 .. 1.2
    breadth_adjustment: float  # 0.8 .. 1.1
    
    # PHASE 15.7: Ecology adjustment
    ecology_adjustment: float  # 0.5 .. 1.1
    
    # Final result
    final_size_pct: float  # final risk % / position size
    size_bucket: SizeBucket
    
    # Explainability
    reason: str
    drivers: Dict[str, any] = field(default_factory=dict)
    
    # Raw input summaries
    decision_summary: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "base_risk": round(self.base_risk, 4),
            "risk_multiplier": round(self.risk_multiplier, 4),
            "volatility_adjustment": round(self.volatility_adjustment, 4),
            "exchange_adjustment": round(self.exchange_adjustment, 4),
            "market_adjustment": round(self.market_adjustment, 4),
            "dominance_adjustment": round(self.dominance_adjustment, 4),
            "breadth_adjustment": round(self.breadth_adjustment, 4),
            "ecology_adjustment": round(self.ecology_adjustment, 4),
            "final_size_pct": round(self.final_size_pct, 4),
            "size_bucket": self.size_bucket.value,
            "reason": self.reason,
            "drivers": {k: round(v, 4) if isinstance(v, float) else v for k, v in self.drivers.items()},
        }
    
    def to_full_dict(self) -> Dict:
        """Include decision summary for debugging."""
        result = self.to_dict()
        result["decision_summary"] = self.decision_summary
        return result


# ══════════════════════════════════════════════════════════════
# INPUT SNAPSHOTS
# ══════════════════════════════════════════════════════════════

@dataclass
class DecisionInputSnapshot:
    """Input from Trading Decision."""
    action: str
    direction: str
    confidence: float
    position_multiplier: float
    execution_mode: str


@dataclass
class TAInputSnapshot:
    """Input from TA Hypothesis."""
    setup_quality: float
    entry_quality: float
    conviction: float
    trend_strength: float


@dataclass
class ExchangeInputSnapshot:
    """Input from Exchange Context."""
    confidence: float
    conflict_ratio: float
    crowding_risk: float
    squeeze_probability: float
    bias: str


@dataclass
class MarketStateInputSnapshot:
    """Input from Market State."""
    volatility_state: str
    derivatives_state: str
    risk_state: str
    combined_state: str
    confidence: float
