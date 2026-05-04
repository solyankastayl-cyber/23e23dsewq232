"""
PHASE 20.2 — Factor Weight Adjustment Engine
============================================
Main engine for recommending factor weight adjustments.

Combines:
- Failure Pattern Engine (critical patterns)
- Factor Governance
- Deployment Governance
- Attribution signals

Outputs:
- Adjustment recommendations per factor
- Summary of all adjustments
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_types import (
    FactorWeightAdjustment,
    FactorWeightAdjustmentSummary,
    AdjustmentAction,
    AdjustmentStrength,
    WEIGHT_MIN,
    WEIGHT_MAX,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_policy import (
    get_factor_weight_policy,
    FactorWeightPolicy,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_registry import (
    get_factor_weight_registry,
    FactorWeightRegistry,
)
from modules.research_loop.failure_patterns import (
    get_failure_pattern_engine,
    PatternSeverity,
)


class FactorWeightAdjustmentEngine:
    """
    Factor Weight Adjustment Engine - PHASE 20.2
    
    Recommends weight adjustments based on failure patterns,
    governance, and deployment signals.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.policy = get_factor_weight_policy()
        self.registry = get_factor_weight_registry()
        self.failure_engine = get_failure_pattern_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_adjustments(self) -> FactorWeightAdjustmentSummary:
        """
        Compute weight adjustments for all factors.
        
        Returns FactorWeightAdjustmentSummary with all recommendations.
        """
        now = datetime.now(timezone.utc)
        
        # Get failure patterns
        failure_summary = self.failure_engine.analyze_trades()
        
        # Build factor failure map
        factor_failures = self._build_factor_failure_map(failure_summary.patterns)
        
        # Get all factors
        factor_names = self.registry.get_factor_names()
        
        # Compute adjustments
        adjustments = []
        increased = []
        decreased = []
        held = []
        shadowed = []
        retired = []
        
        for factor_name in factor_names:
            adjustment = self._compute_factor_adjustment(
                factor_name=factor_name,
                factor_failures=factor_failures,
            )
            adjustments.append(adjustment)
            
            # Categorize by action
            if adjustment.adjustment_action == AdjustmentAction.INCREASE:
                increased.append(factor_name)
            elif adjustment.adjustment_action == AdjustmentAction.DECREASE:
                decreased.append(factor_name)
            elif adjustment.adjustment_action == AdjustmentAction.SHADOW:
                shadowed.append(factor_name)
            elif adjustment.adjustment_action == AdjustmentAction.RETIRE:
                retired.append(factor_name)
            else:
                held.append(factor_name)
        
        return FactorWeightAdjustmentSummary(
            total_factors=len(adjustments),
            increased=increased,
            decreased=decreased,
            held=held,
            shadowed=shadowed,
            retired=retired,
            increase_count=len(increased),
            decrease_count=len(decreased),
            hold_count=len(held),
            shadow_count=len(shadowed),
            retire_count=len(retired),
            adjustments=adjustments,
            timestamp=now,
        )
    
    def compute_factor_adjustment(
        self,
        factor_name: str,
    ) -> Optional[FactorWeightAdjustment]:
        """
        Compute adjustment for a single factor.
        """
        # Get failure patterns
        failure_summary = self.failure_engine.analyze_trades()
        factor_failures = self._build_factor_failure_map(failure_summary.patterns)
        
        return self._compute_factor_adjustment(
            factor_name=factor_name,
            factor_failures=factor_failures,
        )
    
    def apply_adjustment(
        self,
        factor_name: str,
        adjustment: FactorWeightAdjustment,
    ):
        """
        Apply adjustment to registry (recommendation → actual).
        
        Note: In production, this would require governance approval.
        """
        self.registry.update_weight(
            factor_name=factor_name,
            new_weight=adjustment.recommended_weight,
            action=adjustment.adjustment_action,
            reason=adjustment.reason,
        )
    
    def recompute_all(self) -> FactorWeightAdjustmentSummary:
        """
        Recompute and apply all adjustments.
        
        Returns summary of applied adjustments.
        """
        summary = self.compute_adjustments()
        
        for adjustment in summary.adjustments:
            self.apply_adjustment(adjustment.factor_name, adjustment)
        
        return summary
    
    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _compute_factor_adjustment(
        self,
        factor_name: str,
        factor_failures: Dict[str, Dict[str, Any]],
    ) -> FactorWeightAdjustment:
        """
        Compute adjustment for a single factor.
        """
        now = datetime.now(timezone.utc)
        
        # Get current weight state
        weight_state = self.registry.get_weight(factor_name)
        if weight_state is None:
            current_weight = 0.1
            governance_state = "STABLE"
            deployment_state = "LIVE"
        else:
            current_weight = weight_state.current_weight
            governance_state = weight_state.governance_state
            deployment_state = weight_state.deployment_state
        
        # Get failure data for this factor
        failure_data = factor_failures.get(factor_name, {
            "total_patterns": 0,
            "critical_patterns": 0,
            "high_patterns": 0,
            "total_loss_rate": 0.0,
        })
        
        failure_patterns_count = failure_data.get("total_patterns", 0)
        critical_failures = failure_data.get("critical_patterns", 0)
        
        # Determine action and strength
        action, strength = self.policy.determine_action(
            critical_failures=critical_failures,
            failure_patterns_count=failure_patterns_count,
            governance_state=governance_state,
            deployment_state=deployment_state,
        )
        
        # Calculate delta
        delta = self.policy.calculate_delta(
            action=action,
            strength=strength,
            current_weight=current_weight,
        )
        
        # Calculate recommended weight
        recommended_weight = self.policy.calculate_recommended_weight(
            current_weight=current_weight,
            delta=delta,
        )
        
        # Calculate modifiers
        conf_modifier, cap_modifier = self.policy.calculate_modifiers(
            action=action,
            strength=strength,
            recommended_weight=recommended_weight,
            current_weight=current_weight,
        )
        
        # Build reason
        reason = self.policy.build_reason(
            action=action,
            strength=strength,
            critical_failures=critical_failures,
            failure_patterns_count=failure_patterns_count,
            governance_state=governance_state,
            deployment_state=deployment_state,
        )
        
        return FactorWeightAdjustment(
            factor_name=factor_name,
            current_weight=current_weight,
            recommended_weight=recommended_weight,
            weight_delta=delta,
            adjustment_action=action,
            adjustment_strength=strength,
            confidence_modifier=conf_modifier,
            capital_modifier=cap_modifier,
            reason=reason,
            failure_patterns_count=failure_patterns_count,
            critical_failures=critical_failures,
            governance_state=governance_state,
            deployment_state=deployment_state,
            timestamp=now,
        )
    
    def _build_factor_failure_map(
        self,
        patterns: List,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build map of factor → failure statistics.
        """
        factor_map: Dict[str, Dict[str, Any]] = {}
        
        for pattern in patterns:
            factor = pattern.involved_factor
            
            if factor not in factor_map:
                factor_map[factor] = {
                    "total_patterns": 0,
                    "critical_patterns": 0,
                    "high_patterns": 0,
                    "total_loss_rate": 0.0,
                    "total_occurrences": 0,
                }
            
            factor_map[factor]["total_patterns"] += 1
            factor_map[factor]["total_occurrences"] += pattern.occurrences
            factor_map[factor]["total_loss_rate"] += pattern.loss_rate
            
            if pattern.severity == PatternSeverity.CRITICAL:
                factor_map[factor]["critical_patterns"] += 1
            elif pattern.severity == PatternSeverity.HIGH:
                factor_map[factor]["high_patterns"] += 1
        
        return factor_map


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[FactorWeightAdjustmentEngine] = None


def get_factor_weight_adjustment_engine() -> FactorWeightAdjustmentEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorWeightAdjustmentEngine()
    return _engine
