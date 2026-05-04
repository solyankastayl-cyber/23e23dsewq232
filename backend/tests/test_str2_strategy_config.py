"""
Test Suite for STR2 - Strategy Configuration Engine
====================================================

Tests all CRUD operations and versioning for strategy configurations.

Endpoints tested:
- POST /api/strategy-configs - Create configuration
- GET /api/strategy-configs - List configurations
- GET /api/strategy-configs/active - Active configuration
- GET /api/strategy-configs/health - Health check
- GET /api/strategy-configs/bounds - Parameter bounds
- GET /api/strategy-configs/parameters/active - Trading parameters
- GET /api/strategy-configs/compare/diff - Compare configurations
- GET /api/strategy-configs/history/activations - Activation history
- POST /api/strategy-configs/validate - Validate parameters
- GET /api/strategy-configs/{id} - Get by ID
- PUT /api/strategy-configs/{id} - Update configuration
- POST /api/strategy-configs/{id}/activate - Activate configuration
- POST /api/strategy-configs/{id}/clone - Clone configuration
- GET /api/strategy-configs/{id}/versions - Get versions
- POST /api/strategy-configs/{id}/rollback - Rollback version
- DELETE /api/strategy-configs/{id} - Delete configuration
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ============================================
# Fixtures
# ============================================

@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_config_id():
    """Generate unique test config ID for tracking"""
    return f"TEST_{uuid.uuid4().hex[:8]}"


# ============================================
# Health and Static Endpoint Tests
# ============================================

class TestHealthAndBounds:
    """Tests for health check and static endpoints"""
    
    def test_health_endpoint(self, api_client):
        """Test /api/strategy-configs/health returns healthy status"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["module"] == "Strategy Configuration Engine"
        assert data["phase"] == "STR2"
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["config_service"]["status"] == "healthy"
        print("✓ Health endpoint working - STR2 module healthy")
    
    def test_bounds_endpoint(self, api_client):
        """Test /api/strategy-configs/bounds returns parameter bounds"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/bounds")
        assert response.status_code == 200
        
        data = response.json()
        assert "bounds" in data
        bounds = data["bounds"]
        
        # Verify key parameters have bounds
        assert "signal_threshold" in bounds
        assert bounds["signal_threshold"]["min"] == 0.4
        assert bounds["signal_threshold"]["max"] == 0.95
        
        assert "leverage_cap" in bounds
        assert bounds["leverage_cap"]["min"] == 1.0
        assert bounds["leverage_cap"]["max"] == 20.0
        
        assert "stop_loss_pct" in bounds
        assert "take_profit_pct" in bounds
        assert "max_trades_per_day" in bounds
        print("✓ Bounds endpoint returns all parameter limits")


# ============================================
# List and Active Config Tests
# ============================================

class TestListAndActiveConfig:
    """Tests for listing and getting active configurations"""
    
    def test_list_configs(self, api_client):
        """Test GET /api/strategy-configs lists all configs"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs")
        assert response.status_code == 200
        
        data = response.json()
        assert "configs" in data
        assert "count" in data
        assert data["count"] >= 3  # At least 3 default configs
        
        # Verify config structure
        for config in data["configs"]:
            assert "config_id" in config
            assert "name" in config
            assert "status" in config
        print(f"✓ List configs returns {data['count']} configurations")
    
    def test_list_configs_with_status_filter(self, api_client):
        """Test filtering configs by status"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs?status=VALIDATED")
        assert response.status_code == 200
        
        data = response.json()
        for config in data["configs"]:
            assert config["status"]["status"] == "VALIDATED"
        print(f"✓ Status filter works - found {data['count']} VALIDATED configs")
    
    def test_get_active_config(self, api_client):
        """Test GET /api/strategy-configs/active returns active config"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/active")
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_id"] == "cfg_balanced"  # Default active
        assert data["status"]["is_active"] is True
        assert data["status"]["status"] == "ACTIVE"
        print(f"✓ Active config is {data['config_id']} ({data['name']})")
    
    def test_get_trading_parameters(self, api_client):
        """Test GET /api/strategy-configs/parameters/active returns parameters"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/parameters/active")
        assert response.status_code == 200
        
        data = response.json()
        assert "parameters" in data
        assert "active_config_id" in data
        
        params = data["parameters"]
        assert "signal_threshold" in params
        assert "leverage_cap" in params
        assert "stop_loss_pct" in params
        assert "max_trades_per_day" in params
        print(f"✓ Trading parameters returned for {data['active_config_id']}")


# ============================================
# Get Config by ID Tests
# ============================================

class TestGetConfigById:
    """Tests for getting specific configurations by ID"""
    
    def test_get_conservative_config(self, api_client):
        """Test GET /api/strategy-configs/cfg_conservative"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/cfg_conservative")
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_id"] == "cfg_conservative"
        assert data["base_profile"] == "CONSERVATIVE"
        assert data["signals"]["entry_threshold"] == 0.8  # Conservative threshold
        print("✓ Conservative config retrieved correctly")
    
    def test_get_balanced_config(self, api_client):
        """Test GET /api/strategy-configs/cfg_balanced"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/cfg_balanced")
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_id"] == "cfg_balanced"
        assert data["base_profile"] == "BALANCED"
        assert data["signals"]["entry_threshold"] == 0.65  # Balanced threshold
        print("✓ Balanced config retrieved correctly")
    
    def test_get_aggressive_config(self, api_client):
        """Test GET /api/strategy-configs/cfg_aggressive"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/cfg_aggressive")
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_id"] == "cfg_aggressive"
        assert data["base_profile"] == "AGGRESSIVE"
        assert data["signals"]["entry_threshold"] == 0.55  # Aggressive threshold
        print("✓ Aggressive config retrieved correctly")
    
    def test_get_nonexistent_config(self, api_client):
        """Test 404 for non-existent config"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/cfg_nonexistent")
        assert response.status_code == 404
        print("✓ Non-existent config returns 404 as expected")


# ============================================
# Create Configuration Tests
# ============================================

class TestCreateConfig:
    """Tests for creating new configurations"""
    
    def test_create_config_basic(self, api_client, test_config_id):
        """Test POST /api/strategy-configs creates new config"""
        response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": f"Test Config {test_config_id}",
            "base_profile": "BALANCED",
            "description": "Test configuration for automated testing"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "config" in data
        assert data["config"]["name"] == f"Test Config {test_config_id}"
        
        # Verify config was persisted
        config_id = data["config"]["config_id"]
        verify_response = api_client.get(f"{BASE_URL}/api/strategy-configs/{config_id}")
        assert verify_response.status_code == 200
        print(f"✓ Created config {config_id} successfully")
        
        # Cleanup - delete test config
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")
    
    def test_create_config_with_overrides(self, api_client):
        """Test creating config with parameter overrides"""
        response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Override_Config",
            "base_profile": "CONSERVATIVE",
            "signal_threshold": 0.75,
            "leverage_cap": 2.5,
            "stop_loss_pct": 0.02,
            "max_trades_per_day": 5
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        config = data["config"]
        assert config["signals"]["entry_threshold"] == 0.75
        assert config["leverage"]["cap"] == 2.5
        assert config["stops"]["stop_loss_pct"] == 0.02
        assert config["frequency"]["max_trades_per_day"] == 5
        print("✓ Config created with parameter overrides")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{config['config_id']}")
    
    def test_create_config_validation_included(self, api_client):
        """Test that create response includes validation"""
        response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Validation_Config",
            "base_profile": "BALANCED"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "validation" in data
        assert data["validation"]["is_valid"] is True
        assert "risk_assessment" in data["validation"]
        print("✓ Validation included in create response")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{data['config']['config_id']}")


# ============================================
# Update Configuration Tests
# ============================================

class TestUpdateConfig:
    """Tests for updating existing configurations"""
    
    def test_update_config_parameters(self, api_client):
        """Test PUT /api/strategy-configs/{id} updates parameters"""
        # First create a config to update
        create_response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Update_Config",
            "base_profile": "BALANCED"
        })
        config_id = create_response.json()["config"]["config_id"]
        original_version = create_response.json()["config"]["versioning"]["version"]
        
        # Update it
        update_response = api_client.put(f"{BASE_URL}/api/strategy-configs/{config_id}", json={
            "signal_threshold": 0.70,
            "leverage_cap": 4.0,
            "change_reason": "Testing parameter update"
        })
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert data["success"] is True
        assert data["config"]["signals"]["entry_threshold"] == 0.70
        assert data["config"]["leverage"]["cap"] == 4.0
        
        # Verify version incremented
        assert data["config"]["versioning"]["version"] == original_version + 1
        print(f"✓ Config {config_id} updated, version now {data['config']['versioning']['version']}")
        
        # Verify persistence
        verify_response = api_client.get(f"{BASE_URL}/api/strategy-configs/{config_id}")
        assert verify_response.json()["signals"]["entry_threshold"] == 0.70
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")
    
    def test_update_nonexistent_config(self, api_client):
        """Test updating non-existent config returns error"""
        response = api_client.put(f"{BASE_URL}/api/strategy-configs/cfg_nonexistent", json={
            "signal_threshold": 0.70
        })
        assert response.status_code == 400
        print("✓ Updating non-existent config returns 400")


# ============================================
# Validate Configuration Tests
# ============================================

class TestValidateConfig:
    """Tests for configuration validation endpoint"""
    
    def test_validate_valid_config(self, api_client):
        """Test POST /api/strategy-configs/validate with valid params"""
        response = api_client.post(f"{BASE_URL}/api/strategy-configs/validate", json={
            "name": "Validation Test",
            "base_profile": "BALANCED",
            "signal_threshold": 0.70,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_valid"] is True
        assert "risk_assessment" in data
        print(f"✓ Valid config validated - risk level: {data['risk_assessment']['level']}")
    
    def test_validate_includes_risk_assessment(self, api_client):
        """Test validation returns risk assessment"""
        response = api_client.post(f"{BASE_URL}/api/strategy-configs/validate", json={
            "name": "Risk Test",
            "base_profile": "AGGRESSIVE",
            "leverage_cap": 10.0,
            "max_position_pct": 0.25
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "risk_assessment" in data
        assert "score" in data["risk_assessment"]
        assert "level" in data["risk_assessment"]
        # High leverage should have higher risk
        assert data["risk_assessment"]["score"] > 0.3
        print(f"✓ Risk assessment: score={data['risk_assessment']['score']}, level={data['risk_assessment']['level']}")


# ============================================
# Compare Configurations Tests
# ============================================

class TestCompareConfigs:
    """Tests for comparing configurations"""
    
    def test_compare_two_configs(self, api_client):
        """Test GET /api/strategy-configs/compare/diff"""
        response = api_client.get(
            f"{BASE_URL}/api/strategy-configs/compare/diff",
            params={"config_a": "cfg_conservative", "config_b": "cfg_aggressive"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_a_id"] == "cfg_conservative"
        assert data["config_b_id"] == "cfg_aggressive"
        assert "differences" in data
        assert "num_differences" in data
        assert data["num_differences"] > 0
        
        # Should show difference in signal threshold
        assert "signal_threshold" in data["differences"]
        print(f"✓ Compared configs - {data['num_differences']} differences found")
    
    def test_compare_includes_risk_change(self, api_client):
        """Test comparison includes risk change assessment"""
        response = api_client.get(
            f"{BASE_URL}/api/strategy-configs/compare/diff",
            params={"config_a": "cfg_conservative", "config_b": "cfg_aggressive"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "risk_change" in data
        # Aggressive should be riskier than conservative
        assert data["risk_change"] in ["INCREASED", "DECREASED", "SAME"]
        print(f"✓ Risk change: {data['risk_change']}")
    
    def test_compare_nonexistent_config(self, api_client):
        """Test comparing with non-existent config returns 404"""
        response = api_client.get(
            f"{BASE_URL}/api/strategy-configs/compare/diff",
            params={"config_a": "cfg_balanced", "config_b": "cfg_nonexistent"}
        )
        assert response.status_code == 404
        print("✓ Comparing with non-existent config returns 404")


# ============================================
# Clone Configuration Tests
# ============================================

class TestCloneConfig:
    """Tests for cloning configurations"""
    
    def test_clone_config(self, api_client):
        """Test POST /api/strategy-configs/{id}/clone"""
        response = api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/clone",
            json={"new_name": "TEST_Cloned_Config"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["config"]["name"] == "TEST_Cloned_Config"
        
        # Verify clone has parent reference
        assert data["config"]["versioning"]["parent_config_id"] == "cfg_balanced"
        
        # Verify clone is persisted
        clone_id = data["config"]["config_id"]
        verify_response = api_client.get(f"{BASE_URL}/api/strategy-configs/{clone_id}")
        assert verify_response.status_code == 200
        print(f"✓ Cloned config {clone_id} created from cfg_balanced")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{clone_id}")
    
    def test_clone_nonexistent_config(self, api_client):
        """Test cloning non-existent config returns error"""
        response = api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_nonexistent/clone",
            json={"new_name": "Should Fail"}
        )
        assert response.status_code == 400
        print("✓ Cloning non-existent config returns 400")


# ============================================
# Activate Configuration Tests
# ============================================

class TestActivateConfig:
    """Tests for activating configurations"""
    
    def test_activate_config(self, api_client):
        """Test POST /api/strategy-configs/{id}/activate"""
        # Activate conservative
        response = api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_conservative/activate",
            json={"reason": "Testing activation"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["config"]["config_id"] == "cfg_conservative"
        
        # Verify it's now active
        active_response = api_client.get(f"{BASE_URL}/api/strategy-configs/active")
        assert active_response.json()["config_id"] == "cfg_conservative"
        print("✓ Activated cfg_conservative successfully")
        
        # Restore balanced as active
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/activate",
            json={"reason": "Restoring default"}
        )
    
    def test_activate_shows_previous_config(self, api_client):
        """Test activation response includes previous config ID"""
        # First ensure balanced is active
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/activate",
            json={"reason": "Setup"}
        )
        
        # Now activate aggressive
        response = api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_aggressive/activate",
            json={"reason": "Testing"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "previous_config_id" in data
        assert data["previous_config_id"] == "cfg_balanced"
        print(f"✓ Previous config was {data['previous_config_id']}")
        
        # Restore balanced
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/activate",
            json={"reason": "Restoring default"}
        )


# ============================================
# Version Management Tests
# ============================================

class TestVersionManagement:
    """Tests for version tracking and rollback"""
    
    def test_get_versions(self, api_client):
        """Test GET /api/strategy-configs/{id}/versions"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/cfg_balanced/versions")
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_id"] == "cfg_balanced"
        assert "versions" in data
        assert len(data["versions"]) >= 1
        
        # Verify version structure
        for version in data["versions"]:
            assert "version_id" in version
            assert "version_number" in version
            assert "parameters" in version
        print(f"✓ Found {len(data['versions'])} versions for cfg_balanced")
    
    def test_update_creates_version(self, api_client):
        """Test that updating config creates new version"""
        # Create config
        create_response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Version_Test",
            "base_profile": "BALANCED"
        })
        config_id = create_response.json()["config"]["config_id"]
        
        # Check initial versions
        versions_before = api_client.get(f"{BASE_URL}/api/strategy-configs/{config_id}/versions").json()
        initial_count = len(versions_before["versions"])
        
        # Update config
        api_client.put(f"{BASE_URL}/api/strategy-configs/{config_id}", json={
            "signal_threshold": 0.72,
            "change_reason": "First update"
        })
        
        # Check versions again
        versions_after = api_client.get(f"{BASE_URL}/api/strategy-configs/{config_id}/versions").json()
        assert len(versions_after["versions"]) == initial_count + 1
        print(f"✓ Update created new version ({initial_count} -> {len(versions_after['versions'])})")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")
    
    def test_rollback_to_version(self, api_client):
        """Test POST /api/strategy-configs/{id}/rollback"""
        # Create and update config
        create_response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Rollback_Test",
            "base_profile": "BALANCED",
            "signal_threshold": 0.65
        })
        config_id = create_response.json()["config"]["config_id"]
        
        # Update it twice
        api_client.put(f"{BASE_URL}/api/strategy-configs/{config_id}", json={
            "signal_threshold": 0.70,
            "change_reason": "Update 1"
        })
        api_client.put(f"{BASE_URL}/api/strategy-configs/{config_id}", json={
            "signal_threshold": 0.75,
            "change_reason": "Update 2"
        })
        
        # Verify current value
        current = api_client.get(f"{BASE_URL}/api/strategy-configs/{config_id}").json()
        assert current["signals"]["entry_threshold"] == 0.75
        
        # Rollback to version 1
        rollback_response = api_client.post(
            f"{BASE_URL}/api/strategy-configs/{config_id}/rollback",
            json={"version_number": 1}
        )
        assert rollback_response.status_code == 200
        
        data = rollback_response.json()
        assert data["success"] is True
        assert data["rolled_back_to_version"] == 1
        print(f"✓ Rolled back to version 1 successfully")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")
    
    def test_rollback_invalid_version(self, api_client):
        """Test rollback to non-existent version returns error"""
        # Create config
        create_response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Invalid_Rollback",
            "base_profile": "BALANCED"
        })
        config_id = create_response.json()["config"]["config_id"]
        
        response = api_client.post(
            f"{BASE_URL}/api/strategy-configs/{config_id}/rollback",
            json={"version_number": 999}
        )
        assert response.status_code == 400
        print("✓ Rollback to invalid version returns 400")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")


