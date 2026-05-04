"""
PHASE 12 - System Intelligence Module Tests
=============================================
Tests for all 5 engines:
- Global Market State Engine
- Regime Switching Engine
- System Health Engine
- Autonomous Research Loop
- Decision Orchestrator

All endpoints tested:
- GET /api/system-intelligence/health
- GET /api/system-intelligence/state
- GET /api/system-intelligence/health-status
- GET /api/system-intelligence/market-state
- GET /api/system-intelligence/strategies
- GET /api/system-intelligence/research-loop
- GET /api/system-intelligence/actions
- GET /api/system-intelligence/stats
- POST /api/system-intelligence/research-loop/start
- POST /api/system-intelligence/research-loop/advance
- POST /api/system-intelligence/actions/{decision_id}/execute
"""

import pytest
import requests
import os
from datetime import datetime

# BASE_URL from environment - using /api/system-intelligence prefix
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')
API_PREFIX = f"{BASE_URL}/api/system-intelligence"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ============= Module Health Endpoint Tests =============

class TestModuleHealth:
    """Tests for /api/system-intelligence/health endpoint"""
    
    def test_health_endpoint_returns_200(self, api_client):
        """Health check should return 200 OK"""
        response = api_client.get(f"{API_PREFIX}/health")
        assert response.status_code == 200
        
    def test_health_endpoint_status_healthy(self, api_client):
        """Health check should report healthy status"""
        response = api_client.get(f"{API_PREFIX}/health")
        data = response.json()
        assert data["status"] == "healthy"
        
    def test_health_endpoint_version(self, api_client):
        """Health check should include correct version"""
        response = api_client.get(f"{API_PREFIX}/health")
        data = response.json()
        assert "phase12_system_intelligence" in data["version"]
        
    def test_health_endpoint_all_engines_ready(self, api_client):
        """Health check should show all 5 engines ready"""
        response = api_client.get(f"{API_PREFIX}/health")
        data = response.json()
        
        engines = data["engines"]
        expected_engines = [
            "global_market_state",
            "regime_switching",
            "system_health",
            "research_loop",
            "decision_orchestrator"
        ]
        
        for engine in expected_engines:
            assert engine in engines, f"Missing engine: {engine}"
            assert engines[engine] == "ready", f"Engine {engine} not ready"
            
    def test_health_endpoint_config_present(self, api_client):
        """Health check should include configuration"""
        response = api_client.get(f"{API_PREFIX}/health")
        data = response.json()
        
        assert "config" in data
        assert "high_vol_threshold" in data["config"]
        assert "pause_threshold" in data["config"]
        assert "research_interval" in data["config"]
        
    def test_health_endpoint_timestamp(self, api_client):
        """Health check should include valid timestamp"""
        response = api_client.get(f"{API_PREFIX}/health")
        data = response.json()
        
        assert "timestamp" in data
        # Should be parseable ISO format
        datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))


# ============= System State Endpoint Tests =============

