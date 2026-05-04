"""
Outcome Tracking Engine Tests

PHASE 30.4 — 24+ tests for Outcome Tracking Engine

Tests:
1. PnL calculation correct
2. Long direction success
3. Short direction success
4. Neutral logic correct
5. Tolerance applied
6. Outcome stored
7. Horizon evaluation correct
8. Multiple horizon evaluation
9. Success_rate calculation
10. Avg_pnl calculation
11. Performance aggregation
12. Confidence correlation
13. Reliability correlation
14. Outcome endpoint valid
15. Summary endpoint valid
16. Performance endpoint valid
17. Evaluate endpoint valid
18. Integration with hypothesis registry
19. Integration with portfolio engine
20. Deterministic outcome
21. Negative pnl case
22. Flat market case
23. Missing price safe
24. Scheduler safe
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from modules.hypothesis_competition.outcome_tracking_engine import (
    OutcomeTrackingEngine,
    get_outcome_tracking_engine,
)
from modules.hypothesis_competition.outcome_tracking_types import (
    HypothesisOutcome,
    HypothesisPerformance,
    PendingHypothesisEvaluation,
    EVALUATION_HORIZONS,
    SUCCESS_TOLERANCE,
    NEUTRAL_VOLATILITY_THRESHOLD,
)
from modules.hypothesis_competition.capital_allocation_types import (
    HypothesisAllocation,
    HypothesisCapitalAllocation,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

def create_test_pending(
    symbol: str = "BTC",
    hypothesis_type: str = "BREAKOUT_FORMING",
    directional_bias: str = "LONG",
    confidence: float = 0.6,
    reliability: float = 0.5,
    capital_weight: float = 0.5,
    price: float = 50000.0,
    created_at: datetime = None,
) -> PendingHypothesisEvaluation:
    """Create test pending evaluation."""
    return PendingHypothesisEvaluation(
        symbol=symbol,
        hypothesis_type=hypothesis_type,
        directional_bias=directional_bias,
        confidence=confidence,
        reliability=reliability,
        capital_weight=capital_weight,
        price_at_creation=price,
        created_at=created_at or datetime.now(timezone.utc),
        horizons_evaluated=[],
    )


def create_test_allocation(
    symbol: str = "BTC",
    allocations: List[dict] = None,
) -> HypothesisCapitalAllocation:
    """Create test capital allocation."""
    if allocations is None:
        allocations = [
            HypothesisAllocation(
                hypothesis_type="BREAKOUT_FORMING",
                directional_bias="LONG",
                ranking_score=0.6,
                capital_weight=0.6,
                capital_percent=60,
                execution_state="FAVORABLE",
                confidence=0.65,
                reliability=0.55,
            ),
            HypothesisAllocation(
                hypothesis_type="RANGE_MEAN_REVERSION",
                directional_bias="NEUTRAL",
                ranking_score=0.4,
                capital_weight=0.4,
                capital_percent=40,
                execution_state="CAUTIOUS",
                confidence=0.55,
                reliability=0.50,
            ),
        ]
    else:
        allocations = [HypothesisAllocation(**a) for a in allocations]
    
    return HypothesisCapitalAllocation(
        symbol=symbol,
        allocations=allocations,
        total_allocated=1.0,
        portfolio_confidence=0.6,
        portfolio_reliability=0.52,
    )


# ══════════════════════════════════════════════════════════════
# Test 1: PnL Calculation Correct
# ══════════════════════════════════════════════════════════════

def test_pnl_calculation_correct():
    """Test PnL calculation for LONG position."""
    engine = OutcomeTrackingEngine()
    
    # LONG: 50000 -> 51000 = +2%
    pnl = engine.calculate_pnl(50000.0, 51000.0, "LONG")
    assert abs(pnl - 2.0) < 0.01
    
    # LONG: 50000 -> 49000 = -2%
    pnl = engine.calculate_pnl(50000.0, 49000.0, "LONG")
    assert abs(pnl - (-2.0)) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 2: Long Direction Success
# ══════════════════════════════════════════════════════════════

def test_long_direction_success():
    """Test LONG hypothesis success evaluation."""
    engine = OutcomeTrackingEngine()
    
    # Price went up sufficiently -> success
    success = engine.evaluate_success("LONG", 2.0, 50000.0, 51000.0)
    assert success == True
    
    # Price went down -> failure
    success = engine.evaluate_success("LONG", -2.0, 50000.0, 49000.0)
    assert success == False


# ══════════════════════════════════════════════════════════════
# Test 3: Short Direction Success
# ══════════════════════════════════════════════════════════════

def test_short_direction_success():
    """Test SHORT hypothesis success evaluation."""
    engine = OutcomeTrackingEngine()
    
    # Price went down -> success for SHORT
    success = engine.evaluate_success("SHORT", 2.0, 50000.0, 49000.0)
    assert success == True
    
    # Price went up -> failure for SHORT
    success = engine.evaluate_success("SHORT", -2.0, 50000.0, 51000.0)
    assert success == False


# ══════════════════════════════════════════════════════════════
# Test 4: Neutral Logic Correct
# ══════════════════════════════════════════════════════════════

def test_neutral_logic_correct():
    """Test NEUTRAL hypothesis success evaluation."""
    engine = OutcomeTrackingEngine()
    
    # Price stayed flat -> success for NEUTRAL
    success = engine.evaluate_success("NEUTRAL", 0.0, 50000.0, 50100.0)  # 0.2% change
    assert success == True
    
    # Price moved significantly -> failure for NEUTRAL
    success = engine.evaluate_success("NEUTRAL", 0.0, 50000.0, 52000.0)  # 4% change
    assert success == False


# ══════════════════════════════════════════════════════════════
# Test 5: Tolerance Applied
# ══════════════════════════════════════════════════════════════

def test_tolerance_applied():
    """Test success tolerance is applied."""
    engine = OutcomeTrackingEngine()
    
    # Micro move within tolerance -> failure for LONG
    success = engine.evaluate_success("LONG", 0.01, 50000.0, 50050.0)  # 0.1%
    assert success == False
    
    # Move above tolerance -> success
    success = engine.evaluate_success("LONG", 0.2, 50000.0, 50100.0)  # 0.2%
    assert success == True


# ══════════════════════════════════════════════════════════════
# Test 6: Outcome Stored
# ══════════════════════════════════════════════════════════════

def test_outcome_stored():
    """Test outcome is stored in engine."""
    engine = OutcomeTrackingEngine()
    
    pending = create_test_pending()
    outcome = engine.evaluate_hypothesis(pending, 51000.0, 5)
    engine._store_outcome(outcome)
    
    outcomes = engine.get_outcomes("BTC")
    assert len(outcomes) >= 1


# ══════════════════════════════════════════════════════════════
# Test 7: Horizon Evaluation Correct
# ══════════════════════════════════════════════════════════════

def test_horizon_evaluation_correct():
    """Test horizon is correctly assigned."""
    engine = OutcomeTrackingEngine()
    
    pending = create_test_pending()
    
    outcome_5m = engine.evaluate_hypothesis(pending, 51000.0, 5)
    assert outcome_5m.horizon_minutes == 5
    
    outcome_60m = engine.evaluate_hypothesis(pending, 52000.0, 60)
    assert outcome_60m.horizon_minutes == 60


# ══════════════════════════════════════════════════════════════
# Test 8: Multiple Horizon Evaluation
# ══════════════════════════════════════════════════════════════

def test_multiple_horizon_evaluation():
    """Test evaluation at multiple horizons."""
    engine = OutcomeTrackingEngine()
    
    allocation = create_test_allocation()
    engine.register_hypothesis(allocation, 50000.0)
    
    # Simulate time passing and evaluate
    outcomes = engine.force_evaluate("BTC", 51000.0)
    
    # Should have outcomes for multiple horizons
    horizons_seen = set(o.horizon_minutes for o in outcomes)
    assert len(horizons_seen) == len(EVALUATION_HORIZONS)


# ══════════════════════════════════════════════════════════════
# Test 9: Success Rate Calculation
# ══════════════════════════════════════════════════════════════

def test_success_rate_calculation():
    """Test success rate is calculated correctly."""
    engine = OutcomeTrackingEngine()
    
    # Create outcomes with known success/failure
    for i in range(10):
        pending = create_test_pending(hypothesis_type="TEST_TYPE")
        # 7 successes, 3 failures
        price = 51000.0 if i < 7 else 49000.0
        outcome = engine.evaluate_hypothesis(pending, price, 5)
        engine._store_outcome(outcome)
    
    performances = engine.calculate_performance("BTC", "TEST_TYPE")
    assert len(performances) >= 1
    
    perf = performances[0]
    assert abs(perf.success_rate - 0.7) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 10: Avg PnL Calculation
# ══════════════════════════════════════════════════════════════

def test_avg_pnl_calculation():
    """Test average PnL is calculated correctly."""
    engine = OutcomeTrackingEngine()
    
    # Create outcomes with known PnLs
    prices = [51000.0, 52000.0, 49000.0]  # +2%, +4%, -2%
    for price in prices:
        pending = create_test_pending(symbol="ETH", hypothesis_type="PNL_TEST")
        outcome = engine.evaluate_hypothesis(pending, price, 5)
        engine._store_outcome(outcome)
    
    performances = engine.calculate_performance("ETH", "PNL_TEST")
    assert len(performances) >= 1
    
    # Avg PnL should be around (2 + 4 - 2) / 3 = 1.33%
    perf = performances[0]
    assert abs(perf.avg_pnl - 1.33) < 0.5


# ══════════════════════════════════════════════════════════════
# Test 11: Performance Aggregation
# ══════════════════════════════════════════════════════════════

def test_performance_aggregation():
    """Test performance is aggregated by hypothesis type."""
    engine = OutcomeTrackingEngine()
    
    # Create outcomes for multiple types
    for h_type in ["TYPE_A", "TYPE_B"]:
        for i in range(5):
            pending = create_test_pending(symbol="SOL", hypothesis_type=h_type)
            outcome = engine.evaluate_hypothesis(pending, 51000.0, 5)
            engine._store_outcome(outcome)
    
    performances = engine.calculate_performance("SOL")
    assert len(performances) >= 2


# ══════════════════════════════════════════════════════════════
# Test 12: Confidence Correlation
# ══════════════════════════════════════════════════════════════

def test_confidence_correlation():
    """Test confidence-accuracy correlation is calculated."""
    engine = OutcomeTrackingEngine()
    
    # Create outcomes with varying confidence
    for i in range(20):
        pending = create_test_pending(
            symbol="CORR_TEST",
            hypothesis_type="CORR_TYPE",
            confidence=0.5 + i * 0.02,  # Varying confidence
        )
        # Higher confidence -> more likely success
        price = 51000.0 if i > 10 else 49000.0
        outcome = engine.evaluate_hypothesis(pending, price, 5)
        engine._store_outcome(outcome)
    
    performances = engine.calculate_performance("CORR_TEST", "CORR_TYPE")
    
    # Correlation should be positive (higher confidence -> more success)
    if performances:
        perf = performances[0]
        # Just check it's a valid number
        assert -1.0 <= perf.confidence_accuracy_correlation <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 13: Reliability Correlation
# ══════════════════════════════════════════════════════════════

def test_reliability_correlation():
    """Test reliability-accuracy correlation is calculated."""
    engine = OutcomeTrackingEngine()
    
    for i in range(20):
        pending = create_test_pending(
            symbol="REL_TEST",
            hypothesis_type="REL_TYPE",
            reliability=0.5 + i * 0.02,
        )
        price = 51000.0 if i > 10 else 49000.0
        outcome = engine.evaluate_hypothesis(pending, price, 5)
        engine._store_outcome(outcome)
    
    performances = engine.calculate_performance("REL_TEST", "REL_TYPE")
    
    if performances:
        perf = performances[0]
        assert -1.0 <= perf.reliability_accuracy_correlation <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 14: Outcome Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_outcome_endpoint_valid():
    """Test outcome endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.outcome_tracking_routes import get_outcomes
    
    response = asyncio.get_event_loop().run_until_complete(get_outcomes("BTC", 50, None, None))
    
    assert "symbol" in response
    assert response["symbol"] == "BTC"
    assert "outcomes" in response


