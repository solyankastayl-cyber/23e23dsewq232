"""
FOMO Platform - Phase F1, F2, F3 Backend API Tests
===================================================
F1: Research UI (Chart, Hypothesis, Capital Flow, Fractal, Signal)
F2: Trading Terminal (Portfolio, Execution, Risk)
F3: System Control (Safety, Kill Switch, Circuit Breaker)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com')


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHealth:
    """Basic health check"""
    
    def test_api_health(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "timestamp" in data


# ============================================
# PHASE F1: RESEARCH ENDPOINTS
# ============================================

class TestPhaseF1ChartComposer:
    """F1: Chart Composer API Tests"""
    
    def test_full_analysis_btcusdt_1h(self, api_client):
        """GET /api/v1/chart/full-analysis/BTCUSDT/1h returns candles, indicators, hypothesis"""
        response = api_client.get(f"{BASE_URL}/api/v1/chart/full-analysis/BTCUSDT/1h?include_hypothesis=true&include_fractals=true&limit=500")
        assert response.status_code == 200
        data = response.json()
        
        # Must have candles
        assert "candles" in data
        assert len(data["candles"]) > 0
        
        # Must have market_regime
        assert "market_regime" in data or "regime" in data
        
        # Verify candle structure
        candle = data["candles"][0]
        assert "open" in candle or "o" in candle
        assert "close" in candle or "c" in candle
        assert "high" in candle or "h" in candle
        assert "low" in candle or "l" in candle
        
        print(f"✓ Chart full-analysis returned {len(data['candles'])} candles")
    
    def test_full_analysis_ethusdt(self, api_client):
        """Test full analysis for ETH symbol"""
        response = api_client.get(f"{BASE_URL}/api/v1/chart/full-analysis/ETHUSDT/1h")
        assert response.status_code == 200
        data = response.json()
        assert "candles" in data
        assert len(data["candles"]) > 0
        print(f"✓ ETHUSDT analysis returned {len(data['candles'])} candles")


class TestPhaseF1Hypothesis:
    """F1: Hypothesis Engine API Tests"""
    
    def test_hypothesis_list(self, api_client):
        """GET /api/hypothesis/list returns hypotheses with count > 0"""
        response = api_client.get(f"{BASE_URL}/api/hypothesis/list")
        assert response.status_code == 200
        data = response.json()
        
        assert "hypotheses" in data
        assert "count" in data
        assert data["count"] > 0
        assert len(data["hypotheses"]) > 0
        
        # Verify hypothesis structure
        hyp = data["hypotheses"][0]
        assert "hypothesis_id" in hyp or "id" in hyp
        assert "type" in hyp or "name" in hyp
        
        print(f"✓ Hypothesis list returned {data['count']} hypotheses")
    
    def test_hypothesis_top(self, api_client):
        """Test top hypothesis endpoint"""
        response = api_client.get(f"{BASE_URL}/api/hypothesis/top?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert "top_hypotheses" in data
        print(f"✓ Top hypothesis endpoint working")


class TestPhaseF1CapitalFlow:
    """F1: Capital Flow API Tests"""
    
    def test_capital_flow_summary(self, api_client):
        """GET /api/v1/capital-flow/summary returns capital flow data"""
        response = api_client.get(f"{BASE_URL}/api/v1/capital-flow/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Should have flow state data
        assert "current_state" in data or "score" in data
        
        print(f"✓ Capital flow summary returned")


class TestPhaseF1Fractal:
    """F1: Fractal Intelligence API Tests"""
    
    def test_fractal_summary_btcusdt(self, api_client):
        """GET /api/v1/fractal/summary/BTCUSDT returns fractal data"""
        response = api_client.get(f"{BASE_URL}/api/v1/fractal/summary/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        # Should have current fractal state
        assert "current" in data
        assert "bias" in data["current"] or "alignment" in data["current"]
        
        print(f"✓ Fractal summary for BTCUSDT returned")


class TestPhaseF1Signal:
    """F1: Signal Explanation API Tests"""
    
    def test_signal_explanation_btcusdt_1h(self, api_client):
        """GET /api/v1/signal/explanation/BTCUSDT/1h returns signal with drivers"""
        response = api_client.get(f"{BASE_URL}/api/v1/signal/explanation/BTCUSDT/1h")
        assert response.status_code == 200
        data = response.json()
        
        # Should have signal data
        assert "direction" in data
        assert "drivers" in data
        
        print(f"✓ Signal explanation returned with {len(data.get('drivers', []))} drivers")


# ============================================
# PHASE F2: TRADING TERMINAL ENDPOINTS
# ============================================

class TestPhaseF2Portfolio:
    """F2: Portfolio API Tests"""
    
    def test_portfolio_state(self, api_client):
        """GET /api/portfolio/state returns equity with total, available_margin"""
        response = api_client.get(f"{BASE_URL}/api/portfolio/state")
        assert response.status_code == 200
        data = response.json()
        
        # Must have equity data
        assert "equity" in data
        assert "total" in data["equity"]
        assert "available_margin" in data["equity"]
        assert data["equity"]["total"] > 0
        
        print(f"✓ Portfolio state: ${data['equity']['total']} total, ${data['equity']['available_margin']} available")
    
    def test_portfolio_positions(self, api_client):
        """GET /api/portfolio/positions returns positions array"""
        response = api_client.get(f"{BASE_URL}/api/portfolio/positions")
        assert response.status_code == 200
        data = response.json()
        
        assert "positions" in data
        # positions can be empty array
        assert isinstance(data["positions"], list)
        
        print(f"✓ Portfolio positions returned {len(data['positions'])} positions")
    
    def test_portfolio_exposure(self, api_client):
        """GET /api/portfolio/exposure returns by_asset, directional"""
        response = api_client.get(f"{BASE_URL}/api/portfolio/exposure")
        assert response.status_code == 200
        data = response.json()
        
        assert "by_asset" in data
        assert "directional" in data
        
        print(f"✓ Portfolio exposure returned with directional data")


class TestPhaseF2Execution:
    """F2: Execution Brain API Tests"""
    
    def test_execution_plan_btcusdt(self, api_client):
        """GET /api/v1/execution/plan/BTCUSDT returns execution plan"""
        response = api_client.get(f"{BASE_URL}/api/v1/execution/plan/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "ok"
        
        # Should have plan details
        assert "symbol" in data or "direction" in data or "strategy" in data
        
        print(f"✓ Execution plan returned for BTCUSDT")
    
    def test_execution_history_btcusdt(self, api_client):
        """GET /api/v1/execution/history/BTCUSDT returns execution history records"""
        response = api_client.get(f"{BASE_URL}/api/v1/execution/history/BTCUSDT?limit=50")
        assert response.status_code == 200
        data = response.json()
        
        assert "records" in data
        assert isinstance(data["records"], list)
        
        print(f"✓ Execution history returned {len(data['records'])} records")
    
    def test_execution_summary_btcusdt(self, api_client):
        """GET /api/v1/execution/summary/BTCUSDT returns summary stats"""
        response = api_client.get(f"{BASE_URL}/api/v1/execution/summary/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        
        print(f"✓ Execution summary returned")


class TestPhaseF2PortfolioMetrics:
    """F2: Portfolio Metrics API Tests"""
    
    def test_portfolio_metrics(self, api_client):
        """GET /api/portfolio/metrics returns P&L, leverage, risk metrics"""
        response = api_client.get(f"{BASE_URL}/api/portfolio/metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Should have various metrics
        assert "pnl" in data or "leverage" in data or "risk" in data
        
        print(f"✓ Portfolio metrics returned")


# ============================================
# PHASE F3: SYSTEM CONTROL ENDPOINTS
# ============================================

class TestPhaseF3Control:
    """F3: System Control API Tests"""
    
    def test_control_state_btcusdt(self, api_client):
        """GET /api/v1/control/state/BTCUSDT returns decision and risk state"""
        response = api_client.get(f"{BASE_URL}/api/v1/control/state/BTCUSDT")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "ok"
        
        # Should have decision or risk state
        assert "decision" in data or "risk" in data
        
        print(f"✓ Control state returned for BTCUSDT")
    
    def test_control_summary(self, api_client):
        """GET /api/v1/control/summary returns system_status OPERATIONAL"""
        response = api_client.get(f"{BASE_URL}/api/v1/control/summary")
        assert response.status_code == 200
        data = response.json()
        
        assert "system_status" in data
        assert data["system_status"] == "OPERATIONAL"
        assert "symbols_monitored" in data
        
        print(f"✓ Control summary: {data['system_status']}, {len(data['symbols_monitored'])} symbols monitored")


class TestPhaseF3KillSwitch:
    """F3: Kill Switch API Tests"""
    
    def test_kill_switch_state(self, api_client):
        """GET /api/v1/safety/kill-switch/state returns kill switch state"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/state")
        assert response.status_code == 200
        data = response.json()
        
        assert "state" in data
        assert "is_active" in data
        
        # Default should be ACTIVE (normal operations)
        assert data["state"] in ["ACTIVE", "KILLED", "SAFE_MODE"]
        
        print(f"✓ Kill switch state: {data['state']}, active={data['is_active']}")
    
    def test_kill_switch_status(self, api_client):
        """GET /api/v1/safety/kill-switch/status returns status details"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "kill_switch" in data
        
        print(f"✓ Kill switch status returned")


class TestPhaseF3CircuitBreaker:
    """F3: Circuit Breaker API Tests"""
    
    def test_circuit_breaker_status(self, api_client):
        """GET /api/v1/safety/circuit-breaker/status returns breaker status with rules"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "circuit_breaker" in data
        cb = data["circuit_breaker"]
        assert "state" in cb
        assert "total_rules" in cb or "tripped_rules" in cb
        
        print(f"✓ Circuit breaker status: {cb['state']}")
    
    def test_circuit_breaker_rules(self, api_client):
        """GET /api/v1/safety/circuit-breaker/rules returns 6 breaker rules"""
        response = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/rules")
        assert response.status_code == 200
        data = response.json()
        
        assert "rules" in data
        assert "count" in data
        assert data["count"] == 6
        assert len(data["rules"]) == 6
        
        # Verify rule structure
        rule = data["rules"][0]
        assert "rule_id" in rule
        assert "name" in rule
        assert "state" in rule
        
        # All rules should be CLOSED (healthy)
        for rule in data["rules"]:
            assert rule["state"] == "CLOSED"
        
        print(f"✓ Circuit breaker has {data['count']} rules, all CLOSED")


