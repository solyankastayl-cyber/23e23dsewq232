"""
PHASE 21.2 — Capital Budget Types
=================================
Type definitions for Capital Budget Engine.

Core contracts:
- CapitalBudgetState: System-wide budget constraints
- BudgetState: Overall budget state enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# BUDGET STATE ENUM
# ══════════════════════════════════════════════════════════════

class BudgetState(str, Enum):
    """Overall budget state."""
    OPEN = "OPEN"             # > 0.95 multiplier - full deployment
    THROTTLED = "THROTTLED"   # 0.75-0.95 - reduced deployment
    DEFENSIVE = "DEFENSIVE"   # 0.50-0.75 - defensive posture
    EMERGENCY = "EMERGENCY"   # < 0.50 - emergency mode


# ══════════════════════════════════════════════════════════════
# DEFAULT SLEEVE LIMITS
# ══════════════════════════════════════════════════════════════

DEFAULT_SLEEVE_LIMITS = {
    "strategy": 0.35,    # Max 35% to any single strategy
    "factor": 0.25,      # Max 25% to any single factor
    "asset": 0.50,       # Max 50% to any single asset
    "cluster": 0.45,     # Max 45% to any single cluster
}


# ══════════════════════════════════════════════════════════════
# RESERVE CAPITAL BY REGIME
# ══════════════════════════════════════════════════════════════

RESERVE_CAPITAL_BY_REGIME = {
    "normal": 0.10,
    "unclear": 0.15,
    "mixed": 0.15,
    "high_vol": 0.20,
    "stressed": 0.20,
    "crisis": 0.30,
    "emergency": 0.35,
}


# ══════════════════════════════════════════════════════════════
# REGIME THROTTLE MULTIPLIERS
# ══════════════════════════════════════════════════════════════

REGIME_THROTTLE = {
    "TREND": 1.00,
    "TREND_UP": 1.00,
    "TREND_DOWN": 0.95,
    "RANGE": 0.85,
    "SQUEEZE": 0.75,
    "VOL": 0.70,
    "HIGH_VOL": 0.70,
    "VOL_EXPANSION": 0.70,
    "MIXED": 0.80,
    "CRISIS": 0.50,
    "RISK_OFF": 0.50,
}


# ══════════════════════════════════════════════════════════════
# EMERGENCY CUT LEVELS
# ══════════════════════════════════════════════════════════════

EMERGENCY_CUT_LEVELS = {
    "normal": 1.00,
    "mild_stress": 0.90,
    "defensive": 0.75,
    "emergency": 0.50,
}


# ══════════════════════════════════════════════════════════════
# BUDGET STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

BUDGET_STATE_THRESHOLDS = {
    BudgetState.OPEN: 0.95,
    BudgetState.THROTTLED: 0.75,
    BudgetState.DEFENSIVE: 0.50,
    # Below 0.50 = EMERGENCY
}


# ══════════════════════════════════════════════════════════════
# CAPITAL BUDGET STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class CapitalBudgetState:
    """
    System-wide Capital Budget State.
    
    Controls:
    - How much capital can be deployed
    - Reserve requirements
    - Dry powder allocation
    - Sleeve limits
    - Emergency cuts
    """
    total_capital: float
    deployable_capital: float
    
    reserve_capital: float
    dry_powder: float
    
    sleeve_limits: Dict[str, float]
    
    regime_throttle: float
    emergency_cut: float
    
    final_budget_multiplier: float
    
    budget_state: BudgetState
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Explainability
    reason: str
    
    # Input details
    regime_input: str = "MIXED"
    portfolio_state_input: str = "NORMAL"
    loop_state_input: str = "HEALTHY"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_capital": round(self.total_capital, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            
            "reserve_capital": round(self.reserve_capital, 4),
            "dry_powder": round(self.dry_powder, 4),
            
            "sleeve_limits": {k: round(v, 4) for k, v in self.sleeve_limits.items()},
            
            "regime_throttle": round(self.regime_throttle, 4),
            "emergency_cut": round(self.emergency_cut, 4),
            
            "final_budget_multiplier": round(self.final_budget_multiplier, 4),
            
            "budget_state": self.budget_state.value,
            
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            
            "reason": self.reason,
            
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with input details."""
        result = self.to_dict()
        result["inputs"] = {
            "regime": self.regime_input,
            "portfolio_state": self.portfolio_state_input,
            "loop_state": self.loop_state_input,
        }
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "total_capital": round(self.total_capital, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "final_budget_multiplier": round(self.final_budget_multiplier, 4),
            "budget_state": self.budget_state.value,
            "reserve_capital": round(self.reserve_capital, 4),
            "dry_powder": round(self.dry_powder, 4),
        }


# ══════════════════════════════════════════════════════════════
# SLEEVE LIMIT STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class SleeveLimitState:
    """Sleeve limit information."""
    sleeve_name: str
    max_limit: float
    current_allocation: float
    utilization: float          # current / max
    headroom: float             # max - current
    is_breached: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sleeve_name": self.sleeve_name,
            "max_limit": round(self.max_limit, 4),
            "current_allocation": round(self.current_allocation, 4),
            "utilization": round(self.utilization, 4),
            "headroom": round(self.headroom, 4),
            "is_breached": self.is_breached,
        }
