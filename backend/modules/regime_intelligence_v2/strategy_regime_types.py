"""
Strategy Regime Mapping — Types

Contracts for strategy-regime mapping.

Strategies:
- trend_following, breakout, mean_reversion
- liquidation_capture, funding_arb, basis_trade
- volatility_expansion, range_trading

States:
- FAVORED: Strategy works well in this regime
- NEUTRAL: Strategy is regime-agnostic
- DISFAVORED: Strategy underperforms in this regime
"""

from typing import Literal, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

StrategyType = Literal[
    "trend_following",
    "breakout",
    "mean_reversion",
    "liquidation_capture",
    "funding_arb",
    "basis_trade",
    "volatility_expansion",
    "range_trading",
]

MappingState = Literal["FAVORED", "NEUTRAL", "DISFAVORED"]

STRATEGY_LIST: List[str] = [
    "trend_following",
    "breakout",
    "mean_reversion",
    "liquidation_capture",
    "funding_arb",
    "basis_trade",
    "volatility_expansion",
    "range_trading",
]


# ══════════════════════════════════════════════════════════════
# Suitability Ranges
# ══════════════════════════════════════════════════════════════

SUITABILITY_RANGES = {
    "FAVORED": (0.75, 0.90),
    "NEUTRAL": (0.45, 0.65),
    "DISFAVORED": (0.10, 0.35),
}

# Modifiers by state
STATE_MODIFIERS = {
    "FAVORED": {
        "confidence_modifier": 1.08,
        "capital_modifier": 1.12,
    },
    "NEUTRAL": {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    "DISFAVORED": {
        "confidence_modifier": 0.90,
        "capital_modifier": 0.82,
    },
}


# ══════════════════════════════════════════════════════════════
# Mapping Matrix
# ══════════════════════════════════════════════════════════════

# Base mapping: regime -> strategy -> state
REGIME_STRATEGY_MATRIX: Dict[str, Dict[str, str]] = {
    "TRENDING": {
        "trend_following": "FAVORED",
        "breakout": "FAVORED",
        "volatility_expansion": "NEUTRAL",
        "liquidation_capture": "NEUTRAL",
        "mean_reversion": "DISFAVORED",
        "range_trading": "DISFAVORED",
        "basis_trade": "DISFAVORED",
        "funding_arb": "NEUTRAL",
    },
    "RANGING": {
        "mean_reversion": "FAVORED",
        "range_trading": "FAVORED",
        "funding_arb": "FAVORED",
        "basis_trade": "NEUTRAL",
        "trend_following": "DISFAVORED",
        "breakout": "DISFAVORED",
        "volatility_expansion": "NEUTRAL",
        "liquidation_capture": "NEUTRAL",
    },
    "VOLATILE": {
        "volatility_expansion": "FAVORED",
        "liquidation_capture": "FAVORED",
        "breakout": "NEUTRAL",
        "trend_following": "NEUTRAL",
        "mean_reversion": "DISFAVORED",
        "basis_trade": "DISFAVORED",
        "funding_arb": "DISFAVORED",
        "range_trading": "DISFAVORED",
    },
    "ILLIQUID": {
        "funding_arb": "FAVORED",
        "basis_trade": "FAVORED",
        "range_trading": "NEUTRAL",
        "mean_reversion": "NEUTRAL",
        "breakout": "DISFAVORED",
        "liquidation_capture": "DISFAVORED",
        "volatility_expansion": "DISFAVORED",
        "trend_following": "DISFAVORED",
    },
}


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class StrategyRegimeMapping(BaseModel):
    """
    Mapping of a single strategy to current regime.
    
    Determines if strategy is favored/neutral/disfavored.
    """
    strategy: StrategyType
    regime_type: str
    
    # Suitability score (0.0 - 1.0)
    suitability: float = Field(ge=0.0, le=1.0)
    
    # Modifiers for position sizing
    confidence_modifier: float = Field(ge=0.0)
    capital_modifier: float = Field(ge=0.0)
    
    # Classification
    state: MappingState
    
    # Explanation
    reason: str
    
    # Metadata
    regime_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class RegimeStrategySummary(BaseModel):
    """Summary of strategy suitability for current regime."""
    regime_type: str
    regime_confidence: float
    
    favored_strategies: List[str] = Field(default_factory=list)
    neutral_strategies: List[str] = Field(default_factory=list)
    disfavored_strategies: List[str] = Field(default_factory=list)
    
    total_strategies: int = 8


# ══════════════════════════════════════════════════════════════
# History Record
# ══════════════════════════════════════════════════════════════

class StrategyRegimeHistoryRecord(BaseModel):
    """Historical record of strategy-regime mapping."""
    strategy: str
    regime_type: str
    suitability: float
    state: MappingState
    confidence_modifier: float
    capital_modifier: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
