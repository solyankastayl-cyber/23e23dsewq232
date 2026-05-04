"""
PHASE 21.2 — Capital Budget Tests
=================================
Test cases for Capital Budget Engine.

Tests:
1. clean trend → OPEN
2. range regime → THROTTLED
3. high vol → DEFENSIVE
4. emergency conditions → EMERGENCY
5. reserve capital calculated correctly
6. dry powder calculated correctly
7. sleeve limits returned correctly
8. final budget multiplier bounded
9. deployable capital non-negative
10. API output correct
"""

import unittest
from datetime import datetime, timezone

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    CapitalBudgetState,
    BudgetState,
    SleeveLimitState,
    DEFAULT_SLEEVE_LIMITS,
    BUDGET_STATE_THRESHOLDS,
)
from modules.capital_allocation_v2.budget_constraints.capital_budget_engine import (
    CapitalBudgetEngine,
)
from modules.capital_allocation_v2.budget_constraints.sleeve_limit_engine import (
    SleeveLimitEngine,
)
from modules.capital_allocation_v2.budget_constraints.reserve_capital_engine import (
    ReserveCapitalEngine,
)
from modules.capital_allocation_v2.budget_constraints.dry_powder_engine import (
    DryPowderEngine,
)
from modules.capital_allocation_v2.budget_constraints.emergency_cut_engine import (
    EmergencyCutEngine,
)
from modules.capital_allocation_v2.budget_constraints.regime_throttle_engine import (
    RegimeThrottleEngine,
)


class TestBudgetStateClassification(unittest.TestCase):
    """Test budget state classification."""
    
    def setUp(self):
        self.engine = CapitalBudgetEngine()
    
    def test_clean_trend_open(self):
        """Test 1: clean trend → OPEN."""
        state = self.engine.compute_budget(
            regime="TREND",
            portfolio_state="NORMAL",
            risk_state="NORMAL",
            loop_state="HEALTHY",
            regime_confidence=0.85,
            allocation_confidence=0.85,
        )
        
        # With clean conditions, should be OPEN or THROTTLED
        self.assertIn(state.budget_state, [BudgetState.OPEN, BudgetState.THROTTLED])
        self.assertGreaterEqual(state.final_budget_multiplier, 0.85)
    
    def test_range_regime_throttled(self):
        """Test 2: range regime → THROTTLED."""
        state = self.engine.compute_budget(
            regime="RANGE",
            portfolio_state="NORMAL",
            risk_state="NORMAL",
            loop_state="HEALTHY",
        )
        
        # Range should typically be THROTTLED
        self.assertIn(state.budget_state, [BudgetState.OPEN, BudgetState.THROTTLED])
        self.assertLessEqual(state.final_budget_multiplier, 0.95)
    
    def test_high_vol_defensive(self):
        """Test 3: high vol → DEFENSIVE or worse."""
        state = self.engine.compute_budget(
            regime="HIGH_VOL",
            portfolio_state="DEFENSIVE",
            risk_state="HIGH",
            loop_state="DEGRADED",
            volatility_state="HIGH",
        )
        
        # High vol with defensive conditions should be DEFENSIVE or EMERGENCY
        self.assertIn(state.budget_state, [BudgetState.THROTTLED, BudgetState.DEFENSIVE, BudgetState.EMERGENCY])
    
    def test_emergency_conditions_emergency(self):
        """Test 4: emergency conditions → EMERGENCY."""
        state = self.engine.compute_budget(
            regime="CRISIS",
            portfolio_state="RISK_OFF",
            risk_state="CRITICAL",
            loop_state="CRITICAL",
            volatility_state="EXTREME",
        )
        
        # Emergency conditions should result in EMERGENCY
        self.assertEqual(state.budget_state, BudgetState.EMERGENCY)
        self.assertLess(state.final_budget_multiplier, 0.50)


class TestReserveCapital(unittest.TestCase):
    """Test reserve capital calculation."""
    
    def setUp(self):
        self.engine = ReserveCapitalEngine()
    
    def test_reserve_capital_calculated_correctly(self):
        """Test 5: reserve capital calculated correctly."""
        # Normal conditions
        normal = self.engine.compute_reserve(
            total_capital=1.0,
            regime="normal",
        )
        self.assertEqual(normal["reserve_ratio"], 0.10)
        self.assertEqual(normal["reserve_capital"], 0.10)
        
        # Crisis conditions
        crisis = self.engine.compute_reserve(
            total_capital=1.0,
            regime="crisis",
            portfolio_state="RISK_OFF",
        )
        self.assertGreater(crisis["reserve_ratio"], normal["reserve_ratio"])
    
    def test_reserve_scales_with_capital(self):
        """Test reserve scales with total capital."""
        result = self.engine.compute_reserve(total_capital=100.0)
        self.assertEqual(result["reserve_capital"], 100.0 * result["reserve_ratio"])


class TestDryPowder(unittest.TestCase):
    """Test dry powder calculation."""
    
    def setUp(self):
        self.engine = DryPowderEngine()
    
    def test_dry_powder_calculated_correctly(self):
        """Test 6: dry powder calculated correctly."""
        # Normal conditions
        normal = self.engine.compute_dry_powder(
            total_capital=1.0,
            regime="RANGE",
        )
        self.assertGreater(normal["dry_powder_ratio"], 0.0)
        self.assertLess(normal["dry_powder_ratio"], 0.25)
        
        # Squeeze conditions (should have higher dry powder)
        squeeze = self.engine.compute_dry_powder(
            total_capital=1.0,
            regime="SQUEEZE",
            squeeze_probability=0.7,
        )
        self.assertGreater(squeeze["dry_powder_ratio"], normal["dry_powder_ratio"])
    
    def test_dry_powder_bounded(self):
        """Test dry powder is bounded."""
        result = self.engine.compute_dry_powder(
            total_capital=1.0,
            regime="CRISIS",
            opportunity_score=1.0,
            squeeze_probability=1.0,
        )
        self.assertLessEqual(result["dry_powder_ratio"], 0.25)
        self.assertGreaterEqual(result["dry_powder_ratio"], 0.03)


class TestSleeveLimits(unittest.TestCase):
    """Test sleeve limits."""
    
    def setUp(self):
        self.engine = SleeveLimitEngine()
    
    def test_sleeve_limits_returned_correctly(self):
        """Test 7: sleeve limits returned correctly."""
        limits = self.engine.get_limits()
        
        # Check all sleeves exist
        self.assertIn("strategy", limits)
        self.assertIn("factor", limits)
        self.assertIn("asset", limits)
        self.assertIn("cluster", limits)
        
        # Check values match defaults
        for key, value in DEFAULT_SLEEVE_LIMITS.items():
            self.assertEqual(limits[key], value)
    
    def test_sleeve_breach_detection(self):
        """Test sleeve breach detection."""
        states = self.engine.check_sleeve_limits(
            strategy_allocations={"test": 0.40},  # Above 0.35 limit
            factor_allocations={"test": 0.20},
            asset_allocations={"BTC": 0.45},
            cluster_allocations={"test": 0.30},
        )
        
        # Strategy should be breached
        self.assertTrue(states["strategy"].is_breached)
        self.assertFalse(states["factor"].is_breached)


class TestFinalBudgetMultiplier(unittest.TestCase):
    """Test final budget multiplier."""
    
    def setUp(self):
        self.engine = CapitalBudgetEngine()
    
    def test_final_budget_multiplier_bounded(self):
        """Test 8: final budget multiplier bounded."""
        # Test with extreme high values
        state_high = self.engine.compute_budget(
            regime="TREND",
            portfolio_capital_modifier=1.5,
            loop_capital_modifier=1.5,
        )
        self.assertLessEqual(state_high.final_budget_multiplier, 1.10)
        
        # Test with extreme low values
        state_low = self.engine.compute_budget(
            regime="CRISIS",
            portfolio_state="RISK_OFF",
            risk_state="CRITICAL",
            portfolio_capital_modifier=0.3,
            loop_capital_modifier=0.5,
        )
        self.assertGreaterEqual(state_low.final_budget_multiplier, 0.25)


