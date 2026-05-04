"""
PHASE 13.8 — Exchange Intelligence Module Tests
=================================================
Comprehensive tests for the Exchange Intelligence Module API endpoints.
Tests all 6 engines and their signal outputs, plus context aggregation.
"""

import pytest
import requests
import os
from datetime import datetime


# Use external URL for testing (what users actually see)
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://tech-analysis-core-1.preview.emergentagent.com"


# ============================================
# Test Session Fixture
# ============================================

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ============================================
# Engine Status Tests (Health Check)
# ============================================

class TestEngineStatus:
    """Test /api/exchange-intelligence/engines/status endpoint"""

    def test_engines_status_returns_ok(self, api_client):
        """Verify engines status returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/engines/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Engine status returns ok=true")

    def test_engines_status_has_all_six_engines(self, api_client):
        """Verify all 6 engines are listed as active"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/engines/status")
        assert response.status_code == 200
        data = response.json()
        
        engines = data.get("engines", {})
        expected_engines = [
            "funding_oi", "derivatives_pressure", "liquidation",
            "exchange_flow", "exchange_volume", "context_aggregator"
        ]
        
        for engine in expected_engines:
            assert engine in engines, f"Missing engine: {engine}"
            assert engines[engine] == "active", f"Engine {engine} is not active"
        
        print(f"✅ All 6 engines active: {list(engines.keys())}")

    def test_engines_status_candles_available(self, api_client):
        """Verify candles data source is available"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/engines/status")
        assert response.status_code == 200
        data = response.json()
        
        data_sources = data.get("data_sources", {})
        assert data_sources.get("candles") == "available", "Candles should be available"
        print(f"✅ Candles data source: {data_sources.get('candles')}")

    def test_engines_status_has_version_and_module(self, api_client):
        """Verify module metadata is present"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/engines/status")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("module") == "exchange_intelligence"
        assert "version" in data
        assert "timestamp" in data
        print(f"✅ Module: {data.get('module')}, Version: {data.get('version')}")


# ============================================
# Exchange Context Tests (Main Aggregator)
# ============================================

class TestExchangeContext:
    """Test /api/exchange-intelligence/context/{symbol} endpoint"""

    def test_context_btc_returns_ok(self, api_client):
        """Verify context endpoint returns ok=true for BTC"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Context BTC returns ok=true")

    def test_context_has_exchange_bias_field(self, api_client):
        """Verify exchange_bias field is present and valid (BULLISH/BEARISH/NEUTRAL)"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert response.status_code == 200
        data = response.json()
        
        context = data.get("context", {})
        assert "exchange_bias" in context, "Missing exchange_bias field"
        
        valid_biases = ["BULLISH", "BEARISH", "NEUTRAL"]
        assert context["exchange_bias"] in valid_biases, \
            f"Invalid bias: {context['exchange_bias']}"
        print(f"✅ Exchange bias: {context['exchange_bias']}")

    def test_context_has_all_sub_signals(self, api_client):
        """Verify all 5 sub-signal details are present"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert response.status_code == 200
        data = response.json()
        
        context = data.get("context", {})
        required_details = [
            "funding_detail", "derivatives_detail", "liquidation_detail",
            "flow_detail", "volume_detail"
        ]
        
        for detail in required_details:
            assert detail in context, f"Missing {detail}"
            assert isinstance(context[detail], dict), f"{detail} should be a dict"
        
        print(f"✅ All 5 sub-signal details present")

    def test_context_confidence_between_0_and_1(self, api_client):
        """Verify confidence value is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert response.status_code == 200
        data = response.json()
        
        context = data.get("context", {})
        confidence = context.get("confidence")
        
        assert confidence is not None, "Missing confidence field"
        assert 0 <= confidence <= 1, f"Confidence {confidence} not in range [0,1]"
        print(f"✅ Context confidence: {confidence}")

    def test_context_has_drivers_array(self, api_client):
        """Verify drivers array is present"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert response.status_code == 200
        data = response.json()
        
        context = data.get("context", {})
        assert "drivers" in context, "Missing drivers field"
        assert isinstance(context["drivers"], list), "drivers should be a list"
        print(f"✅ Context drivers count: {len(context['drivers'])}")

    def test_context_risk_values_valid(self, api_client):
        """Verify risk values are within expected ranges"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert response.status_code == 200
        data = response.json()
        
        context = data.get("context", {})
        
        # Check crowding_risk (0-1)
        crowding = context.get("crowding_risk", 0)
        assert 0 <= crowding <= 1, f"crowding_risk {crowding} out of range"
        
        # Check squeeze_probability (0-1)
        squeeze = context.get("squeeze_probability", 0)
        assert 0 <= squeeze <= 1, f"squeeze_probability {squeeze} out of range"
        
        # Check cascade_probability (0-1)
        cascade = context.get("cascade_probability", 0)
        assert 0 <= cascade <= 1, f"cascade_probability {cascade} out of range"
        
        print(f"✅ Risk values valid - crowding: {crowding:.3f}, squeeze: {squeeze:.3f}, cascade: {cascade:.3f}")


