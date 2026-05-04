"""
PHASE 4.2 - Execution Reconciliation API Tests
==============================================

Tests for reconciliation endpoints:
- Health check
- Run reconciliation
- Status
- Discrepancies (all, pending)
- History (all, by run_id)
- Events
- Summary
- Seed endpoints (position, balance, order)
- Demo flow
- Resolve discrepancy
- Clear data
- Discrepancy types verification
- Auto-correction strategies
- PHASE 4.1 Order State compatibility
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestReconciliationHealthAndStatus:
    """Health check and status tests"""

    def test_health_endpoint(self):
        """GET /api/reconciliation/health - should return module name, status=healthy, version"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/health", timeout=10)
        
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("module") == "PHASE 4.2 Execution Reconciliation", f"Unexpected module: {data.get('module')}"
        assert data.get("status") == "healthy", f"Unexpected status: {data.get('status')}"
        assert data.get("version") == "1.0.0", f"Unexpected version: {data.get('version')}"
        assert "engines" in data, "engines field missing"
        assert "timestamp" in data, "timestamp field missing"
        
        print(f"✓ Health endpoint returns: module={data['module']}, status={data['status']}, version={data['version']}")

    def test_status_endpoint(self):
        """GET /api/reconciliation/status - should return engine status with totalRuns and subEngines info"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/status", timeout=10)
        
        assert response.status_code == 200, f"Status check failed: {response.text}"
        
        data = response.json()
        assert "engine" in data, "engine field missing"
        assert data.get("engine") == "ReconciliationEngine", f"Unexpected engine: {data.get('engine')}"
        assert "totalRuns" in data, "totalRuns field missing"
        assert "subEngines" in data, "subEngines field missing"
        
        sub_engines = data.get("subEngines", {})
        assert "positions" in sub_engines, "positions subEngine missing"
        assert "orders" in sub_engines, "orders subEngine missing"
        assert "balances" in sub_engines, "balances subEngine missing"
        assert "resolver" in sub_engines, "resolver subEngine missing"
        
        print(f"✓ Status endpoint returns: engine={data['engine']}, totalRuns={data['totalRuns']}")
        print(f"  SubEngines: {list(sub_engines.keys())}")


class TestSeedEndpoints:
    """Seed endpoints for testing - position, balance, order"""

    def test_seed_position(self):
        """POST /api/reconciliation/seed/position - seed internal position for testing"""
        payload = {
            "symbol": "TESTUSDT",
            "side": "LONG",
            "size": 1.5,
            "entry_price": 50000.0,
            "strategy_id": "TEST_STRATEGY"
        }
        response = requests.post(f"{BASE_URL}/api/reconciliation/seed/position", json=payload, timeout=10)
        
        assert response.status_code == 200, f"Seed position failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, f"Seed position not successful: {data}"
        assert "position" in data, "position field missing"
        
        pos = data["position"]
        assert pos.get("symbol") == "TESTUSDT", f"Unexpected symbol: {pos.get('symbol')}"
        assert pos.get("side") == "LONG", f"Unexpected side: {pos.get('side')}"
        assert pos.get("size") == 1.5, f"Unexpected size: {pos.get('size')}"
        
        print(f"✓ Seed position successful: {pos['symbol']} {pos['side']} {pos['size']}")

    def test_seed_balance(self):
        """POST /api/reconciliation/seed/balance - seed internal balance for testing"""
        payload = {
            "asset": "TESTCOIN",
            "total": 5000.0,
            "available": 4000.0,
            "reserved": 1000.0
        }
        response = requests.post(f"{BASE_URL}/api/reconciliation/seed/balance", json=payload, timeout=10)
        
        assert response.status_code == 200, f"Seed balance failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, f"Seed balance not successful: {data}"
        assert "balance" in data, "balance field missing"
        
        bal = data["balance"]
        assert bal.get("asset") == "TESTCOIN", f"Unexpected asset: {bal.get('asset')}"
        assert bal.get("total") == 5000.0, f"Unexpected total: {bal.get('total')}"
        
        print(f"✓ Seed balance successful: {bal['asset']} total={bal['total']}")

    def test_seed_order(self):
        """POST /api/reconciliation/seed/order - seed internal order for testing"""
        params = {
            "order_id": "test_order_123",
            "symbol": "ETHUSDT",
            "side": "BUY",
            "status": "OPEN",
            "quantity": 2.0,
            "filled_quantity": 0.5
        }
        response = requests.post(f"{BASE_URL}/api/reconciliation/seed/order", params=params, timeout=10)
        
        assert response.status_code == 200, f"Seed order failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, f"Seed order not successful: {data}"
        assert "order" in data, "order field missing"
        
        order = data["order"]
        assert order.get("order_id") == "test_order_123", f"Unexpected order_id: {order.get('order_id')}"
        assert order.get("symbol") == "ETHUSDT", f"Unexpected symbol: {order.get('symbol')}"
        
        print(f"✓ Seed order successful: {order['order_id']} {order['symbol']}")


class TestReconciliationRun:
    """Core reconciliation run tests"""

    def test_run_reconciliation(self):
        """POST /api/reconciliation/run - run full reconciliation cycle"""
        payload = {
            "exchange": "BINANCE",
            "check_positions": True,
            "check_orders": True,
            "check_balances": True
        }
        response = requests.post(f"{BASE_URL}/api/reconciliation/run", json=payload, timeout=30)
        
        assert response.status_code == 200, f"Run reconciliation failed: {response.text}"
        
        data = response.json()
        assert "runId" in data, "runId field missing"
        assert "status" in data, "status field missing"
        assert "results" in data, "results field missing"
        
        results = data.get("results", {})
        assert "detected" in results, "detected count missing in results"
        assert "resolved" in results, "resolved count missing in results"
        assert "failed" in results, "failed count missing in results"
        assert "discrepancies" in results, "discrepancies array missing"
        
        print(f"✓ Run reconciliation completed:")
        print(f"  runId={data['runId']}, status={data['status']}")
        print(f"  detected={results['detected']}, resolved={results['resolved']}, failed={results['failed']}")
        
        return data["runId"]  # Return for use in other tests


class TestDiscrepanciesEndpoints:
    """Discrepancy retrieval tests"""

    def test_get_discrepancies(self):
        """GET /api/reconciliation/discrepancies - should list detected discrepancies"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/discrepancies", timeout=10)
        
        assert response.status_code == 200, f"Get discrepancies failed: {response.text}"
        
        data = response.json()
        assert "discrepancies" in data, "discrepancies field missing"
        assert "count" in data, "count field missing"
        assert isinstance(data["discrepancies"], list), "discrepancies should be a list"
        
        print(f"✓ Got {data['count']} discrepancies")
        
        # Verify discrepancy structure if any exist
        if data["discrepancies"]:
            disc = data["discrepancies"][0]
            assert "discrepancyId" in disc, "discrepancyId field missing"
            assert "type" in disc, "type field missing"
            assert "severity" in disc, "severity field missing"
            print(f"  Sample: type={disc['type']}, severity={disc['severity']}")

    def test_get_discrepancies_with_limit(self):
        """GET /api/reconciliation/discrepancies?limit=10 - test limit parameter"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/discrepancies", params={"limit": 10}, timeout=10)
        
        assert response.status_code == 200, f"Get discrepancies with limit failed: {response.text}"
        
        data = response.json()
        assert len(data.get("discrepancies", [])) <= 10, "Limit not respected"
        
        print(f"✓ Discrepancies with limit=10 returned {len(data.get('discrepancies', []))} items")

    def test_get_pending_discrepancies(self):
        """GET /api/reconciliation/discrepancies/pending - should return only pending discrepancies"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/discrepancies/pending", timeout=10)
        
        assert response.status_code == 200, f"Get pending discrepancies failed: {response.text}"
        
        data = response.json()
        assert "discrepancies" in data, "discrepancies field missing"
        assert "count" in data, "count field missing"
        
        # All returned should be PENDING
        for disc in data.get("discrepancies", []):
            res_status = disc.get("resolution", {}).get("status", "")
            assert res_status == "PENDING", f"Non-pending discrepancy in pending list: {res_status}"
        
        print(f"✓ Got {data['count']} pending discrepancies")


