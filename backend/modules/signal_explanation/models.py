"""
Signal Explanation Models — PHASE 51
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class DriverType(str, Enum):
    """Signal driver types."""
    ALPHA = "alpha"
    REGIME = "regime"
    MICROSTRUCTURE = "microstructure"
    CAPITAL_FLOW = "capital_flow"
    FRACTAL = "fractal"
    TECHNICAL = "technical"
    REFLEXIVITY = "reflexivity"
    CROSS_ASSET = "cross_asset"
    MEMORY = "memory"


class ConflictSeverity(str, Enum):
    """Conflict severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SignalDriver(BaseModel):
    """Individual signal driver."""
    driver_type: DriverType
    name: str
    contribution: float  # -1 to 1
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SignalConflict(BaseModel):
    """Conflicting signal factor."""
    name: str
    severity: ConflictSeverity
    description: str
    impact: float  # Negative impact on confidence
    resolution: Optional[str] = None


class ConfidenceBreakdown(BaseModel):
    """Confidence score breakdown by layer."""
    
    # Intelligence layers
    alpha_contribution: float = 0.0
    regime_contribution: float = 0.0
    microstructure_contribution: float = 0.0
    capital_flow_contribution: float = 0.0
    fractal_market_contribution: float = 0.0
    fractal_similarity_contribution: float = 0.0
    cross_asset_contribution: float = 0.0
    memory_contribution: float = 0.0
    reflexivity_contribution: float = 0.0
    
    # Weights used
    weights: Dict[str, float] = Field(default_factory=dict)
    
    def total(self) -> float:
        """Calculate total confidence."""
        return (
            self.alpha_contribution +
            self.regime_contribution +
            self.microstructure_contribution +
            self.capital_flow_contribution +
            self.fractal_market_contribution +
            self.fractal_similarity_contribution +
            self.cross_asset_contribution +
            self.memory_contribution +
            self.reflexivity_contribution
        )


class SignalExplanation(BaseModel):
    """Complete signal explanation."""
    
    # Identity
    signal_id: str
    hypothesis_id: Optional[str] = None
    
    # Context
    symbol: str
    timeframe: str
    timestamp: datetime
    
    # Signal
    direction: str  # bullish, bearish, neutral
    confidence: float
    strength: str  # weak, moderate, strong, very_strong
    
    # Summary
    summary: str
    narrative: str  # Human-readable explanation
    
    # Drivers
    drivers: List[SignalDriver] = Field(default_factory=list)
    supporting_factors: List[str] = Field(default_factory=list)
    conflicting_factors: List[str] = Field(default_factory=list)
    
    # Confidence breakdown
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    
    # Conflicts
    conflicts: List[SignalConflict] = Field(default_factory=list)
    
    # Risk factors
    risk_factors: List[str] = Field(default_factory=list)
    
    # Chart highlights (objects to emphasize)
    chart_highlights: List[str] = Field(default_factory=list)
    
    # Meta-alpha context
    meta_alpha: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetaAlphaExplanation(BaseModel):
    """Explanation for meta-alpha selection."""
    
    active_alpha_family: str
    reason: str
    
    # Performance metrics
    success_rate: float
    avg_pnl: float
    regime_fit: float
    
    # Comparison with others
    comparison: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Rotation history
    last_rotation: Optional[datetime] = None
    rotation_reason: Optional[str] = None
