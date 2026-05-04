"""
PHASE 23.2 — Stress Grid Tests
==============================
Test suite for Multi-Scenario Stress Grid.

Tests:
1. All scenarios executed
2. Worst scenario detection correct
3. Average drawdown calculation correct
4. Fragility index calculation correct
5. Resilience state classification correct
6. Stable state logic correct
7. Fragile state logic correct
8. Critical state logic correct
9. Recommended action correct
10. API output correct
"""

import pytest
from .stress_grid_types import (
    ResilienceState,
    ResilienceAction,
    StressGridState,
    RESILIENCE_THRESHOLDS,
)
from .stress_grid_runner import StressGridRunner
from .stress_grid_engine import StressGridEngine
from .stress_grid_aggregator import StressGridAggregator

from ..scenario_registry import SCENARIO_REGISTRY


class TestStressGrid:
    """Tests for Stress Grid."""
    
    @pytest.fixture
    def aggregator(self):
        return StressGridAggregator()
    
    @pytest.fixture
    def runner(self):
        return StressGridRunner()
    
    @pytest.fixture
    def engine(self):
        return StressGridEngine()
    
    # ═══════════════════════════════════════════════════════════
    # TEST 1: All scenarios executed
    # ═══════════════════════════════════════════════════════════
    
    def test_all_scenarios_executed(self, aggregator):
        """All registered scenarios should be executed."""
        grid_state = aggregator.run_grid(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        assert grid_state.scenarios_run == len(SCENARIO_REGISTRY)
        assert grid_state.scenarios_run >= 20
        assert len(grid_state.scenario_results) == grid_state.scenarios_run
    
    # ═══════════════════════════════════════════════════════════
    # TEST 2: Worst scenario detection correct
    # ═══════════════════════════════════════════════════════════
    
    def test_worst_scenario_detection(self, aggregator):
        """Worst scenario should have highest drawdown."""
        grid_state = aggregator.run_grid(
            net_exposure=0.6,
            gross_exposure=0.9,
            portfolio_beta=1.2,
        )
        
        # Verify worst scenario is correctly identified
        assert grid_state.worst_scenario is not None
        assert grid_state.worst_drawdown > 0
        
        # Verify it has max drawdown
        all_drawdowns = [s.estimated_drawdown for s in grid_state.scenario_results]
        assert grid_state.worst_drawdown == max(all_drawdowns)
    
    # ═══════════════════════════════════════════════════════════
    # TEST 3: Average drawdown calculation correct
    # ═══════════════════════════════════════════════════════════
    
    def test_average_drawdown_calculation(self, aggregator):
        """Average drawdown should be calculated correctly."""
        grid_state = aggregator.run_grid(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        # Calculate expected average
        all_drawdowns = [s.estimated_drawdown for s in grid_state.scenario_results]
        expected_avg = sum(all_drawdowns) / len(all_drawdowns)
        
        assert abs(grid_state.average_drawdown - expected_avg) < 0.001
    
    # ═══════════════════════════════════════════════════════════
    # TEST 4: Fragility index calculation correct
    # ═══════════════════════════════════════════════════════════
    
    def test_fragility_index_calculation(self, engine):
        """Fragility index should be weighted average."""
        # Test with known counts
        # Formula: (0.50*broken + 0.30*fragile + 0.20*stressed) / total
        
        fragility = engine.calculate_fragility_index(
            stable_count=10,
            stressed_count=5,
            fragile_count=3,
            broken_count=2,
        )
        
        # Expected: (0.50*2 + 0.30*3 + 0.20*5 + 0.00*10) / 20
        # = (1.0 + 0.9 + 1.0 + 0) / 20 = 2.9 / 20 = 0.145
        expected = (0.50*2 + 0.30*3 + 0.20*5 + 0.00*10) / 20
        
        assert abs(fragility - expected) < 0.01
    
    # ═══════════════════════════════════════════════════════════
    # TEST 5: Resilience state classification correct
    # ═══════════════════════════════════════════════════════════
    
    def test_resilience_state_classification(self, engine):
        """Resilience state should match fragility thresholds."""
        # STRONG (< 0.20)
        assert engine.get_resilience_state(0.15) == ResilienceState.STRONG
        
        # STABLE (0.20-0.40)
        assert engine.get_resilience_state(0.30) == ResilienceState.STABLE
        
        # FRAGILE (0.40-0.60)
        assert engine.get_resilience_state(0.50) == ResilienceState.FRAGILE
        
        # CRITICAL (> 0.60)
        assert engine.get_resilience_state(0.75) == ResilienceState.CRITICAL
    
    # ═══════════════════════════════════════════════════════════
    # TEST 6: Stable state logic correct
    # ═══════════════════════════════════════════════════════════
    
    def test_stable_state_logic(self, aggregator):
        """Low exposure should produce STRONG/STABLE state."""
        grid_state = aggregator.run_grid(
            net_exposure=0.15,
            gross_exposure=0.20,
            portfolio_beta=0.5,
        )
        
        # Very low exposure should be resilient
        assert grid_state.system_resilience_state in [ResilienceState.STRONG, ResilienceState.STABLE]
        assert grid_state.fragility_index < 0.50
    
    # ═══════════════════════════════════════════════════════════
    # TEST 7: Fragile state logic correct
    # ═══════════════════════════════════════════════════════════
    
    def test_fragile_state_logic(self, aggregator):
        """Moderate-high exposure should produce FRAGILE state."""
        grid_state = aggregator.run_grid(
            net_exposure=0.6,
            gross_exposure=0.9,
            portfolio_beta=1.3,
        )
        
        # Higher exposure should be more fragile
        assert grid_state.fragility_index > 0.30
        assert grid_state.broken_count > 0 or grid_state.fragile_count > 0
    
    # ═══════════════════════════════════════════════════════════
    # TEST 8: Critical state logic correct
    # ═══════════════════════════════════════════════════════════
    
    def test_critical_state_logic(self, aggregator):
        """Very high exposure should produce FRAGILE or CRITICAL state."""
        grid_state = aggregator.run_grid(
            net_exposure=0.9,
            gross_exposure=1.5,
            portfolio_beta=2.0,
        )
        
        # Very high exposure should be fragile or critical
        assert grid_state.fragility_index > 0.40
        assert grid_state.system_resilience_state in [ResilienceState.FRAGILE, ResilienceState.CRITICAL]
        assert grid_state.broken_count > grid_state.stable_count
    
    # ═══════════════════════════════════════════════════════════
    # TEST 9: Recommended action correct
    # ═══════════════════════════════════════════════════════════
    
    def test_recommended_actions(self, engine):
        """Recommended actions should match resilience states."""
        # STRONG -> HOLD
        assert engine.get_recommended_action(ResilienceState.STRONG) == ResilienceAction.HOLD
        
        # STABLE -> HEDGE
        assert engine.get_recommended_action(ResilienceState.STABLE) == ResilienceAction.HEDGE
        
        # FRAGILE -> DELEVER
        assert engine.get_recommended_action(ResilienceState.FRAGILE) == ResilienceAction.DELEVER
        
        # CRITICAL -> REDUCE_SYSTEM_RISK
        assert engine.get_recommended_action(ResilienceState.CRITICAL) == ResilienceAction.REDUCE_SYSTEM_RISK
    
    # ═══════════════════════════════════════════════════════════
    # TEST 10: API output correct
    # ═══════════════════════════════════════════════════════════
    
    def test_api_output_format(self, aggregator):
        """API output should have correct format."""
        grid_state = aggregator.run_grid(
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        output = grid_state.to_dict()
        
        # Check required fields
        assert "scenarios_run" in output
        assert "stable_count" in output
        assert "stressed_count" in output
        assert "fragile_count" in output
        assert "broken_count" in output
        assert "worst_scenario" in output
        assert "worst_drawdown" in output
        assert "average_drawdown" in output
        assert "fragility_index" in output
        assert "system_resilience_state" in output
        assert "recommended_action" in output
        assert "confidence_modifier" in output
        assert "capital_modifier" in output
        assert "reason" in output
        assert "timestamp" in output
        
        # Check types
        assert isinstance(output["scenarios_run"], int)
        assert isinstance(output["fragility_index"], float)
        assert isinstance(output["system_resilience_state"], str)
        
        # Check ranges
        assert 0 <= output["fragility_index"] <= 1
        assert 0 <= output["average_drawdown"] <= 1
        assert output["confidence_modifier"] > 0
        assert output["capital_modifier"] > 0
        
        # Check counts sum
        total = output["stable_count"] + output["stressed_count"] + output["fragile_count"] + output["broken_count"]
        assert total == output["scenarios_run"]
        
        # Check full dict has scenario_results
        full_output = grid_state.to_full_dict()
        assert "scenario_results" in full_output
        assert "by_type_breakdown" in full_output


def run_all_tests():
    """Run all tests and return results."""
    test_class = TestStressGrid()
    aggregator = StressGridAggregator()
    runner = StressGridRunner()
    engine = StressGridEngine()
    
    results = []
    
    tests = [
        ("test_1_all_scenarios_executed", lambda: test_class.test_all_scenarios_executed(aggregator)),
        ("test_2_worst_scenario_detection", lambda: test_class.test_worst_scenario_detection(aggregator)),
        ("test_3_average_drawdown_calculation", lambda: test_class.test_average_drawdown_calculation(aggregator)),
        ("test_4_fragility_index_calculation", lambda: test_class.test_fragility_index_calculation(engine)),
        ("test_5_resilience_state_classification", lambda: test_class.test_resilience_state_classification(engine)),
        ("test_6_stable_state_logic", lambda: test_class.test_stable_state_logic(aggregator)),
        ("test_7_fragile_state_logic", lambda: test_class.test_fragile_state_logic(aggregator)),
        ("test_8_critical_state_logic", lambda: test_class.test_critical_state_logic(aggregator)),
        ("test_9_recommended_actions", lambda: test_class.test_recommended_actions(engine)),
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
    print(f"STRESS GRID TESTS")
    print(f"{'='*60}")
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Failed: {results['failed']}")
    print(f"\nResults:")
    for r in results["results"]:
        status = "✅" if r["status"] == "PASSED" else "❌"
        print(f"  {status} {r['test']}")
        if r["status"] != "PASSED" and "error" in r:
            print(f"     Error: {r['error']}")
