"""
PHASE 19.3 — Strategy Regime Types
==================================
Type definitions for Strategy Regime Switch module.

Core contracts:
- StrategyPriorityState: Priority state for strategies
- RegimeStrategyConfig: Configuration for regime-strategy mapping
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# REGIME CONFIDENCE WEIGHTS
# ══════════════════════════════════════════════════════════════

REGIME_CONFIDENCE_WEIGHTS = {
    "regime": 0.40,
    "volatility": 0.20,
    "breadth": 0.15,
    "interaction": 0.15,
    "ecology": 0.10,
}


# ══════════════════════════════════════════════════════════════
# PRIORITY MODIFIERS
# ══════════════════════════════════════════════════════════════

PRIORITY_MODIFIERS = {
    "primary": {
        "confidence_modifier": 1.10,
        "capital_modifier": 1.15,
    },
    "secondary": {
        "confidence_modifier": 1.05,
        "capital_modifier": 1.05,
    },
    "inactive": {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.80,
    },
}


# ══════════════════════════════════════════════════════════════
# STRATEGY PRIORITY STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategyPriorityState:
    """
    Priority state for strategies based on current regime.
    
    Determines which strategies should be prioritized.
    """
    market_regime: str                   # Current detected regime
    regime_confidence: float             # Confidence in regime detection
    
    # Strategy priorities
    primary_strategy: str                # Highest priority strategy
    secondary_strategies: List[str]      # Supporting strategies
    inactive_strategies: List[str]       # Deprioritized strategies
    
    # Modifiers per strategy
    strategy_modifiers: Dict[str, Dict[str, float]]
    
    # Input scores
    regime_score: float = 0.0
    volatility_score: float = 0.0
    breadth_score: float = 0.0
    interaction_score: float = 0.0
    ecology_score: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "market_regime": self.market_regime,
            "regime_confidence": round(self.regime_confidence, 4),
            "primary_strategy": self.primary_strategy,
            "secondary_strategies": self.secondary_strategies,
            "inactive_strategies": self.inactive_strategies,
            "strategy_modifiers": {
                k: {mk: round(mv, 4) for mk, mv in v.items()}
                for k, v in self.strategy_modifiers.items()
            },
            "breakdown": {
                "regime_score": round(self.regime_score, 4),
                "volatility_score": round(self.volatility_score, 4),
                "breadth_score": round(self.breadth_score, 4),
                "interaction_score": round(self.interaction_score, 4),
                "ecology_score": round(self.ecology_score, 4),
            },
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "regime": self.market_regime,
            "confidence": round(self.regime_confidence, 3),
            "primary": self.primary_strategy,
            "secondary_count": len(self.secondary_strategies),
            "inactive_count": len(self.inactive_strategies),
        }
    
    def get_modifier_for_strategy(self, strategy_name: str) -> Dict[str, float]:
        """Get modifiers for a specific strategy."""
        return self.strategy_modifiers.get(strategy_name, PRIORITY_MODIFIERS["inactive"])


# ══════════════════════════════════════════════════════════════
# REGIME STRATEGY CONFIG
# ══════════════════════════════════════════════════════════════

@dataclass
class RegimeStrategyConfig:
    """
    Configuration for regime-to-strategy mapping.
    """
    regime_name: str
    primary_strategies: List[str]        # Strategies that work best in this regime
    secondary_strategies: List[str]      # Supporting strategies
    anti_strategies: List[str]           # Strategies to avoid
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "regime_name": self.regime_name,
            "primary_strategies": self.primary_strategies,
            "secondary_strategies": self.secondary_strategies,
            "anti_strategies": self.anti_strategies,
        }


# ══════════════════════════════════════════════════════════════
# REGIME SWITCH SUMMARY
# ══════════════════════════════════════════════════════════════

@dataclass
class RegimeSwitchSummary:
    """
    Summary of regime switch state across symbols.
    """
    dominant_regime: str
    regime_stability: float              # How stable the regime is
    
    primary_strategies: List[str]        # Strategies in primary across symbols
    
    strategy_priority_map: Dict[str, str]  # strategy -> priority level
    
    symbols_analyzed: List[str]
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dominant_regime": self.dominant_regime,
            "regime_stability": round(self.regime_stability, 4),
            "primary_strategies": self.primary_strategies,
            "strategy_priority_map": self.strategy_priority_map,
            "symbols_analyzed": self.symbols_analyzed,
            "timestamp": self.timestamp.isoformat(),
        }
