"""
PHASE 18.2 — Portfolio Constraint Tests
=======================================
Unit tests for Portfolio Constraint Engine.

Test scenarios:
1. No violations → OK
2. Factor overload → SOFT_LIMIT
3. Cluster overload → SOFT_LIMIT
4. Net exposure violation → HARD_LIMIT
5. Gross exposure violation → HARD_LIMIT
6. Leverage violation → HARD_LIMIT
7. Allowed logic correct
8. Modifiers correct
"""

import pytest
from datetime import datetime, timezone

from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    ConstraintState,
    ConstraintType,
    ViolationType,
    CONSTRAINT_STATE_MODIFIERS,
    EXPOSURE_LIMITS,
    CLUSTER_LIMITS,
    FACTOR_LIMITS,
    LEVERAGE_LIMITS,
)
from modules.portfolio.portfolio_constraints.portfolio_constraint_engine import (
    get_portfolio_constraint_engine,
)
from modules.portfolio.portfolio_constraints.exposure_constraint_engine import (
    get_exposure_constraint_engine,
)
from modules.portfolio.portfolio_constraints.cluster_constraint_engine import (
    get_cluster_constraint_engine,
)
from modules.portfolio.portfolio_constraints.factor_constraint_engine import (
    get_factor_constraint_engine,
)
from modules.portfolio.portfolio_constraints.leverage_constraint_engine import (
    get_leverage_constraint_engine,
)


class TestExposureConstraintEngine:
    """Tests for Exposure Constraint Engine."""
    
    def test_no_exposure_violation(self):
        """Test no violation when within limits."""
        engine = get_exposure_constraint_engine()
        
        has_violation, violations = engine.check_constraints(
            net_exposure=1.0,
            gross_exposure=1.5,
        )
        
        assert has_violation is False
        assert len(violations) == 0
    
    def test_net_exposure_violation(self):
        """TEST 4: Net exposure violation → HARD_LIMIT."""
        engine = get_exposure_constraint_engine()
        
        # Exceeds max_net_exposure = 1.5
        has_violation, violations = engine.check_constraints(
            net_exposure=2.0,
            gross_exposure=2.0,
        )
        
        assert has_violation is True
        assert len(violations) >= 1
        assert violations[0].violation_type == ViolationType.EXPOSURE
        assert violations[0].constraint_type == ConstraintType.HARD
    
    def test_gross_exposure_violation(self):
        """TEST 5: Gross exposure violation → HARD_LIMIT."""
        engine = get_exposure_constraint_engine()
        
        # Exceeds max_gross_exposure = 2.5
        has_violation, violations = engine.check_constraints(
            net_exposure=1.0,
            gross_exposure=3.0,
        )
        
        assert has_violation is True
        assert any(v.violation_type == ViolationType.EXPOSURE for v in violations)


class TestClusterConstraintEngine:
    """Tests for Cluster Constraint Engine."""
    
    def test_no_cluster_violation(self):
        """Test no violation when within limits."""
        engine = get_cluster_constraint_engine()
        
        has_violation, violations = engine.check_constraints(
            cluster_exposure={"btc_cluster": 0.40, "eth_cluster": 0.30}
        )
        
        assert has_violation is False
        assert len(violations) == 0
    
    def test_cluster_overload(self):
        """TEST 3: Cluster overload → SOFT_LIMIT."""
        engine = get_cluster_constraint_engine()
        
        # Exceeds max_cluster_exposure = 0.65
        has_violation, violations = engine.check_constraints(
            cluster_exposure={"btc_cluster": 0.70, "eth_cluster": 0.15}
        )
        
        assert has_violation is True
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.CLUSTER
        assert violations[0].constraint_type == ConstraintType.SOFT


