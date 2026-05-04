"""
Capital Allocation Engine

PHASE 30.3 — Capital Allocation Engine

Distributes capital among hypotheses from RankedHypothesisPool.
Creates portfolio of hypotheses, not single hypothesis selection.

Key features:
- Base weight calculation (proportional to ranking_score)
- Execution state adjustment (FAVORABLE/CAUTIOUS/UNFAVORABLE)
- Directional risk control (max 65% in one direction)
- Neutral hypothesis cap (max 30%)
- Minimum allocation threshold (5%)
- Portfolio confidence/reliability calculation

This transforms the system from analysis engine → portfolio decision engine.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from .capital_allocation_types import (
    HypothesisAllocation,
    HypothesisCapitalAllocation,
    CapitalAllocationSummary,
    EXECUTION_STATE_MODIFIERS,
    MAX_DIRECTIONAL_EXPOSURE,
    MAX_NEUTRAL_ALLOCATION,
    MIN_ALLOCATION_THRESHOLD,
)
from .hypothesis_ranking_engine import (
    RankedHypothesisPool,
    get_hypothesis_ranking_engine,
)
from .hypothesis_pool_types import HypothesisPoolItem


# ══════════════════════════════════════════════════════════════
# Capital Allocation Engine
# ══════════════════════════════════════════════════════════════

class CapitalAllocationEngine:
    """
    Capital Allocation Engine — PHASE 30.3
    
    Transforms RankedHypothesisPool into capital allocation portfolio.
    
    Pipeline:
    1. Base weight calculation (∝ ranking_score)
    2. Execution state adjustment
    3. Remove unfavorable hypotheses
    4. Directional risk control
    5. Neutral cap application
    6. Minimum allocation filter
    7. Final normalization
    8. Portfolio metrics calculation
    """
    
    def __init__(self):
        self._allocations: Dict[str, List[HypothesisCapitalAllocation]] = {}
        self._current: Dict[str, HypothesisCapitalAllocation] = {}
        self._use_adaptive_weights: bool = True  # Enable adaptive weighting
        self._use_meta_alpha: bool = True  # Enable meta-alpha modifiers
    
    # ═══════════════════════════════════════════════════════════
    # 1. Base Weight Calculation (with Adaptive + Meta-Alpha Modifiers)
    # ═══════════════════════════════════════════════════════════
    
    def calculate_base_weights(
        self,
        items: List[HypothesisPoolItem],
        symbol: str = "BTC",
    ) -> List[tuple]:
        """
        Calculate base capital weights proportional to ranking_score.
        
        PHASE 30.5: Applies adaptive modifiers from AdaptiveWeightEngine.
        PHASE 31.1: Also applies meta_alpha modifiers from MetaAlphaEngine.
        
        Formula: capital_weight = (ranking_score × adaptive_modifier × meta_alpha_modifier) / sum
        
        Returns:
            List of (item, weight) tuples
        """
        if not items:
            return []
        
        # Get adaptive modifiers if enabled
        adaptive_modifiers = {}
        if self._use_adaptive_weights:
            try:
                from .adaptive_weight_engine import get_adaptive_weight_engine
                adaptive_engine = get_adaptive_weight_engine()
                adaptive_modifiers = adaptive_engine.get_all_modifiers(symbol)
            except Exception:
                pass
        
        # Get meta-alpha modifiers if enabled
        meta_modifiers = {}
        if self._use_meta_alpha:
            try:
                from modules.meta_alpha import get_meta_alpha_engine
                meta_engine = get_meta_alpha_engine()
                meta_modifiers = meta_engine.get_all_modifiers(symbol)
            except Exception:
                pass
        
        # Calculate adjusted scores
        adjusted_scores = []
        for item in items:
            adaptive_mod = adaptive_modifiers.get(item.hypothesis_type, 1.0)
            meta_mod = meta_modifiers.get(item.hypothesis_type, 1.0)
            adjusted_score = item.ranking_score * adaptive_mod * meta_mod
            adjusted_scores.append((item, adjusted_score))
        
        total_score = sum(score for _, score in adjusted_scores)
        if total_score <= 0:
            return [(item, 0.0) for item, _ in adjusted_scores]
        
        return [
            (item, round(score / total_score, 4))
            for item, score in adjusted_scores
        ]
    
    # ═══════════════════════════════════════════════════════════
    # 2. Execution State Adjustment
    # ═══════════════════════════════════════════════════════════
    
    def apply_execution_state_adjustment(
        self,
        weighted_items: List[tuple],
    ) -> List[tuple]:
        """
        Apply execution state modifier to weights.
        
        FAVORABLE:   weight *= 1.00
        CAUTIOUS:    weight *= 0.80
        UNFAVORABLE: weight  = 0.00 (removed from portfolio)
        
        Returns:
            List of (item, adjusted_weight) tuples
        """
        adjusted = []
        
        for item, weight in weighted_items:
            modifier = EXECUTION_STATE_MODIFIERS.get(item.execution_state, 1.0)
            adjusted_weight = round(weight * modifier, 4)
            adjusted.append((item, adjusted_weight))
        
        return adjusted
    
    # ═══════════════════════════════════════════════════════════
    # 3. Remove Unfavorable Hypotheses
    # ═══════════════════════════════════════════════════════════
    
    def remove_unfavorable(
        self,
        weighted_items: List[tuple],
    ) -> tuple[List[tuple], int]:
        """
        Remove hypotheses with UNFAVORABLE execution state (weight = 0).
        
        Returns:
            (filtered_items, removed_count)
        """
        filtered = []
        removed_count = 0
        
        for item, weight in weighted_items:
            if item.execution_state == "UNFAVORABLE" or weight <= 0:
                removed_count += 1
            else:
                filtered.append((item, weight))
        
        return filtered, removed_count
    
    # ═══════════════════════════════════════════════════════════
    # 4. Directional Risk Control
    # ═══════════════════════════════════════════════════════════
    
    def apply_directional_cap(
        self,
        weighted_items: List[tuple],
    ) -> tuple[List[tuple], bool]:
        """
        Apply directional exposure cap.
        
        Maximum 65% in one direction (LONG or SHORT).
        If exceeded, reduce weights in dominant direction to cap.
        Excess is redistributed to other directions.
        
        Returns:
            (adjusted_items, cap_applied)
        """
        if not weighted_items:
            return [], False
        
        # Calculate current directional exposure
        long_weight = sum(w for item, w in weighted_items if item.directional_bias == "LONG")
        short_weight = sum(w for item, w in weighted_items if item.directional_bias == "SHORT")
        
        cap_applied = False
        adjusted = list(weighted_items)
        
        # Check if LONG exceeds cap
        if long_weight > MAX_DIRECTIONAL_EXPOSURE:
            # Calculate how much to reduce
            excess = long_weight - MAX_DIRECTIONAL_EXPOSURE
            # Calculate scale factor for LONG items only
            scale_factor = MAX_DIRECTIONAL_EXPOSURE / long_weight
            
            adjusted = []
            for item, w in weighted_items:
                if item.directional_bias == "LONG":
                    adjusted.append((item, round(w * scale_factor, 4)))
                else:
                    adjusted.append((item, w))
            cap_applied = True
        
        # Recalculate after LONG adjustment
        short_weight = sum(w for item, w in adjusted if item.directional_bias == "SHORT")
        
        # Check if SHORT exceeds cap
        if short_weight > MAX_DIRECTIONAL_EXPOSURE:
            scale_factor = MAX_DIRECTIONAL_EXPOSURE / short_weight
            
            new_adjusted = []
            for item, w in adjusted:
                if item.directional_bias == "SHORT":
                    new_adjusted.append((item, round(w * scale_factor, 4)))
                else:
                    new_adjusted.append((item, w))
            adjusted = new_adjusted
            cap_applied = True
        
        return adjusted, cap_applied
    
    # ═══════════════════════════════════════════════════════════
    # 5. Neutral Cap Application
    # ═══════════════════════════════════════════════════════════
    
    def apply_neutral_cap(
        self,
        weighted_items: List[tuple],
    ) -> tuple[List[tuple], bool]:
        """
        Apply neutral hypothesis cap.
        
        Maximum 30% allocation to NEUTRAL hypotheses.
        
        Returns:
            (adjusted_items, cap_applied)
        """
        if not weighted_items:
            return [], False
        
        neutral_weight = sum(w for item, w in weighted_items if item.directional_bias == "NEUTRAL")
        
        if neutral_weight <= MAX_NEUTRAL_ALLOCATION:
            return weighted_items, False
        
        # Scale neutral weights down
        scale_factor = MAX_NEUTRAL_ALLOCATION / neutral_weight
        adjusted = [
            (item, round(w * scale_factor, 4) if item.directional_bias == "NEUTRAL" else w)
            for item, w in weighted_items
        ]
        
        return adjusted, True
    
    # ═══════════════════════════════════════════════════════════
    # 6. Minimum Allocation Filter
    # ═══════════════════════════════════════════════════════════
    
    def apply_min_allocation_filter(
        self,
        weighted_items: List[tuple],
    ) -> tuple[List[tuple], int]:
        """
        Remove allocations below minimum threshold.
        
        Minimum allocation: 5%
        
        Returns:
            (filtered_items, removed_count)
        """
        filtered = []
        removed_count = 0
        
        for item, weight in weighted_items:
            if weight < MIN_ALLOCATION_THRESHOLD:
                removed_count += 1
            else:
                filtered.append((item, weight))
        
        return filtered, removed_count
    
    # ═══════════════════════════════════════════════════════════
    # 7. Final Normalization
    # ═══════════════════════════════════════════════════════════
    
    def normalize_weights(
        self,
        weighted_items: List[tuple],
    ) -> List[tuple]:
        """
        Normalize weights to sum to 1.0.
        
        Returns:
            List of (item, normalized_weight) tuples
        """
        if not weighted_items:
            return []
        
        total = sum(w for _, w in weighted_items)
        if total <= 0:
            return [(item, 0.0) for item, _ in weighted_items]
        
        return [
            (item, round(w / total, 4))
            for item, w in weighted_items
        ]
    
    # ═══════════════════════════════════════════════════════════
    # 8. Portfolio Metrics
    # ═══════════════════════════════════════════════════════════
    
    def calculate_portfolio_confidence(
        self,
        allocations: List[HypothesisAllocation],
    ) -> float:
        """
        Calculate portfolio confidence.
        
        Formula: sum(capital_weight × hypothesis_confidence)
        """
        if not allocations:
            return 0.0
        
        weighted_confidence = sum(
            a.capital_weight * a.confidence
            for a in allocations
        )
        
        return round(weighted_confidence, 4)
    
    def calculate_portfolio_reliability(
        self,
        allocations: List[HypothesisAllocation],
    ) -> float:
        """
        Calculate portfolio reliability.
        
        Formula: sum(capital_weight × hypothesis_reliability)
        """
        if not allocations:
            return 0.0
        
        weighted_reliability = sum(
            a.capital_weight * a.reliability
            for a in allocations
        )
        
        return round(weighted_reliability, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 9. Full Allocation Pipeline
    # ═══════════════════════════════════════════════════════════
    
    def allocate_capital(
        self,
        ranked_pool: RankedHypothesisPool,
    ) -> HypothesisCapitalAllocation:
        """
        Execute full capital allocation pipeline.
        
        PHASE 30.5: Now uses adaptive modifiers from AdaptiveWeightEngine.
        
        Steps:
        1. Base weight calculation (with adaptive modifiers)
        2. Execution state adjustment
        3. Remove unfavorable
        4. First normalization
        5. Directional cap (with renorm)
        6. Neutral cap (with renorm)
        7. Min allocation filter (with renorm)
        8. Portfolio metrics
        """
        items = list(ranked_pool.hypotheses)
        total_input = len(items)
        
        # Step 1: Base weights (with adaptive modifiers)
        weighted = self.calculate_base_weights(items, symbol=ranked_pool.symbol)
        
        # Step 2: Execution state adjustment
        weighted = self.apply_execution_state_adjustment(weighted)
        
        # Step 3: Remove unfavorable
        weighted, unfavorable_removed = self.remove_unfavorable(weighted)
        
        # Step 4: First normalization
        weighted = self.normalize_weights(weighted)
        
        # Step 5: Directional cap (iterative to ensure compliance)
        directional_cap_applied = False
        for _ in range(10):  # Max 10 iterations to ensure convergence
            # Check current exposure
            long_weight = sum(w for item, w in weighted if item.directional_bias == "LONG")
            short_weight = sum(w for item, w in weighted if item.directional_bias == "SHORT")
            
            if long_weight <= MAX_DIRECTIONAL_EXPOSURE and short_weight <= MAX_DIRECTIONAL_EXPOSURE:
                break
            
            weighted_new, cap_applied = self.apply_directional_cap(weighted)
            if cap_applied:
                directional_cap_applied = True
                weighted = self.normalize_weights(weighted_new)
            else:
                break
        
        # Step 6: Neutral cap (iterative)
        neutral_cap_applied = False
        for _ in range(3):
            weighted_new, cap_applied = self.apply_neutral_cap(weighted)
            if cap_applied:
                neutral_cap_applied = True
                weighted = self.normalize_weights(weighted_new)
            else:
                break
        
        # Step 7: Min allocation filter
        weighted, min_threshold_removed = self.apply_min_allocation_filter(weighted)
        
        # Final normalization
        weighted = self.normalize_weights(weighted)
        
        # Build allocations
        allocations = []
        for item, weight in weighted:
            allocation = HypothesisAllocation(
                hypothesis_type=item.hypothesis_type,
                directional_bias=item.directional_bias,
                ranking_score=item.ranking_score,
                capital_weight=weight,
                capital_percent=round(weight * 100, 2),
                execution_state=item.execution_state,
                confidence=item.confidence,
                reliability=item.reliability,
            )
            allocations.append(allocation)
        
        # Calculate portfolio metrics
        portfolio_confidence = self.calculate_portfolio_confidence(allocations)
        portfolio_reliability = self.calculate_portfolio_reliability(allocations)
        total_allocated = sum(a.capital_weight for a in allocations)
        
        # Build result
        result = HypothesisCapitalAllocation(
            symbol=ranked_pool.symbol,
            allocations=allocations,
            total_allocated=round(total_allocated, 4),
            portfolio_confidence=portfolio_confidence,
            portfolio_reliability=portfolio_reliability,
            total_hypotheses_input=total_input,
            hypotheses_removed_unfavorable=unfavorable_removed,
            hypotheses_removed_min_threshold=min_threshold_removed,
            directional_cap_applied=directional_cap_applied,
            neutral_cap_applied=neutral_cap_applied,
        )
        
        # Store
        self._store_allocation(ranked_pool.symbol, result)
        
        return result
    
    # ═══════════════════════════════════════════════════════════
    # 10. Generate from Symbol
    # ═══════════════════════════════════════════════════════════
    
    def generate_allocation(self, symbol: str) -> HypothesisCapitalAllocation:
        """
        Generate capital allocation from symbol.
        
        Fetches RankedHypothesisPool and allocates capital.
        """
        ranking_engine = get_hypothesis_ranking_engine()
        ranked_pool = ranking_engine.generate_ranked_pool(symbol.upper())
        
        return self.allocate_capital(ranked_pool)
    
    # ═══════════════════════════════════════════════════════════
    # 11. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_allocation(
        self,
        symbol: str,
        allocation: HypothesisCapitalAllocation,
    ) -> None:
        """Store allocation in history."""
        if symbol not in self._allocations:
            self._allocations[symbol] = []
        self._allocations[symbol].append(allocation)
        self._current[symbol] = allocation
    
    def get_allocation(self, symbol: str) -> Optional[HypothesisCapitalAllocation]:
        """Get current allocation for symbol."""
        return self._current.get(symbol)
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[HypothesisCapitalAllocation]:
        """Get allocation history for symbol."""
        history = self._allocations.get(symbol, [])
        return sorted(history, key=lambda a: a.created_at, reverse=True)[:limit]
    
    def get_summary(self, symbol: str) -> CapitalAllocationSummary:
        """Get allocation summary for symbol."""
        history = self._allocations.get(symbol, [])
        
        if not history:
            return CapitalAllocationSummary(
                symbol=symbol,
                total_allocations=0,
            )
        
        # Calculate averages
        total = len(history)
        
        avg_long = sum(
            sum(a.capital_weight for a in alloc.allocations if a.directional_bias == "LONG")
            for alloc in history
        ) / total
        
        avg_short = sum(
            sum(a.capital_weight for a in alloc.allocations if a.directional_bias == "SHORT")
            for alloc in history
        ) / total
        
        avg_neutral = sum(
            sum(a.capital_weight for a in alloc.allocations if a.directional_bias == "NEUTRAL")
            for alloc in history
        ) / total
        
        avg_confidence = sum(alloc.portfolio_confidence for alloc in history) / total
        avg_reliability = sum(alloc.portfolio_reliability for alloc in history) / total
        avg_count = sum(len(alloc.allocations) for alloc in history) / total
        
        # Current state
        current = self._current.get(symbol)
        current_count = len(current.allocations) if current else 0
        current_top = current.allocations[0].hypothesis_type if current and current.allocations else "NONE"
        
        return CapitalAllocationSummary(
            symbol=symbol,
            total_allocations=total,
            avg_long_exposure=round(avg_long, 4),
            avg_short_exposure=round(avg_short, 4),
            avg_neutral_exposure=round(avg_neutral, 4),
            avg_portfolio_confidence=round(avg_confidence, 4),
            avg_portfolio_reliability=round(avg_reliability, 4),
            avg_hypothesis_count=round(avg_count, 2),
            current_allocation_count=current_count,
            current_top_hypothesis=current_top,
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_capital_engine: Optional[CapitalAllocationEngine] = None


def get_capital_allocation_engine() -> CapitalAllocationEngine:
    """Get singleton instance of CapitalAllocationEngine."""
    global _capital_engine
    if _capital_engine is None:
        _capital_engine = CapitalAllocationEngine()
    return _capital_engine
