"""
PHASE 22.4 — Correlation Spike Types
====================================
Type definitions for Correlation Spike Engine.

Core contracts:
- CorrelationSpikeState: Correlation metrics and state
- CorrelationState: Correlation level enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# CORRELATION STATE ENUM
# ══════════════════════════════════════════════════════════════

class CorrelationState(str, Enum):
    """Correlation regime state."""
    NORMAL = "NORMAL"         # spike < 0.35
    ELEVATED = "ELEVATED"     # spike 0.35-0.55
    HIGH = "HIGH"             # spike 0.55-0.75
    SYSTEMIC = "SYSTEMIC"     # spike > 0.75


# ══════════════════════════════════════════════════════════════
# CORRELATION RECOMMENDED ACTION ENUM
# ══════════════════════════════════════════════════════════════

class CorrelationAction(str, Enum):
    """Correlation-based recommended action."""
    HOLD = "HOLD"                                     # NORMAL
    REDUCE_RISK = "REDUCE_RISK"                       # ELEVATED
    REDUCE_DIVERSIFICATION = "REDUCE_DIVERSIFICATION" # HIGH
    DELEVER = "DELEVER"                               # SYSTEMIC


# ══════════════════════════════════════════════════════════════
# CORRELATION STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

CORRELATION_THRESHOLDS = {
    CorrelationState.NORMAL: 0.35,
    CorrelationState.ELEVATED: 0.55,
    CorrelationState.HIGH: 0.75,
    # > 0.75 = SYSTEMIC
}


# ══════════════════════════════════════════════════════════════
# VOLATILITY -> ASSET CORRELATION MAPPING
# ══════════════════════════════════════════════════════════════

VOLATILITY_CORRELATION_MAP = {
    "LOW": 0.30,
    "NORMAL": 0.45,
    "HIGH": 0.65,
    "EXPANDING": 0.75,
    "EXTREME": 0.85,
    "COMPRESSED": 0.35,
    "CRISIS": 0.85,
}


# ══════════════════════════════════════════════════════════════
# STRATEGY TYPE CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════

STRATEGY_TYPE_CORRELATION = {
    ("trend", "breakout"): 0.75,
    ("trend", "momentum"): 0.70,
    ("breakout", "momentum"): 0.65,
    ("mean_reversion", "reversal"): 0.60,
    ("trend", "mean_reversion"): 0.25,
    ("breakout", "mean_reversion"): 0.30,
    ("arb", "arb"): 0.50,
    ("arb", "trend"): 0.20,
    ("arb", "mean_reversion"): 0.25,
}


# ══════════════════════════════════════════════════════════════
# FACTOR OVERLAP WEIGHTS
# ══════════════════════════════════════════════════════════════

FACTOR_OVERLAP_WEIGHTS = {
    ("trend_factor", "breakout_factor"): 0.65,
    ("trend_factor", "momentum_factor"): 0.60,
    ("flow_factor", "momentum_factor"): 0.55,
    ("flow_factor", "volume_factor"): 0.50,
    ("volatility_factor", "regime_factor"): 0.45,
    ("mean_reversion_factor", "volatility_factor"): 0.40,
}


# ══════════════════════════════════════════════════════════════
# CORRELATION SPIKE WEIGHTS
# ══════════════════════════════════════════════════════════════

CORRELATION_SPIKE_WEIGHTS = {
    "asset_correlation": 0.40,
    "strategy_correlation": 0.35,
    "factor_correlation": 0.25,
}


# ══════════════════════════════════════════════════════════════
# CORRELATION STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

CORRELATION_MODIFIERS = {
    CorrelationState.NORMAL: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    CorrelationState.ELEVATED: {
        "confidence_modifier": 0.95,
        "capital_modifier": 0.90,
    },
    CorrelationState.HIGH: {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
    CorrelationState.SYSTEMIC: {
        "confidence_modifier": 0.70,
        "capital_modifier": 0.55,
    },
}


# ══════════════════════════════════════════════════════════════
# CORRELATION SPIKE STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class CorrelationSpikeState:
    """
    Correlation Spike State.
    
    Captures correlation regime shifts when diversification breaks down.
    """
    # Correlation components
    asset_correlation: float
    strategy_correlation: float
    factor_correlation: float
    
    # Diversification
    diversification_score: float
    
    # Composite
    correlation_spike_intensity: float
    correlation_state: CorrelationState
    
    # Action
    recommended_action: CorrelationAction
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Analysis
    dominant_correlation: str  # asset / strategy / factor
    
    # Explainability
    reason: str
    
    # Input context
    volatility_state: str = "NORMAL"
    breadth_state: str = "NEUTRAL"
    dominance_regime: str = "NEUTRAL"
    risk_state: str = "NORMAL"
    tail_risk_state: str = "LOW"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "asset_correlation": round(self.asset_correlation, 4),
            "strategy_correlation": round(self.strategy_correlation, 4),
            "factor_correlation": round(self.factor_correlation, 4),
            "diversification_score": round(self.diversification_score, 4),
            "correlation_spike_intensity": round(self.correlation_spike_intensity, 4),
            "correlation_state": self.correlation_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "dominant_correlation": self.dominant_correlation,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with input details."""
        result = self.to_dict()
        result["inputs"] = {
            "volatility_state": self.volatility_state,
            "breadth_state": self.breadth_state,
            "dominance_regime": self.dominance_regime,
            "risk_state": self.risk_state,
            "tail_risk_state": self.tail_risk_state,
        }
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "asset_correlation": round(self.asset_correlation, 4),
            "strategy_correlation": round(self.strategy_correlation, 4),
            "factor_correlation": round(self.factor_correlation, 4),
            "diversification_score": round(self.diversification_score, 4),
            "correlation_spike_intensity": round(self.correlation_spike_intensity, 4),
            "correlation_state": self.correlation_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# CORRELATION HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class CorrelationHistoryEntry:
    """Single history entry for correlation state."""
    correlation_state: CorrelationState
    correlation_spike_intensity: float
    diversification_score: float
    dominant_correlation: str
    recommended_action: CorrelationAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_state": self.correlation_state.value,
            "correlation_spike_intensity": round(self.correlation_spike_intensity, 4),
            "diversification_score": round(self.diversification_score, 4),
            "dominant_correlation": self.dominant_correlation,
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
