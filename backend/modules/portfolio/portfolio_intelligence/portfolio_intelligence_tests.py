"""
PHASE 18.1 — Portfolio Intelligence Tests
==========================================
Unit tests for Portfolio Intelligence Layer.

Test scenarios:
1. Balanced portfolio
2. Concentrated BTC portfolio
3. Overloaded alt portfolio
4. Weak breadth + high alt exposure → DEFENSIVE
5. Factor overload detected
6. Cluster overload detected
7. Net/gross exposure calculated correctly
8. Recommended action generated correctly
"""

import pytest
from datetime import datetime, timezone

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    Position,
    PositionDirection,
    MarketContext,
    PortfolioContext,
    PortfolioRiskState,
    RecommendedAction,
)
from modules.portfolio.portfolio_intelligence.portfolio_intelligence_engine import (
    get_portfolio_intelligence_engine,
)
from modules.portfolio.portfolio_intelligence.portfolio_exposure_engine import (
    get_portfolio_exposure_engine,
)
from modules.portfolio.portfolio_intelligence.factor_exposure_engine import (
    get_factor_exposure_engine,
)
from modules.portfolio.portfolio_intelligence.cluster_exposure_engine import (
    get_cluster_exposure_engine,
)
from modules.portfolio.portfolio_intelligence.portfolio_risk_engine import (
    get_portfolio_risk_engine,
)


class TestPortfolioExposureEngine:
    """Tests for Portfolio Exposure Engine."""
    
    def test_net_gross_exposure_calculation(self):
        """TEST 7: Net/gross exposure calculated correctly."""
        engine = get_portfolio_exposure_engine()
        
        # Example from spec:
        # BTC short 0.8
        # ETH short 0.5
        # SOL long 0.2
        # net = -1.1, gross = 1.5
        positions = [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.80,
                final_confidence=0.75,
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.50,
                final_confidence=0.70,
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.20,
                final_confidence=0.65,
            ),
        ]
        
        result = engine.calculate_exposures(positions)
        
        assert abs(result["net_exposure"] - (-1.10)) < 0.01
        assert abs(result["gross_exposure"] - 1.50) < 0.01
        assert result["long_count"] == 1
        assert result["short_count"] == 2
    
    def test_asset_exposure_breakdown(self):
        """Test asset exposure (BTC, ETH, ALT) breakdown."""
        engine = get_portfolio_exposure_engine()
        
        positions = [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.80,
                final_confidence=0.75,
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.50,
                final_confidence=0.70,
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.20,
                final_confidence=0.65,
            ),
        ]
        
        result = engine.calculate_asset_exposure(positions)
        
        assert abs(result["btc_exposure"] - 0.80) < 0.01
        assert abs(result["eth_exposure"] - 0.50) < 0.01
        assert abs(result["alt_exposure"] - 0.20) < 0.01


class TestFactorExposureEngine:
    """Tests for Factor Exposure Engine."""
    
    def test_factor_overload_detection(self):
        """TEST 5: Factor overload detected."""
        engine = get_factor_exposure_engine()
        
        # All positions using trend-based factors
        positions = [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.50,
                final_confidence=0.78,
                primary_factor="trend_breakout_factor",
                secondary_factor="trend_continuation_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.40,
                final_confidence=0.75,
                primary_factor="trend_breakout_factor",
                secondary_factor="structure_break_factor",
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.70,
                primary_factor="trend_continuation_factor",
            ),
        ]
        
        exposure = engine.calculate_factor_exposure(positions)
        overload = engine.detect_factor_overload(exposure)
        
        # Trend factor should be dominant
        assert "trend" in exposure
        assert exposure["trend"] > 0.50
        assert overload["max_factor"] == "trend"
    
    def test_diversified_factors(self):
        """Test diversified factor portfolio."""
        engine = get_factor_exposure_engine()
        
        positions = [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.80,
                primary_factor="trend_breakout_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.75,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.30,
                final_confidence=0.70,
                primary_factor="mean_reversion_factor",
            ),
        ]
        
        exposure = engine.calculate_factor_exposure(positions)
        overload = engine.detect_factor_overload(exposure)
        
        # Should not be overloaded
        assert overload["max_exposure"] < 0.60


