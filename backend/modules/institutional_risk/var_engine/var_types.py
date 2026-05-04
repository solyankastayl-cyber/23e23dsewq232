"""
PHASE 22.1 — VaR Types
======================
Type definitions for VaR Engine.

Core contracts:
- VaRState: Portfolio VaR and risk state
- RiskState: Overall risk state enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# RISK STATE ENUM
# ══════════════════════════════════════════════════════════════

class RiskState(str, Enum):
    """Portfolio risk state."""
    NORMAL = "NORMAL"         # VaR ratio < 0.10
    ELEVATED = "ELEVATED"     # VaR ratio 0.10-0.18
    HIGH = "HIGH"             # VaR ratio 0.18-0.28
    CRITICAL = "CRITICAL"     # VaR ratio > 0.28


# ══════════════════════════════════════════════════════════════
# RECOMMENDED ACTION ENUM
# ══════════════════════════════════════════════════════════════

class RecommendedAction(str, Enum):
    """Risk-based recommended action."""
    HOLD = "HOLD"                   # Normal - maintain positions
    REDUCE_RISK = "REDUCE_RISK"     # Elevated - reduce exposure
    DELEVER = "DELEVER"             # High - significant deleveraging
    EMERGENCY_CUT = "EMERGENCY_CUT" # Critical - emergency action


# ══════════════════════════════════════════════════════════════
# RISK STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

RISK_STATE_THRESHOLDS = {
    RiskState.NORMAL: 0.10,
    RiskState.ELEVATED: 0.18,
    RiskState.HIGH: 0.28,
    # > 0.28 = CRITICAL
}


# ══════════════════════════════════════════════════════════════
# VOLATILITY MULTIPLIERS
# ══════════════════════════════════════════════════════════════

VOLATILITY_MULTIPLIERS = {
    "LOW": 0.7,
    "NORMAL": 1.0,
    "HIGH": 1.4,
    "EXPANDING": 1.7,
    "EXTREME": 2.0,
    "COMPRESSED": 0.8,
}


# ══════════════════════════════════════════════════════════════
# REGIME MULTIPLIERS
# ══════════════════════════════════════════════════════════════

REGIME_MULTIPLIERS = {
    "TREND": 0.9,
    "TREND_UP": 0.9,
    "TREND_DOWN": 1.0,
    "RANGE": 1.0,
    "MIXED": 1.1,
    "SQUEEZE": 1.3,
    "VOL": 1.3,
    "HIGH_VOL": 1.4,
    "CRISIS": 1.6,
    "RISK_OFF": 1.5,
}


# ══════════════════════════════════════════════════════════════
# RISK STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

RISK_STATE_MODIFIERS = {
    RiskState.NORMAL: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    RiskState.ELEVATED: {
        "confidence_modifier": 0.95,
        "capital_modifier": 0.90,
    },
    RiskState.HIGH: {
        "confidence_modifier": 0.88,
        "capital_modifier": 0.75,
    },
    RiskState.CRITICAL: {
        "confidence_modifier": 0.75,
        "capital_modifier": 0.50,
    },
}


# ══════════════════════════════════════════════════════════════
# VAR STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class VaRState:
    """
    Portfolio VaR State.
    
    Contains:
    - Portfolio VaR at 95% and 99% confidence
    - Expected Shortfall / CVaR
    - Risk ratios
    - Risk state and recommended action
    """
    # VaR values
    portfolio_var_95: float
    portfolio_var_99: float
    
    # Expected Shortfall
    expected_shortfall_95: float
    expected_shortfall_99: float
    
    # Ratios
    var_ratio: float              # VaR relative to deployable capital
    tail_risk_ratio: float        # ES relative to VaR
    
    # State
    risk_state: RiskState
    recommended_action: RecommendedAction
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Explainability
    reason: str
    
    # Input details
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    deployable_capital: float = 1.0
    volatility_state: str = "NORMAL"
    regime: str = "MIXED"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "portfolio_var_95": round(self.portfolio_var_95, 4),
            "portfolio_var_99": round(self.portfolio_var_99, 4),
            
            "expected_shortfall_95": round(self.expected_shortfall_95, 4),
            "expected_shortfall_99": round(self.expected_shortfall_99, 4),
            
            "var_ratio": round(self.var_ratio, 4),
            "tail_risk_ratio": round(self.tail_risk_ratio, 4),
            
            "risk_state": self.risk_state.value,
            "recommended_action": self.recommended_action.value,
            
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            
            "reason": self.reason,
            
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with input details."""
        result = self.to_dict()
        result["inputs"] = {
            "gross_exposure": round(self.gross_exposure, 4),
            "net_exposure": round(self.net_exposure, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "volatility_state": self.volatility_state,
            "regime": self.regime,
        }
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "portfolio_var_95": round(self.portfolio_var_95, 4),
            "var_ratio": round(self.var_ratio, 4),
            "risk_state": self.risk_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# VAR HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class VaRHistoryEntry:
    """Single history entry for VaR state."""
    risk_state: RiskState
    portfolio_var_95: float
    var_ratio: float
    recommended_action: RecommendedAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_state": self.risk_state.value,
            "portfolio_var_95": round(self.portfolio_var_95, 4),
            "var_ratio": round(self.var_ratio, 4),
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
