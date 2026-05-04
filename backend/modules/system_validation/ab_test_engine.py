"""
PHASE 25.6 — A/B Test Engine

Core engine for A/B/C system comparison.

Compares:
- System A: TA + Exchange (baseline)
- System B: TA + Exchange + Fractal
- System C: TA + Exchange + Fractal + Macro

Validates that Macro-Fractal layer does NOT break core signals.
"""

from typing import Optional, Tuple
from datetime import datetime

from .ab_test_types import (
    SystemComparison,
    SystemComparisonSummary,
    SystemValidationHealth,
    SystemOutput,
    ValidationState,
    DirectionType,
    CONFIDENCE_DRIFT_THRESHOLD,
    CAPITAL_DRIFT_THRESHOLD,
    SYSTEM_A_CONFIG,
    SYSTEM_B_CONFIG,
    SYSTEM_C_CONFIG,
)


class ABTestEngine:
    """
    A/B/C Test Engine for system validation.
    
    Key assertions:
    - Direction MUST NOT change across systems
    - Strategy MUST NOT change across systems
    - Drift must be within acceptable bounds
    """
    
    def __init__(self):
        self._last_comparison: Optional[SystemComparison] = None
    
    def compare(
        self,
        system_a: SystemOutput,
        system_b: SystemOutput,
        system_c: SystemOutput,
    ) -> SystemComparison:
        """
        Compare three system configurations.
        
        Args:
            system_a: Output from TA + Exchange
            system_b: Output from TA + Exchange + Fractal
            system_c: Output from TA + Exchange + Fractal + Macro
        
        Returns:
            SystemComparison with validation result
        """
        
        # Check direction consistency
        direction_consistency = self._check_direction_consistency(
            system_a.direction,
            system_b.direction,
            system_c.direction,
        )
        
        # Check strategy consistency
        strategy_consistency = self._check_strategy_consistency(
            system_a.strategy,
            system_b.strategy,
            system_c.strategy,
        )
        
        # Calculate drifts
        confidence_drift = abs(system_c.confidence - system_a.confidence)
        capital_drift = abs(system_c.capital_modifier - system_a.capital_modifier)
        
        # Determine validation state
        validation_state, reason = self._determine_validation_state(
            direction_consistency,
            strategy_consistency,
            confidence_drift,
            capital_drift,
            system_a,
            system_c,
        )
        
        comparison = SystemComparison(
            # Directions
            system_a_direction=system_a.direction,
            system_b_direction=system_b.direction,
            system_c_direction=system_c.direction,
            
            # Strategies
            system_a_strategy=system_a.strategy,
            system_b_strategy=system_b.strategy,
            system_c_strategy=system_c.strategy,
            
            # Confidences
            system_a_confidence=round(system_a.confidence, 4),
            system_b_confidence=round(system_b.confidence, 4),
            system_c_confidence=round(system_c.confidence, 4),
            
            # Capitals
            system_a_capital=round(system_a.capital_modifier, 4),
            system_b_capital=round(system_b.capital_modifier, 4),
            system_c_capital=round(system_c.capital_modifier, 4),
            
            # Drifts
            confidence_drift=round(confidence_drift, 4),
            capital_drift=round(capital_drift, 4),
            
            # Consistency
            direction_consistency=direction_consistency,
            strategy_consistency=strategy_consistency,
            
            # Result
            validation_state=validation_state,
            reason=reason,
            
            timestamp=datetime.utcnow(),
        )
        
        self._last_comparison = comparison
        return comparison
    
    # ═══════════════════════════════════════════════════════════
    # Consistency Checks
    # ═══════════════════════════════════════════════════════════
    
    def _check_direction_consistency(
        self,
        dir_a: DirectionType,
        dir_b: DirectionType,
        dir_c: DirectionType,
    ) -> bool:
        """Check that direction is consistent across all systems."""
        return dir_a == dir_b == dir_c
    
    def _check_strategy_consistency(
        self,
        strat_a: str,
        strat_b: str,
        strat_c: str,
    ) -> bool:
        """Check that strategy is consistent across all systems."""
        return strat_a == strat_b == strat_c
    
    # ═══════════════════════════════════════════════════════════
    # Validation State
    # ═══════════════════════════════════════════════════════════
    
    def _determine_validation_state(
        self,
        direction_consistency: bool,
        strategy_consistency: bool,
        confidence_drift: float,
        capital_drift: float,
        system_a: SystemOutput,
        system_c: SystemOutput,
    ) -> Tuple[ValidationState, str]:
        """
        Determine validation state based on checks.
        
        Rules:
        - FAILED: direction changed OR strategy changed
        - WARNING: drift exceeds thresholds
        - PASSED: all checks pass
        """
        
        # FAILED: direction changed
        if not direction_consistency:
            return "FAILED", f"direction changed across systems (A={system_a.direction}, C={system_c.direction})"
        
        # FAILED: strategy changed
        if not strategy_consistency:
            return "FAILED", f"strategy changed across systems (A={system_a.strategy}, C={system_c.strategy})"
        
        # WARNING: confidence drift too high
        if confidence_drift > CONFIDENCE_DRIFT_THRESHOLD:
            return "WARNING", f"confidence drift {confidence_drift:.2f} exceeds threshold {CONFIDENCE_DRIFT_THRESHOLD}"
        
        # WARNING: capital drift too high
        if capital_drift > CAPITAL_DRIFT_THRESHOLD:
            return "WARNING", f"capital drift {capital_drift:.2f} exceeds threshold {CAPITAL_DRIFT_THRESHOLD}"
        
        # PASSED
        return "PASSED", "macro-fractal context improves confidence without altering core signals"
    
    # ═══════════════════════════════════════════════════════════
    # Summary & Health
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, comparison: SystemComparison) -> SystemComparisonSummary:
        """Get compact summary."""
        return SystemComparisonSummary(
            system_a_confidence=comparison.system_a_confidence,
            system_b_confidence=comparison.system_b_confidence,
            system_c_confidence=comparison.system_c_confidence,
            system_a_capital=comparison.system_a_capital,
            system_b_capital=comparison.system_b_capital,
            system_c_capital=comparison.system_c_capital,
            confidence_drift=comparison.confidence_drift,
            capital_drift=comparison.capital_drift,
            direction_consistency=comparison.direction_consistency,
            strategy_consistency=comparison.strategy_consistency,
            validation_state=comparison.validation_state,
            reason=comparison.reason,
        )
    
    def get_health(self) -> SystemValidationHealth:
        """Get health status."""
        if self._last_comparison is None:
            return SystemValidationHealth(
                status="ERROR",
                system_a_available=False,
                system_b_available=False,
                system_c_available=False,
                last_validation=None,
                last_update=None,
            )
        
        comp = self._last_comparison
        
        # All systems always available in comparison
        return SystemValidationHealth(
            status="OK",
            system_a_available=True,
            system_b_available=True,
            system_c_available=True,
            last_validation=comp.validation_state,
            last_update=comp.timestamp,
        )


# Singleton
_engine: Optional[ABTestEngine] = None


def get_ab_test_engine() -> ABTestEngine:
    """Get singleton instance of ABTestEngine."""
    global _engine
    if _engine is None:
        _engine = ABTestEngine()
    return _engine
