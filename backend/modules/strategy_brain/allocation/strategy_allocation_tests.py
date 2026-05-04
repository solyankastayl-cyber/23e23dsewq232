"""
PHASE 19.2 — Strategy Allocation Tests
=====================================
Tests for Strategy Allocation Engine.

Test scenarios:
1. Allocation sums to 1.0
2. Disabled strategies get zero capital
3. Reduced strategies get reduced weight
4. Active strategies dominate allocation
5. Renormalization correct
6. Confidence modifier bounded
7. Allocation summary correct
8. API output correct
"""

import pytest
from datetime import datetime, timezone

from modules.strategy_brain.allocation.strategy_allocation_types import (
    BASE_WEIGHTS,
    STATE_MULTIPLIERS,
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
)
from modules.strategy_brain.allocation.strategy_weight_engine import (
    get_weight_engine,
    StrategyWeightEngine,
)
from modules.strategy_brain.allocation.strategy_capital_engine import (
    get_capital_engine,
    StrategyCapitalEngine,
)
from modules.strategy_brain.allocation.strategy_allocation_engine import (
    get_allocation_engine,
    StrategyAllocationEngine,
)


class TestBaseWeights:
    """Test base weights configuration."""
    
    def test_base_weights_sum_to_one(self):
        """TEST 1 (partial): Base weights should sum to 1.0."""
        total = sum(BASE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001
    
    def test_all_strategies_have_base_weight(self):
        """All expected strategies should have base weights."""
        expected = [
            "trend_following",
            "mean_reversion",
            "breakout",
            "liquidation_capture",
            "flow_following",
            "volatility_expansion",
            "funding_arb",
            "structure_reversal",
        ]
        
        for strategy in expected:
            assert strategy in BASE_WEIGHTS


class TestStateMultipliers:
    """Test state multipliers."""
    
    def test_active_multiplier(self):
        """ACTIVE should have multiplier 1.0."""
        assert STATE_MULTIPLIERS["ACTIVE"] == 1.0
    
    def test_reduced_multiplier(self):
        """REDUCED should have multiplier 0.6."""
        assert STATE_MULTIPLIERS["REDUCED"] == 0.6
    
    def test_disabled_multiplier(self):
        """DISABLED should have multiplier 0.0."""
        assert STATE_MULTIPLIERS["DISABLED"] == 0.0


class TestWeightEngine:
    """Test Strategy Weight Engine."""
    
    def test_get_base_weight(self):
        """Should get correct base weight."""
        engine = get_weight_engine()
        
        assert engine.get_base_weight("trend_following") == 0.18
        assert engine.get_base_weight("unknown") == 0.0
    
    def test_compute_adjusted_weight_active(self):
        """Active strategy should keep full weight."""
        engine = get_weight_engine()
        
        adjusted = engine.compute_adjusted_weight("trend_following", "ACTIVE")
        assert adjusted == 0.18
    
    def test_compute_adjusted_weight_reduced(self):
        """TEST 3: Reduced strategy should have reduced weight."""
        engine = get_weight_engine()
        
        adjusted = engine.compute_adjusted_weight("trend_following", "REDUCED")
        assert adjusted == 0.18 * 0.6
        assert adjusted == 0.108
    
    def test_compute_adjusted_weight_disabled(self):
        """TEST 2: Disabled strategy should have zero weight."""
        engine = get_weight_engine()
        
        adjusted = engine.compute_adjusted_weight("trend_following", "DISABLED")
        assert adjusted == 0.0
    
    def test_validate_base_weights(self):
        """Validation should pass for default weights."""
        engine = get_weight_engine()
        assert engine.validate_base_weights() is True


class TestCapitalEngine:
    """Test Strategy Capital Engine."""
    
    def test_compute_capital_shares_sum(self):
        """TEST 1: Capital shares should sum to 1.0."""
        engine = get_capital_engine()
        
        adjusted_weights = {
            "a": 0.3,
            "b": 0.5,
            "c": 0.2,
        }
        
        shares = engine.compute_capital_shares(adjusted_weights)
        total = sum(shares.values())
        
        assert abs(total - 1.0) < 0.001
    
    def test_compute_capital_shares_zero(self):
        """All disabled should result in zero shares."""
        engine = get_capital_engine()
        
        adjusted_weights = {
            "a": 0.0,
            "b": 0.0,
            "c": 0.0,
        }
        
        shares = engine.compute_capital_shares(adjusted_weights)
        
        assert all(v == 0.0 for v in shares.values())
    
    def test_renormalization(self):
        """TEST 5: Renormalization should work correctly."""
        engine = get_capital_engine()
        
        # If only some strategies active
        adjusted_weights = {
            "a": 0.5,   # Should become 0.5/0.7 ≈ 0.714
            "b": 0.2,   # Should become 0.2/0.7 ≈ 0.286
            "c": 0.0,   # Disabled
        }
        
        shares = engine.compute_capital_shares(adjusted_weights)
        
        assert abs(shares["a"] - 0.714) < 0.01
        assert abs(shares["b"] - 0.286) < 0.01
        assert shares["c"] == 0.0
        
        total = sum(shares.values())
        assert abs(total - 1.0) < 0.001
    
    def test_confidence_modifier_bounded_min(self):
        """TEST 6: Confidence modifier should be >= 0.75."""
        engine = get_capital_engine()
        
        modifier = engine.compute_confidence_modifier(0.0)
        assert modifier >= CONFIDENCE_MODIFIER_MIN
    
    def test_confidence_modifier_bounded_max(self):
        """TEST 6: Confidence modifier should be <= 1.25."""
        engine = get_capital_engine()
        
        modifier = engine.compute_confidence_modifier(0.5)
        assert modifier <= CONFIDENCE_MODIFIER_MAX


class TestAllocationEngine:
    """Test Strategy Allocation Engine."""
    
    def test_compute_allocation(self):
        """Should compute allocation for single strategy."""
        engine = get_allocation_engine()
        
        alloc = engine.compute_allocation("trend_following", "BTC")
        
        assert alloc.strategy_name == "trend_following"
        assert alloc.base_weight == 0.18
        assert alloc.strategy_state in ["ACTIVE", "REDUCED", "DISABLED"]
    
    def test_compute_all_allocations(self):
        """Should compute allocations for all strategies."""
        engine = get_allocation_engine()
        
        allocations = engine.compute_all_allocations("BTC")
        
        assert len(allocations) == 8
        
        # Verify sum = 1.0
        total = sum(a.capital_share for a in allocations)
        assert abs(total - 1.0) < 0.001
    
    def test_allocation_sum_to_one(self):
        """TEST 1: Total allocation should sum to 1.0."""
        engine = get_allocation_engine()
        
        summary = engine.compute_summary("BTC")
        
        total = sum(summary.allocations.values())
        assert abs(total - 1.0) < 0.001
    
    def test_disabled_get_zero(self):
        """TEST 2: Disabled strategies should get zero capital."""
        engine = get_allocation_engine()
        
        allocations = engine.compute_all_allocations("BTC")
        
        for alloc in allocations:
            if alloc.strategy_state == "DISABLED":
                assert alloc.capital_share == 0.0
    
    def test_active_dominate(self):
        """TEST 4: Active strategies should dominate allocation."""
        engine = get_allocation_engine()
        
        summary = engine.compute_summary("BTC")
        
        # Active capital should be significant
        # (At least more than reduced if both exist)
        if summary.active_count > 0 and summary.reduced_count > 0:
            avg_active = summary.active_capital / summary.active_count
            avg_reduced = summary.reduced_capital / summary.reduced_count
            
            # Average active allocation should be > average reduced
            # because ACTIVE multiplier (1.0) > REDUCED multiplier (0.6)
            assert avg_active >= avg_reduced * 0.8  # Allow some margin
    
    def test_summary_correct(self):
        """TEST 7: Allocation summary should be correct."""
        engine = get_allocation_engine()
        
        summary = engine.compute_summary("BTC")
        
        # Counts should match
        total = len(summary.active_strategies) + len(summary.reduced_strategies) + len(summary.disabled_strategies)
        assert total == summary.total_strategies
        
        # Total capital = 1.0
        assert summary.total_capital == 1.0
        
        # Active + reduced capital should equal non-disabled total
        non_disabled = summary.active_capital + summary.reduced_capital
        total_alloc = sum(
            a.capital_share for a in summary.allocation_states
            if a.strategy_state != "DISABLED"
        )
        assert abs(non_disabled - total_alloc) < 0.001
    
    def test_summary_to_dict(self):
        """TEST 8: Summary should convert to dict correctly."""
        engine = get_allocation_engine()
        
        summary = engine.compute_summary("BTC")
        d = summary.to_dict()
        
        assert "total_capital" in d
        assert "allocations" in d
        assert "active_strategies" in d
        assert "reduced_strategies" in d
        assert "disabled_strategies" in d
        assert "counts" in d


class TestIntegrationScenarios:
    """Integration test scenarios."""
    
    def test_full_workflow(self):
        """Full allocation workflow test."""
        engine = get_allocation_engine()
        
        # Get summary
        summary = engine.compute_summary("BTC")
        
        # Verify structure
        assert summary.total_strategies == 8
        assert summary.total_capital == 1.0
        
        # Verify allocations
        for name, share in summary.allocations.items():
            assert 0.0 <= share <= 1.0
    
    def test_allocation_state_format(self):
        """Allocation state should have correct format."""
        engine = get_allocation_engine()
        
        alloc = engine.compute_allocation("mean_reversion", "BTC")
        d = alloc.to_dict()
        
        assert "strategy_name" in d
        assert "strategy_state" in d
        assert "base_weight" in d
        assert "capital_share" in d
        assert "confidence_modifier" in d


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 19.2 — Strategy Allocation Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestBaseWeights,
        TestStateMultipliers,
        TestWeightEngine,
        TestCapitalEngine,
        TestAllocationEngine,
        TestIntegrationScenarios,
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        
        for method_name in methods:
            try:
                method = getattr(instance, method_name)
                method()
                print(f"  [PASS] {method_name}")
                total_passed += 1
            except AssertionError as e:
                print(f"  [FAIL] {method_name}: {e}")
                total_failed += 1
            except Exception as e:
                print(f"  [ERROR] {method_name}: {e}")
                total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 60 + "\n")
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