# ============================================
# Funding Signal Tests
# ============================================

class TestFundingSignal:
    """Test /api/exchange-intelligence/funding/{symbol} endpoint"""

    def test_funding_btc_returns_ok(self, api_client):
        """Verify funding endpoint returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/funding/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Funding BTC returns ok=true")

    def test_funding_has_required_fields(self, api_client):
        """Verify funding signal has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/funding/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        required_fields = [
            "symbol", "timestamp", "funding_rate", "funding_state",
            "oi_pressure", "crowding_risk", "confidence", "drivers"
        ]
        
        for field in required_fields:
            assert field in signal, f"Missing required field: {field}"
        
        print(f"✅ Funding signal has all required fields")

    def test_funding_crowding_risk_valid(self, api_client):
        """Verify crowding_risk is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/funding/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        crowding = signal.get("crowding_risk", 0)
        assert 0 <= crowding <= 1, f"crowding_risk {crowding} out of range"
        print(f"✅ Funding crowding_risk: {crowding}")

    def test_funding_confidence_valid(self, api_client):
        """Verify confidence is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/funding/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        confidence = signal.get("confidence", 0)
        assert 0 <= confidence <= 1, f"confidence {confidence} out of range"
        print(f"✅ Funding confidence: {confidence}")

    def test_funding_has_drivers_array(self, api_client):
        """Verify drivers is a list"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/funding/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        assert isinstance(signal.get("drivers"), list), "drivers should be a list"
        print(f"✅ Funding drivers: {signal.get('drivers')}")


# ============================================
# Derivatives Signal Tests
# ============================================

class TestDerivativesSignal:
    """Test /api/exchange-intelligence/derivatives/{symbol} endpoint"""

    def test_derivatives_btc_returns_ok(self, api_client):
        """Verify derivatives endpoint returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/derivatives/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Derivatives BTC returns ok=true")

    def test_derivatives_has_required_fields(self, api_client):
        """Verify derivatives signal has required fields"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/derivatives/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        required_fields = [
            "symbol", "timestamp", "long_short_ratio", "squeeze_probability",
            "pressure_state", "confidence", "drivers"
        ]
        
        for field in required_fields:
            assert field in signal, f"Missing required field: {field}"
        
        print(f"✅ Derivatives signal has all required fields")

    def test_derivatives_squeeze_probability_valid(self, api_client):
        """Verify squeeze_probability is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/derivatives/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        squeeze = signal.get("squeeze_probability", 0)
        assert 0 <= squeeze <= 1, f"squeeze_probability {squeeze} out of range"
        print(f"✅ Derivatives squeeze_probability: {squeeze}")

    def test_derivatives_has_long_short_ratio(self, api_client):
        """Verify long_short_ratio is present and positive"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/derivatives/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        ls_ratio = signal.get("long_short_ratio")
        assert ls_ratio is not None, "Missing long_short_ratio"
        assert ls_ratio > 0, f"long_short_ratio {ls_ratio} should be positive"
        print(f"✅ Derivatives long_short_ratio: {ls_ratio}")


# ============================================
# Liquidation Signal Tests
# ============================================

class TestLiquidationSignal:
    """Test /api/exchange-intelligence/liquidation/{symbol} endpoint"""

    def test_liquidation_btc_returns_ok(self, api_client):
        """Verify liquidation endpoint returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/liquidation/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Liquidation BTC returns ok=true")

    def test_liquidation_has_required_fields(self, api_client):
        """Verify liquidation signal has required fields"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/liquidation/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        required_fields = [
            "symbol", "timestamp", "long_liq_zone", "short_liq_zone",
            "cascade_probability", "liquidation_risk", "confidence", "drivers"
        ]
        
        for field in required_fields:
            assert field in signal, f"Missing required field: {field}"
        
        print(f"✅ Liquidation signal has all required fields")

    def test_liquidation_cascade_probability_valid(self, api_client):
        """Verify cascade_probability is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/liquidation/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        cascade = signal.get("cascade_probability", 0)
        assert 0 <= cascade <= 1, f"cascade_probability {cascade} out of range"
        print(f"✅ Liquidation cascade_probability: {cascade}")

    def test_liquidation_zones_present(self, api_client):
        """Verify liquidation zones are present and valid"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/liquidation/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        long_zone = signal.get("long_liq_zone")
        short_zone = signal.get("short_liq_zone")
        
        assert long_zone is not None, "Missing long_liq_zone"
        assert short_zone is not None, "Missing short_liq_zone"
        assert long_zone >= 0, f"long_liq_zone {long_zone} should be >= 0"
        assert short_zone >= 0, f"short_liq_zone {short_zone} should be >= 0"
        print(f"✅ Liquidation zones - Long: {long_zone}, Short: {short_zone}")


# ============================================
# Flow Signal Tests
# ============================================

class TestFlowSignal:
    """Test /api/exchange-intelligence/flow/{symbol} endpoint"""

    def test_flow_btc_returns_ok(self, api_client):
        """Verify flow endpoint returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/flow/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Flow BTC returns ok=true")

    def test_flow_has_required_fields(self, api_client):
        """Verify flow signal has required fields"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/flow/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        required_fields = [
            "symbol", "timestamp", "taker_buy_ratio", "aggressive_flow",
            "flow_direction", "confidence", "drivers"
        ]
        
        for field in required_fields:
            assert field in signal, f"Missing required field: {field}"
        
        print(f"✅ Flow signal has all required fields")

    def test_flow_taker_buy_ratio_valid(self, api_client):
        """Verify taker_buy_ratio is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/flow/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        ratio = signal.get("taker_buy_ratio", 0)
        assert 0 <= ratio <= 1, f"taker_buy_ratio {ratio} out of range"
        print(f"✅ Flow taker_buy_ratio: {ratio}")

    def test_flow_aggressive_flow_valid(self, api_client):
        """Verify aggressive_flow is between -1 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/flow/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        aggressive = signal.get("aggressive_flow", 0)
        assert -1 <= aggressive <= 1, f"aggressive_flow {aggressive} out of range [-1, 1]"
        print(f"✅ Flow aggressive_flow: {aggressive}")


# ============================================
# Volume Signal Tests
# ============================================

class TestVolumeSignal:
    """Test /api/exchange-intelligence/volume/{symbol} endpoint"""

    def test_volume_btc_returns_ok(self, api_client):
        """Verify volume endpoint returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/volume/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ Volume BTC returns ok=true")

    def test_volume_has_required_fields(self, api_client):
        """Verify volume signal has required fields"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/volume/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        required_fields = [
            "symbol", "timestamp", "volume_ratio", "volume_state",
            "anomaly_score", "confidence", "drivers"
        ]
        
        for field in required_fields:
            assert field in signal, f"Missing required field: {field}"
        
        print(f"✅ Volume signal has all required fields")

    def test_volume_ratio_valid(self, api_client):
        """Verify volume_ratio is a positive number"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/volume/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        ratio = signal.get("volume_ratio")
        assert ratio is not None, "Missing volume_ratio"
        assert ratio >= 0, f"volume_ratio {ratio} should be >= 0"
        print(f"✅ Volume ratio: {ratio}")

    def test_volume_anomaly_score_valid(self, api_client):
        """Verify anomaly_score is between 0 and 1"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/volume/BTC")
        assert response.status_code == 200
        data = response.json()
        
        signal = data.get("signal", {})
        anomaly = signal.get("anomaly_score", 0)
        assert 0 <= anomaly <= 1, f"anomaly_score {anomaly} out of range"
        print(f"✅ Volume anomaly_score: {anomaly}")


# ============================================
# History Endpoint Tests
# ============================================

class TestHistoryEndpoint:
    """Test /api/exchange-intelligence/history/{symbol} endpoint"""

    def test_history_btc_returns_ok(self, api_client):
        """Verify history endpoint returns ok=true"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/history/BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        print(f"✅ History BTC returns ok=true")

    def test_history_has_latest_context(self, api_client):
        """Verify history has latest context"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/history/BTC")
        assert response.status_code == 200
        data = response.json()
        
        assert "latest" in data, "Missing latest field"
        assert data["symbol"] == "BTC", "Symbol mismatch"
        print(f"✅ History has latest context for BTC")

    def test_history_has_count_fields(self, api_client):
        """Verify history has count fields"""
        response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/history/BTC")
        assert response.status_code == 200
        data = response.json()
        
        assert "funding_history_count" in data, "Missing funding_history_count"
        assert "volume_history_count" in data, "Missing volume_history_count"
        
        # Counts should be non-negative integers
        assert isinstance(data["funding_history_count"], int)
        assert isinstance(data["volume_history_count"], int)
        assert data["funding_history_count"] >= 0
        assert data["volume_history_count"] >= 0
        
        print(f"✅ History counts - Funding: {data['funding_history_count']}, Volume: {data['volume_history_count']}")


# ============================================
# Cross-Engine Validation Tests
# ============================================

class TestCrossEngineValidation:
    """Cross-validate signals between engines and aggregated context"""

    def test_context_funding_state_matches_funding_signal(self, api_client):
        """Verify context's funding_state matches funding endpoint"""
        ctx_response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        funding_response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/funding/BTC")
        
        assert ctx_response.status_code == 200
        assert funding_response.status_code == 200
        
        ctx = ctx_response.json().get("context", {})
        funding = funding_response.json().get("signal", {})
        
        assert ctx.get("funding_state") == funding.get("funding_state"), \
            f"Funding state mismatch: context={ctx.get('funding_state')}, signal={funding.get('funding_state')}"
        print(f"✅ Funding state consistent: {ctx.get('funding_state')}")

    def test_context_volume_state_matches_volume_signal(self, api_client):
        """Verify context's volume_state matches volume endpoint"""
        ctx_response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        volume_response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/volume/BTC")
        
        assert ctx_response.status_code == 200
        assert volume_response.status_code == 200
        
        ctx = ctx_response.json().get("context", {})
        volume = volume_response.json().get("signal", {})
        
        assert ctx.get("volume_state") == volume.get("volume_state"), \
            f"Volume state mismatch: context={ctx.get('volume_state')}, signal={volume.get('volume_state')}"
        print(f"✅ Volume state consistent: {ctx.get('volume_state')}")

    def test_all_sub_signal_confidences_valid(self, api_client):
        """Verify all sub-signal confidences are in valid range"""
        ctx_response = api_client.get(f"{BASE_URL}/api/exchange-intelligence/context/BTC")
        assert ctx_response.status_code == 200
        
        context = ctx_response.json().get("context", {})
        
        details = [
            ("funding_detail", "funding"),
            ("derivatives_detail", "derivatives"),
            ("liquidation_detail", "liquidation"),
            ("flow_detail", "flow"),
            ("volume_detail", "volume"),
        ]
        
        for detail_key, name in details:
            detail = context.get(detail_key, {})
            conf = detail.get("confidence", 0)
            assert 0 <= conf <= 1, f"{name} confidence {conf} out of range"
            print(f"  {name} confidence: {conf}")
        
        print(f"✅ All sub-signal confidences valid")


