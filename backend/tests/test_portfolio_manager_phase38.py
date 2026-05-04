"""
Portfolio Manager API Tests - PHASE 38

Comprehensive testing of multi-asset portfolio management with:
- Markowitz risk model (wᵀΣw)
- Correlation matrix
- Target-based rebalancing (3% threshold)
- Capital rotation with correlation/risk considerations
- Exposure limits (70% long/short, 10% position)

API Endpoints tested:
- GET /api/v1/portfolio/state
- GET /api/v1/portfolio/exposure
- GET /api/v1/portfolio/positions
- GET /api/v1/portfolio/targets
- GET /api/v1/portfolio/risk
- POST /api/v1/portfolio/targets
- POST /api/v1/portfolio/position
- POST /api/v1/portfolio/rebalance
- DELETE /api/v1/portfolio/position/{symbol}
- GET /api/v1/portfolio/constraints/{symbol}
- POST /api/v1/portfolio/validate-execution
"""

import pytest
import requests
import os
import time
import random
import string

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com').rstrip('/')


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def generate_unique_symbol():
    """Generate unique test symbol to avoid conflicts."""
    suffix = ''.join(random.choices(string.ascii_uppercase, k=4))
    return f"TEST_{suffix}"


# ══════════════════════════════════════════════════════════════
# 1. GET Portfolio State Tests
# ══════════════════════════════════════════════════════════════

class TestPortfolioState:
    """Tests for GET /api/v1/portfolio/state endpoint."""
    
    def test_portfolio_state_returns_200(self, api_client):
        """Test portfolio state endpoint returns 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/state")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ Portfolio state returns 200 OK")
    
    def test_portfolio_state_has_required_fields(self, api_client):
        """Test portfolio state contains all required fields including Markowitz metrics."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/state")
        assert response.status_code == 200
        
        data = response.json()
        
        # Capital fields
        assert "total_capital" in data, "Missing total_capital"
        assert "available_capital" in data, "Missing available_capital"
        assert "allocated_capital" in data, "Missing allocated_capital"
        
        # Position fields
        assert "positions" in data, "Missing positions"
        assert "position_count" in data, "Missing position_count"
        assert "target_positions" in data, "Missing target_positions"
        
        # Exposure fields
        assert "long_exposure" in data, "Missing long_exposure"
        assert "short_exposure" in data, "Missing short_exposure"
        assert "net_exposure" in data, "Missing net_exposure"
        assert "gross_exposure" in data, "Missing gross_exposure"
        
        # Markowitz risk fields (KEY PHASE 38 requirement)
        assert "portfolio_variance" in data, "Missing portfolio_variance (wᵀΣw)"
        assert "portfolio_volatility" in data, "Missing portfolio_volatility"
        assert "portfolio_risk" in data, "Missing portfolio_risk"
        assert "risk_level" in data, "Missing risk_level"
        
        # Rebalance fields
        assert "rebalance_required" in data, "Missing rebalance_required"
        assert "max_weight_deviation" in data, "Missing max_weight_deviation"
        
        # Health fields
        assert "is_healthy" in data, "Missing is_healthy"
        assert "warnings" in data, "Missing warnings"
        
        print("✅ Portfolio state has all required fields including portfolio_variance")
    
    def test_portfolio_state_capital_calculations_valid(self, api_client):
        """Test capital calculations are valid (available + allocated = total)."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/state")
        data = response.json()
        
        total = data["total_capital"]
        available = data["available_capital"]
        allocated = data["allocated_capital"]
        
        assert total > 0, "Total capital should be positive"
        # Allow small float precision tolerance
        assert abs((available + allocated) - total) < 1, \
            f"Capital mismatch: {available} + {allocated} != {total}"
        
        print(f"✅ Capital calculations valid: {available:,.0f} + {allocated:,.0f} = {total:,.0f}")
    
    def test_portfolio_variance_is_non_negative(self, api_client):
        """Test portfolio variance (wᵀΣw) is non-negative."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/state")
        data = response.json()
        
        assert data["portfolio_variance"] >= 0, "Portfolio variance must be >= 0"
        assert data["portfolio_volatility"] >= 0, "Portfolio volatility must be >= 0"
        
        print(f"✅ Portfolio variance: {data['portfolio_variance']:.8f}, volatility: {data['portfolio_volatility']:.6f}")


# ══════════════════════════════════════════════════════════════
# 2. GET Exposure Tests
# ══════════════════════════════════════════════════════════════

