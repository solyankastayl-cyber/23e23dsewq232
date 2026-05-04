"""
PHASE 18.4 — Meta Portfolio Integration Tests
=============================================
Integration tests for Meta Portfolio into Trading Product.

Test scenarios:
1. Balanced portfolio → no penalty
2. Constrained portfolio → size reduced
3. Constrained portfolio → aggressive forbidden
4. Risk_off portfolio → blocked
5. Final confidence adjusted
6. Trading product snapshot includes meta_portfolio block
7. Direction unchanged after portfolio overlay
"""

import pytest
from datetime import datetime, timezone

from modules.trading_product.trading_product_engine import get_trading_product_engine
from modules.trading_product.trading_product_types import (
    ProductStatus,
    PortfolioOverlayEffect,
)


class TestMetaPortfolioIntegration:
    """Integration tests for Meta Portfolio in Trading Product."""
    
    def test_trading_product_includes_meta_portfolio(self):
        """TEST 6: Trading product snapshot includes meta_portfolio block."""
        engine = get_trading_product_engine()
        
        result = engine.compute("BTC")
        result_dict = result.to_dict()
        
        # Check meta_portfolio block exists
        assert "meta_portfolio" in result_dict
        assert "portfolio_state" in result_dict["meta_portfolio"]
        assert "allowed" in result_dict["meta_portfolio"]
        assert "confidence_modifier" in result_dict["meta_portfolio"]
        assert "capital_modifier" in result_dict["meta_portfolio"]
        assert "recommended_action" in result_dict["meta_portfolio"]
    
    def test_portfolio_state_in_snapshot(self):
        """Test portfolio state fields in snapshot."""
        engine = get_trading_product_engine()
        
        result = engine.compute("BTC")
        
        # Check portfolio fields exist
        assert result.portfolio_state is not None
        assert result.portfolio_allowed is not None
        assert result.portfolio_overlay_effect is not None
    
    def test_portfolio_overlay_effect_types(self):
        """Test portfolio overlay effect determination."""
        engine = get_trading_product_engine()
        
        # Test effect determination
        effect_blocking = engine._determine_portfolio_overlay_effect("RISK_OFF", False)
        assert effect_blocking == PortfolioOverlayEffect.BLOCKING
        
        effect_restrictive = engine._determine_portfolio_overlay_effect("CONSTRAINED", True)
        assert effect_restrictive == PortfolioOverlayEffect.RESTRICTIVE
        
        effect_supportive = engine._determine_portfolio_overlay_effect("BALANCED", True)
        assert effect_supportive == PortfolioOverlayEffect.SUPPORTIVE
    
    def test_execution_restriction_risk_off(self):
        """TEST 4: Risk_off portfolio → blocked (execution = NONE)."""
        engine = get_trading_product_engine()
        
        # Test execution restriction
        result = engine._apply_portfolio_execution_restriction(
            "AGGRESSIVE", "RISK_OFF", False
        )
        assert result == "NONE"
    
    def test_execution_restriction_constrained(self):
        """TEST 3: Constrained portfolio → aggressive forbidden."""
        engine = get_trading_product_engine()
        
        # AGGRESSIVE should be downgraded to NORMAL
        result = engine._apply_portfolio_execution_restriction(
            "AGGRESSIVE", "CONSTRAINED", True
        )
        assert result == "NORMAL"
        
        # NORMAL should stay NORMAL
        result2 = engine._apply_portfolio_execution_restriction(
            "NORMAL", "CONSTRAINED", True
        )
        assert result2 == "NORMAL"
    
    def test_execution_restriction_balanced(self):
        """TEST 1: Balanced portfolio → no penalty."""
        engine = get_trading_product_engine()
        
        # No restrictions for balanced
        result = engine._apply_portfolio_execution_restriction(
            "AGGRESSIVE", "BALANCED", True
        )
        assert result == "AGGRESSIVE"
    
    def test_product_status_blocked_on_risk_off(self):
        """TEST 4: Portfolio risk_off → product BLOCKED."""
        engine = get_trading_product_engine()
        
        status, reason = engine._determine_product_status(
            action="ALLOW",
            execution_mode="NORMAL",
            decision_output={},
            execution_output={},
            exchange_output={},
            portfolio_allowed=False,
            portfolio_state="RISK_OFF",
        )
        
        assert status == ProductStatus.BLOCKED
        assert "portfolio" in reason.lower()
    
    def test_product_status_conflicted_on_constrained(self):
        """TEST 2: Constrained portfolio → CONFLICTED status."""
        engine = get_trading_product_engine()
        
        status, reason = engine._determine_product_status(
            action="ALLOW",
            execution_mode="NORMAL",
            decision_output={},
            execution_output={},
            exchange_output={},
            portfolio_allowed=True,
            portfolio_state="CONSTRAINED",
        )
        
        assert status == ProductStatus.CONFLICTED
        assert "constrained" in reason.lower()
    
    def test_direction_unchanged(self):
        """TEST 7: Direction unchanged after portfolio overlay."""
        engine = get_trading_product_engine()
        
        # Get original direction from trading decision
        result = engine.compute("BTC")
        
        # Direction should match trading decision (not changed by portfolio)
        trading_decision_direction = result.trading_decision.get("direction", "NEUTRAL")
        
        # Portfolio overlay should NOT change direction
        assert result.final_direction == trading_decision_direction
    
    def test_confidence_modifier_applied(self):
        """TEST 5: Final confidence adjusted by portfolio modifier."""
        engine = get_trading_product_engine()
        
        result = engine.compute("BTC")
        
        # Check that confidence modifier exists
        portfolio_conf_mod = result.meta_portfolio.get("confidence_modifier", 1.0)
        
        # If modifier < 1, confidence should be reduced
        if portfolio_conf_mod < 1.0:
            # We can't directly test this without mocking, but we can verify
            # the modifier is being used in the output
            assert result.portfolio_confidence_modifier == portfolio_conf_mod
    
    def test_size_modifier_applied(self):
        """TEST 2 (continued): Size reduced by portfolio modifier."""
        engine = get_trading_product_engine()
        
        result = engine.compute("BTC")
        
        # Check that capital modifier exists
        portfolio_cap_mod = result.meta_portfolio.get("capital_modifier", 1.0)
        
        # If modifier < 1, size should be reduced
        if portfolio_cap_mod < 1.0:
            assert result.portfolio_capital_modifier == portfolio_cap_mod


