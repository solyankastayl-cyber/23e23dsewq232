"""
Test Suite for PHASE 1.3 Position Management Policy Module
==========================================================

Tests all endpoints for Position Management Policy including:
- Health check
- Strategies and policies
- Stop loss engine
- Take profit engine
- Trailing stop engine
- Partial close engine
- Time stop engine
- Forced exit engine
- Combined matrices and full evaluation
- Regression tests for PHASE 1.1 and 1.2
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPositionPolicyHealth:
    """Health check tests for Position Policy module"""
    
    def test_health_check(self):
        """Test health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/position-policy/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["module"] == "PHASE 1.3 Position Management Policy"
        assert data["strategiesConfigured"] == 3
        
        # Verify all 6 engines are active
        engines = data["engines"]
        assert engines["stopPolicy"] == "active"
        assert engines["takeProfit"] == "active"
        assert engines["trailingStop"] == "active"
        assert engines["partialClose"] == "active"
        assert engines["timeStop"] == "active"
        assert engines["forcedExit"] == "active"
        print("✓ Health check passed - 6 engines active")


class TestStrategiesAndPolicies:
    """Tests for strategies and complete policies"""
    
    def test_get_all_strategies(self):
        """Test GET /api/position-policy/strategies returns 3 strategies"""
        response = requests.get(f"{BASE_URL}/api/position-policy/strategies")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        assert "TREND_CONFIRMATION" in data["strategies"]
        assert "MOMENTUM_BREAKOUT" in data["strategies"]
        assert "MEAN_REVERSION" in data["strategies"]
        print("✓ GET /strategies - 3 strategies returned")
    
    def test_get_all_policies(self):
        """Test GET /api/position-policy/policies returns 3 policies"""
        response = requests.get(f"{BASE_URL}/api/position-policy/policies")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        assert len(data["policies"]) == 3
        
        # Verify each policy has required components
        for policy in data["policies"]:
            assert "stopLoss" in policy
            assert "takeProfit" in policy
            assert "trailingStop" in policy
            assert "partialClose" in policy
            assert "timeStop" in policy
            assert "forcedExit" in policy
        print("✓ GET /policies - 3 complete policies returned")
    
    def test_get_trend_confirmation_policy(self):
        """Test TREND_CONFIRMATION policy: STRUCTURE_STOP, TRAILING_TP, STRUCTURE_TRAILING"""
        response = requests.get(f"{BASE_URL}/api/position-policy/policies/TREND_CONFIRMATION")
        assert response.status_code == 200
        
        data = response.json()
        assert data["primaryStrategy"] == "TREND_CONFIRMATION"
        
        # Verify TREND_CONFIRMATION specific config
        assert data["stopLoss"]["stopType"] == "STRUCTURE_STOP"
        assert data["takeProfit"]["tpType"] == "TRAILING_TP"
        assert data["trailingStop"]["trailingType"] == "STRUCTURE_TRAILING"
        assert data["partialClose"]["partialType"] == "FIXED_LEVELS"
        print("✓ TREND_CONFIRMATION: STRUCTURE_STOP, TRAILING_TP, STRUCTURE_TRAILING")
    
    def test_get_momentum_breakout_policy(self):
        """Test MOMENTUM_BREAKOUT policy: HARD_STOP, FIXED_RR, ATR_TRAILING, time stop required"""
        response = requests.get(f"{BASE_URL}/api/position-policy/policies/MOMENTUM_BREAKOUT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["primaryStrategy"] == "MOMENTUM_BREAKOUT"
        
        # Verify MOMENTUM_BREAKOUT specific config
        assert data["stopLoss"]["stopType"] == "HARD_STOP"
        assert data["takeProfit"]["tpType"] == "FIXED_RR"
        assert data["trailingStop"]["trailingType"] == "ATR_TRAILING"
        assert data["timeStop"]["timeStopType"] == "BAR_BASED"
        assert data["timeStop"]["barBased"]["maxBars"] == 10  # Quick resolution
        print("✓ MOMENTUM_BREAKOUT: HARD_STOP, FIXED_RR, ATR_TRAILING, time stop required")
    
    def test_get_mean_reversion_policy(self):
        """Test MEAN_REVERSION policy: STRUCTURE_STOP, STRUCTURE_TP, NO trailing, time stop required"""
        response = requests.get(f"{BASE_URL}/api/position-policy/policies/MEAN_REVERSION")
        assert response.status_code == 200
        
        data = response.json()
        assert data["primaryStrategy"] == "MEAN_REVERSION"
        
        # Verify MEAN_REVERSION specific config
        assert data["stopLoss"]["stopType"] == "STRUCTURE_STOP"
        assert data["takeProfit"]["tpType"] == "STRUCTURE_TP"
        assert data["trailingStop"]["trailingType"] == "NONE"  # No trailing
        assert data["timeStop"]["timeStopType"] == "BAR_BASED"
        assert data["timeStop"]["barBased"]["maxBars"] == 30
        print("✓ MEAN_REVERSION: STRUCTURE_STOP, STRUCTURE_TP, NO trailing, time stop required")
    
    def test_get_policy_summary(self):
        """Test GET /api/position-policy/policies/{strategy}/summary"""
        response = requests.get(f"{BASE_URL}/api/position-policy/policies/TREND_CONFIRMATION/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "TREND_CONFIRMATION"
        assert "summary" in data
        assert data["summary"]["stopType"] == "STRUCTURE_STOP"
        assert data["summary"]["tpType"] == "TRAILING_TP"
        print("✓ GET /policies/{strategy}/summary - summary returned")
    
    def test_get_nonexistent_policy(self):
        """Test 404 for non-existent policy"""
        response = requests.get(f"{BASE_URL}/api/position-policy/policies/NONEXISTENT")
        assert response.status_code == 404
        print("✓ Non-existent policy returns 404")


class TestStopLossEngine:
    """Tests for stop loss engine"""
    
    def test_get_stop_types(self):
        """Test GET /api/position-policy/stops returns 3 stop types"""
        response = requests.get(f"{BASE_URL}/api/position-policy/stops")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["stopTypes"]) == 3
        
        stop_type_names = [s["type"] for s in data["stopTypes"]]
        assert "HARD_STOP" in stop_type_names
        assert "STRUCTURE_STOP" in stop_type_names
        assert "VOLATILITY_STOP" in stop_type_names
        print("✓ GET /stops - 3 stop types returned")
    
    def test_calculate_stop_long(self):
        """Test POST /api/position-policy/stops/calculate for LONG position"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "entry_price": 100.0,
            "direction": "LONG",
            "atr": 1.5,
            "swing_low": 98.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/stops/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["stopType"] == "HARD_STOP"
        assert data["entryPrice"] == 100.0
        assert data["stopPrice"] < 100.0  # Stop below entry for LONG
        assert data["stopDistancePct"] > 0
        print(f"✓ Calculate stop LONG: entry=100, stop={data['stopPrice']:.2f}, distance={data['stopDistancePct']:.2f}%")
    
    def test_calculate_stop_short(self):
        """Test POST /api/position-policy/stops/calculate for SHORT position"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "entry_price": 100.0,
            "direction": "SHORT",
            "atr": 1.5,
            "swing_high": 102.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/stops/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["stopType"] == "HARD_STOP"
        assert data["stopPrice"] > 100.0  # Stop above entry for SHORT
        print(f"✓ Calculate stop SHORT: entry=100, stop={data['stopPrice']:.2f}")
    
    def test_get_stop_matrix(self):
        """Test GET /api/position-policy/stops/matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/stops/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert "TREND_CONFIRMATION" in data
        assert "MOMENTUM_BREAKOUT" in data
        assert "MEAN_REVERSION" in data
        
        # Verify strategy-specific stop types
        assert data["MOMENTUM_BREAKOUT"]["stopType"] == "HARD_STOP"
        assert data["TREND_CONFIRMATION"]["stopType"] == "STRUCTURE_STOP"
        assert data["MEAN_REVERSION"]["stopType"] == "STRUCTURE_STOP"
        print("✓ GET /stops/matrix - strategy-stop matrix returned")


class TestTakeProfitEngine:
    """Tests for take profit engine"""
    
    def test_get_tp_types(self):
        """Test GET /api/position-policy/take-profits returns 3 TP types"""
        response = requests.get(f"{BASE_URL}/api/position-policy/take-profits")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["tpTypes"]) == 3
        
        tp_type_names = [t["type"] for t in data["tpTypes"]]
        assert "FIXED_RR" in tp_type_names
        assert "STRUCTURE_TP" in tp_type_names
        assert "TRAILING_TP" in tp_type_names
        print("✓ GET /take-profits - 3 TP types returned")
    
    def test_calculate_tp_levels(self):
        """Test POST /api/position-policy/take-profits/calculate"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "entry_price": 100.0,
            "stop_price": 98.0,
            "direction": "LONG",
            "resistance": 105.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/take-profits/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["tpType"] == "FIXED_RR"
        assert data["entryPrice"] == 100.0
        assert len(data["targets"]) > 0
        
        # Verify targets are above entry for LONG
        for target in data["targets"]:
            if target["price"]:
                assert target["price"] > 100.0
        print(f"✓ Calculate TP: {len(data['targets'])} targets, totalRR={data['totalRR']}")
    
    def test_get_tp_matrix(self):
        """Test GET /api/position-policy/take-profits/matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/take-profits/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert data["MOMENTUM_BREAKOUT"]["tpType"] == "FIXED_RR"
        assert data["TREND_CONFIRMATION"]["tpType"] == "TRAILING_TP"
        assert data["MEAN_REVERSION"]["tpType"] == "STRUCTURE_TP"
        print("✓ GET /take-profits/matrix - strategy-TP matrix returned")


class TestTrailingStopEngine:
    """Tests for trailing stop engine"""
    
    def test_get_trailing_types(self):
        """Test GET /api/position-policy/trailing returns 4 trailing types"""
        response = requests.get(f"{BASE_URL}/api/position-policy/trailing")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["trailingTypes"]) == 4
        
        trailing_type_names = [t["type"] for t in data["trailingTypes"]]
        assert "ATR_TRAILING" in trailing_type_names
        assert "STRUCTURE_TRAILING" in trailing_type_names
        assert "TIME_TRAILING" in trailing_type_names
        assert "NONE" in trailing_type_names
        print("✓ GET /trailing - 4 trailing types returned")
    
    def test_calculate_trailing_stop_update(self):
        """Test POST /api/position-policy/trailing/calculate"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "entry_price": 100.0,
            "current_stop": 98.0,
            "current_price": 103.0,  # In profit
            "direction": "LONG",
            "atr": 1.5,
            "bars_in_trade": 5
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/trailing/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["trailingType"] == "ATR_TRAILING"
        assert data["currentPrice"] == 103.0
        assert data["profitPct"] > 0  # Should be in profit
        print(f"✓ Trailing update: stopMoved={data['stopMoved']}, newStop={data['newStop']:.2f}")
    
    def test_get_trailing_matrix(self):
        """Test GET /api/position-policy/trailing/matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/trailing/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert data["MOMENTUM_BREAKOUT"]["trailingType"] == "ATR_TRAILING"
        assert data["TREND_CONFIRMATION"]["trailingType"] == "STRUCTURE_TRAILING"
        assert data["MEAN_REVERSION"]["trailingType"] == "NONE"  # No trailing for mean reversion
        print("✓ GET /trailing/matrix - strategy-trailing matrix returned")


class TestPartialCloseEngine:
    """Tests for partial close engine"""
    
    def test_get_partial_types(self):
        """Test GET /api/position-policy/partial-close returns 3 partial types"""
        response = requests.get(f"{BASE_URL}/api/position-policy/partial-close")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["partialTypes"]) == 3
        
        partial_type_names = [p["type"] for p in data["partialTypes"]]
        assert "FIXED_LEVELS" in partial_type_names
        assert "DYNAMIC" in partial_type_names
        assert "NONE" in partial_type_names
        print("✓ GET /partial-close - 3 partial types returned")
    
    def test_evaluate_partial_close(self):
        """Test POST /api/position-policy/partial-close/evaluate"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "entry_price": 100.0,
            "current_price": 101.5,  # 50% to target
            "stop_price": 98.0,
            "target_price": 103.0,
            "direction": "LONG",
            "current_position_size": 1.0,
            "already_closed_pct": 0.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/partial-close/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "shouldClose" in data
        assert "closeSizePct" in data
        assert "remainingSizePct" in data
        print(f"✓ Partial close eval: shouldClose={data['shouldClose']}, closePct={data['closeSizePct']}")
    
    def test_get_partial_matrix(self):
        """Test GET /api/position-policy/partial-close/matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/partial-close/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert "TREND_CONFIRMATION" in data
        assert "MOMENTUM_BREAKOUT" in data
        assert "MEAN_REVERSION" in data
        
        # All strategies use FIXED_LEVELS
        for strategy in data:
            assert data[strategy]["partialType"] == "FIXED_LEVELS"
        print("✓ GET /partial-close/matrix - strategy-partial matrix returned")


class TestTimeStopEngine:
    """Tests for time stop engine"""
    
    def test_get_time_stop_types(self):
        """Test GET /api/position-policy/time-stop returns 4 time stop types"""
        response = requests.get(f"{BASE_URL}/api/position-policy/time-stop")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["timeStopTypes"]) == 4
        
        time_stop_names = [t["type"] for t in data["timeStopTypes"]]
        assert "BAR_BASED" in time_stop_names
        assert "TIME_BASED" in time_stop_names
        assert "SESSION_BASED" in time_stop_names
        assert "NONE" in time_stop_names
        print("✓ GET /time-stop - 4 time stop types returned")
    
    def test_evaluate_time_stop_exceeded(self):
        """Test POST /api/position-policy/time-stop/evaluate - bars exceeded"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "bars_held": 15,  # Exceeds max_bars=10
            "entry_price": 100.0,
            "current_price": 99.0,  # At loss
            "direction": "LONG",
            "current_position_size": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/time-stop/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["shouldExit"] == True
        assert data["barsHeld"] == 15
        assert data["maxBars"] == 10
        print(f"✓ Time stop exceeded: shouldExit={data['shouldExit']}, exitType={data['exitType']}")
    
    def test_evaluate_time_stop_not_exceeded(self):
        """Test POST /api/position-policy/time-stop/evaluate - bars not exceeded"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "bars_held": 5,  # Under max_bars=10
            "entry_price": 100.0,
            "current_price": 101.0,
            "direction": "LONG",
            "current_position_size": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/time-stop/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["shouldExit"] == False
        assert data["barsHeld"] == 5
        print(f"✓ Time stop not exceeded: shouldExit={data['shouldExit']}")
    
    def test_get_time_stop_matrix(self):
        """Test GET /api/position-policy/time-stop/matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/time-stop/matrix")
        assert response.status_code == 200
        
        data = response.json()
        
        # MOMENTUM_BREAKOUT has required time stop (10 bars)
        assert data["MOMENTUM_BREAKOUT"]["timeStopType"] == "BAR_BASED"
        assert data["MOMENTUM_BREAKOUT"]["maxBars"] == 10
        assert data["MOMENTUM_BREAKOUT"]["required"] == True
        
        # MEAN_REVERSION has required time stop (30 bars)
        assert data["MEAN_REVERSION"]["timeStopType"] == "BAR_BASED"
        assert data["MEAN_REVERSION"]["maxBars"] == 30
        assert data["MEAN_REVERSION"]["required"] == True
        
        # TREND_CONFIRMATION has optional time stop (50 bars)
        assert data["TREND_CONFIRMATION"]["timeStopType"] == "BAR_BASED"
        assert data["TREND_CONFIRMATION"]["maxBars"] == 50
        print("✓ GET /time-stop/matrix - strategy-time stop matrix returned")


class TestForcedExitEngine:
    """Tests for forced exit engine"""
    
    def test_get_forced_exit_triggers(self):
        """Test GET /api/position-policy/forced-exit returns 6 triggers"""
        response = requests.get(f"{BASE_URL}/api/position-policy/forced-exit")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["triggers"]) == 6
        
        trigger_names = [t["trigger"] for t in data["triggers"]]
        assert "REGIME_SWITCH" in trigger_names
        assert "VOLATILITY_SPIKE" in trigger_names
        assert "STRUCTURE_BREAK" in trigger_names
        assert "RISK_LIMIT_BREACH" in trigger_names
        assert "CORRELATION_SPIKE" in trigger_names
        assert "DRAWDOWN_LIMIT" in trigger_names
        print("✓ GET /forced-exit - 6 triggers returned")
    
    def test_evaluate_forced_exit_regime_switch(self):
        """Test POST /api/position-policy/forced-exit/evaluate - regime switch trigger"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "current_regime": "RANGE",
            "previous_regime": "TRENDING",  # Regime changed
            "current_volatility": 1.0,
            "normal_volatility": 1.0,
            "structure_broken": False,
            "position_pnl_pct": 0.5,
            "daily_pnl_pct": 1.0,
            "correlation_spike": False
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/forced-exit/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["forceExit"] == True
        assert "REGIME_SWITCH" in data["triggersFired"]
        print(f"✓ Forced exit (regime switch): forceExit={data['forceExit']}, triggers={data['triggersFired']}")
    
    def test_evaluate_forced_exit_volatility_spike(self):
        """Test POST /api/position-policy/forced-exit/evaluate - volatility spike trigger"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "current_regime": "TRENDING",
            "previous_regime": "TRENDING",
            "current_volatility": 3.0,  # 3x normal
            "normal_volatility": 1.0,
            "structure_broken": False,
            "position_pnl_pct": 0.5,
            "daily_pnl_pct": 1.0,
            "correlation_spike": False
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/forced-exit/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["forceExit"] == True
        assert "VOLATILITY_SPIKE" in data["triggersFired"]
        print(f"✓ Forced exit (volatility spike): forceExit={data['forceExit']}")
    
    def test_evaluate_forced_exit_risk_limit(self):
        """Test POST /api/position-policy/forced-exit/evaluate - risk limit trigger"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "current_regime": "TRENDING",
            "previous_regime": "TRENDING",
            "current_volatility": 1.0,
            "normal_volatility": 1.0,
            "structure_broken": False,
            "position_pnl_pct": -2.0,  # Exceeds max_position_loss_pct=1.5
            "daily_pnl_pct": -1.0,
            "correlation_spike": False
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/forced-exit/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["forceExit"] == True
        assert "RISK_LIMIT_BREACH" in data["triggersFired"]
        print(f"✓ Forced exit (risk limit): forceExit={data['forceExit']}")
    
    def test_get_forced_exit_matrix(self):
        """Test GET /api/position-policy/forced-exit/matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/forced-exit/matrix")
        assert response.status_code == 200
        
        data = response.json()
        
        # MOMENTUM_BREAKOUT has 4 triggers
        assert len(data["MOMENTUM_BREAKOUT"]["triggers"]) == 4
        assert "REGIME_SWITCH" in data["MOMENTUM_BREAKOUT"]["triggers"]
        assert "VOLATILITY_SPIKE" in data["MOMENTUM_BREAKOUT"]["triggers"]
        
        # MEAN_REVERSION has DRAWDOWN_LIMIT
        assert "DRAWDOWN_LIMIT" in data["MEAN_REVERSION"]["triggers"]
        print("✓ GET /forced-exit/matrix - strategy-forced exit matrix returned")


