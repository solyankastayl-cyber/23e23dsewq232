"""
S3 Capital Allocation Layer Tests
=================================

Tests for the Capital Allocation Layer (S3) including:
- Strategy selection based on ranking and robustness
- Weight calculation with composite score formula
- Allocation plan lifecycle (create, activate, pause, close, delete)
- Rebalancing preview and execution
- Snapshot management
- Policy management
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAllocationHealth:
    """Health check endpoint tests"""
    
    def test_allocation_health(self):
        """Test /api/allocation/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/allocation/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "S3"
        assert "modules" in data
        assert data["modules"]["strategy_selector"] == "ready"
        assert data["modules"]["weight_allocator"] == "ready"
        assert data["modules"]["allocation_engine"] == "ready"
        assert "policies_available" in data
        assert "default" in data["policies_available"]
        print("✓ Health check passed - S3 modules ready")


class TestAllocationPolicies:
    """Allocation policy endpoint tests"""
    
    def test_list_policies(self):
        """Test GET /api/allocation/policies - list all policies"""
        response = requests.get(f"{BASE_URL}/api/allocation/policies")
        assert response.status_code == 200
        
        data = response.json()
        assert "policies" in data
        assert "count" in data
        assert data["count"] >= 3  # default, conservative, aggressive
        
        policy_ids = [p["policy_id"] for p in data["policies"]]
        assert "default" in policy_ids
        assert "conservative" in policy_ids
        assert "aggressive" in policy_ids
        print(f"✓ Listed {data['count']} policies")
    
    def test_get_default_policy(self):
        """Test GET /api/allocation/policies/{id} - get default policy"""
        response = requests.get(f"{BASE_URL}/api/allocation/policies/default")
        assert response.status_code == 200
        
        data = response.json()
        assert data["policy_id"] == "default"
        assert "selection" in data
        assert "robustness" in data
        assert "weights" in data
        assert "rebalance" in data
        assert "score_weights" in data
        
        # Verify score weights sum to 1.0
        score_weights = data["score_weights"]
        total = score_weights["ranking"] + score_weights["robustness"] + score_weights["calmar"] + score_weights["low_dd"]
        assert abs(total - 1.0) < 0.01
        print("✓ Default policy retrieved with valid score weights")
    
    def test_get_conservative_policy(self):
        """Test GET /api/allocation/policies/conservative"""
        response = requests.get(f"{BASE_URL}/api/allocation/policies/conservative")
        assert response.status_code == 200
        
        data = response.json()
        assert data["policy_id"] == "conservative"
        assert data["robustness"]["require_robust"] == True
        assert data["weights"]["max_weight"] == 0.25
        print("✓ Conservative policy retrieved")
    
    def test_get_aggressive_policy(self):
        """Test GET /api/allocation/policies/aggressive"""
        response = requests.get(f"{BASE_URL}/api/allocation/policies/aggressive")
        assert response.status_code == 200
        
        data = response.json()
        assert data["policy_id"] == "aggressive"
        assert data["weights"]["max_strategies"] == 8
        assert data["weights"]["max_weight"] == 0.40
        print("✓ Aggressive policy retrieved")
    
    def test_get_nonexistent_policy(self):
        """Test GET /api/allocation/policies/{id} - 404 for nonexistent"""
        response = requests.get(f"{BASE_URL}/api/allocation/policies/nonexistent_policy")
        assert response.status_code == 404
        print("✓ 404 returned for nonexistent policy")
    
    def test_create_custom_policy(self):
        """Test POST /api/allocation/policies - create custom policy"""
        policy_id = f"test_policy_{int(time.time())}"
        payload = {
            "policy_id": policy_id,
            "name": "Test Custom Policy",
            "min_ranking_score": 0.50,
            "min_trades_count": 30,
            "max_drawdown_threshold": 0.25,
            "require_robust": True,
            "allow_weak": False,
            "allow_overfit": False,
            "max_strategies": 3,
            "max_weight_per_strategy": 0.40,
            "min_weight_per_strategy": 0.10,
            "rebalance_threshold": 0.08
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/policies", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "created"
        assert data["policy"]["policy_id"] == policy_id
        assert data["policy"]["selection"]["min_ranking_score"] == 0.50
        print(f"✓ Custom policy '{policy_id}' created")
        
        # Verify it can be retrieved
        get_response = requests.get(f"{BASE_URL}/api/allocation/policies/{policy_id}")
        assert get_response.status_code == 200
        print(f"✓ Custom policy '{policy_id}' verified via GET")


class TestAllocationPlans:
    """Allocation plan CRUD tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data - create a research experiment first"""
        # Create a research experiment for testing
        exp_payload = {
            "name": f"TEST_Allocation_Exp_{int(time.time())}",
            "description": "Test experiment for allocation testing",
            "strategies": [
                {"strategy_id": "strat_test_1", "name": "Test Strategy 1"},
                {"strategy_id": "strat_test_2", "name": "Test Strategy 2"}
            ],
            "config": {
                "symbol": "BTCUSDT",
                "timeframe": "4h",
                "start_date": "2024-01-01",
                "end_date": "2024-06-30"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/research/experiments", json=exp_payload)
        if response.status_code == 200:
            self.experiment_id = response.json().get("experiment", {}).get("experiment_id")
        else:
            self.experiment_id = "test_exp_placeholder"
        
        yield
        
        # Cleanup - delete test experiment if created
        if hasattr(self, 'experiment_id') and self.experiment_id != "test_exp_placeholder":
            requests.delete(f"{BASE_URL}/api/research/experiments/{self.experiment_id}")
    
    def test_create_allocation_plan(self):
        """Test POST /api/allocation/plans - create allocation plan"""
        payload = {
            "experiment_id": self.experiment_id,
            "total_capital_usd": 100000.0,
            "policy_id": "default",
            "notes": "Test allocation plan"
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "created"
        assert "plan" in data
        
        plan = data["plan"]
        assert "plan_id" in plan
        assert plan["experiment_id"] == self.experiment_id
        assert plan["capital"]["total_usd"] == 100000.0
        assert plan["policy_id"] == "default"
        assert plan["status"] == "DRAFT"
        assert "selection_stats" in plan
        print(f"✓ Allocation plan created: {plan['plan_id']}")
        
        # Store for cleanup
        self.plan_id = plan["plan_id"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{self.plan_id}")
    
    def test_create_plan_with_invalid_capital(self):
        """Test POST /api/allocation/plans - reject negative capital"""
        payload = {
            "experiment_id": "test_exp",
            "total_capital_usd": -1000.0,
            "policy_id": "default"
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/plans", json=payload)
        assert response.status_code == 400
        print("✓ Negative capital rejected with 400")
    
    def test_list_plans(self):
        """Test GET /api/allocation/plans - list all plans"""
        response = requests.get(f"{BASE_URL}/api/allocation/plans")
        assert response.status_code == 200
        
        data = response.json()
        assert "plans" in data
        assert "count" in data
        assert isinstance(data["plans"], list)
        print(f"✓ Listed {data['count']} plans")
    
    def test_list_plans_with_status_filter(self):
        """Test GET /api/allocation/plans?status=DRAFT"""
        response = requests.get(f"{BASE_URL}/api/allocation/plans?status=DRAFT")
        assert response.status_code == 200
        
        data = response.json()
        # All returned plans should be DRAFT
        for plan in data["plans"]:
            assert plan["status"] == "DRAFT"
        print(f"✓ Listed {data['count']} DRAFT plans")


class TestAllocationPlanLifecycle:
    """Test complete allocation plan lifecycle"""
    
    def test_full_plan_lifecycle(self):
        """Test create -> activate -> pause -> close -> delete lifecycle"""
        # Step 1: Create plan
        create_payload = {
            "experiment_id": f"lifecycle_test_{int(time.time())}",
            "total_capital_usd": 50000.0,
            "policy_id": "default",
            "notes": "Lifecycle test plan"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/allocation/plans", json=create_payload)
        assert create_response.status_code == 200
        plan_id = create_response.json()["plan"]["plan_id"]
        assert create_response.json()["plan"]["status"] == "DRAFT"
        print(f"✓ Step 1: Plan created in DRAFT status: {plan_id}")
        
        # Step 2: Get plan by ID
        get_response = requests.get(f"{BASE_URL}/api/allocation/plans/{plan_id}")
        assert get_response.status_code == 200
        assert get_response.json()["plan_id"] == plan_id
        print(f"✓ Step 2: Plan retrieved by ID")
        
        # Step 3: Activate plan
        activate_response = requests.post(f"{BASE_URL}/api/allocation/plans/{plan_id}/activate")
        assert activate_response.status_code == 200
        assert activate_response.json()["status"] == "activated"
        assert activate_response.json()["plan"]["status"] == "ACTIVE"
        assert activate_response.json()["plan"]["timestamps"]["activated_at"] is not None
        print(f"✓ Step 3: Plan activated")
        
        # Step 4: Pause plan
        pause_response = requests.post(f"{BASE_URL}/api/allocation/plans/{plan_id}/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "paused"
        assert pause_response.json()["plan"]["status"] == "PAUSED"
        print(f"✓ Step 4: Plan paused")
        
        # Step 5: Close plan
        close_response = requests.post(f"{BASE_URL}/api/allocation/plans/{plan_id}/close")
        assert close_response.status_code == 200
        assert close_response.json()["status"] == "closed"
        assert close_response.json()["plan"]["status"] == "CLOSED"
        print(f"✓ Step 5: Plan closed")
        
        # Step 6: Delete plan
        delete_response = requests.delete(f"{BASE_URL}/api/allocation/plans/{plan_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"
        print(f"✓ Step 6: Plan deleted")
        
        # Verify deletion
        verify_response = requests.get(f"{BASE_URL}/api/allocation/plans/{plan_id}")
        assert verify_response.status_code == 404
        print(f"✓ Step 7: Deletion verified (404)")
    
    def test_activate_nonexistent_plan(self):
        """Test POST /api/allocation/plans/{id}/activate - 404 for nonexistent"""
        response = requests.post(f"{BASE_URL}/api/allocation/plans/nonexistent_plan_id/activate")
        assert response.status_code == 404
        print("✓ 404 returned for activating nonexistent plan")
    
    def test_pause_nonexistent_plan(self):
        """Test POST /api/allocation/plans/{id}/pause - 404 for nonexistent"""
        response = requests.post(f"{BASE_URL}/api/allocation/plans/nonexistent_plan_id/pause")
        assert response.status_code == 404
        print("✓ 404 returned for pausing nonexistent plan")
    
    def test_close_nonexistent_plan(self):
        """Test POST /api/allocation/plans/{id}/close - 404 for nonexistent"""
        response = requests.post(f"{BASE_URL}/api/allocation/plans/nonexistent_plan_id/close")
        assert response.status_code == 404
        print("✓ 404 returned for closing nonexistent plan")


class TestRebalancing:
    """Rebalancing endpoint tests"""
    
    def test_rebalance_preview(self):
        """Test POST /api/allocation/plans/{id}/rebalance-preview"""
        # Create a plan first
        create_payload = {
            "experiment_id": f"rebalance_test_{int(time.time())}",
            "total_capital_usd": 75000.0,
            "policy_id": "default"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/allocation/plans", json=create_payload)
        assert create_response.status_code == 200
        plan_id = create_response.json()["plan"]["plan_id"]
        
        # Preview rebalance
        preview_response = requests.post(f"{BASE_URL}/api/allocation/plans/{plan_id}/rebalance-preview")
        assert preview_response.status_code == 200
        
        data = preview_response.json()
        assert "plan_id" in data
        assert "changes" in data
        assert "summary" in data
        assert "recommendation" in data
        assert "should_rebalance" in data["recommendation"]
        assert "reason" in data["recommendation"]
        print(f"✓ Rebalance preview returned: should_rebalance={data['recommendation']['should_rebalance']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{plan_id}")
    
    def test_execute_rebalance(self):
        """Test POST /api/allocation/plans/{id}/rebalance"""
        # Create a plan first
        create_payload = {
            "experiment_id": f"rebalance_exec_test_{int(time.time())}",
            "total_capital_usd": 60000.0,
            "policy_id": "default"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/allocation/plans", json=create_payload)
        assert create_response.status_code == 200
        plan_id = create_response.json()["plan"]["plan_id"]
        initial_version = create_response.json()["plan"]["version"]
        
        # Execute rebalance
        rebalance_response = requests.post(f"{BASE_URL}/api/allocation/plans/{plan_id}/rebalance")
        assert rebalance_response.status_code == 200
        
        data = rebalance_response.json()
        assert data["status"] == "rebalanced"
        assert data["version"] == initial_version + 1
        assert "plan" in data
        assert data["plan"]["timestamps"]["last_rebalance_at"] is not None
        print(f"✓ Rebalance executed: version {initial_version} -> {data['version']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{plan_id}")
    
    def test_rebalance_nonexistent_plan(self):
        """Test POST /api/allocation/plans/{id}/rebalance - 404 for nonexistent"""
        response = requests.post(f"{BASE_URL}/api/allocation/plans/nonexistent_plan_id/rebalance")
        assert response.status_code == 404
        print("✓ 404 returned for rebalancing nonexistent plan")


class TestSnapshots:
    """Snapshot endpoint tests"""
    
    def test_get_latest_snapshot(self):
        """Test GET /api/allocation/plans/{id}/latest"""
        # Create a plan first (which creates initial snapshot)
        create_payload = {
            "experiment_id": f"snapshot_test_{int(time.time())}",
            "total_capital_usd": 80000.0,
            "policy_id": "default"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/allocation/plans", json=create_payload)
        assert create_response.status_code == 200
        plan_id = create_response.json()["plan"]["plan_id"]
        
        # Get latest snapshot
        snapshot_response = requests.get(f"{BASE_URL}/api/allocation/plans/{plan_id}/latest")
        assert snapshot_response.status_code == 200
        
        data = snapshot_response.json()
        assert "snapshot_id" in data
        assert data["plan_id"] == plan_id
        assert data["reason"] == "CREATION"
        assert "strategies" in data
        assert "timestamp" in data
        print(f"✓ Latest snapshot retrieved: {data['snapshot_id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{plan_id}")
    
    def test_get_snapshot_history(self):
        """Test GET /api/allocation/plans/{id}/history"""
        # Create a plan
        create_payload = {
            "experiment_id": f"history_test_{int(time.time())}",
            "total_capital_usd": 90000.0,
            "policy_id": "default"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/allocation/plans", json=create_payload)
        assert create_response.status_code == 200
        plan_id = create_response.json()["plan"]["plan_id"]
        
        # Execute rebalance to create another snapshot
        requests.post(f"{BASE_URL}/api/allocation/plans/{plan_id}/rebalance")
        
        # Get history
        history_response = requests.get(f"{BASE_URL}/api/allocation/plans/{plan_id}/history")
        assert history_response.status_code == 200
        
        data = history_response.json()
        assert data["plan_id"] == plan_id
        assert "snapshots" in data
        assert "count" in data
        assert data["count"] >= 2  # CREATION + REBALANCE
        
        # Verify snapshots are ordered by timestamp (newest first)
        snapshots = data["snapshots"]
        if len(snapshots) >= 2:
            assert snapshots[0]["reason"] == "REBALANCE"
            assert snapshots[1]["reason"] == "CREATION"
        print(f"✓ Snapshot history retrieved: {data['count']} snapshots")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{plan_id}")
    
    def test_get_latest_snapshot_no_plan(self):
        """Test GET /api/allocation/plans/{id}/latest - returns null for nonexistent"""
        response = requests.get(f"{BASE_URL}/api/allocation/plans/nonexistent_plan_id/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert data["snapshot"] is None
        print("✓ Null snapshot returned for nonexistent plan")


class TestEligibleStrategies:
    """Eligible strategies endpoint tests"""
    
    def test_get_eligible_strategies(self):
        """Test GET /api/allocation/eligible/{experiment_id}"""
        # Use a test experiment ID
        experiment_id = f"eligible_test_{int(time.time())}"
        
        response = requests.get(f"{BASE_URL}/api/allocation/eligible/{experiment_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["experiment_id"] == experiment_id
        assert data["policy_id"] == "default"
        assert "eligible_strategies" in data
        assert "rejected_strategies" in data
        assert "summary" in data
        assert "total_evaluated" in data["summary"]
        assert "eligible" in data["summary"]
        assert "rejected" in data["summary"]
        print(f"✓ Eligible strategies retrieved: {data['summary']['eligible']} eligible, {data['summary']['rejected']} rejected")
    
    def test_get_eligible_with_policy(self):
        """Test GET /api/allocation/eligible/{experiment_id}?policy_id=conservative"""
        experiment_id = f"eligible_policy_test_{int(time.time())}"
        
        response = requests.get(f"{BASE_URL}/api/allocation/eligible/{experiment_id}?policy_id=conservative")
        assert response.status_code == 200
        
        data = response.json()
        assert data["policy_id"] == "conservative"
        print(f"✓ Eligible strategies with conservative policy retrieved")
    
    def test_eligible_strategy_structure(self):
        """Test eligible strategy response structure"""
        experiment_id = f"structure_test_{int(time.time())}"
        
        response = requests.get(f"{BASE_URL}/api/allocation/eligible/{experiment_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check structure of eligible strategies (if any)
        for strategy in data["eligible_strategies"]:
            assert "strategy_id" in strategy
            assert "scores" in strategy
            assert "metrics" in strategy
            assert "walk_forward" in strategy
            assert "selection" in strategy
            assert strategy["selection"]["is_eligible"] == True
            assert strategy["selection"]["reason"] == "SELECTED"
        
        # Check structure of rejected strategies (if any)
        for strategy in data["rejected_strategies"]:
            assert "strategy_id" in strategy
            assert "selection" in strategy
            assert strategy["selection"]["is_eligible"] == False
            assert strategy["selection"]["reason"] != "SELECTED"
        
        print("✓ Strategy structure validated")


class TestAllocationWithDifferentPolicies:
    """Test allocation with different policies"""
    
    def test_create_plan_with_conservative_policy(self):
        """Test creating plan with conservative policy"""
        payload = {
            "experiment_id": f"conservative_test_{int(time.time())}",
            "total_capital_usd": 100000.0,
            "policy_id": "conservative",
            "notes": "Conservative allocation test"
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["plan"]["policy_id"] == "conservative"
        print(f"✓ Plan created with conservative policy")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{data['plan']['plan_id']}")
    
    def test_create_plan_with_aggressive_policy(self):
        """Test creating plan with aggressive policy"""
        payload = {
            "experiment_id": f"aggressive_test_{int(time.time())}",
            "total_capital_usd": 100000.0,
            "policy_id": "aggressive",
            "notes": "Aggressive allocation test"
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["plan"]["policy_id"] == "aggressive"
        print(f"✓ Plan created with aggressive policy")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{data['plan']['plan_id']}")


class TestAllocationDataValidation:
    """Test allocation data validation and constraints"""
    
    def test_plan_capital_allocation(self):
        """Test that allocated capital doesn't exceed total capital"""
        payload = {
            "experiment_id": f"capital_test_{int(time.time())}",
            "total_capital_usd": 100000.0,
            "policy_id": "default"
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/plans", json=payload)
        assert response.status_code == 200
        
        plan = response.json()["plan"]
        total = plan["capital"]["total_usd"]
        allocated = plan["capital"]["allocated_usd"]
        cash_reserve = plan["capital"]["cash_reserve_usd"]
        
        # Verify capital constraint
        assert allocated + cash_reserve == total
        assert allocated <= total
        print(f"✓ Capital constraint validated: ${allocated} allocated + ${cash_reserve} reserve = ${total} total")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{plan['plan_id']}")
    
    def test_strategy_weight_constraints(self):
        """Test that strategy weights are within policy constraints"""
        payload = {
            "experiment_id": f"weight_test_{int(time.time())}",
            "total_capital_usd": 100000.0,
            "policy_id": "default"
        }
        
        response = requests.post(f"{BASE_URL}/api/allocation/plans", json=payload)
        assert response.status_code == 200
        
        plan = response.json()["plan"]
        strategies = plan["strategies"]
        
        # Get policy constraints
        policy_response = requests.get(f"{BASE_URL}/api/allocation/policies/default")
        policy = policy_response.json()
        max_weight = policy["weights"]["max_weight"]
        min_weight = policy["weights"]["min_weight"]
        
        # Verify weight constraints for each strategy
        for strategy in strategies:
            weight = strategy["allocation"]["target_weight"]
            if strategy["status"]["enabled"]:
                assert weight <= max_weight, f"Weight {weight} exceeds max {max_weight}"
                assert weight >= min_weight, f"Weight {weight} below min {min_weight}"
        
        print(f"✓ Weight constraints validated for {len(strategies)} strategies")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/allocation/plans/{plan['plan_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
