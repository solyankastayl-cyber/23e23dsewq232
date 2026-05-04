"""
PHASE 18.2 — Factor Constraint Engine
=====================================
Checks factor concentration constraints.

Soft constraint:
- max_factor_exposure = 0.70

Violation results in SOFT_LIMIT (allowed with penalty).
Protects against trend-only or momentum-only portfolios.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintViolation,
    ViolationType,
    ConstraintType,
    FACTOR_LIMITS,
)


class FactorConstraintEngine:
    """
    Factor Constraint Engine - PHASE 18.2 STEP 4
    
    Checks if any factor exceeds concentration limit.
    This is a SOFT constraint - can violate with penalty.
    
    Protection against:
    - trend-only portfolio
    - momentum-only portfolio
    - single factor dominance
    """
    
    def __init__(self):
        self.max_factor_exposure = FACTOR_LIMITS["max_factor_exposure"]
    
    def check_constraints(
        self,
        factor_exposure: Dict[str, float],
    ) -> Tuple[bool, List[ConstraintViolation]]:
        """
        Check factor constraints.
        
        Args:
            factor_exposure: Dict mapping factor name to exposure (0-1)
        
        Returns:
            Tuple of (has_violation, list of violations)
        """
        violations = []
        
        for factor, exposure in factor_exposure.items():
            if exposure > self.max_factor_exposure:
                severity = (exposure - self.max_factor_exposure) / self.max_factor_exposure
                violations.append(ConstraintViolation(
                    violation_type=ViolationType.FACTOR,
                    constraint_type=ConstraintType.SOFT,
                    current_value=exposure,
                    limit_value=self.max_factor_exposure,
                    severity=min(severity, 1.0),
                    description=f"Factor '{factor}' exposure {exposure:.2f} exceeds max {self.max_factor_exposure}",
                ))
        
        has_violation = len(violations) > 0
        return has_violation, violations
    
    def get_dominant_factor(
        self,
        factor_exposure: Dict[str, float],
    ) -> Tuple[str, float]:
        """Get the factor with highest exposure."""
        if not factor_exposure:
            return "", 0.0
        
        max_factor = max(factor_exposure.items(), key=lambda x: x[1])
        return max_factor[0], max_factor[1]
    
    def get_constraint_values(
        self,
        factor_exposure: Dict[str, float],
    ) -> Dict:
        """Get constraint values for reporting."""
        result = {}
        for factor, exposure in factor_exposure.items():
            result[factor] = {
                "current": exposure,
                "limit": self.max_factor_exposure,
                "headroom": max(0, self.max_factor_exposure - exposure),
                "utilization": exposure / self.max_factor_exposure,
                "violation": exposure > self.max_factor_exposure,
            }
        return result


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[FactorConstraintEngine] = None


def get_factor_constraint_engine() -> FactorConstraintEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorConstraintEngine()
    return _engine
