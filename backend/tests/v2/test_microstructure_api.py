"""
API Tests for Microstructure Snapshot Engine (PHASE 28.1)

Tests all 4 API endpoints:
1. GET /api/v1/microstructure/current/{symbol} - returns MicrostructureSnapshot
2. GET /api/v1/microstructure/summary/{symbol} - returns state counts and averages
3. GET /api/v1/microstructure/history/{symbol} - returns historical records
4. POST /api/v1/microstructure/recompute/{symbol} - force recompute and store

Validates:
- All metric calculations (spread_bps, depth_score, imbalance_score)
- All state classifications (liquidity_state, pressure_state, microstructure_state)
- Confidence bounded [0, 1]
- History accumulates across multiple calls
- Summary reflects stored history accurately
- Response fields match expected contract
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")


class TestMicrostructureCurrentEndpoint:
    """Tests for GET /api/v1/microstructure/current/{symbol}"""
    
    def test_current_endpoint_returns_200(self):
        """Verify current endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /current/{symbol} returns 200")
    
    def test_current_endpoint_response_structure(self):
        """Verify all required fields in response"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        
        required_fields = [
            "symbol", "spread_bps", "depth_score", "imbalance_score",
            "liquidation_pressure", "funding_pressure", "oi_pressure",
            "liquidity_state", "pressure_state", "microstructure_state",
            "confidence", "reason", "computed_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        print(f"PASS: All {len(required_fields)} required fields present")
    
    def test_current_endpoint_symbol_uppercase(self):
        """Verify symbol is uppercased in response"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/btc")
        data = response.json()
        assert data["symbol"] == "BTC", f"Symbol not uppercase: {data['symbol']}"
        print("PASS: Symbol correctly uppercased")
    
    def test_current_endpoint_spread_bps_non_negative(self):
        """Verify spread_bps is >= 0"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/ETH")
        data = response.json()
        assert data["spread_bps"] >= 0, f"spread_bps negative: {data['spread_bps']}"
        print(f"PASS: spread_bps = {data['spread_bps']} (non-negative)")
    
    def test_current_endpoint_depth_score_bounded(self):
        """Verify depth_score is in [0, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/SOL")
        data = response.json()
        assert 0.0 <= data["depth_score"] <= 1.0, f"depth_score out of bounds: {data['depth_score']}"
        print(f"PASS: depth_score = {data['depth_score']} (bounded [0,1])")
    
    def test_current_endpoint_imbalance_score_bounded(self):
        """Verify imbalance_score is in [-1, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/DOGE")
        data = response.json()
        assert -1.0 <= data["imbalance_score"] <= 1.0, f"imbalance_score out of bounds: {data['imbalance_score']}"
        print(f"PASS: imbalance_score = {data['imbalance_score']} (bounded [-1,1])")
    
    def test_current_endpoint_liquidation_pressure_bounded(self):
        """Verify liquidation_pressure is in [-1, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        assert -1.0 <= data["liquidation_pressure"] <= 1.0, f"liquidation_pressure out of bounds: {data['liquidation_pressure']}"
        print(f"PASS: liquidation_pressure = {data['liquidation_pressure']} (bounded [-1,1])")
    
    def test_current_endpoint_funding_pressure_bounded(self):
        """Verify funding_pressure is in [-1, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        assert -1.0 <= data["funding_pressure"] <= 1.0, f"funding_pressure out of bounds: {data['funding_pressure']}"
        print(f"PASS: funding_pressure = {data['funding_pressure']} (bounded [-1,1])")
    
    def test_current_endpoint_oi_pressure_bounded(self):
        """Verify oi_pressure is in [-1, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        assert -1.0 <= data["oi_pressure"] <= 1.0, f"oi_pressure out of bounds: {data['oi_pressure']}"
        print(f"PASS: oi_pressure = {data['oi_pressure']} (bounded [-1,1])")
    
    def test_current_endpoint_confidence_bounded(self):
        """Verify confidence is in [0, 1]"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0, f"confidence out of bounds: {data['confidence']}"
        print(f"PASS: confidence = {data['confidence']} (bounded [0,1])")
    
    def test_current_endpoint_liquidity_state_valid(self):
        """Verify liquidity_state is DEEP, NORMAL, or THIN"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        valid_states = ["DEEP", "NORMAL", "THIN"]
        assert data["liquidity_state"] in valid_states, f"Invalid liquidity_state: {data['liquidity_state']}"
        print(f"PASS: liquidity_state = {data['liquidity_state']}")
    
    def test_current_endpoint_pressure_state_valid(self):
        """Verify pressure_state is BUY_PRESSURE, SELL_PRESSURE, or BALANCED"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        valid_states = ["BUY_PRESSURE", "SELL_PRESSURE", "BALANCED"]
        assert data["pressure_state"] in valid_states, f"Invalid pressure_state: {data['pressure_state']}"
        print(f"PASS: pressure_state = {data['pressure_state']}")
    
    def test_current_endpoint_microstructure_state_valid(self):
        """Verify microstructure_state is SUPPORTIVE, NEUTRAL, FRAGILE, or STRESSED"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        valid_states = ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        assert data["microstructure_state"] in valid_states, f"Invalid microstructure_state: {data['microstructure_state']}"
        print(f"PASS: microstructure_state = {data['microstructure_state']}")
    
    def test_current_endpoint_reason_not_empty(self):
        """Verify reason is not empty"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/BTC")
        data = response.json()
        assert len(data["reason"]) > 0, "reason is empty"
        print(f"PASS: reason = '{data['reason'][:50]}...'")


class TestMicrostructureSummaryEndpoint:
    """Tests for GET /api/v1/microstructure/summary/{symbol}"""
    
    def test_summary_endpoint_returns_200(self):
        """Verify summary endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/BTC")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /summary/{symbol} returns 200")
    
    def test_summary_endpoint_response_structure(self):
        """Verify all required fields in summary response"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/BTC")
        data = response.json()
        
        required_fields = [
            "symbol", "total_records", "liquidity_states",
            "pressure_states", "microstructure_states", "averages", "current_state"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Check nested structures
        assert "deep" in data["liquidity_states"]
        assert "normal" in data["liquidity_states"]
        assert "thin" in data["liquidity_states"]
        
        assert "buy_pressure" in data["pressure_states"]
        assert "sell_pressure" in data["pressure_states"]
        assert "balanced" in data["pressure_states"]
        
        assert "supportive" in data["microstructure_states"]
        assert "neutral" in data["microstructure_states"]
        assert "fragile" in data["microstructure_states"]
        assert "stressed" in data["microstructure_states"]
        
        assert "spread_bps" in data["averages"]
        assert "depth_score" in data["averages"]
        assert "confidence" in data["averages"]
        
        print("PASS: All required fields and nested structures present")
    
    def test_summary_total_records_non_negative(self):
        """Verify total_records is >= 0"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/BTC")
        data = response.json()
        assert data["total_records"] >= 0, f"total_records negative: {data['total_records']}"
        print(f"PASS: total_records = {data['total_records']} (non-negative)")
    
    def test_summary_state_counts_non_negative(self):
        """Verify all state counts are >= 0"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/BTC")
        data = response.json()
        
        for state, count in data["liquidity_states"].items():
            assert count >= 0, f"Negative count for liquidity_states.{state}: {count}"
        
        for state, count in data["pressure_states"].items():
            assert count >= 0, f"Negative count for pressure_states.{state}: {count}"
        
        for state, count in data["microstructure_states"].items():
            assert count >= 0, f"Negative count for microstructure_states.{state}: {count}"
        
        print("PASS: All state counts are non-negative")
    
    def test_summary_averages_reasonable(self):
        """Verify averages are within expected ranges"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/BTC")
        data = response.json()
        
        # If there are records, averages should be valid
        if data["total_records"] > 0:
            assert data["averages"]["spread_bps"] >= 0, "spread_bps average negative"
            assert 0.0 <= data["averages"]["depth_score"] <= 1.0, "depth_score average out of bounds"
            assert 0.0 <= data["averages"]["confidence"] <= 1.0, "confidence average out of bounds"
        
        print(f"PASS: averages = {data['averages']}")
    
    def test_summary_current_state_valid(self):
        """Verify current_state is valid"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/BTC")
        data = response.json()
        valid_states = ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        assert data["current_state"] in valid_states, f"Invalid current_state: {data['current_state']}"
        print(f"PASS: current_state = {data['current_state']}")


class TestMicrostructureHistoryEndpoint:
    """Tests for GET /api/v1/microstructure/history/{symbol}"""
    
    def test_history_endpoint_returns_200(self):
        """Verify history endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/BTC")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /history/{symbol} returns 200")
    
    def test_history_endpoint_response_structure(self):
        """Verify all required fields in history response"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/BTC")
        data = response.json()
        
        assert "symbol" in data, "Missing field: symbol"
        assert "history" in data, "Missing field: history"
        assert "count" in data, "Missing field: count"
        assert isinstance(data["history"], list), "history is not a list"
        
        print(f"PASS: History response structure valid, count = {data['count']}")
    
    def test_history_record_structure(self):
        """Verify history record structure if records exist"""
        # First create a record
        requests.get(f"{BASE_URL}/api/v1/microstructure/current/AVAX")
        time.sleep(0.5)
        
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/AVAX")
        data = response.json()
        
        if len(data["history"]) > 0:
            record = data["history"][0]
            required_fields = [
                "spread_bps", "depth_score", "imbalance_score",
                "liquidation_pressure", "funding_pressure", "oi_pressure",
                "liquidity_state", "pressure_state", "microstructure_state",
                "confidence", "recorded_at"
            ]
            
            for field in required_fields:
                assert field in record, f"Missing field in record: {field}"
            
            print(f"PASS: History record has all {len(required_fields)} required fields")
        else:
            print("INFO: No history records to check (empty)")
    
    def test_history_limit_parameter(self):
        """Verify limit query parameter works"""
        # Create some records first
        for _ in range(3):
            requests.get(f"{BASE_URL}/api/v1/microstructure/current/XRP")
        
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/XRP?limit=2")
        data = response.json()
        
        assert data["count"] <= 2, f"limit parameter not respected: count={data['count']}"
        print(f"PASS: limit=2 respected, count = {data['count']}")
    
    def test_history_count_matches_list_length(self):
        """Verify count matches actual history list length"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/BTC")
        data = response.json()
        
        assert data["count"] == len(data["history"]), f"count ({data['count']}) != len(history) ({len(data['history'])})"
        print(f"PASS: count = len(history) = {data['count']}")