class TestHistoryEndpoints:
    """History and run detail tests"""

    def test_get_history(self):
        """GET /api/reconciliation/history - should list reconciliation run history"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/history", timeout=10)
        
        assert response.status_code == 200, f"Get history failed: {response.text}"
        
        data = response.json()
        assert "runs" in data, "runs field missing"
        assert "count" in data, "count field missing"
        assert isinstance(data["runs"], list), "runs should be a list"
        
        print(f"✓ Got {data['count']} reconciliation runs in history")
        
        # Verify run structure if any exist
        if data["runs"]:
            run = data["runs"][0]
            assert "runId" in run, "runId field missing"
            assert "status" in run, "status field missing"
            assert "timing" in run, "timing field missing"
            print(f"  Latest run: {run['runId']} - {run['status']}")
            
            return run["runId"]
        return None

    def test_get_history_specific_run(self):
        """GET /api/reconciliation/history/{run_id} - should return specific run with events"""
        # First get a valid run_id
        history_response = requests.get(f"{BASE_URL}/api/reconciliation/history", timeout=10)
        if history_response.status_code == 200:
            data = history_response.json()
            if data.get("runs"):
                run_id = data["runs"][0]["runId"]
                
                # Now fetch specific run
                response = requests.get(f"{BASE_URL}/api/reconciliation/history/{run_id}", timeout=10)
                
                assert response.status_code == 200, f"Get specific run failed: {response.text}"
                
                run_data = response.json()
                assert "run" in run_data, "run field missing"
                assert "events" in run_data, "events field missing"
                
                run = run_data["run"]
                assert run.get("runId") == run_id, f"Run ID mismatch"
                
                print(f"✓ Got run {run_id} with {len(run_data.get('events', []))} events")
            else:
                print("⚠ No runs in history to test specific run retrieval")
        else:
            print("⚠ Could not fetch history to get run_id")

    def test_get_history_nonexistent_run(self):
        """GET /api/reconciliation/history/{run_id} - should return 404 for non-existent run"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/history/nonexistent_run_xyz", timeout=10)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        print("✓ Non-existent run returns 404")


