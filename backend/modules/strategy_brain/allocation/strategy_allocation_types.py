"""
PHASE 19.2 — Strategy Allocation Types
======================================
Type definitions for Strategy Allocation module.

Core contracts:
- StrategyAllocationState: Allocation state for single strategy
- StrategyAllocationSummary: Aggregated allocation summary
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# BASE WEIGHTS CONFIGURATION
# ══════════════════════════════════════════════════════════════

BASE_WEIGHTS: Dict[str, float] = {
    "trend_following": 0.18,
    "mean_reversion": 0.18,
    "breakout": 0.14,
    "liquidation_capture": 0.10,
    "flow_following": 0.12,
    "volatility_expansion": 0.10,
    "funding_arb": 0.10,
    "structure_reversal": 0.08,
}

# Total = 1.0


# ══════════════════════════════════════════════════════════════
# STATE MULTIPLIERS
# ══════════════════════════════════════════════════════════════

STATE_MULTIPLIERS: Dict[str, float] = {
    "ACTIVE": 1.0,
    "REDUCED": 0.6,
    "DISABLED": 0.0,
}


# ══════════════════════════════════════════════════════════════
# CONFIDENCE MODIFIER BOUNDS
# ══════════════════════════════════════════════════════════════

CONFIDENCE_MODIFIER_MIN = 0.75
CONFIDENCE_MODIFIER_MAX = 1.25


# ══════════════════════════════════════════════════════════════
# STRATEGY ALLOCATION STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategyAllocationState:
    """
    Allocation state for a single strategy.
    
    Represents how much capital is allocated to this strategy
    and the resulting modifiers.
    """
    strategy_name: str
    strategy_state: str          # ACTIVE / REDUCED / DISABLED
    
    # Weights
    base_weight: float           # Original base weight
    state_multiplier: float      # Multiplier from state
    adjusted_weight: float       # After state adjustment
    
    # Capital allocation
    capital_share: float         # Normalized share (0-1)
    capital_percent: float       # Percentage (0-100)
    
    # Modifiers
    confidence_modifier: float   # Bounded modifier for signals
    capital_modifier: float      # From strategy state
    
    # Metadata
    reason: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "strategy_state": self.strategy_state,
            "base_weight": round(self.base_weight, 4),
            "state_multiplier": round(self.state_multiplier, 2),
            "adjusted_weight": round(self.adjusted_weight, 4),
            "capital_share": round(self.capital_share, 4),
            "capital_percent": round(self.capital_percent, 2),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "name": self.strategy_name,
            "state": self.strategy_state,
            "share": round(self.capital_share, 3),
            "pct": round(self.capital_percent, 1),
        }


# ══════════════════════════════════════════════════════════════
# STRATEGY ALLOCATION SUMMARY
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategyAllocationSummary:
    """
    Aggregated summary of all strategy allocations.
    
    Provides global view of capital distribution.
    """
    total_capital: float                           # Always 1.0
    
    # Allocations dict (strategy -> share)
    allocations: Dict[str, float]
    allocations_percent: Dict[str, float]          # Percentage form
    
    # Strategy lists by state
    active_strategies: List[str]
    reduced_strategies: List[str]
    disabled_strategies: List[str]
    
    # Counts
    total_strategies: int
    active_count: int
    reduced_count: int
    disabled_count: int
    
    # Capital distribution
    active_capital: float                          # Capital in ACTIVE
    reduced_capital: float                         # Capital in REDUCED
    
    # Full allocations
    allocation_states: List[StrategyAllocationState] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_capital": round(self.total_capital, 4),
            "allocations": {k: round(v, 4) for k, v in self.allocations.items()},
            "allocations_percent": {k: round(v, 2) for k, v in self.allocations_percent.items()},
            "active_strategies": self.active_strategies,
            "reduced_strategies": self.reduced_strategies,
            "disabled_strategies": self.disabled_strategies,
            "counts": {
                "total": self.total_strategies,
                "active": self.active_count,
                "reduced": self.reduced_count,
                "disabled": self.disabled_count,
            },
            "capital_distribution": {
                "active_capital": round(self.active_capital, 4),
                "reduced_capital": round(self.reduced_capital, 4),
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all allocation details."""
        result = self.to_dict()
        result["strategies"] = [s.to_dict() for s in self.allocation_states]
        return result
