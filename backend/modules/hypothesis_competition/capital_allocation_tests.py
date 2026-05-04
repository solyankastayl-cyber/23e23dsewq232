"""
Capital Allocation Engine Tests

PHASE 30.3 — 22+ tests for Capital Allocation Engine

Tests:
1. Base weight calculation
2. Normalization correct
3. Execution_state modifier applied
4. Unfavorable removed
5. Neutral allocation cap
6. Directional exposure cap
7. Min allocation threshold
8. Renormalization correct
9. Portfolio_confidence calculation
10. Portfolio_reliability calculation
11. Capital_percent correct
12. Sum weights = 1
13. Portfolio endpoint valid
14. Summary endpoint valid
15. History endpoint valid
16. Recompute endpoint valid
17. Single hypothesis case
18. Empty pool case
19. Deterministic output
20. Integration with ranking engine
21. Integration with pool engine
22. Directional balance preserved
"""

import pytest
from datetime import datetime, timezone
from typing import List

from modules.hypothesis_competition.capital_allocation_engine import (
    CapitalAllocationEngine,
    get_capital_allocation_engine,
)
from modules.hypothesis_competition.capital_allocation_types import (
    HypothesisAllocation,
    HypothesisCapitalAllocation,
    EXECUTION_STATE_MODIFIERS,
    MAX_DIRECTIONAL_EXPOSURE,
    MAX_NEUTRAL_ALLOCATION,
    MIN_ALLOCATION_THRESHOLD,
)
from modules.hypothesis_competition.hypothesis_pool_types import (
    HypothesisPoolItem,
    HypothesisPool,
)
from modules.hypothesis_competition.hypothesis_ranking_engine import (
    RankedHypothesisPool,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

def create_test_item(
    hypothesis_type: str = "BULLISH_CONTINUATION",
    directional_bias: str = "LONG",
    confidence: float = 0.6,
    reliability: float = 0.5,
    ranking_score: float = 0.55,
    execution_state: str = "FAVORABLE",
) -> HypothesisPoolItem:
    """Create test hypothesis pool item."""
    return HypothesisPoolItem(
        hypothesis_type=hypothesis_type,
        directional_bias=directional_bias,
        confidence=confidence,
        reliability=reliability,
        structural_score=0.5,
        execution_score=0.5,
        conflict_score=0.1,
        ranking_score=ranking_score,
        execution_state=execution_state,
        reason="test reason",
    )


def create_test_ranked_pool(
    symbol: str = "BTC",
    items: List[HypothesisPoolItem] = None,
) -> RankedHypothesisPool:
    """Create test ranked pool."""
    if items is None:
        items = [
            create_test_item("BREAKOUT_FORMING", "LONG", 0.66, 0.55, 0.66),
            create_test_item("RANGE_MEAN_REVERSION", "NEUTRAL", 0.52, 0.48, 0.52),
            create_test_item("BEARISH_CONTINUATION", "SHORT", 0.49, 0.45, 0.49),
        ]
    
    return RankedHypothesisPool(
        symbol=symbol,
        hypotheses=items,
        top_hypothesis=items[0].hypothesis_type if items else "NO_EDGE",
        directional_balance={"LONG": 1, "SHORT": 1, "NEUTRAL": 1},
        pool_confidence=0.56,
        pool_reliability=0.49,
        pool_size=len(items),
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Base Weight Calculation
# ══════════════════════════════════════════════════════════════

def test_base_weight_calculation():
    """Test base weight calculation proportional to ranking_score."""
    engine = CapitalAllocationEngine()
    
    items = [
        create_test_item(ranking_score=0.6),
        create_test_item(ranking_score=0.4),
    ]
    
    weighted = engine.calculate_base_weights(items)
    
    assert len(weighted) == 2
    assert weighted[0][1] == 0.6  # 0.6 / (0.6 + 0.4)
    assert weighted[1][1] == 0.4  # 0.4 / (0.6 + 0.4)


# ══════════════════════════════════════════════════════════════
# Test 2: Normalization Correct
# ══════════════════════════════════════════════════════════════

def test_normalization_correct():
    """Test that normalized weights sum to 1.0."""
    engine = CapitalAllocationEngine()
    
    items = [
        create_test_item(ranking_score=0.3),
        create_test_item(ranking_score=0.5),
        create_test_item(ranking_score=0.2),
    ]
    
    weighted = engine.calculate_base_weights(items)
    total = sum(w for _, w in weighted)
    
    assert abs(total - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 3: Execution State Modifier Applied
# ══════════════════════════════════════════════════════════════

def test_execution_state_modifier_applied():
    """Test execution state modifiers are applied correctly."""
    engine = CapitalAllocationEngine()
    
    items = [
        (create_test_item(execution_state="FAVORABLE"), 0.5),
        (create_test_item(execution_state="CAUTIOUS"), 0.5),
    ]
    
    adjusted = engine.apply_execution_state_adjustment(items)
    
    assert adjusted[0][1] == 0.5  # FAVORABLE: 0.5 * 1.0
    assert adjusted[1][1] == 0.4  # CAUTIOUS: 0.5 * 0.8


# ══════════════════════════════════════════════════════════════
# Test 4: Unfavorable Removed
# ══════════════════════════════════════════════════════════════

def test_unfavorable_removed():
    """Test unfavorable hypotheses are removed."""
    engine = CapitalAllocationEngine()
    
    items = [
        (create_test_item(execution_state="FAVORABLE"), 0.5),
        (create_test_item(execution_state="UNFAVORABLE"), 0.5),
    ]
    
    # Apply modifier first (UNFAVORABLE becomes 0)
    adjusted = engine.apply_execution_state_adjustment(items)
    filtered, removed = engine.remove_unfavorable(adjusted)
    
    assert len(filtered) == 1
    assert removed == 1
    assert filtered[0][0].execution_state == "FAVORABLE"


# ══════════════════════════════════════════════════════════════
# Test 5: Neutral Allocation Cap
# ══════════════════════════════════════════════════════════════

def test_neutral_allocation_cap():
    """Test neutral hypotheses are capped at 30%."""
    engine = CapitalAllocationEngine()
    
    items = [
        (create_test_item(directional_bias="NEUTRAL"), 0.5),
        (create_test_item(directional_bias="LONG"), 0.5),
    ]
    
    adjusted, cap_applied = engine.apply_neutral_cap(items)
    
    assert cap_applied == True
    neutral_weight = sum(w for item, w in adjusted if item.directional_bias == "NEUTRAL")
    assert neutral_weight <= MAX_NEUTRAL_ALLOCATION + 0.001


# ══════════════════════════════════════════════════════════════
# Test 6: Directional Exposure Cap
# ══════════════════════════════════════════════════════════════

def test_directional_exposure_cap():
    """Test directional exposure is capped at 65%."""
    engine = CapitalAllocationEngine()
    
    items = [
        (create_test_item(directional_bias="LONG"), 0.4),
        (create_test_item(directional_bias="LONG"), 0.4),
        (create_test_item(directional_bias="SHORT"), 0.2),
    ]
    
    adjusted, cap_applied = engine.apply_directional_cap(items)
    
    assert cap_applied == True
    long_weight = sum(w for item, w in adjusted if item.directional_bias == "LONG")
    assert long_weight <= MAX_DIRECTIONAL_EXPOSURE + 0.001


# ══════════════════════════════════════════════════════════════
# Test 7: Min Allocation Threshold
# ══════════════════════════════════════════════════════════════

def test_min_allocation_threshold():
    """Test allocations below 5% are removed."""
    engine = CapitalAllocationEngine()
    
    items = [
        (create_test_item(), 0.9),
        (create_test_item(), 0.03),  # Below threshold
    ]
    
    filtered, removed = engine.apply_min_allocation_filter(items)
    
    assert len(filtered) == 1
    assert removed == 1


# ══════════════════════════════════════════════════════════════
# Test 8: Renormalization Correct
# ══════════════════════════════════════════════════════════════

def test_renormalization_correct():
    """Test weights are renormalized after filtering."""
    engine = CapitalAllocationEngine()
    
    items = [
        (create_test_item(), 0.3),
        (create_test_item(), 0.3),
    ]
    
    normalized = engine.normalize_weights(items)
    total = sum(w for _, w in normalized)
    
    assert abs(total - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 9: Portfolio Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_portfolio_confidence_calculation():
    """Test portfolio confidence is weighted sum."""
    engine = CapitalAllocationEngine()
    
    allocations = [
        HypothesisAllocation(
            hypothesis_type="BREAKOUT",
            directional_bias="LONG",
            ranking_score=0.6,
            capital_weight=0.6,
            capital_percent=60,
            execution_state="FAVORABLE",
            confidence=0.7,
            reliability=0.5,
        ),
        HypothesisAllocation(
            hypothesis_type="RANGE",
            directional_bias="NEUTRAL",
            ranking_score=0.4,
            capital_weight=0.4,
            capital_percent=40,
            execution_state="CAUTIOUS",
            confidence=0.5,
            reliability=0.4,
        ),
    ]
    
    confidence = engine.calculate_portfolio_confidence(allocations)
    expected = 0.6 * 0.7 + 0.4 * 0.5  # 0.42 + 0.20 = 0.62
    
    assert abs(confidence - expected) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 10: Portfolio Reliability Calculation
# ══════════════════════════════════════════════════════════════

def test_portfolio_reliability_calculation():
    """Test portfolio reliability is weighted sum."""
    engine = CapitalAllocationEngine()
    
    allocations = [
        HypothesisAllocation(
            hypothesis_type="BREAKOUT",
            directional_bias="LONG",
            ranking_score=0.6,
            capital_weight=0.6,
            capital_percent=60,
            execution_state="FAVORABLE",
            confidence=0.7,
            reliability=0.5,
        ),
        HypothesisAllocation(
            hypothesis_type="RANGE",
            directional_bias="NEUTRAL",
            ranking_score=0.4,
            capital_weight=0.4,
            capital_percent=40,
            execution_state="CAUTIOUS",
            confidence=0.5,
            reliability=0.4,
        ),
    ]
    
    reliability = engine.calculate_portfolio_reliability(allocations)
    expected = 0.6 * 0.5 + 0.4 * 0.4  # 0.30 + 0.16 = 0.46
    
    assert abs(reliability - expected) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 11: Capital Percent Correct
# ══════════════════════════════════════════════════════════════

def test_capital_percent_correct():
    """Test capital_percent = capital_weight * 100."""
    engine = CapitalAllocationEngine()
    ranked_pool = create_test_ranked_pool()
    
    allocation = engine.allocate_capital(ranked_pool)
    
    for a in allocation.allocations:
        expected_percent = round(a.capital_weight * 100, 2)
        assert abs(a.capital_percent - expected_percent) < 0.1


# ══════════════════════════════════════════════════════════════
# Test 12: Sum Weights = 1
# ══════════════════════════════════════════════════════════════

def test_sum_weights_equals_one():
    """Test total capital weights sum to 1.0."""
    engine = CapitalAllocationEngine()
    ranked_pool = create_test_ranked_pool()
    
    allocation = engine.allocate_capital(ranked_pool)
    
    if allocation.allocations:
        total_weight = sum(a.capital_weight for a in allocation.allocations)
        assert abs(total_weight - 1.0) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 13: Portfolio Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_portfolio_endpoint_valid():
    """Test portfolio endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.capital_allocation_routes import get_portfolio_allocation
    
    response = asyncio.get_event_loop().run_until_complete(get_portfolio_allocation("BTC"))
    
    assert "symbol" in response
    assert response["symbol"] == "BTC"
    assert "allocations" in response
    assert "portfolio_confidence" in response
    assert "portfolio_reliability" in response


# ══════════════════════════════════════════════════════════════
# Test 14: Summary Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_valid():
    """Test summary endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.capital_allocation_routes import get_portfolio_summary
    
    response = asyncio.get_event_loop().run_until_complete(get_portfolio_summary("BTC"))
    
    assert "symbol" in response
    assert "directional_distribution" in response
    assert "averages" in response


# ══════════════════════════════════════════════════════════════
# Test 15: History Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_history_endpoint_valid():
    """Test history endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.capital_allocation_routes import get_portfolio_history
    
    response = asyncio.get_event_loop().run_until_complete(get_portfolio_history("BTC"))
    
    assert "symbol" in response
    assert "total" in response
    assert "allocations" in response


# ══════════════════════════════════════════════════════════════
# Test 16: Recompute Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint_valid():
    """Test recompute endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.capital_allocation_routes import recompute_portfolio_allocation
    
    response = asyncio.get_event_loop().run_until_complete(recompute_portfolio_allocation("BTC"))
    
    assert "status" in response
    assert response["status"] == "ok"
    assert "symbol" in response
    assert "computed_at" in response


# ══════════════════════════════════════════════════════════════
# Test 17: Single Hypothesis Case
# ══════════════════════════════════════════════════════════════

def test_single_hypothesis_case():
    """Test allocation with single hypothesis."""
    engine = CapitalAllocationEngine()
    
    items = [create_test_item()]
    ranked_pool = create_test_ranked_pool("BTC", items)
    
    allocation = engine.allocate_capital(ranked_pool)
    
    assert len(allocation.allocations) == 1
    assert allocation.allocations[0].capital_weight == 1.0


# ══════════════════════════════════════════════════════════════
# Test 18: Empty Pool Case
# ══════════════════════════════════════════════════════════════

def test_empty_pool_case():
    """Test allocation with empty pool."""
    engine = CapitalAllocationEngine()
    
    ranked_pool = create_test_ranked_pool("BTC", [])
    
    allocation = engine.allocate_capital(ranked_pool)
    
    assert len(allocation.allocations) == 0
    assert allocation.portfolio_confidence == 0.0
    assert allocation.portfolio_reliability == 0.0


# ══════════════════════════════════════════════════════════════
# Test 19: Deterministic Output
# ══════════════════════════════════════════════════════════════

def test_deterministic_output():
    """Test same input produces same output."""
    engine = CapitalAllocationEngine()
    
    items = [
        create_test_item("BREAKOUT", "LONG", 0.66, 0.55, 0.66),
        create_test_item("RANGE", "NEUTRAL", 0.52, 0.48, 0.52),
    ]
    
    pool1 = create_test_ranked_pool("BTC", items.copy())
    pool2 = create_test_ranked_pool("BTC", items.copy())
    
    # Use separate engine instances to avoid history interference
    engine1 = CapitalAllocationEngine()
    engine2 = CapitalAllocationEngine()
    
    alloc1 = engine1.allocate_capital(pool1)
    alloc2 = engine2.allocate_capital(pool2)
    
    # Compare weights
    for a1, a2 in zip(alloc1.allocations, alloc2.allocations):
        assert abs(a1.capital_weight - a2.capital_weight) < 0.001


# ══════════════════════════════════════════════════════════════
# Test 20: Integration with Ranking Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_ranking_engine():
    """Test integration with HypothesisRankingEngine."""
    from modules.hypothesis_competition import get_hypothesis_ranking_engine
    
    ranking_engine = get_hypothesis_ranking_engine()
    capital_engine = CapitalAllocationEngine()
    
    # Generate ranked pool
    ranked_pool = ranking_engine.generate_ranked_pool("BTC")
    
    # Allocate capital
    allocation = capital_engine.allocate_capital(ranked_pool)
    
    assert allocation.symbol == "BTC"
    assert isinstance(allocation, HypothesisCapitalAllocation)


# ══════════════════════════════════════════════════════════════
# Test 21: Integration with Pool Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_pool_engine():
    """Test integration with HypothesisPoolEngine."""
    from modules.hypothesis_competition import get_hypothesis_pool_engine, get_hypothesis_ranking_engine
    
    pool_engine = get_hypothesis_pool_engine()
    ranking_engine = get_hypothesis_ranking_engine()
    capital_engine = CapitalAllocationEngine()
    
    # Full pipeline
    base_pool = pool_engine.generate_pool("BTC")
    ranked_pool = ranking_engine.rank_hypotheses(base_pool)
    allocation = capital_engine.allocate_capital(ranked_pool)
    
    assert allocation.symbol == "BTC"
    assert allocation.total_hypotheses_input >= 0


# ══════════════════════════════════════════════════════════════
# Test 22: Directional Balance Preserved
# ══════════════════════════════════════════════════════════════

def test_directional_balance_preserved():
    """Test directional balance is maintained after caps."""
    engine = CapitalAllocationEngine()
    
    items = [
        create_test_item("BREAKOUT1", "LONG", 0.7, 0.6, 0.7),
        create_test_item("BREAKOUT2", "LONG", 0.6, 0.5, 0.6),
        create_test_item("BREAKOUT3", "LONG", 0.55, 0.45, 0.55),
        create_test_item("BEARISH", "SHORT", 0.5, 0.4, 0.5),
    ]
    
    ranked_pool = create_test_ranked_pool("BTC", items)
    allocation = engine.allocate_capital(ranked_pool)
    
    # Check directional cap is applied
    long_weight = sum(
        a.capital_weight 
        for a in allocation.allocations 
        if a.directional_bias == "LONG"
    )
    
    # Should be at most 65% in LONG (allowing for rounding)
    assert long_weight <= MAX_DIRECTIONAL_EXPOSURE + 0.02


# ══════════════════════════════════════════════════════════════
# Additional Tests (23-26)
# ══════════════════════════════════════════════════════════════

def test_cautious_modifier_value():
    """Test CAUTIOUS modifier is exactly 0.80."""
    assert EXECUTION_STATE_MODIFIERS["CAUTIOUS"] == 0.80


def test_favorable_modifier_value():
    """Test FAVORABLE modifier is exactly 1.00."""
    assert EXECUTION_STATE_MODIFIERS["FAVORABLE"] == 1.00


def test_unfavorable_modifier_value():
    """Test UNFAVORABLE modifier is exactly 0.00."""
    assert EXECUTION_STATE_MODIFIERS["UNFAVORABLE"] == 0.00


def test_constants_values():
    """Test constant values are correct."""
    assert MAX_DIRECTIONAL_EXPOSURE == 0.65
    assert MAX_NEUTRAL_ALLOCATION == 0.30
    assert MIN_ALLOCATION_THRESHOLD == 0.05


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