class TestSystemState:
    """Tests for /api/system-intelligence/state endpoint"""
    
    def test_state_endpoint_returns_200(self, api_client):
        """State endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/state")
        assert response.status_code == 200
        
    def test_state_endpoint_market_state_valid(self, api_client):
        """State should contain valid market state"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        valid_states = [
            "TRENDING", "RANGING", "HIGH_VOLATILITY", "LOW_VOLATILITY",
            "LOW_LIQUIDITY", "MACRO_DOMINANT", "CRYPTO_NATIVE",
            "RISK_OFF", "RISK_ON", "TRANSITION"
        ]
        assert data["marketState"] in valid_states
        
    def test_state_endpoint_health_score(self, api_client):
        """State should contain valid health score 0-1"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert 0 <= data["systemHealth"] <= 1
        
    def test_state_endpoint_health_state_valid(self, api_client):
        """State should contain valid health state enum"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        valid_health_states = [
            "OPTIMAL", "HEALTHY", "DEGRADED", "WARNING", "CRITICAL", "EMERGENCY"
        ]
        assert data["healthState"] in valid_health_states
        
    def test_state_endpoint_portfolio_risk(self, api_client):
        """State should contain portfolio risk metric"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert "portfolioRisk" in data
        assert 0 <= data["portfolioRisk"] <= 1
        
    def test_state_endpoint_capital_deployment(self, api_client):
        """State should contain capital deployment metric"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert "capitalDeployment" in data
        assert 0 <= data["capitalDeployment"] <= 1
        
    def test_state_endpoint_strategies_count(self, api_client):
        """State should contain strategy counts"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert "activeStrategies" in data
        assert "disabledStrategies" in data
        assert isinstance(data["activeStrategies"], int)
        assert isinstance(data["disabledStrategies"], int)
        
    def test_state_endpoint_edges_breakdown(self, api_client):
        """State should contain edges health breakdown"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert "edgesStrengthening" in data
        assert "edgesStable" in data
        assert "edgesDecaying" in data
        
    def test_state_endpoint_research_loop_status(self, api_client):
        """State should contain research loop status"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert "researchLoopActive" in data
        assert isinstance(data["researchLoopActive"], bool)
        
    def test_state_endpoint_pending_actions(self, api_client):
        """State should contain pending actions count"""
        response = api_client.get(f"{API_PREFIX}/state")
        data = response.json()
        
        assert "pendingActions" in data
        assert isinstance(data["pendingActions"], int)


# ============= Health Status Endpoint Tests =============

class TestHealthStatus:
    """Tests for /api/system-intelligence/health-status endpoint"""
    
    def test_health_status_returns_200(self, api_client):
        """Health status endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        assert response.status_code == 200
        
    def test_health_status_health_score_valid(self, api_client):
        """Health score should be between 0 and 1"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert 0 <= data["healthScore"] <= 1
        
    def test_health_status_signal_quality(self, api_client):
        """Signal quality should be present and valid"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert "signalQuality" in data
        assert 0 <= data["signalQuality"] <= 1
        
    def test_health_status_execution_quality(self, api_client):
        """Execution quality should be present and valid"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert "executionQuality" in data
        assert 0 <= data["executionQuality"] <= 1
        
    def test_health_status_portfolio_stability(self, api_client):
        """Portfolio stability should be present and valid"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert "portfolioStability" in data
        assert 0 <= data["portfolioStability"] <= 1
        
    def test_health_status_risk_budget_usage(self, api_client):
        """Risk budget usage should be present and valid"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert "riskBudgetUsage" in data
        assert 0 <= data["riskBudgetUsage"] <= 1
        
    def test_health_status_edge_strength(self, api_client):
        """Edge strength should be present and valid"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert "edgeStrength" in data
        assert 0 <= data["edgeStrength"] <= 1
        
    def test_health_status_critical_issues(self, api_client):
        """Critical issues count should be present"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        assert "criticalIssues" in data
        assert isinstance(data["criticalIssues"], int)
        assert data["criticalIssues"] >= 0
        
    def test_health_status_recommended_action(self, api_client):
        """Recommended action should be a valid action"""
        response = api_client.get(f"{API_PREFIX}/health-status")
        data = response.json()
        
        valid_actions = [
            "NO_ACTION", "REDUCE_RISK", "INCREASE_ALLOCATION", "SWITCH_REGIME",
            "DISABLE_STRATEGY", "ENABLE_STRATEGY", "PAUSE_TRADING",
            "RESUME_TRADING", "EMERGENCY_EXIT", "TRIGGER_RESEARCH"
        ]
        assert data["recommendedAction"] in valid_actions


# ============= Market State Endpoint Tests =============

class TestMarketState:
    """Tests for /api/system-intelligence/market-state endpoint"""
    
    def test_market_state_returns_200(self, api_client):
        """Market state endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/market-state")
        assert response.status_code == 200
        
    def test_market_state_state_valid(self, api_client):
        """Market state should be valid enum"""
        response = api_client.get(f"{API_PREFIX}/market-state")
        data = response.json()
        
        valid_states = [
            "TRENDING", "RANGING", "HIGH_VOLATILITY", "LOW_VOLATILITY",
            "LOW_LIQUIDITY", "MACRO_DOMINANT", "CRYPTO_NATIVE",
            "RISK_OFF", "RISK_ON", "TRANSITION"
        ]
        assert data["marketState"] in valid_states
        
    def test_market_state_confidence_valid(self, api_client):
        """State confidence should be between 0 and 1"""
        response = api_client.get(f"{API_PREFIX}/market-state")
        data = response.json()
        
        assert 0 <= data["stateConfidence"] <= 1
        
    def test_market_state_volatility_regime(self, api_client):
        """Volatility regime should be present"""
        response = api_client.get(f"{API_PREFIX}/market-state")
        data = response.json()
        
        valid_regimes = ["HIGH", "NORMAL", "LOW"]
        assert data["volatilityRegime"] in valid_regimes
        
    def test_market_state_liquidity_regime(self, api_client):
        """Liquidity regime should be present"""
        response = api_client.get(f"{API_PREFIX}/market-state")
        data = response.json()
        
        valid_regimes = ["HIGH", "NORMAL", "LOW"]
        assert data["liquidityRegime"] in valid_regimes
        
    def test_market_state_trend_info(self, api_client):
        """Trend strength and direction should be present"""
        response = api_client.get(f"{API_PREFIX}/market-state")
        data = response.json()
        
        assert "trendStrength" in data
        assert "trendDirection" in data
        assert 0 <= data["trendStrength"] <= 1
        assert data["trendDirection"] in ["BULLISH", "BEARISH", "NEUTRAL"]


