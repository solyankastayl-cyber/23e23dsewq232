"""
Adaptive Weight Engine Tests

PHASE 30.5 — 24+ tests for Adaptive Weight Engine

Tests:
1. Success modifier calculation
2. Success modifier bounds
3. PnL modifier calculation
4. PnL modifier bounds
5. Combined modifier calculation
6. Combined bounds
7. Min observation protection
8. Adaptive weight calculation
9. Final weight calculation
10. Adaptive endpoint valid
11. Summary endpoint valid
12. Recompute endpoint valid
13. Storage correct
14. Integration with outcome engine
15. Integration with allocation engine
16. Deterministic result
17. Negative PnL scenario
18. Strong alpha scenario
19. Weak alpha scenario
20. Normalization safe
21. Missing data safe
22. Multi hypothesis evaluation
23. Scheduler safe
24. Modifier bounds respected
"""

import pytest
from datetime import datetime, timezone
from typing import List

from modules.hypothesis_competition.adaptive_weight_engine import (
    AdaptiveWeightEngine,
    get_adaptive_weight_engine,
)
from modules.hypothesis_competition.adaptive_weight_types import (
    HypothesisAdaptiveWeight,
    AdaptiveWeightSummary,
    MIN_OBSERVATIONS,
    SUCCESS_MODIFIER_MIN,
    SUCCESS_MODIFIER_MAX,
    PNL_MODIFIER_MIN,
    PNL_MODIFIER_MAX,
    COMBINED_MODIFIER_MIN,
    COMBINED_MODIFIER_MAX,
)
from modules.hypothesis_competition.outcome_tracking_types import HypothesisPerformance


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

