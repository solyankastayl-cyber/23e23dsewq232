"""
Market Simulation Types

PHASE 32.3 — Market Simulation Engine Types

Types for forward-looking scenario generation.
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Scenario types
SCENARIO_TYPES = [
    "BREAKOUT_CONTINUATION",
    "MEAN_REVERSION",
    "TREND_ACCELERATION",
    "VOLATILITY_EXPANSION",
    "LIQUIDATION_EVENT",
]

ScenarioType = Literal[
    "BREAKOUT_CONTINUATION",
    "MEAN_REVERSION",
    "TREND_ACCELERATION",
    "VOLATILITY_EXPANSION",
    "LIQUIDATION_EVENT",
]

# Direction types
DirectionType = Literal["LONG", "SHORT", "NEUTRAL"]

# Horizons in minutes
SIMULATION_HORIZONS = [15, 60, 240]

# Probability weights
WEIGHT_HYPOTHESIS = 0.35
WEIGHT_REGIME = 0.20
WEIGHT_MICROSTRUCTURE = 0.15
WEIGHT_FRACTAL_SIMILARITY = 0.15
WEIGHT_META_ALPHA = 0.15

# Regime multipliers for expected move
REGIME_MULTIPLIERS = {
    "TREND_UP": 1.3,
    "TREND_DOWN": 1.3,
    "RANGE": 0.7,
    "COMPRESSION": 0.5,
    "EXPANSION": 1.5,
    "UNKNOWN": 1.0,
}

# Microstructure multipliers
MICROSTRUCTURE_MULTIPLIERS = {
    "SUPPORTIVE": 1.2,
    "NEUTRAL": 1.0,
    "FRAGILE": 0.8,
    "STRESSED": 1.4,  # High volatility expected
}

# Scenario base probabilities
SCENARIO_BASE_PROBABILITIES = {
    "BREAKOUT_CONTINUATION": 0.30,
    "MEAN_REVERSION": 0.25,
    "TREND_ACCELERATION": 0.20,
    "VOLATILITY_EXPANSION": 0.15,
    "LIQUIDATION_EVENT": 0.10,
}


# ══════════════════════════════════════════════════════════════
# Market Scenario
# ══════════════════════════════════════════════════════════════

class MarketScenario(BaseModel):
    """
    Single market scenario prediction.
    """
    scenario_id: str
    symbol: str
    scenario_type: ScenarioType
    
    # Probability and confidence
    probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Direction and expected move
    expected_direction: DirectionType = "NEUTRAL"
    expected_move_percent: float = Field(default=0.0)
    
    # Time horizon
    horizon_minutes: int = Field(default=60)
    
    # Component scores
    hypothesis_score: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_score: float = Field(default=0.0, ge=0.0, le=1.0)
    microstructure_score: float = Field(default=0.0, ge=0.0, le=1.0)
    fractal_similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    meta_alpha_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Metadata
    reasoning: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Simulation Input
# ══════════════════════════════════════════════════════════════

class SimulationInput(BaseModel):
    """
    Input data for scenario simulation.
    """
    symbol: str
    
    # From Hypothesis Engine
    hypothesis_type: str = "UNKNOWN"
    hypothesis_direction: str = "NEUTRAL"
    hypothesis_confidence: float = 0.5
    
    # From Regime Intelligence
    regime_type: str = "UNKNOWN"
    regime_confidence: float = 0.5
    transition_state: str = "STABLE"
    
    # From Microstructure
    microstructure_state: str = "NEUTRAL"
    microstructure_confidence: float = 0.5
    liquidation_pressure: float = 0.0
    
    # From Fractal Similarity
    similarity_direction: str = "NEUTRAL"
    similarity_confidence: float = 0.5
    similarity_modifier: float = 1.0
    
    # From Meta Alpha
    meta_alpha_pattern: str = "NONE"
    meta_alpha_score: float = 0.5
    
    # Market data
    current_price: float = 0.0
    atr_percent: float = 2.0  # Average True Range as percent
    volatility_24h: float = 0.0


# ══════════════════════════════════════════════════════════════
# Simulation Result
# ══════════════════════════════════════════════════════════════

class SimulationResult(BaseModel):
    """
    Complete simulation result with multiple scenarios.
    """
    symbol: str
    
    # All scenarios (sorted by probability)
    scenarios: List[MarketScenario] = Field(default_factory=list)
    
    # Top scenario
    top_scenario: Optional[MarketScenario] = None
    
    # Aggregated metrics
    dominant_direction: DirectionType = "NEUTRAL"
    direction_confidence: float = 0.0
    expected_volatility: float = 0.0
    
    # Input data snapshot
    input_data: Optional[SimulationInput] = None
    
    # Metadata
    scenarios_generated: int = 0
    horizon_minutes: int = 60
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Scenario Modifier (for Capital Allocation)
# ══════════════════════════════════════════════════════════════

class ScenarioModifier(BaseModel):
    """
    Modifier for capital allocation based on scenario analysis.
    """
    symbol: str
    
    # Current allocation modifier
    allocation_modifier: float = Field(default=1.0, ge=0.5, le=1.5)
    
    # Top scenario info
    top_scenario_type: str = "UNKNOWN"
    top_scenario_probability: float = 0.0
    
    # Risk assessment
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    liquidation_risk: float = 0.0
    
    # Reasoning
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Simulation Summary
# ══════════════════════════════════════════════════════════════

class SimulationSummary(BaseModel):
    """
    Summary of simulation results for a symbol.
    """
    symbol: str
    
    # Current state
    current_top_scenario: str = "UNKNOWN"
    current_probability: float = 0.0
    current_direction: DirectionType = "NEUTRAL"
    
    # Historical stats
    total_simulations: int = 0
    avg_top_probability: float = 0.0
    scenario_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Accuracy tracking (if outcomes recorded)
    accuracy_rate: float = 0.0
    
    last_updated: Optional[datetime] = None
