"""
System Control Types

PHASE 33 — System Control Layer Types

Types for decision engine, risk control, and alerts.
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Market States
MarketStateType = Literal[
    "TRENDING",
    "BREAKOUT_SETUP",
    "MEAN_REVERSION",
    "VOLATILITY_EXPANSION",
    "HIGH_RISK",
    "NO_EDGE",
]

MARKET_STATES = [
    "TRENDING",
    "BREAKOUT_SETUP",
    "MEAN_REVERSION",
    "VOLATILITY_EXPANSION",
    "HIGH_RISK",
    "NO_EDGE",
]

# Risk Levels
RiskLevelType = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]

RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "EXTREME"]

# Alert Types
AlertType = Literal[
    "MARKET_SHIFT",
    "LIQUIDITY_EVENT",
    "CASCADE_RISK",
    "SCENARIO_CHANGE",
    "RISK_ALERT",
    "OPPORTUNITY",
]

ALERT_TYPES = [
    "MARKET_SHIFT",
    "LIQUIDITY_EVENT",
    "CASCADE_RISK",
    "SCENARIO_CHANGE",
    "RISK_ALERT",
    "OPPORTUNITY",
]

# Alert Severity
SeverityType = Literal["INFO", "WARNING", "CRITICAL"]

# Direction
DirectionType = Literal["LONG", "SHORT", "NEUTRAL"]

# Strategy Types
StrategyType = Literal[
    "breakout_trading",
    "trend_following",
    "mean_reversion",
    "volatility_trading",
    "risk_off",
    "no_action",
]


# ══════════════════════════════════════════════════════════════
# Market Decision State
# ══════════════════════════════════════════════════════════════

class MarketDecisionState(BaseModel):
    """
    Main decision output from the system.
    
    Aggregates all intelligence layers into actionable state.
    """
    symbol: str
    
    # Market analysis
    market_state: MarketStateType = "NO_EDGE"
    dominant_scenario: str = "UNKNOWN"
    dominant_direction: DirectionType = "NEUTRAL"
    
    # Recommendation
    recommended_strategy: StrategyType = "no_action"
    recommended_direction: DirectionType = "NEUTRAL"
    
    # Confidence and risk
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_level: RiskLevelType = "MEDIUM"
    
    # Supporting data
    hypothesis_type: str = "UNKNOWN"
    top_scenario_type: str = "UNKNOWN"
    top_scenario_probability: float = 0.0
    
    # Intelligence scores
    alpha_score: float = 0.0
    regime_score: float = 0.0
    microstructure_score: float = 0.0
    similarity_score: float = 0.0
    cross_asset_score: float = 0.0
    
    # Metadata
    reasoning: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Risk State
# ══════════════════════════════════════════════════════════════

class RiskState(BaseModel):
    """
    System risk assessment.
    """
    symbol: str
    
    # Risk level
    risk_level: RiskLevelType = "MEDIUM"
    risk_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Exposure
    exposure_long: float = 0.0
    exposure_short: float = 0.0
    net_exposure: float = 0.0
    
    # Limits
    max_allowed_position: float = 1.0
    current_utilization: float = 0.0
    
    # Stress indicators
    stress_indicator: float = Field(default=0.0, ge=0.0, le=1.0)
    liquidation_pressure: float = 0.0
    cascade_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Volatility
    expected_volatility: float = 0.0
    volatility_regime: str = "NORMAL"
    
    # Reasoning
    risk_factors: List[str] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Alert
# ══════════════════════════════════════════════════════════════

class Alert(BaseModel):
    """
    System alert notification.
    """
    alert_id: str
    symbol: str
    
    # Alert classification
    alert_type: AlertType
    severity: SeverityType = "INFO"
    
    # Content
    title: str
    message: str
    
    # Context
    trigger_value: float = 0.0
    threshold_value: float = 0.0
    
    # State
    acknowledged: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Cockpit State
# ══════════════════════════════════════════════════════════════

class CockpitState(BaseModel):
    """
    Aggregated UI state for decision cockpit.
    
    Complete system state for display.
    """
    symbol: str
    
    # Core states
    decision_state: MarketDecisionState
    risk_state: RiskState
    
    # Intelligence summary
    top_hypothesis: str = "UNKNOWN"
    top_scenario: str = "UNKNOWN"
    
    # Allocation
    capital_allocation: Dict[str, float] = Field(default_factory=dict)
    
    # Active alerts
    alerts: List[Alert] = Field(default_factory=list)
    active_alert_count: int = 0
    
    # System health
    system_status: str = "OPERATIONAL"
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Control Summary
# ══════════════════════════════════════════════════════════════

class ControlSummary(BaseModel):
    """
    Summary of control state across all symbols.
    """
    symbols_monitored: List[str] = Field(default_factory=list)
    
    # Aggregated stats
    total_alerts: int = 0
    critical_alerts: int = 0
    
    # Risk overview
    high_risk_symbols: List[str] = Field(default_factory=list)
    extreme_risk_symbols: List[str] = Field(default_factory=list)
    
    # Opportunity overview
    opportunity_symbols: List[str] = Field(default_factory=list)
    
    # System status
    system_status: str = "OPERATIONAL"
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
