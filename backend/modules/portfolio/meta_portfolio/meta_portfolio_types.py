"""
PHASE 18.3 — Meta Portfolio Types
=================================
Contracts for Meta Portfolio Aggregator.

Purpose:
    Define contracts for the unified portfolio management layer
    that combines Portfolio Intelligence and Portfolio Constraints.

Key States:
- BALANCED: Portfolio healthy, no restrictions
- CONSTRAINED: Soft limits hit or intelligence warning
- RISK_OFF: Hard limits hit, no new positions allowed
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class PortfolioState(str, Enum):
    """Meta portfolio state."""
    BALANCED = "BALANCED"         # Portfolio healthy, no restrictions
    CONSTRAINED = "CONSTRAINED"   # Soft limits or intelligence warning
    RISK_OFF = "RISK_OFF"         # Hard limits, no new positions


# ══════════════════════════════════════════════════════════════
# STATE MAPPING
# ══════════════════════════════════════════════════════════════

# Mapping from (constraint_state, intelligence_state) to portfolio_state
# Priority: HARD constraints > SOFT constraints > Intelligence state

STATE_PRIORITY = {
    "HARD_LIMIT": PortfolioState.RISK_OFF,
    "SOFT_LIMIT": PortfolioState.CONSTRAINED,
}

INTELLIGENCE_TO_PORTFOLIO = {
    "BALANCED": PortfolioState.BALANCED,
    "CONCENTRATED": PortfolioState.CONSTRAINED,
    "OVERLOADED": PortfolioState.CONSTRAINED,
    "DEFENSIVE": PortfolioState.RISK_OFF,
}


# ══════════════════════════════════════════════════════════════
# MAIN OUTPUT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class MetaPortfolioState:
    """
    Meta Portfolio State - Main output contract.
    
    Unified portfolio management state combining:
    - Portfolio Intelligence (risk assessment)
    - Portfolio Constraints (limit enforcement)
    
    Key fields:
    - portfolio_state: BALANCED / CONSTRAINED / RISK_OFF
    - allowed: Whether new positions can be opened
    - confidence_modifier: Combined modifier for trade confidence
    - capital_modifier: Combined modifier for position sizing
    """
    # Main state
    portfolio_state: PortfolioState
    
    # Component states
    intelligence_state: str
    constraint_state: str
    
    # Permission
    allowed: bool
    
    # Combined modifiers (min of both sources)
    confidence_modifier: float
    capital_modifier: float
    
    # Exposure metrics (from intelligence)
    net_exposure: float
    gross_exposure: float
    
    # Concentration metrics (from intelligence)
    concentration_score: float
    diversification_score: float
    
    # Action
    recommended_action: str
    
    # Reason
    reason: str
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Component details
    intelligence_details: Dict[str, Any] = field(default_factory=dict)
    constraint_details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "portfolio_state": self.portfolio_state.value,
            "intelligence_state": self.intelligence_state,
            "constraint_state": self.constraint_state,
            "allowed": self.allowed,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "net_exposure": round(self.net_exposure, 4),
            "gross_exposure": round(self.gross_exposure, 4),
            "concentration_score": round(self.concentration_score, 4),
            "diversification_score": round(self.diversification_score, 4),
            "recommended_action": self.recommended_action,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict:
        """Full dictionary with all details."""
        result = self.to_dict()
        result["intelligence_details"] = self.intelligence_details
        result["constraint_details"] = self.constraint_details
        return result
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "state": self.portfolio_state.value,
            "allowed": self.allowed,
            "confidence_mod": round(self.confidence_modifier, 2),
            "capital_mod": round(self.capital_modifier, 2),
            "action": self.recommended_action,
        }
