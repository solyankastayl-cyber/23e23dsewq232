"""
PHASE 17.4 — Attribution Types
===============================
Contracts for Attribution / Failure Forensics Engine.

Purpose:
    Define contracts for trade attribution, failure analysis,
    and explainability of trading decisions.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class TradeOutcome(str, Enum):
    """Trade outcome classification."""
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    OPEN = "OPEN"


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "LONG"
    SHORT = "SHORT"


class FailureClassification(str, Enum):
    """Classification of trade failure reasons."""
    MODEL_ERROR = "MODEL_ERROR"                    # TA/signal model was wrong
    MARKET_REGIME_SHIFT = "MARKET_REGIME_SHIFT"   # Market changed during trade
    EXECUTION_ERROR = "EXECUTION_ERROR"           # Slippage, timing issues
    RISK_MODEL_ERROR = "RISK_MODEL_ERROR"         # Position sizing / risk was wrong
    EXTERNAL_SHOCK = "EXTERNAL_SHOCK"             # Black swan event
    LIQUIDITY_TRAP = "LIQUIDITY_TRAP"             # Trapped in low liquidity
    CROWDING_REVERSAL = "CROWDING_REVERSAL"       # Too many on same side
    FALSE_BREAKOUT = "FALSE_BREAKOUT"             # Breakout failed
    GOVERNANCE_DEGRADATION = "GOVERNANCE_DEGRADATION"  # Factor/feature degraded
    NONE = "NONE"                                 # No failure (winning trade)


class SystemLayer(str, Enum):
    """System layers for attribution."""
    TA = "TA"
    EXCHANGE = "Exchange"
    MARKET_STATE = "MarketState"
    ECOLOGY = "Ecology"
    INTERACTION = "Interaction"
    GOVERNANCE = "Governance"
    POSITION_SIZING = "PositionSizing"
    EXECUTION = "Execution"


class FailureSource(str, Enum):
    """Possible failure sources."""
    TA_ERROR = "ta_error"
    MARKET_REGIME_SHIFT = "market_regime_shift"
    CROWDING_REVERSAL = "crowding_reversal"
    FALSE_BREAKOUT = "false_breakout"
    LIQUIDITY_TRAP = "liquidity_trap"
    EXECUTION_SLIPPAGE = "execution_slippage"
    GOVERNANCE_DEGRADATION = "governance_degradation"
    STRUCTURE_FLOW_CONFLICT = "structure_flow_conflict"
    ECOLOGY_STRESS = "ecology_stress"
    INTERACTION_CONFLICT = "interaction_conflict"


# ══════════════════════════════════════════════════════════════
# LAYER CONTRIBUTION WEIGHTS
# ══════════════════════════════════════════════════════════════

DEFAULT_LAYER_WEIGHTS = {
    SystemLayer.TA: 0.30,
    SystemLayer.EXCHANGE: 0.20,
    SystemLayer.MARKET_STATE: 0.18,
    SystemLayer.ECOLOGY: 0.12,
    SystemLayer.INTERACTION: 0.12,
    SystemLayer.GOVERNANCE: 0.08,
}


# ══════════════════════════════════════════════════════════════
# INPUT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class TradeContext:
    """Context of a trade for attribution."""
    trade_id: str
    symbol: str
    direction: TradeDirection
    entry_price: float
    exit_price: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    position_size: float
    outcome: TradeOutcome
    pnl: float
    pnl_percent: float


@dataclass
class DecisionContext:
    """Context of the decision that led to the trade."""
    decision_confidence: float
    ta_score: float
    exchange_score: float
    market_state_score: float
    ecology_score: float
    interaction_score: float
    governance_score: float
    primary_factor: str
    secondary_factor: str
    execution_mode: str


@dataclass
class LayerContribution:
    """Contribution of a single layer."""
    layer: SystemLayer
    contribution: float  # 0-1
    score: float  # Raw score from layer
    influence: str  # POSITIVE / NEGATIVE / NEUTRAL
    details: Dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════
# TRADE ATTRIBUTION REPORT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class TradeAttributionReport:
    """
    Full attribution report for a trade.
    
    Explains:
    - WHY the trade happened
    - WHY it succeeded or failed
    - WHICH layer was responsible
    """
    trade_id: str
    timestamp: datetime
    
    # Trade details
    trade_direction: TradeDirection
    trade_outcome: TradeOutcome
    
    # Decision context
    decision_confidence: float
    position_size: float
    
    # Primary attribution
    primary_driver: str
    secondary_driver: str
    
    # Layer contributions
    layer_contributions: Dict[str, float]
    
    # Failure analysis (if applicable)
    failure_reason: Optional[FailureSource]
    failure_classification: FailureClassification
    responsible_layer: Optional[SystemLayer]
    
    # Breakdowns
    confidence_breakdown: Dict[str, float]
    risk_breakdown: Dict[str, float]
    
    # Human-readable explanation
    explanation: str
    
    # Detailed layer results
    layer_details: List[LayerContribution] = field(default_factory=list)
    
    # Metadata
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "trade_direction": self.trade_direction.value,
            "trade_outcome": self.trade_outcome.value,
            "decision_confidence": round(self.decision_confidence, 4),
            "position_size": round(self.position_size, 4),
            "primary_driver": self.primary_driver,
            "secondary_driver": self.secondary_driver,
            "layer_contributions": {
                k: round(v, 4) for k, v in self.layer_contributions.items()
            },
            "failure_reason": self.failure_reason.value if self.failure_reason else None,
            "failure_classification": self.failure_classification.value,
            "responsible_layer": self.responsible_layer.value if self.responsible_layer else None,
            "confidence_breakdown": {
                k: round(v, 4) for k, v in self.confidence_breakdown.items()
            },
            "risk_breakdown": {
                k: round(v, 4) for k, v in self.risk_breakdown.items()
            },
            "explanation": self.explanation,
            "layer_details": [
                {
                    "layer": lc.layer.value,
                    "contribution": round(lc.contribution, 4),
                    "score": round(lc.score, 4),
                    "influence": lc.influence,
                }
                for lc in self.layer_details
            ],
            "drivers": self.drivers,
        }
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "trade_id": self.trade_id,
            "trade_outcome": self.trade_outcome.value,
            "primary_driver": self.primary_driver,
            "responsible_layer": self.responsible_layer.value if self.responsible_layer else None,
            "failure_reason": self.failure_reason.value if self.failure_reason else None,
            "explanation": self.explanation[:200] + "..." if len(self.explanation) > 200 else self.explanation,
        }


# ══════════════════════════════════════════════════════════════
# BATCH REQUEST/RESPONSE
# ══════════════════════════════════════════════════════════════

@dataclass
class AttributionBatchRequest:
    """Request for batch attribution."""
    trade_ids: List[str]


@dataclass
class AttributionBatchResponse:
    """Response from batch attribution."""
    results: Dict[str, TradeAttributionReport]
    summary: Dict[str, Any]
    timestamp: datetime
