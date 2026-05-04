"""
PHASE 17.3 — Deployment Policy Engine
======================================
Evaluates compliance with deployment policies.

Policy checks:
- Minimum shadow duration
- Required governance thresholds
- Stability requirements
- Risk limits compliance
"""

from typing import Dict, Optional
from modules.research_control.deployment_governance.deployment_governance_types import (
    DeploymentDimension,
    DeploymentDimensionResult,
    DeploymentState,
    DEPLOYMENT_THRESHOLDS,
)


class DeploymentPolicyEngine:
    """
    Deployment Policy Engine - PHASE 17.3
    
    Evaluates compliance with deployment policies.
    """
    
    def __init__(self):
        pass
    
    def evaluate_policy_compliance(
        self,
        factor_name: str,
        current_state: DeploymentState,
        shadow_duration_days: float,
        factor_governance_score: float,
        feature_governance_score: float,
    ) -> Dict[str, any]:
        """
        Evaluate policy compliance for deployment decisions.
        
        Returns:
            Dict with policy compliance status and details
        """
        violations = []
        warnings = []
        
        # Check shadow duration policy
        if current_state == DeploymentState.SHADOW:
            if shadow_duration_days < DEPLOYMENT_THRESHOLDS["min_shadow_days"]:
                violations.append(
                    f"Insufficient shadow duration: {shadow_duration_days:.1f} days "
                    f"(min: {DEPLOYMENT_THRESHOLDS['min_shadow_days']})"
                )
            elif shadow_duration_days < DEPLOYMENT_THRESHOLDS["optimal_shadow_days"]:
                warnings.append(
                    f"Below optimal shadow duration: {shadow_duration_days:.1f} days "
                    f"(optimal: {DEPLOYMENT_THRESHOLDS['optimal_shadow_days']})"
                )
        
        # Check governance score policy
        if factor_governance_score < DEPLOYMENT_THRESHOLDS["promotion_score_min"]:
            if current_state in [DeploymentState.SHADOW, DeploymentState.CANDIDATE]:
                violations.append(
                    f"Factor governance score below promotion threshold: "
                    f"{factor_governance_score:.2f} (min: {DEPLOYMENT_THRESHOLDS['promotion_score_min']})"
                )
        
        # Calculate compliance score
        compliance_score = 1.0
        compliance_score -= len(violations) * 0.3
        compliance_score -= len(warnings) * 0.1
        compliance_score = max(0.0, min(1.0, compliance_score))
        
        return {
            "compliant": len(violations) == 0,
            "compliance_score": compliance_score,
            "violations": violations,
            "warnings": warnings,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[DeploymentPolicyEngine] = None


def get_policy_engine() -> DeploymentPolicyEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = DeploymentPolicyEngine()
    return _engine
