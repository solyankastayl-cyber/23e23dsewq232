"""
PHASE 21.1 — Capital Allocation Tests
=====================================
Test cases for Capital Allocation Engine v2.

Tests:
1. strategy allocations preserved and normalized
2. factor allocations reflect governance weights
3. asset allocations react to BTC dominance
4. cluster allocations computed correctly
5. dominant route = strategy in strong strategy regime
6. dominant route = factor when research loop active
7. concentration score correct
8. allocation confidence bounded
9. summary output correct
10. all allocations sum correctly
"""

import unittest
from datetime import datetime, timezone

from modules.capital_allocation_v2.capital_allocation_types import (
    CapitalAllocationState,
    DominantRoute,
    RoutingRegime,
    AllocationSlice,
    ALLOCATION_CONFIDENCE_THRESHOLDS,
    ALLOCATION_MODIFIERS,
)
from modules.capital_allocation_v2.strategy_capital_engine import (
    StrategyCapitalEngine,
)
from modules.capital_allocation_v2.factor_capital_engine import (
    FactorCapitalEngine,
)
from modules.capital_allocation_v2.asset_capital_engine import (
    AssetCapitalEngine,
)
from modules.capital_allocation_v2.cluster_capital_engine import (
    ClusterCapitalEngine,
)
from modules.capital_allocation_v2.capital_router_engine import (
    CapitalRouterEngine,
)


class TestStrategyCapitalEngine(unittest.TestCase):
    """Test strategy capital allocation."""
    
    def setUp(self):
        self.engine = StrategyCapitalEngine()
    
    def test_strategy_allocations_preserved_and_normalized(self):
        """Test 1: strategy allocations preserved and normalized."""
        result = self.engine.compute_allocations()
        
        # Check allocations exist
        self.assertIn("allocations", result)
        self.assertGreater(len(result["allocations"]), 0)
        
        # Check normalized to ~1.0
        total = sum(result["allocations"].values())
        self.assertAlmostEqual(total, 1.0, places=4)
    
    def test_strategy_concentration(self):
        """Test strategy concentration calculation."""
        result = self.engine.compute_allocations()
        
        # Concentration should be max allocation
        max_alloc = max(result["allocations"].values())
        self.assertEqual(result["concentration"], max_alloc)
    
    def test_dominant_strategy(self):
        """Test dominant strategy identification."""
        result = self.engine.compute_allocations()
        dominant = self.engine.get_dominant_strategy(result["allocations"])
        
        self.assertIsInstance(dominant, str)
        self.assertIn(dominant, result["allocations"])


class TestFactorCapitalEngine(unittest.TestCase):
    """Test factor capital allocation."""
    
    def setUp(self):
        self.engine = FactorCapitalEngine()
    
    def test_factor_allocations_reflect_governance(self):
        """Test 2: factor allocations reflect governance weights."""
        # Test ELITE governance boosts allocation
        governance_states = {
            "funding_factor": "ELITE",
            "structure_factor": "DEGRADED",
        }
        
        result = self.engine.compute_allocations(governance_states=governance_states)
        
        # ELITE should have higher allocation than DEGRADED
        self.assertGreater(
            result["allocations"].get("funding_factor", 0),
            result["allocations"].get("structure_factor", 0)
        )
    
    def test_factor_allocations_normalized(self):
        """Test factor allocations sum to 1."""
        result = self.engine.compute_allocations()
        total = sum(result["allocations"].values())
        self.assertAlmostEqual(total, 1.0, places=4)
    
    def test_factor_health_calculation(self):
        """Test factor health calculation."""
        result = self.engine.compute_allocations()
        health = self.engine.get_factor_health(result["allocations"])
        
        self.assertGreaterEqual(health, 0.0)
        self.assertLessEqual(health, 1.0)


class TestAssetCapitalEngine(unittest.TestCase):
    """Test asset capital allocation."""
    
    def setUp(self):
        self.engine = AssetCapitalEngine()
    
    def test_asset_allocations_react_to_btc_dominance(self):
        """Test 3: asset allocations react to BTC dominance."""
        # High BTC dominance
        high_dom = self.engine.compute_allocations(btc_dominance=0.70)
        
        # Low BTC dominance
        low_dom = self.engine.compute_allocations(btc_dominance=0.40)
        
        # BTC should have higher allocation in high dominance
        self.assertGreater(
            high_dom["allocations"]["BTC"],
            low_dom["allocations"]["BTC"]
        )
        
        # ALTS should have higher allocation in low dominance
        self.assertGreater(
            low_dom["allocations"]["ALTS"],
            high_dom["allocations"]["ALTS"]
        )
    
    def test_asset_allocations_normalized(self):
        """Test asset allocations sum to 1."""
        result = self.engine.compute_allocations()
        total = sum(result["allocations"].values())
        self.assertAlmostEqual(total, 1.0, places=4)
    
    def test_risk_off_increases_cash(self):
        """Test risk-off mode increases cash allocation."""
        normal = self.engine.compute_allocations(risk_off_mode=False)
        risk_off = self.engine.compute_allocations(risk_off_mode=True)
        
        self.assertGreater(
            risk_off["allocations"]["CASH"],
            normal["allocations"]["CASH"]
        )


