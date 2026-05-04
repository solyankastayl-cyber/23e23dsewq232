"""
Test Suite for SEC2 API Key Vault and State Reconciliation Layer

Modules Tested:
- SEC2 Vault: API Key Vault for secure storage of exchange API keys
- State Reconciliation: Compares internal state with exchange state

Endpoints:
SEC2 Vault:
- /api/vault/health
- POST /api/vault/keys - Create key
- GET /api/vault/keys - List keys
- GET /api/vault/keys/{key_id} - Get key
- POST /api/vault/access-token - Request access token
- GET /api/vault/internal/token/{token_id} - Get token credentials
- POST /api/vault/keys/{key_id}/rotate - Rotate key
- POST /api/vault/keys/{key_id}/disable - Disable key
- POST /api/vault/keys/{key_id}/enable - Enable key
- GET /api/vault/audit - Get audit events

Reconciliation:
- /api/reconciliation/health
- POST /api/reconciliation/run/quick - Run quick reconciliation
- GET /api/reconciliation/mismatches - Get mismatches
- POST /api/reconciliation/quarantine/{exchange} - Quarantine exchange
- DELETE /api/reconciliation/quarantine/{exchange} - Release exchange
- POST /api/reconciliation/mismatches/{id}/resolve - Resolve mismatch
"""

import pytest
import requests
import os
import time
from typing import Optional

# Get base URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://tech-analysis-core-1.preview.emergentagent.com"


# ============================================================
# SEC2 Vault Tests
# ============================================================

