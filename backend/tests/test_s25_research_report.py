"""
Test S2.5 Research Report Module
================================

Tests for the Research Report endpoints that bridge Research (S2) with Capital Allocation (S3).

Endpoints tested:
- GET /api/research/experiments/{id}/report - Full research report
- GET /api/research/experiments/{id}/summary - Quick experiment summary
- GET /api/research/experiments/{id}/leaderboard - Strategy leaderboard
- GET /api/research/experiments/{id}/diagnostics - Strategy diagnostics with quality flags
- GET /api/research/experiments/{id}/allocation-candidates - Allocation readiness (S2->S3 bridge)
- GET /api/research/experiments/{id}/warnings - Warnings with level filter
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test experiment ID (created by previous tests)
TEST_EXPERIMENT_ID = "exp_48948f61"


class TestResearchReportHealth:
    """Health check tests for Research module"""
    
    def test_research_health_endpoint(self):
        """Test /api/research/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/research/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "modules" in data
        assert data["modules"]["experiment_manager"] == "ready"
        assert data["modules"]["ranking_engine"] == "ready"


class TestFullResearchReport:
    """Tests for GET /api/research/experiments/{id}/report"""
    
    def test_get_full_report_success(self):
        """Test full report returns all required sections"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/report")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify report structure
        assert "report_id" in data
        assert "experiment_id" in data
        assert data["experiment_id"] == TEST_EXPERIMENT_ID
        
        # Verify experiment_summary section
        assert "experiment_summary" in data
        summary = data["experiment_summary"]
        assert "name" in summary
        assert "asset" in summary
        assert "timeframe" in summary
        assert "start_date" in summary
        assert "end_date" in summary
        assert "initial_capital_usd" in summary
        assert "strategies_tested" in summary
        
        # Verify winner section
        assert "winner" in data
        assert "strategy_id" in data["winner"]
        assert "score" in data["winner"]
        
        # Verify leaderboard section
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        
        # Verify walk_forward_analysis section
        assert "walk_forward_analysis" in data
        assert "has_data" in data["walk_forward_analysis"]
        assert "strategies" in data["walk_forward_analysis"]
        
        # Verify strategy_diagnostics section
        assert "strategy_diagnostics" in data
        assert isinstance(data["strategy_diagnostics"], list)
        
        # Verify warnings section
        assert "warnings" in data
        assert isinstance(data["warnings"], list)
        
        # Verify allocation_readiness section (S2->S3 bridge)
        assert "allocation_readiness" in data
        assert "total_eligible" in data["allocation_readiness"]
        assert "candidates" in data["allocation_readiness"]
        
        # Verify metadata section
        assert "metadata" in data
        assert "generated_at" in data["metadata"]
        assert "report_version" in data["metadata"]
    
    def test_report_regenerate_parameter(self):
        """Test regenerate=true creates new report"""
        # Get first report
        response1 = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/report")
        assert response1.status_code == 200
        report_id_1 = response1.json()["report_id"]
        
        # Regenerate report
        response2 = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/report?regenerate=true")
        assert response2.status_code == 200
        report_id_2 = response2.json()["report_id"]
        
        # Report IDs should be different
        assert report_id_1 != report_id_2
    
    def test_report_leaderboard_entries_structure(self):
        """Test leaderboard entries have correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/report")
        assert response.status_code == 200
        
        data = response.json()
        leaderboard = data["leaderboard"]
        
        if len(leaderboard) > 0:
            entry = leaderboard[0]
            assert "rank" in entry
            assert "strategy_id" in entry
            assert "sharpe_ratio" in entry
            assert "sortino_ratio" in entry
            assert "profit_factor" in entry
            assert "calmar_ratio" in entry
            assert "max_drawdown_pct" in entry
            assert "win_rate" in entry
            assert "trades_count" in entry
            assert "composite_score" in entry
            assert "is_winner" in entry
            
            # First entry should be winner
            assert entry["rank"] == 1
            assert entry["is_winner"] == True


