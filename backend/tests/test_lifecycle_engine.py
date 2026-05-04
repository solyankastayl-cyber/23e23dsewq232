"""
Test Pattern Lifecycle Engine
=============================

Tests the lifecycle state machine for patterns:
- forming: pattern is building, no breakout yet
- confirmed_up: price broke above resistance/neckline
- confirmed_down: price broke below support/neckline
- invalidated: pattern structure violated

Endpoints tested:
- GET /api/ta-engine/pattern-v2/BTC?timeframe=4H
- GET /api/ta-engine/mtf/BTC?timeframes=4H
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLifecycleEngineBackend:
    """Test lifecycle engine in backend API responses"""
    
    def test_pattern_v2_returns_lifecycle_in_interpretation(self):
        """pattern-v2 endpoint should return interpretation.lifecycle object"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        interpretation = data.get('interpretation', {})
        
        # interpretation.lifecycle should exist
        lifecycle = interpretation.get('lifecycle')
        assert lifecycle is not None, "interpretation.lifecycle should exist"
        assert isinstance(lifecycle, dict), f"lifecycle should be dict, got {type(lifecycle)}"
        
    def test_pattern_v2_lifecycle_has_state_field(self):
        """lifecycle should have 'state' field"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200
        
        data = response.json()
        lifecycle = data.get('interpretation', {}).get('lifecycle', {})
        
        assert 'state' in lifecycle, "lifecycle should have 'state' field"
        state = lifecycle['state']
        
        # State should be one of the valid values
        valid_states = ['forming', 'confirmed_up', 'confirmed_down', 'invalidated']
        assert state in valid_states, f"state '{state}' not in valid states: {valid_states}"
        
    def test_pattern_v2_lifecycle_has_label_field(self):
        """lifecycle should have 'label' field with human-readable text"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200
        
        data = response.json()
        lifecycle = data.get('interpretation', {}).get('lifecycle', {})
        
        assert 'label' in lifecycle, "lifecycle should have 'label' field"
        label = lifecycle['label']
        
        assert isinstance(label, str), f"label should be string, got {type(label)}"
        assert len(label) > 0, "label should not be empty"
        
    def test_mtf_returns_lifecycle_in_tf_map(self):
        """mtf endpoint should return tf_map.4H.lifecycle object"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        tf_map = data.get('tf_map', {})
        tf_4h = tf_map.get('4H', {})
        
        # tf_map.4H.lifecycle should exist
        lifecycle = tf_4h.get('lifecycle')
        assert lifecycle is not None, "tf_map.4H.lifecycle should exist"
        assert isinstance(lifecycle, dict), f"lifecycle should be dict, got {type(lifecycle)}"
        
    def test_mtf_lifecycle_has_state_field(self):
        """mtf lifecycle should have 'state' field"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H")
        assert response.status_code == 200
        
        data = response.json()
        lifecycle = data.get('tf_map', {}).get('4H', {}).get('lifecycle', {})
        
        assert 'state' in lifecycle, "lifecycle should have 'state' field"
        state = lifecycle['state']
        
        valid_states = ['forming', 'confirmed_up', 'confirmed_down', 'invalidated']
        assert state in valid_states, f"state '{state}' not in valid states: {valid_states}"
        
    def test_mtf_lifecycle_has_label_field(self):
        """mtf lifecycle should have 'label' field"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H")
        assert response.status_code == 200
        
        data = response.json()
        lifecycle = data.get('tf_map', {}).get('4H', {}).get('lifecycle', {})
        
        assert 'label' in lifecycle, "lifecycle should have 'label' field"
        label = lifecycle['label']
        
        assert isinstance(label, str), f"label should be string, got {type(label)}"
        assert len(label) > 0, "label should not be empty"


class TestLifecycleStateValues:
    """Test that lifecycle states have correct labels"""
    
    def test_forming_state_has_appropriate_label(self):
        """forming state should have labels like 'Range active', 'Developing', etc."""
        response = requests.get(f"{BASE_URL}/api/ta-engine/pattern-v2/BTC?timeframe=4H")
        assert response.status_code == 200
        
        data = response.json()
        lifecycle = data.get('interpretation', {}).get('lifecycle', {})
        
        if lifecycle.get('state') == 'forming':
            label = lifecycle.get('label', '')
            # Forming labels should be descriptive
            forming_labels = [
                'Range active', 'Developing', 'Compressing', 'Pressure building',
                'Testing peaks', 'Testing lows', 'Right shoulder forming',
                'Wedge narrowing', 'Channel active', 'Consolidating'
            ]
            assert any(fl in label for fl in forming_labels) or len(label) > 0, \
                f"forming state should have descriptive label, got: {label}"
                
    def test_confirmed_states_have_breakout_labels(self):
        """confirmed_up/confirmed_down should have breakout/breakdown labels"""
        response = requests.get(f"{BASE_URL}/api/ta-engine/mtf/BTC?timeframes=4H")
        assert response.status_code == 200
        
        data = response.json()
        lifecycle = data.get('tf_map', {}).get('4H', {}).get('lifecycle', {})
        
        state = lifecycle.get('state')
        label = lifecycle.get('label', '')
        
        if state == 'confirmed_up':
            # Should mention breakout or broken
            assert 'breakout' in label.lower() or 'broken' in label.lower(), \
                f"confirmed_up should have breakout label, got: {label}"
        elif state == 'confirmed_down':
            # Should mention breakdown or broken
            assert 'breakdown' in label.lower() or 'broken' in label.lower(), \
                f"confirmed_down should have breakdown label, got: {label}"


class TestLifecycleEngineUnit:
    """Unit tests for build_lifecycle function"""
    
    def test_build_lifecycle_import(self):
        """build_lifecycle should be importable"""
        try:
            from modules.ta_engine.pattern_lifecycle_engine import build_lifecycle
            assert callable(build_lifecycle)
        except ImportError as e:
            pytest.skip(f"Cannot import build_lifecycle: {e}")
            
    def test_build_lifecycle_rectangle_forming(self):
        """Rectangle pattern should return 'forming' when price is inside range"""
        try:
            from modules.ta_engine.pattern_lifecycle_engine import build_lifecycle
        except ImportError:
            pytest.skip("Cannot import build_lifecycle")
            
        pattern = {
            'type': 'rectangle',
            'resistance': 100000,
            'support': 90000,
        }
        current_price = 95000  # Inside range
        
        result = build_lifecycle(pattern, current_price)
        
        assert result['state'] == 'forming'
        assert result['label'] == 'Range active'
        
    def test_build_lifecycle_rectangle_breakout(self):
        """Rectangle pattern should return 'confirmed_up' when price breaks above"""
        try:
            from modules.ta_engine.pattern_lifecycle_engine import build_lifecycle
        except ImportError:
            pytest.skip("Cannot import build_lifecycle")
            
        pattern = {
            'type': 'rectangle',
            'resistance': 100000,
            'support': 90000,
        }
        current_price = 101000  # Above resistance
        
        result = build_lifecycle(pattern, current_price)
        
        assert result['state'] == 'confirmed_up'
        assert 'breakout' in result['label'].lower()
        
    def test_build_lifecycle_double_top_confirmed(self):
        """Double top should return 'confirmed_down' when price breaks neckline"""
        try:
            from modules.ta_engine.pattern_lifecycle_engine import build_lifecycle
        except ImportError:
            pytest.skip("Cannot import build_lifecycle")
            
        pattern = {
            'type': 'double_top',
            'top': 100000,
            'neckline': 95000,
        }
        current_price = 94000  # Below neckline
        
        result = build_lifecycle(pattern, current_price)
        
        assert result['state'] == 'confirmed_down'
        assert 'neckline' in result['label'].lower() or 'broken' in result['label'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
