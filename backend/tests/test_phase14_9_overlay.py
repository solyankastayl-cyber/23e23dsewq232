"""
PHASE 14.9 — Dominance/Breadth Overlay Integration Tests
=========================================================
Tests for trading product overlay integration:
- Overlay fields in trading product response
- Overlay effect calculation (SUPPORTIVE/NEUTRAL/HOSTILE)
- Position sizing with dominance/breadth adjustments
- Execution mode downgrade logic
- Market structure API
- Batch endpoints
"""

import pytest
import requests
import os

# Base URL for testing - use localhost since external URL routing has issues
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')


class TestTradingProductOverlayFields:
    """Test that trading product endpoints return new overlay fields from PHASE 14.9"""

    def test_trading_product_btc_returns_overlay_fields(self):
        """GET /api/trading-product/BTC should return all overlay fields"""
        response = requests.get(f"{BASE_URL}/api/trading-product/BTC")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", "Response status should be 'ok'"
        
        product_data = data.get("data", {})
        
        # Verify all new overlay fields exist
        assert "dominance_state" in product_data, "Missing dominance_state field"
        assert "breadth_state" in product_data, "Missing breadth_state field"
        assert "dominance_modifier" in product_data, "Missing dominance_modifier field"
        assert "breadth_modifier" in product_data, "Missing breadth_modifier field"
        assert "overlay_effect" in product_data, "Missing overlay_effect field"
        
        # Verify field types
        assert isinstance(product_data["dominance_state"], str), "dominance_state should be string"
        assert isinstance(product_data["breadth_state"], str), "breadth_state should be string"
        assert isinstance(product_data["dominance_modifier"], (int, float)), "dominance_modifier should be numeric"
        assert isinstance(product_data["breadth_modifier"], (int, float)), "breadth_modifier should be numeric"
        assert isinstance(product_data["overlay_effect"], str), "overlay_effect should be string"
        
        # Verify enum values are valid
        assert product_data["overlay_effect"] in ["SUPPORTIVE", "NEUTRAL", "HOSTILE"], \
            f"Invalid overlay_effect: {product_data['overlay_effect']}"
        
        print(f"✅ BTC overlay fields: dominance={product_data['dominance_state']}, "
              f"breadth={product_data['breadth_state']}, effect={product_data['overlay_effect']}")

    def test_trading_product_sol_returns_overlay_fields(self):
        """GET /api/trading-product/SOL should return overlay fields (ALT coin)"""
        response = requests.get(f"{BASE_URL}/api/trading-product/SOL")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        product_data = data.get("data", {})
        
        # Verify overlay fields exist
        assert "dominance_state" in product_data
        assert "breadth_state" in product_data
        assert "dominance_modifier" in product_data
        assert "breadth_modifier" in product_data
        assert "overlay_effect" in product_data
        
        print(f"✅ SOL overlay fields: dominance={product_data['dominance_state']}, "
              f"breadth={product_data['breadth_state']}, effect={product_data['overlay_effect']}")

    def test_trading_product_eth_returns_overlay_fields(self):
        """GET /api/trading-product/ETH should return overlay fields"""
        response = requests.get(f"{BASE_URL}/api/trading-product/ETH")
        assert response.status_code == 200
        
        data = response.json()
        product_data = data.get("data", {})
        
        assert "dominance_state" in product_data
        assert "overlay_effect" in product_data
        
        print(f"✅ ETH overlay fields: dominance={product_data['dominance_state']}, "
              f"effect={product_data['overlay_effect']}")