class TestFactorConstraintEngine:
    """Tests for Factor Constraint Engine."""
    
    def test_no_factor_violation(self):
        """Test no violation when within limits."""
        engine = get_factor_constraint_engine()
        
        has_violation, violations = engine.check_constraints(
            factor_exposure={"trend": 0.50, "momentum": 0.30}
        )
        
        assert has_violation is False
        assert len(violations) == 0
    
    def test_factor_overload(self):
        """TEST 2: Factor overload → SOFT_LIMIT."""
        engine = get_factor_constraint_engine()
        
        # Exceeds max_factor_exposure = 0.70
        has_violation, violations = engine.check_constraints(
            factor_exposure={"trend": 0.80, "momentum": 0.10}
        )
        
        assert has_violation is True
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.FACTOR
        assert violations[0].constraint_type == ConstraintType.SOFT


class TestLeverageConstraintEngine:
    """Tests for Leverage Constraint Engine."""
    
    def test_no_leverage_violation(self):
        """Test no violation when within limits."""
        engine = get_leverage_constraint_engine()
        
        has_violation, violations = engine.check_constraints(
            gross_exposure=2.0
        )
        
        assert has_violation is False
        assert len(violations) == 0
    
    def test_leverage_violation(self):
        """TEST 6: Leverage violation → HARD_LIMIT."""
        engine = get_leverage_constraint_engine()
        
        # Exceeds max_leverage = 2.5
        has_violation, violations = engine.check_constraints(
            gross_exposure=3.0
        )
        
        assert has_violation is True
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.LEVERAGE
        assert violations[0].constraint_type == ConstraintType.HARD