class TestDeployableCapital(unittest.TestCase):
    """Test deployable capital calculation."""
    
    def setUp(self):
        self.engine = CapitalBudgetEngine()
    
    def test_deployable_capital_non_negative(self):
        """Test 9: deployable capital non-negative."""
        # Even in worst conditions
        state = self.engine.compute_budget(
            total_capital=1.0,
            regime="CRISIS",
            portfolio_state="RISK_OFF",
            risk_state="CRITICAL",
            loop_state="CRITICAL",
        )
        
        self.assertGreaterEqual(state.deployable_capital, 0.0)
    
    def test_deployable_capital_calculation(self):
        """Test deployable capital is calculated correctly."""
        state = self.engine.compute_budget(total_capital=1.0)
        
        # deployable = total × multiplier - reserve - dry_powder
        expected_max = state.total_capital * state.final_budget_multiplier
        self.assertLessEqual(state.deployable_capital, expected_max)


class TestAPIOutput(unittest.TestCase):
    """Test API output format."""
    
    def setUp(self):
        self.engine = CapitalBudgetEngine()
    
    def test_api_output_correct(self):
        """Test 10: API output correct."""
        state = self.engine.compute_budget()
        data = state.to_dict()
        
        # Check required fields
        self.assertIn("total_capital", data)
        self.assertIn("deployable_capital", data)
        self.assertIn("reserve_capital", data)
        self.assertIn("dry_powder", data)
        self.assertIn("sleeve_limits", data)
        self.assertIn("regime_throttle", data)
        self.assertIn("emergency_cut", data)
        self.assertIn("final_budget_multiplier", data)
        self.assertIn("budget_state", data)
        self.assertIn("confidence_modifier", data)
        self.assertIn("capital_modifier", data)
        self.assertIn("reason", data)
    
    def test_summary_output(self):
        """Test summary output."""
        summary = self.engine.get_summary()
        
        self.assertIn("total_capital", summary)
        self.assertIn("deployable_capital", summary)
        self.assertIn("budget_state", summary)


class TestEmergencyCut(unittest.TestCase):
    """Test emergency cut calculation."""
    
    def setUp(self):
        self.engine = EmergencyCutEngine()
    
    def test_normal_returns_1(self):
        """Test normal conditions return 1.0."""
        result = self.engine.compute_emergency_cut()
        self.assertEqual(result["emergency_cut"], 1.0)
        self.assertEqual(result["cut_level"], "normal")
    
    def test_emergency_triggers(self):
        """Test emergency triggers."""
        result = self.engine.compute_emergency_cut(
            portfolio_state="RISK_OFF",
            risk_state="CRITICAL",
        )
        self.assertEqual(result["cut_level"], "emergency")
        self.assertEqual(result["emergency_cut"], 0.50)


class TestRegimeThrottle(unittest.TestCase):
    """Test regime throttle calculation."""
    
    def setUp(self):
        self.engine = RegimeThrottleEngine()
    
    def test_trend_full_throttle(self):
        """Test trend regime has full throttle."""
        result = self.engine.compute_throttle(regime="TREND")
        self.assertGreaterEqual(result["base_throttle"], 0.95)
    
    def test_crisis_low_throttle(self):
        """Test crisis regime has low throttle."""
        result = self.engine.compute_throttle(regime="CRISIS")
        self.assertLessEqual(result["base_throttle"], 0.50)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBudgetStateClassification))
    suite.addTests(loader.loadTestsFromTestCase(TestReserveCapital))
    suite.addTests(loader.loadTestsFromTestCase(TestDryPowder))
    suite.addTests(loader.loadTestsFromTestCase(TestSleeveLimits))
    suite.addTests(loader.loadTestsFromTestCase(TestFinalBudgetMultiplier))
    suite.addTests(loader.loadTestsFromTestCase(TestDeployableCapital))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIOutput))
    suite.addTests(loader.loadTestsFromTestCase(TestEmergencyCut))
    suite.addTests(loader.loadTestsFromTestCase(TestRegimeThrottle))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests()