class TestEventsEndpoint:
    """Events retrieval test"""

    def test_get_events(self):
        """GET /api/reconciliation/events - should list reconciliation events"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/events", timeout=10)
        
        assert response.status_code == 200, f"Get events failed: {response.text}"
        
        data = response.json()
        assert "events" in data, "events field missing"
        assert "count" in data, "count field missing"
        assert isinstance(data["events"], list), "events should be a list"
        
        print(f"✓ Got {data['count']} reconciliation events")
        
        # Verify event structure if any exist
        if data["events"]:
            evt = data["events"][0]
            assert "eventId" in evt, "eventId field missing"
            assert "eventType" in evt, "eventType field missing"
            assert "timestamp" in evt, "timestamp field missing"
            print(f"  Sample event: {evt['eventType']}")


class TestSummaryEndpoint:
    """Summary endpoint test"""

    def test_get_summary(self):
        """GET /api/reconciliation/summary - should return summary with runs/discrepancies/breakdown"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/summary", timeout=10)
        
        assert response.status_code == 200, f"Get summary failed: {response.text}"
        
        data = response.json()
        assert "runs" in data, "runs field missing"
        assert "discrepancies" in data, "discrepancies field missing"
        assert "breakdown" in data, "breakdown field missing"
        
        runs = data.get("runs", {})
        assert "total" in runs, "runs.total field missing"
        assert "lastAt" in runs, "runs.lastAt field missing"
        
        discrepancies = data.get("discrepancies", {})
        assert "total" in discrepancies, "discrepancies.total field missing"
        assert "pending" in discrepancies, "discrepancies.pending field missing"
        assert "resolved" in discrepancies, "discrepancies.resolved field missing"
        
        breakdown = data.get("breakdown", {})
        assert "byType" in breakdown, "breakdown.byType field missing"
        assert "bySeverity" in breakdown, "breakdown.bySeverity field missing"
        
        print(f"✓ Summary: runs={runs['total']}, discrepancies={discrepancies['total']}")
        print(f"  By type: {breakdown.get('byType', {})}")
        print(f"  By severity: {breakdown.get('bySeverity', {})}")


class TestDemoEndpoint:
    """Demo endpoint test"""

    def test_demo_full_flow(self):
        """POST /api/reconciliation/demo - run full demo with seeded data"""
        response = requests.post(f"{BASE_URL}/api/reconciliation/demo", timeout=30)
        
        assert response.status_code == 200, f"Demo failed: {response.text}"
        
        data = response.json()
        assert data.get("demo") == "complete", f"Demo not complete: {data.get('demo')}"
        assert "run" in data, "run field missing"
        assert "summary" in data, "summary field missing"
        assert "notes" in data, "notes field missing"
        
        run = data.get("run", {})
        assert "runId" in run, "runId missing in run"
        assert "status" in run, "status missing in run"
        
        results = run.get("results", {})
        print(f"✓ Demo completed:")
        print(f"  runId={run.get('runId')}")
        print(f"  status={run.get('status')}")
        print(f"  detected={results.get('detected')}, resolved={results.get('resolved')}")
        
        # Check notes explain the demo
        notes = data.get("notes", [])
        assert len(notes) > 0, "No notes in demo response"
        print(f"  Notes: {notes}")


