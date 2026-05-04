"""
Hypothesis Ranking Engine — Tests

PHASE 30.2 — 20+ tests for Hypothesis Ranking Engine

Tests:
1. base_score calculation
2. duplicate suppression
3. duplicate strongest retained
4. directional clustering detection
5. dominance penalty applied
6. diversity penalty applied
7. ranking_score bounds
8. ranking order correct
9. max pool size respected
10. directional_balance calculation
11. ranked endpoint valid
12. integration with pool engine
13. empty pool safe
14. single hypothesis safe
15. similarity threshold logic
16. conflict state preserved
17. execution_state preserved
18. top_hypothesis correct
19. ranking deterministic
20. recompute endpoint valid
"""

import pytest
from datetime import datetime

from modules.hypothesis_competition.hypothesis_ranking_engine import (
    HypothesisRankingEngine,
    get_hypothesis_ranking_engine,
    RankedHypothesisPool,
    DOMINANCE_THRESHOLD,
    DOMINANCE_PENALTY,
    SIMILARITY_THRESHOLD,
    DIVERSITY_PENALTY,
)
from modules.hypothesis_competition.hypothesis_pool_types import (
    HypothesisPoolItem,
    HypothesisPool,
    RANKING_WEIGHT_CONFIDENCE,
    RANKING_WEIGHT_RELIABILITY,
    RANKING_WEIGHT_EXECUTION,
    MAX_POOL_SIZE,
)


# ══════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════

def create_ranking_engine():
    """Create isolated ranking engine for testing."""
    engine = HypothesisRankingEngine()
    engine._ranked_pools = {}
    engine._current = {}
    return engine


def create_pool_item(
    hypothesis_type="BULLISH_CONTINUATION",
    directional_bias="LONG",
    confidence=0.65,
    reliability=0.55,
    structural_score=0.70,
    execution_score=0.60,
    conflict_score=0.10,
    execution_state="CAUTIOUS",
    ranking_score=None,
):
    if ranking_score is None:
        ranking_score = (
            RANKING_WEIGHT_CONFIDENCE * confidence
            + RANKING_WEIGHT_RELIABILITY * reliability
            + RANKING_WEIGHT_EXECUTION * execution_score
        )
    return HypothesisPoolItem(
        hypothesis_type=hypothesis_type,
        directional_bias=directional_bias,
        confidence=confidence,
        reliability=reliability,
        structural_score=structural_score,
        execution_score=execution_score,
        conflict_score=conflict_score,
        ranking_score=round(ranking_score, 4),
        execution_state=execution_state,
        reason="test hypothesis",
    )


def create_pool(symbol="BTC", items=None):
    if items is None:
        items = [create_pool_item()]
    return HypothesisPool(
        symbol=symbol,
        hypotheses=items,
        top_hypothesis=items[0].hypothesis_type if items else "NO_EDGE",
        pool_confidence=0.65,
        pool_reliability=0.55,
        pool_size=len(items),
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Base Score Calculation
# ══════════════════════════════════════════════════════════════

def test_base_score_calculation():
    """Test base ranking score formula."""
    engine = create_ranking_engine()
    
    score = engine.calculate_base_score(
        confidence=0.70,
        reliability=0.60,
        execution_score=0.50,
    )
    
    # 0.50*0.70 + 0.30*0.60 + 0.20*0.50 = 0.35 + 0.18 + 0.10 = 0.63
    expected = (
        RANKING_WEIGHT_CONFIDENCE * 0.70
        + RANKING_WEIGHT_RELIABILITY * 0.60
        + RANKING_WEIGHT_EXECUTION * 0.50
    )
    
    assert abs(score - round(expected, 4)) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 2: Duplicate Suppression
# ══════════════════════════════════════════════════════════════

def test_duplicate_suppression():
    """Test that duplicates are removed."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(hypothesis_type="BREAKOUT_FORMING", ranking_score=0.66),
        create_pool_item(hypothesis_type="BREAKOUT_FORMING", ranking_score=0.61),
        create_pool_item(hypothesis_type="BREAKOUT_FORMING", ranking_score=0.58),
        create_pool_item(hypothesis_type="BULLISH_CONTINUATION", ranking_score=0.64),
    ]
    
    filtered, removed = engine.apply_duplicate_suppression(items)
    
    assert removed == 2  # 2 BREAKOUT_FORMING duplicates removed
    assert len(filtered) == 2  # BREAKOUT_FORMING + BULLISH_CONTINUATION


# ══════════════════════════════════════════════════════════════
# Test 3: Duplicate Strongest Retained
# ══════════════════════════════════════════════════════════════

def test_duplicate_strongest_retained():
    """Test that strongest duplicate is retained."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(hypothesis_type="BREAKOUT_FORMING", ranking_score=0.58),
        create_pool_item(hypothesis_type="BREAKOUT_FORMING", ranking_score=0.66),  # Strongest
        create_pool_item(hypothesis_type="BREAKOUT_FORMING", ranking_score=0.61),
    ]
    
    filtered, _ = engine.apply_duplicate_suppression(items)
    
    assert len(filtered) == 1
    assert filtered[0].ranking_score == 0.66  # Strongest kept


