"""
Hypothesis Ranking Engine

PHASE 30.2 — Hypothesis Ranking Engine

Makes ranking robust through:
- Duplicate suppression (same hypothesis type)
- Directional clustering (LONG/SHORT/NEUTRAL)
- Dominance penalty (prevents overweight)
- Diversity penalty (similar structures)

This separates institutional systems from simple signal generators.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from collections import defaultdict

from pydantic import BaseModel, Field

from .hypothesis_pool_types import (
    HypothesisPoolItem,
    HypothesisPool,
    RANKING_WEIGHT_CONFIDENCE,
    RANKING_WEIGHT_RELIABILITY,
    RANKING_WEIGHT_EXECUTION,
    MAX_POOL_SIZE,
)


# ══════════════════════════════════════════════════════════════
# Constants — Ranking Adjustments
# ══════════════════════════════════════════════════════════════

# Dominance penalty when ≥3 hypotheses in same direction
DOMINANCE_THRESHOLD = 3
DOMINANCE_PENALTY = 0.92

# Diversity penalty when structural scores too similar
SIMILARITY_THRESHOLD = 0.05
DIVERSITY_PENALTY = 0.95


# ══════════════════════════════════════════════════════════════
# Directional Groups
# ══════════════════════════════════════════════════════════════

DIRECTIONAL_MAPPING = {
    "LONG": "LONG",
    "SHORT": "SHORT",
    "NEUTRAL": "NEUTRAL",
}


# ══════════════════════════════════════════════════════════════
# Ranked Hypothesis Pool
# ══════════════════════════════════════════════════════════════

class RankedHypothesisPool(BaseModel):
    """
    Ranked pool with diversification applied.
    
    Contains directional balance information for capital allocation.
    """
    symbol: str
    
    # Ranked hypotheses (top first)
    hypotheses: List[HypothesisPoolItem] = Field(default_factory=list)
    
    # Best hypothesis
    top_hypothesis: str = "NO_EDGE"
    
    # Directional balance for capital allocator
    directional_balance: Dict[str, int] = Field(default_factory=dict)
    
    # Pool metrics
    pool_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    pool_reliability: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Pool size
    pool_size: int = 0
    
    # Ranking metadata
    duplicates_removed: int = 0
    dominance_penalty_applied: bool = False
    diversity_penalties_applied: int = 0
    
    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Hypothesis Ranking Engine
# ══════════════════════════════════════════════════════════════

class HypothesisRankingEngine:
    """
    Hypothesis Ranking Engine — PHASE 30.2
    
    Two-step ranking:
    1. Base ranking (confidence + reliability + execution)
    2. Ranking adjustments (duplicate, dominance, diversity)
    
    Prevents:
    - Same hypotheses dominating
    - Directional overweight
    - Structural similarity flooding
    """
    
    def __init__(self):
        self._ranked_pools: Dict[str, List[RankedHypothesisPool]] = {}
        self._current: Dict[str, RankedHypothesisPool] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Base Score Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_base_score(
        self,
        confidence: float,
        reliability: float,
        execution_score: float,
    ) -> float:
        """
        Calculate base ranking score.
        
        Formula:
        base_score = 0.50*confidence + 0.30*reliability + 0.20*execution_score
        """
        score = (
            RANKING_WEIGHT_CONFIDENCE * confidence
            + RANKING_WEIGHT_RELIABILITY * reliability
            + RANKING_WEIGHT_EXECUTION * execution_score
        )
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 2. Duplicate Suppression
    # ═══════════════════════════════════════════════════════════
    
    def apply_duplicate_suppression(
        self,
        items: List[HypothesisPoolItem],
    ) -> tuple[List[HypothesisPoolItem], int]:
        """
        Remove duplicate hypothesis types, keeping strongest.
        
        Example:
        BREAKOUT_FORMING (0.66), BREAKOUT_FORMING (0.61), BREAKOUT_FORMING (0.58)
        → BREAKOUT_FORMING (0.66)
        
        Returns:
            (filtered_items, duplicates_removed_count)
        """
        if not items:
            return [], 0
        
        # Group by hypothesis type
        type_groups: Dict[str, List[HypothesisPoolItem]] = defaultdict(list)
        for item in items:
            type_groups[item.hypothesis_type].append(item)
        
        # Keep only strongest of each type
        unique_items = []
        duplicates_removed = 0
        
        for hypothesis_type, group in type_groups.items():
            # Sort by ranking_score descending
            group.sort(key=lambda x: x.ranking_score, reverse=True)
            # Keep strongest
            unique_items.append(group[0])
            # Count removed
            duplicates_removed += len(group) - 1
        
        return unique_items, duplicates_removed
    
    # ═══════════════════════════════════════════════════════════
    # 3. Directional Clustering
    # ═══════════════════════════════════════════════════════════
    
    def get_directional_groups(
        self,
        items: List[HypothesisPoolItem],
    ) -> Dict[str, List[HypothesisPoolItem]]:
        """
        Group hypotheses by directional bias.
        
        Groups: LONG, SHORT, NEUTRAL
        """
        groups: Dict[str, List[HypothesisPoolItem]] = {
            "LONG": [],
            "SHORT": [],
            "NEUTRAL": [],
        }
        
        for item in items:
            direction = DIRECTIONAL_MAPPING.get(item.directional_bias, "NEUTRAL")
            groups[direction].append(item)
        
        return groups
    
    def calculate_directional_balance(
        self,
        items: List[HypothesisPoolItem],
    ) -> Dict[str, int]:
        """
        Calculate directional balance for pool.
        
        Returns: {"LONG": 2, "SHORT": 1, "NEUTRAL": 1}
        """
        groups = self.get_directional_groups(items)
        return {
            direction: len(group)
            for direction, group in groups.items()
        }
    
    # ═══════════════════════════════════════════════════════════
    # 4. Dominance Penalty
    # ═══════════════════════════════════════════════════════════
    
    def apply_dominance_penalty(
        self,
        items: List[HypothesisPoolItem],
    ) -> tuple[List[HypothesisPoolItem], bool]:
        """
        Apply penalty when one direction dominates (≥3 hypotheses).
        
        Dominant group gets ranking_score *= 0.92
        
        Returns:
            (adjusted_items, penalty_applied)
        """
        if not items:
            return [], False
        
        groups = self.get_directional_groups(items)
        
        # Find dominant direction
        dominant_direction = None
        for direction, group in groups.items():
            if len(group) >= DOMINANCE_THRESHOLD:
                dominant_direction = direction
                break
        
        if dominant_direction is None:
            return items, False
        
        # Apply penalty to dominant group
        adjusted_items = []
        for item in items:
            if item.directional_bias == dominant_direction:
                # Create new item with penalized score
                adjusted_item = HypothesisPoolItem(
                    hypothesis_type=item.hypothesis_type,
                    directional_bias=item.directional_bias,
                    confidence=item.confidence,
                    reliability=item.reliability,
                    structural_score=item.structural_score,
                    execution_score=item.execution_score,
                    conflict_score=item.conflict_score,
                    ranking_score=round(item.ranking_score * DOMINANCE_PENALTY, 4),
                    execution_state=item.execution_state,
                    reason=item.reason,
                )
                adjusted_items.append(adjusted_item)
            else:
                adjusted_items.append(item)
        
        return adjusted_items, True
    
    # ═══════════════════════════════════════════════════════════
    # 5. Diversity Penalty
    # ═══════════════════════════════════════════════════════════
    
    def apply_diversity_penalty(
        self,
        items: List[HypothesisPoolItem],
    ) -> tuple[List[HypothesisPoolItem], int]:
        """
        Apply penalty when hypotheses are structurally too similar.
        
        If |structural_score difference| < 0.05, apply ranking_score *= 0.95
        
        Returns:
            (adjusted_items, penalties_applied_count)
        """
        if len(items) < 2:
            return items, 0
        
        # Sort by structural score for comparison
        sorted_items = sorted(items, key=lambda x: x.structural_score, reverse=True)
        
        adjusted_items = []
        penalties_applied = 0
        penalized_indices = set()
        
        for i in range(len(sorted_items)):
            for j in range(i + 1, len(sorted_items)):
                diff = abs(sorted_items[i].structural_score - sorted_items[j].structural_score)
                if diff < SIMILARITY_THRESHOLD:
                    # Penalize the weaker one (lower index j has lower score)
                    penalized_indices.add(j)
        
        for i, item in enumerate(sorted_items):
            if i in penalized_indices:
                adjusted_item = HypothesisPoolItem(
                    hypothesis_type=item.hypothesis_type,
                    directional_bias=item.directional_bias,
                    confidence=item.confidence,
                    reliability=item.reliability,
                    structural_score=item.structural_score,
                    execution_score=item.execution_score,
                    conflict_score=item.conflict_score,
                    ranking_score=round(item.ranking_score * DIVERSITY_PENALTY, 4),
                    execution_state=item.execution_state,
                    reason=item.reason,
                )
                adjusted_items.append(adjusted_item)
                penalties_applied += 1
            else:
                adjusted_items.append(item)
        
        return adjusted_items, penalties_applied
    
    # ═══════════════════════════════════════════════════════════
    # 6. Full Ranking Pipeline
    # ═══════════════════════════════════════════════════════════
    
    def rank_hypotheses(
        self,
        pool: HypothesisPool,
    ) -> RankedHypothesisPool:
        """
        Apply full ranking pipeline.
        
        Steps:
        1. Duplicate suppression
        2. Dominance penalty
        3. Diversity penalty
        4. Re-sort by ranking_score
        5. Limit to max pool size
        """
        items = list(pool.hypotheses)
        
        # Step 1: Duplicate suppression
        items, duplicates_removed = self.apply_duplicate_suppression(items)
        
        # Step 2: Dominance penalty
        items, dominance_applied = self.apply_dominance_penalty(items)
        
        # Step 3: Diversity penalty
        items, diversity_penalties = self.apply_diversity_penalty(items)
        
        # Step 4: Re-sort by ranking_score
        items.sort(key=lambda x: x.ranking_score, reverse=True)
        
        # Step 5: Limit to max pool size
        items = items[:MAX_POOL_SIZE]
        
        # Calculate metrics
        directional_balance = self.calculate_directional_balance(items)
        pool_confidence = self._calculate_pool_confidence(items)
        pool_reliability = self._calculate_pool_reliability(items)
        top_hypothesis = items[0].hypothesis_type if items else "NO_EDGE"
        
        ranked_pool = RankedHypothesisPool(
            symbol=pool.symbol,
            hypotheses=items,
            top_hypothesis=top_hypothesis,
            directional_balance=directional_balance,
            pool_confidence=pool_confidence,
            pool_reliability=pool_reliability,
            pool_size=len(items),
            duplicates_removed=duplicates_removed,
            dominance_penalty_applied=dominance_applied,
            diversity_penalties_applied=diversity_penalties,
        )
        
        # Store
        self._store_ranked_pool(pool.symbol, ranked_pool)
        
        return ranked_pool
    
    # ═══════════════════════════════════════════════════════════
    # 7. Generate Ranked Pool from Symbol
    # ═══════════════════════════════════════════════════════════
    
    def generate_ranked_pool(self, symbol: str) -> RankedHypothesisPool:
        """
        Generate ranked pool from HypothesisPoolEngine.
        """
        from .hypothesis_pool_engine import get_hypothesis_pool_engine
        
        pool_engine = get_hypothesis_pool_engine()
        base_pool = pool_engine.generate_pool(symbol)
        
        return self.rank_hypotheses(base_pool)
    
    # ═══════════════════════════════════════════════════════════
    # 8. Pool Metrics
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_pool_confidence(self, items: List[HypothesisPoolItem]) -> float:
        """Calculate pool confidence as mean of top 3."""
        if not items:
            return 0.0
        top_n = min(3, len(items))
        confidences = [item.confidence for item in items[:top_n]]
        return round(sum(confidences) / len(confidences), 4)
    
    def _calculate_pool_reliability(self, items: List[HypothesisPoolItem]) -> float:
        """Calculate pool reliability as mean of all."""
        if not items:
            return 0.0
        reliabilities = [item.reliability for item in items]
        return round(sum(reliabilities) / len(reliabilities), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 9. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_ranked_pool(self, symbol: str, pool: RankedHypothesisPool) -> None:
        """Store ranked pool in history."""
        if symbol not in self._ranked_pools:
            self._ranked_pools[symbol] = []
        self._ranked_pools[symbol].append(pool)
        self._current[symbol] = pool
    
    def get_ranked_pool(self, symbol: str) -> Optional[RankedHypothesisPool]:
        """Get current ranked pool for symbol."""
        return self._current.get(symbol)
    
    def get_history(self, symbol: str, limit: int = 100) -> List[RankedHypothesisPool]:
        """Get ranked pool history for symbol."""
        history = self._ranked_pools.get(symbol, [])
        return sorted(history, key=lambda p: p.created_at, reverse=True)[:limit]


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_ranking_engine: Optional[HypothesisRankingEngine] = None


def get_hypothesis_ranking_engine() -> HypothesisRankingEngine:
    """Get singleton instance of HypothesisRankingEngine."""
    global _ranking_engine
    if _ranking_engine is None:
        _ranking_engine = HypothesisRankingEngine()
    return _ranking_engine