class TestExperimentSummary:
    """Tests for GET /api/research/experiments/{id}/summary"""
    
    def test_get_summary_success(self):
        """Test summary endpoint returns quick view"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/summary")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify summary structure
        assert data["experiment_id"] == TEST_EXPERIMENT_ID
        assert "name" in data
        assert "asset" in data
        assert "timeframe" in data
        assert "period" in data
        assert "strategies_tested" in data
        
        # Verify winner info
        assert "winner" in data
        assert "strategy_id" in data["winner"]
        assert "score" in data["winner"]
        
        # Verify walkforward flag
        assert "has_walkforward_data" in data
        
        # Verify allocation eligible count
        assert "allocation_eligible" in data
        
        # Verify warning counts
        assert "warning_counts" in data
        assert "critical" in data["warning_counts"]
        assert "warning" in data["warning_counts"]
        assert "info" in data["warning_counts"]
        
        # Verify generated_at timestamp
        assert "generated_at" in data


class TestLeaderboard:
    """Tests for GET /api/research/experiments/{id}/leaderboard"""
    
    def test_get_leaderboard_success(self):
        """Test leaderboard endpoint returns ranked strategies"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["experiment_id"] == TEST_EXPERIMENT_ID
        assert "leaderboard" in data
        assert "count" in data
        assert isinstance(data["leaderboard"], list)
        assert data["count"] == len(data["leaderboard"])
    
    def test_leaderboard_ranking_order(self):
        """Test leaderboard is ordered by rank"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        leaderboard = data["leaderboard"]
        
        if len(leaderboard) > 1:
            for i in range(len(leaderboard) - 1):
                assert leaderboard[i]["rank"] < leaderboard[i + 1]["rank"]


class TestDiagnostics:
    """Tests for GET /api/research/experiments/{id}/diagnostics"""
    
    def test_get_diagnostics_success(self):
        """Test diagnostics endpoint returns strategy details"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/diagnostics")
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["experiment_id"] == TEST_EXPERIMENT_ID
        assert "diagnostics" in data
        assert "count" in data
        assert isinstance(data["diagnostics"], list)
    
    def test_diagnostics_structure(self):
        """Test diagnostics entries have correct structure with quality flags"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/diagnostics")
        assert response.status_code == 200
        
        data = response.json()
        diagnostics = data["diagnostics"]
        
        if len(diagnostics) > 0:
            diag = diagnostics[0]
            
            # Verify strategy_id
            assert "strategy_id" in diag
            
            # Verify performance section
            assert "performance" in diag
            assert "sharpe_ratio" in diag["performance"]
            assert "sortino_ratio" in diag["performance"]
            assert "profit_factor" in diag["performance"]
            assert "expectancy" in diag["performance"]
            
            # Verify risk section
            assert "risk" in diag
            assert "max_drawdown_pct" in diag["risk"]
            assert "calmar_ratio" in diag["risk"]
            assert "recovery_factor" in diag["risk"]
            assert "volatility_annual" in diag["risk"]
            
            # Verify trade_stats section
            assert "trade_stats" in diag
            assert "trades_count" in diag["trade_stats"]
            assert "win_rate" in diag["trade_stats"]
            
            # Verify returns section
            assert "returns" in diag
            assert "total_return_pct" in diag["returns"]
            assert "annual_return_pct" in diag["returns"]
            
            # Verify warnings list
            assert "warnings" in diag
            assert isinstance(diag["warnings"], list)
            
            # Verify quality_flags section (key feature)
            assert "quality_flags" in diag
            assert "has_valid_metrics" in diag["quality_flags"]
            assert "has_sufficient_trades" in diag["quality_flags"]
            assert "has_acceptable_drawdown" in diag["quality_flags"]


class TestAllocationCandidates:
    """Tests for GET /api/research/experiments/{id}/allocation-candidates (S2->S3 bridge)"""
    
    def test_get_allocation_candidates_success(self):
        """Test allocation candidates endpoint returns eligibility assessment"""
        # Force regenerate to get fresh data
        requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/report?regenerate=true")
        
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/allocation-candidates")
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["experiment_id"] == TEST_EXPERIMENT_ID
        assert "candidates" in data
        assert "eligible_count" in data
        assert "rejected_count" in data
        
        # These fields are only present when there are candidates
        if len(data["candidates"]) > 0:
            assert "eligible_strategies" in data
            assert "rejection_summary" in data
            # Verify counts match
            assert data["eligible_count"] + data["rejected_count"] == len(data["candidates"])
    
    def test_allocation_candidate_structure(self):
        """Test allocation candidate entries have eligibility_checks"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/allocation-candidates")
        assert response.status_code == 200
        
        data = response.json()
        candidates = data["candidates"]
        
        if len(candidates) > 0:
            candidate = candidates[0]
            
            # Verify basic fields
            assert "strategy_id" in candidate
            assert "eligible_for_allocation" in candidate
            assert "recommended_weight" in candidate
            
            # Verify scores section
            assert "scores" in candidate
            assert "ranking" in candidate["scores"]
            assert "robustness" in candidate["scores"]
            assert "combined" in candidate["scores"]
            
            # Verify rejection_reason
            assert "rejection_reason" in candidate
            
            # Verify eligibility_checks section (key feature for S2->S3 bridge)
            assert "eligibility_checks" in candidate
            checks = candidate["eligibility_checks"]
            assert "passes_ranking" in checks
            assert "passes_robustness" in checks
            assert "passes_risk" in checks
            assert "passes_sample_size" in checks
            
            # Verify allocation_params section
            assert "allocation_params" in candidate
            assert "max_recommended_weight" in candidate["allocation_params"]
            assert "risk_adjustment_factor" in candidate["allocation_params"]
    
    def test_rejection_summary_matches_candidates(self):
        """Test rejection_summary contains all rejected strategies"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/allocation-candidates")
        assert response.status_code == 200
        
        data = response.json()
        
        rejected_candidates = [c for c in data["candidates"] if not c["eligible_for_allocation"]]
        
        # Each rejected candidate should be in rejection_summary
        for candidate in rejected_candidates:
            assert candidate["strategy_id"] in data["rejection_summary"]
            assert data["rejection_summary"][candidate["strategy_id"]] == candidate["rejection_reason"]


class TestWarnings:
    """Tests for GET /api/research/experiments/{id}/warnings"""
    
    def test_get_warnings_success(self):
        """Test warnings endpoint returns all warnings"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/warnings")
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["experiment_id"] == TEST_EXPERIMENT_ID
        assert "warnings" in data
        assert "count" in data
        assert isinstance(data["warnings"], list)
        assert data["count"] == len(data["warnings"])
    
    def test_warning_structure(self):
        """Test warning entries have correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/warnings")
        assert response.status_code == 200
        
        data = response.json()
        warnings = data["warnings"]
        
        if len(warnings) > 0:
            warning = warnings[0]
            assert "code" in warning
            assert "level" in warning
            assert "strategy_id" in warning
            assert "message" in warning
            
            # Level should be valid
            assert warning["level"] in ["CRITICAL", "WARNING", "INFO"]
    
    def test_warnings_filter_critical(self):
        """Test warnings filter by CRITICAL level"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/warnings?level=CRITICAL")
        assert response.status_code == 200
        
        data = response.json()
        
        # All warnings should be CRITICAL
        for warning in data["warnings"]:
            assert warning["level"] == "CRITICAL"
    
    def test_warnings_filter_warning(self):
        """Test warnings filter by WARNING level"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/warnings?level=WARNING")
        assert response.status_code == 200
        
        data = response.json()
        
        # All warnings should be WARNING
        for warning in data["warnings"]:
            assert warning["level"] == "WARNING"
    
    def test_warnings_filter_info(self):
        """Test warnings filter by INFO level"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/warnings?level=INFO")
        assert response.status_code == 200
        
        data = response.json()
        
        # All warnings should be INFO
        for warning in data["warnings"]:
            assert warning["level"] == "INFO"
    
    def test_warnings_categorization(self):
        """Test warnings are properly categorized (INVALID_METRICS=CRITICAL, LOW_SAMPLE_SIZE=WARNING)"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/{TEST_EXPERIMENT_ID}/warnings")
        assert response.status_code == 200
        
        data = response.json()
        
        for warning in data["warnings"]:
            if warning["code"] == "INVALID_METRICS":
                assert warning["level"] == "CRITICAL"
            elif warning["code"] == "OVERFIT":
                assert warning["level"] == "CRITICAL"
            elif warning["code"] == "LOW_SAMPLE_SIZE":
                assert warning["level"] == "WARNING"
            elif warning["code"] == "HIGH_DRAWDOWN":
                assert warning["level"] == "WARNING"


class TestEdgeCases:
    """Edge case tests"""
    
    def test_nonexistent_experiment_leaderboard(self):
        """Test leaderboard for nonexistent experiment returns empty"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/nonexistent_exp_xyz/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        assert data["leaderboard"] == []
        assert data["count"] == 0
    
    def test_nonexistent_experiment_diagnostics(self):
        """Test diagnostics for nonexistent experiment returns empty"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/nonexistent_exp_xyz/diagnostics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["diagnostics"] == []
        assert data["count"] == 0
    
    def test_nonexistent_experiment_allocation_candidates(self):
        """Test allocation-candidates for nonexistent experiment returns empty"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/nonexistent_exp_xyz/allocation-candidates")
        assert response.status_code == 200
        
        data = response.json()
        assert data["candidates"] == []
        assert data["eligible_count"] == 0
        assert data["rejected_count"] == 0
    
    def test_nonexistent_experiment_warnings(self):
        """Test warnings for nonexistent experiment returns empty"""
        response = requests.get(f"{BASE_URL}/api/research/experiments/nonexistent_exp_xyz/warnings")
        assert response.status_code == 200
        
        data = response.json()
        assert data["warnings"] == []
        assert data["count"] == 0


