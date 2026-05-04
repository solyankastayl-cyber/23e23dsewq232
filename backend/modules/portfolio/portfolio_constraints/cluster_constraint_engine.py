"""
PHASE 18.2 — Cluster Constraint Engine
======================================
Checks cluster concentration constraints.

Soft constraint:
- max_cluster_exposure = 0.65

Violation results in SOFT_LIMIT (allowed with penalty).
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintViolation,
    ViolationType,
    ConstraintType,
    CLUSTER_LIMITS,
)


class ClusterConstraintEngine:
    """
    Cluster Constraint Engine - PHASE 18.2 STEP 3
    
    Checks if any cluster exceeds concentration limit.
    This is a SOFT constraint - can violate with penalty.
    
    Example:
        btc_cluster = 0.70
        max_cluster_exposure = 0.65
        → cluster_violation = True
    """
    
    def __init__(self):
        self.max_cluster_exposure = CLUSTER_LIMITS["max_cluster_exposure"]
    
    def check_constraints(
        self,
        cluster_exposure: Dict[str, float],
    ) -> Tuple[bool, List[ConstraintViolation]]:
        """
        Check cluster constraints.
        
        Args:
            cluster_exposure: Dict mapping cluster name to exposure (0-1)
        
        Returns:
            Tuple of (has_violation, list of violations)
        """
        violations = []
        
        for cluster, exposure in cluster_exposure.items():
            if exposure > self.max_cluster_exposure:
                severity = (exposure - self.max_cluster_exposure) / self.max_cluster_exposure
                violations.append(ConstraintViolation(
                    violation_type=ViolationType.CLUSTER,
                    constraint_type=ConstraintType.SOFT,
                    current_value=exposure,
                    limit_value=self.max_cluster_exposure,
                    severity=min(severity, 1.0),
                    description=f"Cluster '{cluster}' exposure {exposure:.2f} exceeds max {self.max_cluster_exposure}",
                ))
        
        has_violation = len(violations) > 0
        return has_violation, violations
    
    def get_most_concentrated_cluster(
        self,
        cluster_exposure: Dict[str, float],
    ) -> Tuple[str, float]:
        """Get the cluster with highest exposure."""
        if not cluster_exposure:
            return "", 0.0
        
        max_cluster = max(cluster_exposure.items(), key=lambda x: x[1])
        return max_cluster[0], max_cluster[1]
    
    def get_constraint_values(
        self,
        cluster_exposure: Dict[str, float],
    ) -> Dict:
        """Get constraint values for reporting."""
        result = {}
        for cluster, exposure in cluster_exposure.items():
            result[cluster] = {
                "current": exposure,
                "limit": self.max_cluster_exposure,
                "headroom": max(0, self.max_cluster_exposure - exposure),
                "utilization": exposure / self.max_cluster_exposure,
                "violation": exposure > self.max_cluster_exposure,
            }
        return result


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ClusterConstraintEngine] = None


def get_cluster_constraint_engine() -> ClusterConstraintEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ClusterConstraintEngine()
    return _engine