class TestOverlayEffectCalculation:
    """Test overlay effect calculation based on dominance regime and symbol type"""

    def test_btc_in_btc_dom_should_be_supportive_or_neutral(self):
        """BTC in BTC_DOM regime should have SUPPORTIVE or NEUTRAL effect"""
        response = requests.get(f"{BASE_URL}/api/trading-product/BTC")
        assert response.status_code == 200
        
        data = response.json()
        product_data = data.get("data", {})
        
        dominance_state = product_data.get("dominance_state")
        overlay_effect = product_data.get("overlay_effect")
        
        # If dominance is BTC_DOM, BTC should be supportive
        if dominance_state == "BTC_DOM":
            # BTC in BTC_DOM should get a boost, so SUPPORTIVE or at least NEUTRAL
            assert overlay_effect in ["SUPPORTIVE", "NEUTRAL"], \
                f"BTC in BTC_DOM should be SUPPORTIVE or NEUTRAL, got {overlay_effect}"
            print(f"✅ BTC in {dominance_state}: overlay_effect={overlay_effect} (expected SUPPORTIVE/NEUTRAL)")
        else:
            print(f"ℹ️ Current regime is {dominance_state}, BTC overlay_effect={overlay_effect}")

    def test_sol_alt_in_btc_dom_should_be_hostile(self):
        """SOL (ALT) in BTC_DOM regime should have HOSTILE overlay effect"""
        response = requests.get(f"{BASE_URL}/api/trading-product/SOL")
        assert response.status_code == 200
        
        data = response.json()
        product_data = data.get("data", {})
        
        dominance_state = product_data.get("dominance_state")
        overlay_effect = product_data.get("overlay_effect")
        action = product_data.get("final_action")
        
        # If dominance is BTC_DOM and there's an active signal, ALT should be HOSTILE
        if dominance_state == "BTC_DOM" and action not in ["BLOCK", "WAIT"]:
            assert overlay_effect == "HOSTILE", \
                f"SOL (ALT) in BTC_DOM with action {action} should be HOSTILE, got {overlay_effect}"
            print(f"✅ SOL in BTC_DOM: overlay_effect={overlay_effect} (expected HOSTILE)")
        elif action in ["BLOCK", "WAIT"]:
            # For blocked/wait actions, overlay is NEUTRAL
            assert overlay_effect == "NEUTRAL", \
                f"SOL with action {action} should have NEUTRAL overlay, got {overlay_effect}"
            print(f"ℹ️ SOL action is {action}, overlay_effect={overlay_effect} (NEUTRAL for blocked/wait)")
        else:
            print(f"ℹ️ Current regime is {dominance_state}, SOL overlay_effect={overlay_effect}")


class TestPositionSizingWithOverlay:
    """Test position sizing includes dominance and breadth adjustments"""

    def test_position_sizing_has_dominance_adjustment(self):
        """Position sizing response should include dominance_adjustment"""
        response = requests.get(f"{BASE_URL}/api/position-sizing/BTC")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        sizing_data = data.get("data", {})
        
        # Verify dominance and breadth adjustments exist
        assert "dominance_adjustment" in sizing_data, "Missing dominance_adjustment in position sizing"
        assert "breadth_adjustment" in sizing_data, "Missing breadth_adjustment in position sizing"
        
        # Verify they are within expected ranges
        dom_adj = sizing_data["dominance_adjustment"]
        breadth_adj = sizing_data["breadth_adjustment"]
        
        assert 0.7 <= dom_adj <= 1.3, f"dominance_adjustment {dom_adj} out of range [0.7, 1.3]"
        assert 0.6 <= breadth_adj <= 1.15, f"breadth_adjustment {breadth_adj} out of range [0.6, 1.15]"
        
        print(f"✅ Position sizing adjustments: dominance={dom_adj}, breadth={breadth_adj}")

    def test_position_sizing_formula_includes_7_multipliers(self):
        """Position sizing should include all 7 multipliers in formula"""
        response = requests.get(f"{BASE_URL}/api/position-sizing/SOL")
        assert response.status_code == 200
        
        data = response.json()
        sizing_data = data.get("data", {})
        
        # All 7 multipliers should be present
        expected_fields = [
            "base_risk",
            "risk_multiplier",
            "volatility_adjustment",
            "exchange_adjustment",
            "market_adjustment",
            "dominance_adjustment",
            "breadth_adjustment",
        ]
        
        for field in expected_fields:
            assert field in sizing_data, f"Missing {field} in position sizing"
        
        # Verify final_size_pct is result of formula
        assert "final_size_pct" in sizing_data
        
        print(f"✅ All 7 multipliers present in position sizing")
        print(f"   Final size: {sizing_data.get('final_size_pct')}%")

    def test_trading_product_position_sizing_has_adjustments(self):
        """Trading product full response should show dominance/breadth adjustments"""
        response = requests.get(f"{BASE_URL}/api/trading-product/full/BTC")
        assert response.status_code == 200
        
        data = response.json()
        full_data = data.get("data", {})
        
        position_sizing = full_data.get("position_sizing", {})
        
        assert "dominance_adjustment" in position_sizing, \
            "position_sizing in trading product should have dominance_adjustment"
        assert "breadth_adjustment" in position_sizing, \
            "position_sizing in trading product should have breadth_adjustment"
        
        print(f"✅ Trading product full response includes position sizing adjustments")


