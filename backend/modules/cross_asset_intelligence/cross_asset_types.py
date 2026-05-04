"""
PHASE 25.3 — Cross-Asset Intelligence Types

Data models for cross-asset bridge engine.
Formalizes the causal chain: Macro → DXY → SPX → BTC
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Bridge Types
# ══════════════════════════════════════════════════════════════

AlignmentType = Literal["SUPPORTIVE", "CONTRARY", "MIXED", "NEUTRAL"]
InfluenceDirection = Literal["BULLISH", "BEARISH", "NEUTRAL"]
AlignmentStateType = Literal["STRONG", "MODERATE", "WEAK", "CONFLICTED"]
FinalBiasType = Literal["BULLISH", "BEARISH", "MIXED", "NEUTRAL"]


# ══════════════════════════════════════════════════════════════
# Bridge Contract
# ══════════════════════════════════════════════════════════════

class CrossAssetBridge(BaseModel):
    """
    Represents causal influence between two layers.
    
    Bridges:
    - Macro → DXY: Macro regime affects USD strength
    - DXY → SPX: Dollar strength affects equity pressure
    - SPX → BTC: Risk appetite affects crypto
    """
    
    source: str = Field(
        description="Source layer: MACRO, DXY, or SPX"
    )
    target: str = Field(
        description="Target layer: DXY, SPX, or BTC"
    )
    
    alignment: AlignmentType = Field(
        description="How well source and target align"
    )
    influence_direction: InfluenceDirection = Field(
        description="Direction of influence propagation"
    )
    
    strength: float = Field(
        ge=0.0, le=1.0,
        description="Bridge signal strength"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in bridge assessment"
    )
    
    # Computed effective strength with alignment penalty
    effective_strength: float = Field(
        ge=0.0, le=1.0,
        default=0.0,
        description="strength * alignment_multiplier"
    )
    
    reason: str = Field(
        description="Human-readable explanation"
    )


# ══════════════════════════════════════════════════════════════
# Aggregate Alignment Contract
# ══════════════════════════════════════════════════════════════

class CrossAssetAlignment(BaseModel):
    """
    Aggregate cross-asset alignment state.
    
    Combines all three bridges into unified assessment
    of the Macro → DXY → SPX → BTC chain.
    """
    
    # Individual bridges
    macro_dxy: CrossAssetBridge = Field(
        description="Macro → DXY bridge"
    )
    dxy_spx: CrossAssetBridge = Field(
        description="DXY → SPX bridge"
    )
    spx_btc: CrossAssetBridge = Field(
        description="SPX → BTC bridge"
    )
    
    # Aggregate score
    alignment_score: float = Field(
        ge=0.0, le=1.0,
        description="Weighted aggregate alignment score"
    )
    alignment_state: AlignmentStateType = Field(
        description="Overall alignment state"
    )
    
    # Bridge analysis
    dominant_bridge: str = Field(
        description="Strongest bridge (macro_dxy, dxy_spx, spx_btc)"
    )
    weakest_bridge: str = Field(
        description="Weakest bridge"
    )
    
    # Final assessment
    final_bias: FinalBiasType = Field(
        description="Final directional bias for BTC"
    )
    
    reason: str = Field(
        description="Human-readable explanation"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="25.3.0")


# ══════════════════════════════════════════════════════════════
# Summary Contract
# ══════════════════════════════════════════════════════════════

class CrossAssetSummary(BaseModel):
    """Compact summary of cross-asset alignment."""
    alignment_score: float
    alignment_state: AlignmentStateType
    final_bias: FinalBiasType
    dominant_bridge: str
    weakest_bridge: str


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class CrossAssetHealthStatus(BaseModel):
    """Health status for cross-asset module."""
    status: Literal["OK", "DEGRADED", "ERROR"]
    macro_available: bool
    dxy_available: bool
    spx_available: bool
    btc_available: bool
    bridges_computed: int
    last_update: Optional[datetime]


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Alignment multipliers for effective strength
ALIGNMENT_MULTIPLIERS = {
    "SUPPORTIVE": 1.0,
    "MIXED": 0.7,
    "NEUTRAL": 0.5,
    "CONTRARY": 0.2,
}

# Alignment state thresholds
ALIGNMENT_STATE_THRESHOLDS = {
    "STRONG": 0.70,
    "MODERATE": 0.50,
    "WEAK": 0.30,
}

# Bridge weights for aggregate score
BRIDGE_WEIGHTS = {
    "macro_dxy": 0.30,
    "dxy_spx": 0.30,
    "spx_btc": 0.40,  # BTC-facing bridge has highest weight
}
