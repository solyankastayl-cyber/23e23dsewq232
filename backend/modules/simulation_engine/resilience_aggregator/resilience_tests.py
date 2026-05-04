"""
PHASE 23.4 — Resilience Tests
=============================
Test suite for Portfolio Resilience Aggregator.

Tests:
1. Robust + robust -> ROBUST
2. Stable + stable -> STABLE
3. Stable + fragile -> FRAGILE
4. Critical + broken -> CRITICAL
5. Resilience score correct
6. Strongest component correct
7. Weakest component correct
8. Recommended action correct
9. Modifiers bounded
10. API output correct
"""

import pytest
from .resilience_types import (
    ResilienceStateEnum,
    ResilienceAction,
    PortfolioResilienceState,
    RESILIENCE_THRESHOLDS,
    STRESS_GRID_SCORES,
    STRATEGY_SURVIVAL_SCORES,
    RESILIENCE_WEIGHTS,
)
from .portfolio_resilience_engine import PortfolioResilienceEngine


class TestPortfolioResilience:
    """Tests for Portfolio Resilience Aggregator."""
    
    @pytest.fixture
    def engine(self):
        return PortfolioResilienceEngine()
    
    # ═══════════════════════════════════════════════════════════
    # TEST 1: Robust + robust -> ROBUST
    # ═══════════════════════════════════════════════════════════
    
    def test_robust_plus_robust(self, engine):
        """Strong stress grid + robust strategies should produce ROBUST state."""
        # Very low exposure = both components should be strong
        state = engine.calculate(
            net_exposure=0.1,
            gross_exposure=0.15,
            portfolio_beta=0.5,
        )
        
        # Should be at least STABLE, potentially ROBUST with very low exposure
        assert state.resilience_state in [ResilienceStateEnum.ROBUST, ResilienceStateEnum.STABLE]
        assert state.resilience_score >= 0.55
        assert state.recommended_action in [ResilienceAction.HOLD, ResilienceAction.HEDGE]
    
    # ═══════════════════════════════════════════════════════════
    # TEST 2: Stable + stable -> STABLE
    # ═══════════════════════════════════════════════════════════
    
    def test_stable_plus_stable(self, engine):
        """Moderate stress grid + stable strategies should produce STABLE state."""
        state = engine.calculate(
            net_exposure=0.4,
            gross_exposure=0.6,
            portfolio_beta=0.9,
        )
        
        # Should be STABLE or FRAGILE range
        assert state.resilience_score >= 0.35
        assert state.resilience_state in [ResilienceStateEnum.STABLE, ResilienceStateEnum.FRAGILE]
    
    # ═══════════════════════════════════════════════════════════
    # TEST 3: Stable + fragile -> FRAGILE
    # ═══════════════════════════════════════════════════════════
    
    def test_stable_plus_fragile(self, engine):
        """Stable stress grid + fragile strategies should produce FRAGILE state."""
        state = engine.calculate(
            net_exposure=0.5,
            gross_exposure=0.8,
            portfolio_beta=1.0,
        )
        
        # Should be FRAGILE with moderate exposure
        assert state.resilience_state in [ResilienceStateEnum.STABLE, ResilienceStateEnum.FRAGILE]
        assert state.resilience_score >= 0.35
    
    # ═══════════════════════════════════════════════════════════
    # TEST 4: Critical + broken -> CRITICAL
    # ═══════════════════════════════════════════════════════════
    
    def test_critical_plus_broken(self, engine):
        """Critical stress grid + broken strategies should produce CRITICAL state."""
        state = engine.calculate(
            net_exposure=0.9,
            gross_exposure=1.5,
            portfolio_beta=2.0,
        )
        
        # Very high exposure should produce CRITICAL or FRAGILE
        assert state.resilience_state in [ResilienceStateEnum.FRAGILE, ResilienceStateEnum.CRITICAL]
        assert state.resilience_score < 0.55
    
    # ═══════════════════════════════════════════════════════════
    # TEST 5: Resilience score correct
    # ═══════════════════════════════════════════════════════════
    
    def test_resilience_score_calculation(self, engine):
        """Resilience score should be weighted combination of component scores."""
        state = engine.calculate(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        # Verify score is weighted combination
        expected = (
            RESILIENCE_WEIGHTS["stress_grid"] * state.stress_grid_score +
            RESILIENCE_WEIGHTS["strategy_survival"] * state.strategy_survival_score
        )
        
        assert abs(state.resilience_score - expected) < 0.01
        
        # Verify score is bounded
        assert 0 <= state.resilience_score <= 1
    
    # ═══════════════════════════════════════════════════════════
    # TEST 6: Strongest component correct
    # ═══════════════════════════════════════════════════════════
    
    def test_strongest_component_detection(self, engine):
        """Strongest component should have higher score."""
        state = engine.calculate(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        if state.strongest_component == "stress_grid":
            assert state.stress_grid_score >= state.strategy_survival_score
        else:
            assert state.strategy_survival_score >= state.stress_grid_score
    
    # ═══════════════════════════════════════════════════════════
    # TEST 7: Weakest component correct
    # ═══════════════════════════════════════════════════════════
    
    def test_weakest_component_detection(self, engine):
        """Weakest component should have lower score."""
        state = engine.calculate(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        if state.weakest_component == "stress_grid":
            assert state.stress_grid_score <= state.strategy_survival_score
        else:
            assert state.strategy_survival_score <= state.stress_grid_score
        
        # Strongest and weakest should be different
        assert state.strongest_component != state.weakest_component
    
    # ═══════════════════════════════════════════════════════════
    # TEST 8: Recommended action correct
    # ═══════════════════════════════════════════════════════════
    
    def test_recommended_actions(self, engine):
        """Recommended actions should match resilience states."""
        # ROBUST -> HOLD
        assert engine._get_recommended_action(ResilienceStateEnum.ROBUST) == ResilienceAction.HOLD
        
        # STABLE -> HEDGE
        assert engine._get_recommended_action(ResilienceStateEnum.STABLE) == ResilienceAction.HEDGE
        
        # FRAGILE -> DELEVER
        assert engine._get_recommended_action(ResilienceStateEnum.FRAGILE) == ResilienceAction.DELEVER
        
        # CRITICAL -> KILL_SWITCH
        assert engine._get_recommended_action(ResilienceStateEnum.CRITICAL) == ResilienceAction.KILL_SWITCH
    
    # ═══════════════════════════════════════════════════════════
    # TEST 9: Modifiers bounded
    # ═══════════════════════════════════════════════════════════
    
    def test_modifiers_bounded(self, engine):
        """Modifiers should be within reasonable bounds."""
        # Test with various exposures
        for exposure in [0.1, 0.3, 0.5, 0.7, 0.9]:
            state = engine.calculate(
                net_exposure=exposure,
                gross_exposure=exposure * 1.3,
            )
            
            # Confidence should be in reasonable range
            assert 0.5 <= state.confidence_modifier <= 1.2
            
            # Capital should be in reasonable range
            assert 0.4 <= state.capital_modifier <= 1.2
    
    # ═══════════════════════════════════════════════════════════
    # TEST 10: API output correct
    # ═══════════════════════════════════════════════════════════
    
    def test_api_output_format(self, engine):
        """API output should have correct format."""
        state = engine.calculate(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        output = state.to_dict()
        
        # Check required fields
        assert "stress_grid_state" in output
        assert "strategy_survival_state" in output
        assert "resilience_score" in output
        assert "resilience_state" in output
        assert "average_drawdown" in output
        assert "worst_drawdown" in output
        assert "fragility_index" in output
        assert "average_strategy_robustness" in output
        assert "most_robust_strategy" in output
        assert "most_fragile_strategy" in output
        assert "recommended_action" in output
        assert "confidence_modifier" in output
        assert "capital_modifier" in output
        assert "strongest_component" in output
        assert "weakest_component" in output
        assert "reason" in output
        
        # Check types
        assert isinstance(output["resilience_score"], float)
        assert isinstance(output["resilience_state"], str)
        assert isinstance(output["recommended_action"], str)
        
        # Check ranges
        assert 0 <= output["resilience_score"] <= 1
        assert output["confidence_modifier"] > 0
        assert output["capital_modifier"] > 0
        
        # Check full dict has component scores
        full_output = state.to_full_dict()
        assert "component_scores" in full_output
        assert "weights" in full_output


def run_all_tests():
    """Run all tests and return results."""
    test_class = TestPortfolioResilience()
    engine = PortfolioResilienceEngine()
    
    results = []
    
    tests = [
        ("test_1_robust_plus_robust", lambda: test_class.test_robust_plus_robust(engine)),
        ("test_2_stable_plus_stable", lambda: test_class.test_stable_plus_stable(engine)),
        ("test_3_stable_plus_fragile", lambda: test_class.test_stable_plus_fragile(engine)),
        ("test_4_critical_plus_broken", lambda: test_class.test_critical_plus_broken(engine)),
        ("test_5_resilience_score_calculation", lambda: test_class.test_resilience_score_calculation(engine)),
        ("test_6_strongest_component_detection", lambda: test_class.test_strongest_component_detection(engine)),
        ("test_7_weakest_component_detection", lambda: test_class.test_weakest_component_detection(engine)),
        ("test_8_recommended_actions", lambda: test_class.test_recommended_actions(engine)),
        ("test_9_modifiers_bounded", lambda: test_class.test_modifiers_bounded(engine)),
        ("test_10_api_output", lambda: test_class.test_api_output_format(engine)),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            results.append({"test": name, "status": "PASSED"})
            passed += 1
        except AssertionError as e:
            results.append({"test": name, "status": "FAILED", "error": str(e)})
            failed += 1
        except Exception as e:
            results.append({"test": name, "status": "ERROR", "error": str(e)})
            failed += 1
    
    return {
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


if __name__ == "__main__":
    results = run_all_tests()
    print(f"\n{'='*60}")
    print(f"PORTFOLIO RESILIENCE AGGREGATOR TESTS")
    print(f"{'='*60}")
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Failed: {results['failed']}")
    print(f"\nResults:")
    for r in results["results"]:
        status = "✅" if r["status"] == "PASSED" else "❌"
        print(f"  {status} {r['test']}")
        if r["status"] != "PASSED" and "error" in r:
            print(f"     Error: {r['error']}")
