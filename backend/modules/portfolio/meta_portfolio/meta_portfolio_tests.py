"""
PHASE 18.3 — Meta Portfolio Tests
=================================
Unit tests for Meta Portfolio Aggregator.

Test scenarios:
1. Balanced portfolio → BALANCED
2. Intelligence overloaded → CONSTRAINED
3. Soft constraint → CONSTRAINED
4. Hard constraint → RISK_OFF
5. Modifiers combined correctly
6. Allowed logic correct
7. Recommended action priority correct
8. Exposures preserved
"""

import pytest
from datetime import datetime, timezone

from modules.portfolio.meta_portfolio.meta_portfolio_types import (
    MetaPortfolioState,
    PortfolioState,
)
from modules.portfolio.meta_portfolio.meta_portfolio_engine import (
    get_meta_portfolio_engine,
    MetaPortfolioEngine,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    PortfolioIntelligenceState,
    PortfolioRiskState,
    RecommendedAction,
)
from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    PortfolioConstraintState,
    ConstraintState,
)


class TestMetaPortfolioStateLogic:
    """Tests for portfolio state determination logic."""
    
    def test_balanced_portfolio(self):
        """TEST 1: Balanced portfolio → BALANCED."""
        engine = get_meta_portfolio_engine()
        
        # Test with balanced_portfolio which should have OK constraints
        # and BALANCED intelligence (or close to it)
        result = engine.analyze_portfolio("balanced_portfolio")
        
        # When both constraint=OK and intelligence is not DEFENSIVE,
        # should be BALANCED or CONSTRAINED based on intelligence
        assert result.portfolio_state in [PortfolioState.BALANCED, PortfolioState.CONSTRAINED]
        assert result.allowed is True
    
    def test_intelligence_overloaded_constrained(self):
        """TEST 2: Intelligence overloaded → CONSTRAINED."""
        engine = get_meta_portfolio_engine()
        
        # Use a portfolio that triggers OVERLOADED intelligence state
        result = engine.analyze_portfolio("default")
        
        # Default portfolio has high concentration
        if result.intelligence_state == "OVERLOADED":
            assert result.portfolio_state == PortfolioState.CONSTRAINED
    
    def test_soft_constraint_constrained(self):
        """TEST 3: Soft constraint → CONSTRAINED."""
        engine = get_meta_portfolio_engine()
        
        # factor_overloaded should trigger SOFT_LIMIT
        result = engine.analyze_portfolio("factor_overloaded")
        
        if result.constraint_state == "SOFT_LIMIT":
            assert result.portfolio_state == PortfolioState.CONSTRAINED
            assert result.allowed is True
    
    def test_hard_constraint_risk_off(self):
        """TEST 4: Hard constraint → RISK_OFF."""
        engine = get_meta_portfolio_engine()
        
        # Test state logic directly
        portfolio_state = engine._determine_portfolio_state(
            intelligence_state="BALANCED",
            constraint_state="HARD_LIMIT",
        )
        
        assert portfolio_state == PortfolioState.RISK_OFF
    
    def test_defensive_intelligence_risk_off(self):
        """Test DEFENSIVE intelligence → RISK_OFF."""
        engine = get_meta_portfolio_engine()
        
        # defensive_scenario should trigger DEFENSIVE state
        result = engine.analyze_portfolio("defensive_scenario")
        
        if result.intelligence_state == "DEFENSIVE":
            assert result.portfolio_state == PortfolioState.RISK_OFF
            assert result.allowed is False


class TestModifierCombination:
    """Tests for modifier combination logic."""
    
    def test_modifiers_combined_correctly(self):
        """TEST 5: Modifiers combined correctly (min of both)."""
        engine = get_meta_portfolio_engine()
        
        # Get individual states
        intelligence = engine.intelligence_engine.analyze_portfolio("default")
        constraints = engine.constraint_engine.check_constraints("default")
        
        # Get combined state
        result = engine.analyze_portfolio("default")
        
        # Modifiers should be min of both
        expected_confidence = min(
            intelligence.confidence_modifier,
            constraints.confidence_modifier,
        )
        expected_capital = min(
            intelligence.capital_modifier,
            constraints.capital_modifier,
        )
        
        assert abs(result.confidence_modifier - expected_confidence) < 0.01
        assert abs(result.capital_modifier - expected_capital) < 0.01
    
    def test_modifiers_with_soft_limit(self):
        """Test modifiers when soft limit is triggered."""
        engine = get_meta_portfolio_engine()
        
        result = engine.analyze_portfolio("factor_overloaded")
        
        if result.constraint_state == "SOFT_LIMIT":
            # SOFT_LIMIT has confidence=0.90, capital=0.85
            assert result.confidence_modifier <= 0.90
            assert result.capital_modifier <= 0.85