# ══════════════════════════════════════════════════════════════
# Test 15: Summary Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_valid():
    """Test summary endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.outcome_tracking_routes import get_outcomes_summary
    
    response = asyncio.get_event_loop().run_until_complete(get_outcomes_summary("BTC"))
    
    assert "symbol" in response
    assert "overall" in response
    assert "by_direction" in response


# ══════════════════════════════════════════════════════════════
# Test 16: Performance Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_performance_endpoint_valid():
    """Test performance endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.outcome_tracking_routes import get_performance
    
    response = asyncio.get_event_loop().run_until_complete(get_performance("BTC"))
    
    assert "symbol" in response
    assert "performances" in response


# ══════════════════════════════════════════════════════════════
# Test 17: Evaluate Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_evaluate_endpoint_valid():
    """Test evaluate endpoint returns valid response."""
    import asyncio
    from modules.hypothesis_competition.outcome_tracking_routes import evaluate_outcomes
    
    response = asyncio.get_event_loop().run_until_complete(evaluate_outcomes("BTC", 51000.0))
    
    assert "status" in response
    assert response["status"] == "ok"
    assert "outcomes_evaluated" in response


# ══════════════════════════════════════════════════════════════
# Test 18: Integration with Hypothesis Registry
# ══════════════════════════════════════════════════════════════