# ============================================
# Data Integrity Tests
# ============================================

class TestDataIntegrity:
    """Test data consistency and integrity across endpoints"""

    def test_all_signals_have_symbol_btc(self, api_client):
        """Verify all signals return correct symbol"""
        endpoints = [
            "/api/exchange-intelligence/funding/BTC",
            "/api/exchange-intelligence/derivatives/BTC",
            "/api/exchange-intelligence/liquidation/BTC",
            "/api/exchange-intelligence/flow/BTC",
            "/api/exchange-intelligence/volume/BTC",
        ]
        
        for endpoint in endpoints:
            response = api_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200
            signal = response.json().get("signal", {})
            assert signal.get("symbol") == "BTC", f"Symbol mismatch in {endpoint}"
        
        print(f"✅ All signals return symbol=BTC")

    def test_all_signals_have_timestamp(self, api_client):
        """Verify all signals have valid timestamps"""
        endpoints = [
            "/api/exchange-intelligence/funding/BTC",
            "/api/exchange-intelligence/derivatives/BTC",
            "/api/exchange-intelligence/liquidation/BTC",
            "/api/exchange-intelligence/flow/BTC",
            "/api/exchange-intelligence/volume/BTC",
        ]
        
        for endpoint in endpoints:
            response = api_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200
            signal = response.json().get("signal", {})
            
            ts = signal.get("timestamp")
            assert ts is not None, f"Missing timestamp in {endpoint}"
            
            # Verify it's a valid ISO timestamp
            try:
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except:
                pytest.fail(f"Invalid timestamp format in {endpoint}: {ts}")
        
        print(f"✅ All signals have valid timestamps")

    def test_all_drivers_are_lists(self, api_client):
        """Verify all signals have drivers as lists"""
        endpoints = [
            "/api/exchange-intelligence/funding/BTC",
            "/api/exchange-intelligence/derivatives/BTC",
            "/api/exchange-intelligence/liquidation/BTC",
            "/api/exchange-intelligence/flow/BTC",
            "/api/exchange-intelligence/volume/BTC",
            "/api/exchange-intelligence/context/BTC",
        ]
        
        for endpoint in endpoints:
            response = api_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200
            
            data = response.json()
            if "signal" in data:
                obj = data["signal"]
            else:
                obj = data.get("context", {})
            
            assert isinstance(obj.get("drivers"), list), f"drivers not a list in {endpoint}"
        
        print(f"✅ All drivers are lists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
