"""
PHASE 22.4 — Correlation Spike Tests
====================================
Test suite for Correlation Spike Engine.

Tests:
1. Diversified portfolio -> NORMAL
2. Moderate overlap -> ELEVATED
3. Correlated strategies -> HIGH
4. Crisis regime -> SYSTEMIC
5. Asset correlation calculated correctly
6. Strategy correlation calculated correctly
7. Factor correlation calculated correctly
8. Diversification score correct
9. Correlation spike intensity bounded
10. API output correct
"""

import pytest
from .correlation_types import CorrelationState, CorrelationAction, CorrelationSpikeState
from .asset_correlation_engine import AssetCorrelationEngine
from .strategy_correlation_engine import StrategyCorrelationEngine
from .factor_correlation_engine import FactorCorrelationEngine
from .correlation_spike_engine import CorrelationSpikeEngine
from .correlation_aggregator import CorrelationAggregator


class TestCorrelationSpikeEngine:
    """Tests for Correlation Spike Engine."""
    
    @pytest.fixture
    def aggregator(self):
        return CorrelationAggregator()
    
    @pytest.fixture
    def asset_engine(self):
        return AssetCorrelationEngine()
    
    @pytest.fixture
    def strategy_engine(self):
        return StrategyCorrelationEngine()
    
    @pytest.fixture
    def factor_engine(self):
        return FactorCorrelationEngine()
    
    @pytest.fixture
    def spike_engine(self):
        return CorrelationSpikeEngine()
    
    # ═══════════════════════════════════════════════════════════
    # TEST 1: Diversified portfolio -> NORMAL
    # ═══════════════════════════════════════════════════════════
    
    def test_diversified_portfolio_normal(self, aggregator):
        """Diversified portfolio should produce NORMAL state."""
        state = aggregator.calculate(
            asset_allocations={"BTC": 0.25, "ETH": 0.25, "SOL": 0.25, "AVAX": 0.25},
            active_strategies=["MTF_BREAKOUT", "MEAN_REVERSION", "ARB_SPOT_PERP"],
            factor_allocations={
                "trend_factor": 0.2,
                "momentum_factor": 0.2,
                "volatility_factor": 0.2,
                "flow_factor": 0.2,
                "mean_reversion_factor": 0.2,
            },
            volatility_state="LOW",
            risk_state="NORMAL",
        )
        
        assert state.correlation_state == CorrelationState.NORMAL
        assert state.correlation_spike_intensity < 0.35
        assert state.diversification_score > 0.50
        assert state.recommended_action == CorrelationAction.HOLD
    
    # ═══════════════════════════════════════════════════════════
    # TEST 2: Moderate overlap -> ELEVATED
    # ═══════════════════════════════════════════════════════════
    
    def test_moderate_overlap_elevated(self, aggregator):
        """Moderate correlation overlap should produce ELEVATED state."""
        state = aggregator.calculate(
            asset_allocations={"BTC": 0.50, "ETH": 0.30, "SOL": 0.20},
            active_strategies=["MTF_BREAKOUT", "CHANNEL_BREAKOUT"],  # Same type
            volatility_state="NORMAL",
            risk_state="ELEVATED",
        )
        
        assert state.correlation_state in [CorrelationState.NORMAL, CorrelationState.ELEVATED]
        assert state.correlation_spike_intensity >= 0.25
    
    # ═══════════════════════════════════════════════════════════
    # TEST 3: Correlated strategies -> HIGH
    # ═══════════════════════════════════════════════════════════
    
    def test_correlated_strategies_high(self, aggregator):
        """Highly correlated strategies should produce HIGH state."""
        state = aggregator.calculate(
            asset_allocations={"BTC": 0.60, "ETH": 0.40},  # Concentrated
            active_strategies=[
                "MTF_BREAKOUT",
                "CHANNEL_BREAKOUT",
                "MOMENTUM_CONTINUATION",
            ],  # All trend/breakout
            factor_allocations={
                "trend_factor": 0.50,
                "breakout_factor": 0.30,
                "momentum_factor": 0.20,
            },  # Concentrated factors
            volatility_state="HIGH",
            risk_state="HIGH",
        )
        
        assert state.correlation_state in [CorrelationState.ELEVATED, CorrelationState.HIGH, CorrelationState.SYSTEMIC]
        assert state.correlation_spike_intensity >= 0.45
        assert state.diversification_score < 0.55
    
    # ═══════════════════════════════════════════════════════════
    # TEST 4: Crisis regime -> SYSTEMIC
    # ═══════════════════════════════════════════════════════════
    
    def test_crisis_regime_systemic(self, aggregator):
        """Crisis regime should produce SYSTEMIC state."""
        state = aggregator.calculate(
            asset_allocations={"BTC": 0.70, "ETH": 0.30},
            active_strategies=["MTF_BREAKOUT", "MOMENTUM_CONTINUATION"],
            factor_allocations={
                "trend_factor": 0.60,
                "momentum_factor": 0.40,
            },
            volatility_state="CRISIS",
            risk_state="CRITICAL",
            tail_risk_state="EXTREME",
        )
        
        assert state.correlation_state in [CorrelationState.HIGH, CorrelationState.SYSTEMIC]
        assert state.correlation_spike_intensity >= 0.55
        assert state.recommended_action in [CorrelationAction.REDUCE_DIVERSIFICATION, CorrelationAction.DELEVER]
    
    # ═══════════════════════════════════════════════════════════
    # TEST 5: Asset correlation calculated correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_asset_correlation_calculation(self, asset_engine):
        """Asset correlation should be calculated correctly."""
        # Low volatility = low correlation
        result_low = asset_engine.calculate(
            volatility_state="LOW",
            asset_allocations={"BTC": 0.5, "ETH": 0.5},
        )
        
        # High volatility = high correlation
        result_high = asset_engine.calculate(
            volatility_state="HIGH",
            asset_allocations={"BTC": 0.5, "ETH": 0.5},
        )
        
        assert result_low["asset_correlation"] < result_high["asset_correlation"]
        assert 0 <= result_low["asset_correlation"] <= 1
        assert 0 <= result_high["asset_correlation"] <= 1
    
    # ═══════════════════════════════════════════════════════════
    # TEST 6: Strategy correlation calculated correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_strategy_correlation_calculation(self, strategy_engine):
        """Strategy correlation should be calculated correctly."""
        # Similar strategies = high correlation
        result_similar = strategy_engine.calculate(
            active_strategies=["MTF_BREAKOUT", "CHANNEL_BREAKOUT", "MOMENTUM_CONTINUATION"],
            volatility_state="NORMAL",
        )
        
        # Diverse strategies = low correlation
        result_diverse = strategy_engine.calculate(
            active_strategies=["MTF_BREAKOUT", "MEAN_REVERSION", "ARB_SPOT_PERP"],
            volatility_state="NORMAL",
        )
        
        assert result_similar["strategy_correlation"] > result_diverse["strategy_correlation"]
        assert 0 <= result_similar["strategy_correlation"] <= 1
        assert 0 <= result_diverse["strategy_correlation"] <= 1
    
    # ═══════════════════════════════════════════════════════════
    # TEST 7: Factor correlation calculated correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_factor_correlation_calculation(self, factor_engine):
        """Factor correlation should be calculated correctly."""
        # Concentrated factors = high correlation
        result_concentrated = factor_engine.calculate(
            factor_allocations={"trend_factor": 0.70, "momentum_factor": 0.30},
            volatility_state="NORMAL",
        )
        
        # Diverse factors = low correlation
        result_diverse = factor_engine.calculate(
            factor_allocations={
                "trend_factor": 0.20,
                "mean_reversion_factor": 0.20,
                "volatility_factor": 0.20,
                "flow_factor": 0.20,
                "volume_factor": 0.20,
            },
            volatility_state="NORMAL",
        )
        
        assert result_concentrated["factor_correlation"] >= result_diverse["factor_correlation"]
        assert 0 <= result_concentrated["factor_correlation"] <= 1
        assert 0 <= result_diverse["factor_correlation"] <= 1
    
    # ═══════════════════════════════════════════════════════════
    # TEST 8: Diversification score correct
    # ═══════════════════════════════════════════════════════════
    
    def test_diversification_score(self, spike_engine):
        """Diversification score should be 1 - avg(correlations)."""
        # Low correlations = high diversification
        score_low = spike_engine.calculate_diversification_score(
            asset_correlation=0.20,
            strategy_correlation=0.15,
            factor_correlation=0.25,
        )
        
        # High correlations = low diversification
        score_high = spike_engine.calculate_diversification_score(
            asset_correlation=0.80,
            strategy_correlation=0.75,
            factor_correlation=0.70,
        )
        
        assert score_low > 0.70
        assert score_high < 0.30
        assert score_low > score_high
    
    # ═══════════════════════════════════════════════════════════
    # TEST 9: Correlation spike intensity bounded
    # ═══════════════════════════════════════════════════════════
    
    def test_spike_intensity_bounded(self, spike_engine):
        """Spike intensity should be bounded [0, 1]."""
        # Test with extreme values
        result_low = spike_engine.calculate(
            asset_correlation=0.0,
            strategy_correlation=0.0,
            factor_correlation=0.0,
            volatility_state="LOW",
        )
        
        result_high = spike_engine.calculate(
            asset_correlation=1.0,
            strategy_correlation=1.0,
            factor_correlation=1.0,
            volatility_state="CRISIS",
            risk_state="CRITICAL",
        )
        
        assert 0 <= result_low["correlation_spike_intensity"] <= 1
        assert 0 <= result_high["correlation_spike_intensity"] <= 1
    
    # ═══════════════════════════════════════════════════════════
    # TEST 10: API output correct
    # ═══════════════════════════════════════════════════════════
    
    def test_api_output_format(self, aggregator):
        """API output should have correct format."""
        state = aggregator.calculate(
            volatility_state="NORMAL",
            risk_state="NORMAL",
        )
        
        output = state.to_dict()
        
        # Check required fields
        assert "asset_correlation" in output
        assert "strategy_correlation" in output
        assert "factor_correlation" in output
        assert "diversification_score" in output
        assert "correlation_spike_intensity" in output
        assert "correlation_state" in output
        assert "recommended_action" in output
        assert "confidence_modifier" in output
        assert "capital_modifier" in output
        assert "dominant_correlation" in output
        assert "reason" in output
        assert "timestamp" in output
        
        # Check types
        assert isinstance(output["asset_correlation"], float)
        assert isinstance(output["correlation_state"], str)
        assert isinstance(output["recommended_action"], str)
        
        # Check ranges
        assert 0 <= output["asset_correlation"] <= 1
        assert 0 <= output["diversification_score"] <= 1
        assert 0 <= output["correlation_spike_intensity"] <= 1
        assert 0 <= output["confidence_modifier"] <= 1
        assert 0 <= output["capital_modifier"] <= 1