# ============================================
# Activation History Tests
# ============================================

class TestActivationHistory:
    """Tests for activation history tracking"""
    
    def test_get_activation_history(self, api_client):
        """Test GET /api/strategy-configs/history/activations"""
        response = api_client.get(f"{BASE_URL}/api/strategy-configs/history/activations")
        assert response.status_code == 200
        
        data = response.json()
        assert "history" in data
        assert "count" in data
        
        # Verify history structure
        for event in data["history"]:
            assert "event_id" in event
            assert "to_config_id" in event
            assert "timestamp" in event
        print(f"✓ Activation history has {data['count']} events")
    
    def test_activation_creates_history_event(self, api_client):
        """Test that activation creates history event"""
        # Get current history count
        before = api_client.get(f"{BASE_URL}/api/strategy-configs/history/activations").json()
        before_count = before["count"]
        
        # Activate a config
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_aggressive/activate",
            json={"reason": "History test"}
        )
        
        # Check history increased
        after = api_client.get(f"{BASE_URL}/api/strategy-configs/history/activations").json()
        assert after["count"] > before_count
        
        # Verify latest event
        latest = after["history"][0]
        assert latest["to_config_id"] == "cfg_aggressive"
        assert latest["reason"] == "History test"
        print(f"✓ Activation created history event (count: {before_count} -> {after['count']})")
        
        # Restore balanced
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/activate",
            json={"reason": "Restoring default"}
        )


