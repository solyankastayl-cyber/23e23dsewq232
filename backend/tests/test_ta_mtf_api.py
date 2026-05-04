"""
Test suite for TA Engine MTF API endpoints
Tests: health, status, mtf endpoint with various timeframes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndStatus:
    """Health and status endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('ok') == True
        print(f"✓ Health check passed: {data.get('mode')}")
    
    def test_ta_engine_status(self):
        """Test /api/ta-engine/status returns active components"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/status")
        assert response.status_code == 200
        data = response.json()
        assert data.get('ok') == True
        assert 'components' in data
        print(f"✓ TA Engine status: v{data.get('version')}, phase: {data.get('phase')}")


class TestMTFEndpoint:
    """MTF (Multi-Timeframe) endpoint tests"""
    
    def test_mtf_btc_1d_returns_primary_pattern(self):
        """Test /api/ta-engine/mtf/BTC?timeframes=1D returns primary_pattern with points"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=1D", timeout=45)
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data.get('ok') == True
        assert 'tf_map' in data
        assert '1D' in data['tf_map']
        
        tf_data = data['tf_map']['1D']
        
        # Verify primary_pattern exists with required fields
        primary_pattern = tf_data.get('primary_pattern')
        assert primary_pattern is not None, "primary_pattern should exist"
        assert 'type' in primary_pattern, "primary_pattern should have type"
        assert 'points' in primary_pattern, "primary_pattern should have points"
        
        # Check points structure
        points_data = primary_pattern.get('points', {})
        if isinstance(points_data, dict) and 'points' in points_data:
            assert len(points_data['points']) >= 2, "Pattern should have at least 2 points"
        
        # Check breakout and invalidation levels
        assert 'breakout_level' in primary_pattern or 'breakout' in primary_pattern
        assert 'invalidation' in primary_pattern or 'invalidation_level' in primary_pattern
        
        print(f"✓ 1D primary_pattern: {primary_pattern.get('type')}, "
              f"breakout: {primary_pattern.get('breakout_level')}")
    
    def test_mtf_btc_4h_returns_poi_and_liquidity(self):
        """Test /api/ta-engine/mtf/BTC?timeframes=4H returns POI zones and liquidity"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H", timeout=45)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('ok') == True
        assert '4H' in data['tf_map']
        
        tf_data = data['tf_map']['4H']
        
        # Verify POI zones exist
        poi = tf_data.get('poi')
        assert poi is not None, "POI data should exist"
        zones = poi.get('zones', [])
        assert len(zones) > 0, "Should have at least 1 POI zone"
        
        # Check POI zone structure
        first_zone = zones[0]
        assert 'type' in first_zone, "POI zone should have type"
        assert first_zone['type'] in ['demand', 'supply'], f"POI type should be demand/supply, got: {first_zone['type']}"
        assert 'price_high' in first_zone
        assert 'price_low' in first_zone
        
        # Verify liquidity data exists
        liquidity = tf_data.get('liquidity')
        assert liquidity is not None, "Liquidity data should exist"
        pools = liquidity.get('pools', [])
        assert len(pools) > 0, "Should have at least 1 liquidity pool"
        
        print(f"✓ 4H data: {len(zones)} POI zones, {len(pools)} liquidity pools")
        print(f"  First POI: {first_zone.get('type')} @ {first_zone.get('price_mid'):.2f}")
    
    def test_mtf_btc_1h_returns_valid_structure(self):
        """Test /api/ta-engine/mtf/BTC?timeframes=1H returns valid data structure"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=1H", timeout=45)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('ok') == True
        assert '1H' in data['tf_map']
        
        tf_data = data['tf_map']['1H']
        
        # Check essential fields exist
        assert 'candles' in tf_data
        assert 'decision' in tf_data
        assert len(tf_data['candles']) > 0, "Should have candle data"
        
        print(f"✓ 1H data: {len(tf_data['candles'])} candles")
    
    def test_decision_has_bias_field(self):
        """Test that decision object contains bias information"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H", timeout=45)
        assert response.status_code == 200
        data = response.json()
        
        decision = data['tf_map']['4H'].get('decision', {})
        
        # Decision should have bias or direction
        has_bias = 'bias' in decision or 'direction' in decision
        assert has_bias, "Decision should have bias or direction field"
        
        bias_value = decision.get('bias') or decision.get('direction')
        assert bias_value in ['bullish', 'bearish', 'neutral', None], \
            f"Bias should be bullish/bearish/neutral, got: {bias_value}"
        
        print(f"✓ Decision bias: {bias_value}, confidence: {decision.get('confidence')}")


class TestStructureAndLevels:
    """Structure context and levels tests"""
    
    def test_structure_context_exists(self):
        """Test that structure_context is present in response"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=1D", timeout=45)
        assert response.status_code == 200
        data = response.json()
        
        tf_data = data['tf_map']['1D']
        
        # Either structure_context or structure_state should exist
        has_structure = 'structure_context' in tf_data or 'structure_state' in tf_data
        assert has_structure, "Response should have structure data"
        
        structure = tf_data.get('structure_context') or tf_data.get('structure_state', {})
        print(f"✓ Structure data present: {list(structure.keys())[:5]}...")
    
    def test_execution_plan_exists(self):
        """Test that execution data is present"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=1D", timeout=45)
        assert response.status_code == 200
        data = response.json()
        
        tf_data = data['tf_map']['1D']
        
        # Check for execution or trade_setup
        has_execution = 'execution' in tf_data or 'trade_setup' in tf_data
        assert has_execution, "Response should have execution/trade_setup data"
        
        execution = tf_data.get('execution') or tf_data.get('trade_setup', {})
        print(f"✓ Execution data present")


class TestDifferentSymbols:
    """Test API with different symbols"""
    
    def test_eth_symbol(self):
        """Test API with ETH symbol"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/ETH?timeframes=4H", timeout=45)
        assert response.status_code == 200
        data = response.json()
        assert data.get('ok') == True
        assert data.get('symbol') == 'ETH'
        print(f"✓ ETH symbol works")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
