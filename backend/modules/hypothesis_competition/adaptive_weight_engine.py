"""
Adaptive Weight Engine

PHASE 30.5 — Adaptive Weight Engine

Automatically adjusts hypothesis weights based on their real performance.

Key features:
- Success rate modifier (boost/penalize based on success_rate)
- PnL modifier (boost/penalize based on avg_pnl)
- Combined adaptive modifier
- Minimum observations threshold
- Integration with Capital Allocation Engine

This transforms the system into an adaptive trading intelligence:
market → hypothesis → portfolio → outcome → learning → improved portfolio
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from .adaptive_weight_types import (
    HypothesisAdaptiveWeight,
    AdaptiveWeightSummary,
    MIN_OBSERVATIONS,
    SUCCESS_MODIFIER_MIN,
    SUCCESS_MODIFIER_MAX,
    SUCCESS_MODIFIER_SCALE,
    PNL_MODIFIER_MIN,
    PNL_MODIFIER_MAX,
    PNL_POSITIVE_SCALE,
    PNL_NEGATIVE_SCALE,
    COMBINED_MODIFIER_MIN,
    COMBINED_MODIFIER_MAX,
    SUCCESS_WEIGHT,
    PNL_WEIGHT,
)
from .outcome_tracking_engine import get_outcome_tracking_engine
from .outcome_tracking_types import HypothesisPerformance


# ══════════════════════════════════════════════════════════════
# Adaptive Weight Engine
# ══════════════════════════════════════════════════════════════

class AdaptiveWeightEngine:
    """
    Adaptive Weight Engine — PHASE 30.5
    
    Automatically adjusts hypothesis weights based on performance.
    
    Pipeline:
    1. Get performance data from OutcomeTrackingEngine
    2. Calculate success_modifier
    3. Calculate pnl_modifier
    4. Combine modifiers
    5. Apply to base weight
    6. Store for use by Capital Allocation Engine
    """
    
    def __init__(self):
        self._weights: Dict[str, Dict[str, HypothesisAdaptiveWeight]] = {}
        self._base_weights: Dict[str, float] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Success Rate Modifier
    # ═══════════════════════════════════════════════════════════
    
    def calculate_success_modifier(self, success_rate: float) -> float:
        """
        Calculate success rate modifier.
        
        success_rate >= 0.60 → boost
        success_rate 0.50-0.60 → neutral
        success_rate < 0.50 → penalize
        
        Formula: 1 + (success_rate - 0.50) × 1.2
        Bounds: 0.70 ≤ modifier ≤ 1.30
        """
        modifier = 1.0 + (success_rate - 0.50) * SUCCESS_MODIFIER_SCALE
        
        # Clamp to bounds
        modifier = max(SUCCESS_MODIFIER_MIN, min(SUCCESS_MODIFIER_MAX, modifier))
        
        return round(modifier, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 2. PnL Modifier
    # ═══════════════════════════════════════════════════════════
    
    def calculate_pnl_modifier(self, avg_pnl: float) -> float:
        """
        Calculate PnL modifier.
        
        avg_pnl > 0: modifier = 1 + (avg_pnl × 0.25)
        avg_pnl < 0: modifier = 1 + (avg_pnl × 0.40)
        
        Bounds: 0.75 ≤ modifier ≤ 1.25
        """
        if avg_pnl >= 0:
            modifier = 1.0 + (avg_pnl / 100.0) * PNL_POSITIVE_SCALE
        else:
            modifier = 1.0 + (avg_pnl / 100.0) * PNL_NEGATIVE_SCALE
        
        # Clamp to bounds
        modifier = max(PNL_MODIFIER_MIN, min(PNL_MODIFIER_MAX, modifier))
        
        return round(modifier, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Combined Modifier
    # ═══════════════════════════════════════════════════════════
    
    def calculate_combined_modifier(
        self,
        success_modifier: float,
        pnl_modifier: float,
    ) -> float:
        """
        Calculate combined adaptive modifier.
        
        Formula: 0.60 × success_modifier + 0.40 × pnl_modifier
        Bounds: 0.65 ≤ modifier ≤ 1.35
        """
        modifier = SUCCESS_WEIGHT * success_modifier + PNL_WEIGHT * pnl_modifier
        
        # Clamp to bounds
        modifier = max(COMBINED_MODIFIER_MIN, min(COMBINED_MODIFIER_MAX, modifier))
        
        return round(modifier, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Calculate Adaptive Weight
    # ═══════════════════════════════════════════════════════════
    
    def calculate_adaptive_weight(
        self,
        performance: HypothesisPerformance,
        base_weight: float = 1.0,
    ) -> HypothesisAdaptiveWeight:
        """
        Calculate adaptive weight for a hypothesis type.
        
        If observations < MIN_OBSERVATIONS, modifier = 1.0
        """
        # Check minimum observations
        if performance.total_predictions < MIN_OBSERVATIONS:
            return HypothesisAdaptiveWeight(
                hypothesis_type=performance.hypothesis_type,
                success_rate=performance.success_rate,
                avg_pnl=performance.avg_pnl,
                base_weight=base_weight,
                success_modifier=1.0,
                pnl_modifier=1.0,
                adaptive_modifier=1.0,
                final_weight=base_weight,
                observations=performance.total_predictions,
            )
        
        # Calculate modifiers
        success_mod = self.calculate_success_modifier(performance.success_rate)
        pnl_mod = self.calculate_pnl_modifier(performance.avg_pnl)
        combined_mod = self.calculate_combined_modifier(success_mod, pnl_mod)
        
        # Calculate final weight
        final_weight = round(base_weight * combined_mod, 4)
        
        return HypothesisAdaptiveWeight(
            hypothesis_type=performance.hypothesis_type,
            success_rate=performance.success_rate,
            avg_pnl=performance.avg_pnl,
            base_weight=base_weight,
            success_modifier=success_mod,
            pnl_modifier=pnl_mod,
            adaptive_modifier=combined_mod,
            final_weight=final_weight,
            observations=performance.total_predictions,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 5. Generate Adaptive Weights for Symbol
    # ═══════════════════════════════════════════════════════════
    
    def generate_adaptive_weights(
        self,
        symbol: str,
    ) -> List[HypothesisAdaptiveWeight]:
        """
        Generate adaptive weights for all hypothesis types for a symbol.
        """
        # Get performance data from OutcomeTrackingEngine
        outcome_engine = get_outcome_tracking_engine()
        performances = outcome_engine.calculate_performance(symbol.upper())
        
        if not performances:
            return []
        
        # Calculate base weights (equal distribution initially)
        num_types = len(performances)
        base_weight = 1.0 / num_types if num_types > 0 else 1.0
        
        # Calculate adaptive weights
        weights = []
        for perf in performances:
            weight = self.calculate_adaptive_weight(perf, base_weight)
            weights.append(weight)
        
        # Normalize final weights to sum to 1.0
        weights = self._normalize_weights(weights)
        
        # Store
        self._store_weights(symbol.upper(), weights)
        
        return weights
    
    def _normalize_weights(
        self,
        weights: List[HypothesisAdaptiveWeight],
    ) -> List[HypothesisAdaptiveWeight]:
        """
        Normalize final weights to sum to 1.0.
        """
        if not weights:
            return weights
        
        total = sum(w.final_weight for w in weights)
        if total <= 0:
            return weights
        
        for w in weights:
            w.final_weight = round(w.final_weight / total, 4)
        
        return weights
    
    # ═══════════════════════════════════════════════════════════
    # 6. Get Adaptive Modifier for Hypothesis
    # ═══════════════════════════════════════════════════════════
    
    def get_adaptive_modifier(
        self,
        symbol: str,
        hypothesis_type: str,
    ) -> float:
        """
        Get adaptive modifier for a specific hypothesis type.
        
        Used by Capital Allocation Engine.
        """
        symbol_weights = self._weights.get(symbol.upper(), {})
        weight = symbol_weights.get(hypothesis_type)
        
        if weight:
            return weight.adaptive_modifier
        
        return 1.0
    
    def get_all_modifiers(self, symbol: str) -> Dict[str, float]:
        """
        Get all adaptive modifiers for a symbol.
        """
        symbol_weights = self._weights.get(symbol.upper(), {})
        return {
            h_type: w.adaptive_modifier
            for h_type, w in symbol_weights.items()
        }
    
    # ═══════════════════════════════════════════════════════════
    # 7. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_weights(
        self,
        symbol: str,
        weights: List[HypothesisAdaptiveWeight],
    ) -> None:
        """Store weights in memory."""
        if symbol not in self._weights:
            self._weights[symbol] = {}
        
        for w in weights:
            self._weights[symbol][w.hypothesis_type] = w
    
    def get_weights(self, symbol: str) -> List[HypothesisAdaptiveWeight]:
        """Get all weights for a symbol."""
        symbol_weights = self._weights.get(symbol.upper(), {})
        return list(symbol_weights.values())
    
    # ═══════════════════════════════════════════════════════════
    # 8. Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> AdaptiveWeightSummary:
        """
        Get summary of adaptive weights for a symbol.
        """
        weights = self.get_weights(symbol.upper())
        
        if not weights:
            return AdaptiveWeightSummary(symbol=symbol.upper())
        
        modifiers = [w.adaptive_modifier for w in weights]
        total_obs = sum(w.observations for w in weights)
        
        boosted = sum(1 for m in modifiers if m > 1.0)
        penalized = sum(1 for m in modifiers if m < 1.0)
        neutral = sum(1 for m in modifiers if m == 1.0)
        
        best = max(weights, key=lambda w: w.adaptive_modifier)
        worst = min(weights, key=lambda w: w.adaptive_modifier)
        
        return AdaptiveWeightSummary(
            symbol=symbol.upper(),
            total_hypothesis_types=len(weights),
            total_observations=total_obs,
            avg_adaptive_modifier=round(sum(modifiers) / len(modifiers), 4),
            max_adaptive_modifier=round(max(modifiers), 4),
            min_adaptive_modifier=round(min(modifiers), 4),
            boosted_count=boosted,
            penalized_count=penalized,
            neutral_count=neutral,
            best_hypothesis=best.hypothesis_type,
            best_modifier=best.adaptive_modifier,
            worst_hypothesis=worst.hypothesis_type,
            worst_modifier=worst.adaptive_modifier,
            last_updated=max(w.last_updated for w in weights),
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_adaptive_engine: Optional[AdaptiveWeightEngine] = None


def get_adaptive_weight_engine() -> AdaptiveWeightEngine:
    """Get singleton instance of AdaptiveWeightEngine."""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveWeightEngine()
    return _adaptive_engine