# ============================================
# Delete Configuration Tests
# ============================================

class TestDeleteConfig:
    """Tests for deleting configurations"""
    
    def test_delete_custom_config(self, api_client):
        """Test DELETE /api/strategy-configs/{id}"""
        # Create config to delete
        create_response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Delete_Me",
            "base_profile": "BALANCED"
        })
        config_id = create_response.json()["config"]["config_id"]
        
        # Delete it
        delete_response = api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")
        assert delete_response.status_code == 200
        
        data = delete_response.json()
        assert data["success"] is True
        
        # Verify deleted
        verify_response = api_client.get(f"{BASE_URL}/api/strategy-configs/{config_id}")
        assert verify_response.status_code == 404
        print(f"✓ Deleted config {config_id} successfully")
    
    def test_cannot_delete_active_config(self, api_client):
        """Test that active config cannot be deleted"""
        # Get active config
        active = api_client.get(f"{BASE_URL}/api/strategy-configs/active").json()
        
        # Try to delete it
        response = api_client.delete(f"{BASE_URL}/api/strategy-configs/{active['config_id']}")
        assert response.status_code == 400
        print(f"✓ Cannot delete active config {active['config_id']}")


# ============================================
# Parameter Bounds Validation Tests
# ============================================

class TestParameterBoundsValidation:
    """Tests for parameter bounds enforcement"""
    
    def test_signal_threshold_bounds(self, api_client):
        """Test signal_threshold respects bounds (0.4-0.95)"""
        # Too low
        response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Bounds_Low",
            "base_profile": "BALANCED",
            "signal_threshold": 0.3  # Below 0.4 min
        })
        assert response.status_code == 422  # Pydantic validation error
        print("✓ Signal threshold below minimum rejected (422)")
    
    def test_leverage_cap_bounds(self, api_client):
        """Test leverage_cap respects bounds (1-20)"""
        # Too high
        response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Bounds_High",
            "base_profile": "BALANCED",
            "leverage_cap": 25.0  # Above 20 max
        })
        assert response.status_code == 422
        print("✓ Leverage cap above maximum rejected (422)")
    
    def test_holding_bars_consistency(self, api_client):
        """Test min_holding_bars < max_holding_bars validation"""
        response = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Holding_Invalid",
            "base_profile": "BALANCED",
            "min_holding_bars": 50,
            "max_holding_bars": 20  # Invalid: min > max
        })
        # Should fail either via Pydantic or service validation
        assert response.status_code in [400, 422]
        print("✓ Invalid holding bars configuration rejected")


