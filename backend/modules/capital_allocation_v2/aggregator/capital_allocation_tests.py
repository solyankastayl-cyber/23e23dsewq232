"""
PHASE 21.3 — Capital Allocation Layer Tests
==========================================
Test cases for Capital Allocation Aggregator.

Tests:
1. core allocator integrated correctly
2. budget engine integrated correctly
3. deployable capital respected
4. capital efficiency calculated correctly
5. allocation state optimal
6. allocation state balanced
7. allocation state constrained
8. allocation state stressed
9. modifiers bounded
10. summary output correct
"""

import unittest
from datetime import datetime, timezone

from modules.capital_allocation_v2.aggregator.capital_allocation_layer_types import (
    CapitalAllocationLayerState,
    AllocationState,
    ALLOCATION_STATE_THRESHOLDS,
)
from modules.capital_allocation_v2.aggregator.capital_allocation_aggregator import (
    CapitalAllocationAggregator,
)
from modules.capital_allocation_v2.aggregator.capital_allocation_registry import (
    CapitalAllocationRegistry,
)


class TestCoreAllocatorIntegration(unittest.TestCase):
    """Test core allocator integration."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_core_allocator_integrated_correctly(self):
        """Test 1: core allocator integrated correctly."""
        state = self.aggregator.compute_layer_state()
        
        # Should have all allocation dimensions
        self.assertGreater(len(state.strategy_allocations), 0)
        self.assertGreater(len(state.factor_allocations), 0)
        self.assertGreater(len(state.asset_allocations), 0)
        self.assertGreater(len(state.cluster_allocations), 0)
        
        # Should have routing info
        self.assertIsNotNone(state.dominant_route)
        self.assertIsNotNone(state.routing_regime)
        
        # Allocations should sum to ~1.0
        strategy_sum = sum(state.strategy_allocations.values())
        self.assertAlmostEqual(strategy_sum, 1.0, places=2)


class TestBudgetEngineIntegration(unittest.TestCase):
    """Test budget engine integration."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_budget_engine_integrated_correctly(self):
        """Test 2: budget engine integrated correctly."""
        state = self.aggregator.compute_layer_state()
        
        # Should have budget info
        self.assertIsNotNone(state.budget_state)
        self.assertGreater(state.budget_multiplier, 0)
        
        # Should have reserve and dry powder
        self.assertGreaterEqual(state.reserve_capital, 0)
        self.assertGreaterEqual(state.dry_powder, 0)


class TestDeployableCapital(unittest.TestCase):
    """Test deployable capital."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_deployable_capital_respected(self):
        """Test 3: deployable capital respected."""
        state = self.aggregator.compute_layer_state(total_capital=1.0)
        
        # Deployable should be <= total
        self.assertLessEqual(state.deployable_capital, state.total_capital)
        
        # Deployable should be non-negative
        self.assertGreaterEqual(state.deployable_capital, 0)


class TestCapitalEfficiency(unittest.TestCase):
    """Test capital efficiency calculation."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_capital_efficiency_calculated_correctly(self):
        """Test 4: capital efficiency calculated correctly."""
        state = self.aggregator.compute_layer_state()
        
        # Efficiency should be in [0, 1]
        self.assertGreaterEqual(state.capital_efficiency, 0.0)
        self.assertLessEqual(state.capital_efficiency, 1.0)
        
        # Verify formula: deployable × confidence × (1 - concentration)
        expected = (
            state.deployable_capital *
            state.allocation_confidence *
            (1.0 - state.concentration_score)
        )
        self.assertAlmostEqual(state.capital_efficiency, expected, places=3)


class TestAllocationStateOptimal(unittest.TestCase):
    """Test optimal allocation state."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_allocation_state_optimal(self):
        """Test 5: allocation state optimal under good conditions."""
        # Use conditions that should result in OPTIMAL
        state = self.aggregator.compute_layer_state(
            market_regime="TREND",
            regime_confidence=0.9,
            portfolio_state="NORMAL",
            risk_state="NORMAL",
            loop_state="HEALTHY",
        )
        
        # With clean trend and good conditions, should be OPTIMAL or BALANCED
        self.assertIn(state.allocation_state, [AllocationState.OPTIMAL, AllocationState.BALANCED])


class TestAllocationStateBalanced(unittest.TestCase):
    """Test balanced allocation state."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_allocation_state_balanced(self):
        """Test 6: allocation state balanced under normal conditions."""
        state = self.aggregator.compute_layer_state(
            market_regime="RANGE",
            regime_confidence=0.7,
            portfolio_state="NORMAL",
        )
        
        # Range regime with normal conditions should be BALANCED or CONSTRAINED
        self.assertIn(state.allocation_state, [AllocationState.BALANCED, AllocationState.CONSTRAINED])


