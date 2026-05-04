"""
PHASE 18.2 — Exposure Constraint Engine
=======================================
Checks net and gross exposure constraints.

Hard constraints:
- max_net_exposure = 1.5
- max_gross_exposure = 2.5

Violation of these constraints results in HARD_LIMIT.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintViolation,
    ViolationType,
    ConstraintType,
    EXPOSURE_LIMITS,
)


class ExposureConstraintEngine:
    """
    Exposure Constraint Engine - PHASE 18.2 STEP 2
    
    Checks if net/gross exposure exceeds limits.
    These are HARD constraints - cannot be violated.
    """
    
    def __init__(self):
        self.max_net_exposure = EXPOSURE_LIMITS["max_net_exposure"]
        self.max_gross_exposure = EXPOSURE_LIMITS["max_gross_exposure"]
    
    def check_constraints(
        self,
        net_exposure: float,
        gross_exposure: float,
    ) -> Tuple[bool, List[ConstraintViolation]]:
        """
        Check exposure constraints.
        
        Args:
            net_exposure: Current net exposure
            gross_exposure: Current gross exposure
        
        Returns:
            Tuple of (has_violation, list of violations)
        """
        violations = []
        
        # Check net exposure (absolute value)
        abs_net = abs(net_exposure)
        if abs_net > self.max_net_exposure:
            severity = (abs_net - self.max_net_exposure) / self.max_net_exposure
            violations.append(ConstraintViolation(
                violation_type=ViolationType.EXPOSURE,
                constraint_type=ConstraintType.HARD,
                current_value=abs_net,
                limit_value=self.max_net_exposure,
                severity=min(severity, 1.0),
                description=f"Net exposure {abs_net:.2f} exceeds max {self.max_net_exposure}",
            ))
        
        # Check gross exposure
        if gross_exposure > self.max_gross_exposure:
            severity = (gross_exposure - self.max_gross_exposure) / self.max_gross_exposure
            violations.append(ConstraintViolation(
                violation_type=ViolationType.EXPOSURE,
                constraint_type=ConstraintType.HARD,
                current_value=gross_exposure,
                limit_value=self.max_gross_exposure,
                severity=min(severity, 1.0),
                description=f"Gross exposure {gross_exposure:.2f} exceeds max {self.max_gross_exposure}",
            ))
        
        has_violation = len(violations) > 0
        return has_violation, violations
    
    def get_constraint_values(
        self,
        net_exposure: float,
        gross_exposure: float,
    ) -> Dict:
        """Get constraint values for reporting."""
        return {
            "net_exposure": {
                "current": abs(net_exposure),
                "limit": self.max_net_exposure,
                "headroom": max(0, self.max_net_exposure - abs(net_exposure)),
                "utilization": abs(net_exposure) / self.max_net_exposure,
            },
            "gross_exposure": {
                "current": gross_exposure,
                "limit": self.max_gross_exposure,
                "headroom": max(0, self.max_gross_exposure - gross_exposure),
                "utilization": gross_exposure / self.max_gross_exposure,
            },
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ExposureConstraintEngine] = None


def get_exposure_constraint_engine() -> ExposureConstraintEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ExposureConstraintEngine()
    return _engine
