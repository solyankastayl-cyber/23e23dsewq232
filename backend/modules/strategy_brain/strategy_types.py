"""
Strategy Brain — Types

PHASE 29.5 — Strategy Brain Integration with Hypothesis Engine

Types for strategy selection based on market hypothesis.
"""

from typing import Optional, List, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Strategy Definitions
# ══════════════════════════════════════════════════════════════

StrategyType = Literal[
    "trend_following",
    "breakout_trading",
    "mean_reversion",
    "volatility_expansion",
    "liquidation_capture",
    "range_trading",
    "basis_trade",
    "funding_arb",
    "none",
]

# All available strategies
AVAILABLE_STRATEGIES: List[str] = [
    "trend_following",
    "breakout_trading",
    "mean_reversion",
    "volatility_expansion",
    "liquidation_capture",
    "range_trading",
    "basis_trade",
    "funding_arb",
]


# ══════════════════════════════════════════════════════════════
# Hypothesis → Strategy Mapping
# ══════════════════════════════════════════════════════════════

HYPOTHESIS_STRATEGY_MAP = {
    "BULLISH_CONTINUATION": ["trend_following", "breakout_trading"],
    "BEARISH_CONTINUATION": ["trend_following", "volatility_expansion"],
    "BREAKOUT_FORMING": ["breakout_trading", "volatility_expansion"],
    "RANGE_MEAN_REVERSION": ["mean_reversion", "range_trading"],
    "SHORT_SQUEEZE_SETUP": ["liquidation_capture", "volatility_expansion"],
    "LONG_SQUEEZE_SETUP": ["liquidation_capture", "volatility_expansion"],
    "VOLATILE_UNWIND": ["volatility_expansion", "mean_reversion"],
    "BREAKOUT_FAILURE_RISK": ["mean_reversion", "range_trading"],
    "NO_EDGE": [],
}


# ══════════════════════════════════════════════════════════════
# Microstructure Quality Mapping
# ══════════════════════════════════════════════════════════════

MICROSTRUCTURE_EXECUTION_QUALITY = {
    "SUPPORTIVE": 1.0,
    "NEUTRAL": 0.7,
    "FRAGILE": 0.45,
    "STRESSED": 0.25,
}


# ══════════════════════════════════════════════════════════════
# Suitability Score Weights
# ══════════════════════════════════════════════════════════════

WEIGHT_CONFIDENCE = 0.45
WEIGHT_RELIABILITY = 0.25
WEIGHT_REGIME = 0.20
WEIGHT_MICROSTRUCTURE = 0.10


# ══════════════════════════════════════════════════════════════
# Strategy Decision
# ══════════════════════════════════════════════════════════════

class StrategyDecision(BaseModel):
    """
    Strategy decision output from Strategy Brain.
    
    Contains selected strategy and supporting metrics.
    """
    symbol: str
    
    # Hypothesis context
    hypothesis_type: str
    directional_bias: str
    
    # Strategy selection
    selected_strategy: StrategyType
    alternative_strategies: List[str] = Field(default_factory=list)
    
    # Scoring
    suitability_score: float = Field(ge=0.0, le=1.0)
    
    # Execution context
    execution_state: str
    
    # Confidence metrics (from hypothesis)
    confidence: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    
    # Explanation
    reason: str
    
    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategySummary(BaseModel):
    """
    Summary statistics for strategy decisions.
    """
    symbol: str
    total_decisions: int
    
    # Strategy distribution
    trend_following_count: int = 0
    breakout_trading_count: int = 0
    mean_reversion_count: int = 0
    volatility_expansion_count: int = 0
    liquidation_capture_count: int = 0
    range_trading_count: int = 0
    basis_trade_count: int = 0
    funding_arb_count: int = 0
    none_count: int = 0
    
    # Averages
    avg_suitability_score: float = 0.0
    avg_confidence: float = 0.0
    avg_reliability: float = 0.0
    
    # Current
    current_strategy: str = "none"
    current_hypothesis: str = "NO_EDGE"


class StrategyCandidate(BaseModel):
    """
    Candidate strategy for selection.
    """
    strategy: str
    base_score: float
    adjusted_score: float
    reason: str