class TestExecutionModeDowngrade:
    """Test execution mode can be downgraded by overlay but signal/action is preserved"""

    def test_execution_mode_endpoint_has_overlay_info(self):
        """Execution mode should include dominance/breadth info in drivers"""
        response = requests.get(f"{BASE_URL}/api/execution-mode/SOL")
        assert response.status_code == 200
        
        data = response.json()
        exec_data = data.get("data", {})
        drivers = exec_data.get("drivers", {})
        
        # Check drivers include dominance info
        assert "dominance_regime" in drivers or "dominance_regime" in exec_data, \
            "Execution mode should include dominance_regime"
        
        print(f"✅ Execution mode includes overlay information")
        print(f"   Mode: {exec_data.get('execution_mode')}, Reason: {exec_data.get('reason')}")

    def test_execution_mode_downgrade_preserves_action(self):
        """Overlay downgrade should preserve signal/action, only modify execution mode"""
        # Get trading product to see both decision and execution
        response = requests.get(f"{BASE_URL}/api/trading-product/full/SOL")
        assert response.status_code == 200
        
        data = response.json()
        full_data = data.get("data", {})
        
        # Check that action from decision is preserved in final output
        trading_decision = full_data.get("trading_decision", {})
        decision_action = trading_decision.get("action")
        final_action = full_data.get("final_action")
        
        # Final action should match decision action - overlay doesn't change this
        assert final_action == decision_action, \
            f"Final action {final_action} should match decision action {decision_action}"
        
        print(f"✅ Overlay preserves action: decision={decision_action}, final={final_action}")


class TestMarketStructureAPI:
    """Test /api/market-structure returns dominance and breadth state"""

    def test_market_structure_dominance(self):
        """GET /api/market-structure/dominance should return dominance state"""
        response = requests.get(f"{BASE_URL}/api/market-structure/dominance")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "ok"
        
        dominance_data = data.get("data", {})
        assert "dominance_regime" in dominance_data, "Missing dominance_regime"
        assert "rotation_state" in dominance_data, "Missing rotation_state"
        
        regime = dominance_data["dominance_regime"]
        rotation = dominance_data["rotation_state"]
        
        assert regime in ["BTC_DOM", "ETH_DOM", "ALT_DOM", "BALANCED"], \
            f"Invalid dominance_regime: {regime}"
        
        print(f"✅ Market structure dominance: regime={regime}, rotation={rotation}")

    def test_market_structure_breadth(self):
        """GET /api/market-structure/breadth should return breadth state"""
        response = requests.get(f"{BASE_URL}/api/market-structure/breadth")
        assert response.status_code == 200
        
        data = response.json()
        breadth_data = data.get("data", {})
        
        assert "breadth_state" in breadth_data, "Missing breadth_state"
        
        breadth_state = breadth_data["breadth_state"]
        assert breadth_state in ["STRONG", "WEAK", "MIXED"], \
            f"Invalid breadth_state: {breadth_state}"
        
        print(f"✅ Market structure breadth: state={breadth_state}")

    def test_market_structure_state_includes_modifiers(self):
        """GET /api/market-structure/state should include all modifiers"""
        response = requests.get(f"{BASE_URL}/api/market-structure/state")
        assert response.status_code == 200
        
        data = response.json()
        state_data = data.get("data", {})
        
        # Check all modifier fields
        assert "btc_confidence_modifier" in state_data
        assert "eth_confidence_modifier" in state_data
        assert "alt_confidence_modifier" in state_data
        assert "size_modifier" in state_data
        
        print(f"✅ Market structure state modifiers: "
              f"BTC={state_data.get('btc_confidence_modifier')}, "
              f"ALT={state_data.get('alt_confidence_modifier')}")

    def test_market_structure_modifier_for_symbol(self):
        """GET /api/market-structure/modifier/{symbol} should return symbol-specific modifiers"""
        for symbol in ["BTC", "ETH", "SOL"]:
            response = requests.get(f"{BASE_URL}/api/market-structure/modifier/{symbol}")
            assert response.status_code == 200, f"Failed for {symbol}"
            
            data = response.json()
            modifiers = data.get("modifiers", {})
            
            assert "confidence_modifier" in modifiers
            assert "size_modifier" in modifiers
            assert "dominance_regime" in modifiers
            assert "breadth_state" in modifiers
            
            print(f"✅ {symbol} modifiers: conf={modifiers['confidence_modifier']}, size={modifiers['size_modifier']}")


