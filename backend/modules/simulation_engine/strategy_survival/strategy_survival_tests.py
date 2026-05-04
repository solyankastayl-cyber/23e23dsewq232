"""
PHASE 23.3 — Strategy Survival Tests
====================================
Test suite for Strategy Survival Matrix.

Tests:
1. Robust strategy classified correctly
2. Stable strategy classified correctly
3. Fragile strategy classified correctly
4. Broken strategy classified correctly
5. Robustness score calculation correct
6. Recommended action correct
7. Worst scenario detected
8. Most robust / fragile detected
9. Matrix summary correct
10. API output correct
"""

import pytest
from .strategy_survival_types import (
    StrategySurvivalStateEnum,
    StrategyAction,
    StrategySurvivalState,
    StrategySurvivalMatrix,
    DEFAULT_STRATEGIES,
)
from .strategy_survival_engine import StrategySurvivalEngine
from .strategy_survival_aggregator import StrategySurvivalAggregator


class TestStrategySurvival:
    """Tests for Strategy Survival Matrix."""
    
    @pytest.fixture
    def aggregator(self):
        return StrategySurvivalAggregator()
    
    @pytest.fixture
    def engine(self):
        return StrategySurvivalEngine()
    
    # ═══════════════════════════════════════════════════════════
    # TEST 1: Robust strategy classified correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_robust_strategy_classification(self, engine):
        """High stable count should produce ROBUST state."""
        # High stable, low broken = robust
        robustness = engine.calculate_robustness_score(
            stable_count=15,
            stressed_count=4,
            fragile_count=1,
            broken_count=0,
        )
        
        state = engine.get_survival_state(robustness)
        
        assert robustness >= 0.70
        assert state == StrategySurvivalStateEnum.ROBUST
    
    # ═══════════════════════════════════════════════════════════
    # TEST 2: Stable strategy classified correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_stable_strategy_classification(self, engine):
        """Moderate stable count should produce STABLE state."""
        robustness = engine.calculate_robustness_score(
            stable_count=8,
            stressed_count=6,
            fragile_count=4,
            broken_count=2,
        )
        
        state = engine.get_survival_state(robustness)
        
        assert 0.50 <= robustness < 0.70
        assert state == StrategySurvivalStateEnum.STABLE
    
    # ═══════════════════════════════════════════════════════════
    # TEST 3: Fragile strategy classified correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_fragile_strategy_classification(self, engine):
        """Low stable count should produce FRAGILE state."""
        robustness = engine.calculate_robustness_score(
            stable_count=4,
            stressed_count=4,
            fragile_count=6,
            broken_count=6,
        )
        
        state = engine.get_survival_state(robustness)
        
        assert 0.30 <= robustness < 0.50
        assert state == StrategySurvivalStateEnum.FRAGILE
    
    # ═══════════════════════════════════════════════════════════
    # TEST 4: Broken strategy classified correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_broken_strategy_classification(self, engine):
        """High broken count should produce BROKEN state."""
        robustness = engine.calculate_robustness_score(
            stable_count=2,
            stressed_count=2,
            fragile_count=4,
            broken_count=12,
        )
        
        state = engine.get_survival_state(robustness)
        
        assert robustness < 0.30
        assert state == StrategySurvivalStateEnum.BROKEN
    
    # ═══════════════════════════════════════════════════════════
    # TEST 5: Robustness score calculation correct
    # ═══════════════════════════════════════════════════════════
    
    def test_robustness_score_calculation(self, engine):
        """Robustness score should follow the formula."""
        # All stable = max robustness
        all_stable = engine.calculate_robustness_score(
            stable_count=20,
            stressed_count=0,
            fragile_count=0,
            broken_count=0,
        )
        
        # All broken = min robustness
        all_broken = engine.calculate_robustness_score(
            stable_count=0,
            stressed_count=0,
            fragile_count=0,
            broken_count=20,
        )
        
        assert all_stable >= 0.95  # Near max
        assert all_broken <= 0.05  # Near min
        assert all_stable > all_broken
    
    # ═══════════════════════════════════════════════════════════
    # TEST 6: Recommended action correct
    # ═══════════════════════════════════════════════════════════
    
    def test_recommended_actions(self, engine):
        """Recommended actions should match survival states."""
        # ROBUST -> KEEP_ACTIVE
        assert engine.get_recommended_action(StrategySurvivalStateEnum.ROBUST) == StrategyAction.KEEP_ACTIVE
        
        # STABLE -> REDUCE
        assert engine.get_recommended_action(StrategySurvivalStateEnum.STABLE) == StrategyAction.REDUCE
        
        # FRAGILE -> SHADOW
        assert engine.get_recommended_action(StrategySurvivalStateEnum.FRAGILE) == StrategyAction.SHADOW
        
        # BROKEN -> DISABLE
        assert engine.get_recommended_action(StrategySurvivalStateEnum.BROKEN) == StrategyAction.DISABLE
    
    # ═══════════════════════════════════════════════════════════
    # TEST 7: Worst scenario detected
    # ═══════════════════════════════════════════════════════════
    
    def test_worst_scenario_detected(self, aggregator):
        """Worst scenario should be detected for each strategy."""
        state = aggregator.analyze_strategy(
            strategy_name="TREND_FOLLOWING",
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        assert state.worst_scenario is not None
        assert state.worst_scenario != "none"
        assert state.worst_drawdown > 0
    
    # ═══════════════════════════════════════════════════════════
    # TEST 8: Most robust / fragile detected
    # ═══════════════════════════════════════════════════════════
    
    def test_most_robust_fragile_detected(self, aggregator):
        """Matrix should identify most robust and fragile strategies."""
        matrix = aggregator.build_matrix(
            strategies=["FUNDING_ARB", "TREND_FOLLOWING", "LIQUIDATION_CAPTURE"],
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        assert matrix.most_robust is not None
        assert matrix.most_fragile is not None
        assert matrix.most_robust != matrix.most_fragile or len(matrix.strategies) == 1
        
        # Verify most robust has highest score
        most_robust_score = matrix.strategies[matrix.most_robust].robustness_score
        for state in matrix.strategies.values():
            assert state.robustness_score <= most_robust_score
    
    # ═══════════════════════════════════════════════════════════
    # TEST 9: Matrix summary correct
    # ═══════════════════════════════════════════════════════════
    
    def test_matrix_summary(self, aggregator):
        """Matrix summary should be correctly calculated."""
        matrix = aggregator.build_matrix(
            strategies=DEFAULT_STRATEGIES[:4],  # Use first 4
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        # Check counts
        total = matrix.robust_count + matrix.stable_count + matrix.fragile_count + matrix.broken_count
        assert total == len(matrix.strategies)
        
        # Check average robustness
        expected_avg = sum(s.robustness_score for s in matrix.strategies.values()) / len(matrix.strategies)
        assert abs(matrix.average_system_strategy_robustness - expected_avg) < 0.001
    
    # ═══════════════════════════════════════════════════════════
    # TEST 10: API output correct
    # ═══════════════════════════════════════════════════════════
    
    def test_api_output_format(self, aggregator):
        """API output should have correct format."""
        state = aggregator.analyze_strategy(
            strategy_name="MEAN_REVERSION",
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        output = state.to_dict()
        
        # Check required fields
        assert "strategy_name" in output
        assert "scenarios_run" in output
        assert "stable_count" in output
        assert "stressed_count" in output
        assert "fragile_count" in output
        assert "broken_count" in output
        assert "average_drawdown" in output
        assert "worst_drawdown" in output
        assert "robustness_score" in output
        assert "survival_state" in output
        assert "recommended_action" in output
        assert "confidence_modifier" in output
        assert "capital_modifier" in output
        assert "worst_scenario" in output
        assert "reason" in output
        
        # Check types
        assert isinstance(output["robustness_score"], float)
        assert isinstance(output["survival_state"], str)
        assert isinstance(output["recommended_action"], str)
        
        # Check ranges
        assert 0 <= output["robustness_score"] <= 1
        assert 0 <= output["average_drawdown"] <= 1
        assert output["confidence_modifier"] > 0
        
        # Check full dict has by_scenario_type
        full_output = state.to_full_dict()
        assert "by_scenario_type" in full_output


def run_all_tests():
    """Run all tests and return results."""
    test_class = TestStrategySurvival()
    aggregator = StrategySurvivalAggregator()
    engine = StrategySurvivalEngine()
    
    results = []
    
    tests = [
        ("test_1_robust_strategy_classification", lambda: test_class.test_robust_strategy_classification(engine)),
        ("test_2_stable_strategy_classification", lambda: test_class.test_stable_strategy_classification(engine)),
        ("test_3_fragile_strategy_classification", lambda: test_class.test_fragile_strategy_classification(engine)),
        ("test_4_broken_strategy_classification", lambda: test_class.test_broken_strategy_classification(engine)),
        ("test_5_robustness_score_calculation", lambda: test_class.test_robustness_score_calculation(engine)),
        ("test_6_recommended_actions", lambda: test_class.test_recommended_actions(engine)),
        ("test_7_worst_scenario_detected", lambda: test_class.test_worst_scenario_detected(aggregator)),
        ("test_8_most_robust_fragile_detected", lambda: test_class.test_most_robust_fragile_detected(aggregator)),
        ("test_9_matrix_summary", lambda: test_class.test_matrix_summary(aggregator)),
        ("test_10_api_output", lambda: test_class.test_api_output_format(aggregator)),
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
    print(f"STRATEGY SURVIVAL MATRIX TESTS")
    print(f"{'='*60}")
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Failed: {results['failed']}")
    print(f"\nResults:")
    for r in results["results"]:
        status = "✅" if r["status"] == "PASSED" else "❌"
        print(f"  {status} {r['test']}")
        if r["status"] != "PASSED" and "error" in r:
            print(f"     Error: {r['error']}")
