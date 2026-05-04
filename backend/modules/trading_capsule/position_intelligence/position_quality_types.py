"""
Position Intelligence Types
===========================

Core types for Position Intelligence (PHASE 3.1)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time


class QualityGrade(str, Enum):
    """Quality grade based on score"""
    A_PLUS = "A+"   # 90-100
    A = "A"         # 80-89
    B_PLUS = "B+"   # 70-79
    B = "B"         # 60-69
    C = "C"         # 50-59
    D = "D"         # 40-49
    F = "F"         # 0-39


class HealthStatus(str, Enum):
    """Trade health status"""
    EXCELLENT = "EXCELLENT"   # >80
    GOOD = "GOOD"             # 60-80
    WARNING = "WARNING"       # 40-60
    CRITICAL = "CRITICAL"     # 20-40
    TERMINAL = "TERMINAL"     # <20


class RiskLevel(str, Enum):
    """Risk level"""
    MINIMAL = "MINIMAL"       # 0.25x base
    REDUCED = "REDUCED"       # 0.5x base
    NORMAL = "NORMAL"         # 1x base
    ELEVATED = "ELEVATED"     # 1.25x base (only for A+ quality)
    MAXIMUM = "MAXIMUM"       # 1.5x base (rare, exceptional setup)


# ===========================================
# Position Quality Score
# ===========================================

@dataclass
class SignalQualityMetrics:
    """Signal quality component metrics"""
    confluence_score: float = 0.0      # Multiple confirmations
    pattern_clarity: float = 0.0       # Clear pattern recognition
    volume_confirmation: float = 0.0   # Volume supports signal
    indicator_alignment: float = 0.0   # Indicators agree
    timeframe_alignment: float = 0.0   # HTF/LTF agreement
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "confluence": round(self.confluence_score, 1),
            "patternClarity": round(self.pattern_clarity, 1),
            "volumeConfirmation": round(self.volume_confirmation, 1),
            "indicatorAlignment": round(self.indicator_alignment, 1),
            "timeframeAlignment": round(self.timeframe_alignment, 1)
        }


@dataclass
class MarketContextMetrics:
    """Market context component metrics"""
    regime_stability: float = 0.0      # Stable vs transitioning
    trend_strength: float = 0.0        # ADX / trend clarity
    volatility_favorable: float = 0.0  # Volatility suits strategy
    structure_intact: float = 0.0      # Key levels holding
    momentum_support: float = 0.0      # Momentum direction
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regimeStability": round(self.regime_stability, 1),
            "trendStrength": round(self.trend_strength, 1),
            "volatilityFavorable": round(self.volatility_favorable, 1),
            "structureIntact": round(self.structure_intact, 1),
            "momentumSupport": round(self.momentum_support, 1)
        }


@dataclass
class RiskMetrics:
    """Risk component metrics"""
    risk_reward_ratio: float = 0.0     # R:R attractiveness
    stop_distance_quality: float = 0.0 # Stop at logical level
    exposure_acceptable: float = 0.0   # Within exposure limits
    correlation_safe: float = 0.0      # Not over-correlated
    drawdown_buffer: float = 0.0       # Room before max DD
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "riskRewardRatio": round(self.risk_reward_ratio, 1),
            "stopDistanceQuality": round(self.stop_distance_quality, 1),
            "exposureAcceptable": round(self.exposure_acceptable, 1),
            "correlationSafe": round(self.correlation_safe, 1),
            "drawdownBuffer": round(self.drawdown_buffer, 1)
        }


@dataclass
class PositionQualityScore:
    """Complete position quality assessment"""
    position_id: str = ""
    symbol: str = ""
    strategy: str = ""
    direction: str = ""
    
    # Component scores (0-100)
    signal_quality: float = 0.0
    market_context: float = 0.0
    risk_quality: float = 0.0
    timing_quality: float = 0.0
    execution_quality: float = 0.0
    
    # Detailed metrics
    signal_metrics: SignalQualityMetrics = field(default_factory=SignalQualityMetrics)
    context_metrics: MarketContextMetrics = field(default_factory=MarketContextMetrics)
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    
    # Overall score
    total_score: float = 0.0
    grade: QualityGrade = QualityGrade.C
    
    # Weights used
    weights: Dict[str, float] = field(default_factory=lambda: {
        "signal": 0.30,
        "context": 0.25,
        "risk": 0.25,
        "timing": 0.10,
        "execution": 0.10
    })
    
    # Recommendations
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendation: str = ""
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "direction": self.direction,
            "scores": {
                "signalQuality": round(self.signal_quality, 1),
                "marketContext": round(self.market_context, 1),
                "riskQuality": round(self.risk_quality, 1),
                "timingQuality": round(self.timing_quality, 1),
                "executionQuality": round(self.execution_quality, 1),
                "total": round(self.total_score, 1)
            },
            "grade": self.grade.value,
            "details": {
                "signal": self.signal_metrics.to_dict(),
                "context": self.context_metrics.to_dict(),
                "risk": self.risk_metrics.to_dict()
            },
            "weights": self.weights,
            "analysis": {
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "recommendation": self.recommendation
            },
            "computedAt": self.computed_at
        }


# ===========================================
# Trade Health Score
# ===========================================

@dataclass
class TradeHealthScore:
    """Dynamic trade health assessment"""
    position_id: str = ""
    
    # Current health (0-100)
    current_health: float = 100.0
    previous_health: float = 100.0
    health_change: float = 0.0  # Positive = improving
    
    # Status
    status: HealthStatus = HealthStatus.GOOD
    
    # Components (0-100)
    price_action_health: float = 0.0   # Price moving favorably
    structure_health: float = 0.0       # Key levels intact
    momentum_health: float = 0.0        # Momentum supportive
    time_health: float = 0.0            # Not overstaying
    pnl_health: float = 0.0             # Current P&L state
    
    # Trend
    health_trend: str = "STABLE"  # IMPROVING, STABLE, DETERIORATING
    bars_in_current_status: int = 0
    
    # Alerts
    warnings: List[str] = field(default_factory=list)
    critical_alerts: List[str] = field(default_factory=list)
    
    # Actions
    recommended_action: str = "HOLD"  # HOLD, REDUCE, EXIT
    action_urgency: str = "LOW"  # LOW, MEDIUM, HIGH, IMMEDIATE
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "health": {
                "current": round(self.current_health, 1),
                "previous": round(self.previous_health, 1),
                "change": round(self.health_change, 1),
                "status": self.status.value,
                "trend": self.health_trend
            },
            "components": {
                "priceAction": round(self.price_action_health, 1),
                "structure": round(self.structure_health, 1),
                "momentum": round(self.momentum_health, 1),
                "time": round(self.time_health, 1),
                "pnl": round(self.pnl_health, 1)
            },
            "alerts": {
                "warnings": self.warnings,
                "critical": self.critical_alerts
            },
            "action": {
                "recommended": self.recommended_action,
                "urgency": self.action_urgency
            },
            "barsInStatus": self.bars_in_current_status,
            "computedAt": self.computed_at
        }


# ===========================================
# Risk Adjustment
# ===========================================

@dataclass
class RiskAdjustment:
    """Dynamic risk adjustment"""
    position_id: str = ""
    
    # Base risk
    base_risk_pct: float = 1.0
    
    # Adjustments
    quality_multiplier: float = 1.0    # Based on quality score
    health_multiplier: float = 1.0     # Based on health score
    regime_multiplier: float = 1.0     # Based on regime stability
    confidence_multiplier: float = 1.0 # Based on signal confidence
    
    # Final risk
    adjusted_risk_pct: float = 1.0
    risk_level: RiskLevel = RiskLevel.NORMAL
    
    # Constraints applied
    constraints_applied: List[str] = field(default_factory=list)
    
    # Explanation
    adjustment_reasons: List[str] = field(default_factory=list)
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "risk": {
                "base": round(self.base_risk_pct, 2),
                "adjusted": round(self.adjusted_risk_pct, 2),
                "level": self.risk_level.value
            },
            "multipliers": {
                "quality": round(self.quality_multiplier, 2),
                "health": round(self.health_multiplier, 2),
                "regime": round(self.regime_multiplier, 2),
                "confidence": round(self.confidence_multiplier, 2)
            },
            "constraints": self.constraints_applied,
            "reasons": self.adjustment_reasons,
            "computedAt": self.computed_at
        }


# ===========================================
# Combined Position Intelligence
# ===========================================

@dataclass
class PositionIntelligence:
    """Complete position intelligence package"""
    position_id: str = ""
    symbol: str = ""
    strategy: str = ""
    
    quality: PositionQualityScore = field(default_factory=PositionQualityScore)
    health: TradeHealthScore = field(default_factory=TradeHealthScore)
    risk_adjustment: RiskAdjustment = field(default_factory=RiskAdjustment)
    
    # Overall recommendation
    overall_score: float = 0.0
    overall_status: str = "NEUTRAL"  # STRONG, GOOD, NEUTRAL, WEAK, EXIT
    primary_action: str = "HOLD"
    
    computed_at: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "positionId": self.position_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "quality": self.quality.to_dict(),
            "health": self.health.to_dict(),
            "riskAdjustment": self.risk_adjustment.to_dict(),
            "overall": {
                "score": round(self.overall_score, 1),
                "status": self.overall_status,
                "primaryAction": self.primary_action
            },
            "computedAt": self.computed_at
        }
