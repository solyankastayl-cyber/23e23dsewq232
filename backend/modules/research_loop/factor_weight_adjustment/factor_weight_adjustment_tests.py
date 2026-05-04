"""
PHASE 20.2 — Factor Weight Adjustment Tests
==========================================
Tests for Factor Weight Adjustment Engine.

Test scenarios:
1. Critical failure → decrease
2. Retire governance → retire
3. Stable factor → hold/increase
4. Shadow action sets low weight
5. Weights stay bounded
6. Summary output correct
7. Registry persistence correct
8. Repeated failures amplify decrease
9. No failures = no harsh penalty
10. API output correct
"""

import pytest
from datetime import datetime, timezone

from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_types import (
    FactorWeightAdjustment,
    FactorWeightAdjustmentSummary,
    AdjustmentAction,
    AdjustmentStrength,
    WEIGHT_MIN,
    WEIGHT_MAX,
    SHADOW_WEIGHT,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_policy import (
    get_factor_weight_policy,
    FactorWeightPolicy,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_registry import (
    get_factor_weight_registry,
    FactorWeightRegistry,
    DEFAULT_FACTOR_WEIGHTS,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_engine import (
    get_factor_weight_adjustment_engine,
    FactorWeightAdjustmentEngine,
)


class TestAdjustmentAction:
    """Tests for adjustment actions."""
    
    def test_action_values(self):
        """Should have all action values."""
        assert AdjustmentAction.INCREASE.value == "INCREASE"
        assert AdjustmentAction.DECREASE.value == "DECREASE"
        assert AdjustmentAction.HOLD.value == "HOLD"
        assert AdjustmentAction.SHADOW.value == "SHADOW"
        assert AdjustmentAction.RETIRE.value == "RETIRE"


class TestFactorWeightPolicy:
    """Tests for factor weight policy."""
    
    def test_critical_failure_decrease(self):
        """TEST 1: Critical failures should trigger decrease."""
        policy = get_factor_weight_policy()
        
        action, strength = policy.determine_action(
            critical_failures=2,
            failure_patterns_count=3,
            governance_state="WATCHLIST",
            deployment_state="LIVE",
        )
        
        assert action in [AdjustmentAction.DECREASE, AdjustmentAction.SHADOW]
    
    def test_retire_governance(self):
        """TEST 2: Retire governance should trigger retire action."""
        policy = get_factor_weight_policy()
        
        action, strength = policy.determine_action(
            critical_failures=0,
            failure_patterns_count=0,
            governance_state="RETIRE",
            deployment_state="LIVE",
        )
        
        assert action == AdjustmentAction.RETIRE
        assert strength == AdjustmentStrength.CRITICAL
    
    def test_stable_factor_hold(self):
        """TEST 3: Stable factor with some failures should hold."""
        policy = get_factor_weight_policy()
        
        action, strength = policy.determine_action(
            critical_failures=0,
            failure_patterns_count=1,
            governance_state="STABLE",
            deployment_state="LIVE",
        )
        
        assert action == AdjustmentAction.HOLD
    
    def test_elite_factor_increase(self):
        """TEST 3: Elite factor with promote should increase."""
        policy = get_factor_weight_policy()
        
        action, strength = policy.determine_action(
            critical_failures=0,
            failure_patterns_count=0,
            governance_state="ELITE",
            deployment_state="PROMOTE",
        )
        
        assert action == AdjustmentAction.INCREASE
    
    def test_shadow_weight(self):
        """TEST 4: Shadow action should set near shadow weight."""
        policy = get_factor_weight_policy()
        
        delta = policy.calculate_delta(
            action=AdjustmentAction.SHADOW,
            strength=AdjustmentStrength.HIGH,
            current_weight=0.15,
        )
        
        recommended = 0.15 + delta
        assert abs(recommended - SHADOW_WEIGHT) < 0.01


class TestWeightBounds:
    """Tests for weight bounds."""
    
    def test_weight_bounded_min(self):
        """TEST 5: Weight should not go below 0."""
        policy = get_factor_weight_policy()
        
        recommended = policy.calculate_recommended_weight(
            current_weight=0.05,
            delta=-0.10,
        )
        
        assert recommended >= WEIGHT_MIN
    
    def test_weight_bounded_max(self):
        """TEST 5: Weight should not exceed 1.0."""
        policy = get_factor_weight_policy()
        
        recommended = policy.calculate_recommended_weight(
            current_weight=0.95,
            delta=0.15,
        )
        
        assert recommended <= WEIGHT_MAX


class TestFactorWeightRegistry:
    """Tests for factor weight registry."""
    
    def test_initialize_defaults(self):
        """Registry should initialize with defaults."""
        registry = FactorWeightRegistry()
        registry.initialize_defaults()
        
        weights = registry.get_all_weights()
        assert len(weights) > 0
    
    def test_update_weight(self):
        """TEST 7: Should update weight and record history."""
        registry = FactorWeightRegistry()
        registry.initialize_defaults()
        
        registry.update_weight(
            factor_name="trend_breakout_factor",
            new_weight=0.08,
            action=AdjustmentAction.DECREASE,
            reason="test_decrease",
        )
        
        state = registry.get_weight("trend_breakout_factor")
        assert state.current_weight == 0.08
        
        history = registry.get_history("trend_breakout_factor")
        assert len(history) > 0


class TestFactorWeightAdjustmentEngine:
    """Tests for factor weight adjustment engine."""
    
    def test_compute_adjustments(self):
        """Should compute adjustments for all factors."""
        engine = get_factor_weight_adjustment_engine()
        
        summary = engine.compute_adjustments()
        
        assert summary.total_factors > 0
        assert len(summary.adjustments) == summary.total_factors
    
    def test_summary_output(self):
        """TEST 6: Summary should have correct structure."""
        engine = get_factor_weight_adjustment_engine()
        
        summary = engine.compute_adjustments()
        
        # All factors should be categorized
        total_categorized = (
            len(summary.increased) +
            len(summary.decreased) +
            len(summary.held) +
            len(summary.shadowed) +
            len(summary.retired)
        )
        assert total_categorized == summary.total_factors
    
    def test_no_failures_no_harsh_penalty(self):
        """TEST 9: Factor with no failures should not be harshly penalized."""
        engine = get_factor_weight_adjustment_engine()
        
        # funding_factor has ELITE governance
        adjustment = engine.compute_factor_adjustment("funding_factor")
        
        if adjustment:
            # Should not be SHADOW or RETIRE
            assert adjustment.adjustment_action not in [
                AdjustmentAction.SHADOW,
                AdjustmentAction.RETIRE,
            ]
    
    def test_adjustment_to_dict(self):
        """TEST 10: Adjustment should convert to dict correctly."""
        engine = get_factor_weight_adjustment_engine()
        
        summary = engine.compute_adjustments()
        
        if summary.adjustments:
            d = summary.adjustments[0].to_dict()
            
            assert "factor_name" in d
            assert "current_weight" in d
            assert "recommended_weight" in d
            assert "weight_delta" in d
            assert "adjustment_action" in d
            assert "signals" in d


class TestRepeatedFailures:
    """Tests for repeated failure handling."""
    
    def test_repeated_failures_amplify(self):
        """TEST 8: Repeated failures should amplify decrease."""
        policy = get_factor_weight_policy()
        
        # Single critical failure
        action1, strength1 = policy.determine_action(
            critical_failures=1,
            failure_patterns_count=1,
            governance_state="WATCHLIST",
            deployment_state="LIVE",
        )
        
        # Multiple critical failures
        action2, strength2 = policy.determine_action(
            critical_failures=3,
            failure_patterns_count=5,
            governance_state="DEGRADED",
            deployment_state="REDUCE",
        )
        
        # Multiple should be more severe
        strength_order = {
            AdjustmentStrength.LOW: 1,
            AdjustmentStrength.MEDIUM: 2,
            AdjustmentStrength.HIGH: 3,
            AdjustmentStrength.CRITICAL: 4,
        }
        
        # Either strength should be higher or action should be more severe
        assert (
            strength_order.get(strength2, 0) >= strength_order.get(strength1, 0) or
            action2 in [AdjustmentAction.SHADOW, AdjustmentAction.RETIRE]
        )


class TestOutputFormats:
    """Tests for output formats."""
    
    def test_summary_to_dict(self):
        """Summary to_dict should be correct."""
        engine = get_factor_weight_adjustment_engine()
        
        summary = engine.compute_adjustments()
        d = summary.to_dict()
        
        assert "total_factors" in d
        assert "increased" in d
        assert "decreased" in d
        assert "counts" in d
    
    def test_summary_to_full_dict(self):
        """Summary to_full_dict should include adjustments."""
        engine = get_factor_weight_adjustment_engine()
        
        summary = engine.compute_adjustments()
        d = summary.to_full_dict()
        
        assert "adjustments" in d
        assert isinstance(d["adjustments"], list)


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 20.2 — Factor Weight Adjustment Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestAdjustmentAction,
        TestFactorWeightPolicy,
        TestWeightBounds,
        TestFactorWeightRegistry,
        TestFactorWeightAdjustmentEngine,
        TestRepeatedFailures,
        TestOutputFormats,
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
