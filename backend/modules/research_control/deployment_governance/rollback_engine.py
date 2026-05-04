"""
PHASE 17.3 — Rollback Engine
=============================
Evaluates rollback risk for deployed factors.

Rollback risk is high when:
- Factor governance degraded
- Ecology critical
- Interaction critical
- Recent instability
"""

from typing import Dict, Optional
from modules.research_control.deployment_governance.deployment_governance_types import (
    DeploymentDimension,
    DeploymentDimensionResult,
    DeploymentState,
    DEPLOYMENT_THRESHOLDS,
)


class RollbackEngine:
    """
    Rollback Engine - PHASE 17.3
    
    Evaluates rollback risk for deployed factors.
    """
    
    def __init__(self):
        pass
    
    def calculate_rollback_risk(
        self,
        factor_name: str,
        factor_governance_score: float,
        factor_governance_state: str,
        ecology_score: float,
        ecology_state: str,
        interaction_score: float,  # -1 to 1
        interaction_state: str,
        recent_errors: int,
        current_state: DeploymentState,
    ) -> float:
        """
        Calculate rollback risk score (0-1, higher = more risk).
        
        Rollback risk increases when:
        - Factor governance is degraded
        - Ecology is critical
        - Interaction is critical
        - Recent errors occurred
        """
        # Base risk from governance (inverted - low score = high risk)
        governance_risk = max(0.0, 1.0 - factor_governance_score)
        
        # Ecology risk
        ecology_risk = max(0.0, 1.0 - ecology_score)
        
        # Interaction risk (normalized from -1..1)
        # Negative interaction = higher risk
        interaction_risk = max(0.0, (1.0 - interaction_score) / 2)
        
        # State-based risk multipliers
        state_risk_multiplier = 1.0
        if factor_governance_state == "RETIRE":
            state_risk_multiplier = 1.5
        elif factor_governance_state == "DEGRADED":
            state_risk_multiplier = 1.3
        elif factor_governance_state == "WATCHLIST":
            state_risk_multiplier = 1.1
        
        ecology_risk_multiplier = 1.0
        if ecology_state == "CRITICAL":
            ecology_risk_multiplier = 1.5
        elif ecology_state == "STRESSED":
            ecology_risk_multiplier = 1.2
        
        interaction_risk_multiplier = 1.0
        if interaction_state == "CRITICAL":
            interaction_risk_multiplier = 1.4
        elif interaction_state == "NEGATIVE":
            interaction_risk_multiplier = 1.15
        
        # Error-based risk
        error_risk = min(0.3, recent_errors * 0.05)
        
        # Combined rollback risk
        rollback_risk = (
            0.35 * governance_risk * state_risk_multiplier +
            0.25 * ecology_risk * ecology_risk_multiplier +
            0.20 * interaction_risk * interaction_risk_multiplier +
            0.20 * error_risk
        )
        
        # Deployment state adjustments
        if current_state == DeploymentState.LIVE:
            # Live factors have slightly higher base risk
            rollback_risk *= 1.05
        elif current_state == DeploymentState.SHADOW:
            # Shadow factors have lower risk (can't lose money)
            rollback_risk *= 0.8
        
        return max(0.0, min(1.0, rollback_risk))
    
    def should_rollback(
        self,
        rollback_risk: float,
        current_state: DeploymentState,
    ) -> bool:
        """
        Determine if rollback is recommended.
        """
        if current_state == DeploymentState.SHADOW:
            return False  # Can't rollback shadow
        
        return rollback_risk > 0.60


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[RollbackEngine] = None


def get_rollback_engine() -> RollbackEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = RollbackEngine()
    return _engine