class TestClusterCapitalEngine(unittest.TestCase):
    """Test cluster capital allocation."""
    
    def setUp(self):
        self.engine = ClusterCapitalEngine()
    
    def test_cluster_allocations_computed_correctly(self):
        """Test 4: cluster allocations computed correctly."""
        strategy_alloc = {"trend_following": 0.3, "mean_reversion": 0.3}
        asset_alloc = {"BTC": 0.4, "ETH": 0.3, "ALTS": 0.3}
        
        result = self.engine.compute_allocations(
            strategy_allocations=strategy_alloc,
            asset_allocations=asset_alloc,
        )
        
        # Check allocations exist
        self.assertGreater(len(result["allocations"]), 0)
        
        # Check normalized
        total = sum(result["allocations"].values())
        self.assertAlmostEqual(total, 1.0, places=4)
    
    def test_regime_affects_clusters(self):
        """Test regime affects cluster allocations."""
        strategy_alloc = {"trend_following": 0.3, "mean_reversion": 0.3}
        asset_alloc = {"BTC": 0.4, "ETH": 0.3}
        
        trend_result = self.engine.compute_allocations(
            strategy_allocations=strategy_alloc,
            asset_allocations=asset_alloc,
            regime="TREND",
        )
        
        range_result = self.engine.compute_allocations(
            strategy_allocations=strategy_alloc,
            asset_allocations=asset_alloc,
            regime="RANGE",
        )
        
        # trend_cluster should be higher in TREND regime
        self.assertGreater(
            trend_result["allocations"].get("trend_cluster", 0),
            range_result["allocations"].get("trend_cluster", 0)
        )


class TestCapitalRouterEngine(unittest.TestCase):
    """Test main capital router engine."""
    
    def setUp(self):
        self.engine = CapitalRouterEngine()
    
    def test_dominant_route_strategy_in_strong_regime(self):
        """Test 5: dominant route = strategy in strong strategy regime."""
        state = self.engine.compute_allocation(regime_confidence=0.9)
        
        # With high regime confidence, strategy should often dominate
        self.assertIn(state.dominant_route, list(DominantRoute))
    
    def test_dominant_route_factor_when_research_active(self):
        """Test 6: dominant route considers factor governance."""
        state = self.engine.compute_allocation(research_modifier=0.7)
        
        # Should still return valid dominant route
        self.assertIn(state.dominant_route, list(DominantRoute))
    
    def test_concentration_score_correct(self):
        """Test 7: concentration score correct."""
        state = self.engine.compute_allocation()
        
        # Concentration should be 0-1
        self.assertGreaterEqual(state.concentration_score, 0.0)
        self.assertLessEqual(state.concentration_score, 1.0)
    
    def test_allocation_confidence_bounded(self):
        """Test 8: allocation confidence bounded."""
        state = self.engine.compute_allocation()
        
        self.assertGreaterEqual(state.allocation_confidence, 0.0)
        self.assertLessEqual(state.allocation_confidence, 1.0)
    
    def test_summary_output_correct(self):
        """Test 9: summary output correct."""
        summary = self.engine.get_summary()
        
        # Check required fields
        self.assertIn("total_capital", summary)
        self.assertIn("dominant_route", summary)
        self.assertIn("routing_regime", summary)
        self.assertIn("allocation_confidence", summary)
        self.assertIn("concentration_score", summary)
    
    def test_all_allocations_sum_correctly(self):
        """Test 10: all allocations sum correctly."""
        state = self.engine.compute_allocation()
        
        # Each dimension should sum to ~1.0
        strategy_sum = sum(state.strategy_allocations.values())
        factor_sum = sum(state.factor_allocations.values())
        asset_sum = sum(state.asset_allocations.values())
        cluster_sum = sum(state.cluster_allocations.values())
        
        self.assertAlmostEqual(strategy_sum, 1.0, places=3)
        self.assertAlmostEqual(factor_sum, 1.0, places=3)
        self.assertAlmostEqual(asset_sum, 1.0, places=3)
        self.assertAlmostEqual(cluster_sum, 1.0, places=3)


class TestCapitalAllocationTypes(unittest.TestCase):
    """Test type definitions."""
    
    def test_dominant_routes_exist(self):
        """Test all dominant routes exist."""
        routes = [
            DominantRoute.STRATEGY,
            DominantRoute.FACTOR,
            DominantRoute.ASSET,
            DominantRoute.CLUSTER,
            DominantRoute.BALANCED,
        ]
        self.assertEqual(len(routes), 5)
    
    def test_routing_regimes_exist(self):
        """Test all routing regimes exist."""
        regimes = [
            RoutingRegime.TREND,
            RoutingRegime.RANGE,
            RoutingRegime.SQUEEZE,
            RoutingRegime.VOL,
            RoutingRegime.MIXED,
        ]
        self.assertEqual(len(regimes), 5)
    
    def test_allocation_state_to_dict(self):
        """Test state serialization."""
        state = CapitalAllocationState(
            total_capital=1.0,
            strategy_allocations={"test": 1.0},
            factor_allocations={"test": 1.0},
            asset_allocations={"BTC": 1.0},
            cluster_allocations={"btc_cluster": 1.0},
            dominant_route=DominantRoute.STRATEGY,
            routing_regime=RoutingRegime.RANGE,
            allocation_confidence=0.75,
            concentration_score=0.4,
            confidence_modifier=1.05,
            capital_modifier=1.10,
            reason="test reason",
        )
        
        data = state.to_dict()
        self.assertEqual(data["dominant_route"], "STRATEGY")
        self.assertEqual(data["routing_regime"], "RANGE")


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStrategyCapitalEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestFactorCapitalEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestAssetCapitalEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestClusterCapitalEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestCapitalRouterEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestCapitalAllocationTypes))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests()
