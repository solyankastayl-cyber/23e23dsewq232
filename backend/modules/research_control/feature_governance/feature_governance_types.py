"""
PHASE 17.1 — Feature Governance Types
======================================
Contracts for Feature Governance Engine.

Purpose:
    Define governance evaluation contracts for features.
    Feature Governance evaluates quality across 5 dimensions.

Key Principle:
    Feature Governance creates control signals, does NOT block system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# GOVERNANCE STATE ENUM
# ══════════════════════════════════════════════════════════════

class GovernanceState(str, Enum):
    """Feature governance state classification."""
    HEALTHY = "HEALTHY"       # Feature is performing well
    WATCHLIST = "WATCHLIST"   # Feature needs monitoring
    DEGRADED = "DEGRADED"     # Feature is degrading
    RETIRE = "RETIRE"         # Feature should be retired


class GovernanceDimension(str, Enum):
    """Governance evaluation dimensions."""
    STABILITY = "stability"
    DRIFT = "drift"
    COVERAGE = "coverage"
    REDUNDANCY = "redundancy"
    UTILITY = "utility"


# ══════════════════════════════════════════════════════════════
# GOVERNANCE THRESHOLDS
# ══════════════════════════════════════════════════════════════

GOVERNANCE_THRESHOLDS = {
    "healthy_min": 0.80,     # score > 0.80 = HEALTHY
    "watchlist_min": 0.65,   # score > 0.65 = WATCHLIST
    "degraded_min": 0.45,    # score > 0.45 = DEGRADED
    # score <= 0.45 = RETIRE
}


# ══════════════════════════════════════════════════════════════
# GOVERNANCE WEIGHTS
# ══════════════════════════════════════════════════════════════

GOVERNANCE_WEIGHTS = {
    "stability": 0.25,
    "drift": 0.20,
    "coverage": 0.15,
    "redundancy": 0.15,
    "utility": 0.25,
}


# ══════════════════════════════════════════════════════════════
# GOVERNANCE MODIFIERS BY STATE
# ══════════════════════════════════════════════════════════════

GOVERNANCE_MODIFIERS = {
    GovernanceState.HEALTHY: {
        "confidence_modifier": 1.00,
        "size_modifier": 1.00,
    },
    GovernanceState.WATCHLIST: {
        "confidence_modifier": 0.95,
        "size_modifier": 0.95,
    },
    GovernanceState.DEGRADED: {
        "confidence_modifier": 0.85,
        "size_modifier": 0.85,
    },
    GovernanceState.RETIRE: {
        "confidence_modifier": 0.70,
        "size_modifier": 0.70,
    },
}


# ══════════════════════════════════════════════════════════════
# DIMENSION INPUT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class StabilityInput:
    """Input for stability evaluation."""
    values_history: List[float]  # Historical values
    lookback_periods: int = 30
    
    def to_dict(self) -> Dict:
        return {
            "values_count": len(self.values_history),
            "lookback_periods": self.lookback_periods,
        }


@dataclass
class DriftInput:
    """Input for drift evaluation."""
    current_distribution: Dict[str, float]  # mean, std, min, max
    baseline_distribution: Dict[str, float]
    
    def to_dict(self) -> Dict:
        return {
            "current": self.current_distribution,
            "baseline": self.baseline_distribution,
        }


@dataclass
class CoverageInput:
    """Input for coverage evaluation."""
    total_observations: int
    valid_observations: int
    null_rate: float
    
    def to_dict(self) -> Dict:
        return {
            "total_observations": self.total_observations,
            "valid_observations": self.valid_observations,
            "null_rate": round(self.null_rate, 4),
            "coverage_rate": round(1 - self.null_rate, 4),
        }


@dataclass
class RedundancyInput:
    """Input for redundancy evaluation."""
    correlation_scores: Dict[str, float]  # feature_name -> correlation
    max_correlation: float
    most_correlated_feature: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "max_correlation": round(self.max_correlation, 4),
            "most_correlated_feature": self.most_correlated_feature,
            "correlation_count": len(self.correlation_scores),
        }


@dataclass
class UtilityInput:
    """Input for predictive utility evaluation."""
    information_ratio: float
    signal_to_noise: float
    predictive_power: float  # e.g., IC (information coefficient)
    
    def to_dict(self) -> Dict:
        return {
            "information_ratio": round(self.information_ratio, 4),
            "signal_to_noise": round(self.signal_to_noise, 4),
            "predictive_power": round(self.predictive_power, 4),
        }


# ══════════════════════════════════════════════════════════════
# DIMENSION RESULT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class DimensionResult:
    """Result from a single dimension evaluation."""
    dimension: GovernanceDimension
    score: float  # 0..1
    status: str   # GOOD / WARNING / POOR
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 4),
            "status": self.status,
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# FEATURE GOVERNANCE STATE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class FeatureGovernanceState:
    """
    Output from Feature Governance Engine.
    
    Evaluates feature quality across 5 dimensions:
    - Stability: How stable is the feature over time
    - Drift: Has distribution drifted from baseline
    - Coverage: How often is feature available/valid
    - Redundancy: Does feature duplicate others
    - Utility: Does feature provide signal value
    
    Key Principle:
        Feature Governance creates control signals.
        It does NOT block the system directly.
    """
    feature_name: str
    timestamp: datetime
    
    # Dimension scores (0..1)
    stability_score: float
    drift_score: float
    coverage_score: float
    redundancy_score: float
    utility_score: float
    
    # Aggregated governance
    governance_score: float  # 0..1
    governance_state: GovernanceState
    
    # Modifiers for downstream use
    confidence_modifier: float  # 0.70 to 1.00
    size_modifier: float        # 0.70 to 1.00
    
    # Dimension analysis
    weakest_dimension: GovernanceDimension
    strongest_dimension: GovernanceDimension
    
    # Detailed results
    dimension_results: List[DimensionResult] = field(default_factory=list)
    
    # Metadata
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "feature_name": self.feature_name,
            "timestamp": self.timestamp.isoformat(),
            "stability_score": round(self.stability_score, 4),
            "drift_score": round(self.drift_score, 4),
            "coverage_score": round(self.coverage_score, 4),
            "redundancy_score": round(self.redundancy_score, 4),
            "utility_score": round(self.utility_score, 4),
            "governance_score": round(self.governance_score, 4),
            "governance_state": self.governance_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "weakest_dimension": self.weakest_dimension.value,
            "strongest_dimension": self.strongest_dimension.value,
            "dimension_results": [r.to_dict() for r in self.dimension_results],
            "drivers": self.drivers,
        }
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "feature_name": self.feature_name,
            "governance_score": round(self.governance_score, 4),
            "governance_state": self.governance_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "weakest_dimension": self.weakest_dimension.value,
            "strongest_dimension": self.strongest_dimension.value,
        }


# ══════════════════════════════════════════════════════════════
# BATCH REQUEST/RESPONSE
# ══════════════════════════════════════════════════════════════

@dataclass
class BatchGovernanceRequest:
    """Request for batch governance evaluation."""
    feature_names: List[str]


@dataclass  
class BatchGovernanceResponse:
    """Response from batch governance evaluation."""
    results: Dict[str, FeatureGovernanceState]
    summary: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "results": {k: v.to_summary() for k, v in self.results.items()},
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }
