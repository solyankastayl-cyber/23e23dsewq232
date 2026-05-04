"""
PHASE 23.1 — Simulation Tests
=============================
Test suite for Simulation / Crisis Engine.

Tests:
1. Scenario registry loads
2. Flash crash simulated
3. Vol shock simulated
4. Correlation spike simulated
5. Liquidity freeze simulated
6. Regime flip simulated
7. Drawdown classification correct
8. Survival state correct
9. Recommended action correct
10. API output correct
"""

import pytest
from .simulation_types import (
    ScenarioType,
    SeverityLevel,
    SurvivalState,
    SurvivalAction,
    SimulationScenario,
    SimulationResult,
)
from .scenario_registry import (
    SCENARIO_REGISTRY,
    get_scenario,
    list_scenarios,
    get_scenarios_by_type,
)
from .shock_simulator import ShockSimulator
from .portfolio_impact_engine import PortfolioImpactEngine
from .simulation_aggregator import SimulationAggregator


class TestSimulationEngine:
    """Tests for Simulation Engine."""
    
    @pytest.fixture
    def aggregator(self):
        return SimulationAggregator()
    
    @pytest.fixture
    def shock_simulator(self):
        return ShockSimulator()
    
    @pytest.fixture
    def impact_engine(self):
        return PortfolioImpactEngine()
    
    # ═══════════════════════════════════════════════════════════
    # TEST 1: Scenario registry loads
    # ═══════════════════════════════════════════════════════════
    
    def test_scenario_registry_loads(self):
        """Scenario registry should load all scenarios."""
        scenarios = list_scenarios()
        
        assert len(scenarios) > 0
        assert len(SCENARIO_REGISTRY) >= 20  # At least 20 scenarios
        
        # Check all scenario types are covered
        types_covered = set()
        for scenario in SCENARIO_REGISTRY.values():
            types_covered.add(scenario.scenario_type)
        
        assert ScenarioType.FLASH_CRASH in types_covered
        assert ScenarioType.VOL_SHOCK in types_covered
        assert ScenarioType.CORR_SPIKE in types_covered
        assert ScenarioType.LIQ_FREEZE in types_covered
        assert ScenarioType.REGIME_FLIP in types_covered
    
    # ═══════════════════════════════════════════════════════════
    # TEST 2: Flash crash simulated
    # ═══════════════════════════════════════════════════════════
    
    def test_flash_crash_simulation(self, aggregator):
        """Flash crash scenario should simulate correctly."""
        result = aggregator.run_scenario(
            scenario_name="flash_crash_high",
            net_exposure=0.6,
            gross_exposure=0.9,
            portfolio_beta=1.2,
        )
        
        assert result is not None
        assert result.scenario_name == "flash_crash_high"
        assert result.severity == SeverityLevel.HIGH
        assert result.estimated_pnl_impact < 0  # Should be negative
        assert result.estimated_drawdown > 0   # Should have drawdown
    
    # ═══════════════════════════════════════════════════════════
    # TEST 3: Vol shock simulated
    # ═══════════════════════════════════════════════════════════
    
    def test_vol_shock_simulation(self, aggregator):
        """Volatility shock scenario should simulate correctly."""
        result = aggregator.run_scenario(
            scenario_name="vol_shock_high",
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        assert result is not None
        assert result.scenario_name == "vol_shock_high"
        assert result.estimated_var_post_shock > 0.10  # VaR should increase
    
    # ═══════════════════════════════════════════════════════════
    # TEST 4: Correlation spike simulated
    # ═══════════════════════════════════════════════════════════
    
    def test_corr_spike_simulation(self, aggregator):
        """Correlation spike scenario should simulate correctly."""
        result = aggregator.run_scenario(
            scenario_name="corr_spike_high",
            net_exposure=0.5,
            gross_exposure=0.8,
            current_correlation=0.40,
        )
        
        assert result is not None
        assert result.scenario_name == "corr_spike_high"
        assert result.estimated_drawdown > 0
    
    # ═══════════════════════════════════════════════════════════
    # TEST 5: Liquidity freeze simulated
    # ═══════════════════════════════════════════════════════════
    
    def test_liq_freeze_simulation(self, aggregator):
        """Liquidity freeze scenario should simulate correctly."""
        result = aggregator.run_scenario(
            scenario_name="liq_freeze_high",
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        assert result is not None
        assert result.scenario_name == "liq_freeze_high"
        assert result.estimated_pnl_impact < 0
    
    # ═══════════════════════════════════════════════════════════
    # TEST 6: Regime flip simulated
    # ═══════════════════════════════════════════════════════════
    
    def test_regime_flip_simulation(self, aggregator):
        """Regime flip scenario should simulate correctly."""
        result = aggregator.run_scenario(
            scenario_name="regime_flip_bull_to_bear",
            net_exposure=0.6,
            gross_exposure=0.9,
        )
        
        assert result is not None
        assert result.scenario_name == "regime_flip_bull_to_bear"
        assert result.severity == SeverityLevel.HIGH
    
    # ═══════════════════════════════════════════════════════════
    # TEST 7: Drawdown classification correct
    # ═══════════════════════════════════════════════════════════
    
    def test_drawdown_classification(self, impact_engine):
        """Drawdown should be correctly classified to survival states."""
        # Test STABLE (< 5%)
        state_stable = impact_engine._get_survival_state(0.03)
        assert state_stable == SurvivalState.STABLE
        
        # Test STRESSED (5-10%)
        state_stressed = impact_engine._get_survival_state(0.07)
        assert state_stressed == SurvivalState.STRESSED
        
        # Test FRAGILE (10-18%)
        state_fragile = impact_engine._get_survival_state(0.14)
        assert state_fragile == SurvivalState.FRAGILE
        
        # Test BROKEN (> 18%)
        state_broken = impact_engine._get_survival_state(0.22)
        assert state_broken == SurvivalState.BROKEN
    
    # ═══════════════════════════════════════════════════════════
    # TEST 8: Survival state correct
    # ═══════════════════════════════════════════════════════════
    
    def test_survival_state_correct(self, aggregator):
        """Survival state should match drawdown severity."""
        # Low exposure should be more stable
        result_low = aggregator.run_scenario(
            scenario_name="flash_crash_low",
            net_exposure=0.2,
            gross_exposure=0.3,
            portfolio_beta=0.8,
        )
        
        # High exposure should be more fragile
        result_high = aggregator.run_scenario(
            scenario_name="flash_crash_extreme",
            net_exposure=0.8,
            gross_exposure=1.2,
            portfolio_beta=1.5,
        )
        
        # Lower exposure should have better survival state
        survival_order = [SurvivalState.STABLE, SurvivalState.STRESSED, SurvivalState.FRAGILE, SurvivalState.BROKEN]
        assert survival_order.index(result_low.survival_state) <= survival_order.index(result_high.survival_state)
    
    # ═══════════════════════════════════════════════════════════
    # TEST 9: Recommended action correct
    # ═══════════════════════════════════════════════════════════
    
    def test_recommended_actions(self, impact_engine):
        """Recommended actions should match survival states."""
        # STABLE -> HOLD
        action_stable = impact_engine._get_recommended_action(SurvivalState.STABLE)
        assert action_stable == SurvivalAction.HOLD
        
        # STRESSED -> HEDGE
        action_stressed = impact_engine._get_recommended_action(SurvivalState.STRESSED)
        assert action_stressed == SurvivalAction.HEDGE
        
        # FRAGILE -> DELEVER
        action_fragile = impact_engine._get_recommended_action(SurvivalState.FRAGILE)
        assert action_fragile == SurvivalAction.DELEVER
        
        # BROKEN -> KILL_SWITCH
        action_broken = impact_engine._get_recommended_action(SurvivalState.BROKEN)
        assert action_broken == SurvivalAction.KILL_SWITCH
    
    # ═══════════════════════════════════════════════════════════
    # TEST 10: API output correct
    # ═══════════════════════════════════════════════════════════
    
    def test_api_output_format(self, aggregator):
        """API output should have correct format."""
        result = aggregator.run_scenario(
            scenario_name="flash_crash_high",
            net_exposure=0.5,
            gross_exposure=0.8,
        )
        
        assert result is not None
        output = result.to_dict()
        
        # Check required fields
        assert "scenario_name" in output
        assert "severity" in output
        assert "estimated_pnl_impact" in output
        assert "estimated_drawdown" in output
        assert "estimated_var_post_shock" in output
        assert "estimated_tail_risk_post_shock" in output
        assert "survival_state" in output
        assert "recommended_action" in output
        assert "confidence_modifier" in output
        assert "capital_modifier" in output
        assert "reason" in output
        assert "timestamp" in output
        
        # Check types
        assert isinstance(output["estimated_pnl_impact"], float)
        assert isinstance(output["estimated_drawdown"], float)
        assert isinstance(output["survival_state"], str)
        assert isinstance(output["recommended_action"], str)
        
        # Check ranges
        assert 0 <= output["estimated_drawdown"] <= 1
        assert 0 <= output["confidence_modifier"] <= 1
        assert 0 <= output["capital_modifier"] <= 1
        
        # Check full dict has inputs
        full_output = result.to_full_dict()
        assert "inputs" in full_output


def run_all_tests():
    """Run all tests and return results."""
    test_class = TestSimulationEngine()
    aggregator = SimulationAggregator()
    shock_simulator = ShockSimulator()
    impact_engine = PortfolioImpactEngine()
    
    results = []
    
    tests = [
        ("test_1_scenario_registry_loads", lambda: test_class.test_scenario_registry_loads()),
        ("test_2_flash_crash_simulation", lambda: test_class.test_flash_crash_simulation(aggregator)),
        ("test_3_vol_shock_simulation", lambda: test_class.test_vol_shock_simulation(aggregator)),
        ("test_4_corr_spike_simulation", lambda: test_class.test_corr_spike_simulation(aggregator)),
        ("test_5_liq_freeze_simulation", lambda: test_class.test_liq_freeze_simulation(aggregator)),
        ("test_6_regime_flip_simulation", lambda: test_class.test_regime_flip_simulation(aggregator)),
        ("test_7_drawdown_classification", lambda: test_class.test_drawdown_classification(impact_engine)),
        ("test_8_survival_state_correct", lambda: test_class.test_survival_state_correct(aggregator)),
        ("test_9_recommended_actions", lambda: test_class.test_recommended_actions(impact_engine)),
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
    print(f"SIMULATION ENGINE TESTS")
    print(f"{'='*60}")
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Failed: {results['failed']}")
    print(f"\nResults:")
    for r in results["results"]:
        status = "✅" if r["status"] == "PASSED" else "❌"
        print(f"  {status} {r['test']}")
        if r["status"] != "PASSED" and "error" in r:
            print(f"     Error: {r['error']}")
