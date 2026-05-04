"""
Test TA Setup V2 - Structure-First Architecture
================================================

Tests the refactored TA engine with:
- Structure Engine V2 (runs BEFORE pattern detection)
- Structure gating (patterns rejected by incompatible regimes)
- Base layer (supports, resistances, trendlines, channels) always visible
- Hardened pattern filters (min 4 touches, recency checks)
- Decision engine includes regime, market_phase, last_event
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com')


class TestHealthEndpoint:
    """Health check tests"""
    
    def test_health_returns_ok(self):
        """Test health endpoint returns ok=true"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        print(f"✓ Health check passed: {data}")


class TestStructureContextV2:
    """Tests for structure_context with V2 fields"""
    
    def test_structure_context_has_v2_fields_btc_1d(self):
        """Test structure_context returns all V2 fields for BTCUSDT 1D"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        assert response.status_code == 200
        data = response.json()
        
        ctx = data.get("structure_context")
        assert ctx is not None, "structure_context should not be None"
        
        # Check all V2 fields exist
        required_fields = [
            "bias", "regime", "market_phase", "last_event",
            "hh_count", "hl_count", "lh_count", "ll_count",
            "structure_score", "active_supports", "active_resistances",
            "active_trendlines", "active_channels", "notes"
        ]
        
        for field in required_fields:
            assert field in ctx, f"Missing field '{field}' in structure_context"
        
        # Check types
        assert ctx["bias"] in ["bullish", "bearish", "neutral"]
        assert ctx["regime"] in ["trend_up", "trend_down", "range", "compression", "expansion", "accumulation", "distribution", "reversal_candidate", "unknown"]
        assert ctx["market_phase"] in ["markup", "markdown", "range", "compression", "accumulation", "distribution", "unknown"]
        assert ctx["last_event"] in ["bos_up", "bos_down", "choch_up", "choch_down", "none"]
        
        # Check numeric fields
        assert isinstance(ctx["hh_count"], int)
        assert isinstance(ctx["hl_count"], int)
        assert isinstance(ctx["lh_count"], int)
        assert isinstance(ctx["ll_count"], int)
        assert isinstance(ctx["structure_score"], float)
        
        # Check array fields
        assert isinstance(ctx["active_supports"], list)
        assert isinstance(ctx["active_resistances"], list)
        assert isinstance(ctx["active_trendlines"], list)
        assert isinstance(ctx["active_channels"], list)
        assert isinstance(ctx["notes"], list)
        
        print(f"✓ Structure context V2 fields verified: bias={ctx['bias']}, regime={ctx['regime']}, phase={ctx['market_phase']}, event={ctx['last_event']}")


class TestBaseLayer:
    """Tests for base_layer object"""
    
    def test_base_layer_returns_required_arrays_btc_1d(self):
        """Test base_layer returns supports, resistances, trendlines, channels arrays"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        assert response.status_code == 200
        data = response.json()
        
        base_layer = data.get("base_layer")
        assert base_layer is not None, "base_layer should not be None"
        
        # Check all required arrays exist
        assert "supports" in base_layer
        assert "resistances" in base_layer
        assert "trendlines" in base_layer
        assert "channels" in base_layer
        
        assert isinstance(base_layer["supports"], list)
        assert isinstance(base_layer["resistances"], list)
        assert isinstance(base_layer["trendlines"], list)
        assert isinstance(base_layer["channels"], list)
        
        print(f"✓ Base layer structure verified: {len(base_layer['supports'])} supports, {len(base_layer['resistances'])} resistances, {len(base_layer['trendlines'])} trendlines, {len(base_layer['channels'])} channels")
    
    def test_base_layer_support_structure(self):
        """Test support objects have correct structure"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        supports = data.get("base_layer", {}).get("supports", [])
        if len(supports) > 0:
            support = supports[0]
            assert "price" in support
            assert "strength" in support or "touches" in support
            assert "type" in support
            assert support["type"] == "support"
            print(f"✓ Support structure verified: price={support['price']}")
        else:
            print("✓ No supports found (acceptable for some market conditions)")
    
    def test_base_layer_trendline_structure(self):
        """Test trendline objects have correct structure"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        trendlines = data.get("base_layer", {}).get("trendlines", [])
        if len(trendlines) > 0:
            tl = trendlines[0]
            assert "type" in tl  # uptrend / downtrend
            assert "direction" in tl  # bullish / bearish
            assert "start" in tl
            assert "end" in tl
            assert "time" in tl["start"]
            assert "value" in tl["start"]
            print(f"✓ Trendline structure verified: type={tl['type']}, direction={tl['direction']}")
        else:
            print("✓ No trendlines found (acceptable for some market conditions)")