class TestPortfolioExposure:
    """Tests for GET /api/v1/portfolio/exposure endpoint."""
    
    def test_exposure_returns_200(self, api_client):
        """Test exposure endpoint returns 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/exposure")
        assert response.status_code == 200
        print("✅ Exposure endpoint returns 200 OK")
    
    def test_exposure_has_required_fields(self, api_client):
        """Test exposure contains long/short/net/gross exposure."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/exposure")
        data = response.json()
        
        required_fields = [
            "long_exposure", "short_exposure", "net_exposure", "gross_exposure",
            "exposure_by_symbol", "long_within_limit", "short_within_limit",
            "available_long_capacity", "available_short_capacity"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing {field}"
        
        print("✅ Exposure has all required fields")
    
    def test_exposure_limits_validated(self, api_client):
        """Test exposure limits (70% max) are validated."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/exposure")
        data = response.json()
        
        # Exposure should be within 0-1 range
        assert 0 <= data["long_exposure"] <= 1, "Long exposure out of range"
        assert 0 <= data["short_exposure"] <= 1, "Short exposure out of range"
        
        # Net exposure = long - short
        expected_net = data["long_exposure"] - data["short_exposure"]
        assert abs(data["net_exposure"] - expected_net) < 0.001, "Net exposure calculation mismatch"
        
        # Gross exposure = long + short
        expected_gross = data["long_exposure"] + data["short_exposure"]
        assert abs(data["gross_exposure"] - expected_gross) < 0.001, "Gross exposure calculation mismatch"
        
        print(f"✅ Exposure: long={data['long_exposure']:.2%}, short={data['short_exposure']:.2%}, net={data['net_exposure']:.2%}")
    
    def test_exposure_capacity_calculations(self, api_client):
        """Test available capacity is calculated correctly (70% - current)."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/exposure")
        data = response.json()
        
        MAX_LONG = 0.70
        MAX_SHORT = 0.70
        
        # Available capacity = max - current
        expected_long_capacity = max(MAX_LONG - data["long_exposure"], 0)
        expected_short_capacity = max(MAX_SHORT - data["short_exposure"], 0)
        
        assert abs(data["available_long_capacity"] - expected_long_capacity) < 0.01, \
            f"Long capacity mismatch: {data['available_long_capacity']} vs {expected_long_capacity}"
        assert abs(data["available_short_capacity"] - expected_short_capacity) < 0.01, \
            f"Short capacity mismatch: {data['available_short_capacity']} vs {expected_short_capacity}"
        
        print(f"✅ Available capacity: long={data['available_long_capacity']:.2%}, short={data['available_short_capacity']:.2%}")


# ══════════════════════════════════════════════════════════════
# 3. GET Positions Tests
# ══════════════════════════════════════════════════════════════

class TestPortfolioPositions:
    """Tests for GET /api/v1/portfolio/positions endpoint."""
    
    def test_positions_returns_200(self, api_client):
        """Test positions endpoint returns 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/positions")
        assert response.status_code == 200
        print("✅ Positions endpoint returns 200 OK")
    
    def test_positions_returns_list(self, api_client):
        """Test positions returns a list."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/positions")
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ Positions returns list with {len(data)} positions")
    
    def test_position_fields_structure(self, api_client):
        """Test position objects have required fields."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/positions")
        data = response.json()
        
        if len(data) > 0:
            position = data[0]
            required_fields = [
                "symbol", "direction", "size_usd", "size_percent",
                "entry_price", "current_price", "stop_loss", "take_profit",
                "risk_contribution", "correlation_penalty", "status"
            ]
            
            for field in required_fields:
                assert field in position, f"Missing field: {field}"
            
            # Validate field values
            assert position["direction"] in ["LONG", "SHORT"], f"Invalid direction: {position['direction']}"
            assert position["size_percent"] <= 0.10, f"Position exceeds 10% limit: {position['size_percent']}"
            
            print(f"✅ Position structure valid: {position['symbol']} {position['direction']} {position['size_percent']:.2%}")
        else:
            print("⚠️ No positions to validate structure")


# ══════════════════════════════════════════════════════════════
# 4. GET Targets Tests
# ══════════════════════════════════════════════════════════════

class TestPortfolioTargets:
    """Tests for GET /api/v1/portfolio/targets endpoint."""
    
    def test_targets_returns_200(self, api_client):
        """Test targets endpoint returns 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/targets")
        assert response.status_code == 200
        print("✅ Targets endpoint returns 200 OK")
    
    def test_targets_returns_list(self, api_client):
        """Test targets returns a list."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/targets")
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✅ Targets returns list with {len(data)} targets")
    
    def test_target_fields_structure(self, api_client):
        """Test target objects have required fields."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/targets")
        data = response.json()
        
        if len(data) > 0:
            target = data[0]
            required_fields = [
                "symbol", "target_weight", "direction", "confidence"
            ]
            
            for field in required_fields:
                assert field in target, f"Missing field: {field}"
            
            # Validate ranges
            assert 0 <= target["target_weight"] <= 0.10, f"Target weight out of range: {target['target_weight']}"
            assert 0 <= target["confidence"] <= 1, f"Confidence out of range: {target['confidence']}"
            
            print(f"✅ Target structure valid: {target['symbol']} {target['direction']} {target['target_weight']:.2%}")
        else:
            print("⚠️ No targets to validate structure")


