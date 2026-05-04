"""
PHASE 14.4 — Trading Decision Types
====================================
Trading decision output contracts.

This is the final decision layer that answers:
"What should we do right now?"

Actions:
- ALLOW: Execute trade with normal size
- ALLOW_REDUCED: Execute with reduced size due to conflict
- ALLOW_AGGRESSIVE: Execute with increased size due to strong alignment
- BLOCK: Do not execute trade
- WAIT: Wait for better setup/conditions
- REVERSE_CANDIDATE: Potential opposite direction trade
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ACTION ENUMS
# ══════════════════════════════════════════════════════════════

class DecisionAction(str, Enum):
    """Trading decision action."""
    ALLOW = "ALLOW"
    ALLOW_REDUCED = "ALLOW_REDUCED"
    ALLOW_AGGRESSIVE = "ALLOW_AGGRESSIVE"
    BLOCK = "BLOCK"
    WAIT = "WAIT"
    REVERSE_CANDIDATE = "REVERSE_CANDIDATE"


class ExecutionMode(str, Enum):
    """Execution mode for the trade."""
    NONE = "NONE"           # Blocked/no trade
    PASSIVE = "PASSIVE"     # Limit orders, patient entry
    NORMAL = "NORMAL"       # Standard execution
    AGGRESSIVE = "AGGRESSIVE"  # Market orders, immediate
    WAIT = "WAIT"           # Hold, wait for better conditions


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# DECISION RULE ENUM (for explainability)
# ══════════════════════════════════════════════════════════════

class DecisionRule(str, Enum):
    """Which rule triggered the decision."""
    NO_SETUP = "no_setup"
    STRONG_AGREEMENT = "strong_agreement"
    MILD_AGREEMENT = "mild_agreement"
    WEAK_CONFLICT = "weak_conflict"
    STRONG_CONFLICT = "strong_conflict"
    EXTREME_CONFLICT_REVERSE = "extreme_conflict_reverse"
    BAD_MARKET_STATE = "bad_market_state"
    LOW_CONVICTION = "low_conviction"


# ══════════════════════════════════════════════════════════════
# TRADING DECISION CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class TradingDecision:
    """
    Final trading decision output.
    
    This is what the execution layer consumes.
    """
    symbol: str
    timestamp: datetime
    
    # Core decision
    action: DecisionAction
    direction: TradeDirection
    
    # Confidence and sizing
    confidence: float  # 0..1
    position_multiplier: float  # 0.0 .. 1.25
    
    # Execution guidance
    execution_mode: ExecutionMode
    
    # Explainability
    reason: str
    decision_rule: DecisionRule
    drivers: Dict[str, any] = field(default_factory=dict)
    
    # Raw input summaries
    ta_summary: Dict[str, any] = field(default_factory=dict)
    exchange_summary: Dict[str, any] = field(default_factory=dict)
    market_state_summary: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 4),
            "position_multiplier": round(self.position_multiplier, 3),
            "execution_mode": self.execution_mode.value,
            "reason": self.reason,
            "decision_rule": self.decision_rule.value,
            "drivers": self.drivers,
        }
    
    def to_full_dict(self) -> Dict:
        """Include raw input summaries for debugging."""
        result = self.to_dict()
        result["ta_summary"] = self.ta_summary
        result["exchange_summary"] = self.exchange_summary
        result["market_state_summary"] = self.market_state_summary
        return result


# ══════════════════════════════════════════════════════════════
# INPUT SNAPSHOTS
# ══════════════════════════════════════════════════════════════

@dataclass
class TADecisionInput:
    """TA Hypothesis input for decision."""
    direction: str  # LONG / SHORT / NEUTRAL
    setup_quality: float  # 0..1
    trend_strength: float  # 0..1
    entry_quality: float  # 0..1
    regime_fit: float  # 0..1
    conviction: float  # 0..1
    setup_type: str  # BREAKOUT / PULLBACK / etc
    has_valid_setup: bool


@dataclass
class ExchangeDecisionInput:
    """Exchange Context input for decision."""
    bias: str  # BULLISH / BEARISH / NEUTRAL
    confidence: float  # 0..1
    conflict_ratio: float  # 0..1
    dominant_signal: str
    crowding_risk: float  # 0..1
    squeeze_probability: float  # 0..1
    cascade_probability: float  # 0..1
    derivatives_pressure: float  # -1 to 1
    flow_pressure: float  # -1 to 1


@dataclass
class MarketStateDecisionInput:
    """Market State input for decision."""
    trend_state: str
    volatility_state: str
    exchange_state: str
    derivatives_state: str
    risk_state: str
    combined_state: str
    confidence: float
    is_hostile: bool
    is_supportive: bool