# ══════════════════════════════════════════════════════════════
# Test 4: Directional Clustering Detection
# ══════════════════════════════════════════════════════════════

def test_directional_clustering():
    """Test directional clustering groups hypotheses correctly."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(directional_bias="LONG"),
        create_pool_item(directional_bias="LONG", hypothesis_type="BREAKOUT_FORMING"),
        create_pool_item(directional_bias="SHORT", hypothesis_type="BEARISH_CONTINUATION"),
        create_pool_item(directional_bias="NEUTRAL", hypothesis_type="RANGE_MEAN_REVERSION"),
    ]
    
    groups = engine.get_directional_groups(items)
    
    assert len(groups["LONG"]) == 2
    assert len(groups["SHORT"]) == 1
    assert len(groups["NEUTRAL"]) == 1


# ══════════════════════════════════════════════════════════════
# Test 5: Dominance Penalty Applied
# ══════════════════════════════════════════════════════════════

def test_dominance_penalty_applied():
    """Test that dominance penalty is applied when ≥3 in same direction."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(directional_bias="LONG", ranking_score=0.70, hypothesis_type="H1"),
        create_pool_item(directional_bias="LONG", ranking_score=0.65, hypothesis_type="H2"),
        create_pool_item(directional_bias="LONG", ranking_score=0.60, hypothesis_type="H3"),
        create_pool_item(directional_bias="SHORT", ranking_score=0.55, hypothesis_type="H4"),
    ]
    
    adjusted, penalty_applied = engine.apply_dominance_penalty(items)
    
    assert penalty_applied is True
    
    # LONG items should be penalized
    for item in adjusted:
        if item.directional_bias == "LONG":
            original = next(i for i in items if i.hypothesis_type == item.hypothesis_type)
            assert item.ranking_score == round(original.ranking_score * DOMINANCE_PENALTY, 4)
        else:
            # SHORT not penalized
            assert item.ranking_score == 0.55


# ══════════════════════════════════════════════════════════════
# Test 6: Diversity Penalty Applied
# ══════════════════════════════════════════════════════════════

def test_diversity_penalty_applied():
    """Test that diversity penalty is applied for similar structures."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(structural_score=0.70, hypothesis_type="H1"),
        create_pool_item(structural_score=0.72, hypothesis_type="H2"),  # Similar to H1 (diff=0.02)
        create_pool_item(structural_score=0.50, hypothesis_type="H3"),  # Different
    ]
    
    adjusted, penalties = engine.apply_diversity_penalty(items)
    
    assert penalties >= 1  # At least one penalty applied


# ══════════════════════════════════════════════════════════════
# Test 7: Ranking Score Bounds
# ══════════════════════════════════════════════════════════════

def test_ranking_score_bounds():
    """Test ranking score is bounded [0, 1]."""
    engine = create_ranking_engine()
    
    # Test min
    score = engine.calculate_base_score(0.0, 0.0, 0.0)
    assert score >= 0.0
    
    # Test max
    score = engine.calculate_base_score(1.0, 1.0, 1.0)
    assert score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 8: Ranking Order Correct
# ══════════════════════════════════════════════════════════════

def test_ranking_order_correct():
    """Test that final pool is sorted by ranking_score descending."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(ranking_score=0.50, hypothesis_type="H1"),
        create_pool_item(ranking_score=0.70, hypothesis_type="H2"),
        create_pool_item(ranking_score=0.60, hypothesis_type="H3"),
    ]
    
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    # Check sort order
    for i in range(len(ranked.hypotheses) - 1):
        assert ranked.hypotheses[i].ranking_score >= ranked.hypotheses[i + 1].ranking_score


