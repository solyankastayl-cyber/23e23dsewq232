"""
PHASE 6.4 - Edge Discovery Types
=================================
Core data types for edge discovery system.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class EdgeStatus(str, Enum):
    """Edge lifecycle status"""
    CANDIDATE = "CANDIDATE"       # Just discovered
    VALIDATING = "VALIDATING"     # Under validation
    VALIDATED = "VALIDATED"       # Passed all checks
    REJECTED = "REJECTED"         # Failed validation
    PRODUCTION = "PRODUCTION"     # Active in production
    DEPRECATED = "DEPRECATED"     # No longer valid


class EdgeCategory(str, Enum):
    """Categories of discovered edges"""
    VOLATILITY = "VOLATILITY"
    LIQUIDITY = "LIQUIDITY"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    STRUCTURE = "STRUCTURE"
    FUNDING = "FUNDING"
    VOLUME = "VOLUME"
    CORRELATION = "CORRELATION"
    REGIME = "REGIME"
    MICROSTRUCTURE = "MICROSTRUCTURE"


class PatternType(str, Enum):
    """Types of patterns to scan"""
    PRICE_PATTERN = "PRICE_PATTERN"
    VOLUME_ANOMALY = "VOLUME_ANOMALY"
    LIQUIDITY_EVENT = "LIQUIDITY_EVENT"
    VOLATILITY_COMPRESSION = "VOLATILITY_COMPRESSION"
    STRUCTURE_SHIFT = "STRUCTURE_SHIFT"
    FUNDING_EXTREME = "FUNDING_EXTREME"
    ORDERBOOK_IMBALANCE = "ORDERBOOK_IMBALANCE"
    CORRELATION_BREAKDOWN = "CORRELATION_BREAKDOWN"


class ValidationResult(str, Enum):
    """Validation outcome"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"


@dataclass
class MarketFeatures:
    """Extracted market features at a point in time"""
    timestamp: int
    
    # Price features
    trend_strength: float = 0.0
    trend_direction: str = "NEUTRAL"
    volatility_percentile: float = 0.5
    price_momentum: float = 0.0
    
    # Volume features
    volume_spike: float = 1.0
    volume_trend: float = 0.0
    
    # Liquidity features
    liquidity_score: float = 0.5
    spread_percentile: float = 0.5
    orderbook_imbalance: float = 0.0
    
    # Derivatives features
    funding_rate_zscore: float = 0.0
    oi_change_pct: float = 0.0
    
    # Structure features
    near_support: bool = False
    near_resistance: bool = False
    structure_type: str = "RANGE"
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "trend_strength": round(self.trend_strength, 4),
            "trend_direction": self.trend_direction,
            "volatility_percentile": round(self.volatility_percentile, 4),
            "price_momentum": round(self.price_momentum, 4),
            "volume_spike": round(self.volume_spike, 4),
            "volume_trend": round(self.volume_trend, 4),
            "liquidity_score": round(self.liquidity_score, 4),
            "spread_percentile": round(self.spread_percentile, 4),
            "orderbook_imbalance": round(self.orderbook_imbalance, 4),
            "funding_rate_zscore": round(self.funding_rate_zscore, 4),
            "oi_change_pct": round(self.oi_change_pct, 4),
            "near_support": self.near_support,
            "near_resistance": self.near_resistance,
            "structure_type": self.structure_type
        }


@dataclass
class PatternMatch:
    """Detected pattern in market data"""
    pattern_id: str
    pattern_type: PatternType
    timestamp: int
    
    # Pattern details
    features: MarketFeatures
    confidence: float = 0.5
    
    # Outcome (if known from historical data)
    outcome_direction: Optional[str] = None  # LONG, SHORT, NEUTRAL
    outcome_return: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value if isinstance(self.pattern_type, Enum) else self.pattern_type,
            "timestamp": self.timestamp,
            "features": self.features.to_dict(),
            "confidence": round(self.confidence, 4),
            "outcome_direction": self.outcome_direction,
            "outcome_return": round(self.outcome_return, 4) if self.outcome_return else None
        }


