"""
PHASE 20.4 — Research Loop Engine
=================================
Main aggregator engine for self-improving research loop.

Combines:
- Failure Pattern Engine
- Factor Weight Adjustment Engine
- Adaptive Promotion Engine

Outputs unified loop state with recommendations.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.research_loop.aggregator.research_loop_types import (
    LoopState,
    LoopSignal,
    ResearchLoopState,
    LOOP_STATE_THRESHOLDS,
    LOOP_MODIFIERS,
    LOOP_SCORE_WEIGHTS,
)
from modules.research_loop.aggregator.research_loop_registry import (
    get_research_loop_registry,
    ResearchLoopRegistry,
)

# Import dependent engines
from modules.research_loop.failure_patterns import (
    get_failure_pattern_engine,
    PatternSeverity,
)
from modules.research_loop.factor_weight_adjustment import (
    get_factor_weight_adjustment_engine,
    AdjustmentAction,
)
from modules.research_loop.adaptive_promotion import (
    get_adaptive_promotion_engine,
    TransitionAction,
    LifecycleState,
)


class ResearchLoopEngine:
    """
    Research Loop Aggregator Engine - PHASE 20.4
    
    Aggregates all research loop components into unified state.
    Creates meta-state for:
    - System health overlay
    - Governance overlay
    - Capital overlay
    """
    
    def __init__(self):
        """Initialize engine."""
        self.registry = get_research_loop_registry()
        self.failure_engine = get_failure_pattern_engine()
        self.weight_engine = get_factor_weight_adjustment_engine()
        self.promotion_engine = get_adaptive_promotion_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_state(self) -> ResearchLoopState:
        """
        Compute unified research loop state.
        
        Returns ResearchLoopState with all aggregated data.
        """
        now = datetime.now(timezone.utc)
        
        # Gather data from all engines
        failure_data = self._gather_failure_data()
        weight_data = self._gather_weight_data()
        promotion_data = self._gather_promotion_data()
        
        # Calculate signals
        signals = self._calculate_signals(
            failure_data=failure_data,
            weight_data=weight_data,
            promotion_data=promotion_data,
        )
        
        # Calculate loop score
        loop_score = self._calculate_loop_score(signals)
        
        # Determine loop state
        loop_state = self._determine_loop_state(loop_score)
        
        # Get modifiers
        modifiers = LOOP_MODIFIERS[loop_state]
        
        # Determine strongest/weakest signals
        strongest, weakest = self._determine_signal_extremes(signals)
        
        # Build reason
        reason = self._build_reason(
            loop_state=loop_state,
            failure_data=failure_data,
            weight_data=weight_data,
            promotion_data=promotion_data,
        )
        
        # Calculate factor counts
        factor_counts = self._calculate_factor_counts(promotion_data)
        
        state = ResearchLoopState(
            loop_state=loop_state,
            loop_score=loop_score,
            
            total_factors=factor_counts["total"],
            healthy_factors=factor_counts["healthy"],
            watchlist_factors=factor_counts["watchlist"],
            degraded_factors=factor_counts["degraded"],
            retired_factors=factor_counts["retired"],
            
            critical_failure_patterns=failure_data["critical_patterns"],
            
            recommended_increases=weight_data["increased"],
            recommended_decreases=weight_data["decreased"],
            
            recommended_promotions=promotion_data["promoted"],
            recommended_demotions=promotion_data["demoted"],
            recommended_freezes=promotion_data["frozen"],
            recommended_retires=promotion_data["retired"],
            
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            
            strongest_signal=strongest,
            weakest_signal=weakest,
            
            reason=reason,
            signals=signals,
            timestamp=now,
        )
        
        return state
    
    def recompute(self) -> ResearchLoopState:
        """
        Recompute state and record to registry.
        """
        state = self.compute_state()
        self.registry.record_state(state)
        return state
    
    def get_current_state(self) -> Optional[ResearchLoopState]:
        """Get current state from registry."""
        return self.registry.get_current_state()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current state summary."""
        state = self.compute_state()
        return state.to_summary()
    
    # ═══════════════════════════════════════════════════════════
    # DATA GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _gather_failure_data(self) -> Dict[str, Any]:
        """Gather data from Failure Pattern Engine."""
        summary = self.failure_engine.analyze_trades()
        
        critical_patterns = [
            p.pattern_name for p in summary.patterns 
            if p.severity == PatternSeverity.CRITICAL
        ]
        high_patterns = [
            p.pattern_name for p in summary.patterns 
            if p.severity == PatternSeverity.HIGH
        ]
        
        return {
            "total_patterns": summary.total_patterns,
            "critical_count": summary.critical_count,
            "high_count": summary.high_count,
            "critical_patterns": critical_patterns,
            "high_patterns": high_patterns,
            "overall_loss_rate": summary.overall_loss_rate,
        }
    
    def _gather_weight_data(self) -> Dict[str, Any]:
        """Gather data from Factor Weight Adjustment Engine."""
        summary = self.weight_engine.compute_adjustments()
        
        return {
            "total_factors": summary.total_factors,
            "increased": summary.increased,
            "decreased": summary.decreased,
            "held": summary.held,
            "shadowed": summary.shadowed,
            "retired": summary.retired,
            "increase_count": summary.increase_count,
            "decrease_count": summary.decrease_count,
            "shadow_count": summary.shadow_count,
            "retire_count": summary.retire_count,
        }
    
    def _gather_promotion_data(self) -> Dict[str, Any]:
        """Gather data from Adaptive Promotion Engine."""
        summary = self.promotion_engine.compute_all_decisions()
        
        # Get state distribution from registry
        registry = self.promotion_engine.registry
        state_dist = registry.get_state_distribution()
        
        return {
            "total_factors": summary.total_factors,
            "promoted": summary.promoted,
            "demoted": summary.demoted,
            "frozen": summary.frozen,
            "retired": summary.retired,
            "held": summary.held,
            "promote_count": summary.promote_count,
            "demote_count": summary.demote_count,
            "freeze_count": summary.freeze_count,
            "retire_count": summary.retire_count,
            "hold_count": summary.hold_count,
            "state_distribution": state_dist,
        }
    
    # ═══════════════════════════════════════════════════════════
    # SIGNAL CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_signals(
        self,
        failure_data: Dict[str, Any],
        weight_data: Dict[str, Any],
        promotion_data: Dict[str, Any],
    ) -> List[LoopSignal]:
        """Calculate all loop signals."""
        signals = []
        
        # 1. Healthy Factor Ratio
        total = promotion_data["total_factors"]
        state_dist = promotion_data.get("state_distribution", {})
        
        # Factors in LIVE or CANDIDATE are considered healthy
        live_count = state_dist.get("LIVE", 0)
        candidate_count = state_dist.get("CANDIDATE", 0)
        healthy_count = live_count + candidate_count
        
        healthy_ratio = healthy_count / total if total > 0 else 0.0
        healthy_weight = LOOP_SCORE_WEIGHTS["healthy_factor_ratio"]
        
        signals.append(LoopSignal(
            name="healthy_factor_ratio",
            value=healthy_ratio,
            weight=healthy_weight,
            contribution=healthy_weight * healthy_ratio,
            status=self._classify_signal_status(healthy_ratio, positive=True),
        ))
        
        # 2. Promotion Health (more promotions = good)
        promote_count = promotion_data["promote_count"]
        demote_count = promotion_data["demote_count"]
        
        if promote_count + demote_count > 0:
            promotion_health = promote_count / (promote_count + demote_count)
        else:
            promotion_health = 0.5  # Neutral if no changes
        
        promotion_weight = LOOP_SCORE_WEIGHTS["promotion_health"]
        
        signals.append(LoopSignal(
            name="promotion_health",
            value=promotion_health,
            weight=promotion_weight,
            contribution=promotion_weight * promotion_health,
            status=self._classify_signal_status(promotion_health, positive=True),
        ))
        
        # 3. Adjustment Stability (more holds = stable)
        hold_count = weight_data.get("hold_count", 0) or len(weight_data.get("held", []))
        weight_total = weight_data["total_factors"]
        
        stability_ratio = hold_count / weight_total if weight_total > 0 else 0.5
        stability_weight = LOOP_SCORE_WEIGHTS["adjustment_stability"]
        
        signals.append(LoopSignal(
            name="adjustment_stability",
            value=stability_ratio,
            weight=stability_weight,
            contribution=stability_weight * stability_ratio,
            status=self._classify_signal_status(stability_ratio, positive=True),
        ))
        
        # 4. Critical Pattern Pressure (negative)
        critical_count = failure_data["critical_count"]
        high_count = failure_data["high_count"]
        
        # Normalize: 0 patterns = 0, 5+ critical = 1.0
        pattern_pressure = min(1.0, (critical_count * 0.2 + high_count * 0.1))
        pattern_weight = LOOP_SCORE_WEIGHTS["critical_pattern_pressure"]  # Negative weight
        
        signals.append(LoopSignal(
            name="critical_pattern_pressure",
            value=pattern_pressure,
            weight=pattern_weight,
            contribution=pattern_weight * pattern_pressure,  # Negative contribution
            status=self._classify_signal_status(pattern_pressure, positive=False),
        ))
        
        # 5. Retire/Freeze Pressure (negative)
        freeze_count = promotion_data["freeze_count"]
        retire_count = promotion_data["retire_count"]
        shadow_count = weight_data.get("shadow_count", 0)
        
        # Normalize
        retire_freeze_pressure = min(1.0, (freeze_count * 0.3 + retire_count * 0.4 + shadow_count * 0.1))
        rf_weight = LOOP_SCORE_WEIGHTS["retire_freeze_pressure"]  # Negative weight
        
        signals.append(LoopSignal(
            name="retire_freeze_pressure",
            value=retire_freeze_pressure,
            weight=rf_weight,
            contribution=rf_weight * retire_freeze_pressure,  # Negative contribution
            status=self._classify_signal_status(retire_freeze_pressure, positive=False),
        ))
        
        return signals
    
    def _classify_signal_status(self, value: float, positive: bool) -> str:
        """Classify signal status."""
        if positive:
            if value >= 0.75:
                return "STRONG"
            elif value >= 0.50:
                return "MODERATE"
            elif value >= 0.25:
                return "WEAK"
            else:
                return "CRITICAL"
        else:
            # For negative signals (pressure), high is bad
            if value <= 0.15:
                return "STRONG"
            elif value <= 0.35:
                return "MODERATE"
            elif value <= 0.60:
                return "WEAK"
            else:
                return "CRITICAL"
    
    # ═══════════════════════════════════════════════════════════
    # LOOP SCORE & STATE
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_loop_score(self, signals: List[LoopSignal]) -> float:
        """
        Calculate overall loop score from signals.
        
        Score = sum of all contributions, normalized to 0..1
        """
        total_contribution = sum(s.contribution for s in signals)
        
        # Normalize: max positive = 0.70, max negative = -0.30
        # So range is -0.30 to 0.70, shift to 0..1
        normalized = (total_contribution + 0.30) / 1.0
        
        return max(0.0, min(1.0, normalized))
    
    def _determine_loop_state(self, score: float) -> LoopState:
        """Determine loop state from score."""
        if score >= LOOP_STATE_THRESHOLDS[LoopState.HEALTHY]:
            return LoopState.HEALTHY
        elif score >= LOOP_STATE_THRESHOLDS[LoopState.ADAPTING]:
            return LoopState.ADAPTING
        elif score >= LOOP_STATE_THRESHOLDS[LoopState.DEGRADED]:
            return LoopState.DEGRADED
        else:
            return LoopState.CRITICAL
    
    def _determine_signal_extremes(
        self,
        signals: List[LoopSignal],
    ) -> Tuple[str, str]:
        """Determine strongest and weakest signals."""
        if not signals:
            return "none", "none"
        
        # For strongest: highest positive contribution
        # For weakest: lowest (most negative) contribution or worst status
        
        sorted_by_contribution = sorted(
            signals,
            key=lambda s: s.contribution,
            reverse=True,
        )
        
        strongest = sorted_by_contribution[0].name
        weakest = sorted_by_contribution[-1].name
        
        return strongest, weakest
    
    # ═══════════════════════════════════════════════════════════
    # FACTOR COUNTS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_factor_counts(
        self,
        promotion_data: Dict[str, Any],
    ) -> Dict[str, int]:
        """Calculate factor counts by category."""
        state_dist = promotion_data.get("state_distribution", {})
        
        # Healthy = LIVE + CANDIDATE
        healthy = state_dist.get("LIVE", 0) + state_dist.get("CANDIDATE", 0)
        
        # Watchlist = REDUCED + SHADOW
        watchlist = state_dist.get("REDUCED", 0) + state_dist.get("SHADOW", 0)
        
        # Degraded = FROZEN
        degraded = state_dist.get("FROZEN", 0)
        
        # Retired
        retired = state_dist.get("RETIRED", 0)
        
        total = promotion_data["total_factors"]
        
        return {
            "total": total,
            "healthy": healthy,
            "watchlist": watchlist,
            "degraded": degraded,
            "retired": retired,
        }
    
    # ═══════════════════════════════════════════════════════════
    # REASON BUILDER
    # ═══════════════════════════════════════════════════════════
    
    def _build_reason(
        self,
        loop_state: LoopState,
        failure_data: Dict[str, Any],
        weight_data: Dict[str, Any],
        promotion_data: Dict[str, Any],
    ) -> str:
        """Build human-readable reason for current state."""
        reasons = []
        
        if loop_state == LoopState.HEALTHY:
            reasons.append("system stable with minimal issues")
            if promotion_data["promote_count"] > 0:
                reasons.append(f"{promotion_data['promote_count']} factors being promoted")
        
        elif loop_state == LoopState.ADAPTING:
            reasons.append("loop actively rebalancing factors")
            if weight_data["decrease_count"] > 0:
                reasons.append(f"{weight_data['decrease_count']} weight decreases recommended")
            if promotion_data["demote_count"] > 0:
                reasons.append(f"{promotion_data['demote_count']} demotions pending")
        
        elif loop_state == LoopState.DEGRADED:
            reasons.append("multiple factors degrading")
            if failure_data["critical_count"] > 0:
                reasons.append(f"{failure_data['critical_count']} critical failure patterns")
            if promotion_data["freeze_count"] > 0:
                reasons.append(f"{promotion_data['freeze_count']} factors frozen")
        
        elif loop_state == LoopState.CRITICAL:
            reasons.append("system-wide degradation detected")
            if failure_data["critical_count"] > 2:
                reasons.append(f"{failure_data['critical_count']} critical patterns across factors")
            if promotion_data["retire_count"] > 0:
                reasons.append(f"{promotion_data['retire_count']} factors recommended for retirement")
        
        return ", ".join(reasons) if reasons else "loop state computed"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[ResearchLoopEngine] = None


def get_research_loop_engine() -> ResearchLoopEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = ResearchLoopEngine()
    return _engine
