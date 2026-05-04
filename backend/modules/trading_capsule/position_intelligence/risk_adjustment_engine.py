"""
Risk Adjustment Engine
======================

Dynamic risk adjustment based on quality and health (PHASE 3.1)
"""

import time
from typing import Dict, List, Optional, Any

from .position_quality_types import (
    RiskAdjustment,
    RiskLevel,
    PositionQualityScore,
    TradeHealthScore,
    QualityGrade,
    HealthStatus
)


class RiskAdjustmentEngine:
    """
    Calculates dynamic risk adjustment.
    
    Based on:
    - Position Quality Score
    - Trade Health Score
    - Regime Stability
    - Signal Confidence
    
    Output: Adjusted risk percentage and level
    """
    
    def __init__(self):
        # Quality grade multipliers
        self._quality_multipliers = {
            QualityGrade.A_PLUS: 1.50,   # 50% more risk allowed
            QualityGrade.A: 1.25,         # 25% more
            QualityGrade.B_PLUS: 1.10,    # 10% more
            QualityGrade.B: 1.00,         # Normal
            QualityGrade.C: 0.75,         # 25% less
            QualityGrade.D: 0.50,         # 50% less
            QualityGrade.F: 0.25          # 75% less
        }
        
        # Health status multipliers
        self._health_multipliers = {
            HealthStatus.EXCELLENT: 1.10,
            HealthStatus.GOOD: 1.00,
            HealthStatus.WARNING: 0.70,
            HealthStatus.CRITICAL: 0.40,
            HealthStatus.TERMINAL: 0.10
        }
        
        # Regime stability multipliers
        self._regime_multipliers = {
            "STABLE": 1.10,
            "NORMAL": 1.00,
            "TRANSITIONING": 0.75,
            "UNSTABLE": 0.50
        }
        
        # Risk level thresholds
        self._risk_levels = {
            RiskLevel.MAXIMUM: 1.40,    # > 140% of base
            RiskLevel.ELEVATED: 1.15,   # > 115% of base
            RiskLevel.NORMAL: 0.85,     # > 85% of base
            RiskLevel.REDUCED: 0.50,    # > 50% of base
            RiskLevel.MINIMAL: 0.0      # <= 50% of base
        }
        
        # Constraints
        self._max_risk_multiplier = 1.50
        self._min_risk_multiplier = 0.25
        
        print("[RiskAdjustmentEngine] Initialized (PHASE 3.1)")
    
    def calculate_adjustment(
        self,
        position_id: str,
        base_risk_pct: float,
        quality: PositionQualityScore,
        health: Optional[TradeHealthScore] = None,
        regime_stability: str = "NORMAL",
        signal_confidence: float = 0.8
    ) -> RiskAdjustment:
        """
        Calculate risk adjustment.
        """
        
        adjustment = RiskAdjustment(
            position_id=position_id,
            base_risk_pct=base_risk_pct,
            computed_at=int(time.time() * 1000)
        )
        
        reasons = []
        constraints = []
        
        # Quality multiplier
        adjustment.quality_multiplier = self._quality_multipliers.get(
            quality.grade,
            1.0
        )
        reasons.append(f"Quality grade {quality.grade.value}: {adjustment.quality_multiplier:.2f}x")
        
        # Health multiplier
        if health:
            adjustment.health_multiplier = self._health_multipliers.get(
                health.status,
                1.0
            )
            reasons.append(f"Health status {health.status.value}: {adjustment.health_multiplier:.2f}x")
        else:
            adjustment.health_multiplier = 1.0
            reasons.append("No health data: 1.00x")
        
        # Regime multiplier
        adjustment.regime_multiplier = self._regime_multipliers.get(
            regime_stability.upper(),
            1.0
        )
        reasons.append(f"Regime {regime_stability}: {adjustment.regime_multiplier:.2f}x")
        
        # Confidence multiplier
        if signal_confidence >= 0.9:
            adjustment.confidence_multiplier = 1.15
        elif signal_confidence >= 0.8:
            adjustment.confidence_multiplier = 1.05
        elif signal_confidence >= 0.7:
            adjustment.confidence_multiplier = 1.00
        elif signal_confidence >= 0.6:
            adjustment.confidence_multiplier = 0.85
        else:
            adjustment.confidence_multiplier = 0.70
        reasons.append(f"Confidence {signal_confidence:.0%}: {adjustment.confidence_multiplier:.2f}x")
        
        # Calculate combined multiplier
        combined = (
            adjustment.quality_multiplier *
            adjustment.health_multiplier *
            adjustment.regime_multiplier *
            adjustment.confidence_multiplier
        )
        
        # Apply constraints
        if combined > self._max_risk_multiplier:
            combined = self._max_risk_multiplier
            constraints.append(f"Capped at max multiplier ({self._max_risk_multiplier:.2f}x)")
        
        if combined < self._min_risk_multiplier:
            combined = self._min_risk_multiplier
            constraints.append(f"Floored at min multiplier ({self._min_risk_multiplier:.2f}x)")
        
        # Special constraints
        if quality.grade == QualityGrade.F:
            combined = min(combined, 0.25)
            constraints.append("F-grade: max 0.25x risk")
        
        if health and health.status == HealthStatus.TERMINAL:
            combined = min(combined, 0.10)
            constraints.append("Terminal health: max 0.10x risk")
        
        # Calculate adjusted risk
        adjustment.adjusted_risk_pct = base_risk_pct * combined
        
        # Determine risk level
        adjustment.risk_level = self._get_risk_level(combined)
        
        adjustment.adjustment_reasons = reasons
        adjustment.constraints_applied = constraints
        
        return adjustment
    
    def calculate_position_size_adjustment(
        self,
        current_size: float,
        current_risk_pct: float,
        new_adjustment: RiskAdjustment
    ) -> Dict[str, Any]:
        """
        Calculate how to adjust position size based on new risk.
        """
        
        target_risk = new_adjustment.adjusted_risk_pct
        
        if target_risk <= 0:
            return {
                "action": "EXIT",
                "currentSize": current_size,
                "targetSize": 0,
                "changePercent": -100,
                "reason": "Risk reduced to zero - exit position"
            }
        
        # Calculate size adjustment ratio
        size_ratio = target_risk / current_risk_pct if current_risk_pct > 0 else 1.0
        target_size = current_size * size_ratio
        change_pct = (size_ratio - 1) * 100
        
        # Determine action
        if change_pct > 10:
            action = "INCREASE"
        elif change_pct < -10:
            action = "REDUCE"
        else:
            action = "HOLD"
        
        return {
            "action": action,
            "currentSize": round(current_size, 4),
            "targetSize": round(target_size, 4),
            "changePercent": round(change_pct, 1),
            "reason": f"Risk adjustment from {current_risk_pct:.2f}% to {target_risk:.2f}%"
        }
    
    def _get_risk_level(self, multiplier: float) -> RiskLevel:
        """Convert multiplier to risk level"""
        
        if multiplier >= self._risk_levels[RiskLevel.MAXIMUM]:
            return RiskLevel.MAXIMUM
        elif multiplier >= self._risk_levels[RiskLevel.ELEVATED]:
            return RiskLevel.ELEVATED
        elif multiplier >= self._risk_levels[RiskLevel.NORMAL]:
            return RiskLevel.NORMAL
        elif multiplier >= self._risk_levels[RiskLevel.REDUCED]:
            return RiskLevel.REDUCED
        else:
            return RiskLevel.MINIMAL
    
    def get_multiplier_tables(self) -> Dict[str, Any]:
        """Get all multiplier tables"""
        return {
            "quality": {k.value: v for k, v in self._quality_multipliers.items()},
            "health": {k.value: v for k, v in self._health_multipliers.items()},
            "regime": self._regime_multipliers,
            "constraints": {
                "max": self._max_risk_multiplier,
                "min": self._min_risk_multiplier
            }
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "RiskAdjustmentEngine",
            "status": "active",
            "version": "1.0.0",
            "riskLevels": [r.value for r in RiskLevel],
            "multiplierRanges": {
                "max": self._max_risk_multiplier,
                "min": self._min_risk_multiplier
            },
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
risk_adjustment_engine = RiskAdjustmentEngine()
