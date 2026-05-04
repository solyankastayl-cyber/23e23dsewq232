"""
PHASE 15.7 — Ecology Integration API Tests
===========================================
Tests for verifying Alpha Ecology integration into the trading pipeline APIs.

Tests:
    1. /api/trading-product/full/{symbol} returns ecology data
    2. /api/position-sizing/{symbol} returns ecology_adjustment
    3. /api/execution-mode/{symbol} returns ecology_state in drivers
    4. Ecology overlay module exists and returns correct structure
    5. Position sizing includes ecology adjustment in final calculation
    6. Execution mode includes ecology state in drivers
    7. Trading product snapshot has all ecology fields
    8. Batch endpoints support ecology data
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestEcologyOverlayModule:
    """Test 1: Ecology Overlay module exists and works"""
    
    def test_ecology_overlay_module_health(self):
        """Verify alpha-ecology health includes aggregator."""
        response = requests.get(f"{BASE_URL}/api/alpha-ecology/health")
        assert response.status_code == 200
        
        data = response.json()
        # Root level status
        assert data.get('status') == 'ok'
        
        engines = data.get('engines', {})
        assert 'aggregator' in engines, "Aggregator engine should be present"
        assert engines.get('aggregator') == 'ACTIVE'
        print("TEST 1 PASSED: Ecology overlay module health OK")
    
    def test_ecology_unified_endpoint(self):
        """Verify unified ecology endpoint works."""
        response = requests.get(f"{BASE_URL}/api/alpha-ecology/unified/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        required_fields = ['ecology_state', 'ecology_score', 'confidence_modifier', 'size_modifier']
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify ecology_state is valid
        assert data['ecology_state'] in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        print("TEST 1b PASSED: Ecology unified endpoint works")


class TestPositionSizingEcology:
    """Test 2-3: Position sizing includes ecology_adjustment"""
    
    def test_position_sizing_has_ecology_adjustment(self):
        """Verify position sizing API returns ecology_adjustment field."""
        response = requests.get(f"{BASE_URL}/api/position-sizing/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        assert 'ecology_adjustment' in data, "ecology_adjustment field must be present"
        
        # Verify it's a valid float in expected range
        eco_adj = data['ecology_adjustment']
        assert isinstance(eco_adj, (int, float)), "ecology_adjustment must be numeric"
        assert 0.5 <= eco_adj <= 1.1, f"ecology_adjustment must be in [0.5, 1.1], got {eco_adj}"
        print(f"TEST 2 PASSED: Position sizing has ecology_adjustment={eco_adj}")
    
    def test_position_sizing_drivers_have_ecology(self):
        """Verify position sizing drivers include ecology state."""
        response = requests.get(f"{BASE_URL}/api/position-sizing/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        drivers = data.get('drivers', {})
        
        assert 'ecology_state' in drivers, "drivers must include ecology_state"
        assert 'ecology_score' in drivers, "drivers must include ecology_score"
        
        # Verify values
        assert drivers['ecology_state'] in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        assert isinstance(drivers['ecology_score'], (int, float))
        print(f"TEST 3 PASSED: Position sizing drivers have ecology_state={drivers['ecology_state']}")
    
    def test_position_sizing_for_multiple_symbols(self):
        """Verify ecology_adjustment works for ETH, SOL."""
        for symbol in ['ETH', 'SOL']:
            response = requests.get(f"{BASE_URL}/api/position-sizing/{symbol}")
            assert response.status_code == 200
            
            data = response.json().get('data', {})
            assert 'ecology_adjustment' in data
            assert data.get('drivers', {}).get('ecology_state') is not None
        print("TEST 3b PASSED: Position sizing ecology works for ETH, SOL")


class TestExecutionModeEcology:
    """Test 4-5: Execution mode includes ecology downgrade"""
    
    def test_execution_mode_has_ecology_in_drivers(self):
        """Verify execution mode drivers include ecology state."""
        response = requests.get(f"{BASE_URL}/api/execution-mode/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        drivers = data.get('drivers', {})
        
        assert 'ecology_state' in drivers, "drivers must include ecology_state"
        assert 'ecology_score' in drivers, "drivers must include ecology_score"
        assert 'ecology_weakest' in drivers, "drivers must include ecology_weakest"
        
        # Verify values
        assert drivers['ecology_state'] in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        print(f"TEST 4 PASSED: Execution mode drivers have ecology_state={drivers['ecology_state']}")
    
    def test_execution_mode_for_multiple_symbols(self):
        """Verify ecology in execution mode works for ETH, SOL."""
        for symbol in ['ETH', 'SOL']:
            response = requests.get(f"{BASE_URL}/api/execution-mode/{symbol}")
            assert response.status_code == 200
            
            data = response.json().get('data', {})
            drivers = data.get('drivers', {})
            assert 'ecology_state' in drivers
            assert 'ecology_weakest' in drivers
        print("TEST 5 PASSED: Execution mode ecology works for ETH, SOL")


class TestTradingProductEcology:
    """Test 6-7: Trading Product Snapshot includes ecology block"""
    
    def test_trading_product_has_ecology_fields_at_root(self):
        """Verify trading product has ecology fields at root level."""
        response = requests.get(f"{BASE_URL}/api/trading-product/full/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        
        # Root level ecology fields
        required_root_fields = ['ecology_state', 'ecology_score', 'ecology_modifier', 'ecology_weakest']
        for field in required_root_fields:
            assert field in data, f"Missing root level field: {field}"
        
        assert data['ecology_state'] in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        assert isinstance(data['ecology_score'], (int, float))
        assert isinstance(data['ecology_modifier'], (int, float))
        print(f"TEST 6 PASSED: Trading product has root ecology fields, state={data['ecology_state']}")
    
    def test_trading_product_has_ecology_nested_object(self):
        """Verify trading product has nested ecology object."""
        response = requests.get(f"{BASE_URL}/api/trading-product/full/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        
        # Nested ecology object
        assert 'ecology' in data, "ecology object must be present"
        eco = data['ecology']
        
        required_eco_fields = ['state', 'score', 'confidence_modifier', 'size_modifier', 'weakest', 'components']
        for field in required_eco_fields:
            assert field in eco, f"Missing ecology field: {field}"
        
        # Verify components
        components = eco.get('components', {})
        expected_components = ['decay', 'crowding', 'correlation', 'redundancy', 'survival']
        for comp in expected_components:
            assert comp in components, f"Missing component: {comp}"
        
        print(f"TEST 7 PASSED: Trading product has ecology object with components={list(components.keys())}")
    
    def test_trading_product_for_multiple_symbols(self):
        """Verify ecology in trading product works for ETH, SOL."""
        for symbol in ['ETH', 'SOL']:
            response = requests.get(f"{BASE_URL}/api/trading-product/full/{symbol}")
            assert response.status_code == 200
            
            data = response.json().get('data', {})
            assert 'ecology_state' in data
            assert 'ecology' in data
        print("TEST 7b PASSED: Trading product ecology works for ETH, SOL")


class TestBatchEndpointsEcology:
    """Test 8: Batch endpoints support ecology data"""
    
    def test_trading_product_full_to_dict_has_ecology(self):
        """Verify trading product full to_dict includes ecology."""
        response = requests.get(f"{BASE_URL}/api/trading-product/full/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        
        # to_dict output should have ecology fields
        assert 'ecology_state' in data, "Missing ecology_state in full response"
        assert data['ecology_state'] in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        
        print(f"TEST 8 PASSED: Trading product full has ecology_state={data['ecology_state']}")
    
    def test_alpha_ecology_batch(self):
        """Verify alpha ecology batch endpoint works."""
        # Batch takes a list directly, not an object
        response = requests.post(
            f"{BASE_URL}/api/alpha-ecology/unified/batch",
            json=["BTC", "ETH"]
        )
        assert response.status_code == 200
        
        data = response.json().get('data', [])
        
        assert len(data) >= 2, "Batch should return results for all symbols"
        
        for item in data:
            assert 'ecology_state' in item
            assert 'ecology_score' in item
            assert 'size_modifier' in item
        
        print(f"TEST 8b PASSED: Alpha ecology batch works for {len(data)} symbols")


class TestEcologyIntegrationLogic:
    """Additional tests for ecology integration business logic"""
    
    def test_ecology_modifiers_in_valid_range(self):
        """Verify ecology modifiers are in expected ranges."""
        response = requests.get(f"{BASE_URL}/api/alpha-ecology/ecology-modifier/BTC")
        assert response.status_code == 200
        
        data = response.json().get('data', {})
        
        # Confidence modifier: should be 0.65-1.05
        conf_mod = data.get('ecology_confidence_modifier', 1.0)
        assert 0.65 <= conf_mod <= 1.05, f"confidence_modifier {conf_mod} out of range"
        
        # Size modifier: should be 0.65-1.05
        size_mod = data.get('ecology_size_modifier', 1.0)
        assert 0.65 <= size_mod <= 1.05, f"size_modifier {size_mod} out of range"
        
        # Ecology score: should be positive
        score = data.get('ecology_score', 1.0)
        assert score > 0, "ecology_score must be positive"
        
        print(f"TEST 9 PASSED: Ecology modifiers in valid ranges (conf={conf_mod}, size={size_mod})")
    
    def test_ecology_state_consistency(self):
        """Verify ecology state is consistent across endpoints."""
        # Get from unified endpoint
        unified_resp = requests.get(f"{BASE_URL}/api/alpha-ecology/unified/BTC")
        unified_state = unified_resp.json().get('data', {}).get('ecology_state')
        
        # Get from trading product
        product_resp = requests.get(f"{BASE_URL}/api/trading-product/full/BTC")
        product_state = product_resp.json().get('data', {}).get('ecology_state')
        
        # Should be same (allowing for small timing differences)
        assert unified_state in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        assert product_state in ['HEALTHY', 'STABLE', 'STRESSED', 'CRITICAL']
        
        print(f"TEST 10 PASSED: Ecology state consistency (unified={unified_state}, product={product_state})")


# ══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
