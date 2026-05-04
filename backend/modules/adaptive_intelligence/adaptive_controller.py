"""
PHASE 11.5 - Adaptive Controller
=================================
Main brain of the adaptive system.

Makes decisions:
- Adjust parameters
- Change weights
- Disable strategies
- Modify allocations

All decisions must pass through Adaptive Safety Layer!
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .adaptive_types import (
    AdaptiveState, AdaptiveAction, AdaptiveRecommendation,
    SystemAdaptiveSnapshot, EdgeStatus, PerformanceTrend,
    ChangeDecision, DEFAULT_ADAPTIVE_CONFIG
)
from .strategy_performance_tracker import StrategyPerformanceTracker
from .parameter_optimizer import ParameterOptimizer
from .factor_weight_optimizer import FactorWeightOptimizer
from .edge_decay_detector import EdgeDecayDetector
from .adaptive_safety.change_guard import ChangeGuard
from .adaptive_safety.cooldown_manager import CooldownManager
from .adaptive_safety.shadow_mode_engine import ShadowModeEngine
from .adaptive_safety.oos_gate import OOSGate
from .adaptive_safety.change_audit import ChangeAudit
from .adaptive_safety.adaptive_limits import AdaptiveLimits


class AdaptiveController:
    """
    Adaptive Controller - Central Brain
    
    Coordinates all adaptive intelligence components and
    ensures changes pass through safety layer.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        
        # Core engines
        self.performance_tracker = StrategyPerformanceTracker(config)
        self.parameter_optimizer = ParameterOptimizer(config)
        self.weight_optimizer = FactorWeightOptimizer(config)
        self.edge_detector = EdgeDecayDetector(config)
        
        # Safety layer (CRITICAL!)
        self.change_guard = ChangeGuard(config)
        self.cooldown_manager = CooldownManager(config)
        self.shadow_engine = ShadowModeEngine(config)
        self.oos_gate = OOSGate(config)
        self.change_audit = ChangeAudit()
        self.limits = AdaptiveLimits()
        
        # State
        self.current_state = AdaptiveState.STABLE
        self.recommendations: List[AdaptiveRecommendation] = []
        self.disabled_strategies: set = set()
    
    def evaluate_system(
        self,
        strategies: List[Dict],
        factors: Dict[str, str],
        current_equity: float = 1000000
    ) -> SystemAdaptiveSnapshot:
        """
        Evaluate entire system and generate recommendations.
        
        Args:
            strategies: List of strategy info dicts
            factors: Dict of factor_name -> category
            current_equity: Current portfolio equity
            
        Returns:
            SystemAdaptiveSnapshot with system state
        """
        now = datetime.now(timezone.utc)
        self.recommendations = []
        
        # Track performance for each strategy
        for strat in strategies:
            perf = self.performance_tracker.track_performance(
                strat.get("id", "unknown"),
                strat.get("name", "Strategy"),
                strat.get("trades", None)
            )
            
            # Check for decay
            decay = self.edge_detector.detect_decay(
                strat.get("id", "unknown"),
                strat.get("edge_name", "main_edge")
            )
            
            # Generate recommendations if needed
            self._generate_strategy_recommendations(strat, perf, decay)
        
        # Optimize weights
        weight_adjustments = self.weight_optimizer.optimize_weights(factors)
        for adj in weight_adjustments:
            if abs(adj.weight_change) > 0.02:  # Only significant changes
                self._generate_weight_recommendation(adj)
        
        # Count edges by status
        edge_summary = self.edge_detector.get_decay_summary()
        
        # Determine system state
        in_cooldown = len(self.cooldown_manager.get_active_cooldowns()) > 0
        shadow_running = len(self.shadow_engine.get_active_tests())
        
        if shadow_running > 0:
            self.current_state = AdaptiveState.SHADOW_TESTING
        elif in_cooldown:
            self.current_state = AdaptiveState.COOLDOWN
        elif len(self.recommendations) > 0:
            self.current_state = AdaptiveState.ADAPTING
        elif edge_summary.get("edges_requiring_attention", 0) > 0:
            self.current_state = AdaptiveState.OBSERVING
        else:
            self.current_state = AdaptiveState.STABLE
        
        # Calculate system health
        health_score = self._calculate_system_health(edge_summary)
        
        # Calculate adaptivity score
        adaptivity_score = self._calculate_adaptivity_score()
        
        return SystemAdaptiveSnapshot(
            timestamp=now,
            adaptive_state=self.current_state,
            system_adaptivity_score=adaptivity_score,
            edges_strengthening=edge_summary.get("strong", 0),
            edges_stable=edge_summary.get("healthy", 0),
            edges_degrading=edge_summary.get("weakening", 0),
            edges_critical=edge_summary.get("critical", 0) + edge_summary.get("dead", 0),
            pending_parameter_changes=len(self.parameter_optimizer.get_pending_adjustments()),
            pending_weight_changes=len(self.weight_optimizer.get_pending_changes()),
            strategies_disabled=len(self.disabled_strategies),
            in_cooldown=in_cooldown,
            shadow_tests_running=shadow_running,
            overall_system_health=health_score
        )
    
    def _generate_strategy_recommendations(
        self,
        strategy: Dict,
        performance,
        decay
    ):
        """Generate recommendations for a strategy."""
        now = datetime.now(timezone.utc)
        strat_id = strategy.get("id", "unknown")
        
        # Check if strategy needs attention
        if decay.edge_status == EdgeStatus.DEAD:
            rec = self._create_recommendation(
                AdaptiveAction.DISABLE_STRATEGY,
                strat_id,
                {"edge_status": decay.edge_status.value},
                {"action": "DISABLE"},
                decay.decay_probability,
                decay.urgency
            )
            if rec:
                self.recommendations.append(rec)
        
        elif decay.edge_status == EdgeStatus.CRITICAL:
            rec = self._create_recommendation(
                AdaptiveAction.DECREASE_ALLOCATION,
                strat_id,
                {"current_allocation": strategy.get("allocation", 0.2)},
                {"decrease_by": 0.5},
                decay.decay_probability,
                decay.urgency
            )
            if rec:
                self.recommendations.append(rec)
        
        elif performance.performance_trend == PerformanceTrend.DECLINING:
            # Consider parameter optimization
            rec = self._create_recommendation(
                AdaptiveAction.ADJUST_PARAMETER,
                strat_id,
                {"trend": performance.performance_trend.value},
                {"optimize_parameters": True},
                performance.trend_strength * 0.8,
                0.5
            )
            if rec:
                self.recommendations.append(rec)
    
    def _generate_weight_recommendation(self, weight_adj):
        """Generate recommendation for weight adjustment."""
        rec = self._create_recommendation(
            AdaptiveAction.ADJUST_WEIGHT,
            weight_adj.factor_name,
            {"current_weight": weight_adj.current_weight},
            {"new_weight": weight_adj.suggested_weight},
            0.7,  # Confidence
            0.4   # Urgency
        )
        if rec:
            self.recommendations.append(rec)
    
    def _create_recommendation(
        self,
        action: AdaptiveAction,
        target: str,
        current_state: Dict,
        proposed_change: Dict,
        confidence: float,
        urgency: float
    ) -> Optional[AdaptiveRecommendation]:
        """Create a recommendation after safety validation."""
        now = datetime.now(timezone.utc)
        
        # Run through safety checks
        safety_checks = {}
        
        # 1. Change Guard
        is_valid, reason = self.change_guard.validate_action(
            action, target, {**current_state, **proposed_change}
        )
        safety_checks["change_guard"] = is_valid
        
        if not is_valid:
            return None  # Blocked by change guard
        
        # 2. Cooldown Check
        cooldown_key = f"{action.value}_{target}"
        cooldown_clear, _ = self.cooldown_manager.check_cooldown(cooldown_key)
        safety_checks["cooldown"] = cooldown_clear
        
        # 3. Confidence Check
        min_conf = self.limits.get_limit("min_parameter_confidence")
        safety_checks["confidence"] = confidence >= min_conf
        
        # Determine if safety cleared
        safety_cleared = all(safety_checks.values())
        
        # Determine execution timing
        if not cooldown_clear:
            remaining = self.cooldown_manager.get_remaining_cooldown(cooldown_key)
            if remaining and remaining.total_seconds() > 24 * 3600:
                timing = "COOLDOWN"
            else:
                timing = "NEXT_SESSION"
        elif urgency > 0.8:
            timing = "IMMEDIATE"
        else:
            timing = "NEXT_SESSION"
        
        # Calculate expected impact (mock)
        expected_impact = confidence * 0.1 * (1 if action != AdaptiveAction.DISABLE_STRATEGY else -0.5)
        
        return AdaptiveRecommendation(
            timestamp=now,
            action=action,
            target=target,
            current_state=current_state,
            proposed_change=proposed_change,
            expected_impact=expected_impact,
            safety_cleared=safety_cleared,
            safety_checks=safety_checks,
            confidence=confidence,
            evidence_strength=urgency,
            execution_timing=timing
        )
    
    def execute_recommendation(
        self,
        recommendation: AdaptiveRecommendation
    ) -> Dict:
        """Execute an approved recommendation."""
        
        if not recommendation.safety_cleared:
            return {
                "executed": False,
                "reason": "Safety checks not passed",
                "failed_checks": [k for k, v in recommendation.safety_checks.items() if not v]
            }
        
        # Start shadow test if required
        if self.config.get("shadow_test_required", True):
            test = self.shadow_engine.start_shadow_test(
                key=recommendation.target,
                change_type=recommendation.action.value,
                current_config=recommendation.current_state,
                candidate_config=recommendation.proposed_change
            )
            
            return {
                "executed": False,
                "reason": "Shadow test started",
                "shadow_test_id": test.test_id,
                "shadow_ends": test.ends_at.isoformat()
            }
        
        # Run OOS validation
        if self.limits.get_limit("oos_validation_required"):
            validation = self.oos_gate.validate_change(
                key=recommendation.target,
                change_config=recommendation.proposed_change
            )
            
            if validation.overall_result.value != "PASSED":
                return {
                    "executed": False,
                    "reason": f"OOS validation {validation.overall_result.value}",
                    "gates_passed": validation.gates_passed,
                    "gates_required": validation.gates_total
                }
        
        # Record change
        cooldown_key = f"{recommendation.action.value}_{recommendation.target}"
        
        record = self.change_audit.record_change(
            change_type=recommendation.action.value,
            target=recommendation.target,
            old_value=recommendation.current_state,
            new_value=recommendation.proposed_change,
            trigger_reason="Adaptive recommendation",
            evidence={"confidence": recommendation.confidence},
            confidence=recommendation.confidence,
            approved_by="adaptive_controller",
            safety_checks=list(recommendation.safety_checks.keys())
        )
        
        # Start cooldown
        self.cooldown_manager.start_cooldown(
            cooldown_key,
            recommendation.action.value,
            {"record_id": record.record_id}
        )
        
        # Apply change (in real system)
        if recommendation.action == AdaptiveAction.DISABLE_STRATEGY:
            self.disabled_strategies.add(recommendation.target)
        
        return {
            "executed": True,
            "record_id": record.record_id,
            "cooldown_started": True,
            "action": recommendation.action.value,
            "target": recommendation.target
        }
    
    def _calculate_system_health(self, edge_summary: Dict) -> float:
        """Calculate overall system health score."""
        total = edge_summary.get("total_edges", 1)
        if total == 0:
            return 1.0
        
        strong = edge_summary.get("strong", 0)
        healthy = edge_summary.get("healthy", 0)
        weakening = edge_summary.get("weakening", 0)
        critical = edge_summary.get("critical", 0)
        dead = edge_summary.get("dead", 0)
        
        # Weighted score
        score = (
            strong * 1.0 +
            healthy * 0.8 +
            weakening * 0.4 +
            critical * 0.1 +
            dead * 0.0
        ) / total
        
        return min(1.0, max(0.0, score))
    
    def _calculate_adaptivity_score(self) -> float:
        """Calculate how well system is adapting."""
        audit_summary = self.change_audit.get_audit_summary()
        
        if audit_summary.get("summary") == "NO_RECORDS":
            return 0.5  # Neutral
        
        success_rate = audit_summary.get("success_rate", 0)
        avg_confidence = audit_summary.get("avg_confidence", 0.5)
        
        return success_rate * 0.7 + avg_confidence * 0.3
    
    def get_pending_recommendations(self) -> List[Dict]:
        """Get all pending recommendations."""
        return [r.to_dict() for r in self.recommendations if r.safety_cleared]
    
    def get_controller_summary(self) -> Dict:
        """Get summary of adaptive controller state."""
        return {
            "state": self.current_state.value,
            "pending_recommendations": len(self.recommendations),
            "disabled_strategies": list(self.disabled_strategies),
            "safety_summary": {
                "change_guard": self.change_guard.get_guard_summary(),
                "cooldowns": self.cooldown_manager.get_cooldown_summary(),
                "shadow_tests": self.shadow_engine.get_shadow_summary(),
                "oos_gate": self.oos_gate.get_oos_summary(),
                "audit": self.change_audit.get_audit_summary()
            },
            "limits": self.limits.get_limits_summary()
        }