# ============================================
# INTEGRATION TESTS
# ============================================

class TestIntegration:
    """Cross-phase integration tests"""
    
    def test_f1_data_flow(self, api_client):
        """Test full F1 research data flow"""
        # Chart analysis
        chart = api_client.get(f"{BASE_URL}/api/v1/chart/full-analysis/BTCUSDT/1h").json()
        assert len(chart.get("candles", [])) > 0
        
        # Hypothesis
        hyp = api_client.get(f"{BASE_URL}/api/hypothesis/list").json()
        assert hyp.get("count", 0) > 0
        
        # Signal
        signal = api_client.get(f"{BASE_URL}/api/v1/signal/explanation/BTCUSDT/1h").json()
        assert "direction" in signal
        
        print(f"✓ F1 data flow integration test passed")
    
    def test_f2_terminal_data_flow(self, api_client):
        """Test full F2 terminal data flow"""
        # Portfolio
        portfolio = api_client.get(f"{BASE_URL}/api/portfolio/state").json()
        assert portfolio.get("equity", {}).get("total", 0) > 0
        
        # Execution
        exec_plan = api_client.get(f"{BASE_URL}/api/v1/execution/plan/BTCUSDT").json()
        assert exec_plan.get("status") == "ok"
        
        # Exposure
        exposure = api_client.get(f"{BASE_URL}/api/portfolio/exposure").json()
        assert "directional" in exposure
        
        print(f"✓ F2 terminal data flow integration test passed")
    
    def test_f3_system_control_flow(self, api_client):
        """Test full F3 system control data flow"""
        # Control state
        control = api_client.get(f"{BASE_URL}/api/v1/control/state/BTCUSDT").json()
        assert control.get("status") == "ok"
        
        # Summary
        summary = api_client.get(f"{BASE_URL}/api/v1/control/summary").json()
        assert summary.get("system_status") == "OPERATIONAL"
        
        # Kill switch
        ks = api_client.get(f"{BASE_URL}/api/v1/safety/kill-switch/state").json()
        assert "state" in ks
        
        # Circuit breaker
        cb = api_client.get(f"{BASE_URL}/api/v1/safety/circuit-breaker/rules").json()
        assert cb.get("count") == 6
        
        print(f"✓ F3 system control data flow integration test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
