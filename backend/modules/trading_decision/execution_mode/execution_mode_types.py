"""
PHASE 14.6 — Execution Mode Types
==================================
Execution mode contracts and enums.

This layer determines HOW to enter a trade, not just whether to enter.
Even a good signal can be ruined by bad execution.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# EXECUTION MODE ENUM
# ══════════════════════════════════════════════════════════════

class ExecutionMode(str, Enum):
    """How to execute the trade."""
    NONE = "NONE"                    # No execution (blocked/wait)
    PASSIVE = "PASSIVE"              # Patient limit orders
    NORMAL = "NORMAL"                # Standard execution
    AGGRESSIVE = "AGGRESSIVE"        # Immediate market orders
    DELAYED = "DELAYED"              # Wait for better timing
    PARTIAL_ENTRY = "PARTIAL_ENTRY"  # Staged entry, split position


class EntryStyle(str, Enum):
    """Order type / entry approach."""
    MARKET = "MARKET"    # Market order, immediate
    LIMIT = "LIMIT"      # Limit order, patient
    STAGED = "STAGED"    # Multiple entries, DCA style
    WAIT = "WAIT"        # Do not enter yet


# ══════════════════════════════════════════════════════════════
# EXECUTION MODE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class ExecutionModeDecision:
    """
    Final execution mode output.
    
    Determines exactly how to enter the trade.
    """
    symbol: str
    timestamp: datetime
    
    # Core decision
    execution_mode: ExecutionMode
    urgency_score: float  # 0..1, how urgent is entry
    slippage_tolerance: float  # e.g. 0.1% - 1.0%
    entry_style: EntryStyle
    partial_ratio: float  # 0.0 - 1.0, how much to enter initially
    
    # Explainability
    reason: str
    drivers: Dict[str, any] = field(default_factory=dict)
    
    # Input summaries
    decision_summary: Dict[str, any] = field(default_factory=dict)
    sizing_summary: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "execution_mode": self.execution_mode.value,
            "urgency_score": round(self.urgency_score, 4),
            "slippage_tolerance": round(self.slippage_tolerance, 4),
            "entry_style": self.entry_style.value,
            "partial_ratio": round(self.partial_ratio, 4),
            "reason": self.reason,
            "drivers": {k: round(v, 4) if isinstance(v, float) else v for k, v in self.drivers.items()},
        }
    
    def to_full_dict(self) -> Dict:
        """Include input summaries for debugging."""
        result = self.to_dict()
        result["decision_summary"] = self.decision_summary
        result["sizing_summary"] = self.sizing_summary
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
    execution_mode_hint: str  # Base hint from decision layer


@dataclass
class SizingInputSnapshot:
    """Input from Position Sizing."""
    final_size_pct: float
    size_bucket: str
    risk_multiplier: float


@dataclass
class ExchangeInputSnapshot:
    """Input from Exchange Context."""
    conflict_ratio: float
    dominant_signal: str
    squeeze_probability: float
    confidence: float
    crowding_risk: float


@dataclass
class MarketStateInputSnapshot:
    """Input from Market State."""
    volatility_state: str
    exchange_state: str
    derivatives_state: str
    combined_state: str
    risk_state: str