# ══════════════════════════════════════════════════════════════
# Test 9: Max Pool Size Respected
# ══════════════════════════════════════════════════════════════

def test_max_pool_size_respected():
    """Test that pool is limited to MAX_POOL_SIZE."""
    engine = create_ranking_engine()
    
    # Create 10 unique items
    items = [
        create_pool_item(hypothesis_type=f"TYPE_{i}", ranking_score=0.5 + i * 0.05)
        for i in range(10)
    ]
    
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    assert ranked.pool_size <= MAX_POOL_SIZE


# ══════════════════════════════════════════════════════════════
# Test 10: Directional Balance Calculation
# ══════════════════════════════════════════════════════════════

def test_directional_balance_calculation():
    """Test directional_balance is calculated correctly."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(directional_bias="LONG", hypothesis_type="H1"),
        create_pool_item(directional_bias="LONG", hypothesis_type="H2"),
        create_pool_item(directional_bias="SHORT", hypothesis_type="H3"),
        create_pool_item(directional_bias="NEUTRAL", hypothesis_type="H4"),
    ]
    
    balance = engine.calculate_directional_balance(items)
    
    assert balance["LONG"] == 2
    assert balance["SHORT"] == 1
    assert balance["NEUTRAL"] == 1


# ══════════════════════════════════════════════════════════════
# Test 11: Ranked Endpoint Valid (simulated)
# ══════════════════════════════════════════════════════════════

def test_ranked_endpoint_simulated():
    """Test ranked endpoint simulation."""
    engine = create_ranking_engine()
    ranked = engine.generate_ranked_pool("BTC")
    
    # Simulate API response
    response = {
        "symbol": ranked.symbol,
        "hypotheses": [h.model_dump() for h in ranked.hypotheses],
        "top_hypothesis": ranked.top_hypothesis,
        "directional_balance": ranked.directional_balance,
        "pool_size": ranked.pool_size,
    }
    
    assert response["symbol"] == "BTC"
    assert "directional_balance" in response


# ══════════════════════════════════════════════════════════════
# Test 12: Integration with Pool Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_pool_engine():
    """Test integration with HypothesisPoolEngine."""
    engine = create_ranking_engine()
    ranked = engine.generate_ranked_pool("ETH")
    
    assert ranked.symbol == "ETH"
    assert ranked.top_hypothesis is not None


# ══════════════════════════════════════════════════════════════
# Test 13: Empty Pool Safe
# ══════════════════════════════════════════════════════════════

def test_empty_pool_safe():
    """Test handling of empty pool."""
    engine = create_ranking_engine()
    
    pool = create_pool(items=[])
    ranked = engine.rank_hypotheses(pool)
    
    assert ranked.pool_size == 0
    assert ranked.top_hypothesis == "NO_EDGE"


# ══════════════════════════════════════════════════════════════
# Test 14: Single Hypothesis Safe
# ══════════════════════════════════════════════════════════════

def test_single_hypothesis_safe():
    """Test handling of single hypothesis."""
    engine = create_ranking_engine()
    
    items = [create_pool_item(hypothesis_type="BULLISH_CONTINUATION")]
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    assert ranked.pool_size == 1
    assert ranked.top_hypothesis == "BULLISH_CONTINUATION"


# ══════════════════════════════════════════════════════════════
# Test 15: Similarity Threshold Logic
# ══════════════════════════════════════════════════════════════

def test_similarity_threshold_logic():
    """Test that similarity threshold is respected."""
    engine = create_ranking_engine()
    
    # Items with diff > threshold should not be penalized
    items = [
        create_pool_item(structural_score=0.70, hypothesis_type="H1"),
        create_pool_item(structural_score=0.60, hypothesis_type="H2"),  # diff=0.10 > 0.05
    ]
    
    _, penalties = engine.apply_diversity_penalty(items)
    
    assert penalties == 0  # No penalty for different structures


# ══════════════════════════════════════════════════════════════
# Test 16: Conflict State Preserved
# ══════════════════════════════════════════════════════════════

def test_conflict_state_preserved():
    """Test that conflict_score is preserved through ranking."""
    engine = create_ranking_engine()
    
    items = [create_pool_item(conflict_score=0.15)]
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    assert ranked.hypotheses[0].conflict_score == 0.15


# ══════════════════════════════════════════════════════════════
# Test 17: Execution State Preserved
# ══════════════════════════════════════════════════════════════

def test_execution_state_preserved():
    """Test that execution_state is preserved through ranking."""
    engine = create_ranking_engine()
    
    items = [create_pool_item(execution_state="FAVORABLE")]
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    assert ranked.hypotheses[0].execution_state == "FAVORABLE"


# ══════════════════════════════════════════════════════════════
# Test 18: Top Hypothesis Correct
# ══════════════════════════════════════════════════════════════

def test_top_hypothesis_correct():
    """Test that top_hypothesis is first in sorted pool."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(hypothesis_type="H1", ranking_score=0.50),
        create_pool_item(hypothesis_type="H2", ranking_score=0.70),
        create_pool_item(hypothesis_type="H3", ranking_score=0.60),
    ]
    
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    assert ranked.top_hypothesis == ranked.hypotheses[0].hypothesis_type


