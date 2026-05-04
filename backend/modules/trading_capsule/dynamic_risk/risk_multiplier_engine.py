"""
Risk Multiplier Engine
======================

PHASE 3.3 - Calculates risk multipliers based on Quality, Health, Regime, Confidence.
"""

import time
from typing import Dict, List, Optional, Any

from .risk_types import (
    QualityMultiplier,
    HealthMultiplier,
    RegimeMultiplier,
    ConfidenceMultiplier,
    CorrelationMultiplier
)


class RiskMultiplierEngine:
    """
    Calculates risk multipliers:
    - Quality multiplier (Grade A+ to F)
    - Health multiplier (EXCELLENT to TERMINAL)
    - Regime multiplier (TRENDING, RANGE, HIGH_VOL)
    - Confidence multiplier (Signal confidence)
    - Correlation multiplier (Portfolio correlation)
    """
    
    def __init__(self):
        # Quality grade multipliers
        self._quality_multipliers = {
            "A+": 1.5,
            "A": 1.3,
            "B+": 1.1,
            "B": 1.0,
            "C": 0.7,
            "D": 0.4,
            "F": 0.0
        }
        
        # Health status multipliers
        self._health_multipliers = {
            "EXCELLENT": 1.1,
            "GOOD": 1.0,
            "STABLE": 0.9,
            "WEAK": 0.7,
            "CRITICAL": 0.4,
            "TERMINAL": 0.0
        }
        
        # Regime multipliers
        self._regime_multipliers = {
            "TRENDING": 1.1,
            "TREND_UP": 1.1,
            "TREND_DOWN": 1.1,
            "RANGE": 1.0,
            "HIGH_VOLATILITY": 0.8,
            "LOW_VOLATILITY": 0.95,
            "TRANSITION": 0.7,
            "COMPRESSION": 0.85,
            "EXPANSION": 0.9
        }
        
        # Stability adjustments
        self._stability_adjustments = {
            "HIGH": 1.05,     # Stability >= 0.8
            "NORMAL": 1.0,   # Stability 0.5-0.8
            "LOW": 0.85,     # Stability 0.3-0.5
            "VERY_LOW": 0.7  # Stability < 0.3
        }
        
        # Confidence thresholds
        self._confidence_thresholds = [
            (0.9, 1.15),  # Very high confidence
            (0.8, 1.1),   # High confidence
            (0.7, 1.0),   # Normal confidence
            (0.6, 0.9),   # Below average
            (0.5, 0.8),   # Low confidence
            (0.0, 0.6)    # Very low confidence
        ]
        
        # Correlation thresholds
        self._correlation_thresholds = [
            (0.8, 0.5),   # High correlation - reduce significantly
            (0.6, 0.7),   # Moderate-high correlation
            (0.4, 0.85),  # Moderate correlation
            (0.2, 0.95),  # Low correlation
            (0.0, 1.0)    # No correlation
        ]
        
        print("[RiskMultiplierEngine] Initialized (PHASE 3.3)")
    
    def calculate_quality_multiplier(
        self,
        grade: str,
        score: float = 0.0
    ) -> QualityMultiplier:
        """Calculate multiplier based on quality grade"""
        
        grade = grade.upper()
        multiplier = self._quality_multipliers.get(grade, 1.0)
        
        # Small bonus for high scores within grade
        if score >= 90:
            multiplier += 0.05
        elif score >= 85:
            multiplier += 0.03
        
        # Generate reason
        if grade in ["A+", "A"]:
            reason = f"High quality setup ({grade}) - increased risk allocation"
        elif grade in ["B+", "B"]:
            reason = f"Standard quality ({grade}) - normal risk"
        elif grade == "C":
            reason = f"Below average quality ({grade}) - reduced risk"
        elif grade == "D":
            reason = f"Poor quality ({grade}) - minimal risk"
        else:
            reason = f"Unacceptable quality ({grade}) - no risk"
        
        return QualityMultiplier(
            grade=grade,
            multiplier=max(0, min(1.6, multiplier)),
            reason=reason
        )
    
    def calculate_health_multiplier(
        self,
        status: str,
        health_score: float = 70.0
    ) -> HealthMultiplier:
        """Calculate multiplier based on health status"""
        
        status = status.upper()
        multiplier = self._health_multipliers.get(status, 1.0)
        
        # Continuous adjustment based on score
        if health_score >= 90:
            multiplier += 0.05
        elif health_score <= 30:
            multiplier -= 0.1
        
        # Generate reason
        if status == "EXCELLENT":
            reason = "Position health excellent - can increase exposure"
        elif status == "GOOD":
            reason = "Position health good - normal exposure"
        elif status == "STABLE":
            reason = "Position health stable - slightly reduced exposure"
        elif status == "WEAK":
            reason = "Position health weak - significant reduction"
        elif status == "CRITICAL":
            reason = "Position health critical - minimal exposure only"
        else:
            reason = "Position health terminal - no additional exposure"
        
        return HealthMultiplier(
            status=status,
            health_score=health_score,
            multiplier=max(0, min(1.2, multiplier)),
            reason=reason
        )
    
    def calculate_regime_multiplier(
        self,
        regime: str,
        stability: float = 0.8
    ) -> RegimeMultiplier:
        """Calculate multiplier based on market regime"""
        
        regime = regime.upper()
        base_multiplier = self._regime_multipliers.get(regime, 1.0)
        
        # Stability adjustment
        if stability >= 0.8:
            stability_adj = self._stability_adjustments["HIGH"]
        elif stability >= 0.5:
            stability_adj = self._stability_adjustments["NORMAL"]
        elif stability >= 0.3:
            stability_adj = self._stability_adjustments["LOW"]
        else:
            stability_adj = self._stability_adjustments["VERY_LOW"]
        
        multiplier = base_multiplier * stability_adj
        
        # Generate reason
        if regime in ["TRENDING", "TREND_UP", "TREND_DOWN"]:
            reason = f"Trending regime ({stability:.0%} stable) - favorable conditions"
        elif regime == "RANGE":
            reason = f"Range regime ({stability:.0%} stable) - standard conditions"
        elif regime in ["HIGH_VOLATILITY", "EXPANSION"]:
            reason = f"High volatility ({stability:.0%} stable) - reduced exposure"
        elif regime == "TRANSITION":
            reason = f"Regime transition ({stability:.0%} stable) - caution advised"
        else:
            reason = f"Regime: {regime} ({stability:.0%} stable)"
        
        return RegimeMultiplier(
            regime=regime,
            stability=stability,
            multiplier=max(0.5, min(1.2, multiplier)),
            reason=reason
        )
    
    def calculate_confidence_multiplier(
        self,
        confidence: float
    ) -> ConfidenceMultiplier:
        """Calculate multiplier based on signal confidence"""
        
        multiplier = 1.0
        for threshold, mult in self._confidence_thresholds:
            if confidence >= threshold:
                multiplier = mult
                break
        
        # Generate reason
        if confidence >= 0.85:
            reason = f"High signal confidence ({confidence:.0%}) - increased allocation"
        elif confidence >= 0.7:
            reason = f"Normal signal confidence ({confidence:.0%})"
        elif confidence >= 0.55:
            reason = f"Below average confidence ({confidence:.0%}) - reduced allocation"
        else:
            reason = f"Low confidence ({confidence:.0%}) - minimal allocation"
        
        return ConfidenceMultiplier(
            confidence=confidence,
            multiplier=max(0.5, min(1.2, multiplier)),
            reason=reason
        )
    
    def calculate_correlation_multiplier(
        self,
        correlation_score: float,
        correlated_positions: List[str] = None
    ) -> CorrelationMultiplier:
        """Calculate multiplier based on portfolio correlation"""
        
        correlated_positions = correlated_positions or []
        
        multiplier = 1.0
        for threshold, mult in self._correlation_thresholds:
            if correlation_score >= threshold:
                multiplier = mult
                break
        
        # Additional reduction for many correlated positions
        if len(correlated_positions) >= 3:
            multiplier *= 0.9
        
        # Generate reason
        if correlation_score >= 0.7:
            reason = f"High correlation ({correlation_score:.0%}) with {len(correlated_positions)} positions - significantly reduced"
        elif correlation_score >= 0.4:
            reason = f"Moderate correlation ({correlation_score:.0%}) - slightly reduced"
        else:
            reason = f"Low correlation ({correlation_score:.0%}) - no reduction"
        
        return CorrelationMultiplier(
            correlation_score=correlation_score,
            multiplier=max(0.4, min(1.0, multiplier)),
            correlated_positions=correlated_positions,
            reason=reason
        )
    
    def get_multiplier_tables(self) -> Dict[str, Any]:
        """Get all multiplier configuration tables"""
        return {
            "quality": self._quality_multipliers,
            "health": self._health_multipliers,
            "regime": self._regime_multipliers,
            "stability": self._stability_adjustments,
            "confidence": [
                {"minConfidence": t, "multiplier": m}
                for t, m in self._confidence_thresholds
            ],
            "correlation": [
                {"minCorrelation": t, "multiplier": m}
                for t, m in self._correlation_thresholds
            ]
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "RiskMultiplierEngine",
            "version": "1.0.0",
            "phase": "3.3",
            "status": "active",
            "multiplierTypes": ["quality", "health", "regime", "confidence", "correlation"],
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
risk_multiplier_engine = RiskMultiplierEngine()