class TestVaultHealth:
    """Test Vault health endpoint"""
    
    def test_vault_health_status(self):
        """Test /api/vault/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/vault/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy", f"Expected healthy status, got {data['status']}"
        assert data["version"] == "sec2_v1", f"Expected sec2_v1 version"
        assert data["encryption_enabled"] == True, "Encryption should be enabled"
        assert data["audit_enabled"] == True, "Audit should be enabled"
        assert "total_keys" in data, "Should have total_keys count"
        assert "active_keys" in data, "Should have active_keys count"
        assert "timestamp" in data, "Should have timestamp"
        
        print(f"✓ Vault health: {data['status']}, keys={data['total_keys']}, active={data['active_keys']}")


class TestVaultKeyManagement:
    """Test Vault key CRUD operations"""
    
    created_key_id: Optional[str] = None
    
    def test_01_create_key_with_encryption(self):
        """Test POST /api/vault/keys creates key with AES-256-GCM encryption"""
        payload = {
            "exchange": "BINANCE",
            "account_name": "TEST_account_pytest",
            "api_key": "TEST_api_key_12345_pytest",
            "secret_key": "TEST_secret_key_67890_pytest",
            "permissions": ["READ", "TRADE"],
            "notes": "Test key created by pytest"
        }
        
        response = requests.post(f"{BASE_URL}/api/vault/keys", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "key_id" in data, "Response should have key_id"
        assert data["exchange"] == "BINANCE", f"Exchange should be BINANCE"
        assert data["account_name"] == "TEST_account_pytest", "Account name should match"
        assert "api_key_masked" in data, "Should have masked API key"
        assert "*" in data["api_key_masked"], "API key should be masked with asterisks"
        assert "secret_key" not in data, "Secret key should NEVER be returned in response"
        assert data["status"] == "ACTIVE", "New key should be ACTIVE"
        assert "READ" in data["permissions"], "Should have READ permission"
        assert "TRADE" in data["permissions"], "Should have TRADE permission"
        
        TestVaultKeyManagement.created_key_id = data["key_id"]
        print(f"✓ Created key: {data['key_id']}, masked_api: {data['api_key_masked']}")
    
    def test_02_list_keys_with_masked_secrets(self):
        """Test GET /api/vault/keys returns masked key info"""
        response = requests.get(f"{BASE_URL}/api/vault/keys")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify secrets are never returned
        for key in data:
            assert "secret_key" not in key, "Secret key should NEVER be in list response"
            assert "encrypted_api_key" not in key, "Encrypted data should not be exposed"
            assert "encrypted_secret_key" not in key, "Encrypted data should not be exposed"
            if "api_key_masked" in key:
                assert "*" in key["api_key_masked"], "API key should be masked"
        
        print(f"✓ Listed {len(data)} keys with masked secrets")
    
    def test_03_get_key_by_id(self):
        """Test GET /api/vault/keys/{key_id} returns specific key"""
        if not TestVaultKeyManagement.created_key_id:
            pytest.skip("No key created to test")
        
        key_id = TestVaultKeyManagement.created_key_id
        response = requests.get(f"{BASE_URL}/api/vault/keys/{key_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["key_id"] == key_id, f"Key ID should match"
        assert "secret_key" not in data, "Secret key should NEVER be returned"
        assert data["exchange"] == "BINANCE"
        
        print(f"✓ Retrieved key: {key_id}")
    
    def test_04_get_key_not_found(self):
        """Test GET /api/vault/keys/{key_id} returns 404 for non-existent key"""
        response = requests.get(f"{BASE_URL}/api/vault/keys/nonexistent_key_123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent key returns 404")
    
    def test_05_filter_keys_by_exchange(self):
        """Test GET /api/vault/keys?exchange=BINANCE filters correctly"""
        response = requests.get(f"{BASE_URL}/api/vault/keys?exchange=BINANCE")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for key in data:
            assert key["exchange"] == "BINANCE", f"All keys should be BINANCE"
        
        print(f"✓ Filtered {len(data)} BINANCE keys")


class TestVaultAccessTokens:
    """Test Vault access token flow"""
    
    token_id: Optional[str] = None
    test_key_id: Optional[str] = None
    
    @pytest.fixture(autouse=True)
    def setup_key(self):
        """Ensure we have a key to test with"""
        # First, get existing keys
        response = requests.get(f"{BASE_URL}/api/vault/keys?status=ACTIVE")
        if response.status_code == 200:
            keys = response.json()
            if keys:
                TestVaultAccessTokens.test_key_id = keys[0]["key_id"]
                return
        
        # Create a key if none exist
        payload = {
            "exchange": "BYBIT",
            "account_name": "TEST_token_test_account",
            "api_key": "TEST_token_api_key",
            "secret_key": "TEST_token_secret_key",
            "permissions": ["READ", "TRADE"]
        }
        response = requests.post(f"{BASE_URL}/api/vault/keys", json=payload)
        if response.status_code == 200:
            TestVaultAccessTokens.test_key_id = response.json()["key_id"]
    
    def test_01_request_access_token_success(self):
        """Test POST /api/vault/access-token with allowed service"""
        if not TestVaultAccessTokens.test_key_id:
            pytest.skip("No test key available")
        
        payload = {
            "key_id": TestVaultAccessTokens.test_key_id,
            "scope": "READ",
            "requesting_service": "portfolio_monitor",  # Allowed READ scope
            "ttl_seconds": 300
        }
        
        response = requests.post(f"{BASE_URL}/api/vault/access-token", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token_id" in data, "Response should have token_id"
        assert data["key_id"] == TestVaultAccessTokens.test_key_id
        assert data["scope"] == "READ"
        assert "expires_at" in data, "Token should have expiration"
        
        # Store for later tests
        TestVaultAccessTokens.token_id = data["token_id"]
        print(f"✓ Access token granted: {data['token_id'][:20]}...")
    
    def test_02_get_token_credentials_internal(self):
        """Test GET /api/vault/internal/token/{token_id} returns credentials"""
        if not TestVaultAccessTokens.token_id:
            pytest.skip("No token to test")
        
        token_id = TestVaultAccessTokens.token_id
        response = requests.get(f"{BASE_URL}/api/vault/internal/token/{token_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "api_key" in data, "Should return decrypted api_key"
        assert "secret_key" in data, "Should return decrypted secret_key"
        assert data["key_id"] == TestVaultAccessTokens.test_key_id
        assert "expires_at" in data
        
        print(f"✓ Token credentials retrieved for key: {data['key_id']}")
    
    def test_03_permission_policy_service_not_allowed(self):
        """Test that service requesting scope it's not allowed fails"""
        if not TestVaultAccessTokens.test_key_id:
            pytest.skip("No test key available")
        
        # portfolio_monitor is only allowed READ scope, not TRADE
        payload = {
            "key_id": TestVaultAccessTokens.test_key_id,
            "scope": "TRADE",  # Not allowed for portfolio_monitor
            "requesting_service": "portfolio_monitor",
            "ttl_seconds": 300
        }
        
        response = requests.post(f"{BASE_URL}/api/vault/access-token", json=payload)
        
        # Should be denied (403)
        assert response.status_code == 403, f"Expected 403 for unauthorized scope, got {response.status_code}"
        
        data = response.json()
        assert "not allowed" in data.get("detail", "").lower() or "service" in data.get("detail", "").lower(), \
            f"Error should mention service not allowed: {data}"
        
        print(f"✓ Permission denied for unauthorized scope: {data.get('detail')}")
    
    def test_04_invalid_token_returns_404(self):
        """Test GET /api/vault/internal/token/{invalid} returns 404"""
        response = requests.get(f"{BASE_URL}/api/vault/internal/token/invalid_token_xyz")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid token returns 404")