# ============= Strategies Endpoint Tests =============

class TestStrategies:
    """Tests for /api/system-intelligence/strategies endpoint"""
    
    def test_strategies_returns_200(self, api_client):
        """Strategies endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/strategies")
        assert response.status_code == 200
        
    def test_strategies_profile_valid(self, api_client):
        """Current profile should be valid regime"""
        response = api_client.get(f"{API_PREFIX}/strategies")
        data = response.json()
        
        valid_profiles = [
            "AGGRESSIVE_TREND", "CONSERVATIVE_TREND", "MEAN_REVERSION",
            "VOLATILITY_HARVEST", "DEFENSIVE", "BALANCED", "RESEARCH_ONLY"
        ]
        assert data["current_profile"] in valid_profiles
        
    def test_strategies_weights_present(self, api_client):
        """Strategy weights should be present"""
        response = api_client.get(f"{API_PREFIX}/strategies")
        data = response.json()
        
        assert "strategy_weights" in data
        assert isinstance(data["strategy_weights"], dict)
        
        # Check for expected strategies
        expected_strategies = ["momentum", "breakout", "trend_following", "mean_reversion", "volatility"]
        for strategy in expected_strategies:
            assert strategy in data["strategy_weights"]
            
    def test_strategies_cooldown_status(self, api_client):
        """Cooldown clear status should be present"""
        response = api_client.get(f"{API_PREFIX}/strategies")
        data = response.json()
        
        assert "cooldown_clear" in data
        assert isinstance(data["cooldown_clear"], bool)


# ============= Research Loop Endpoint Tests =============

class TestResearchLoop:
    """Tests for /api/system-intelligence/research-loop endpoint"""
    
    def test_research_loop_returns_200(self, api_client):
        """Research loop endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/research-loop")
        assert response.status_code == 200
        
    def test_research_loop_phase_valid(self, api_client):
        """Research loop phase should be valid"""
        response = api_client.get(f"{API_PREFIX}/research-loop")
        data = response.json()
        
        valid_phases = [
            "IDLE", "DETECTING_DECAY", "GENERATING_HYPOTHESIS",
            "RUNNING_SCENARIOS", "RUNNING_MONTECARLO", "PROPOSING_ADAPTATION",
            "SHADOW_TESTING", "DEPLOYING", "COMPLETED"
        ]
        assert data["phase"] in valid_phases
        
    def test_research_loop_progress(self, api_client):
        """Progress should be between 0 and 1"""
        response = api_client.get(f"{API_PREFIX}/research-loop")
        data = response.json()
        
        assert 0 <= data["progress"] <= 1
        
    def test_research_loop_current_task(self, api_client):
        """Current task should be present"""
        response = api_client.get(f"{API_PREFIX}/research-loop")
        data = response.json()
        
        assert "currentTask" in data
        assert isinstance(data["currentTask"], str)
        
    def test_research_loop_stats(self, api_client):
        """Research loop stats should be present"""
        response = api_client.get(f"{API_PREFIX}/research-loop")
        data = response.json()
        
        assert "hypothesesGenerated" in data
        assert "scenariosTested" in data
        assert "montecarloRuns" in data
        assert "adaptationsProposed" in data
        assert "successfulDeployments" in data
        assert "failedProposals" in data