class TestCombinedMatrixAndEvaluation:
    """Tests for combined matrix and full evaluation"""
    
    def test_get_complete_matrix(self):
        """Test GET /api/position-policy/matrix - complete strategy-policy matrix"""
        response = requests.get(f"{BASE_URL}/api/position-policy/matrix")
        assert response.status_code == 200
        
        data = response.json()
        assert "matrix" in data
        
        matrix = data["matrix"]
        assert "TREND_CONFIRMATION" in matrix
        assert "MOMENTUM_BREAKOUT" in matrix
        assert "MEAN_REVERSION" in matrix
        
        # Verify matrix structure
        for strategy in matrix:
            assert "stop" in matrix[strategy]
            assert "tp" in matrix[strategy]
            assert "trailing" in matrix[strategy]
            assert "partialClose" in matrix[strategy]
            assert "timeStop" in matrix[strategy]
        print("✓ GET /matrix - complete strategy-policy matrix returned")
    
    def test_full_position_evaluation(self):
        """Test POST /api/position-policy/evaluate - full position evaluation"""
        payload = {
            "strategy": "MOMENTUM_BREAKOUT",
            "entry_price": 100.0,
            "current_price": 102.0,
            "stop_price": 98.0,
            "target_price": 104.0,
            "direction": "LONG",
            "bars_held": 5,
            "current_regime": "TRENDING",
            "previous_regime": "TRENDING",
            "atr": 1.5,
            "current_volatility": 1.0,
            "structure_broken": False,
            "position_pnl_pct": 2.0
        }
        response = requests.post(f"{BASE_URL}/api/position-policy/evaluate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MOMENTUM_BREAKOUT"
        
        # Verify all components are evaluated
        assert "position" in data
        assert "trailing" in data
        assert "partialClose" in data
        assert "timeStop" in data
        assert "forcedExit" in data
        
        # Verify position data
        assert data["position"]["entryPrice"] == 100.0
        assert data["position"]["currentPrice"] == 102.0
        assert data["position"]["direction"] == "LONG"
        assert data["position"]["pnlPct"] > 0  # Should be in profit
        print(f"✓ Full evaluation: pnlPct={data['position']['pnlPct']:.2f}%")


class TestRegressionPhase1_1:
    """Regression tests for PHASE 1.1 Strategy Doctrine"""
    
    def test_strategy_doctrine_health(self):
        """Test PHASE 1.1 /api/strategy-doctrine/health"""
        response = requests.get(f"{BASE_URL}/api/strategy-doctrine/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ PHASE 1.1 Regression: /api/strategy-doctrine/health - healthy")
    
    def test_strategy_doctrine_strategies(self):
        """Test PHASE 1.1 /api/strategy-doctrine/strategies returns 3 strategies"""
        response = requests.get(f"{BASE_URL}/api/strategy-doctrine/strategies")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        print("✓ PHASE 1.1 Regression: /api/strategy-doctrine/strategies - 3 strategies")


class TestRegressionPhase1_2:
    """Regression tests for PHASE 1.2 Execution Styles"""
    
    def test_execution_styles_health(self):
        """Test PHASE 1.2 /api/execution-styles/health"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ PHASE 1.2 Regression: /api/execution-styles/health - healthy")
    
    def test_execution_styles_list(self):
        """Test PHASE 1.2 /api/execution-styles returns 5 styles"""
        response = requests.get(f"{BASE_URL}/api/execution-styles")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 5
        print("✓ PHASE 1.2 Regression: /api/execution-styles - 5 styles")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
