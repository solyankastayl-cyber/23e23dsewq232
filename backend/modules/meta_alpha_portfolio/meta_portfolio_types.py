"""
Meta-Alpha Portfolio Types

PHASE 45 — Meta-Alpha Portfolio Engine

Distributes capital between alpha types, not assets.

Alpha families:
- TREND_BREAKOUT
- MEAN_REVERSION
- FRACTAL
- CAPITAL_FLOW
- REFLEXIVITY

Formula:
meta_score = 0.35 * success_rate + 0.25 * avg_pnl + 0.20 * regime_fit + 0.20 * decay_adjusted
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class AlphaFamily(str, Enum):
    """Alpha family types."""
    TREND_BREAKOUT = "TREND_BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"
    FRACTAL = "FRACTAL"
    CAPITAL_FLOW = "CAPITAL_FLOW"
    REFLEXIVITY = "REFLEXIVITY"


class PatternClass(str, Enum):
    """Pattern classification by meta score."""
    STRONG = "STRONG"       # >= 0.70
    MODERATE = "MODERATE"   # 0.55 - 0.70
    WEAK = "WEAK"           # < 0.55


# Meta score formula weights
META_SCORE_WEIGHTS = {
    "success_rate": 0.35,
    "avg_pnl": 0.25,
    "regime_fit": 0.20,
    "decay_adjusted": 0.20,
}

# Pattern class thresholds
PATTERN_THRESHOLDS = {
    "STRONG": 0.70,
    "MODERATE": 0.55,
}


class MetaAlphaWeight(BaseModel):
    """
    Weight for a single alpha family.
    
    PHASE 45 Core Contract.
    """
    weight_id: str = Field(default_factory=lambda: f"maw_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    alpha_family: AlphaFamily
    
    # Performance metrics
    recent_success_rate: float = 0.5      # Win rate 0-1
    recent_avg_pnl: float = 0.0           # Average PnL per trade
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Fit scores
    regime_fit_score: float = 0.5         # How well alpha fits current regime
    decay_adjusted_score: float = 0.5     # Adjusted for signal decay
    
    # Computed values
    meta_score: float = 0.5               # Combined score
    meta_weight: float = 0.2              # Normalized weight (sum=1)
    pattern_class: PatternClass = PatternClass.MODERATE
    
    # Hypothesis modifier
    hypothesis_modifier: float = 1.0       # Applied to hypothesis confidence
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def compute_meta_score(self) -> float:
        """Compute meta score from components."""
        # Normalize avg_pnl to 0-1 range (assuming typical range -5% to +5%)
        normalized_pnl = (self.recent_avg_pnl + 5) / 10
        normalized_pnl = max(0, min(1, normalized_pnl))
        
        self.meta_score = (
            META_SCORE_WEIGHTS["success_rate"] * self.recent_success_rate
            + META_SCORE_WEIGHTS["avg_pnl"] * normalized_pnl
            + META_SCORE_WEIGHTS["regime_fit"] * self.regime_fit_score
            + META_SCORE_WEIGHTS["decay_adjusted"] * self.decay_adjusted_score
        )
        
        # Determine pattern class
        if self.meta_score >= PATTERN_THRESHOLDS["STRONG"]:
            self.pattern_class = PatternClass.STRONG
            self.hypothesis_modifier = 1.08
        elif self.meta_score >= PATTERN_THRESHOLDS["MODERATE"]:
            self.pattern_class = PatternClass.MODERATE
            self.hypothesis_modifier = 1.0
        else:
            self.pattern_class = PatternClass.WEAK
            self.hypothesis_modifier = 0.93
        
        return self.meta_score


class MetaAlphaPortfolioState(BaseModel):
    """
    Complete meta-alpha portfolio state.
    
    Shows how capital should be distributed between alpha families.
    """
    state_id: str = Field(default_factory=lambda: f"maps_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Alpha weights
    alpha_weights: Dict[str, MetaAlphaWeight] = Field(default_factory=dict)
    
    # Summary
    dominant_alpha_family: Optional[str] = None
    diversification_score: float = 0.5    # 0=concentrated, 1=diversified
    total_signals_tracked: int = 0
    
    # Statistics
    best_performing_family: Optional[str] = None
    worst_performing_family: Optional[str] = None
    avg_meta_score: float = 0.5
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetaAlphaConfig(BaseModel):
    """Configuration for Meta-Alpha Portfolio Engine."""
    # Score formula weights
    success_rate_weight: float = 0.35
    avg_pnl_weight: float = 0.25
    regime_fit_weight: float = 0.20
    decay_adjusted_weight: float = 0.20
    
    # Pattern class thresholds
    strong_threshold: float = 0.70
    moderate_threshold: float = 0.55
    
    # Modifiers
    strong_modifier: float = 1.08
    weak_modifier: float = 0.93
    
    # Rebalance
    rebalance_interval_minutes: int = 30
    min_trades_for_stats: int = 10
    
    # Lookback
    lookback_hours: int = 168  # 7 days


class TradeOutcome(BaseModel):
    """Record of a trade outcome for learning."""
    outcome_id: str = Field(default_factory=lambda: f"to_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    hypothesis_id: str
    alpha_family: AlphaFamily
    symbol: str
    
    entry_time: datetime
    exit_time: Optional[datetime] = None
    
    entry_price: float
    exit_price: Optional[float] = None
    
    pnl_pct: float = 0.0
    is_winner: bool = False
    
    regime_at_entry: str = "UNKNOWN"
    signal_age_at_execution: int = 0
    
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