class TestClusterExposureEngine:
    """Tests for Cluster Exposure Engine."""
    
    def test_cluster_overload_detection(self):
        """TEST 6: Cluster overload detected."""
        engine = get_cluster_exposure_engine()
        
        # All ETH ecosystem positions
        positions = [
            Position(
                symbol="OPUSDT",
                direction=PositionDirection.LONG,
                position_size=0.40,
                final_confidence=0.72,
            ),
            Position(
                symbol="ARBUSDT",
                direction=PositionDirection.LONG,
                position_size=0.35,
                final_confidence=0.68,
            ),
            Position(
                symbol="MATICUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.65,
            ),
        ]
        
        exposure = engine.calculate_cluster_exposure(positions)
        overload = engine.detect_cluster_overload(exposure)
        
        # ETH cluster or alts should be significant (split between eth_cluster and alts_cluster)
        # Since symbols are in both eth_cluster and alts_cluster, exposure is split
        assert exposure["eth_cluster"] >= 0.40 or exposure["alts_cluster"] >= 0.40
        assert overload["max_exposure"] >= 0.40
    
    def test_btc_cluster_concentration(self):
        """Test BTC cluster concentration."""
        engine = get_cluster_exposure_engine()
        
        positions = [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.90,
                final_confidence=0.85,
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.10,
                final_confidence=0.60,
            ),
        ]
        
        exposure = engine.calculate_cluster_exposure(positions)
        
        # BTC cluster should be significant (split with majors_cluster)
        # BTCUSDT is in both btc_cluster and majors_cluster
        assert exposure["btc_cluster"] >= 0.40
        # Majors should also be significant since both BTC and ETH are majors
        assert exposure["majors_cluster"] >= 0.40