def create_test_performance(
    hypothesis_type: str = "BREAKOUT_FORMING",
    total_predictions: int = 50,
    success_rate: float = 0.55,
    avg_pnl: float = 1.0,
    avg_confidence: float = 0.6,
    avg_reliability: float = 0.5,
) -> HypothesisPerformance:
    """Create test performance data."""
    return HypothesisPerformance(
        hypothesis_type=hypothesis_type,
        total_predictions=total_predictions,
        success_rate=success_rate,
        avg_pnl=avg_pnl,
        avg_confidence=avg_confidence,
        avg_reliability=avg_reliability,
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Success Modifier Calculation
# ══════════════════════════════════════════════════════════════

def test_success_modifier_calculation():
    """Test success modifier is calculated correctly."""
    engine = AdaptiveWeightEngine()
    
    # 50% success rate -> modifier = 1.0
    modifier = engine.calculate_success_modifier(0.50)
    assert abs(modifier - 1.0) < 0.01
    
    # 60% success rate -> modifier = 1 + 0.10 * 1.2 = 1.12
    modifier = engine.calculate_success_modifier(0.60)
    assert abs(modifier - 1.12) < 0.01
    
    # 40% success rate -> modifier = 1 - 0.10 * 1.2 = 0.88
    modifier = engine.calculate_success_modifier(0.40)
    assert abs(modifier - 0.88) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 2: Success Modifier Bounds
# ══════════════════════════════════════════════════════════════

def test_success_modifier_bounds():
    """Test success modifier is clamped to bounds."""
    engine = AdaptiveWeightEngine()
    
    # Very high success rate -> max bound
    modifier = engine.calculate_success_modifier(1.0)
    assert modifier <= SUCCESS_MODIFIER_MAX
    
    # Very low success rate -> min bound
    modifier = engine.calculate_success_modifier(0.0)
    assert modifier >= SUCCESS_MODIFIER_MIN


# ══════════════════════════════════════════════════════════════
# Test 3: PnL Modifier Calculation
# ══════════════════════════════════════════════════════════════

def test_pnl_modifier_calculation():
    """Test PnL modifier is calculated correctly."""
    engine = AdaptiveWeightEngine()
    
    # 0% PnL -> modifier = 1.0
    modifier = engine.calculate_pnl_modifier(0.0)
    assert abs(modifier - 1.0) < 0.01
    
    # Positive PnL (2%) -> modifier = 1 + 0.02 * 0.25 = 1.005
    modifier = engine.calculate_pnl_modifier(2.0)
    assert modifier > 1.0
    
    # Negative PnL (-2%) -> modifier = 1 - 0.02 * 0.40 = 0.992
    modifier = engine.calculate_pnl_modifier(-2.0)
    assert modifier < 1.0


# ══════════════════════════════════════════════════════════════
# Test 4: PnL Modifier Bounds
# ══════════════════════════════════════════════════════════════

def test_pnl_modifier_bounds():
    """Test PnL modifier is clamped to bounds."""
    engine = AdaptiveWeightEngine()
    
    # Very high PnL -> max bound
    modifier = engine.calculate_pnl_modifier(100.0)
    assert modifier <= PNL_MODIFIER_MAX
    
    # Very low PnL -> min bound
    modifier = engine.calculate_pnl_modifier(-100.0)
    assert modifier >= PNL_MODIFIER_MIN


# ══════════════════════════════════════════════════════════════
# Test 5: Combined Modifier Calculation
# ══════════════════════════════════════════════════════════════

def test_combined_modifier_calculation():
    """Test combined modifier is calculated correctly."""
    engine = AdaptiveWeightEngine()
    
    # 60% success + 40% PnL weights
    combined = engine.calculate_combined_modifier(1.0, 1.0)
    assert abs(combined - 1.0) < 0.01
    
    # Boost both -> boosted combined
    combined = engine.calculate_combined_modifier(1.2, 1.1)
    assert combined > 1.0
    
    # Penalize both -> penalized combined
    combined = engine.calculate_combined_modifier(0.8, 0.9)
    assert combined < 1.0


# ══════════════════════════════════════════════════════════════
# Test 6: Combined Modifier Bounds
# ══════════════════════════════════════════════════════════════

def test_combined_modifier_bounds():
    """Test combined modifier is clamped to bounds."""
    engine = AdaptiveWeightEngine()
    
    # Max both -> still within bounds
    combined = engine.calculate_combined_modifier(
        SUCCESS_MODIFIER_MAX,
        PNL_MODIFIER_MAX,
    )
    assert combined <= COMBINED_MODIFIER_MAX
    
    # Min both -> still within bounds
    combined = engine.calculate_combined_modifier(
        SUCCESS_MODIFIER_MIN,
        PNL_MODIFIER_MIN,
    )
    assert combined >= COMBINED_MODIFIER_MIN


# ══════════════════════════════════════════════════════════════
# Test 7: Min Observation Protection
# ══════════════════════════════════════════════════════════════

def test_min_observation_protection():
    """Test modifier is 1.0 if observations < MIN_OBSERVATIONS."""
    engine = AdaptiveWeightEngine()
    
    # Below threshold
    perf = create_test_performance(
        total_predictions=10,
        success_rate=0.80,
        avg_pnl=5.0,
    )
    
    weight = engine.calculate_adaptive_weight(perf)
    
    assert weight.adaptive_modifier == 1.0
    assert weight.success_modifier == 1.0
    assert weight.pnl_modifier == 1.0


# ══════════════════════════════════════════════════════════════
# Test 8: Adaptive Weight Calculation
# ══════════════════════════════════════════════════════════════

def test_adaptive_weight_calculation():
    """Test adaptive weight is calculated correctly."""
    engine = AdaptiveWeightEngine()
    
    perf = create_test_performance(
        total_predictions=50,
        success_rate=0.60,
        avg_pnl=2.0,
    )
    
    weight = engine.calculate_adaptive_weight(perf)
    
    assert weight.hypothesis_type == "BREAKOUT_FORMING"
    assert weight.observations == 50
    assert weight.success_modifier > 1.0  # Good success rate
    assert weight.adaptive_modifier > 1.0  # Overall boost


# ══════════════════════════════════════════════════════════════
# Test 9: Final Weight Calculation
# ══════════════════════════════════════════════════════════════

def test_final_weight_calculation():
    """Test final weight = base_weight × adaptive_modifier."""
    engine = AdaptiveWeightEngine()
    
    perf = create_test_performance(
        total_predictions=50,
        success_rate=0.60,
    )
    
    weight = engine.calculate_adaptive_weight(perf, base_weight=0.5)
    
    expected_final = 0.5 * weight.adaptive_modifier
    assert abs(weight.final_weight - expected_final) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 10: Adaptive Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_adaptive_endpoint_valid():
    """Test adaptive endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.adaptive_weight_routes import get_adaptive_weights
    
    response = asyncio.get_event_loop().run_until_complete(get_adaptive_weights("BTC"))
    
    assert "symbol" in response
    assert response["symbol"] == "BTC"
    assert "weights" in response


# ══════════════════════════════════════════════════════════════
# Test 11: Summary Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_valid():
    """Test summary endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.adaptive_weight_routes import get_adaptive_summary
    
    response = asyncio.get_event_loop().run_until_complete(get_adaptive_summary("BTC"))
    
    assert "symbol" in response
    assert "modifiers" in response
    assert "distribution" in response


# ══════════════════════════════════════════════════════════════
# Test 12: Recompute Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint_valid():
    """Test recompute endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.adaptive_weight_routes import recompute_adaptive_weights
    
    response = asyncio.get_event_loop().run_until_complete(recompute_adaptive_weights("BTC"))
    
    assert "status" in response
    assert response["status"] == "ok"


# ══════════════════════════════════════════════════════════════
# Test 13: Storage Correct
# ══════════════════════════════════════════════════════════════

def test_storage_correct():
    """Test weights are stored correctly."""
    engine = AdaptiveWeightEngine()
    
    perf = create_test_performance(total_predictions=50)
    weight = engine.calculate_adaptive_weight(perf)
    
    engine._store_weights("BTC", [weight])
    
    stored = engine.get_weights("BTC")
    assert len(stored) >= 1


# ══════════════════════════════════════════════════════════════
# Test 14: Integration with Outcome Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_outcome_engine():
    """Test integration with OutcomeTrackingEngine."""
    from modules.hypothesis_competition import get_outcome_tracking_engine
    
    outcome_engine = get_outcome_tracking_engine()
    adaptive_engine = AdaptiveWeightEngine()
    
    # Both engines should work together
    assert outcome_engine is not None
    assert adaptive_engine is not None


# ══════════════════════════════════════════════════════════════
# Test 15: Integration with Allocation Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_allocation_engine():
    """Test integration with CapitalAllocationEngine."""
    from modules.hypothesis_competition import get_capital_allocation_engine
    
    alloc_engine = get_capital_allocation_engine()
    
    # Allocation should use adaptive weights
    assert alloc_engine._use_adaptive_weights == True


# ══════════════════════════════════════════════════════════════
# Test 16: Deterministic Result
# ══════════════════════════════════════════════════════════════

def test_deterministic_result():
    """Test same input produces same output."""
    engine1 = AdaptiveWeightEngine()
    engine2 = AdaptiveWeightEngine()
    
    perf = create_test_performance()
    
    weight1 = engine1.calculate_adaptive_weight(perf)
    weight2 = engine2.calculate_adaptive_weight(perf)
    
    assert weight1.adaptive_modifier == weight2.adaptive_modifier


# ══════════════════════════════════════════════════════════════
# Test 17: Negative PnL Scenario
# ══════════════════════════════════════════════════════════════

def test_negative_pnl_scenario():
    """Test handling of negative PnL."""
    engine = AdaptiveWeightEngine()
    
    perf = create_test_performance(
        total_predictions=50,
        success_rate=0.45,
        avg_pnl=-3.0,
    )
    
    weight = engine.calculate_adaptive_weight(perf)
    
    # Should be penalized
    assert weight.adaptive_modifier < 1.0


# ══════════════════════════════════════════════════════════════
# Test 18: Strong Alpha Scenario
# ══════════════════════════════════════════════════════════════

def test_strong_alpha_scenario():
    """Test boosting of strong alpha hypothesis."""
    engine = AdaptiveWeightEngine()
    
    perf = create_test_performance(
        total_predictions=100,
        success_rate=0.70,
        avg_pnl=5.0,
    )
    
    weight = engine.calculate_adaptive_weight(perf)
    
    # Should be boosted
    assert weight.adaptive_modifier > 1.0


# ══════════════════════════════════════════════════════════════
# Test 19: Weak Alpha Scenario
# ══════════════════════════════════════════════════════════════

def test_weak_alpha_scenario():
    """Test penalizing of weak alpha hypothesis."""
    engine = AdaptiveWeightEngine()
    
    perf = create_test_performance(
        total_predictions=100,
        success_rate=0.35,
        avg_pnl=-2.0,
    )
    
    weight = engine.calculate_adaptive_weight(perf)
    
    # Should be penalized
    assert weight.adaptive_modifier < 1.0


# ══════════════════════════════════════════════════════════════
# Test 20: Normalization Safe
# ══════════════════════════════════════════════════════════════

def test_normalization_safe():
    """Test weight normalization is safe."""
    engine = AdaptiveWeightEngine()
    
    weights = [
        HypothesisAdaptiveWeight(
            hypothesis_type="TYPE_A",
            final_weight=0.6,
        ),
        HypothesisAdaptiveWeight(
            hypothesis_type="TYPE_B",
            final_weight=0.4,
        ),
    ]
    
    normalized = engine._normalize_weights(weights)
    
    total = sum(w.final_weight for w in normalized)
    assert abs(total - 1.0) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 21: Missing Data Safe
# ══════════════════════════════════════════════════════════════

def test_missing_data_safe():
    """Test handling of missing data."""
    engine = AdaptiveWeightEngine()
    
    # Empty symbol should return empty list
    weights = engine.generate_adaptive_weights("NONEXISTENT")
    assert isinstance(weights, list)


# ══════════════════════════════════════════════════════════════
# Test 22: Multi Hypothesis Evaluation
# ══════════════════════════════════════════════════════════════

def test_multi_hypothesis_evaluation():
    """Test evaluation of multiple hypothesis types."""
    engine = AdaptiveWeightEngine()
    
    perfs = [
        create_test_performance("TYPE_A", 50, 0.65, 3.0),
        create_test_performance("TYPE_B", 50, 0.45, -1.0),
        create_test_performance("TYPE_C", 50, 0.55, 0.5),
    ]
    
    weights = [engine.calculate_adaptive_weight(p, 1/3) for p in perfs]
    
    assert len(weights) == 3
    
    # TYPE_A should be boosted
    assert weights[0].adaptive_modifier > 1.0
    
    # TYPE_B should be penalized
    assert weights[1].adaptive_modifier < 1.0


# ══════════════════════════════════════════════════════════════
# Test 23: Scheduler Safe
# ══════════════════════════════════════════════════════════════

def test_scheduler_safe():
    """Test scheduler-like repeated calls are safe."""
    engine = AdaptiveWeightEngine()
    
    # Simulate scheduler calls
    for _ in range(5):
        weights = engine.generate_adaptive_weights("BTC")
        assert isinstance(weights, list)


# ══════════════════════════════════════════════════════════════
# Test 24: Modifier Bounds Respected
# ══════════════════════════════════════════════════════════════

def test_modifier_bounds_respected():
    """Test all modifier bounds are respected."""
    engine = AdaptiveWeightEngine()
    
    # Extreme high performance
    perf_high = create_test_performance(
        total_predictions=100,
        success_rate=0.95,
        avg_pnl=50.0,
    )
    weight_high = engine.calculate_adaptive_weight(perf_high)
    
    # Extreme low performance
    perf_low = create_test_performance(
        total_predictions=100,
        success_rate=0.10,
        avg_pnl=-50.0,
    )
    weight_low = engine.calculate_adaptive_weight(perf_low)
    
    # Check bounds
    assert weight_high.adaptive_modifier <= COMBINED_MODIFIER_MAX
    assert weight_low.adaptive_modifier >= COMBINED_MODIFIER_MIN


# ══════════════════════════════════════════════════════════════
# Additional Tests (25-28)
# ══════════════════════════════════════════════════════════════

def test_constants_values():
    """Test constant values are correct."""
    assert MIN_OBSERVATIONS == 30
    assert SUCCESS_MODIFIER_MIN == 0.70
    assert SUCCESS_MODIFIER_MAX == 1.30
    assert PNL_MODIFIER_MIN == 0.75
    assert PNL_MODIFIER_MAX == 1.25
    assert COMBINED_MODIFIER_MIN == 0.65
    assert COMBINED_MODIFIER_MAX == 1.35


def test_get_modifier_for_missing_hypothesis():
    """Test get_adaptive_modifier returns 1.0 for missing hypothesis."""
    engine = AdaptiveWeightEngine()
    
    modifier = engine.get_adaptive_modifier("BTC", "NONEXISTENT_TYPE")
    assert modifier == 1.0


def test_get_all_modifiers():
    """Test get_all_modifiers returns dict."""
    engine = AdaptiveWeightEngine()
    
    modifiers = engine.get_all_modifiers("BTC")
    assert isinstance(modifiers, dict)


def test_summary_empty_symbol():
    """Test summary for symbol with no data."""
    engine = AdaptiveWeightEngine()
    
    summary = engine.get_summary("EMPTY_SYMBOL")
    
    assert summary.total_hypothesis_types == 0


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