# ══════════════════════════════════════════════════════════════
# Test 19: Ranking Deterministic
# ══════════════════════════════════════════════════════════════

def test_ranking_deterministic():
    """Test that ranking produces same result for same input."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(hypothesis_type="H1", ranking_score=0.65),
        create_pool_item(hypothesis_type="H2", ranking_score=0.60),
    ]
    
    pool1 = create_pool(items=items)
    pool2 = create_pool(items=items)
    
    ranked1 = engine.rank_hypotheses(pool1)
    ranked2 = engine.rank_hypotheses(pool2)
    
    assert ranked1.top_hypothesis == ranked2.top_hypothesis
    assert len(ranked1.hypotheses) == len(ranked2.hypotheses)


# ══════════════════════════════════════════════════════════════
# Test 20: Recompute Endpoint Valid (simulated)
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint_simulated():
    """Test recompute endpoint simulation."""
    engine = create_ranking_engine()
    
    ranked1 = engine.generate_ranked_pool("SOL")
    ranked2 = engine.generate_ranked_pool("SOL")
    
    assert ranked1.symbol == "SOL"
    assert ranked2.symbol == "SOL"
    
    # History should have 2 entries
    history = engine.get_history("SOL")
    assert len(history) == 2


# ══════════════════════════════════════════════════════════════
# Test 21: Dominance Not Applied When Below Threshold
# ══════════════════════════════════════════════════════════════

def test_dominance_not_applied_below_threshold():
    """Test that dominance penalty is NOT applied when < 3 in same direction."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(directional_bias="LONG", ranking_score=0.70, hypothesis_type="H1"),
        create_pool_item(directional_bias="LONG", ranking_score=0.65, hypothesis_type="H2"),
        create_pool_item(directional_bias="SHORT", ranking_score=0.55, hypothesis_type="H3"),
    ]
    
    adjusted, penalty_applied = engine.apply_dominance_penalty(items)
    
    assert penalty_applied is False  # Only 2 LONG, threshold is 3


# ══════════════════════════════════════════════════════════════
# Test 22: Pool Reliability Calculation
# ══════════════════════════════════════════════════════════════

def test_pool_reliability_calculation():
    """Test pool reliability is mean of all."""
    engine = create_ranking_engine()
    
    items = [
        create_pool_item(reliability=0.60, hypothesis_type="H1"),
        create_pool_item(reliability=0.50, hypothesis_type="H2"),
        create_pool_item(reliability=0.40, hypothesis_type="H3"),
    ]
    
    pool = create_pool(items=items)
    ranked = engine.rank_hypotheses(pool)
    
    # Mean: (0.60 + 0.50 + 0.40) / 3 = 0.50
    expected = (0.60 + 0.50 + 0.40) / 3
    assert abs(ranked.pool_reliability - expected) < 0.01


# ══════════════════════════════════════════════════════════════
# Run tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
