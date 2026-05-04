"""
Hypothesis Conflict Resolver

PHASE 29.3 — Hypothesis Conflict Resolver

Purpose: Prevent system from making decisions when signals strongly contradict each other.

Conflict States:
- LOW_CONFLICT: No changes needed
- MODERATE_CONFLICT: Reduce confidence by 10%, downgrade execution state
- HIGH_CONFLICT: Reduce confidence by 30%, force UNFAVORABLE execution state

This makes the system self-protecting against signal chaos.
"""

from enum import Enum
from typing import Optional, Dict, Tuple
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Constants — Conflict Thresholds
# ══════════════════════════════════════════════════════════════

CONFLICT_LOW_THRESHOLD = 0.10
CONFLICT_HIGH_THRESHOLD = 0.25

# ══════════════════════════════════════════════════════════════
# Constants — Conflict Modifiers
# ══════════════════════════════════════════════════════════════

# MODERATE_CONFLICT modifiers
MODERATE_CONFIDENCE_MODIFIER = 0.90
MODERATE_RELIABILITY_MODIFIER = 0.90

# HIGH_CONFLICT modifiers
HIGH_CONFIDENCE_MODIFIER = 0.70
HIGH_RELIABILITY_MODIFIER = 0.75


# ══════════════════════════════════════════════════════════════
# Conflict State Enum
# ══════════════════════════════════════════════════════════════

class ConflictState(str, Enum):
    """
    Conflict state classification.
    
    LOW: Signals are aligned, safe to trade
    MODERATE: Some disagreement, reduce confidence
    HIGH: Strong disagreement, avoid trading
    """
    LOW = "LOW_CONFLICT"
    MODERATE = "MODERATE_CONFLICT"
    HIGH = "HIGH_CONFLICT"


# ══════════════════════════════════════════════════════════════
# Conflict Resolution Result
# ══════════════════════════════════════════════════════════════

class ConflictResolutionResult:
    """
    Result of conflict resolution.
    
    Contains adjusted scores and state after conflict analysis.
    """
    
    def __init__(
        self,
        conflict_state: ConflictState,
        adjusted_confidence: float,
        adjusted_reliability: float,
        adjusted_execution_state: str,
        reason_suffix: str,
    ):
        self.conflict_state = conflict_state
        self.adjusted_confidence = adjusted_confidence
        self.adjusted_reliability = adjusted_reliability
        self.adjusted_execution_state = adjusted_execution_state
        self.reason_suffix = reason_suffix


# ══════════════════════════════════════════════════════════════
# Hypothesis Conflict Resolver
# ══════════════════════════════════════════════════════════════