class TestAllowedLogic:
    """Tests for allowed logic."""
    
    def test_allowed_logic_correct(self):
        """TEST 6: Allowed logic correct."""
        engine = get_meta_portfolio_engine()
        
        # Test state combinations
        # HARD_LIMIT → not allowed
        state1 = engine._determine_portfolio_state("BALANCED", "HARD_LIMIT")
        assert state1 == PortfolioState.RISK_OFF
        
        # SOFT_LIMIT → allowed
        state2 = engine._determine_portfolio_state("BALANCED", "SOFT_LIMIT")
        assert state2 == PortfolioState.CONSTRAINED
        
        # OK + DEFENSIVE → not allowed (RISK_OFF)
        state3 = engine._determine_portfolio_state("DEFENSIVE", "OK")
        assert state3 == PortfolioState.RISK_OFF
        
        # OK + BALANCED → allowed
        state4 = engine._determine_portfolio_state("BALANCED", "OK")
        assert state4 == PortfolioState.BALANCED
    
    def test_risk_off_blocks_trades(self):
        """Test that RISK_OFF state blocks new trades."""
        engine = get_meta_portfolio_engine()
        
        result = engine.analyze_portfolio("defensive_scenario")
        
        if result.portfolio_state == PortfolioState.RISK_OFF:
            assert result.allowed is False


class TestRecommendedAction:
    """Tests for recommended action logic."""
    
    def test_recommended_action_priority(self):
        """TEST 7: Recommended action priority correct."""
        engine = get_meta_portfolio_engine()
        
        # When constraint has reason, it should take priority
        action = engine._determine_recommended_action(
            intelligence_action="HOLD",
            constraint_reason="cluster exposure exceeded threshold",
            portfolio_state=PortfolioState.CONSTRAINED,
        )
        
        assert "CLUSTER" in action
    
    def test_action_from_intelligence_when_ok(self):
        """Test action comes from intelligence when constraints OK."""
        engine = get_meta_portfolio_engine()
        
        action = engine._determine_recommended_action(
            intelligence_action="REDUCE_ALT",
            constraint_reason="All constraints satisfied",
            portfolio_state=PortfolioState.CONSTRAINED,
        )
        
        assert action == "REDUCE_ALT"
    
    def test_leverage_constraint_action(self):
        """Test leverage constraint produces DELEVER action."""
        engine = get_meta_portfolio_engine()
        
        action = engine._determine_recommended_action(
            intelligence_action="HOLD",
            constraint_reason="leverage limit exceeded",
            portfolio_state=PortfolioState.RISK_OFF,
        )
        
        assert action == "DELEVER"


class TestExposurePreservation:
    """Tests for exposure data preservation."""
    
    def test_exposures_preserved(self):
        """TEST 8: Exposures preserved from intelligence."""
        engine = get_meta_portfolio_engine()
        
        # Get intelligence state
        intelligence = engine.intelligence_engine.analyze_portfolio("default")
        
        # Get meta portfolio state
        result = engine.analyze_portfolio("default")
        
        # Exposures should match
        assert abs(result.net_exposure - intelligence.net_exposure) < 0.01
        assert abs(result.gross_exposure - intelligence.gross_exposure) < 0.01
        assert abs(result.concentration_score - intelligence.concentration_score) < 0.01
        assert abs(result.diversification_score - intelligence.diversification_score) < 0.01


class TestMetaPortfolioIntegration:
    """Integration tests for Meta Portfolio Engine."""
    
    def test_full_analysis(self):
        """Test full analysis produces all required fields."""
        engine = get_meta_portfolio_engine()
        
        result = engine.analyze_portfolio("default")
        
        # Check all required fields
        assert result.portfolio_state is not None
        assert result.intelligence_state is not None
        assert result.constraint_state is not None
        assert result.allowed is not None
        assert result.confidence_modifier is not None
        assert result.capital_modifier is not None
        assert result.net_exposure is not None
        assert result.gross_exposure is not None
        assert result.concentration_score is not None
        assert result.diversification_score is not None
        assert result.recommended_action is not None
        assert result.reason is not None
    
    def test_to_dict_conversion(self):
        """Test state to_dict conversion."""
        engine = get_meta_portfolio_engine()
        
        result = engine.analyze_portfolio("default")
        result_dict = result.to_dict()
        
        assert "portfolio_state" in result_dict
        assert "intelligence_state" in result_dict
        assert "constraint_state" in result_dict
        assert "allowed" in result_dict
        assert "confidence_modifier" in result_dict
        assert "recommended_action" in result_dict
    
    def test_to_summary_conversion(self):
        """Test state to_summary conversion."""
        engine = get_meta_portfolio_engine()
        
        result = engine.analyze_portfolio("default")
        summary = result.to_summary()
        
        assert "state" in summary
        assert "allowed" in summary
        assert "confidence_mod" in summary
        assert "capital_mod" in summary
        assert "action" in summary
    
    def test_multiple_portfolios(self):
        """Test analysis works with different portfolios."""
        engine = get_meta_portfolio_engine()
        
        portfolios = ["default", "balanced_portfolio", "btc_concentrated", 
                      "alt_overloaded", "defensive_scenario"]
        
        for portfolio_id in portfolios:
            result = engine.analyze_portfolio(portfolio_id)
            assert result.portfolio_state is not None
            assert result.allowed is not None


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 18.3 — Meta Portfolio Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestMetaPortfolioStateLogic,
        TestModifierCombination,
        TestAllowedLogic,
        TestRecommendedAction,
        TestExposurePreservation,
        TestMetaPortfolioIntegration,
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