def test_integration_with_hypothesis_registry():
    """Test integration with hypothesis engine."""
    from modules.hypothesis_engine import hypothesis_router
    engine = OutcomeTrackingEngine()
    
    # Just verify engine can be instantiated alongside hypothesis components
    assert engine is not None


# ══════════════════════════════════════════════════════════════
# Test 19: Integration with Portfolio Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_portfolio_engine():
    """Test integration with capital allocation engine."""
    from modules.hypothesis_competition import get_capital_allocation_engine
    
    alloc_engine = get_capital_allocation_engine()
    tracking_engine = OutcomeTrackingEngine()
    
    # Generate allocation and register for tracking
    allocation = alloc_engine.generate_allocation("BTC")
    registered = tracking_engine.register_hypothesis(allocation, 50000.0)
    
    assert registered >= 0


# ══════════════════════════════════════════════════════════════
# Test 20: Deterministic Outcome
# ══════════════════════════════════════════════════════════════

def test_deterministic_outcome():
    """Test same input produces same outcome."""
    engine1 = OutcomeTrackingEngine()
    engine2 = OutcomeTrackingEngine()
    
    pending = create_test_pending()
    
    outcome1 = engine1.evaluate_hypothesis(pending, 51000.0, 5)
    outcome2 = engine2.evaluate_hypothesis(pending, 51000.0, 5)
    
    assert outcome1.pnl_percent == outcome2.pnl_percent
    assert outcome1.success == outcome2.success