class TestResolveDiscrepancy:
    """Manual discrepancy resolution test"""

    def test_resolve_discrepancy(self):
        """POST /api/reconciliation/resolve/{discrepancy_id} - manually resolve a discrepancy"""
        # First run a demo to ensure we have discrepancies
        demo_response = requests.post(f"{BASE_URL}/api/reconciliation/demo", timeout=30)
        assert demo_response.status_code == 200, f"Demo failed: {demo_response.text}"
        
        # Get discrepancies
        disc_response = requests.get(f"{BASE_URL}/api/reconciliation/discrepancies", timeout=10)
        assert disc_response.status_code == 200, f"Get discrepancies failed: {disc_response.text}"
        
        data = disc_response.json()
        discrepancies = data.get("discrepancies", [])
        
        if discrepancies:
            disc_id = discrepancies[0].get("discrepancyId")
            
            # Try to resolve it
            resolve_response = requests.post(
                f"{BASE_URL}/api/reconciliation/resolve/{disc_id}",
                params={"action": "sync"},
                timeout=10
            )
            
            assert resolve_response.status_code == 200, f"Resolve failed: {resolve_response.text}"
            
            result = resolve_response.json()
            assert result.get("discrepancyId") == disc_id, "Discrepancy ID mismatch"
            print(f"✓ Resolved discrepancy {disc_id}: status={result.get('resolution', {}).get('status')}")
        else:
            print("⚠ No discrepancies to resolve")

    def test_resolve_nonexistent_discrepancy(self):
        """POST /api/reconciliation/resolve/{discrepancy_id} - 404 for non-existent"""
        response = requests.post(
            f"{BASE_URL}/api/reconciliation/resolve/nonexistent_disc_xyz",
            params={"action": "sync"},
            timeout=10
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        print("✓ Non-existent discrepancy returns 404")


class TestClearEndpoint:
    """Clear endpoint test"""

    def test_clear_all_data(self):
        """DELETE /api/reconciliation/clear - clear all reconciliation data"""
        response = requests.delete(f"{BASE_URL}/api/reconciliation/clear", timeout=10)
        
        assert response.status_code == 200, f"Clear failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, f"Clear not successful: {data}"
        assert data.get("action") == "cleared", f"Unexpected action: {data.get('action')}"
        assert "timestamp" in data, "timestamp field missing"
        
        print(f"✓ Cleared all reconciliation data")
        
        # Verify by checking summary
        summary_response = requests.get(f"{BASE_URL}/api/reconciliation/summary", timeout=10)
        if summary_response.status_code == 200:
            summary = summary_response.json()
            runs = summary.get("runs", {})
            discrepancies = summary.get("discrepancies", {})
            print(f"  After clear: runs={runs.get('total')}, discrepancies={discrepancies.get('total')}")


class TestDiscrepancyTypesVerification:
    """Verify all discrepancy types are detected properly"""

    def test_discrepancy_types_present(self):
        """Verify discrepancy types: GHOST_POSITION, MISSING_POSITION, etc."""
        # Run demo to generate discrepancies
        demo_response = requests.post(f"{BASE_URL}/api/reconciliation/demo", timeout=30)
        assert demo_response.status_code == 200, f"Demo failed: {demo_response.text}"
        
        # Get summary to check breakdown by type
        summary_response = requests.get(f"{BASE_URL}/api/reconciliation/summary", timeout=10)
        assert summary_response.status_code == 200, f"Summary failed: {summary_response.text}"
        
        data = summary_response.json()
        by_type = data.get("breakdown", {}).get("byType", {})
        
        expected_types = [
            "GHOST_POSITION", "MISSING_POSITION", "POSITION_SIZE_MISMATCH",
            "GHOST_ORDER", "MISSING_ORDER", "ORDER_STATE_MISMATCH", "ORDER_FILL_MISMATCH",
            "BALANCE_DRIFT", "MARGIN_MISMATCH"
        ]
        
        found_types = list(by_type.keys())
        print(f"✓ Discrepancy types found: {found_types}")
        
        # At least some types should be detected
        assert len(found_types) > 0, "No discrepancy types detected"
        
        # Check that detected types are valid
        for t in found_types:
            assert t in expected_types, f"Unknown discrepancy type: {t}"


class TestAutoCorrectionStrategies:
    """Verify auto-correction works"""

    def test_auto_correction_strategies(self):
        """Verify auto-correction: SOFT_SYNC, HARD_SYNC, ORDER_RECOVERY, BALANCE_REFRESH"""
        # Run demo
        demo_response = requests.post(f"{BASE_URL}/api/reconciliation/demo", timeout=30)
        assert demo_response.status_code == 200, f"Demo failed: {demo_response.text}"
        
        demo_data = demo_response.json()
        run = demo_data.get("run", {})
        results = run.get("results", {})
        
        detected = results.get("detected", 0)
        resolved = results.get("resolved", 0)
        failed = results.get("failed", 0)
        
        print(f"✓ Auto-correction results:")
        print(f"  Detected: {detected}")
        print(f"  Resolved: {resolved}")
        print(f"  Failed: {failed}")
        
        # Most should be resolved
        if detected > 0:
            resolution_rate = (resolved / detected) * 100
            print(f"  Resolution rate: {resolution_rate:.1f}%")
            assert resolution_rate >= 50, f"Low resolution rate: {resolution_rate}%"
        
        # Check discrepancies for resolution strategies
        discrepancies = results.get("discrepancies", [])
        strategies_used = set()
        for disc in discrepancies:
            strategy = disc.get("resolution", {}).get("strategy", "")
            if strategy:
                strategies_used.add(strategy)
        
        if strategies_used:
            print(f"  Strategies used: {strategies_used}")
        
        expected_strategies = ["SOFT_SYNC", "HARD_SYNC", "ORDER_RECOVERY", "BALANCE_REFRESH"]
        for s in strategies_used:
            assert s in expected_strategies or s in ["MANUAL", "IGNORE"], f"Unknown strategy: {s}"


class TestPhase41Compatibility:
    """Verify existing PHASE 4.1 Order State endpoints still work"""

    def test_orders_health_endpoint(self):
        """GET /api/orders/health - verify PHASE 4.1 still works"""
        response = requests.get(f"{BASE_URL}/api/orders/health", timeout=10)
        
        assert response.status_code == 200, f"Orders health failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Unexpected status: {data.get('status')}"
        
        print(f"✓ PHASE 4.1 Order State Engine health check passed")
        print(f"  Module: {data.get('module', 'N/A')}")
        print(f"  Version: {data.get('version', 'N/A')}")


class TestEdgeCases:
    """Edge case tests"""

    def test_run_with_minimal_options(self):
        """POST /api/reconciliation/run with only positions checked"""
        payload = {
            "exchange": "BINANCE",
            "check_positions": True,
            "check_orders": False,
            "check_balances": False
        }
        response = requests.post(f"{BASE_URL}/api/reconciliation/run", json=payload, timeout=30)
        
        assert response.status_code == 200, f"Run failed: {response.text}"
        
        data = response.json()
        scope = data.get("scope", {})
        assert scope.get("checkPositions") is True, "checkPositions should be True"
        assert scope.get("checkOrders") is False, "checkOrders should be False"
        assert scope.get("checkBalances") is False, "checkBalances should be False"
        
        print(f"✓ Run with positions-only scope completed")

    def test_history_with_limit(self):
        """GET /api/reconciliation/history?limit=5"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/history", params={"limit": 5}, timeout=10)
        
        assert response.status_code == 200, f"History with limit failed: {response.text}"
        
        data = response.json()
        assert len(data.get("runs", [])) <= 5, "Limit not respected"
        
        print(f"✓ History with limit=5 returned {len(data.get('runs', []))} runs")

    def test_events_with_limit(self):
        """GET /api/reconciliation/events?limit=10"""
        response = requests.get(f"{BASE_URL}/api/reconciliation/events", params={"limit": 10}, timeout=10)
        
        assert response.status_code == 200, f"Events with limit failed: {response.text}"
        
        data = response.json()
        assert len(data.get("events", [])) <= 10, "Limit not respected"
        
        print(f"✓ Events with limit=10 returned {len(data.get('events', []))} events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