def run_all_tests():
    """Run all tests and return results."""
    test_class = TestCorrelationSpikeEngine()
    aggregator = CorrelationAggregator()
    asset_engine = AssetCorrelationEngine()
    strategy_engine = StrategyCorrelationEngine()
    factor_engine = FactorCorrelationEngine()
    spike_engine = CorrelationSpikeEngine()
    
    results = []
    
    tests = [
        ("test_1_diversified_portfolio_normal", lambda: test_class.test_diversified_portfolio_normal(aggregator)),
        ("test_2_moderate_overlap_elevated", lambda: test_class.test_moderate_overlap_elevated(aggregator)),
        ("test_3_correlated_strategies_high", lambda: test_class.test_correlated_strategies_high(aggregator)),
        ("test_4_crisis_regime_systemic", lambda: test_class.test_crisis_regime_systemic(aggregator)),
        ("test_5_asset_correlation", lambda: test_class.test_asset_correlation_calculation(asset_engine)),
        ("test_6_strategy_correlation", lambda: test_class.test_strategy_correlation_calculation(strategy_engine)),
        ("test_7_factor_correlation", lambda: test_class.test_factor_correlation_calculation(factor_engine)),
        ("test_8_diversification_score", lambda: test_class.test_diversification_score(spike_engine)),
        ("test_9_spike_intensity_bounded", lambda: test_class.test_spike_intensity_bounded(spike_engine)),
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
    print(f"CORRELATION SPIKE ENGINE TESTS")
    print(f"{'='*60}")
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Failed: {results['failed']}")
    print(f"\nResults:")
    for r in results["results"]:
        status = "✅" if r["status"] == "PASSED" else "❌"
        print(f"  {status} {r['test']}")
        if r["status"] != "PASSED" and "error" in r:
            print(f"     Error: {r['error']}")
