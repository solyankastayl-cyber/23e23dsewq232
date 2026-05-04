"""
Dynamic Risk Types
==================

Core types for PHASE 3.3 Dynamic Risk Engine
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class RiskLevel(str, Enum):
    """Risk level classification"""
    MINIMAL = "MINIMAL"       # 0.25x base - Very conservative
    REDUCED = "REDUCED"       # 0.5x base - Conservative
    NORMAL = "NORMAL"         # 1.0x base - Standard
    ELEVATED = "ELEVATED"     # 1.25x base - Aggressive (only A+ quality)
    MAXIMUM = "MAXIMUM"       # 1.5x base - Maximum (exceptional setup)


class ExposureType(str, Enum):
    """Types of exposure limits"""
    SINGLE_TRADE = "SINGLE_TRADE"
    STRATEGY = "STRATEGY"
    ASSET = "ASSET"
    REGIME = "REGIME"
    DIRECTION = "DIRECTION"
    PORTFOLIO = "PORTFOLIO"


class BudgetStatus(str, Enum):
    """Risk budget status"""
    AVAILABLE = "AVAILABLE"     # Under 50% used
    LIMITED = "LIMITED"         # 50-80% used
    RESTRICTED = "RESTRICTED"   # 80-95% used
    EXHAUSTED = "EXHAUSTED"     # 95-100% used
    EXCEEDED = "EXCEEDED"       # Over 100%


# ===========================================
# Risk Multipliers
# ===========================================

@dataclass
class QualityMultiplier:
    """Multiplier based on quality grade"""
    grade: str = "B"
    multiplier: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "grade": self.grade,
            "multiplier": round(self.multiplier, 2),
            "reason": self.reason
        }


@dataclass
class HealthMultiplier:
    """Multiplier based on health status"""
    status: str = "GOOD"
    health_score: float = 70.0
    multiplier: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "healthScore": round(self.health_score, 1),
            "multiplier": round(self.multiplier, 2),
            "reason": self.reason
        }


@dataclass
class RegimeMultiplier:
    """Multiplier based on market regime"""
    regime: str = "TRENDING"
    stability: float = 0.8
    multiplier: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "stability": round(self.stability, 2),
            "multiplier": round(self.multiplier, 2),
            "reason": self.reason
        }


@dataclass
class ConfidenceMultiplier:
    """Multiplier based on signal confidence"""
    confidence: float = 0.7
    multiplier: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": round(self.confidence, 2),
            "multiplier": round(self.multiplier, 2),
            "reason": self.reason
        }


@dataclass
class CorrelationMultiplier:
    """Multiplier based on portfolio correlation"""
    correlation_score: float = 0.3
    multiplier: float = 1.0
    correlated_positions: List[str] = field(default_factory=list)
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlationScore": round(self.correlation_score, 2),
            "multiplier": round(self.multiplier, 2),
            "correlatedPositions": self.correlated_positions,
            "reason": self.reason
        }


# ===========================================
# Risk Calculation Result
# ===========================================

@dataclass
class RiskCalculation:
    """Complete risk calculation result"""
    position_id: str = ""
    symbol: str = ""
    strategy: str = ""
    direction: str = ""
    
    # Base risk
    base_risk_pct: float = 1.0
    
    # Multipliers
    quality_multiplier: QualityMultiplier = field(default_factory=QualityMultiplier)
    health_multiplier: HealthMultiplier = field(default_factory=HealthMultiplier)
    regime_multiplier: RegimeMultiplier = field(default_factory=RegimeMultiplier)
    confidence_multiplier: ConfidenceMultiplier = field(default_factory=ConfidenceMultiplier)
    correlation_multiplier: CorrelationMultiplier = field(default_factory=CorrelationMultiplier)
    
    # Combined multiplier
    combined_multiplier: float = 1.0
    
    # Final risk
    adjusted_risk_pct: float = 1.0
    risk_level: RiskLevel = RiskLevel.NORMAL
    
    # Position sizing
    recommended_position_pct: float = 0.0
    max_position_pct: float = 0.0
    
    # Constraints applied
    constraints_applied: List[str] = field(default_factory=list)
    
    # Budget impact
    budget_before: float = 0.0
    budget_after: float = 0.0
    budget_status: BudgetStatus = BudgetStatus.AVAILABLE
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "direction": self.direction,
            "risk": {
                "base": round(self.base_risk_pct, 2),
                "adjusted": round(self.adjusted_risk_pct, 2),
                "level": self.risk_level.value,
                "combinedMultiplier": round(self.combined_multiplier, 3)
            },
            "multipliers": {
                "quality": self.quality_multiplier.to_dict(),
                "health": self.health_multiplier.to_dict(),
                "regime": self.regime_multiplier.to_dict(),
                "confidence": self.confidence_multiplier.to_dict(),
                "correlation": self.correlation_multiplier.to_dict()
            },
            "positionSizing": {
                "recommended": round(self.recommended_position_pct, 2),
                "max": round(self.max_position_pct, 2)
            },
            "constraints": self.constraints_applied,
            "budget": {
                "before": round(self.budget_before, 2),
                "after": round(self.budget_after, 2),
                "status": self.budget_status.value
            },
            "computedAt": self.computed_at
        }


# ===========================================
# Risk Budget
# ===========================================

@dataclass
class RiskBudget:
    """Portfolio risk budget"""
    # Total budget
    total_budget_pct: float = 10.0  # 10% max portfolio risk
    used_budget_pct: float = 0.0
    available_budget_pct: float = 10.0
    
    # Status
    status: BudgetStatus = BudgetStatus.AVAILABLE
    utilization_pct: float = 0.0
    
    # Breakdown by type
    by_strategy: Dict[str, float] = field(default_factory=dict)
    by_asset: Dict[str, float] = field(default_factory=dict)
    by_regime: Dict[str, float] = field(default_factory=dict)
    by_direction: Dict[str, float] = field(default_factory=dict)
    
    # Active positions
    active_positions: int = 0
    position_risks: Dict[str, float] = field(default_factory=dict)
    
    # Limits
    max_single_trade_pct: float = 2.0
    max_strategy_pct: float = 4.0
    max_asset_pct: float = 3.0
    max_regime_pct: float = 5.0
    max_direction_pct: float = 6.0
    
    updated_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget": {
                "total": round(self.total_budget_pct, 2),
                "used": round(self.used_budget_pct, 2),
                "available": round(self.available_budget_pct, 2),
                "status": self.status.value,
                "utilization": round(self.utilization_pct, 1)
            },
            "breakdown": {
                "byStrategy": {k: round(v, 2) for k, v in self.by_strategy.items()},
                "byAsset": {k: round(v, 2) for k, v in self.by_asset.items()},
                "byRegime": {k: round(v, 2) for k, v in self.by_regime.items()},
                "byDirection": {k: round(v, 2) for k, v in self.by_direction.items()}
            },
            "positions": {
                "active": self.active_positions,
                "risks": {k: round(v, 2) for k, v in self.position_risks.items()}
            },
            "limits": {
                "maxSingleTrade": round(self.max_single_trade_pct, 2),
                "maxStrategy": round(self.max_strategy_pct, 2),
                "maxAsset": round(self.max_asset_pct, 2),
                "maxRegime": round(self.max_regime_pct, 2),
                "maxDirection": round(self.max_direction_pct, 2)
            },
            "updatedAt": self.updated_at
        }


# ===========================================
# Exposure Limit
# ===========================================

@dataclass
class ExposureLimit:
    """Exposure limit configuration"""
    exposure_type: ExposureType = ExposureType.SINGLE_TRADE
    category: str = ""  # e.g., "BTC", "TREND_CONFIRMATION", "LONG"
    
    # Limits
    max_exposure_pct: float = 2.0
    current_exposure_pct: float = 0.0
    available_pct: float = 2.0
    
    # Status
    utilization_pct: float = 0.0
    is_breached: bool = False
    positions_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.exposure_type.value,
            "category": self.category,
            "exposure": {
                "max": round(self.max_exposure_pct, 2),
                "current": round(self.current_exposure_pct, 2),
                "available": round(self.available_pct, 2)
            },
            "utilization": round(self.utilization_pct, 1),
            "isBreached": self.is_breached,
            "positionsCount": self.positions_count
        }


@dataclass
class ExposureSummary:
    """Summary of all exposure limits"""
    limits: List[ExposureLimit] = field(default_factory=list)
    breached_limits: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    total_portfolio_exposure: float = 0.0
    max_portfolio_exposure: float = 15.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "limits": [l.to_dict() for l in self.limits],
            "breached": self.breached_limits,
            "warnings": self.warnings,
            "portfolio": {
                "current": round(self.total_portfolio_exposure, 2),
                "max": round(self.max_portfolio_exposure, 2),
                "utilization": round(self.total_portfolio_exposure / self.max_portfolio_exposure * 100, 1) if self.max_portfolio_exposure > 0 else 0
            }
        }


# ===========================================
# Risk Adjustment Request
# ===========================================

@dataclass
class RiskAdjustmentInput:
    """Input for risk calculation"""
    position_id: str = ""
    symbol: str = ""
    strategy: str = ""
    direction: str = ""
    
    # Base parameters
    base_risk_pct: float = 1.0
    
    # Quality inputs
    quality_grade: str = "B"
    quality_score: float = 65.0
    
    # Health inputs
    health_status: str = "GOOD"
    health_score: float = 70.0
    
    # Market context
    regime: str = "TRENDING"
    regime_stability: float = 0.8
    
    # Signal inputs
    signal_confidence: float = 0.7
    
    # Correlation inputs
    correlated_positions: List[str] = field(default_factory=list)
    correlation_score: float = 0.3