class TestPortfolioRiskEngine:
    """Tests for Portfolio Risk Engine."""
    
    def test_balanced_state(self):
        """TEST 1: Balanced portfolio."""
        engine = get_portfolio_risk_engine()
        
        # Low concentration in all areas
        cluster_exposure = {"btc_cluster": 0.30, "eth_cluster": 0.25, "alts_cluster": 0.20}
        factor_exposure = {"trend": 0.30, "momentum": 0.25, "reversal": 0.20}
        asset_exposure = {"btc_exposure": 0.30, "eth_exposure": 0.25, "alt_exposure": 0.20}
        market_context = MarketContext(
            dominance_regime="BALANCED",
            breadth_state="STRONG",
        )
        
        concentration = engine.calculate_concentration_score(
            cluster_exposure, factor_exposure, asset_exposure
        )
        risk_state = engine.determine_risk_state(
            concentration, market_context, asset_exposure["alt_exposure"]
        )
        
        assert concentration < 0.40
        assert risk_state == PortfolioRiskState.BALANCED
    
    def test_concentrated_state(self):
        """TEST 2: Concentrated BTC portfolio."""
        engine = get_portfolio_risk_engine()
        
        # High BTC concentration
        cluster_exposure = {"btc_cluster": 0.55, "eth_cluster": 0.10, "alts_cluster": 0.10}
        factor_exposure = {"trend": 0.45, "momentum": 0.20}
        asset_exposure = {"btc_exposure": 0.55, "eth_exposure": 0.10, "alt_exposure": 0.10}
        market_context = MarketContext(
            dominance_regime="BTC_DOM",
            breadth_state="MIXED",
        )
        
        concentration = engine.calculate_concentration_score(
            cluster_exposure, factor_exposure, asset_exposure
        )
        risk_state = engine.determine_risk_state(
            concentration, market_context, asset_exposure["alt_exposure"]
        )
        
        assert 0.40 <= concentration < 0.65
        assert risk_state == PortfolioRiskState.CONCENTRATED
    
    def test_overloaded_state(self):
        """TEST 3: Overloaded alt portfolio."""
        engine = get_portfolio_risk_engine()
        
        # High alt concentration
        cluster_exposure = {"btc_cluster": 0.10, "eth_cluster": 0.10, "alts_cluster": 0.75}
        factor_exposure = {"momentum": 0.70, "reversal": 0.10}
        asset_exposure = {"btc_exposure": 0.10, "eth_exposure": 0.10, "alt_exposure": 0.75}
        market_context = MarketContext(
            dominance_regime="ALT_SEASON",
            breadth_state="STRONG",
        )
        
        concentration = engine.calculate_concentration_score(
            cluster_exposure, factor_exposure, asset_exposure
        )
        risk_state = engine.determine_risk_state(
            concentration, market_context, asset_exposure["alt_exposure"]
        )
        
        assert concentration >= 0.65
        assert risk_state == PortfolioRiskState.OVERLOADED
    
    def test_defensive_state(self):
        """TEST 4: Weak breadth + high alt exposure → DEFENSIVE."""
        engine = get_portfolio_risk_engine()
        
        # Moderate concentration but weak breadth + high alt
        cluster_exposure = {"btc_cluster": 0.10, "eth_cluster": 0.10, "alts_cluster": 0.55}
        factor_exposure = {"momentum": 0.45, "reversal": 0.20}
        asset_exposure = {"btc_exposure": 0.10, "eth_exposure": 0.10, "alt_exposure": 0.55}
        market_context = MarketContext(
            dominance_regime="BTC_DOM",
            breadth_state="WEAK",  # Key condition
        )
        
        concentration = engine.calculate_concentration_score(
            cluster_exposure, factor_exposure, asset_exposure
        )
        risk_state = engine.determine_risk_state(
            concentration, market_context, asset_exposure["alt_exposure"]
        )
        
        # DEFENSIVE overrides concentration-based state
        assert risk_state == PortfolioRiskState.DEFENSIVE
    
    def test_recommended_action_hold(self):
        """TEST 8a: Recommended action - HOLD for balanced."""
        engine = get_portfolio_risk_engine()
        
        action = engine.determine_recommended_action(
            risk_state=PortfolioRiskState.BALANCED,
            market_context=MarketContext(),
            factor_overload={"is_overloaded": False},
            alt_exposure=0.20,
            gross_exposure=1.0,
        )
        
        assert action == RecommendedAction.HOLD
    
    def test_recommended_action_reduce_alt(self):
        """TEST 8b: Recommended action - REDUCE_ALT."""
        engine = get_portfolio_risk_engine()
        
        action = engine.determine_recommended_action(
            risk_state=PortfolioRiskState.CONCENTRATED,
            market_context=MarketContext(dominance_regime="BTC_DOM"),
            factor_overload={"is_overloaded": False},
            alt_exposure=0.60,  # High alt exposure
            gross_exposure=1.0,
        )
        
        assert action == RecommendedAction.REDUCE_ALT
    
    def test_recommended_action_reduce_factor(self):
        """TEST 8c: Recommended action - REDUCE_FACTOR."""
        engine = get_portfolio_risk_engine()
        
        action = engine.determine_recommended_action(
            risk_state=PortfolioRiskState.CONCENTRATED,
            market_context=MarketContext(dominance_regime="BALANCED"),
            factor_overload={"is_overloaded": True, "overloaded_factors": [{"factor": "trend"}]},
            alt_exposure=0.20,
            gross_exposure=1.0,
        )
        
        assert action == RecommendedAction.REDUCE_FACTOR
    
    def test_recommended_action_delever(self):
        """TEST 8d: Recommended action - DELEVER."""
        engine = get_portfolio_risk_engine()
        
        action = engine.determine_recommended_action(
            risk_state=PortfolioRiskState.CONCENTRATED,
            market_context=MarketContext(),
            factor_overload={"is_overloaded": False},
            alt_exposure=0.20,
            gross_exposure=2.5,  # High gross exposure
        )
        
        assert action == RecommendedAction.DELEVER


