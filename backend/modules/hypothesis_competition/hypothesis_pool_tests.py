"""
Hypothesis Pool Engine — Tests

PHASE 30.1 — 18+ tests for Hypothesis Pool Engine

Tests:
1. pool generation from multiple hypotheses
2. confidence threshold filter
3. reliability threshold filter
4. unfavorable execution excluded
5. NO_EDGE fallback when no candidates
6. ranking_score calculation
7. ranking_score bounds
8. sort order correct
9. top_hypothesis selected correctly
10. max pool size = 5
11. pool_confidence top-3 mean
12. pool_reliability mean
13. pool endpoint valid
14. summary endpoint valid
15. history endpoint valid
16. recompute endpoint valid
17. integration with hypothesis engine
18. empty pool edge case
"""

import pytest
from datetime import datetime

from modules.hypothesis_competition.hypothesis_pool_engine import (
    HypothesisPoolEngine,
    get_hypothesis_pool_engine,
)
from modules.hypothesis_competition.hypothesis_pool_types import (
    HypothesisPoolItem,
    HypothesisPool,
    CONFIDENCE_THRESHOLD,
    RELIABILITY_THRESHOLD,
    MAX_POOL_SIZE,
    RANKING_WEIGHT_CONFIDENCE,
    RANKING_WEIGHT_RELIABILITY,
    RANKING_WEIGHT_EXECUTION,
)


# ══════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════

def create_pool_engine():
    """Create isolated pool engine for testing."""
    engine = HypothesisPoolEngine()
    engine._pools = {}
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
):
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


# ══════════════════════════════════════════════════════════════
# Test 1: Pool Generation from Multiple Hypotheses
# ══════════════════════════════════════════════════════════════

def test_pool_generation():
    """Test that pool generates with multiple hypotheses."""
    engine = create_pool_engine()
    pool = engine.generate_pool("BTC")
    
    assert pool.symbol == "BTC"
    assert isinstance(pool.hypotheses, list)
    assert pool.pool_size <= MAX_POOL_SIZE


# ══════════════════════════════════════════════════════════════
# Test 2: Confidence Threshold Filter
# ══════════════════════════════════════════════════════════════

def test_confidence_threshold_filter():
    """Test that hypotheses below confidence threshold are excluded."""
    engine = create_pool_engine()
    
    # Low confidence should be excluded
    is_valid = engine.is_valid_for_pool(
        hypothesis_type="BULLISH_CONTINUATION",
        confidence=0.25,  # Below 0.30 threshold
        reliability=0.50,
        execution_state="CAUTIOUS",
    )
    assert is_valid is False
    
    # Above threshold should be valid
    is_valid = engine.is_valid_for_pool(
        hypothesis_type="BULLISH_CONTINUATION",
        confidence=0.35,  # Above 0.30 threshold
        reliability=0.50,
        execution_state="CAUTIOUS",
    )
    assert is_valid is True


# ══════════════════════════════════════════════════════════════
# Test 3: Reliability Threshold Filter
# ══════════════════════════════════════════════════════════════

def test_reliability_threshold_filter():
    """Test that hypotheses below reliability threshold are excluded."""
    engine = create_pool_engine()
    
    # Low reliability should be excluded
    is_valid = engine.is_valid_for_pool(
        hypothesis_type="BULLISH_CONTINUATION",
        confidence=0.50,
        reliability=0.20,  # Below 0.25 threshold
        execution_state="CAUTIOUS",
    )
    assert is_valid is False
    
    # Above threshold should be valid
    is_valid = engine.is_valid_for_pool(
        hypothesis_type="BULLISH_CONTINUATION",
        confidence=0.50,
        reliability=0.30,  # Above 0.25 threshold
        execution_state="CAUTIOUS",
    )
    assert is_valid is True


# ══════════════════════════════════════════════════════════════
# Test 4: Unfavorable Execution Excluded
# ══════════════════════════════════════════════════════════════

def test_unfavorable_execution_excluded():
    """Test that UNFAVORABLE execution state excludes hypothesis."""
    engine = create_pool_engine()
    
    is_valid = engine.is_valid_for_pool(
        hypothesis_type="BULLISH_CONTINUATION",
        confidence=0.70,
        reliability=0.60,
        execution_state="UNFAVORABLE",
    )
    assert is_valid is False


