"""
Dynamic Risk Engine
===================

PHASE 3.3 - Core risk calculation engine combining all multipliers.
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .risk_types import (
    RiskLevel,
    RiskCalculation,
    BudgetStatus,
    RiskAdjustmentInput
)
from .risk_multiplier_engine import risk_multiplier_engine
from .risk_budget_engine import risk_budget_engine
from .risk_limits_engine import risk_limits_engine


class DynamicRiskEngine:
    """
    Dynamic Risk Engine:
    - Calculates risk multipliers from Quality, Health, Regime, Confidence
    - Combines multipliers to get final risk
    - Checks budget and exposure limits
    - Returns position sizing recommendations
    """
    
    def __init__(self):
        # Risk level thresholds
        self._risk_thresholds = {
            RiskLevel.MAXIMUM: 1.4,
            RiskLevel.ELEVATED: 1.2,
            RiskLevel.NORMAL: 0.9,
            RiskLevel.REDUCED: 0.6,
            RiskLevel.MINIMAL: 0.0
        }
        
        # Minimum risk floor
        self._min_risk_pct = 0.1
        
        # Maximum risk cap
        self._max_risk_pct = 2.5
        
        print("[DynamicRiskEngine] Initialized (PHASE 3.3)")
    
    def calculate_risk(
        self,
        position_id: str,
        symbol: str,
        strategy: str,
        direction: str,
        base_risk_pct: float,
        quality_grade: str,
        quality_score: float,
        health_status: str,
        health_score: float,
        regime: str,
        regime_stability: float,
        signal_confidence: float,
        correlated_positions: List[str] = None,
        correlation_score: float = 0.0,
        allocate_budget: bool = True
    ) -> RiskCalculation:
        """
        Calculate dynamic risk with all factors.
        """
        
        correlated_positions = correlated_positions or []
        
        calc = RiskCalculation(
            position_id=position_id or f"pos_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            strategy=strategy,
            direction=direction,
            base_risk_pct=base_risk_pct,
            computed_at=int(time.time() * 1000)
        )
        
        # Calculate multipliers
        calc.quality_multiplier = risk_multiplier_engine.calculate_quality_multiplier(
            grade=quality_grade,
            score=quality_score
        )
        
        calc.health_multiplier = risk_multiplier_engine.calculate_health_multiplier(
            status=health_status,
            health_score=health_score
        )
        
        calc.regime_multiplier = risk_multiplier_engine.calculate_regime_multiplier(
            regime=regime,
            stability=regime_stability
        )
        
        calc.confidence_multiplier = risk_multiplier_engine.calculate_confidence_multiplier(
            confidence=signal_confidence
        )
        
        calc.correlation_multiplier = risk_multiplier_engine.calculate_correlation_multiplier(
            correlation_score=correlation_score,
            correlated_positions=correlated_positions
        )
        
        # Calculate combined multiplier
        calc.combined_multiplier = (
            calc.quality_multiplier.multiplier *
            calc.health_multiplier.multiplier *
            calc.regime_multiplier.multiplier *
            calc.confidence_multiplier.multiplier *
            calc.correlation_multiplier.multiplier
        )
        
        # Calculate adjusted risk
        adjusted = base_risk_pct * calc.combined_multiplier
        
        # Apply floor and cap
        if adjusted < self._min_risk_pct:
            adjusted = self._min_risk_pct
            calc.constraints_applied.append(f"Min risk floor: {self._min_risk_pct}%")
        
        if adjusted > self._max_risk_pct:
            adjusted = self._max_risk_pct
            calc.constraints_applied.append(f"Max risk cap: {self._max_risk_pct}%")
        
        # Zero risk for F grade or TERMINAL health
        if quality_grade.upper() == "F":
            adjusted = 0.0
            calc.constraints_applied.append("Zero risk: F quality grade")
        
        if health_status.upper() == "TERMINAL":
            adjusted = 0.0
            calc.constraints_applied.append("Zero risk: TERMINAL health")
        
        calc.adjusted_risk_pct = adjusted
        
        # Determine risk level
        calc.risk_level = self._get_risk_level(calc.combined_multiplier)
        
        # Check limits
        if adjusted > 0:
            limits_check = risk_limits_engine.check_limits(
                risk_pct=adjusted,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                regime=regime
            )
            
            if not limits_check["canProceed"]:
                for violation in limits_check["violations"]:
                    calc.constraints_applied.append(f"Limit violated: {violation['type']}")
                
                # Reduce to available
                adjusted = self._find_available_risk(adjusted, limits_check)
                calc.adjusted_risk_pct = adjusted
        
        # Position sizing
        calc.recommended_position_pct = adjusted
        calc.max_position_pct = min(adjusted * 1.2, self._max_risk_pct)
        
        # Budget allocation
        budget_before = risk_budget_engine.get_budget()
        calc.budget_before = budget_before.used_budget_pct
        
        if allocate_budget and adjusted > 0:
            allocation = risk_budget_engine.allocate_risk(
                position_id=calc.position_id,
                risk_pct=adjusted,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                regime=regime
            )
            
            if not allocation["success"]:
                calc.constraints_applied.append("Budget allocation failed")
                calc.adjusted_risk_pct = 0.0
            elif allocation["allocated"] < adjusted:
                calc.constraints_applied.extend(allocation["constraints"])
                calc.adjusted_risk_pct = allocation["allocated"]
            
            calc.budget_after = allocation["budgetAfter"]
            calc.budget_status = BudgetStatus(allocation["budgetStatus"])
        else:
            calc.budget_after = calc.budget_before
            calc.budget_status = budget_before.status
        
        # Add exposure tracking if allocated
        if allocate_budget and calc.adjusted_risk_pct > 0:
            risk_limits_engine.add_exposure(
                position_id=calc.position_id,
                risk_pct=calc.adjusted_risk_pct,
                symbol=symbol,
                strategy=strategy,
                direction=direction,
                regime=regime
            )
        
        return calc
    
    def calculate_multiplier_only(
        self,
        quality_grade: str,
        quality_score: float,
        health_status: str,
        health_score: float,
        regime: str,
        regime_stability: float,
        signal_confidence: float,
        correlation_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate multipliers without budget allocation.
        """
        
        quality = risk_multiplier_engine.calculate_quality_multiplier(quality_grade, quality_score)
        health = risk_multiplier_engine.calculate_health_multiplier(health_status, health_score)
        regime_mult = risk_multiplier_engine.calculate_regime_multiplier(regime, regime_stability)
        confidence = risk_multiplier_engine.calculate_confidence_multiplier(signal_confidence)
        correlation = risk_multiplier_engine.calculate_correlation_multiplier(correlation_score)
        
        combined = (
            quality.multiplier *
            health.multiplier *
            regime_mult.multiplier *
            confidence.multiplier *
            correlation.multiplier
        )
        
        return {
            "multipliers": {
                "quality": quality.to_dict(),
                "health": health.to_dict(),
                "regime": regime_mult.to_dict(),
                "confidence": confidence.to_dict(),
                "correlation": correlation.to_dict()
            },
            "combined": round(combined, 3),
            "riskLevel": self._get_risk_level(combined).value,
            "effectiveRisk": f"{combined:.0%} of base"
        }
    
    def release_position(self, position_id: str) -> Dict[str, Any]:
        """Release risk and exposure for closed position"""
        
        budget_release = risk_budget_engine.release_risk(position_id)
        limits_release = risk_limits_engine.remove_exposure(position_id)
        
        return {
            "positionId": position_id,
            "budget": budget_release,
            "limitsReleased": limits_release,
            "timestamp": int(time.time() * 1000)
        }
    
    def _get_risk_level(self, multiplier: float) -> RiskLevel:
        """Determine risk level from multiplier"""
        
        if multiplier >= self._risk_thresholds[RiskLevel.MAXIMUM]:
            return RiskLevel.MAXIMUM
        elif multiplier >= self._risk_thresholds[RiskLevel.ELEVATED]:
            return RiskLevel.ELEVATED
        elif multiplier >= self._risk_thresholds[RiskLevel.NORMAL]:
            return RiskLevel.NORMAL
        elif multiplier >= self._risk_thresholds[RiskLevel.REDUCED]:
            return RiskLevel.REDUCED
        else:
            return RiskLevel.MINIMAL
    
    def _find_available_risk(self, requested: float, limits_check: Dict) -> float:
        """Find maximum available risk within limits"""
        
        # Find the most restrictive limit
        min_available = requested
        
        for violation in limits_check.get("violations", []):
            if "available" in violation:
                min_available = min(min_available, violation.get("available", 0))
        
        return max(0, min_available)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete risk management summary"""
        
        budget = risk_budget_engine.get_budget()
        exposure = risk_limits_engine.get_exposure_summary()
        
        return {
            "budget": budget.to_dict(),
            "exposure": exposure.to_dict(),
            "config": {
                "minRisk": self._min_risk_pct,
                "maxRisk": self._max_risk_pct,
                "riskThresholds": {k.value: v for k, v in self._risk_thresholds.items()}
            },
            "timestamp": int(time.time() * 1000)
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        budget = risk_budget_engine.get_budget()
        
        return {
            "engine": "DynamicRiskEngine",
            "version": "1.0.0",
            "phase": "3.3",
            "status": "active",
            "subEngines": {
                "multiplier": risk_multiplier_engine.get_health(),
                "budget": risk_budget_engine.get_health(),
                "limits": risk_limits_engine.get_health()
            },
            "summary": {
                "budgetUtilization": round(budget.utilization_pct, 1),
                "budgetStatus": budget.status.value,
                "activePositions": budget.active_positions
            },
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
dynamic_risk_engine = DynamicRiskEngine()