class TestAllocationStateConstrained(unittest.TestCase):
    """Test constrained allocation state."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_allocation_state_constrained(self):
        """Test 7: allocation state constrained under defensive conditions."""
        state = self.aggregator.compute_layer_state(
            market_regime="HIGH_VOL",
            portfolio_state="DEFENSIVE",
            risk_state="HIGH",
        )
        
        # Should be at least CONSTRAINED
        self.assertIn(state.allocation_state, [
            AllocationState.CONSTRAINED, 
            AllocationState.STRESSED
        ])


class TestAllocationStateStressed(unittest.TestCase):
    """Test stressed allocation state."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_allocation_state_stressed(self):
        """Test 8: allocation state stressed under emergency conditions."""
        state = self.aggregator.compute_layer_state(
            market_regime="CRISIS",
            portfolio_state="RISK_OFF",
            risk_state="CRITICAL",
            loop_state="CRITICAL",
        )
        
        # Emergency conditions should result in STRESSED
        self.assertEqual(state.allocation_state, AllocationState.STRESSED)


class TestModifiersBounded(unittest.TestCase):
    """Test modifiers are bounded."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_modifiers_bounded(self):
        """Test 9: modifiers bounded."""
        # Test with extreme good conditions
        state_good = self.aggregator.compute_layer_state(
            market_regime="TREND",
            regime_confidence=0.95,
            portfolio_state="NORMAL",
        )
        
        # Test with extreme bad conditions
        state_bad = self.aggregator.compute_layer_state(
            market_regime="CRISIS",
            portfolio_state="RISK_OFF",
            risk_state="CRITICAL",
        )
        
        # Confidence modifier should be in [0.75, 1.20]
        self.assertGreaterEqual(state_good.confidence_modifier, 0.75)
        self.assertLessEqual(state_good.confidence_modifier, 1.20)
        self.assertGreaterEqual(state_bad.confidence_modifier, 0.75)
        self.assertLessEqual(state_bad.confidence_modifier, 1.20)
        
        # Capital modifier should be in [0.70, 1.15]
        self.assertGreaterEqual(state_good.capital_modifier, 0.70)
        self.assertLessEqual(state_good.capital_modifier, 1.15)
        self.assertGreaterEqual(state_bad.capital_modifier, 0.70)
        self.assertLessEqual(state_bad.capital_modifier, 1.15)


class TestSummaryOutput(unittest.TestCase):
    """Test summary output."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_summary_output_correct(self):
        """Test 10: summary output correct."""
        summary = self.aggregator.get_summary()
        
        # Check required fields
        self.assertIn("total_capital", summary)
        self.assertIn("deployable_capital", summary)
        self.assertIn("dominant_route", summary)
        self.assertIn("budget_state", summary)
        self.assertIn("allocation_state", summary)
        self.assertIn("capital_efficiency", summary)
        self.assertIn("confidence_modifier", summary)
        self.assertIn("capital_modifier", summary)


class TestRegistry(unittest.TestCase):
    """Test registry functionality."""
    
    def setUp(self):
        self.registry = CapitalAllocationRegistry()
    
    def test_registry_records_state(self):
        """Test registry records state correctly."""
        aggregator = CapitalAllocationAggregator()
        state = aggregator.compute_layer_state()
        
        # Create fresh registry for test
        registry = CapitalAllocationRegistry()
        registry.record_state(state)
        
        # Check recorded
        current = registry.get_current_state()
        self.assertIsNotNone(current)
        self.assertEqual(current.allocation_state, state.allocation_state)
        
        # Check stats
        stats = registry.get_stats()
        self.assertEqual(stats["total_recomputes"], 1)


class TestFullDict(unittest.TestCase):
    """Test full dict output."""
    
    def setUp(self):
        self.aggregator = CapitalAllocationAggregator()
    
    def test_full_dict_has_details(self):
        """Test full dict includes details."""
        state = self.aggregator.compute_layer_state()
        full = state.to_full_dict()
        
        # Should have details section
        self.assertIn("details", full)
        self.assertIn("allocator", full["details"])
        self.assertIn("budget", full["details"])


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCoreAllocatorIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBudgetEngineIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDeployableCapital))
    suite.addTests(loader.loadTestsFromTestCase(TestCapitalEfficiency))
    suite.addTests(loader.loadTestsFromTestCase(TestAllocationStateOptimal))
    suite.addTests(loader.loadTestsFromTestCase(TestAllocationStateBalanced))
    suite.addTests(loader.loadTestsFromTestCase(TestAllocationStateConstrained))
    suite.addTests(loader.loadTestsFromTestCase(TestAllocationStateStressed))
    suite.addTests(loader.loadTestsFromTestCase(TestModifiersBounded))
    suite.addTests(loader.loadTestsFromTestCase(TestSummaryOutput))
    suite.addTests(loader.loadTestsFromTestCase(TestRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestFullDict))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests()
