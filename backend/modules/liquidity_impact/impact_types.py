"""
Liquidity Impact Types

PHASE 37 Sublayer — Liquidity Impact Engine

Types for estimating trade execution impact on market.

Key Formulas:
- expected_slippage_bps = order_size / effective_depth × 10000
- market_impact_bps = 0.50 * slippage + 0.30 * vacuum_penalty + 0.20 * pressure_penalty
- fill_quality = 1 - normalized_impact
"""

from typing import Literal, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Impact state thresholds (in basis points)
SLIPPAGE_THRESHOLDS = {
    "LOW_IMPACT": 5,      # < 5 bps
    "MANAGEABLE": 15,     # 5-15 bps
    "HIGH_IMPACT": 30,    # 15-30 bps
    "UNTRADEABLE": 100,   # > 30 bps
}

# Position size modifiers based on impact state
IMPACT_MODIFIERS = {
    "LOW_IMPACT": 1.00,
    "MANAGEABLE": 0.85,
    "HIGH_IMPACT": 0.60,
    "UNTRADEABLE": 0.00,
}

# Market impact formula weights
WEIGHT_SLIPPAGE = 0.50
WEIGHT_VACUUM = 0.30
WEIGHT_PRESSURE = 0.20


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

LiquidityBucket = Literal[
    "DEEP",      # High liquidity, minimal impact
    "NORMAL",    # Standard liquidity
    "THIN",      # Low liquidity, moderate impact
    "FRAGILE",   # Very low liquidity, high impact
]

ImpactState = Literal[
    "LOW_IMPACT",     # < 5 bps
    "MANAGEABLE",     # 5-15 bps
    "HIGH_IMPACT",    # 15-30 bps
    "UNTRADEABLE",    # > 30 bps
]

ExecutionRecommendation = Literal[
    "MARKET_OK",       # Safe for market order
    "LIMIT_PREFERRED", # Use limit order
    "TWAP_REQUIRED",   # Split order over time
    "BLOCK_TRADE",     # Use block trade / OTC
]

SideType = Literal["BUY", "SELL"]


# ══════════════════════════════════════════════════════════════
# Liquidity Impact Estimate
# ══════════════════════════════════════════════════════════════

class LiquidityImpactEstimate(BaseModel):
    """
    Main contract for liquidity impact estimation.
    
    Estimates what happens to the market if we execute the intended trade.
    """
    symbol: str
    
    # Order intent
    intended_size_usd: float = Field(ge=0)
    side: SideType
    
    # Impact metrics (in basis points)
    expected_slippage_bps: float = Field(ge=0)
    expected_market_impact_bps: float = Field(ge=0)
    
    # Fill quality [0, 1] where 1 = excellent
    expected_fill_quality: float = Field(ge=0, le=1)
    
    # Classifications
    liquidity_bucket: LiquidityBucket = "NORMAL"
    impact_state: ImpactState = "MANAGEABLE"
    
    # Recommendation
    execution_recommendation: ExecutionRecommendation = "LIMIT_PREFERRED"
    
    # Size modifier (how much to reduce size)
    size_modifier: float = Field(ge=0, le=1, default=1.0)
    
    # Component metrics
    vacuum_penalty_bps: float = 0.0
    pressure_penalty_bps: float = 0.0
    
    # Depth info
    effective_depth_usd: float = 0.0
    depth_ratio: float = 0.0  # intended_size / effective_depth
    
    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Explanation
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Order Book Depth Input
# ══════════════════════════════════════════════════════════════

class OrderBookDepth(BaseModel):
    """
    Order book depth information for impact calculation.
    """
    symbol: str
    
    # Depth near mid price (USD)
    bid_depth_1pct: float = 0.0  # Depth within 1% of mid
    ask_depth_1pct: float = 0.0
    
    # Spread
    spread_bps: float = 0.0
    
    # Imbalance
    imbalance_ratio: float = 0.0  # [-1, 1]
    
    timestamp: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Impact Summary
# ══════════════════════════════════════════════════════════════

class ImpactSummary(BaseModel):
    """
    Summary statistics for impact history.
    """
    symbol: str
    
    # Current state
    current_liquidity_bucket: str = "NORMAL"
    current_impact_state: str = "MANAGEABLE"
    
    # Historical stats
    total_estimates: int = 0
    avg_slippage_bps: float = 0.0
    avg_market_impact_bps: float = 0.0
    avg_fill_quality: float = 0.0
    
    # Distribution
    low_impact_count: int = 0
    manageable_count: int = 0
    high_impact_count: int = 0
    untradeable_count: int = 0
    
    # Recent
    recent_avg_slippage_bps: float = 0.0
    
    last_updated: Optional[datetime] = None
