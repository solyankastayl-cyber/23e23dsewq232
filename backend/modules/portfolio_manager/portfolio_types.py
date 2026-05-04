"""
Portfolio Manager Types

PHASE 38 — Portfolio Manager (Updated with Markowitz)

Types for multi-asset portfolio management.

Key constraints:
- max_long_exposure: 70%
- max_short_exposure: 70%
- max_single_position: 10%

Risk model:
- Portfolio variance: wᵀΣw (Markowitz)
- Correlation penalty: position_weight × (1 - avg_correlation)
- Rebalance trigger: |current_weight - target_weight| > 3%

Pipeline:
hypothesis → portfolio targets → portfolio manager → execution brain
"""

from typing import Literal, Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Exposure limits
EXPOSURE_LIMITS = {
    "MAX_LONG": 0.70,      # 70% max long exposure
    "MAX_SHORT": 0.70,     # 70% max short exposure
    "MAX_TOTAL": 1.00,     # 100% max total exposure
}

# Position limits
MAX_SINGLE_POSITION = 0.10  # 10% max single position

# Risk thresholds (as % of capital)
RISK_THRESHOLDS = {
    "LOW": 0.10,           # < 10%
    "MEDIUM": 0.20,        # 10-20%
    "HIGH": 0.30,          # 20-30%
    "CRITICAL": 0.40,      # > 30%
}

# Correlation penalty
CORRELATION_PENALTY_THRESHOLD = 0.70  # Start penalizing above 70% correlation
MAX_CORRELATION_PENALTY = 0.40  # Max 40% reduction

# Rebalance trigger
REBALANCE_THRESHOLD = 0.03  # 3% deviation triggers rebalance


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

DirectionType = Literal["LONG", "SHORT"]

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

PositionStatus = Literal["ACTIVE", "PENDING", "CLOSED"]


# ══════════════════════════════════════════════════════════════
# Portfolio Target (NEW - User requirement 1️⃣)
# ══════════════════════════════════════════════════════════════

class PortfolioTarget(BaseModel):
    """
    Target allocation for an asset.
    
    Pipeline: hypothesis → portfolio targets → portfolio manager → execution brain
    """
    symbol: str
    target_weight: float = Field(ge=0, le=1)  # Target % of portfolio
    direction: DirectionType
    confidence: float = Field(ge=0, le=1)  # From hypothesis
    
    # Source tracking
    source_hypothesis_id: Optional[str] = None
    
    # Priority for capital rotation
    priority: int = Field(default=0, ge=0)
    
    # Timestamps
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Portfolio Position
# ══════════════════════════════════════════════════════════════

class PortfolioPosition(BaseModel):
    """
    Single position in portfolio.
    """
    symbol: str
    direction: DirectionType
    
    # Size
    size_usd: float = Field(ge=0)
    size_percent: float = Field(ge=0, le=1)  # % of portfolio
    
    # Prices
    entry_price: float = Field(gt=0)
    current_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    
    # P&L
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_percent: float = 0.0
    
    # Risk
    risk_contribution: float = Field(ge=0, le=1, default=0.0)  # Contribution to total risk
    max_loss_usd: float = 0.0  # Size * (entry - stop) / entry
    
    # Correlation info
    correlation_penalty: float = Field(ge=0, le=1, default=0.0)
    correlated_with: List[str] = Field(default_factory=list)
    
    # Status
    status: PositionStatus = "ACTIVE"
    
    # Timestamps
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Exposure State
# ══════════════════════════════════════════════════════════════

class ExposureState(BaseModel):
    """
    Current portfolio exposure.
    """
    # Directional exposure
    long_exposure: float = Field(ge=0, le=1, default=0.0)
    short_exposure: float = Field(ge=0, le=1, default=0.0)
    net_exposure: float = Field(ge=-1, le=1, default=0.0)  # Long - short
    gross_exposure: float = Field(ge=0, le=2, default=0.0)  # Long + short
    
    # Exposure by asset
    exposure_by_symbol: Dict[str, float] = Field(default_factory=dict)
    
    # Limits check
    long_within_limit: bool = True
    short_within_limit: bool = True
    total_within_limit: bool = True
    
    # Available capacity
    available_long_capacity: float = 0.70
    available_short_capacity: float = 0.70


# ══════════════════════════════════════════════════════════════
# Portfolio Risk (Updated with Markowitz)
# ══════════════════════════════════════════════════════════════

class PortfolioRisk(BaseModel):
    """
    Portfolio risk metrics using Markowitz model.
    
    portfolio_variance = wᵀΣw
    where:
    - w = weight vector
    - Σ = covariance matrix
    """
    # Markowitz risk
    portfolio_variance: float = Field(ge=0, default=0.0)  # wᵀΣw
    portfolio_volatility: float = Field(ge=0, default=0.0)  # √variance
    
    # Total risk as % of capital (normalized)
    portfolio_risk: float = Field(ge=0, le=1, default=0.0)
    
    # Risk level classification
    risk_level: RiskLevel = "LOW"
    
    # Risk by position
    risk_by_symbol: Dict[str, float] = Field(default_factory=dict)
    risk_contribution_by_symbol: Dict[str, float] = Field(default_factory=dict)
    
    # Max drawdown potential
    max_drawdown_usd: float = 0.0
    max_drawdown_percent: float = 0.0
    
    # Concentration risk (Herfindahl index)
    concentration_risk: float = 0.0
    
    # Correlation risk (portfolio correlation component)
    correlation_risk: float = 0.0
    
    # VaR estimates (optional)
    var_95_percent: float = 0.0  # 95% VaR
    var_99_percent: float = 0.0  # 99% VaR


