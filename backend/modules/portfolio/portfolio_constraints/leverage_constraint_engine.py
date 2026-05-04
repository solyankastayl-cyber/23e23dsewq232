"""
PHASE 18.2 — Leverage Constraint Engine
=======================================
Checks leverage constraints.

Hard constraint:
- max_leverage = 2.5

Violation results in HARD_LIMIT (not allowed).
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintViolation,
    ViolationType,
    ConstraintType,
    LEVERAGE_LIMITS,
)


class LeverageConstraintEngine:
    """
    Leverage Constraint Engine - PHASE 18.2 STEP 5
    
    Checks if leverage (gross exposure) exceeds limit.
    This is a HARD constraint - cannot be violated.
    """
    
    def __init__(self):
        self.max_leverage = LEVERAGE_LIMITS["max_leverage"]
    
    def check_constraints(
        self,
        gross_exposure: float,
    ) -> Tuple[bool, List[ConstraintViolation]]:
        """
        Check leverage constraints.
        
        Args:
            gross_exposure: Current gross exposure (used as leverage proxy)
        
        Returns:
            Tuple of (has_violation, list of violations)
        """
        violations = []
        
        if gross_exposure > self.max_leverage:
            severity = (gross_exposure - self.max_leverage) / self.max_leverage
            violations.append(ConstraintViolation(
                violation_type=ViolationType.LEVERAGE,
                constraint_type=ConstraintType.HARD,
                current_value=gross_exposure,
                limit_value=self.max_leverage,
                severity=min(severity, 1.0),
                description=f"Leverage {gross_exposure:.2f} exceeds max {self.max_leverage}",
            ))
        
        has_violation = len(violations) > 0
        return has_violation, violations
    
    def get_constraint_values(
        self,
        gross_exposure: float,
    ) -> Dict:
        """Get constraint values for reporting."""
        return {
            "leverage": {
                "current": gross_exposure,
                "limit": self.max_leverage,
                "headroom": max(0, self.max_leverage - gross_exposure),
                "utilization": gross_exposure / self.max_leverage,
                "violation": gross_exposure > self.max_leverage,
            },
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[LeverageConstraintEngine] = None


def get_leverage_constraint_engine() -> LeverageConstraintEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = LeverageConstraintEngine()
    return _engine
