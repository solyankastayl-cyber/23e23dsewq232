"""
PHASE 17.3 — Shadow Mode Engine
================================
Evaluates shadow mode readiness and effectiveness.

Shadow readiness depends on:
- Factor governance quality
- Ecology stability
- Interaction state
- Shadow duration sufficiency
"""

from typing import Dict, Optional
from modules.research_control.deployment_governance.deployment_governance_types import (
    DeploymentDimension,
    DeploymentDimensionResult,
    DeploymentState,
    DEPLOYMENT_THRESHOLDS,
)


class ShadowModeEngine:
    """
    Shadow Mode Engine - PHASE 17.3
    
    Evaluates shadow mode readiness and effectiveness.
    """
    
    def __init__(self):
        pass
    
    def calculate_shadow_readiness(
        self,
        factor_name: str,
        factor_governance_score: float,
        factor_governance_state: str,
        ecology_score: float,
        ecology_state: str,
        interaction_score: float,  # -1 to 1
        interaction_state: str,
        shadow_duration_days: float,
    ) -> DeploymentDimensionResult:
        """
        Calculate shadow readiness score.
        
        Shadow readiness is high when:
        - Factor governance is good
        - Ecology is stable
        - Interaction is not critical
        - Shadow duration is sufficient
        """
        # Normalize interaction score from -1..1 to 0..1
        interaction_normalized = (interaction_score + 1) / 2
        
        # Duration factor (0 to 1)
        optimal_days = DEPLOYMENT_THRESHOLDS["optimal_shadow_days"]
        min_days = DEPLOYMENT_THRESHOLDS["min_shadow_days"]
        
        if shadow_duration_days >= optimal_days:
            duration_factor = 1.0
        elif shadow_duration_days >= min_days:
            duration_factor = 0.5 + 0.5 * ((shadow_duration_days - min_days) / (optimal_days - min_days))
        else:
            duration_factor = 0.5 * (shadow_duration_days / min_days)
        
        # State factors
        factor_state_bonus = self._get_state_bonus(factor_governance_state)
        ecology_state_bonus = self._get_ecology_state_bonus(ecology_state)
        interaction_penalty = self._get_interaction_penalty(interaction_state)
        
        # Calculate shadow readiness
        shadow_readiness = (
            0.35 * factor_governance_score +
            0.25 * ecology_score +
            0.15 * interaction_normalized +
            0.25 * duration_factor +
            factor_state_bonus +
            ecology_state_bonus -
            interaction_penalty
        )
        shadow_readiness = max(0.0, min(1.0, shadow_readiness))
        
        # Determine status
        if shadow_readiness >= 0.75:
            status = "READY"
            reason = "Ready for promotion consideration"
        elif shadow_readiness >= 0.55:
            status = "CAUTION"
            reason = "Continue shadow monitoring"
        else:
            status = "NOT_READY"
            reason = "Not ready for promotion"
        
        return DeploymentDimensionResult(
            dimension=DeploymentDimension.SHADOW_READINESS,
            score=shadow_readiness,
            status=status,
            reason=reason,
            inputs={
                "factor_governance_score": round(factor_governance_score, 4),
                "ecology_score": round(ecology_score, 4),
                "interaction_normalized": round(interaction_normalized, 4),
                "duration_factor": round(duration_factor, 4),
                "shadow_duration_days": round(shadow_duration_days, 1),
            },
        )
    
    def _get_state_bonus(self, factor_state: str) -> float:
        """Get bonus/penalty based on factor governance state."""
        bonuses = {
            "ELITE": 0.10,
            "STABLE": 0.05,
            "WATCHLIST": 0.00,
            "DEGRADED": -0.10,
            "RETIRE": -0.20,
        }
        return bonuses.get(factor_state, 0.0)
    
    def _get_ecology_state_bonus(self, ecology_state: str) -> float:
        """Get bonus/penalty based on ecology state."""
        bonuses = {
            "OPTIMAL": 0.08,
            "STABLE": 0.04,
            "TRANSITIONING": 0.00,
            "STRESSED": -0.08,
            "CRITICAL": -0.15,
        }
        return bonuses.get(ecology_state, 0.0)
    
    def _get_interaction_penalty(self, interaction_state: str) -> float:
        """Get penalty based on interaction state."""
        penalties = {
            "STRONG_POSITIVE": 0.00,
            "POSITIVE": 0.00,
            "NEUTRAL": 0.02,
            "NEGATIVE": 0.08,
            "CRITICAL": 0.20,
        }
        return penalties.get(interaction_state, 0.05)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[ShadowModeEngine] = None


def get_shadow_engine() -> ShadowModeEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ShadowModeEngine()
    return _engine
