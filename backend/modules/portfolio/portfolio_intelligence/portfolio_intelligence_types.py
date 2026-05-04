"""
PHASE 18.1 — Portfolio Intelligence Types
==========================================
Contracts for Portfolio Intelligence Layer.

Purpose:
    Define contracts for portfolio-level risk analysis,
    exposure tracking, and concentration monitoring.

Key Questions Answered:
- How much net exposure do we have?
- How much BTC beta exposure?
- How much alt exposure?
- How much factor concentration?
- Is there portfolio overcrowding?
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class PortfolioRiskState(str, Enum):
    """Portfolio risk state classification."""
    BALANCED = "BALANCED"           # concentration < 0.40
    CONCENTRATED = "CONCENTRATED"   # 0.40 - 0.65
    OVERLOADED = "OVERLOADED"       # 0.65 - 0.80
    DEFENSIVE = "DEFENSIVE"         # breadth weak + alt exposure high


class RecommendedAction(str, Enum):
    """Recommended portfolio action."""
    HOLD = "HOLD"                   # Balanced - no action needed
    REDUCE_ALT = "REDUCE_ALT"       # BTC_DOM + high alt exposure
    REDUCE_FACTOR = "REDUCE_FACTOR" # One factor overloaded
    DELEVER = "DELEVER"             # Gross exposure too high
    REBALANCE = "REBALANCE"         # Mixed concentrations


class PositionDirection(str, Enum):
    """Position direction."""
    LONG = "LONG"
    SHORT = "SHORT"


class AssetClass(str, Enum):
    """Asset classification."""
    BTC = "BTC"
    ETH = "ETH"
    ALT = "ALT"


class ClusterType(str, Enum):
    """Portfolio cluster types."""
    BTC_CLUSTER = "btc_cluster"
    ETH_CLUSTER = "eth_cluster"
    MAJORS_CLUSTER = "majors_cluster"
    ALTS_CLUSTER = "alts_cluster"


# ══════════════════════════════════════════════════════════════
# INPUT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class Position:
    """Individual position in the portfolio."""
    symbol: str
    direction: PositionDirection
    position_size: float           # 0-1 normalized
    final_confidence: float        # 0-1
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    pnl_percent: Optional[float] = None
    
    # Factor attribution (if available from Attribution/Factor Governance)
    primary_factor: Optional[str] = None
    secondary_factor: Optional[str] = None
    factor_confidence_modifier: float = 1.0
    factor_capital_modifier: float = 1.0


@dataclass
class MarketContext:
    """Market structure context for portfolio analysis."""
    dominance_regime: str = "BALANCED"     # BTC_DOM, ALT_SEASON, BALANCED
    breadth_state: str = "MIXED"           # STRONG, MIXED, WEAK
    btc_dominance: float = 0.50
    total_market_cap: Optional[float] = None


@dataclass
class PortfolioContext:
    """Full context for portfolio intelligence analysis."""
    positions: List[Position]
    market_context: MarketContext
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

RISK_STATE_MODIFIERS = {
    PortfolioRiskState.BALANCED: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    PortfolioRiskState.CONCENTRATED: {
        "confidence_modifier": 0.95,
        "capital_modifier": 0.90,
    },
    PortfolioRiskState.OVERLOADED: {
        "confidence_modifier": 0.88,
        "capital_modifier": 0.80,
    },
    PortfolioRiskState.DEFENSIVE: {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
}


# ══════════════════════════════════════════════════════════════
# THRESHOLDS
# ══════════════════════════════════════════════════════════════

CONCENTRATION_THRESHOLDS = {
    "balanced_max": 0.40,
    "concentrated_max": 0.65,
    "overloaded_max": 0.80,
}

FACTOR_CONCENTRATION_THRESHOLD = 0.60   # Single factor > 60% = overloaded
CLUSTER_CONCENTRATION_THRESHOLD = 0.70  # Single cluster > 70% = overloaded
GROSS_EXPOSURE_MAX = 2.0                # Max gross exposure


# ══════════════════════════════════════════════════════════════
# MAIN OUTPUT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class PortfolioIntelligenceState:
    """
    Portfolio Intelligence State - Main output contract.
    
    Answers:
    - Net/Gross exposure
    - Asset exposure (BTC, ETH, ALT)
    - Factor exposure
    - Cluster exposure
    - Concentration/Diversification
    - Risk state and recommended action
    - Confidence/Capital modifiers
    """
    # Exposure metrics
    net_exposure: float             # longs - shorts
    gross_exposure: float           # abs(longs) + abs(shorts)
    
    # Asset exposure
    btc_exposure: float
    eth_exposure: float
    alt_exposure: float
    
    # Factor exposure (by factor type)
    factor_exposure: Dict[str, float]
    
    # Cluster exposure
    cluster_exposure: Dict[str, float]
    
    # Concentration metrics
    concentration_score: float      # 0-1
    diversification_score: float    # 1 - concentration_score
    
    # Portfolio state
    portfolio_risk_state: PortfolioRiskState
    recommended_action: RecommendedAction
    
    # Modifiers for trading system
    confidence_modifier: float      # Applied to trade confidence
    capital_modifier: float         # Applied to position sizing
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    position_count: int = 0
    long_count: int = 0
    short_count: int = 0
    
    # Detailed breakdowns
    asset_breakdown: Dict[str, Any] = field(default_factory=dict)
    factor_breakdown: Dict[str, Any] = field(default_factory=dict)
    cluster_breakdown: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "net_exposure": round(self.net_exposure, 4),
            "gross_exposure": round(self.gross_exposure, 4),
            "btc_exposure": round(self.btc_exposure, 4),
            "eth_exposure": round(self.eth_exposure, 4),
            "alt_exposure": round(self.alt_exposure, 4),
            "factor_exposure": {
                k: round(v, 4) for k, v in self.factor_exposure.items()
            },
            "cluster_exposure": {
                k: round(v, 4) for k, v in self.cluster_exposure.items()
            },
            "concentration_score": round(self.concentration_score, 4),
            "diversification_score": round(self.diversification_score, 4),
            "portfolio_risk_state": self.portfolio_risk_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "timestamp": self.timestamp.isoformat(),
            "position_count": self.position_count,
            "long_count": self.long_count,
            "short_count": self.short_count,
        }
    
    def to_full_dict(self) -> Dict:
        """Full dictionary with all breakdowns."""
        result = self.to_dict()
        result["asset_breakdown"] = self.asset_breakdown
        result["factor_breakdown"] = self.factor_breakdown
        result["cluster_breakdown"] = self.cluster_breakdown
        return result
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "net_exposure": round(self.net_exposure, 2),
            "gross_exposure": round(self.gross_exposure, 2),
            "concentration_score": round(self.concentration_score, 2),
            "risk_state": self.portfolio_risk_state.value,
            "action": self.recommended_action.value,
            "confidence_mod": round(self.confidence_modifier, 2),
            "capital_mod": round(self.capital_modifier, 2),
        }


# ══════════════════════════════════════════════════════════════
# BATCH REQUEST/RESPONSE
# ══════════════════════════════════════════════════════════════

@dataclass
class PortfolioIntelligenceBatchRequest:
    """Request for batch portfolio analysis."""
    portfolio_ids: List[str]


@dataclass
class ExposuresResponse:
    """Response for exposures endpoint."""
    net_exposure: float
    gross_exposure: float
    btc_exposure: float
    eth_exposure: float
    alt_exposure: float
    long_exposure: float
    short_exposure: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "net_exposure": round(self.net_exposure, 4),
            "gross_exposure": round(self.gross_exposure, 4),
            "btc_exposure": round(self.btc_exposure, 4),
            "eth_exposure": round(self.eth_exposure, 4),
            "alt_exposure": round(self.alt_exposure, 4),
            "long_exposure": round(self.long_exposure, 4),
            "short_exposure": round(self.short_exposure, 4),
            "timestamp": self.timestamp.isoformat(),
        }