# ══════════════════════════════════════════════════════════════
# 5. GET Risk Tests (Markowitz metrics)
# ══════════════════════════════════════════════════════════════

class TestPortfolioRisk:
    """Tests for GET /api/v1/portfolio/risk endpoint - Markowitz model."""
    
    def test_risk_returns_200(self, api_client):
        """Test risk endpoint returns 200 OK."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/risk")
        assert response.status_code == 200
        print("✅ Risk endpoint returns 200 OK")
    
    def test_risk_has_markowitz_fields(self, api_client):
        """Test risk contains Markowitz portfolio variance and VaR."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/risk")
        data = response.json()
        
        # Markowitz fields
        assert "portfolio_variance" in data, "Missing portfolio_variance (wᵀΣw)"
        assert "portfolio_volatility" in data, "Missing portfolio_volatility"
        assert "portfolio_risk" in data, "Missing portfolio_risk"
        assert "risk_level" in data, "Missing risk_level"
        
        # VaR fields
        assert "var_95_percent" in data, "Missing var_95_percent"
        assert "var_99_percent" in data, "Missing var_99_percent"
        
        # Risk contribution fields
        assert "risk_by_symbol" in data, "Missing risk_by_symbol"
        assert "risk_contribution_by_symbol" in data, "Missing risk_contribution_by_symbol"
        
        # Other risk metrics
        assert "concentration_risk" in data, "Missing concentration_risk"
        assert "correlation_risk" in data, "Missing correlation_risk"
        
        print(f"✅ Risk has Markowitz fields: variance={data['portfolio_variance']:.8f}, VaR95={data['var_95_percent']:.6f}")
    
    def test_risk_level_valid(self, api_client):
        """Test risk level is one of valid values."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/risk")
        data = response.json()
        
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert data["risk_level"] in valid_levels, f"Invalid risk level: {data['risk_level']}"
        
        print(f"✅ Risk level valid: {data['risk_level']}")
    
    def test_var_99_greater_than_var_95(self, api_client):
        """Test VaR 99% >= VaR 95% (higher confidence = higher VaR)."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/risk")
        data = response.json()
        
        # VaR99 should be >= VaR95 (or both 0)
        assert data["var_99_percent"] >= data["var_95_percent"] - 0.0001, \
            f"VaR99 ({data['var_99_percent']}) should be >= VaR95 ({data['var_95_percent']})"
        
        print(f"✅ VaR ordering correct: 99%={data['var_99_percent']:.6f} >= 95%={data['var_95_percent']:.6f}")


# ══════════════════════════════════════════════════════════════
# 6. POST Targets Tests
# ══════════════════════════════════════════════════════════════