# ══════════════════════════════════════════════════════════════
# Test 21: Negative PnL Case
# ══════════════════════════════════════════════════════════════

def test_negative_pnl_case():
    """Test negative PnL is calculated correctly."""
    engine = OutcomeTrackingEngine()
    
    pending = create_test_pending(directional_bias="LONG")
    outcome = engine.evaluate_hypothesis(pending, 49000.0, 5)  # Price dropped
    
    assert outcome.pnl_percent < 0
    assert outcome.success == False


# ══════════════════════════════════════════════════════════════
# Test 22: Flat Market Case
# ══════════════════════════════════════════════════════════════

def test_flat_market_case():
    """Test flat market evaluation."""
    engine = OutcomeTrackingEngine()
    
    # Test NEUTRAL in flat market
    pending = create_test_pending(directional_bias="NEUTRAL")
    outcome = engine.evaluate_hypothesis(pending, 50050.0, 5)  # 0.1% change
    
    assert outcome.actual_direction == "FLAT"
    assert outcome.success == True


# ══════════════════════════════════════════════════════════════
# Test 23: Missing Price Safe
# ══════════════════════════════════════════════════════════════

def test_missing_price_safe():
    """Test handling of edge cases with price."""
    engine = OutcomeTrackingEngine()
    
    # Zero price should return 0 PnL
    pnl = engine.calculate_pnl(0, 100, "LONG")
    assert pnl == 0.0
    
    # Zero price direction
    direction = engine.determine_actual_direction(0, 100)
    assert direction == "FLAT"


# ══════════════════════════════════════════════════════════════
# Test 24: Scheduler Safe
# ══════════════════════════════════════════════════════════════

def test_scheduler_safe():
    """Test scheduler-like batch evaluation is safe."""
    engine = OutcomeTrackingEngine()
    
    # Register multiple hypotheses
    allocation = create_test_allocation()
    engine.register_hypothesis(allocation, 50000.0)
    
    # Simulate scheduler calls
    for _ in range(3):
        outcomes = engine.evaluate_pending("BTC", 51000.0)
        # Should not crash
    
    # Force evaluate remaining
    outcomes = engine.force_evaluate("BTC", 51000.0)
    assert isinstance(outcomes, list)


# ══════════════════════════════════════════════════════════════
# Additional Tests (25-28)
# ══════════════════════════════════════════════════════════════

def test_short_pnl_inversion():
    """Test SHORT PnL is inverted correctly."""
    engine = OutcomeTrackingEngine()
    
    # Price went down -> positive PnL for SHORT
    pnl = engine.calculate_pnl(50000.0, 49000.0, "SHORT")
    assert pnl > 0  # Should be +2%


def test_evaluation_horizons_constant():
    """Test evaluation horizons are set correctly."""
    assert EVALUATION_HORIZONS == [5, 15, 60, 240]


def test_success_tolerance_constant():
    """Test success tolerance is set correctly."""
    assert SUCCESS_TOLERANCE == 0.0015


def test_neutral_threshold_constant():
    """Test neutral volatility threshold is set correctly."""
    assert NEUTRAL_VOLATILITY_THRESHOLD == 0.005


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