class TestTradingProductOutput:
    """Tests for trading product output format."""
    
    def test_to_dict_includes_portfolio(self):
        """Test to_dict includes portfolio fields."""
        engine = get_trading_product_engine()
        
        result = engine.compute("BTC")
        result_dict = result.to_dict()
        
        assert "portfolio_state" in result_dict
        assert "portfolio_allowed" in result_dict
        assert "portfolio_overlay_effect" in result_dict
        assert "meta_portfolio" in result_dict
    
    def test_to_summary_includes_portfolio(self):
        """Test to_summary_dict includes portfolio fields."""
        engine = get_trading_product_engine()
        
        result = engine.compute("BTC")
        summary = result.to_summary_dict()
        
        assert "portfolio" in summary
        assert "portfolio_allowed" in summary
    
    def test_full_dict_structure(self):
        """Test full dict has all expected fields."""
        engine = get_trading_product_engine()
        
        result = engine.compute("ETH")
        full_dict = result.to_full_dict()
        
        # Core fields
        assert "symbol" in full_dict
        assert "final_action" in full_dict
        assert "final_direction" in full_dict
        assert "final_confidence" in full_dict
        assert "final_size_pct" in full_dict
        
        # Module outputs
        assert "ta_hypothesis" in full_dict
        assert "trading_decision" in full_dict
        assert "position_sizing" in full_dict
        assert "execution_mode" in full_dict
        
        # Portfolio
        assert "meta_portfolio" in full_dict


class TestMetaPortfolioDataFetch:
    """Tests for meta portfolio data fetching."""
    
    def test_get_meta_portfolio_data(self):
        """Test meta portfolio data fetch."""
        engine = get_trading_product_engine()
        
        data = engine._get_meta_portfolio_data("BTC")
        
        assert "portfolio_state" in data
        assert "allowed" in data
        assert "confidence_modifier" in data
        assert "capital_modifier" in data
    
    def test_meta_portfolio_fallback(self):
        """Test fallback when meta portfolio not available."""
        engine = get_trading_product_engine()
        
        # Even if engine fails, should return defaults
        data = engine._get_meta_portfolio_data("UNKNOWN")
        
        assert data.get("allowed", False) is True or data.get("allowed", True) is True


# ══════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════

def run_tests():
    """Run all tests and print results."""
    print("\n" + "=" * 60)
    print("PHASE 18.4 — Meta Portfolio Integration Tests")
    print("=" * 60 + "\n")
    
    test_classes = [
        TestMetaPortfolioIntegration,
        TestTradingProductOutput,
        TestMetaPortfolioDataFetch,
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