# ============================================
# End-to-End Workflow Tests
# ============================================

class TestE2EWorkflows:
    """End-to-end workflow tests"""
    
    def test_full_config_lifecycle(self, api_client):
        """Test complete lifecycle: create -> update -> activate -> rollback -> delete"""
        # 1. Create
        create_resp = api_client.post(f"{BASE_URL}/api/strategy-configs", json={
            "name": "TEST_Lifecycle_Config",
            "base_profile": "BALANCED",
            "signal_threshold": 0.65
        })
        assert create_resp.status_code == 200
        config_id = create_resp.json()["config"]["config_id"]
        print(f"1. Created config {config_id}")
        
        # 2. Update
        update_resp = api_client.put(f"{BASE_URL}/api/strategy-configs/{config_id}", json={
            "signal_threshold": 0.72,
            "change_reason": "Lifecycle test update"
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["config"]["versioning"]["version"] == 2
        print("2. Updated config to version 2")
        
        # 3. Activate
        activate_resp = api_client.post(
            f"{BASE_URL}/api/strategy-configs/{config_id}/activate",
            json={"reason": "Lifecycle test activation"}
        )
        assert activate_resp.status_code == 200
        print("3. Activated config")
        
        # 4. Verify active
        active = api_client.get(f"{BASE_URL}/api/strategy-configs/active").json()
        assert active["config_id"] == config_id
        print("4. Verified config is active")
        
        # 5. Rollback to v1
        rollback_resp = api_client.post(
            f"{BASE_URL}/api/strategy-configs/{config_id}/rollback",
            json={"version_number": 1}
        )
        assert rollback_resp.status_code == 200
        print("5. Rolled back to version 1")
        
        # 6. Restore balanced as active (so we can delete)
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/activate",
            json={"reason": "Restore for cleanup"}
        )
        print("6. Restored cfg_balanced as active")
        
        # 7. Delete
        delete_resp = api_client.delete(f"{BASE_URL}/api/strategy-configs/{config_id}")
        assert delete_resp.status_code == 200
        print("7. Deleted config")
        
        print("✓ Full lifecycle test passed!")
    
    def test_clone_and_modify_workflow(self, api_client):
        """Test cloning and modifying a configuration"""
        # Clone aggressive
        clone_resp = api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_aggressive/clone",
            json={"new_name": "TEST_Cloned_Aggressive"}
        )
        assert clone_resp.status_code == 200
        clone_id = clone_resp.json()["config"]["config_id"]
        
        # Verify parent reference
        clone = api_client.get(f"{BASE_URL}/api/strategy-configs/{clone_id}").json()
        assert clone["versioning"]["parent_config_id"] == "cfg_aggressive"
        
        # Modify clone
        update_resp = api_client.put(f"{BASE_URL}/api/strategy-configs/{clone_id}", json={
            "signal_threshold": 0.60,
            "leverage_cap": 8.0
        })
        assert update_resp.status_code == 200
        
        # Verify original unchanged
        original = api_client.get(f"{BASE_URL}/api/strategy-configs/cfg_aggressive").json()
        assert original["signals"]["entry_threshold"] == 0.55  # Still original value
        
        print(f"✓ Clone workflow test passed - clone {clone_id} modified independently")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/strategy-configs/{clone_id}")


# ============================================
# Cleanup after all tests
# ============================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_configs(api_client):
    """Cleanup any TEST_ prefixed configs after all tests"""
    yield
    
    # Get all configs and delete test ones
    try:
        response = api_client.get(f"{BASE_URL}/api/strategy-configs?limit=100")
        if response.status_code == 200:
            for config in response.json()["configs"]:
                if config["name"].startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/strategy-configs/{config['config_id']}")
                    print(f"Cleaned up test config: {config['config_id']}")
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    # Ensure balanced is active
    try:
        api_client.post(
            f"{BASE_URL}/api/strategy-configs/cfg_balanced/activate",
            json={"reason": "Test cleanup - restore default"}
        )
    except:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