class TestVaultKeyLifecycle:
    """Test key rotation, disable, enable lifecycle"""
    
    lifecycle_key_id: Optional[str] = None
    
    def test_01_create_key_for_lifecycle(self):
        """Create a key for lifecycle tests"""
        payload = {
            "exchange": "OKX",
            "account_name": "TEST_lifecycle_account",
            "api_key": "TEST_lifecycle_api_key",
            "secret_key": "TEST_lifecycle_secret_key",
            "permissions": ["READ", "TRADE"]
        }
        
        response = requests.post(f"{BASE_URL}/api/vault/keys", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        TestVaultKeyLifecycle.lifecycle_key_id = response.json()["key_id"]
        print(f"✓ Created lifecycle test key: {TestVaultKeyLifecycle.lifecycle_key_id}")
    
    def test_02_disable_key(self):
        """Test POST /api/vault/keys/{key_id}/disable"""
        if not TestVaultKeyLifecycle.lifecycle_key_id:
            pytest.skip("No lifecycle key")
        
        key_id = TestVaultKeyLifecycle.lifecycle_key_id
        response = requests.post(
            f"{BASE_URL}/api/vault/keys/{key_id}/disable",
            params={"reason": "Testing disable functionality"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        
        # Verify key is disabled
        check_response = requests.get(f"{BASE_URL}/api/vault/keys/{key_id}")
        assert check_response.status_code == 200
        assert check_response.json()["status"] == "DISABLED"
        
        print(f"✓ Key {key_id} disabled")
    
    def test_03_enable_key(self):
        """Test POST /api/vault/keys/{key_id}/enable"""
        if not TestVaultKeyLifecycle.lifecycle_key_id:
            pytest.skip("No lifecycle key")
        
        key_id = TestVaultKeyLifecycle.lifecycle_key_id
        response = requests.post(f"{BASE_URL}/api/vault/keys/{key_id}/enable")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        
        # Verify key is active
        check_response = requests.get(f"{BASE_URL}/api/vault/keys/{key_id}")
        assert check_response.status_code == 200
        assert check_response.json()["status"] == "ACTIVE"
        
        print(f"✓ Key {key_id} enabled")
    
    def test_04_rotate_key(self):
        """Test POST /api/vault/keys/{key_id}/rotate creates new key"""
        if not TestVaultKeyLifecycle.lifecycle_key_id:
            pytest.skip("No lifecycle key")
        
        old_key_id = TestVaultKeyLifecycle.lifecycle_key_id
        payload = {
            "new_api_key": "TEST_rotated_api_key_new",
            "new_secret_key": "TEST_rotated_secret_key_new"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vault/keys/{old_key_id}/rotate",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        new_key_id = data["key_id"]
        assert new_key_id != old_key_id, "New key should have different ID"
        assert data["status"] == "ACTIVE", "New key should be ACTIVE"
        
        # Verify old key is marked as ROTATED
        check_response = requests.get(f"{BASE_URL}/api/vault/keys/{old_key_id}")
        assert check_response.status_code == 200
        assert check_response.json()["status"] == "ROTATED"
        
        # Update lifecycle_key_id to new key for cleanup
        TestVaultKeyLifecycle.lifecycle_key_id = new_key_id
        
        print(f"✓ Key rotated: {old_key_id} -> {new_key_id}")


class TestVaultAudit:
    """Test Vault audit trail"""
    
    def test_01_get_audit_events(self):
        """Test GET /api/vault/audit returns audit trail"""
        response = requests.get(f"{BASE_URL}/api/vault/audit?limit=50")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "events" in data, "Should have events list"
        assert "count" in data, "Should have count"
        
        # Verify audit events have required fields
        if data["events"]:
            event = data["events"][0]
            assert "event_id" in event
            assert "key_id" in event
            assert "action" in event
            assert "service" in event
            assert "created_at" in event
        
        print(f"✓ Retrieved {data['count']} audit events")
    
    def test_02_audit_by_action(self):
        """Test GET /api/vault/audit?action=CREATE filters by action"""
        response = requests.get(f"{BASE_URL}/api/vault/audit?action=CREATE&limit=20")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for event in data.get("events", []):
            assert event["action"] == "CREATE", f"All events should be CREATE"
        
        print(f"✓ Filtered {data['count']} CREATE events")


# ============================================================
# Reconciliation Tests
# ============================================================

class TestReconciliationHealth:
    """Test Reconciliation health endpoint"""
    
    def test_reconciliation_health_status(self):
        """Test /api/reconciliation/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy", f"Expected healthy status"
        assert data["version"] == "recon_v1", "Expected recon_v1 version"
        assert "active_exchanges" in data
        assert "quarantined_exchanges" in data
        assert "mismatches_unresolved" in data
        assert "timestamp" in data
        
        print(f"✓ Reconciliation health: {data['status']}, exchanges={data['active_exchanges']}")


class TestReconciliationRunQuick:
    """Test quick reconciliation run"""
    
    run_id: Optional[str] = None
    
    def test_01_run_quick_reconciliation(self):
        """Test POST /api/reconciliation/run/quick executes reconciliation"""
        response = requests.post(f"{BASE_URL}/api/reconciliation/run/quick")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "run_id" in data, "Should have run_id"
        assert "status" in data, "Should have status"
        assert data["status"] in ["COMPLETED", "PARTIAL", "RUNNING"], f"Status should be valid"
        assert "exchanges" in data, "Should list exchanges checked"
        assert "total_mismatches" in data
        
        TestReconciliationRunQuick.run_id = data["run_id"]
        print(f"✓ Quick reconciliation completed: run_id={data['run_id']}, status={data['status']}, mismatches={data['total_mismatches']}")
    
    def test_02_get_run_by_id(self):
        """Test GET /api/reconciliation/runs/{run_id} returns run details"""
        if not TestReconciliationRunQuick.run_id:
            pytest.skip("No run ID available")
        
        run_id = TestReconciliationRunQuick.run_id
        response = requests.get(f"{BASE_URL}/api/reconciliation/runs/{run_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["run_id"] == run_id
        assert "results" in data
        
        print(f"✓ Retrieved run: {run_id}")
    
    def test_03_get_recent_runs(self):
        """Test GET /api/reconciliation/runs returns recent runs"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/runs?limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "runs" in data
        assert "count" in data
        
        print(f"✓ Retrieved {data['count']} recent runs")


class TestReconciliationMismatches:
    """Test mismatch retrieval and resolution"""
    
    mismatch_id: Optional[str] = None
    
    def test_01_get_mismatches(self):
        """Test GET /api/reconciliation/mismatches returns mismatches"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/mismatches?limit=50")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "mismatches" in data
        assert "count" in data
        
        # Store a mismatch ID for resolution test
        if data["mismatches"]:
            TestReconciliationMismatches.mismatch_id = data["mismatches"][0]["mismatch_id"]
        
        print(f"✓ Retrieved {data['count']} mismatches")
    
    def test_02_get_critical_mismatches(self):
        """Test GET /api/reconciliation/mismatches/critical returns critical only"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/mismatches/critical")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "mismatches" in data
        assert data.get("severity") == "CRITICAL"
        
        # Verify all returned are critical
        for mismatch in data.get("mismatches", []):
            assert mismatch["severity"] == "CRITICAL"
        
        print(f"✓ Retrieved {data['count']} critical mismatches")
    
    def test_03_resolve_mismatch(self):
        """Test POST /api/reconciliation/mismatches/{id}/resolve marks as resolved"""
        if not TestReconciliationMismatches.mismatch_id:
            pytest.skip("No mismatch to resolve")
        
        mismatch_id = TestReconciliationMismatches.mismatch_id
        response = requests.post(
            f"{BASE_URL}/api/reconciliation/mismatches/{mismatch_id}/resolve",
            params={"notes": "Resolved by pytest"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        assert data["mismatch"]["resolved"] == True
        assert data["mismatch"]["resolved_at"] is not None
        
        print(f"✓ Resolved mismatch: {mismatch_id}")


class TestReconciliationQuarantine:
    """Test quarantine management"""
    
    test_exchange = "TESTEXCHANGE"
    
    def test_01_quarantine_exchange(self):
        """Test POST /api/reconciliation/quarantine/{exchange} quarantines exchange"""
        response = requests.post(
            f"{BASE_URL}/api/reconciliation/quarantine/{TestReconciliationQuarantine.test_exchange}",
            params={"reason": "Testing quarantine feature"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        assert "quarantine" in data
        assert data["quarantine"]["exchange"] == TestReconciliationQuarantine.test_exchange
        
        print(f"✓ Quarantined exchange: {TestReconciliationQuarantine.test_exchange}")
    
    def test_02_get_quarantined_list(self):
        """Test GET /api/reconciliation/quarantine returns quarantined exchanges"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/quarantine")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "quarantined" in data
        assert "count" in data
        
        # Verify our test exchange is in quarantine
        exchanges = [q["exchange"] for q in data["quarantined"]]
        assert TestReconciliationQuarantine.test_exchange in exchanges
        
        print(f"✓ Retrieved {data['count']} quarantined exchanges")
    
    def test_03_release_exchange(self):
        """Test DELETE /api/reconciliation/quarantine/{exchange} releases exchange"""
        response = requests.delete(
            f"{BASE_URL}/api/reconciliation/quarantine/{TestReconciliationQuarantine.test_exchange}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        
        # Verify exchange is no longer in quarantine
        check_response = requests.get(f"{BASE_URL}/api/reconciliation/quarantine")
        quarantined = [q["exchange"] for q in check_response.json()["quarantined"]]
        assert TestReconciliationQuarantine.test_exchange not in quarantined
        
        print(f"✓ Released exchange: {TestReconciliationQuarantine.test_exchange}")
    
    def test_04_release_not_quarantined_returns_404(self):
        """Test DELETE for non-quarantined exchange returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/reconciliation/quarantine/NOTQUARANTINED"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-quarantined exchange release returns 404")


class TestReconciliationStats:
    """Test reconciliation statistics endpoints"""
    
    def test_01_get_summary(self):
        """Test GET /api/reconciliation/summary returns summary"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "last_run" in data or data.get("last_run") is None
        assert "exchanges_in_sync" in data
        assert "quarantined_exchanges" in data
        
        print(f"✓ Reconciliation summary retrieved")
    
    def test_02_get_stats(self):
        """Test GET /api/reconciliation/stats returns statistics"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "runs_24h" in data
        assert "mismatches_24h" in data
        
        print(f"✓ Stats: runs_24h={data['runs_24h']}, mismatches_24h={data['mismatches_24h']}")
    
    def test_03_get_exchange_status(self):
        """Test GET /api/reconciliation/exchanges returns exchange status"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/exchanges")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "exchanges" in data
        assert "total" in data
        assert "in_sync" in data
        assert "quarantined" in data
        
        print(f"✓ Exchange status: total={data['total']}, in_sync={data['in_sync']}")


# ============================================================
# Cleanup Fixture
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Clean up test data after all tests complete"""
    yield
    
    # Clean up test keys
    print("\n--- Cleaning up test data ---")
    
    response = requests.get(f"{BASE_URL}/api/vault/keys")
    if response.status_code == 200:
        keys = response.json()
        for key in keys:
            if "TEST_" in key.get("account_name", ""):
                delete_response = requests.delete(
                    f"{BASE_URL}/api/vault/keys/{key['key_id']}",
                    params={"reason": "Pytest cleanup"}
                )
                if delete_response.status_code == 200:
                    print(f"  Deleted test key: {key['key_id']}")
    
    # Clean up test quarantine entries
    quarantine_response = requests.get(f"{BASE_URL}/api/reconciliation/quarantine")
    if quarantine_response.status_code == 200:
        quarantined = quarantine_response.json().get("quarantined", [])
        for q in quarantined:
            if "TEST" in q.get("exchange", ""):
                requests.delete(f"{BASE_URL}/api/reconciliation/quarantine/{q['exchange']}")
                print(f"  Released test quarantine: {q['exchange']}")
    
    print("--- Cleanup complete ---\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