# ══════════════════════════════════════════════════════════════
# Test 5: NO_EDGE Fallback When No Candidates
# ══════════════════════════════════════════════════════════════

def test_no_edge_fallback():
    """Test NO_EDGE is excluded normally but used as fallback."""
    engine = create_pool_engine()
    
    # NO_EDGE should not be valid for normal pool
    is_valid = engine.is_valid_for_pool(
        hypothesis_type="NO_EDGE",
        confidence=0.50,
        reliability=0.50,
        execution_state="CAUTIOUS",
    )
    assert is_valid is False
    
    # Fallback should exist
    fallback = engine._get_no_edge_fallback("BTC")
    assert fallback.hypothesis_type == "NO_EDGE"


# ══════════════════════════════════════════════════════════════
# Test 6: Ranking Score Calculation
# ══════════════════════════════════════════════════════════════

def test_ranking_score_calculation():
    """Test ranking score formula."""
    engine = create_pool_engine()
    
    score = engine.calculate_ranking_score(
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
# Test 7: Ranking Score Bounds
# ══════════════════════════════════════════════════════════════

def test_ranking_score_bounds():
    """Test ranking score is bounded [0, 1]."""
    engine = create_pool_engine()
    
    # Test min
    score = engine.calculate_ranking_score(0.0, 0.0, 0.0)
    assert score >= 0.0
    
    # Test max
    score = engine.calculate_ranking_score(1.0, 1.0, 1.0)
    assert score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 8: Sort Order Correct
# ══════════════════════════════════════════════════════════════

def test_sort_order_correct():
    """Test that pool is sorted by ranking_score descending."""
    engine = create_pool_engine()
    pool = engine.generate_pool("ETH")
    
    # Check sort order
    for i in range(len(pool.hypotheses) - 1):
        assert pool.hypotheses[i].ranking_score >= pool.hypotheses[i + 1].ranking_score


# ══════════════════════════════════════════════════════════════
# Test 9: Top Hypothesis Selected Correctly
# ══════════════════════════════════════════════════════════════

def test_top_hypothesis_selected():
    """Test that top_hypothesis is first in pool."""
    engine = create_pool_engine()
    pool = engine.generate_pool("SOL")
    
    if pool.hypotheses:
        assert pool.top_hypothesis == pool.hypotheses[0].hypothesis_type


# ══════════════════════════════════════════════════════════════
# Test 10: Max Pool Size = 5
# ══════════════════════════════════════════════════════════════

def test_max_pool_size():
    """Test that pool is limited to 5 hypotheses."""
    engine = create_pool_engine()
    pool = engine.generate_pool("BTC")
    
    assert pool.pool_size <= MAX_POOL_SIZE
    assert len(pool.hypotheses) <= MAX_POOL_SIZE


# ══════════════════════════════════════════════════════════════
# Test 11: Pool Confidence Top-3 Mean
# ══════════════════════════════════════════════════════════════

def test_pool_confidence_calculation():
    """Test pool_confidence is mean of top 3."""
    engine = create_pool_engine()
    
    items = [
        create_pool_item(confidence=0.70),
        create_pool_item(confidence=0.60, hypothesis_type="BREAKOUT_FORMING"),
        create_pool_item(confidence=0.50, hypothesis_type="RANGE_MEAN_REVERSION"),
        create_pool_item(confidence=0.40, hypothesis_type="BEARISH_CONTINUATION"),
    ]
    
    conf = engine._calculate_pool_confidence(items)
    # Mean of top 3: (0.70 + 0.60 + 0.50) / 3 = 0.60
    expected = (0.70 + 0.60 + 0.50) / 3
    
    assert abs(conf - expected) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 12: Pool Reliability Mean
# ══════════════════════════════════════════════════════════════

def test_pool_reliability_calculation():
    """Test pool_reliability is mean of all."""
    engine = create_pool_engine()
    
    items = [
        create_pool_item(reliability=0.60),
        create_pool_item(reliability=0.50, hypothesis_type="BREAKOUT_FORMING"),
        create_pool_item(reliability=0.40, hypothesis_type="RANGE_MEAN_REVERSION"),
    ]
    
    rel = engine._calculate_pool_reliability(items)
    # Mean: (0.60 + 0.50 + 0.40) / 3 = 0.50
    expected = (0.60 + 0.50 + 0.40) / 3
    
    assert abs(rel - expected) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 13: Pool Endpoint Valid (simulated)
# ══════════════════════════════════════════════════════════════

def test_pool_endpoint_simulated():
    """Test pool endpoint simulation."""
    engine = create_pool_engine()
    pool = engine.generate_pool("BTC")
    
    # Simulate API response
    response = {
        "symbol": pool.symbol,
        "hypotheses": [h.model_dump() for h in pool.hypotheses],
        "top_hypothesis": pool.top_hypothesis,
        "pool_confidence": pool.pool_confidence,
        "pool_size": pool.pool_size,
    }
    
    assert response["symbol"] == "BTC"
    assert "hypotheses" in response


# ══════════════════════════════════════════════════════════════
# Test 14: Summary Endpoint Valid (simulated)
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_simulated():
    """Test summary endpoint simulation."""
    engine = create_pool_engine()
    
    for _ in range(5):
        engine.generate_pool("ETH")
    
    summary = engine.get_summary("ETH")
    
    assert summary.symbol == "ETH"
    assert summary.total_pools == 5


# ══════════════════════════════════════════════════════════════
# Test 15: History Endpoint Valid (simulated)
# ══════════════════════════════════════════════════════════════

def test_history_endpoint_simulated():
    """Test history endpoint simulation."""
    engine = create_pool_engine()
    
    for _ in range(3):
        engine.generate_pool("SOL")
    
    history = engine.get_history("SOL", limit=10)
    
    assert len(history) == 3


# ══════════════════════════════════════════════════════════════
# Test 16: Recompute Endpoint Valid (simulated)
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint_simulated():
    """Test recompute endpoint simulation."""
    engine = create_pool_engine()
    
    pool1 = engine.generate_pool("AVAX")
    pool2 = engine.generate_pool("AVAX")
    
    # Both should be valid
    assert pool1.symbol == "AVAX"
    assert pool2.symbol == "AVAX"
    
    # History should have 2
    history = engine.get_history("AVAX")
    assert len(history) == 2


# ══════════════════════════════════════════════════════════════
# Test 17: Integration with Hypothesis Engine
# ══════════════════════════════════════════════════════════════

def test_integration_hypothesis_engine():
    """Test integration with hypothesis engine."""
    engine = create_pool_engine()
    pool = engine.generate_pool("BTC")
    
    # Should generate valid pool
    assert pool.symbol == "BTC"
    assert pool.top_hypothesis in [
        "BULLISH_CONTINUATION",
        "BEARISH_CONTINUATION",
        "BREAKOUT_FORMING",
        "RANGE_MEAN_REVERSION",
        "NO_EDGE",
        "SHORT_SQUEEZE_SETUP",
        "LONG_SQUEEZE_SETUP",
        "VOLATILE_UNWIND",
        "BREAKOUT_FAILURE_RISK",
    ]


# ══════════════════════════════════════════════════════════════
# Test 18: Empty Pool Edge Case
# ══════════════════════════════════════════════════════════════

def test_empty_pool_edge_case():
    """Test edge case when no valid hypotheses."""
    engine = create_pool_engine()
    
    # Empty items should have 0 confidence
    conf = engine._calculate_pool_confidence([])
    assert conf == 0.0
    
    rel = engine._calculate_pool_reliability([])
    assert rel == 0.0


# ══════════════════════════════════════════════════════════════
# Test 19: Symbol Isolation
# ══════════════════════════════════════════════════════════════

def test_symbol_isolation():
    """Test that pools are isolated by symbol."""
    engine = create_pool_engine()
    
    engine.generate_pool("BTC")
    engine.generate_pool("ETH")
    
    btc_pool = engine.get_pool("BTC")
    eth_pool = engine.get_pool("ETH")
    
    assert btc_pool.symbol == "BTC"
    assert eth_pool.symbol == "ETH"


# ══════════════════════════════════════════════════════════════
# Test 20: Pool History Tracking
# ══════════════════════════════════════════════════════════════

def test_pool_history_tracking():
    """Test that pools are tracked in history."""
    engine = create_pool_engine()
    
    for _ in range(5):
        engine.generate_pool("DOGE")
    
    history = engine.get_history("DOGE", limit=3)
    
    # Should respect limit
    assert len(history) == 3
    
    # Should be sorted newest first
    for i in range(len(history) - 1):
        assert history[i].created_at >= history[i + 1].created_at


# ══════════════════════════════════════════════════════════════
# Run tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