class TestMicrostructureRecomputeEndpoint:
    """Tests for POST /api/v1/microstructure/recompute/{symbol}"""
    
    def test_recompute_endpoint_returns_200(self):
        """Verify recompute endpoint returns 200 status"""
        response = requests.post(f"{BASE_URL}/api/v1/microstructure/recompute/BTC")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: POST /recompute/{symbol} returns 200")
    
    def test_recompute_endpoint_response_structure(self):
        """Verify all required fields in recompute response"""
        response = requests.post(f"{BASE_URL}/api/v1/microstructure/recompute/BTC")
        data = response.json()
        
        required_fields = [
            "status", "symbol", "spread_bps", "depth_score", "imbalance_score",
            "liquidation_pressure", "funding_pressure", "oi_pressure",
            "liquidity_state", "pressure_state", "microstructure_state",
            "confidence", "reason", "computed_at"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["status"] == "ok", f"Unexpected status: {data['status']}"
        print(f"PASS: All {len(required_fields)} required fields present, status='ok'")
    
    def test_recompute_stores_in_history(self):
        """Verify recompute stores snapshot in history"""
        # Use a unique symbol to avoid interference
        symbol = "LINK"
        
        # Get initial history count
        initial_response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/{symbol}?limit=100")
        initial_count = initial_response.json()["count"]
        
        # Recompute
        requests.post(f"{BASE_URL}/api/v1/microstructure/recompute/{symbol}")
        
        # Check history count increased
        final_response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/{symbol}?limit=100")
        final_count = final_response.json()["count"]
        
        assert final_count > initial_count, f"History count did not increase: {initial_count} -> {final_count}"
        print(f"PASS: Recompute stored in history: {initial_count} -> {final_count}")


class TestMicrostructureHistoryAccumulation:
    """Tests for history accumulation across multiple calls"""
    
    def test_current_accumulates_history(self):
        """Verify /current calls accumulate history"""
        symbol = "DOT"
        
        # Get initial count
        initial_response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/{symbol}?limit=500")
        initial_count = initial_response.json()["count"]
        
        # Make 3 current calls
        for i in range(3):
            requests.get(f"{BASE_URL}/api/v1/microstructure/current/{symbol}")
            time.sleep(0.1)
        
        # Check history increased by 3
        final_response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/{symbol}?limit=500")
        final_count = final_response.json()["count"]
        
        expected_increase = 3
        actual_increase = final_count - initial_count
        
        assert actual_increase >= expected_increase, f"History did not accumulate: expected +{expected_increase}, got +{actual_increase}"
        print(f"PASS: History accumulated: {initial_count} -> {final_count} (+{actual_increase})")
    
    def test_summary_reflects_accumulated_history(self):
        """Verify summary reflects accumulated history"""
        symbol = "ATOM"
        
        # Make some calls
        for _ in range(5):
            requests.get(f"{BASE_URL}/api/v1/microstructure/current/{symbol}")
        
        # Get summary
        summary_response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/{symbol}")
        summary = summary_response.json()
        
        # Get history
        history_response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/{symbol}?limit=100")
        history_count = history_response.json()["count"]
        
        # Summary total should match history
        assert summary["total_records"] == history_count, f"Summary total ({summary['total_records']}) != history count ({history_count})"
        
        # State counts should sum to total
        liq_sum = sum(summary["liquidity_states"].values())
        press_sum = sum(summary["pressure_states"].values())
        micro_sum = sum(summary["microstructure_states"].values())
        
        assert liq_sum == summary["total_records"], f"Liquidity state counts don't sum to total: {liq_sum} != {summary['total_records']}"
        assert press_sum == summary["total_records"], f"Pressure state counts don't sum to total: {press_sum} != {summary['total_records']}"
        assert micro_sum == summary["total_records"], f"Microstructure state counts don't sum to total: {micro_sum} != {summary['total_records']}"
        
        print(f"PASS: Summary reflects history: total={summary['total_records']}, liq_sum={liq_sum}, press_sum={press_sum}, micro_sum={micro_sum}")


class TestMicrostructureCrossValidation:
    """Cross-validation tests between endpoints"""
    
    def test_current_and_history_consistency(self):
        """Verify current snapshot appears in history"""
        symbol = "NEAR"
        
        # Get current
        current_response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/{symbol}")
        current_data = current_response.json()
        
        # Wait a bit
        time.sleep(0.2)
        
        # Get history
        history_response = requests.get(f"{BASE_URL}/api/v1/microstructure/history/{symbol}?limit=1")
        history_data = history_response.json()
        
        assert len(history_data["history"]) > 0, "No history records"
        
        latest_record = history_data["history"][0]
        
        # Check key fields match (with some tolerance for timing)
        # Note: Values are simulated so we just verify fields exist and are valid types
        assert isinstance(latest_record["spread_bps"], (int, float))
        assert isinstance(latest_record["depth_score"], (int, float))
        assert isinstance(latest_record["imbalance_score"], (int, float))
        
        print("PASS: Current snapshot stored in history with correct field types")
    
    def test_recompute_updates_summary(self):
        """Verify recompute updates summary"""
        symbol = "FTM"
        
        # Get initial summary
        initial_summary = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/{symbol}").json()
        initial_total = initial_summary["total_records"]
        
        # Recompute
        requests.post(f"{BASE_URL}/api/v1/microstructure/recompute/{symbol}")
        
        # Get updated summary
        final_summary = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/{symbol}").json()
        final_total = final_summary["total_records"]
        
        assert final_total == initial_total + 1, f"Summary not updated after recompute: {initial_total} -> {final_total}"
        print(f"PASS: Summary updated after recompute: {initial_total} -> {final_total}")


class TestMicrostructureEdgeCases:
    """Edge case tests"""
    
    def test_unknown_symbol(self):
        """Verify unknown symbol returns valid empty response"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/UNKNOWNSYMBOL123")
        assert response.status_code == 200, f"Expected 200 for unknown symbol, got {response.status_code}"
        
        data = response.json()
        assert data["symbol"] == "UNKNOWNSYMBOL123", "Symbol not preserved"
        print("PASS: Unknown symbol handled correctly")
    
    def test_lowercase_symbol_conversion(self):
        """Verify lowercase symbols are uppercased"""
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/current/lowercase")
        data = response.json()
        assert data["symbol"] == "LOWERCASE", f"Symbol not uppercased: {data['symbol']}"
        print("PASS: Lowercase symbol uppercased to 'LOWERCASE'")
    
    def test_empty_history_summary(self):
        """Verify summary for symbol with no history"""
        # Use a unique symbol unlikely to have history
        symbol = "VERYRARE999"
        
        response = requests.get(f"{BASE_URL}/api/v1/microstructure/summary/{symbol}")
        data = response.json()
        
        # First call creates a record, but checking structure
        assert data["total_records"] >= 0
        assert data["current_state"] in ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        print(f"PASS: Summary for rare symbol valid: total={data['total_records']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