class TestDecisionEngine:
    """Tests for decision engine including regime/phase/event"""
    
    def test_decision_includes_regime_phase_event(self):
        """Test decision response includes regime, market_phase, last_event"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        assert response.status_code == 200
        data = response.json()
        
        decision = data.get("decision")
        assert decision is not None, "decision should not be None"
        
        # Check required decision fields
        assert "bias" in decision
        assert "regime" in decision
        assert "market_phase" in decision
        assert "last_event" in decision
        assert "confidence" in decision
        
        # Validate types
        assert decision["bias"] in ["bullish", "bearish", "neutral"]
        assert isinstance(decision["confidence"], float)
        
        print(f"✓ Decision verified: bias={decision['bias']}, regime={decision['regime']}, phase={decision['market_phase']}, event={decision['last_event']}, confidence={decision['confidence']}")


class TestScenariosBlock:
    """Tests for scenarios generation"""
    
    def test_scenarios_structure_when_no_pattern(self):
        """Test scenarios show structure-based insight when no pattern detected"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        scenarios = data.get("scenarios", [])
        assert isinstance(scenarios, list), "scenarios should be a list"
        assert len(scenarios) > 0, "scenarios should not be empty"
        
        # Check scenario structure
        scenario = scenarios[0]
        assert "type" in scenario
        assert "title" in scenario
        assert "direction" in scenario
        assert "probability" in scenario
        assert "summary" in scenario
        assert "action" in scenario
        
        # When no primary pattern, type should be 'structure' (not 'primary')
        primary_pattern = data.get("primary_pattern")
        if primary_pattern is None:
            assert scenario["type"] == "structure", "Scenario type should be 'structure' when no pattern detected"
            print(f"✓ Structure-based scenario verified: type={scenario['type']}, title='{scenario['title']}'")
        else:
            print(f"✓ Primary scenario verified: type={scenario['type']}, title='{scenario['title']}'")