class TestBatchEndpoint:
    """Test batch endpoint works with new overlay fields"""

    def test_trading_product_batch_returns_overlay_fields(self):
        """GET /api/trading-product/batch should return overlay fields for all symbols"""
        response = requests.get(f"{BASE_URL}/api/trading-product/batch?symbols=BTC,ETH,SOL")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        
        for result in results:
            assert result.get("status") == "ok", f"Result for {result.get('symbol')} failed"
            
            product_data = result.get("data", {})
            symbol = result.get("symbol")
            
            # Verify overlay fields
            assert "dominance_state" in product_data, f"Missing dominance_state for {symbol}"
            assert "breadth_state" in product_data, f"Missing breadth_state for {symbol}"
            assert "overlay_effect" in product_data, f"Missing overlay_effect for {symbol}"
            
            print(f"✅ Batch {symbol}: overlay_effect={product_data['overlay_effect']}")

    def test_trading_product_summary_includes_overlay(self):
        """GET /api/trading-product/summary should include overlay in summary"""
        response = requests.get(f"{BASE_URL}/api/trading-product/summary?symbols=BTC,SOL")
        assert response.status_code == 200
        
        data = response.json()
        summary = data.get("summary", [])
        
        assert len(summary) >= 2
        
        for item in summary:
            if "error" not in item:
                # Summary dict should include overlay
                assert "overlay" in item, f"Missing overlay in summary for {item.get('symbol')}"
                print(f"✅ Summary {item.get('symbol')}: overlay={item.get('overlay')}")


class TestOverlayRules:
    """Test specific overlay rules from PHASE 14.9"""

    def test_overlay_never_blocks_allow_action(self):
        """Overlay should NEVER change ALLOW to BLOCK - key rule"""
        # Get multiple symbols to find one with ALLOW action
        for symbol in ["BTC", "ETH", "SOL", "AVAX", "DOGE"]:
            response = requests.get(f"{BASE_URL}/api/trading-product/full/{symbol}")
            if response.status_code != 200:
                continue
            
            data = response.json()
            full_data = data.get("data", {})
            
            decision = full_data.get("trading_decision", {})
            decision_action = decision.get("action")
            final_action = full_data.get("final_action")
            
            # Key rule: If decision says ALLOW, final should still be ALLOW
            if decision_action in ["ALLOW", "ALLOW_AGGRESSIVE", "ALLOW_REDUCED"]:
                assert final_action == decision_action, \
                    f"Overlay changed {symbol} action from {decision_action} to {final_action}! This is NOT allowed."
                print(f"✅ {symbol}: action {decision_action} preserved (not blocked by overlay)")

    def test_dominance_modifier_affects_confidence(self):
        """Dominance modifier should affect final confidence"""
        # Get market structure to see current modifiers
        struct_response = requests.get(f"{BASE_URL}/api/market-structure/state")
        assert struct_response.status_code == 200
        
        struct_data = struct_response.json().get("data", {})
        btc_mod = struct_data.get("btc_confidence_modifier", 1.0)
        alt_mod = struct_data.get("alt_confidence_modifier", 1.0)
        
        # In BTC_DOM, BTC modifier should be > alt modifier
        if struct_data.get("dominance", {}).get("dominance_regime") == "BTC_DOM":
            print(f"ℹ️ BTC_DOM regime: BTC mod={btc_mod}, ALT mod={alt_mod}")
            # BTC should have boost in BTC_DOM
            assert btc_mod >= alt_mod, \
                f"In BTC_DOM, BTC modifier ({btc_mod}) should be >= ALT modifier ({alt_mod})"


class TestHealthAndStatus:
    """Basic health and status checks"""

    def test_health_endpoint(self):
        """Health check should work"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
        print(f"✅ Health check passed: version={data.get('version')}")

    def test_trading_product_status(self):
        """Trading product status should work"""
        response = requests.get(f"{BASE_URL}/api/trading-product/status")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"✅ Trading product status: phase={data.get('phase')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
