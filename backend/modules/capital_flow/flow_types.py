"""
Capital Flow Types

PHASE 42 — Capital Flow Engine

Fixed buckets: BTC, ETH, ALTS, CASH

flow_state = snapshot description (BTC_INFLOW, ETH_INFLOW, etc.)
flow_bias  = final scoring decision (BTC, ETH, ALTS, CASH, NEUTRAL)
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

class FlowBucket(str, Enum):
    """Fixed capital flow buckets."""
    BTC = "BTC"
    ETH = "ETH"
    ALTS = "ALTS"
    CASH = "CASH"


class FlowState(str, Enum):
    """Current flow state — snapshot description."""
    BTC_INFLOW = "BTC_INFLOW"
    ETH_INFLOW = "ETH_INFLOW"
    ALT_INFLOW = "ALT_INFLOW"
    CASH_INFLOW = "CASH_INFLOW"
    MIXED_FLOW = "MIXED_FLOW"


class FlowBias(str, Enum):
    """Final scoring bias — decision output."""
    BTC = "BTC"
    ETH = "ETH"
    ALTS = "ALTS"
    CASH = "CASH"
    NEUTRAL = "NEUTRAL"


class RotationType(str, Enum):
    """Capital rotation types."""
    BTC_TO_ETH = "BTC_TO_ETH"
    ETH_TO_ALTS = "ETH_TO_ALTS"
    ALTS_TO_BTC = "ALTS_TO_BTC"
    BTC_TO_CASH = "BTC_TO_CASH"
    ETH_TO_CASH = "ETH_TO_CASH"
    RISK_TO_CASH = "RISK_TO_CASH"
    CASH_TO_BTC = "CASH_TO_BTC"
    CASH_TO_ETH = "CASH_TO_ETH"
    NO_ROTATION = "NO_ROTATION"


# ══════════════════════════════════════════════════════════════
# 42.1 — Flow Snapshot
# ══════════════════════════════════════════════════════════════

class CapitalFlowSnapshot(BaseModel):
    """
    Capital flow snapshot — PHASE 42.1

    Shows where capital is flowing right now.
    Each flow_score is normalized: -1 (outflow) .. +1 (inflow).
    """
    snapshot_id: str = Field(default_factory=lambda: f"cfs_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Flow scores per bucket: -1..+1
    btc_flow_score: float = 0.0
    eth_flow_score: float = 0.0
    alt_flow_score: float = 0.0
    cash_flow_score: float = 0.0

    # Dominance shifts (separate per asset)
    btc_dominance_shift: float = 0.0
    eth_dominance_shift: float = 0.0

    # Market structure shifts
    oi_shift: float = 0.0
    funding_shift: float = 0.0
    volume_shift: float = 0.0

    # Flow state — snapshot description
    flow_state: FlowState = FlowState.MIXED_FLOW


# ══════════════════════════════════════════════════════════════
# 42.2 — Rotation State
# ══════════════════════════════════════════════════════════════

class RotationState(BaseModel):
    """
    Capital rotation state — PHASE 42.2

    Identifies rotation direction between buckets.
    """
    rotation_id: str = Field(default_factory=lambda: f"rot_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    rotation_type: RotationType = RotationType.NO_ROTATION

    from_bucket: FlowBucket = FlowBucket.BTC
    to_bucket: FlowBucket = FlowBucket.ETH

    rotation_strength: float = 0.0  # 0..1
    confidence: float = 0.0         # 0..1

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# 42.3 — Flow Score
# ══════════════════════════════════════════════════════════════

class FlowScore(BaseModel):
    """
    Flow score — PHASE 42.3

    Final scoring output.
    flow_bias is the decision output (not same as flow_state).
    """
    score_id: str = Field(default_factory=lambda: f"fs_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    flow_bias: FlowBias = FlowBias.NEUTRAL

    flow_strength: float = 0.0      # 0..1
    flow_confidence: float = 0.0    # 0..1

    dominant_rotation: RotationType = RotationType.NO_ROTATION

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Combined Result
# ══════════════════════════════════════════════════════════════

class CapitalFlowResult(BaseModel):
    """Full capital flow analysis result."""
    snapshot: CapitalFlowSnapshot
    rotation: RotationState
    score: FlowScore


# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════

class CapitalFlowConfig(BaseModel):
    """Capital flow engine configuration."""
    # Rotation formula weights
    rotation_weight_flow_diff: float = 0.40
    rotation_weight_dominance: float = 0.20
    rotation_weight_oi: float = 0.20
    rotation_weight_volume: float = 0.20

    # Flow score formula weights
    score_weight_rotation: float = 0.50
    score_weight_dominance: float = 0.30
    score_weight_volume: float = 0.20

    # Confidence formula weights
    confidence_weight_strength: float = 0.60
    confidence_weight_rotation: float = 0.40

    # Thresholds
    min_rotation_strength: float = 0.15    # Below this = NO_ROTATION
    min_flow_strength: float = 0.10        # Below this = NEUTRAL bias
    strong_flow_threshold: float = 0.50    # Above this = strong signal

    # Data source weights for flow score computation
    performance_weight: float = 0.30
    oi_weight: float = 0.25
    funding_weight: float = 0.15
    volume_weight: float = 0.20
    dominance_weight: float = 0.10
