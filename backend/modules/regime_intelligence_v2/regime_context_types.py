"""
Regime Context — Types

Unified context combining:
- MarketRegime
- StrategyRegimeMapping
- RegimeTransitionState

This is the final integrated view for execution decisions.
"""

from typing import Literal, List
from datetime import datetime
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

RegimeType = Literal["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]
NextRegimeCandidate = Literal["TRENDING", "RANGING", "VOLATILE", "ILLIQUID", "NONE"]
TransitionState = Literal["STABLE", "EARLY_SHIFT", "ACTIVE_TRANSITION", "UNSTABLE"]
ContextState = Literal["SUPPORTIVE", "NEUTRAL", "CONFLICTED"]


# ══════════════════════════════════════════════════════════════
# Main Contract
# ══════════════════════════════════════════════════════════════

class RegimeContext(BaseModel):
    """
    Unified regime context for execution decisions.
    
    Combines:
    - MarketRegime (current state)
    - StrategyRegimeMapping (strategy suitability)
    - RegimeTransitionState (transition risk)
    """
    # From MarketRegime
    current_regime: RegimeType
    regime_confidence: float = Field(ge=0.0, le=1.0)
    dominant_driver: str
    
    # From RegimeTransitionState
    next_regime_candidate: NextRegimeCandidate
    transition_probability: float = Field(ge=0.0, le=1.0)
    transition_state: TransitionState
    
    # From StrategyRegimeMapping
    favored_strategies: List[str] = Field(default_factory=list)
    neutral_strategies: List[str] = Field(default_factory=list)
    disfavored_strategies: List[str] = Field(default_factory=list)
    
    # Computed modifiers (from transition state)
    confidence_modifier: float = Field(ge=0.0, le=1.0)
    capital_modifier: float = Field(ge=0.0, le=1.0)
    
    # Unified context state
    context_state: ContextState
    
    # Explanation
    reason: str
    
    # Metadata
    symbol: str = "BTCUSDT"
    timeframe: str = "1H"
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class RegimeContextSummary(BaseModel):
    """Summary of regime context state."""
    current_regime: RegimeType
    regime_confidence: float
    
    transition_state: TransitionState
    transition_probability: float
    
    context_state: ContextState
    
    total_favored: int
    total_neutral: int
    total_disfavored: int
    
    confidence_modifier: float
    capital_modifier: float