class TestCreateAndReportFlow:
    """Test full flow: create experiment -> start -> get report"""
    
    def test_create_experiment_and_get_report(self):
        """Test creating new experiment and generating report"""
        # Create experiment
        create_payload = {
            "name": "TEST_S25_Report_Flow",
            "description": "Test for S2.5 report flow",
            "asset": "ETHUSDT",
            "dataset_id": "ETHUSDT_20200101_20241231_1D",
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "timeframe": "1D",
            "strategies": ["TA_SIGNAL_FOLLOWER", "MBRAIN_SIGNAL_ROUTER"],
            "capital_profile": "SMALL",
            "initial_capital_usd": 5000.0
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/research/experiments",
            json=create_payload
        )
        assert create_response.status_code == 200
        
        response_data = create_response.json()
        # Handle nested response structure
        experiment = response_data.get("experiment", response_data)
        experiment_id = experiment["experiment_id"]
        
        try:
            # Start experiment
            start_response = requests.post(f"{BASE_URL}/api/research/experiments/{experiment_id}/start")
            assert start_response.status_code == 200
            
            # Wait for completion (max 10 seconds)
            for _ in range(10):
                status_response = requests.get(f"{BASE_URL}/api/research/experiments/{experiment_id}")
                if status_response.status_code == 200:
                    status = status_response.json().get("status")
                    if status == "COMPLETED":
                        break
                time.sleep(1)
            
            # Get report
            report_response = requests.get(f"{BASE_URL}/api/research/experiments/{experiment_id}/report")
            assert report_response.status_code == 200
            
            report = report_response.json()
            assert report["experiment_id"] == experiment_id
            assert report["experiment_summary"]["name"] == "TEST_S25_Report_Flow"
            assert report["experiment_summary"]["asset"] == "ETHUSDT"
            assert report["experiment_summary"]["strategies_tested"] == 2
            
            # Verify all sections present
            assert "leaderboard" in report
            assert "strategy_diagnostics" in report
            assert "warnings" in report
            assert "allocation_readiness" in report
            
        finally:
            # Cleanup - delete experiment
            requests.delete(f"{BASE_URL}/api/research/experiments/{experiment_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
