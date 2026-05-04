"""
Tests for TA Setup V2 API — MTF Context Engine and Structure Visualization
===========================================================================

Tests:
1. MTF Context fields (global_bias, local_context, alignment, confidence, summary, tf_breakdown)
2. Structure Visualization (pivot_points, events arrays)
3. Multiple symbols (BTCUSDT, ETHUSDT)
4. Multiple timeframes (1D, 7D, 30D)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com')


class TestTASetupV2API:
    """Tests for /api/ta/setup/v2 endpoint"""
    
    def test_btcusdt_1d_mtf_context_structure(self):
        """Test BTCUSDT 1D returns mtf_context with all required fields"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1d")
        
        assert response.status_code == 200
        data = response.json()
        
        # MTF Context must exist
        assert 'mtf_context' in data, "mtf_context missing from response"
        mtf = data['mtf_context']
        
        # Required MTF fields
        assert 'global_bias' in mtf, "global_bias missing from mtf_context"
        assert 'local_context' in mtf, "local_context missing from mtf_context"
        assert 'alignment' in mtf, "alignment missing from mtf_context"
        assert 'confidence' in mtf, "confidence missing from mtf_context"
        assert 'summary' in mtf, "summary missing from mtf_context"
        assert 'tf_breakdown' in mtf, "tf_breakdown missing from mtf_context"
        
        # Validate field types and values
        assert mtf['global_bias'] in ['bullish', 'bearish', 'neutral'], f"Invalid global_bias: {mtf['global_bias']}"
        assert mtf['alignment'] in ['full_bullish', 'full_bearish', 'mixed', 'neutral'], f"Invalid alignment: {mtf['alignment']}"
        assert isinstance(mtf['confidence'], (int, float)), "confidence should be numeric"
        assert 0 <= mtf['confidence'] <= 1, f"confidence should be 0-1, got {mtf['confidence']}"
        assert isinstance(mtf['summary'], str), "summary should be string"
        assert len(mtf['summary']) > 0, "summary should not be empty"
        
        # TF Breakdown structure
        assert isinstance(mtf['tf_breakdown'], dict), "tf_breakdown should be dict"
        for tf, breakdown in mtf['tf_breakdown'].items():
            assert 'bias' in breakdown, f"bias missing from tf_breakdown[{tf}]"
            assert 'regime' in breakdown, f"regime missing from tf_breakdown[{tf}]"
            assert 'last_event' in breakdown, f"last_event missing from tf_breakdown[{tf}]"
        
        print(f"BTCUSDT 1D MTF Context: global_bias={mtf['global_bias']}, alignment={mtf['alignment']}, confidence={mtf['confidence']}")

    def test_btcusdt_1d_structure_visualization(self):
        """Test BTCUSDT 1D returns structure_visualization with pivot_points and events"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1d")
        
        assert response.status_code == 200
        data = response.json()
        
        # Structure Visualization must exist
        assert 'structure_visualization' in data, "structure_visualization missing from response"
        viz = data['structure_visualization']
        
        # Required fields
        assert 'pivot_points' in viz, "pivot_points missing from structure_visualization"
        assert 'events' in viz, "events missing from structure_visualization"
        
        # Validate pivot_points array
        assert isinstance(viz['pivot_points'], list), "pivot_points should be a list"
        if len(viz['pivot_points']) > 0:
            pivot = viz['pivot_points'][0]
            assert 'time' in pivot, "pivot point missing time field"
            assert 'price' in pivot, "pivot point missing price field"
            assert 'label' in pivot, "pivot point missing label field"
            assert 'kind' in pivot, "pivot point missing kind field"
            assert pivot['label'] in ['HH', 'HL', 'LH', 'LL'], f"Invalid pivot label: {pivot['label']}"
            assert pivot['kind'] in ['high', 'low'], f"Invalid pivot kind: {pivot['kind']}"
        
        # Validate events array
        assert isinstance(viz['events'], list), "events should be a list"
        for event in viz['events']:
            assert 'type' in event, "event missing type field"
            assert 'time' in event, "event missing time field"
            assert 'label' in event, "event missing label field"
            assert event['type'] in ['choch_up', 'choch_down', 'bos_up', 'bos_down'], f"Invalid event type: {event['type']}"
        
        print(f"BTCUSDT 1D Structure: {len(viz['pivot_points'])} pivots, {len(viz['events'])} events")

    def test_ethusdt_7d_mtf_context(self):
        """Test ETHUSDT 7D returns mtf_context"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=ETHUSDT&tf=7d")
        
        assert response.status_code == 200
        data = response.json()
        
        # MTF Context must exist
        assert 'mtf_context' in data, "mtf_context missing from ETHUSDT 7D response"
        mtf = data['mtf_context']
        
        # All required fields
        assert 'global_bias' in mtf
        assert 'local_context' in mtf
        assert 'alignment' in mtf
        assert 'confidence' in mtf
        assert 'summary' in mtf
        assert 'tf_breakdown' in mtf
        
        print(f"ETHUSDT 7D MTF Context: global_bias={mtf['global_bias']}, alignment={mtf['alignment']}")

    def test_btcusdt_multiple_timeframes(self):
        """Test BTCUSDT returns valid data for all timeframes"""
        timeframes = ['4h', '1d', '7d', '30d']
        
        for tf in timeframes:
            response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf={tf}")
            
            assert response.status_code == 200, f"Failed for timeframe {tf}"
            data = response.json()
            
            assert 'candles' in data, f"candles missing for {tf}"
            assert 'mtf_context' in data, f"mtf_context missing for {tf}"
            assert 'structure_visualization' in data, f"structure_visualization missing for {tf}"
            assert len(data['candles']) > 0, f"No candles returned for {tf}"
            
            print(f"BTCUSDT {tf}: {len(data['candles'])} candles, mtf_context present")

    def test_structure_context_fields(self):
        """Test structure_context contains bias and regime"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1d")
        
        assert response.status_code == 200
        data = response.json()
        
        # Structure context
        assert 'structure_context' in data
        ctx = data['structure_context']
        
        assert 'bias' in ctx, "bias missing from structure_context"
        assert 'regime' in ctx, "regime missing from structure_context"
        
        assert ctx['bias'] in ['bullish', 'bearish', 'neutral']
        print(f"Structure Context: bias={ctx['bias']}, regime={ctx['regime']}")

    def test_base_layer_supports_resistances(self):
        """Test base_layer contains supports and resistances"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1d")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'base_layer' in data
        bl = data['base_layer']
        
        assert 'supports' in bl
        assert 'resistances' in bl
        assert 'trendlines' in bl
        assert 'channels' in bl
        
        assert isinstance(bl['supports'], list)
        assert isinstance(bl['resistances'], list)
        
        print(f"Base Layer: {len(bl['supports'])} supports, {len(bl['resistances'])} resistances")

    def test_candles_data_format(self):
        """Test candles have correct format with OHLCV data"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1d")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'candles' in data
        assert len(data['candles']) > 0
        
        candle = data['candles'][0]
        assert 'time' in candle
        assert 'open' in candle
        assert 'high' in candle
        assert 'low' in candle
        assert 'close' in candle
        assert 'volume' in candle
        
        # Validate numeric types
        assert isinstance(candle['time'], int)
        assert isinstance(candle['open'], (int, float))
        assert isinstance(candle['high'], (int, float))
        
        print(f"Candles format OK: {len(data['candles'])} candles")


class TestHealthEndpoint:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("Health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