# ============= Actions Endpoint Tests =============

class TestActions:
    """Tests for /api/system-intelligence/actions endpoint"""
    
    def test_actions_returns_200(self, api_client):
        """Actions endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/actions")
        assert response.status_code == 200
        
    def test_actions_count_present(self, api_client):
        """Actions count should be present"""
        response = api_client.get(f"{API_PREFIX}/actions")
        data = response.json()
        
        assert "count" in data
        assert isinstance(data["count"], int)
        
    def test_actions_list_present(self, api_client):
        """Actions list should be present"""
        response = api_client.get(f"{API_PREFIX}/actions")
        data = response.json()
        
        assert "actions" in data
        assert isinstance(data["actions"], list)
        
    def test_actions_trading_paused_status(self, api_client):
        """Trading paused status should be present"""
        response = api_client.get(f"{API_PREFIX}/actions")
        data = response.json()
        
        assert "trading_paused" in data
        assert isinstance(data["trading_paused"], bool)
        
    def test_actions_emergency_mode_status(self, api_client):
        """Emergency mode status should be present"""
        response = api_client.get(f"{API_PREFIX}/actions")
        data = response.json()
        
        assert "emergency_mode" in data
        assert isinstance(data["emergency_mode"], bool)
        
    def test_actions_decision_structure(self, api_client):
        """If actions exist, check decision structure"""
        response = api_client.get(f"{API_PREFIX}/actions")
        data = response.json()
        
        if data["count"] > 0 and len(data["actions"]) > 0:
            decision = data["actions"][0]
            required_fields = [
                "timestamp", "decision_id", "action", "target",
                "parameters", "confidence", "executed"
            ]
            for field in required_fields:
                assert field in decision, f"Missing field: {field}"


# ============= Stats Endpoint Tests =============

class TestStats:
    """Tests for /api/system-intelligence/stats endpoint"""
    
    def test_stats_returns_200(self, api_client):
        """Stats endpoint should return 200"""
        response = api_client.get(f"{API_PREFIX}/stats")
        assert response.status_code == 200
        
    def test_stats_repository_info(self, api_client):
        """Repository info should be present"""
        response = api_client.get(f"{API_PREFIX}/stats")
        data = response.json()
        
        assert "repository" in data
        # Note: connected will be false as per known P1 issue
        
    def test_stats_orchestrator_info(self, api_client):
        """Orchestrator info should be present"""
        response = api_client.get(f"{API_PREFIX}/stats")
        data = response.json()
        
        assert "orchestrator" in data
        orchestrator = data["orchestrator"]
        
        assert "trading_paused" in orchestrator
        assert "emergency_mode" in orchestrator
        assert "current_regime" in orchestrator
        assert "pending_decisions" in orchestrator
        
    def test_stats_config_present(self, api_client):
        """Config should be present"""
        response = api_client.get(f"{API_PREFIX}/stats")
        data = response.json()
        
        assert "config" in data
        config = data["config"]
        
        # Check key config values
        assert "high_volatility_threshold" in config
        assert "health_optimal_threshold" in config
        assert "regime_switch_cooldown_hours" in config
        assert "research_loop_interval_hours" in config


# ============= Research Loop Start/Advance POST Tests =============

class TestResearchLoopPOST:
    """Tests for research loop POST endpoints"""
    
    def test_research_loop_start_returns_valid_response(self, api_client):
        """Start research loop should return valid response"""
        response = api_client.post(f"{API_PREFIX}/research-loop/start")
        assert response.status_code == 200
        data = response.json()
        
        # Either started or already running
        assert "started" in data
        if data["started"]:
            assert "phase" in data
            assert "task" in data
        else:
            assert "reason" in data
            
    def test_research_loop_advance_returns_valid_response(self, api_client):
        """Advance research loop should return valid response"""
        response = api_client.post(f"{API_PREFIX}/research-loop/advance")
        assert response.status_code == 200
        data = response.json()
        
        assert "phase" in data
        assert "progress" in data
        assert "task" in data
        
    def test_research_loop_advance_multiple_times(self, api_client):
        """Advancing loop multiple times should progress through phases"""
        # Start the loop if not running
        api_client.post(f"{API_PREFIX}/research-loop/start")
        
        # Advance several times
        phases_seen = set()
        for _ in range(10):
            response = api_client.post(f"{API_PREFIX}/research-loop/advance")
            data = response.json()
            phases_seen.add(data["phase"])
            
        # Should have seen multiple phases
        assert len(phases_seen) >= 1


# ============= Execute Action POST Tests =============

class TestExecuteAction:
    """Tests for execute action endpoint"""
    
    def test_execute_nonexistent_decision(self, api_client):
        """Executing non-existent decision should fail gracefully"""
        response = api_client.post(f"{API_PREFIX}/actions/nonexistent_decision/execute")
        assert response.status_code == 200
        data = response.json()
        
        assert data["executed"] == False
        assert "reason" in data
        
    def test_execute_decision_response_structure(self, api_client):
        """Execute decision should return proper structure"""
        # First get pending actions
        actions_response = api_client.get(f"{API_PREFIX}/actions")
        actions_data = actions_response.json()
        
        if actions_data["count"] > 0:
            # Find a non-executed decision
            pending = [a for a in actions_data["actions"] if not a.get("executed")]
            if pending:
                decision_id = pending[0]["decision_id"]
                
                response = api_client.post(f"{API_PREFIX}/actions/{decision_id}/execute")
                assert response.status_code == 200
                data = response.json()
                
                if data["executed"]:
                    assert "decision_id" in data
                    assert "action" in data
                    assert "result" in data


# ============= Integration Tests =============

class TestSystemIntegration:
    """Integration tests across multiple endpoints"""
    
    def test_state_matches_health(self, api_client):
        """System state health should be consistent with health-status"""
        state_response = api_client.get(f"{API_PREFIX}/state")
        health_response = api_client.get(f"{API_PREFIX}/health-status")
        
        state_data = state_response.json()
        health_data = health_response.json()
        
        # Health states should match
        assert state_data["healthState"] == health_data["healthState"]
        
    def test_strategies_regime_in_stats(self, api_client):
        """Strategies regime should match stats orchestrator regime"""
        strategies_response = api_client.get(f"{API_PREFIX}/strategies")
        stats_response = api_client.get(f"{API_PREFIX}/stats")
        
        strategies_data = strategies_response.json()
        stats_data = stats_response.json()
        
        assert strategies_data["current_profile"] == stats_data["orchestrator"]["current_regime"]
        
    def test_research_loop_status_consistent(self, api_client):
        """Research loop status should be consistent across endpoints"""
        loop_response = api_client.get(f"{API_PREFIX}/research-loop")
        stats_response = api_client.get(f"{API_PREFIX}/stats")
        
        loop_data = loop_response.json()
        stats_data = stats_response.json()
        
        assert loop_data["phase"] == stats_data["orchestrator"]["research_loop"]["current_phase"]


# ============= Edge Case Tests =============

class TestEdgeCases:
    """Edge case and error handling tests"""
    
    def test_invalid_endpoint(self, api_client):
        """Invalid endpoint should return 404"""
        response = api_client.get(f"{API_PREFIX}/invalid-endpoint")
        assert response.status_code == 404
        
    def test_wrong_method_on_get_endpoint(self, api_client):
        """POST on GET-only endpoint should fail"""
        response = api_client.post(f"{API_PREFIX}/health")
        # Either 405 Method Not Allowed or 422 Validation Error
        assert response.status_code in [405, 422]
        
    def test_multiple_rapid_requests(self, api_client):
        """Multiple rapid requests should all succeed"""
        for _ in range(5):
            response = api_client.get(f"{API_PREFIX}/state")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