class TestDifferentTimeframes:
    """Tests for different timeframes"""
    
    def test_1d_timeframe(self):
        """Test 1D timeframe returns proper analysis"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        assert response.status_code == 200
        data = response.json()
        
        assert data["timeframe"] == "1D"
        assert data["scale_config"]["lookback"] == 150
        assert len(data["candles"]) <= 150
        assert data.get("structure_context") is not None
        print(f"✓ 1D timeframe: {len(data['candles'])} candles, lookback={data['scale_config']['lookback']}")
    
    def test_7d_timeframe(self):
        """Test 7D timeframe returns proper analysis"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=7D")
        assert response.status_code == 200
        data = response.json()
        
        assert data["timeframe"] == "7D"
        assert data["scale_config"]["lookback"] == 400
        assert len(data["candles"]) <= 400
        assert data.get("structure_context") is not None
        print(f"✓ 7D timeframe: {len(data['candles'])} candles, lookback={data['scale_config']['lookback']}")
    
    def test_30d_timeframe(self):
        """Test 30D timeframe returns proper analysis"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=30D")
        assert response.status_code == 200
        data = response.json()
        
        assert data["timeframe"] == "30D"
        assert data["scale_config"]["lookback"] == 800
        assert len(data["candles"]) <= 800
        assert data.get("structure_context") is not None
        print(f"✓ 30D timeframe: {len(data['candles'])} candles, lookback={data['scale_config']['lookback']}")


class TestDifferentSymbols:
    """Tests for different symbols"""
    
    def test_ethusdt_works(self):
        """Test ETHUSDT returns proper analysis"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=ETHUSDT&tf=1D")
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "ETHUSDT"
        assert data.get("structure_context") is not None
        assert data.get("base_layer") is not None
        assert len(data["candles"]) > 0
        print(f"✓ ETHUSDT: {len(data['candles'])} candles, bias={data['structure_context']['bias']}")
    
    def test_solusdt_works(self):
        """Test SOLUSDT returns proper analysis"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=SOLUSDT&tf=1D")
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "SOLUSDT"
        assert data.get("structure_context") is not None
        print(f"✓ SOLUSDT: {len(data['candles'])} candles, bias={data['structure_context']['bias']}")


class TestStructureGating:
    """Tests for structure gating (hard rejection of patterns incompatible with regime)"""
    
    def test_meta_shows_gating_stats(self):
        """Test meta includes structure_gate statistics"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        meta = data.get("meta", {})
        
        # These fields should show the filtering pipeline
        assert "total_candidates" in meta
        assert "after_structure_gate" in meta
        
        print(f"✓ Structure gating meta: total={meta['total_candidates']}, after_gate={meta['after_structure_gate']}, rejected={meta.get('rejected', 0)}")
    
    def test_pipeline_filtering_stats(self):
        """Test that filtering pipeline shows progressive reduction"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        meta = data.get("meta", {})
        
        total = meta.get("total_candidates", 0)
        after_validation = meta.get("after_validation", total)
        after_expiration = meta.get("after_expiration", after_validation)
        after_structure = meta.get("after_structure_gate", after_expiration)
        after_recency = meta.get("after_recency_filter", after_structure)
        
        # Pipeline should progressively filter (or stay same if all pass)
        assert after_validation <= total
        assert after_expiration <= after_validation
        assert after_structure <= after_expiration
        assert after_recency <= after_structure
        
        print(f"✓ Pipeline filtering verified: {total} → {after_validation} → {after_expiration} → {after_structure} → {after_recency}")


class TestHardenedPatternFilters:
    """Tests for hardened pattern filters (min 4 touches, recency checks)"""
    
    def test_pattern_has_min_touches_when_present(self):
        """Test that any returned pattern has at least 4 touches (hardened rule)"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        primary = data.get("primary_pattern")
        if primary is not None:
            touch_count = primary.get("touch_count", 0)
            # Hardened filter: min 4 touches
            assert touch_count >= 4, f"Pattern should have >= 4 touches, got {touch_count}"
            print(f"✓ Pattern touch count verified: {touch_count} touches")
        else:
            # No pattern is acceptable (structure-first approach)
            print("✓ No pattern detected (acceptable - hardened filters working)")
    
    def test_alternative_patterns_validation(self):
        """Test that alternative patterns also meet hardened criteria"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        alternatives = data.get("alternative_patterns", [])
        for i, alt in enumerate(alternatives):
            touch_count = alt.get("touch_count", 0)
            assert touch_count >= 4, f"Alternative {i} should have >= 4 touches, got {touch_count}"
        
        print(f"✓ {len(alternatives)} alternative patterns validated")


class TestConfidenceExplanation:
    """Tests for confidence explanation"""
    
    def test_confidence_explanation_returned(self):
        """Test confidence_explanation field is returned"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        conf_exp = data.get("confidence_explanation")
        assert conf_exp is not None, "confidence_explanation should exist"
        assert isinstance(conf_exp, dict), "confidence_explanation should be a dict"
        
        print(f"✓ Confidence explanation returned: {list(conf_exp.keys()) if conf_exp else 'empty'}")


class TestSelectionExplanation:
    """Tests for selection explanation"""
    
    def test_selection_explanation_status(self):
        """Test selection_explanation has status field"""
        response = requests.get(f"{BASE_URL}/api/ta/setup/v2?symbol=BTCUSDT&tf=1D")
        data = response.json()
        
        sel_exp = data.get("selection_explanation", {})
        assert "status" in sel_exp, "selection_explanation should have status"
        
        print(f"✓ Selection explanation status: {sel_exp.get('status')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