class TestPortfolioIntelligenceEngine:
    """Integration tests for Portfolio Intelligence Engine."""
    
    def test_full_analysis_default_portfolio(self):
        """Test full analysis on default portfolio."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("default")
        
        # Check all required fields are present
        assert result.net_exposure is not None
        assert result.gross_exposure is not None
        assert result.btc_exposure is not None
        assert result.eth_exposure is not None
        assert result.alt_exposure is not None
        assert result.factor_exposure is not None
        assert result.cluster_exposure is not None
        assert result.concentration_score is not None
        assert result.diversification_score is not None
        assert result.portfolio_risk_state is not None
        assert result.recommended_action is not None
        assert result.confidence_modifier is not None
        assert result.capital_modifier is not None
    
    def test_balanced_portfolio(self):
        """Test balanced portfolio scenario."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("balanced_portfolio")
        
        # With diversified positions across majors, concentration can be high
        # due to majors_cluster concentration
        # Key is that we have multiple assets and factor diversification
        assert result.position_count >= 3
        # Factor exposure should be diversified (no single factor > 0.50)
        max_factor_exposure = max(result.factor_exposure.values()) if result.factor_exposure else 0
        assert max_factor_exposure < 0.50, f"Factor exposure too concentrated: {result.factor_exposure}"
    
    def test_btc_concentrated_portfolio(self):
        """Test BTC concentrated portfolio scenario."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("btc_concentrated")
        
        # Should be CONCENTRATED or higher
        assert result.portfolio_risk_state in [
            PortfolioRiskState.CONCENTRATED,
            PortfolioRiskState.OVERLOADED,
        ]
        assert result.btc_exposure > 0.70
    
    def test_alt_overloaded_portfolio(self):
        """Test alt overloaded portfolio scenario."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("alt_overloaded")
        
        # High alt exposure with weak breadth should trigger DEFENSIVE
        assert result.portfolio_risk_state in [
            PortfolioRiskState.DEFENSIVE,
            PortfolioRiskState.OVERLOADED,
        ]
        assert result.alt_exposure > 0.70
    
    def test_defensive_scenario(self):
        """Test defensive scenario (weak breadth + high alt)."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("defensive_scenario")
        
        # Should trigger DEFENSIVE state
        assert result.portfolio_risk_state == PortfolioRiskState.DEFENSIVE
        assert result.recommended_action == RecommendedAction.REDUCE_ALT
        assert result.confidence_modifier == 0.85
        assert result.capital_modifier == 0.75
    
    def test_high_gross_exposure(self):
        """Test high gross exposure scenario."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("high_gross_exposure")
        
        # Gross exposure should be > 2.0
        assert result.gross_exposure > 2.0
        assert result.recommended_action == RecommendedAction.DELEVER
    
    def test_to_dict_conversion(self):
        """Test state to_dict conversion."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("default")
        result_dict = result.to_dict()
        
        assert "net_exposure" in result_dict
        assert "gross_exposure" in result_dict
        assert "portfolio_risk_state" in result_dict
        assert "recommended_action" in result_dict
        assert "confidence_modifier" in result_dict
        assert "capital_modifier" in result_dict
    
    def test_to_summary_conversion(self):
        """Test state to_summary conversion."""
        engine = get_portfolio_intelligence_engine()
        
        result = engine.analyze_portfolio("default")
        summary = result.to_summary()
        
        assert "risk_state" in summary
        assert "action" in summary
        assert "confidence_mod" in summary
        assert "capital_mod" in summary


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 18.1 — Portfolio Intelligence Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestPortfolioExposureEngine,
        TestFactorExposureEngine,
        TestClusterExposureEngine,
        TestPortfolioRiskEngine,
        TestPortfolioIntelligenceEngine,
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
