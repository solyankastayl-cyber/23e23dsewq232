"""
Fractal Market Intelligence Types

PHASE 32.1 — Fractal Market Intelligence Engine Types

Types for multi-timeframe structural market state analysis.
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Timeframes to analyze
TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]

# Timeframe states
TimeframeState = Literal["TREND_UP", "TREND_DOWN", "RANGE", "VOLATILE"]

# Fractal bias types
FractalBias = Literal["LONG", "SHORT", "NEUTRAL"]

# Alignment thresholds
ALIGNMENT_BIAS_THRESHOLD = 0.6
ALIGNMENT_NEUTRAL_THRESHOLD = 0.4

# Confidence weights
ALIGNMENT_WEIGHT = 0.60
VOLATILITY_CONSISTENCY_WEIGHT = 0.40

# Fractal modifiers
FRACTAL_ALIGNED_MODIFIER = 1.08
FRACTAL_CONFLICT_MODIFIER = 0.92


# ══════════════════════════════════════════════════════════════
# Fractal Market State
# ══════════════════════════════════════════════════════════════

class FractalMarketState(BaseModel):
    """
    Multi-timeframe fractal market state.
    
    Captures structural state across 5 timeframes to determine
    fractal alignment and bias.
    """
    symbol: str
    
    # Timeframe states
    tf_5m_state: TimeframeState = "RANGE"
    tf_15m_state: TimeframeState = "RANGE"
    tf_1h_state: TimeframeState = "RANGE"
    tf_4h_state: TimeframeState = "RANGE"
    tf_1d_state: TimeframeState = "RANGE"
    
    # Fractal metrics
    fractal_alignment: float = Field(ge=0.0, le=1.0, default=0.0)
    fractal_bias: FractalBias = "NEUTRAL"
    fractal_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Volatility consistency
    volatility_consistency: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Raw data
    tf_states: Dict[str, str] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_all_states(self) -> Dict[str, str]:
        """Get all timeframe states as dict."""
        return {
            "5m": self.tf_5m_state,
            "15m": self.tf_15m_state,
            "1h": self.tf_1h_state,
            "4h": self.tf_4h_state,
            "1d": self.tf_1d_state,
        }


# ══════════════════════════════════════════════════════════════
# Fractal Summary
# ══════════════════════════════════════════════════════════════

class FractalSummary(BaseModel):
    """
    Summary of fractal market intelligence.
    """
    symbol: str
    
    current_alignment: float = 0.0
    current_bias: FractalBias = "NEUTRAL"
    current_confidence: float = 0.0
    
    # State distribution
    trend_up_count: int = 0
    trend_down_count: int = 0
    range_count: int = 0
    volatile_count: int = 0
    
    # Historical averages
    avg_alignment: float = 0.0
    avg_confidence: float = 0.0
    
    # Alignment streaks
    alignment_streak: int = 0
    highest_alignment: float = 0.0
    
    total_snapshots: int = 0
    last_updated: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Timeframe Analysis
# ══════════════════════════════════════════════════════════════

class TimeframeAnalysis(BaseModel):
    """
    Analysis for a single timeframe.
    """
    timeframe: str
    state: TimeframeState
    
    # Indicators
    ema_slope: float = 0.0  # Normalized EMA slope
    atr_expansion: float = 0.0  # ATR relative to average
    structure_break: bool = False  # Recent structure break
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


# ══════════════════════════════════════════════════════════════
# Fractal Modifier Response
# ══════════════════════════════════════════════════════════════

class FractalModifier(BaseModel):
    """
    Modifier for hypothesis scoring based on fractal alignment.
    """
    hypothesis_bias: str
    fractal_bias: FractalBias
    alignment: float
    
    is_aligned: bool
    modifier: float
    
    reason: str
