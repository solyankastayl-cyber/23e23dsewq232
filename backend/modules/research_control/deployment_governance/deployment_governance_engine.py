"""
PHASE 17.3 — Deployment Governance Engine
==========================================
Main aggregation engine for deployment lifecycle governance.

Combines inputs from:
- Factor Governance (35%)
- Feature Governance (20%)
- Ecology (20%)
- Interaction (15%)
- Shadow Readiness (10%)

Key Principle:
    Deployment Governance is the FINAL GATE before live trading.
    It controls the factor lifecycle: SHADOW → CANDIDATE → LIVE → FROZEN → RETIRED
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

from modules.research_control.deployment_governance.deployment_governance_types import (
    DeploymentGovernanceResult,
    DeploymentState,
    GovernanceAction,
    DeploymentDimension,
    DeploymentDimensionResult,
    DEPLOYMENT_THRESHOLDS,
    DEPLOYMENT_WEIGHTS,
    DEPLOYMENT_MODIFIERS,
)
from modules.research_control.deployment_governance.deployment_policy_engine import get_policy_engine
from modules.research_control.deployment_governance.shadow_mode_engine import get_shadow_engine
from modules.research_control.deployment_governance.promotion_engine import get_promotion_engine
from modules.research_control.deployment_governance.rollback_engine import get_rollback_engine

# Import governance engines
from modules.research_control.factor_governance.factor_governance_engine import get_factor_governance_engine
from modules.research_control.feature_governance.feature_governance_engine import get_feature_governance_engine


# ══════════════════════════════════════════════════════════════
# KNOWN FACTORS WITH DEPLOYMENT STATE
# ══════════════════════════════════════════════════════════════

FACTOR_DEPLOYMENT_STATE = {
    "trend_breakout_factor": {
        "current_state": DeploymentState.SHADOW,
        "shadow_duration_days": 45,
        "recent_errors": 0,
    },
    "mean_reversion_factor": {
        "current_state": DeploymentState.CANDIDATE,
        "shadow_duration_days": 60,
        "recent_errors": 1,
    },
    "funding_arb_factor": {
        "current_state": DeploymentState.LIVE,
        "shadow_duration_days": 90,
        "recent_errors": 0,
    },
    "liquidation_cascade_factor": {
        "current_state": DeploymentState.SHADOW,
        "shadow_duration_days": 15,
        "recent_errors": 2,
    },
    "structure_break_factor": {
        "current_state": DeploymentState.CANDIDATE,
        "shadow_duration_days": 35,
        "recent_errors": 0,
    },
    "divergence_factor": {
        "current_state": DeploymentState.LIVE,
        "shadow_duration_days": 120,
        "recent_errors": 1,
    },
    "flow_imbalance_factor": {
        "current_state": DeploymentState.SHADOW,
        "shadow_duration_days": 10,
        "recent_errors": 0,
    },
    "volatility_regime_factor": {
        "current_state": DeploymentState.CANDIDATE,
        "shadow_duration_days": 55,
        "recent_errors": 0,
    },
    "dominance_shift_factor": {
        "current_state": DeploymentState.FROZEN,
        "shadow_duration_days": 80,
        "recent_errors": 5,
    },
    "cross_asset_factor": {
        "current_state": DeploymentState.SHADOW,
        "shadow_duration_days": 25,
        "recent_errors": 0,
    },
}


# ══════════════════════════════════════════════════════════════
# SIMULATED ECOLOGY AND INTERACTION DATA
# ══════════════════════════════════════════════════════════════

def get_simulated_ecology(factor_name: str) -> Dict:
    """Get simulated ecology data for a factor."""
    # Simulate based on factor characteristics
    base_scores = {
        "trend_breakout_factor": {"score": 0.72, "state": "STABLE"},
        "mean_reversion_factor": {"score": 0.78, "state": "STABLE"},
        "funding_arb_factor": {"score": 0.85, "state": "OPTIMAL"},
        "liquidation_cascade_factor": {"score": 0.55, "state": "STRESSED"},
        "structure_break_factor": {"score": 0.70, "state": "STABLE"},
        "divergence_factor": {"score": 0.65, "state": "TRANSITIONING"},
        "flow_imbalance_factor": {"score": 0.68, "state": "STABLE"},
        "volatility_regime_factor": {"score": 0.75, "state": "STABLE"},
        "dominance_shift_factor": {"score": 0.40, "state": "CRITICAL"},
        "cross_asset_factor": {"score": 0.70, "state": "STABLE"},
    }
    return base_scores.get(factor_name, {"score": 0.65, "state": "STABLE"})


def get_simulated_interaction(factor_name: str) -> Dict:
    """Get simulated interaction data for a factor."""
    base_scores = {
        "trend_breakout_factor": {"score": 0.25, "state": "POSITIVE"},
        "mean_reversion_factor": {"score": 0.30, "state": "POSITIVE"},
        "funding_arb_factor": {"score": 0.45, "state": "STRONG_POSITIVE"},
        "liquidation_cascade_factor": {"score": -0.15, "state": "NEGATIVE"},
        "structure_break_factor": {"score": 0.20, "state": "POSITIVE"},
        "divergence_factor": {"score": 0.05, "state": "NEUTRAL"},
        "flow_imbalance_factor": {"score": 0.15, "state": "POSITIVE"},
        "volatility_regime_factor": {"score": 0.35, "state": "POSITIVE"},
        "dominance_shift_factor": {"score": -0.45, "state": "CRITICAL"},
        "cross_asset_factor": {"score": 0.10, "state": "NEUTRAL"},
    }
    return base_scores.get(factor_name, {"score": 0.0, "state": "NEUTRAL"})


# ══════════════════════════════════════════════════════════════
# DEPLOYMENT GOVERNANCE ENGINE
# ══════════════════════════════════════════════════════════════

class DeploymentGovernanceEngine:
    """
    Deployment Governance Engine - PHASE 17.3
    
    Third layer of Research Control Fabric.
    Controls factor lifecycle and deployment decisions.
    
    Purpose:
        Final gate before live trading.
        Manages SHADOW → CANDIDATE → LIVE → FROZEN → RETIRED lifecycle.
    
    Input Sources:
        - Factor Governance (35%)
        - Feature Governance (20%)
        - Ecology (20%)
        - Interaction (15%)
        - Shadow Readiness (10%)
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Sub-engines
        self.policy_engine = get_policy_engine()
        self.shadow_engine = get_shadow_engine()
        self.promotion_engine = get_promotion_engine()
        self.rollback_engine = get_rollback_engine()
        
        # Governance engines
        self.factor_governance = get_factor_governance_engine()
        self.feature_governance = get_feature_governance_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN EVALUATION
    # ═══════════════════════════════════════════════════════════
    
    def evaluate(self, factor_name: str) -> DeploymentGovernanceResult:
        """
        Evaluate deployment governance for a factor.
        
        Args:
            factor_name: Name of the factor to evaluate
        
        Returns:
            DeploymentGovernanceResult with full deployment assessment
        """
        now = datetime.now(timezone.utc)
        
        # Get deployment state
        deployment_info = self._get_deployment_info(factor_name)
        current_state = deployment_info["current_state"]
        shadow_duration = deployment_info["shadow_duration_days"]
        recent_errors = deployment_info["recent_errors"]
        
        # Get governance inputs
        factor_gov = self.factor_governance.evaluate(factor_name)
        feature_gov = self.feature_governance.evaluate("funding_skew")  # Use representative feature
        ecology = get_simulated_ecology(factor_name)
        interaction = get_simulated_interaction(factor_name)
        
        # Build dimension results
        dimension_results = []
        
        # Factor Governance dimension
        factor_gov_result = DeploymentDimensionResult(
            dimension=DeploymentDimension.FACTOR_GOVERNANCE,
            score=factor_gov.governance_score,
            status=self._score_to_status(factor_gov.governance_score),
            reason=f"Factor state: {factor_gov.governance_state.value}",
            inputs={
                "governance_score": round(factor_gov.governance_score, 4),
                "governance_state": factor_gov.governance_state.value,
                "capital_modifier": round(factor_gov.capital_modifier, 4),
            },
        )
        dimension_results.append(factor_gov_result)
        
        # Feature Governance dimension
        feature_gov_result = DeploymentDimensionResult(
            dimension=DeploymentDimension.FEATURE_GOVERNANCE,
            score=feature_gov.governance_score,
            status=self._score_to_status(feature_gov.governance_score),
            reason=f"Feature state: {feature_gov.governance_state.value}",
            inputs={
                "governance_score": round(feature_gov.governance_score, 4),
                "governance_state": feature_gov.governance_state.value,
            },
        )
        dimension_results.append(feature_gov_result)
        
        # Ecology dimension
        ecology_result = DeploymentDimensionResult(
            dimension=DeploymentDimension.ECOLOGY,
            score=ecology["score"],
            status=self._score_to_status(ecology["score"]),
            reason=f"Ecology state: {ecology['state']}",
            inputs=ecology,
        )
        dimension_results.append(ecology_result)
        
        # Interaction dimension (normalize -1..1 to 0..1)
        interaction_normalized = (interaction["score"] + 1) / 2
        interaction_result = DeploymentDimensionResult(
            dimension=DeploymentDimension.INTERACTION,
            score=interaction_normalized,
            status=self._score_to_status(interaction_normalized),
            reason=f"Interaction state: {interaction['state']}",
            inputs={
                "raw_score": round(interaction["score"], 4),
                "normalized_score": round(interaction_normalized, 4),
                "state": interaction["state"],
            },
        )
        dimension_results.append(interaction_result)
        
        # Shadow Readiness dimension
        shadow_result = self.shadow_engine.calculate_shadow_readiness(
            factor_name=factor_name,
            factor_governance_score=factor_gov.governance_score,
            factor_governance_state=factor_gov.governance_state.value,
            ecology_score=ecology["score"],
            ecology_state=ecology["state"],
            interaction_score=interaction["score"],
            interaction_state=interaction["state"],
            shadow_duration_days=shadow_duration,
        )
        dimension_results.append(shadow_result)
        
        # Calculate deployment score
        deployment_score = self._calculate_deployment_score(
            factor_governance_score=factor_gov.governance_score,
            feature_governance_score=feature_gov.governance_score,
            ecology_score=ecology["score"],
            interaction_score=interaction_normalized,
            shadow_readiness=shadow_result.score,
        )
        
        # Calculate rollback risk
        rollback_risk = self.rollback_engine.calculate_rollback_risk(
            factor_name=factor_name,
            factor_governance_score=factor_gov.governance_score,
            factor_governance_state=factor_gov.governance_state.value,
            ecology_score=ecology["score"],
            ecology_state=ecology["state"],
            interaction_score=interaction["score"],
            interaction_state=interaction["state"],
            recent_errors=recent_errors,
            current_state=current_state,
        )
        
        # Calculate promotion readiness and get action
        promotion_result = self.promotion_engine.calculate_promotion_readiness(
            factor_name=factor_name,
            deployment_score=deployment_score,
            shadow_readiness=shadow_result.score,
            rollback_risk=rollback_risk,
            current_state=current_state,
            factor_governance_state=factor_gov.governance_state.value,
            ecology_state=ecology["state"],
        )
        
        promotion_readiness = promotion_result["promotion_readiness"]
        governance_action = promotion_result["recommended_action"]
        reason = promotion_result["reason"]
        
        # Get modifiers
        modifiers = DEPLOYMENT_MODIFIERS[governance_action]
        capital_modifier = modifiers["capital_modifier"]
        confidence_modifier = modifiers["confidence_modifier"]
        
        # Find extremes
        weakest, strongest = self._find_extremes(dimension_results)
        
        # Build drivers
        drivers = self._build_drivers(
            factor_name=factor_name,
            current_state=current_state,
            dimension_results=dimension_results,
            governance_action=governance_action,
        )
        
        return DeploymentGovernanceResult(
            factor_name=factor_name,
            timestamp=now,
            deployment_state=current_state,
            deployment_score=deployment_score,
            shadow_readiness=shadow_result.score,
            promotion_readiness=promotion_readiness,
            rollback_risk=rollback_risk,
            governance_action=governance_action,
            capital_modifier=capital_modifier,
            confidence_modifier=confidence_modifier,
            reason=reason,
            strongest_dimension=strongest,
            weakest_dimension=weakest,
            dimension_results=dimension_results,
            drivers=drivers,
        )
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        current_state: DeploymentState,
        factor_governance_score: float,
        feature_governance_score: float,
        ecology_score: float,
        interaction_score: float,  # -1 to 1
        shadow_duration_days: float,
        recent_errors: int = 0,
        factor_governance_state: str = "STABLE",
        ecology_state: str = "STABLE",
        interaction_state: str = "NEUTRAL",
    ) -> DeploymentGovernanceResult:
        """
        Evaluate with provided scores (for testing).
        """
        now = datetime.now(timezone.utc)
        
        # Normalize interaction score
        interaction_normalized = (interaction_score + 1) / 2
        
        # Calculate shadow readiness
        shadow_result = self.shadow_engine.calculate_shadow_readiness(
            factor_name=factor_name,
            factor_governance_score=factor_governance_score,
            factor_governance_state=factor_governance_state,
            ecology_score=ecology_score,
            ecology_state=ecology_state,
            interaction_score=interaction_score,
            interaction_state=interaction_state,
            shadow_duration_days=shadow_duration_days,
        )
        
        # Build dimension results
        dimension_results = [
            DeploymentDimensionResult(
                dimension=DeploymentDimension.FACTOR_GOVERNANCE,
                score=factor_governance_score,
                status=self._score_to_status(factor_governance_score),
                reason="Direct input",
            ),
            DeploymentDimensionResult(
                dimension=DeploymentDimension.FEATURE_GOVERNANCE,
                score=feature_governance_score,
                status=self._score_to_status(feature_governance_score),
                reason="Direct input",
            ),
            DeploymentDimensionResult(
                dimension=DeploymentDimension.ECOLOGY,
                score=ecology_score,
                status=self._score_to_status(ecology_score),
                reason="Direct input",
            ),
            DeploymentDimensionResult(
                dimension=DeploymentDimension.INTERACTION,
                score=interaction_normalized,
                status=self._score_to_status(interaction_normalized),
                reason="Direct input",
            ),
            shadow_result,
        ]
        
        # Calculate deployment score
        deployment_score = self._calculate_deployment_score(
            factor_governance_score=factor_governance_score,
            feature_governance_score=feature_governance_score,
            ecology_score=ecology_score,
            interaction_score=interaction_normalized,
            shadow_readiness=shadow_result.score,
        )
        
        # Calculate rollback risk
        rollback_risk = self.rollback_engine.calculate_rollback_risk(
            factor_name=factor_name,
            factor_governance_score=factor_governance_score,
            factor_governance_state=factor_governance_state,
            ecology_score=ecology_score,
            ecology_state=ecology_state,
            interaction_score=interaction_score,
            interaction_state=interaction_state,
            recent_errors=recent_errors,
            current_state=current_state,
        )
        
        # Calculate promotion readiness
        promotion_result = self.promotion_engine.calculate_promotion_readiness(
            factor_name=factor_name,
            deployment_score=deployment_score,
            shadow_readiness=shadow_result.score,
            rollback_risk=rollback_risk,
            current_state=current_state,
            factor_governance_state=factor_governance_state,
            ecology_state=ecology_state,
        )
        
        promotion_readiness = promotion_result["promotion_readiness"]
        governance_action = promotion_result["recommended_action"]
        reason = promotion_result["reason"]
        
        # Get modifiers
        modifiers = DEPLOYMENT_MODIFIERS[governance_action]
        capital_modifier = modifiers["capital_modifier"]
        confidence_modifier = modifiers["confidence_modifier"]
        
        # Find extremes
        weakest, strongest = self._find_extremes(dimension_results)
        
        return DeploymentGovernanceResult(
            factor_name=factor_name,
            timestamp=now,
            deployment_state=current_state,
            deployment_score=deployment_score,
            shadow_readiness=shadow_result.score,
            promotion_readiness=promotion_readiness,
            rollback_risk=rollback_risk,
            governance_action=governance_action,
            capital_modifier=capital_modifier,
            confidence_modifier=confidence_modifier,
            reason=reason,
            strongest_dimension=strongest,
            weakest_dimension=weakest,
            dimension_results=dimension_results,
            drivers={},
        )
    
    # ═══════════════════════════════════════════════════════════
    # SCORE CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_deployment_score(
        self,
        factor_governance_score: float,
        feature_governance_score: float,
        ecology_score: float,
        interaction_score: float,  # Already normalized 0..1
        shadow_readiness: float,
    ) -> float:
        """
        Calculate deployment score.
        
        Formula:
            score = 0.35 * factor_governance
                  + 0.20 * feature_governance
                  + 0.20 * ecology
                  + 0.15 * interaction
                  + 0.10 * shadow_readiness
        """
        score = (
            DEPLOYMENT_WEIGHTS["factor_governance"] * factor_governance_score +
            DEPLOYMENT_WEIGHTS["feature_governance"] * feature_governance_score +
            DEPLOYMENT_WEIGHTS["ecology"] * ecology_score +
            DEPLOYMENT_WEIGHTS["interaction"] * interaction_score +
            DEPLOYMENT_WEIGHTS["shadow_readiness"] * shadow_readiness
        )
        return max(0.0, min(1.0, score))
    
    def _score_to_status(self, score: float) -> str:
        """Convert score to status."""
        if score >= 0.70:
            return "READY"
        elif score >= 0.50:
            return "CAUTION"
        else:
            return "NOT_READY"
    
    def _find_extremes(
        self,
        dimension_results: List[DeploymentDimensionResult],
    ) -> tuple[DeploymentDimension, DeploymentDimension]:
        """Find weakest and strongest dimensions."""
        sorted_dims = sorted(dimension_results, key=lambda x: x.score)
        weakest = sorted_dims[0].dimension
        strongest = sorted_dims[-1].dimension
        return (weakest, strongest)
    
    # ═══════════════════════════════════════════════════════════
    # DATA GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_deployment_info(self, factor_name: str) -> Dict[str, Any]:
        """Get deployment state info for a factor."""
        if factor_name in FACTOR_DEPLOYMENT_STATE:
            return FACTOR_DEPLOYMENT_STATE[factor_name]
        
        # Default for unknown factors
        return {
            "current_state": DeploymentState.SHADOW,
            "shadow_duration_days": 0,
            "recent_errors": 0,
        }
    
    def _build_drivers(
        self,
        factor_name: str,
        current_state: DeploymentState,
        dimension_results: List[DeploymentDimensionResult],
        governance_action: GovernanceAction,
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        return {
            "current_deployment_state": current_state.value,
            "recommended_action": governance_action.value,
            "dimension_contributions": {
                dim.dimension.value: round(dim.score * DEPLOYMENT_WEIGHTS.get(dim.dimension.value, 0.1), 4)
                for dim in dimension_results
            },
            "warnings": [r.reason for r in dimension_results if r.status == "NOT_READY"],
            "cautions": [r.reason for r in dimension_results if r.status == "CAUTION"],
        }
    
    # ═══════════════════════════════════════════════════════════
    # BATCH AND PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def evaluate_batch(self, factor_names: List[str]) -> Dict[str, DeploymentGovernanceResult]:
        """Evaluate multiple factors at once."""
        results = {}
        for name in factor_names:
            results[name] = self.evaluate(name)
        return results
    
    def get_all_known_factors(self) -> List[str]:
        """Get list of all known factors with deployment state."""
        return list(FACTOR_DEPLOYMENT_STATE.keys())


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[DeploymentGovernanceEngine] = None


def get_deployment_governance_engine() -> DeploymentGovernanceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = DeploymentGovernanceEngine()
    return _engine
