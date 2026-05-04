"""
PHASE 17.3 — Promotion Engine
==============================
Evaluates factor promotion readiness.

Promotion requires:
- High governance score
- Ecology not stressed
- Low rollback risk
- High shadow readiness
"""

from typing import Dict, Optional
from modules.research_control.deployment_governance.deployment_governance_types import (
    DeploymentDimension,
    DeploymentDimensionResult,
    DeploymentState,
    GovernanceAction,
    DEPLOYMENT_THRESHOLDS,
)


class PromotionEngine:
    """
    Promotion Engine - PHASE 17.3
    
    Evaluates factor promotion readiness from SHADOW/CANDIDATE to LIVE.
    """
    
    def __init__(self):
        pass
    
    def calculate_promotion_readiness(
        self,
        factor_name: str,
        deployment_score: float,
        shadow_readiness: float,
        rollback_risk: float,
        current_state: DeploymentState,
        factor_governance_state: str,
        ecology_state: str,
    ) -> Dict[str, any]:
        """
        Calculate promotion readiness and recommended action.
        
        Returns:
            Dict with promotion readiness, can_promote flag, and recommended action
        """
        # Base promotion readiness from deployment score
        promotion_readiness = deployment_score
        
        # Adjust based on shadow readiness
        if shadow_readiness >= 0.80:
            promotion_readiness += 0.10
        elif shadow_readiness >= 0.65:
            promotion_readiness += 0.05
        elif shadow_readiness < 0.50:
            promotion_readiness -= 0.10
        
        # Adjust based on rollback risk
        if rollback_risk > 0.50:
            promotion_readiness -= 0.15
        elif rollback_risk > 0.35:
            promotion_readiness -= 0.08
        elif rollback_risk < 0.20:
            promotion_readiness += 0.05
        
        # State-based adjustments
        if factor_governance_state == "ELITE":
            promotion_readiness += 0.08
        elif factor_governance_state == "DEGRADED":
            promotion_readiness -= 0.15
        elif factor_governance_state == "RETIRE":
            promotion_readiness = 0.0
        
        if ecology_state in ["STRESSED", "CRITICAL"]:
            promotion_readiness -= 0.12
        
        promotion_readiness = max(0.0, min(1.0, promotion_readiness))
        
        # Determine if can promote
        can_promote = (
            promotion_readiness >= DEPLOYMENT_THRESHOLDS["promotion_score_min"] and
            shadow_readiness >= DEPLOYMENT_THRESHOLDS["shadow_readiness_min"] and
            rollback_risk <= DEPLOYMENT_THRESHOLDS["rollback_risk_max"] and
            factor_governance_state not in ["DEGRADED", "RETIRE"] and
            ecology_state not in ["CRITICAL"]
        )
        
        # Determine recommended action
        if current_state == DeploymentState.RETIRED:
            action = GovernanceAction.RETIRE
            reason = "Factor is retired"
        elif promotion_readiness < DEPLOYMENT_THRESHOLDS["retire_threshold"]:
            action = GovernanceAction.RETIRE
            reason = "Factor should be retired"
        elif promotion_readiness < DEPLOYMENT_THRESHOLDS["rollback_threshold"]:
            action = GovernanceAction.ROLLBACK
            reason = "Factor requires rollback"
        elif promotion_readiness < DEPLOYMENT_THRESHOLDS["reduce_threshold"]:
            action = GovernanceAction.REDUCE
            reason = "Factor requires capital reduction"
        elif can_promote:
            action = GovernanceAction.PROMOTE
            reason = "Factor ready for promotion"
        elif current_state == DeploymentState.SHADOW:
            action = GovernanceAction.KEEP_SHADOW
            reason = "Continue shadow monitoring"
        else:
            action = GovernanceAction.HOLD
            reason = "Maintain current state"
        
        return {
            "promotion_readiness": promotion_readiness,
            "can_promote": can_promote,
            "recommended_action": action,
            "reason": reason,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[PromotionEngine] = None


def get_promotion_engine() -> PromotionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PromotionEngine()
    return _engine