@dataclass
class EdgeCandidate:
    """Candidate edge discovered by the system"""
    edge_id: str
    name: str
    description: str
    category: EdgeCategory
    
    # Pattern definition
    pattern_types: List[PatternType]
    feature_conditions: Dict[str, Any]  # Feature name -> condition
    expected_direction: str  # LONG, SHORT
    
    # Sample data
    sample_matches: List[PatternMatch] = field(default_factory=list)
    sample_size: int = 0
    
    # Initial metrics (before validation)
    win_rate_estimate: float = 0.0
    avg_return_estimate: float = 0.0
    
    # Status
    status: EdgeStatus = EdgeStatus.CANDIDATE
    discovered_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "pattern_types": [p.value if isinstance(p, Enum) else p for p in self.pattern_types],
            "feature_conditions": self.feature_conditions,
            "expected_direction": self.expected_direction,
            "sample_size": self.sample_size,
            "win_rate_estimate": round(self.win_rate_estimate, 4),
            "avg_return_estimate": round(self.avg_return_estimate, 4),
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None
        }


@dataclass
class EdgeValidation:
    """Validation results for an edge"""
    edge_id: str
    
    # Hypothesis Engine results
    hypothesis_result: ValidationResult = ValidationResult.PENDING
    hypothesis_win_rate: float = 0.0
    hypothesis_profit_factor: float = 0.0
    
    # Scenario Engine results
    scenario_result: ValidationResult = ValidationResult.PENDING
    scenario_survival_rate: float = 0.0
    scenario_stability_score: float = 0.0
    
    # Monte Carlo results
    monte_carlo_result: ValidationResult = ValidationResult.PENDING
    monte_carlo_profit_prob: float = 0.0
    monte_carlo_risk_score: float = 1.0
    
    # Overall verdict
    overall_result: ValidationResult = ValidationResult.PENDING
    overall_score: float = 0.0
    validation_notes: str = ""
    
    validated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "hypothesis_result": self.hypothesis_result.value if isinstance(self.hypothesis_result, Enum) else self.hypothesis_result,
            "hypothesis_win_rate": round(self.hypothesis_win_rate, 4),
            "hypothesis_profit_factor": round(self.hypothesis_profit_factor, 2),
            "scenario_result": self.scenario_result.value if isinstance(self.scenario_result, Enum) else self.scenario_result,
            "scenario_survival_rate": round(self.scenario_survival_rate, 4),
            "scenario_stability_score": round(self.scenario_stability_score, 3),
            "monte_carlo_result": self.monte_carlo_result.value if isinstance(self.monte_carlo_result, Enum) else self.monte_carlo_result,
            "monte_carlo_profit_prob": round(self.monte_carlo_profit_prob, 4),
            "monte_carlo_risk_score": round(self.monte_carlo_risk_score, 3),
            "overall_result": self.overall_result.value if isinstance(self.overall_result, Enum) else self.overall_result,
            "overall_score": round(self.overall_score, 3),
            "validation_notes": self.validation_notes,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None
        }


@dataclass
class DiscoveredEdge:
    """Fully validated and ranked edge"""
    edge_id: str
    name: str
    description: str
    category: EdgeCategory
    
    # Edge definition
    pattern_types: List[PatternType]
    feature_conditions: Dict[str, Any]
    expected_direction: str
    
    # Validated metrics
    win_rate: float
    profit_factor: float
    expectancy: float
    sharpe_ratio: float
    
    # Risk metrics
    max_drawdown: float
    risk_of_ruin: float
    risk_score: float
    
    # Confidence
    confidence_score: float
    sample_size: int
    
    # Ranking
    rank: int = 0
    composite_score: float = 0.0
    
    # Validation
    validation: Optional[EdgeValidation] = None
    
    # Status and timing
    status: EdgeStatus = EdgeStatus.VALIDATED
    discovered_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "pattern_types": [p.value if isinstance(p, Enum) else p for p in self.pattern_types],
            "feature_conditions": self.feature_conditions,
            "expected_direction": self.expected_direction,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "max_drawdown": round(self.max_drawdown, 4),
            "risk_of_ruin": round(self.risk_of_ruin, 4),
            "risk_score": round(self.risk_score, 3),
            "confidence_score": round(self.confidence_score, 3),
            "sample_size": self.sample_size,
            "rank": self.rank,
            "composite_score": round(self.composite_score, 3),
            "validation": self.validation.to_dict() if self.validation else None,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None
        }


# Validation thresholds
VALIDATION_THRESHOLDS = {
    "hypothesis": {
        "min_win_rate": 0.52,
        "min_profit_factor": 1.2,
        "min_sample_size": 30
    },
    "scenario": {
        "min_survival_rate": 0.7,
        "min_stability_score": 0.5
    },
    "monte_carlo": {
        "min_profit_prob": 0.55,
        "max_risk_score": 0.5
    },
    "overall": {
        "min_score": 0.6
    }
}