class TestPortfolioConstraintEngine:
    """Integration tests for Portfolio Constraint Engine."""
    
    def test_no_violations_ok(self):
        """TEST 1: No violations → OK."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0,
            gross_exposure=1.5,
            cluster_exposure={"btc_cluster": 0.40, "eth_cluster": 0.30},
            factor_exposure={"trend": 0.40, "momentum": 0.30},
        )
        
        assert result.constraint_state == ConstraintState.OK
        assert result.allowed is True
        assert result.exposure_violation is False
        assert result.cluster_violation is False
        assert result.factor_violation is False
        assert result.leverage_violation is False
    
    def test_factor_overload_soft_limit(self):
        """TEST 2: Factor overload → SOFT_LIMIT."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0,
            gross_exposure=1.5,
            cluster_exposure={"btc_cluster": 0.40},
            factor_exposure={"trend": 0.80},  # Exceeds 0.70
        )
        
        assert result.constraint_state == ConstraintState.SOFT_LIMIT
        assert result.allowed is True
        assert result.factor_violation is True
    
    def test_cluster_overload_soft_limit(self):
        """TEST 3: Cluster overload → SOFT_LIMIT."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0,
            gross_exposure=1.5,
            cluster_exposure={"btc_cluster": 0.70},  # Exceeds 0.65
            factor_exposure={"trend": 0.40},
        )
        
        assert result.constraint_state == ConstraintState.SOFT_LIMIT
        assert result.allowed is True
        assert result.cluster_violation is True
    
    def test_net_exposure_violation_hard_limit(self):
        """TEST 4: Net exposure violation → HARD_LIMIT."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=2.0,  # Exceeds 1.5
            gross_exposure=2.0,
            cluster_exposure={"btc_cluster": 0.40},
            factor_exposure={"trend": 0.40},
        )
        
        assert result.constraint_state == ConstraintState.HARD_LIMIT
        assert result.allowed is False
        assert result.exposure_violation is True
    
    def test_gross_exposure_violation_hard_limit(self):
        """TEST 5: Gross exposure violation → HARD_LIMIT."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0,
            gross_exposure=3.0,  # Exceeds 2.5
            cluster_exposure={"btc_cluster": 0.40},
            factor_exposure={"trend": 0.40},
        )
        
        assert result.constraint_state == ConstraintState.HARD_LIMIT
        assert result.allowed is False
        assert result.exposure_violation is True
    
    def test_leverage_violation_hard_limit(self):
        """TEST 6: Leverage violation → HARD_LIMIT."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0,
            gross_exposure=2.8,  # Exceeds leverage limit 2.5
            cluster_exposure={"btc_cluster": 0.40},
            factor_exposure={"trend": 0.40},
        )
        
        assert result.constraint_state == ConstraintState.HARD_LIMIT
        assert result.allowed is False
        assert result.leverage_violation is True
    
    def test_allowed_logic_correct(self):
        """TEST 7: Allowed logic correct."""
        engine = get_portfolio_constraint_engine()
        
        # OK → allowed
        result_ok = engine.check_constraints_from_state(
            net_exposure=0.5, gross_exposure=1.0,
            cluster_exposure={}, factor_exposure={},
        )
        assert result_ok.constraint_state == ConstraintState.OK
        assert result_ok.allowed is True
        
        # SOFT_LIMIT → allowed
        result_soft = engine.check_constraints_from_state(
            net_exposure=0.5, gross_exposure=1.0,
            cluster_exposure={"btc_cluster": 0.70},  # Violation
            factor_exposure={},
        )
        assert result_soft.constraint_state == ConstraintState.SOFT_LIMIT
        assert result_soft.allowed is True
        
        # HARD_LIMIT → not allowed
        result_hard = engine.check_constraints_from_state(
            net_exposure=2.0,  # Violation
            gross_exposure=2.0,
            cluster_exposure={}, factor_exposure={},
        )
        assert result_hard.constraint_state == ConstraintState.HARD_LIMIT
        assert result_hard.allowed is False
    
    def test_modifiers_correct(self):
        """TEST 8: Modifiers correct."""
        engine = get_portfolio_constraint_engine()
        
        # OK modifiers
        result_ok = engine.check_constraints_from_state(
            net_exposure=0.5, gross_exposure=1.0,
            cluster_exposure={}, factor_exposure={},
        )
        assert result_ok.confidence_modifier == 1.00
        assert result_ok.capital_modifier == 1.00
        
        # SOFT_LIMIT modifiers
        result_soft = engine.check_constraints_from_state(
            net_exposure=0.5, gross_exposure=1.0,
            cluster_exposure={"btc_cluster": 0.70},
            factor_exposure={},
        )
        assert result_soft.confidence_modifier == 0.90
        assert result_soft.capital_modifier == 0.85
        
        # HARD_LIMIT modifiers
        result_hard = engine.check_constraints_from_state(
            net_exposure=2.0, gross_exposure=2.0,
            cluster_exposure={}, factor_exposure={},
        )
        assert result_hard.confidence_modifier == 0.70
        assert result_hard.capital_modifier == 0.00
    
    def test_to_dict_conversion(self):
        """Test state to_dict conversion."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0, gross_exposure=1.5,
            cluster_exposure={"btc_cluster": 0.40},
            factor_exposure={"trend": 0.40},
        )
        result_dict = result.to_dict()
        
        assert "constraint_state" in result_dict
        assert "allowed" in result_dict
        assert "confidence_modifier" in result_dict
        assert "capital_modifier" in result_dict
        assert "reason" in result_dict
    
    def test_to_summary_conversion(self):
        """Test state to_summary conversion."""
        engine = get_portfolio_constraint_engine()
        
        result = engine.check_constraints_from_state(
            net_exposure=1.0, gross_exposure=1.5,
            cluster_exposure={"btc_cluster": 0.40},
            factor_exposure={"trend": 0.40},
        )
        summary = result.to_summary()
        
        assert "state" in summary
        assert "allowed" in summary
        assert "confidence_mod" in summary
        assert "capital_mod" in summary
    
    def test_with_portfolio_id(self):
        """Test checking constraints with portfolio ID."""
        engine = get_portfolio_constraint_engine()
        
        # Use a known portfolio from Portfolio Intelligence
        result = engine.check_constraints("default")
        
        assert result.constraint_state is not None
        assert result.allowed is not None
        assert result.reason is not None


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 18.2 — Portfolio Constraint Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestExposureConstraintEngine,
        TestClusterConstraintEngine,
        TestFactorConstraintEngine,
        TestLeverageConstraintEngine,
        TestPortfolioConstraintEngine,
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