class HypothesisConflictResolver:
    """
    Hypothesis Conflict Resolver — PHASE 29.3
    
    Analyzes conflict between intelligence layers and adjusts
    hypothesis confidence and execution state accordingly.
    
    The goal is to prevent trading when signals are chaotic.
    """
    
    def __init__(self):
        pass
    
    # ═══════════════════════════════════════════════════════════
    # 1. Conflict State Detection
    # ═══════════════════════════════════════════════════════════
    
    def detect_conflict_state(self, conflict_score: float) -> ConflictState:
        """
        Classify conflict score into ConflictState.
        
        conflict_score < 0.10 → LOW_CONFLICT
        0.10 ≤ score < 0.25 → MODERATE_CONFLICT
        score ≥ 0.25 → HIGH_CONFLICT
        """
        if conflict_score < CONFLICT_LOW_THRESHOLD:
            return ConflictState.LOW
        elif conflict_score < CONFLICT_HIGH_THRESHOLD:
            return ConflictState.MODERATE
        else:
            return ConflictState.HIGH
    
    # ═══════════════════════════════════════════════════════════
    # 2. Confidence Adjustment
    # ═══════════════════════════════════════════════════════════
    
    def adjust_confidence(
        self,
        confidence: float,
        conflict_state: ConflictState,
    ) -> float:
        """
        Adjust confidence based on conflict state.
        
        LOW_CONFLICT: No change
        MODERATE_CONFLICT: confidence × 0.90
        HIGH_CONFLICT: confidence × 0.70
        """
        if conflict_state == ConflictState.LOW:
            return confidence
        elif conflict_state == ConflictState.MODERATE:
            return round(confidence * MODERATE_CONFIDENCE_MODIFIER, 4)
        else:  # HIGH
            return round(confidence * HIGH_CONFIDENCE_MODIFIER, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Reliability Adjustment
    # ═══════════════════════════════════════════════════════════
    
    def adjust_reliability(
        self,
        reliability: float,
        conflict_state: ConflictState,
    ) -> float:
        """
        Adjust reliability based on conflict state.
        
        LOW_CONFLICT: No change
        MODERATE_CONFLICT: reliability × 0.90
        HIGH_CONFLICT: reliability × 0.75
        """
        if conflict_state == ConflictState.LOW:
            return reliability
        elif conflict_state == ConflictState.MODERATE:
            return round(reliability * MODERATE_RELIABILITY_MODIFIER, 4)
        else:  # HIGH
            return round(reliability * HIGH_RELIABILITY_MODIFIER, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Execution State Adjustment
    # ═══════════════════════════════════════════════════════════
    
    def adjust_execution_state(
        self,
        execution_state: str,
        conflict_state: ConflictState,
    ) -> str:
        """
        Adjust execution state based on conflict state.
        
        LOW_CONFLICT:
            No change
        
        MODERATE_CONFLICT:
            FAVORABLE → CAUTIOUS
            CAUTIOUS → CAUTIOUS
            UNFAVORABLE → UNFAVORABLE
        
        HIGH_CONFLICT:
            → UNFAVORABLE (always)
        """
        if conflict_state == ConflictState.LOW:
            return execution_state
        
        elif conflict_state == ConflictState.MODERATE:
            if execution_state == "FAVORABLE":
                return "CAUTIOUS"
            else:
                return execution_state
        
        else:  # HIGH
            return "UNFAVORABLE"
    
    # ═══════════════════════════════════════════════════════════
    # 5. Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_conflict_reason(
        self,
        conflict_state: ConflictState,
        alpha_support: float,
        regime_support: float,
        microstructure_support: float,
        hypothesis_type: str,
    ) -> str:
        """
        Generate reason suffix explaining the conflict.
        
        Describes which layers are in disagreement.
        """
        if conflict_state == ConflictState.LOW:
            return ""
        
        # Identify which layers are outliers
        values = {
            "alpha": alpha_support,
            "regime": regime_support,
            "microstructure": microstructure_support,
        }
        mean = sum(values.values()) / len(values)
        
        # Find layers far from mean
        high_layers = [k for k, v in values.items() if v > mean + 0.15]
        low_layers = [k for k, v in values.items() if v < mean - 0.15]
        
        parts = []
        
        if conflict_state == ConflictState.MODERATE:
            if high_layers and low_layers:
                parts.append(f"moderate signal conflict between {' and '.join(high_layers)} vs {' and '.join(low_layers)}")
            else:
                parts.append("moderate signal disagreement between layers")
        
        elif conflict_state == ConflictState.HIGH:
            # Build detailed reason for high conflict
            if alpha_support > 0.6 and regime_support < 0.4:
                parts.append("alpha factors bullish but regime instability")
            elif alpha_support < 0.4 and regime_support > 0.6:
                parts.append("regime structure strong but weak alpha factors")
            
            if microstructure_support < 0.4:
                parts.append("fragile microstructure")
            
            if not parts:
                if high_layers and low_layers:
                    parts.append(f"high signal conflict: {' and '.join(high_layers)} contradicts {' and '.join(low_layers)}")
                else:
                    parts.append("high signal conflict between intelligence layers")
            
            parts.append("reduces reliability")
        
        return " ".join(parts) if parts else ""
    
    # ═══════════════════════════════════════════════════════════
    # 6. Main Resolution Method
    # ═══════════════════════════════════════════════════════════
    
    def resolve(
        self,
        conflict_score: float,
        confidence: float,
        reliability: float,
        execution_state: str,
        alpha_support: float,
        regime_support: float,
        microstructure_support: float,
        hypothesis_type: str,
    ) -> ConflictResolutionResult:
        """
        Main conflict resolution method.
        
        Takes hypothesis scores and returns adjusted values
        based on conflict analysis.
        
        Args:
            conflict_score: Already calculated conflict score
            confidence: Current confidence score
            reliability: Current reliability score
            execution_state: Current execution state
            alpha_support: Alpha layer support value
            regime_support: Regime layer support value
            microstructure_support: Microstructure layer support value
            hypothesis_type: Type of hypothesis
        
        Returns:
            ConflictResolutionResult with adjusted values
        """
        # 1. Detect conflict state
        conflict_state = self.detect_conflict_state(conflict_score)
        
        # 2. Adjust confidence
        adjusted_confidence = self.adjust_confidence(confidence, conflict_state)
        
        # 3. Adjust reliability
        adjusted_reliability = self.adjust_reliability(reliability, conflict_state)
        
        # 4. Adjust execution state
        adjusted_execution_state = self.adjust_execution_state(
            execution_state, conflict_state
        )
        
        # 5. Generate reason suffix
        reason_suffix = self.generate_conflict_reason(
            conflict_state=conflict_state,
            alpha_support=alpha_support,
            regime_support=regime_support,
            microstructure_support=microstructure_support,
            hypothesis_type=hypothesis_type,
        )
        
        return ConflictResolutionResult(
            conflict_state=conflict_state,
            adjusted_confidence=adjusted_confidence,
            adjusted_reliability=adjusted_reliability,
            adjusted_execution_state=adjusted_execution_state,
            reason_suffix=reason_suffix,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 7. Helper: Should Block Trade
    # ═══════════════════════════════════════════════════════════
    
    def should_block_trade(self, conflict_state: ConflictState) -> bool:
        """
        Determine if trading should be blocked due to conflict.
        
        HIGH_CONFLICT → Block trade
        Otherwise → Allow (with reduced confidence)
        """
        return conflict_state == ConflictState.HIGH
    
    # ═══════════════════════════════════════════════════════════
    # 8. Helper: Get Conflict Severity
    # ═══════════════════════════════════════════════════════════
    
    def get_conflict_severity(self, conflict_score: float) -> float:
        """
        Get normalized conflict severity [0, 1].
        
        Maps conflict_score to severity where:
        0.0 → no conflict
        0.25+ → full conflict
        """
        if conflict_score < CONFLICT_LOW_THRESHOLD:
            return 0.0
        elif conflict_score >= CONFLICT_HIGH_THRESHOLD:
            return 1.0
        else:
            # Linear interpolation between thresholds
            return (conflict_score - CONFLICT_LOW_THRESHOLD) / (
                CONFLICT_HIGH_THRESHOLD - CONFLICT_LOW_THRESHOLD
            )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_conflict_resolver: Optional[HypothesisConflictResolver] = None


def get_hypothesis_conflict_resolver() -> HypothesisConflictResolver:
    """Get singleton instance of HypothesisConflictResolver."""
    global _conflict_resolver
    if _conflict_resolver is None:
        _conflict_resolver = HypothesisConflictResolver()
    return _conflict_resolver