class TestSetTargets:
    """Tests for POST /api/v1/portfolio/targets endpoint."""
    
    def test_set_targets_returns_200(self, api_client):
        """Test setting targets returns success."""
        payload = {
            "targets": [
                {
                    "symbol": "BTC",
                    "target_weight": 0.08,
                    "direction": "LONG",
                    "confidence": 0.85,
                    "priority": 1
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/targets", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        print(f"✅ Set targets successful: {data.get('message', '')}")
    
    def test_set_multiple_targets(self, api_client):
        """Test setting multiple targets from hypothesis."""
        payload = {
            "targets": [
                {"symbol": "BTC", "target_weight": 0.08, "direction": "LONG", "confidence": 0.9, "priority": 2},
                {"symbol": "ETH", "target_weight": 0.05, "direction": "LONG", "confidence": 0.7, "priority": 1},
                {"symbol": "SOL", "target_weight": 0.03, "direction": "LONG", "confidence": 0.6, "priority": 0}
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/targets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"]["targets_set"] == 3
        
        print(f"✅ Set 3 targets with total weight: {data['data']['total_target_weight']:.2%}")
    
    def test_target_weight_capped_at_10_percent(self, api_client):
        """Test target weight is capped at 10% (MAX_SINGLE_POSITION)."""
        payload = {
            "targets": [
                {"symbol": "LARGECAP", "target_weight": 0.15, "direction": "LONG", "confidence": 0.8}
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/targets", json=payload)
        assert response.status_code == 200
        
        # Verify target was capped
        targets_response = api_client.get(f"{BASE_URL}/api/v1/portfolio/targets")
        targets = targets_response.json()
        
        largecap_target = next((t for t in targets if t["symbol"] == "LARGECAP"), None)
        if largecap_target:
            assert largecap_target["target_weight"] <= 0.10, \
                f"Target weight not capped: {largecap_target['target_weight']}"
            print(f"✅ Target weight capped at 10%: {largecap_target['target_weight']:.2%}")
        else:
            print("⚠️ LARGECAP target not found after setting")


# ══════════════════════════════════════════════════════════════
# 7. POST Position Tests
# ══════════════════════════════════════════════════════════════

class TestAddPosition:
    """Tests for POST /api/v1/portfolio/position endpoint."""
    
    def test_add_position_success(self, api_client):
        """Test adding a valid position."""
        symbol = generate_unique_symbol()
        payload = {
            "symbol": symbol,
            "direction": "LONG",
            "size_usd": 30000,  # 3% of 1M
            "entry_price": 100,
            "stop_loss": 90,
            "take_profit": 120
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/position", json=payload)
        
        # Might get 400 if position limit/exposure reached
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            print(f"✅ Added position: {symbol} LONG $30,000")
            
            # Cleanup - close the position
            api_client.delete(f"{BASE_URL}/api/v1/portfolio/position/{symbol}")
        else:
            print(f"⚠️ Position add returned {response.status_code}: {response.text[:100]}")
    
    def test_add_position_exceeds_10_percent_rejected(self, api_client):
        """Test position exceeding 10% limit is rejected."""
        symbol = generate_unique_symbol()
        payload = {
            "symbol": symbol,
            "direction": "LONG",
            "size_usd": 150000,  # 15% > 10% limit
            "entry_price": 100,
            "stop_loss": 90,
            "take_profit": 120
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/position", json=payload)
        
        # Should be rejected (400)
        assert response.status_code == 400, \
            f"Expected 400 for exceeding 10% limit, got {response.status_code}"
        
        print("✅ Position exceeding 10% correctly rejected")
    
    def test_add_short_position(self, api_client):
        """Test adding a short position."""
        symbol = generate_unique_symbol()
        payload = {
            "symbol": symbol,
            "direction": "SHORT",
            "size_usd": 20000,  # 2%
            "entry_price": 100,
            "stop_loss": 110,  # Stop above entry for short
            "take_profit": 80   # Target below entry for short
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/position", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            print(f"✅ Added SHORT position: {symbol}")
            
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/v1/portfolio/position/{symbol}")
        else:
            print(f"⚠️ Short position returned {response.status_code}: {response.text[:100]}")


# ══════════════════════════════════════════════════════════════
# 8. DELETE Position Tests
# ══════════════════════════════════════════════════════════════

class TestDeletePosition:
    """Tests for DELETE /api/v1/portfolio/position/{symbol} endpoint."""
    
    def test_delete_nonexistent_position_returns_404(self, api_client):
        """Test deleting non-existent position returns 404."""
        response = api_client.delete(f"{BASE_URL}/api/v1/portfolio/position/NONEXISTENT_999")
        assert response.status_code == 404
        print("✅ Delete non-existent position returns 404")
    
    def test_delete_position_flow(self, api_client):
        """Test create -> delete position flow."""
        symbol = generate_unique_symbol()
        
        # Create position
        create_payload = {
            "symbol": symbol,
            "direction": "LONG",
            "size_usd": 10000,
            "entry_price": 100,
            "stop_loss": 90,
            "take_profit": 120
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/v1/portfolio/position", json=create_payload)
        
        if create_response.status_code != 200:
            pytest.skip(f"Could not create position: {create_response.text[:100]}")
        
        # Delete position
        delete_response = api_client.delete(f"{BASE_URL}/api/v1/portfolio/position/{symbol}")
        assert delete_response.status_code == 200
        
        data = delete_response.json()
        assert data["success"] is True
        
        # Verify position is gone
        verify_response = api_client.delete(f"{BASE_URL}/api/v1/portfolio/position/{symbol}")
        assert verify_response.status_code == 404, "Position should not exist after deletion"
        
        print(f"✅ Create -> Delete flow successful for {symbol}")


# ══════════════════════════════════════════════════════════════
# 9. POST Rebalance Tests
# ══════════════════════════════════════════════════════════════

class TestRebalance:
    """Tests for POST /api/v1/portfolio/rebalance endpoint."""
    
    def test_rebalance_returns_200(self, api_client):
        """Test rebalance endpoint returns 200."""
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/rebalance")
        assert response.status_code == 200
        print("✅ Rebalance endpoint returns 200")
    
    def test_rebalance_response_structure(self, api_client):
        """Test rebalance response has required fields."""
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/rebalance")
        data = response.json()
        
        required_fields = [
            "rebalance_triggered", "reason", "weight_deviations",
            "max_deviation", "positions_to_reduce", "positions_to_increase",
            "new_allocations", "risk_before", "risk_after"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Rebalance response structure valid. Triggered: {data['rebalance_triggered']}")
    
    def test_rebalance_check_endpoint(self, api_client):
        """Test rebalance check endpoint."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/rebalance/check")
        assert response.status_code == 200
        
        data = response.json()
        assert "rebalance_needed" in data
        assert "weight_deviations" in data
        assert "max_deviation" in data
        assert "threshold" in data
        
        # Threshold should be 3% (0.03)
        assert data["threshold"] == 0.03, f"Expected threshold 0.03, got {data['threshold']}"
        
        print(f"✅ Rebalance check: needed={data['rebalance_needed']}, max_deviation={data['max_deviation']:.2%}")


# ══════════════════════════════════════════════════════════════
# 10. GET Constraints Tests
# ══════════════════════════════════════════════════════════════

class TestExecutionConstraints:
    """Tests for GET /api/v1/portfolio/constraints/{symbol} endpoint."""
    
    def test_constraints_returns_200(self, api_client):
        """Test constraints endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/constraints/BTC?direction=LONG")
        assert response.status_code == 200
        print("✅ Constraints endpoint returns 200")
    
    def test_constraints_has_required_fields(self, api_client):
        """Test constraints response has required fields."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/constraints/BTC?direction=LONG")
        data = response.json()
        
        required_fields = [
            "symbol", "direction", "max_position_percent", "max_position_usd",
            "correlation_penalty", "correlated_with", "effective_max_usd"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✅ Constraints valid: max={data['max_position_percent']:.2%}, penalty={data['correlation_penalty']:.2%}")
    
    def test_constraints_respects_10_percent_limit(self, api_client):
        """Test max position is capped at 10%."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/constraints/NEW_ASSET?direction=LONG")
        data = response.json()
        
        assert data["max_position_percent"] <= 0.10, \
            f"Max position exceeds 10%: {data['max_position_percent']}"
        
        print(f"✅ Max position correctly limited to {data['max_position_percent']:.2%}")
    
    def test_constraints_for_short_direction(self, api_client):
        """Test constraints for SHORT direction."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/constraints/SOL?direction=SHORT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["direction"] == "SHORT"
        
        print(f"✅ SHORT constraints: max={data['max_position_percent']:.2%}")


# ══════════════════════════════════════════════════════════════
# 11. POST Validate Execution Tests
# ══════════════════════════════════════════════════════════════

class TestValidateExecution:
    """Tests for POST /api/v1/portfolio/validate-execution endpoint."""
    
    def test_validate_execution_valid_plan(self, api_client):
        """Test validation of valid execution plan."""
        payload = {
            "symbol": "NEW_ASSET",
            "direction": "LONG",
            "size_usd": 50000  # 5%
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/validate-execution", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "adjusted_size_usd" in data["data"]
        
        print(f"✅ Validate execution: approved={data['success']}, adjusted=${data['data']['adjusted_size_usd']:,.0f}")
    
    def test_validate_execution_exceeding_limit_rejected(self, api_client):
        """Test validation rejects execution exceeding limit."""
        payload = {
            "symbol": "LARGE_POSITION",
            "direction": "LONG",
            "size_usd": 150000  # 15% > 10% limit
        }
        
        response = api_client.post(f"{BASE_URL}/api/v1/portfolio/validate-execution", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False, "Should reject position exceeding 10% limit"
        
        # Adjusted size should be max allowed
        assert data["data"]["adjusted_size_usd"] <= 100000, "Adjusted size should be <= 10% of capital"
        
        print(f"✅ Validation correctly rejected 15% position. Suggested: ${data['data']['adjusted_size_usd']:,.0f}")


# ══════════════════════════════════════════════════════════════
# 12. Integration Tests - Exposure Limits
# ══════════════════════════════════════════════════════════════

class TestExposureLimits:
    """Integration tests for 70% exposure limits."""
    
    def test_exposure_limits_enforced(self, api_client):
        """Test 70% exposure limits are enforced."""
        exposure = api_client.get(f"{BASE_URL}/api/v1/portfolio/exposure").json()
        
        # Long exposure should be <= 70%
        assert exposure["long_exposure"] <= 0.70 + 0.01, \
            f"Long exposure exceeds 70%: {exposure['long_exposure']:.2%}"
        
        # Short exposure should be <= 70%
        assert exposure["short_exposure"] <= 0.70 + 0.01, \
            f"Short exposure exceeds 70%: {exposure['short_exposure']:.2%}"
        
        print(f"✅ Exposure limits enforced: long={exposure['long_exposure']:.2%}, short={exposure['short_exposure']:.2%}")
    
    def test_available_capacity_correct(self, api_client):
        """Test available capacity is correctly calculated."""
        exposure = api_client.get(f"{BASE_URL}/api/v1/portfolio/exposure").json()
        
        # Available = 70% - current
        expected_long_available = max(0.70 - exposure["long_exposure"], 0)
        
        assert abs(exposure["available_long_capacity"] - expected_long_available) < 0.01, \
            f"Available long capacity mismatch"
        
        print(f"✅ Available capacity: long={exposure['available_long_capacity']:.2%}, short={exposure['available_short_capacity']:.2%}")


# ══════════════════════════════════════════════════════════════
# 13. Integration Tests - Position Limits
# ══════════════════════════════════════════════════════════════

class TestPositionLimits:
    """Integration tests for 10% single position limit."""
    
    def test_all_positions_within_limit(self, api_client):
        """Test all positions are within 10% limit."""
        positions = api_client.get(f"{BASE_URL}/api/v1/portfolio/positions").json()
        
        for pos in positions:
            assert pos["size_percent"] <= 0.10 + 0.001, \
                f"{pos['symbol']} exceeds 10% limit: {pos['size_percent']:.2%}"
        
        print(f"✅ All {len(positions)} positions within 10% limit")


# ══════════════════════════════════════════════════════════════
# 14. Correlation Tests
# ══════════════════════════════════════════════════════════════

class TestCorrelation:
    """Tests for correlation penalty functionality."""
    
    def test_constraints_include_correlation_penalty(self, api_client):
        """Test constraints include correlation penalty field."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/constraints/BTC?direction=LONG")
        data = response.json()
        
        assert "correlation_penalty" in data
        assert 0 <= data["correlation_penalty"] <= 0.40, \
            f"Correlation penalty out of range: {data['correlation_penalty']}"
        
        print(f"✅ Correlation penalty: {data['correlation_penalty']:.2%}")
    
    def test_effective_max_accounts_for_penalty(self, api_client):
        """Test effective max accounts for correlation penalty."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/constraints/BTC?direction=LONG")
        data = response.json()
        
        expected_effective = data["max_position_usd"] * (1 - data["correlation_penalty"])
        
        assert abs(data["effective_max_usd"] - expected_effective) < 1, \
            f"Effective max mismatch: {data['effective_max_usd']} vs {expected_effective}"
        
        print(f"✅ Effective max: ${data['effective_max_usd']:,.0f} (penalty={data['correlation_penalty']:.2%})")


# ══════════════════════════════════════════════════════════════
# 15. Portfolio History Tests
# ══════════════════════════════════════════════════════════════

class TestPortfolioHistory:
    """Tests for portfolio history endpoints."""
    
    def test_history_returns_200(self, api_client):
        """Test history endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/history")
        assert response.status_code == 200
        print("✅ History endpoint returns 200")
    
    def test_history_stats_returns_200(self, api_client):
        """Test history stats endpoint returns 200."""
        response = api_client.get(f"{BASE_URL}/api/v1/portfolio/history/stats?period_days=30")
        assert response.status_code == 200
        print("✅ History stats endpoint returns 200")


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