# ══════════════════════════════════════════════════════════════
# Correlation Matrix
# ══════════════════════════════════════════════════════════════

class CorrelationMatrix(BaseModel):
    """
    Asset correlation matrix for portfolio risk calculation.
    
    Used for:
    - Portfolio variance: wᵀΣw
    - Correlation penalty: position_weight × (1 - avg_correlation)
    """
    symbols: List[str] = Field(default_factory=list)
    matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Covariance matrix (for Markowitz)
    covariance_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Volatilities (std dev of returns)
    volatilities: Dict[str, float] = Field(default_factory=dict)
    
    # High correlation pairs
    high_correlation_pairs: List[tuple] = Field(default_factory=list)
    
    # Average correlation
    avg_correlation: float = 0.0
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Portfolio State (Updated with Markowitz)
# ══════════════════════════════════════════════════════════════

class PortfolioState(BaseModel):
    """
    Complete portfolio state.
    
    Main contract for PHASE 38.
    
    Risk model uses Markowitz:
    - portfolio_variance = wᵀΣw
    - portfolio_volatility = √(portfolio_variance)
    """
    # Capital
    total_capital: float = Field(ge=0)
    available_capital: float = Field(ge=0)
    allocated_capital: float = Field(ge=0)
    
    # Positions (current)
    positions: List[PortfolioPosition] = Field(default_factory=list)
    position_count: int = 0
    
    # Target positions (from hypothesis)
    target_positions: List[PortfolioTarget] = Field(default_factory=list)
    
    # Exposure
    long_exposure: float = Field(ge=0, le=1, default=0.0)
    short_exposure: float = Field(ge=0, le=1, default=0.0)
    net_exposure: float = Field(ge=-1, le=1, default=0.0)
    gross_exposure: float = Field(ge=0, le=2, default=0.0)
    
    # Risk - Markowitz model
    portfolio_variance: float = Field(ge=0, default=0.0)  # wᵀΣw
    portfolio_volatility: float = Field(ge=0, default=0.0)  # √variance
    portfolio_risk: float = Field(ge=0, le=1, default=0.0)  # Normalized risk
    risk_level: RiskLevel = "LOW"
    
    # Diversification
    diversification_score: float = Field(ge=0, le=1, default=0.0)
    
    # P&L
    total_unrealized_pnl_usd: float = 0.0
    total_unrealized_pnl_percent: float = 0.0
    
    # Correlation
    avg_correlation: float = 0.0
    correlation_penalty_applied: float = 0.0
    
    # Rebalance
    rebalance_required: bool = False
    max_weight_deviation: float = 0.0  # Max |current - target|
    
    # Health
    is_healthy: bool = True
    warnings: List[str] = Field(default_factory=list)
    
    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Rebalance Result
# ══════════════════════════════════════════════════════════════

class RebalanceResult(BaseModel):
    """
    Result of portfolio rebalance operation.
    
    Rebalance triggers when:
    - |current_weight - target_weight| > 3%
    - Exposure limits exceeded
    - Risk level CRITICAL
    """
    rebalance_triggered: bool = False
    reason: str = ""
    
    # Weight deviations
    weight_deviations: Dict[str, float] = Field(default_factory=dict)
    max_deviation: float = 0.0
    
    # Positions to adjust
    positions_to_reduce: List[Dict] = Field(default_factory=list)
    positions_to_increase: List[Dict] = Field(default_factory=list)
    positions_to_close: List[str] = Field(default_factory=list)
    positions_to_open: List[Dict] = Field(default_factory=list)
    
    # New allocations
    new_allocations: Dict[str, float] = Field(default_factory=dict)
    
    # Capital impact
    capital_freed: float = 0.0
    capital_required: float = 0.0
    
    # Risk impact
    risk_before: float = 0.0
    risk_after: float = 0.0
    variance_before: float = 0.0
    variance_after: float = 0.0
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Position Request
# ══════════════════════════════════════════════════════════════

class PositionRequest(BaseModel):
    """
    Request to add a new position.
    """
    symbol: str
    direction: DirectionType
    size_usd: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)


# ══════════════════════════════════════════════════════════════
# Capital Rotation Request
# ══════════════════════════════════════════════════════════════

class CapitalRotationRequest(BaseModel):
    """
    Request to rotate capital based on targets.
    """
    targets: List[PortfolioTarget]
    consider_correlation: bool = True
    consider_risk_contribution: bool = True


# ══════════════════════════════════════════════════════════════
# Portfolio History Entry
# ══════════════════════════════════════════════════════════════

class PortfolioHistoryEntry(BaseModel):
    """
    Historical snapshot of portfolio for performance analysis.
    """
    total_capital: float
    allocated_capital: float
    position_count: int
    
    long_exposure: float
    short_exposure: float
    net_exposure: float
    
    portfolio_variance: float
    portfolio_volatility: float
    portfolio_risk: float
    risk_level: RiskLevel
    
    total_pnl_usd: float
    total_pnl_percent: float
    
    diversification_score: float
    avg_correlation: float
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
