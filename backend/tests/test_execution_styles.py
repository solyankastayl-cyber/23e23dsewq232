"""
PHASE 1.2 Execution Styles API Tests
=====================================

Tests for Execution Styles module endpoints:
- Style definitions (5 styles: CLEAN_ENTRY, SCALED_ENTRY, PARTIAL_EXIT, TIME_EXIT, DEFENSIVE_EXIT)
- Compatibility matrices (strategy, profile, regime)
- Blocking rules and policy evaluation
- Style selection and recommendations
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestExecutionStylesHealth:
    """Health check and basic connectivity tests"""
    
    def test_health_check(self):
        """Test execution styles health endpoint"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["module"] == "PHASE 1.2 Execution Styles"
        assert data["status"] == "healthy"
        assert data["stylesLoaded"] == 5
        assert data["policyRules"] >= 6
        print(f"✓ Health check passed: {data['stylesLoaded']} styles, {data['policyRules']} rules")


class TestStyleDefinitions:
    """Tests for style definition endpoints"""
    
    def test_get_all_styles(self):
        """Test GET /api/execution-styles - should return 5 styles"""
        response = requests.get(f"{BASE_URL}/api/execution-styles")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 5
        assert len(data["styles"]) == 5
        
        style_types = [s["styleType"] for s in data["styles"]]
        expected_styles = ["CLEAN_ENTRY", "SCALED_ENTRY", "PARTIAL_EXIT", "TIME_EXIT", "DEFENSIVE_EXIT"]
        for expected in expected_styles:
            assert expected in style_types, f"Missing style: {expected}"
        
        print(f"✓ All 5 styles retrieved: {style_types}")
    
    def test_get_entry_styles(self):
        """Test GET /api/execution-styles/entry - should return 2 entry styles"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/entry")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 2
        
        style_types = [s["styleType"] for s in data["styles"]]
        assert "CLEAN_ENTRY" in style_types
        assert "SCALED_ENTRY" in style_types
        print(f"✓ Entry styles: {style_types}")
    
    def test_get_exit_styles(self):
        """Test GET /api/execution-styles/exit - should return 3 exit styles"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/exit")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        
        style_types = [s["styleType"] for s in data["styles"]]
        assert "PARTIAL_EXIT" in style_types
        assert "TIME_EXIT" in style_types
        assert "DEFENSIVE_EXIT" in style_types
        print(f"✓ Exit styles: {style_types}")
    
    def test_get_clean_entry_style(self):
        """Test GET /api/execution-styles/CLEAN_ENTRY"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/CLEAN_ENTRY")
        assert response.status_code == 200
        
        data = response.json()
        assert data["styleType"] == "CLEAN_ENTRY"
        assert data["name"] == "Clean Entry"
        assert data["entry"]["behavior"] == "SINGLE"
        assert data["entry"]["maxEntries"] == 1
        assert data["riskImplications"]["riskLevel"] == "LOW"
        print(f"✓ CLEAN_ENTRY: {data['name']} - {data['description'][:50]}...")
    
    def test_get_scaled_entry_style(self):
        """Test GET /api/execution-styles/SCALED_ENTRY"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/SCALED_ENTRY")
        assert response.status_code == 200
        
        data = response.json()
        assert data["styleType"] == "SCALED_ENTRY"
        assert data["name"] == "Scaled Entry"
        assert data["entry"]["behavior"] == "LADDER"
        assert data["entry"]["maxEntries"] == 3
        assert data["riskImplications"]["riskLevel"] == "MODERATE"
        print(f"✓ SCALED_ENTRY: {data['name']} - max {data['entry']['maxEntries']} entries")
    
    def test_get_partial_exit_style(self):
        """Test GET /api/execution-styles/PARTIAL_EXIT"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/PARTIAL_EXIT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["styleType"] == "PARTIAL_EXIT"
        assert data["exit"]["behavior"] == "PARTIAL_SCALING"
        assert len(data["exit"]["partialExits"]) >= 2
        print(f"✓ PARTIAL_EXIT: {len(data['exit']['partialExits'])} partial exit levels")
    
    def test_get_time_exit_style(self):
        """Test GET /api/execution-styles/TIME_EXIT"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/TIME_EXIT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["styleType"] == "TIME_EXIT"
        assert data["exit"]["behavior"] == "TIME_BASED"
        assert data["exit"]["timeExit"]["enabled"] == True
        assert data["exit"]["timeExit"]["bars"] > 0
        print(f"✓ TIME_EXIT: exits after {data['exit']['timeExit']['bars']} bars")
    
    def test_get_defensive_exit_style(self):
        """Test GET /api/execution-styles/DEFENSIVE_EXIT"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/DEFENSIVE_EXIT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["styleType"] == "DEFENSIVE_EXIT"
        assert data["exit"]["behavior"] == "DEFENSIVE"
        assert data["exit"]["defensive"]["enabled"] == True
        assert data["riskImplications"]["riskLevel"] == "LOW"
        print(f"✓ DEFENSIVE_EXIT: structure_break={data['exit']['defensive']['structureBreakExit']}")
    
    def test_invalid_style_returns_400(self):
        """Test invalid style type returns 400"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/INVALID_STYLE")
        assert response.status_code == 400
        print("✓ Invalid style correctly returns 400")


class TestPolicyRules:
    """Tests for policy rules endpoint"""
    
    def test_get_policy_rules(self):
        """Test GET /api/execution-styles/rules - should return 6 rules"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/rules")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] >= 6
        
        # Check for expected blocking rules
        rule_ids = [r["ruleId"] for r in data["rules"]]
        expected_rules = [
            "BLOCK_SCALED_MOMENTUM",
            "BLOCK_SCALED_CONSERVATIVE",
            "BLOCK_SCALED_HIGHVOL",
            "BLOCK_SCALED_TRANSITION"
        ]
        
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule: {expected}"
        
        print(f"✓ Policy rules: {data['count']} rules found")
        for rule in data["rules"]:
            print(f"  - {rule['ruleId']}: {rule['action']} - {rule['reason'][:50]}...")


class TestCompatibilityMatrices:
    """Tests for compatibility matrix endpoints"""
    
    def test_strategy_matrix(self):
        """Test GET /api/execution-styles/matrix/strategy"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/matrix/strategy")
        assert response.status_code == 200
        
        data = response.json()
        matrix = data["matrix"]
        
        # Check all 3 strategies present
        assert "TREND_CONFIRMATION" in matrix
        assert "MOMENTUM_BREAKOUT" in matrix
        assert "MEAN_REVERSION" in matrix
        
        # Verify MOMENTUM_BREAKOUT blocks SCALED_ENTRY
        assert matrix["MOMENTUM_BREAKOUT"]["SCALED_ENTRY"] == "FORBIDDEN"
        
        # Verify MEAN_REVERSION allows SCALED_ENTRY (OPTIMAL)
        assert matrix["MEAN_REVERSION"]["SCALED_ENTRY"] == "OPTIMAL"
        
        print(f"✓ Strategy matrix: 3 strategies mapped")
        print(f"  - MOMENTUM_BREAKOUT + SCALED_ENTRY = {matrix['MOMENTUM_BREAKOUT']['SCALED_ENTRY']}")
        print(f"  - MEAN_REVERSION + SCALED_ENTRY = {matrix['MEAN_REVERSION']['SCALED_ENTRY']}")
    
    def test_profile_matrix(self):
        """Test GET /api/execution-styles/matrix/profile"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/matrix/profile")
        assert response.status_code == 200
        
        data = response.json()
        matrix = data["matrix"]
        
        # Check all 3 profiles present
        assert "CONSERVATIVE" in matrix
        assert "BALANCED" in matrix
        assert "AGGRESSIVE" in matrix
        
        # Verify CONSERVATIVE blocks SCALED_ENTRY
        assert matrix["CONSERVATIVE"]["SCALED_ENTRY"] == "FORBIDDEN"
        
        # Verify BALANCED allows SCALED_ENTRY
        assert matrix["BALANCED"]["SCALED_ENTRY"] == "ALLOWED"
        
        print(f"✓ Profile matrix: 3 profiles mapped")
        print(f"  - CONSERVATIVE + SCALED_ENTRY = {matrix['CONSERVATIVE']['SCALED_ENTRY']}")
        print(f"  - BALANCED + SCALED_ENTRY = {matrix['BALANCED']['SCALED_ENTRY']}")
    
    def test_regime_matrix(self):
        """Test GET /api/execution-styles/matrix/regime"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/matrix/regime")
        assert response.status_code == 200
        
        data = response.json()
        matrix = data["matrix"]
        
        # Check all 5 regimes present
        expected_regimes = ["TRENDING", "RANGE", "HIGH_VOLATILITY", "LOW_VOLATILITY", "TRANSITION"]
        for regime in expected_regimes:
            assert regime in matrix, f"Missing regime: {regime}"
        
        # Verify HIGH_VOLATILITY blocks SCALED_ENTRY
        assert matrix["HIGH_VOLATILITY"]["SCALED_ENTRY"] == "FORBIDDEN"
        
        # Verify RANGE allows SCALED_ENTRY (OPTIMAL)
        assert matrix["RANGE"]["SCALED_ENTRY"] == "OPTIMAL"
        
        print(f"✓ Regime matrix: 5 regimes mapped")
        print(f"  - HIGH_VOLATILITY + SCALED_ENTRY = {matrix['HIGH_VOLATILITY']['SCALED_ENTRY']}")
        print(f"  - RANGE + SCALED_ENTRY = {matrix['RANGE']['SCALED_ENTRY']}")


class TestStrategyCompatibility:
    """Tests for strategy compatibility endpoints"""
    
    def test_momentum_breakout_compatibility(self):
        """Test MOMENTUM_BREAKOUT compatibility - SCALED should be FORBIDDEN"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/compatibility/strategy/MOMENTUM_BREAKOUT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MOMENTUM_BREAKOUT"
        
        # SCALED_ENTRY should be forbidden
        assert data["styles"]["SCALED_ENTRY"]["level"] == "FORBIDDEN"
        assert data["styles"]["SCALED_ENTRY"]["allowed"] == False
        
        # CLEAN_ENTRY should be optimal
        assert data["styles"]["CLEAN_ENTRY"]["level"] == "OPTIMAL"
        assert data["styles"]["CLEAN_ENTRY"]["allowed"] == True
        
        # SCALED_ENTRY should NOT be in allowed styles
        assert "SCALED_ENTRY" not in data["allowedStyles"]
        
        print(f"✓ MOMENTUM_BREAKOUT: SCALED_ENTRY={data['styles']['SCALED_ENTRY']['level']}")
        print(f"  Allowed styles: {data['allowedStyles']}")
    
    def test_mean_reversion_compatibility(self):
        """Test MEAN_REVERSION compatibility - SCALED should be OPTIMAL"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/compatibility/strategy/MEAN_REVERSION")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MEAN_REVERSION"
        
        # SCALED_ENTRY should be optimal
        assert data["styles"]["SCALED_ENTRY"]["level"] == "OPTIMAL"
        assert data["styles"]["SCALED_ENTRY"]["allowed"] == True
        
        # SCALED_ENTRY should be in allowed styles
        assert "SCALED_ENTRY" in data["allowedStyles"]
        
        print(f"✓ MEAN_REVERSION: SCALED_ENTRY={data['styles']['SCALED_ENTRY']['level']}")
        print(f"  Allowed styles: {data['allowedStyles']}")


class TestProfileCompatibility:
    """Tests for profile compatibility endpoints"""
    
    def test_conservative_compatibility(self):
        """Test CONSERVATIVE profile - SCALED should be FORBIDDEN"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/compatibility/profile/CONSERVATIVE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["profile"] == "CONSERVATIVE"
        
        # SCALED_ENTRY should be forbidden
        assert data["styles"]["SCALED_ENTRY"]["level"] == "FORBIDDEN"
        assert data["styles"]["SCALED_ENTRY"]["allowed"] == False
        
        # SCALED_ENTRY should NOT be in allowed styles
        assert "SCALED_ENTRY" not in data["allowedStyles"]
        
        print(f"✓ CONSERVATIVE: SCALED_ENTRY={data['styles']['SCALED_ENTRY']['level']}")
    
    def test_balanced_compatibility(self):
        """Test BALANCED profile - SCALED should be ALLOWED"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/compatibility/profile/BALANCED")
        assert response.status_code == 200
        
        data = response.json()
        assert data["profile"] == "BALANCED"
        
        # SCALED_ENTRY should be allowed
        assert data["styles"]["SCALED_ENTRY"]["level"] == "ALLOWED"
        assert data["styles"]["SCALED_ENTRY"]["allowed"] == True
        
        # SCALED_ENTRY should be in allowed styles
        assert "SCALED_ENTRY" in data["allowedStyles"]
        
        print(f"✓ BALANCED: SCALED_ENTRY={data['styles']['SCALED_ENTRY']['level']}")


class TestStyleSelection:
    """Tests for style selection endpoints"""
    
    def test_select_trend_confirmation_balanced(self):
        """Test selection for TREND_CONFIRMATION/BALANCED - should allow 5 styles"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/select/TREND_CONFIRMATION/BALANCED")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "TREND_CONFIRMATION"
        assert data["profile"] == "BALANCED"
        
        # Should have 5 allowed styles (all styles allowed for this combo)
        assert data["allowedCount"] == 5
        assert data["blockedCount"] == 0
        
        print(f"✓ TREND_CONFIRMATION/BALANCED: {data['allowedCount']} allowed, {data['blockedCount']} blocked")
    
    def test_select_momentum_breakout_conservative(self):
        """Test selection for MOMENTUM_BREAKOUT/CONSERVATIVE - should block SCALED_ENTRY"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/select/MOMENTUM_BREAKOUT/CONSERVATIVE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MOMENTUM_BREAKOUT"
        assert data["profile"] == "CONSERVATIVE"
        
        # SCALED_ENTRY should be blocked
        scaled_style = next((s for s in data["styles"] if s["style"] == "SCALED_ENTRY"), None)
        assert scaled_style is not None
        assert scaled_style["blocked"] == True
        assert scaled_style["allowed"] == False
        
        # Should have 4 allowed styles (SCALED_ENTRY blocked)
        assert data["allowedCount"] == 4
        assert data["blockedCount"] == 1
        
        print(f"✓ MOMENTUM_BREAKOUT/CONSERVATIVE: {data['allowedCount']} allowed, {data['blockedCount']} blocked")
        print(f"  SCALED_ENTRY blocked: {scaled_style['blockReason']}")
    
    def test_select_mean_reversion_balanced_range(self):
        """Test selection with regime RANGE - all should be allowed"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/select/MEAN_REVERSION/BALANCED?regime=RANGE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MEAN_REVERSION"
        assert data["profile"] == "BALANCED"
        assert data["regime"] == "RANGE"
        
        # All styles should be allowed in RANGE regime for MEAN_REVERSION/BALANCED
        assert data["allowedCount"] == 5
        assert data["blockedCount"] == 0
        
        print(f"✓ MEAN_REVERSION/BALANCED/RANGE: {data['allowedCount']} allowed")
    
    def test_select_trend_confirmation_balanced_high_volatility(self):
        """Test selection with HIGH_VOLATILITY regime - SCALED should be blocked"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/select/TREND_CONFIRMATION/BALANCED?regime=HIGH_VOLATILITY")
        assert response.status_code == 200
        
        data = response.json()
        assert data["regime"] == "HIGH_VOLATILITY"
        
        # SCALED_ENTRY should be blocked in HIGH_VOLATILITY
        scaled_style = next((s for s in data["styles"] if s["style"] == "SCALED_ENTRY"), None)
        assert scaled_style is not None
        assert scaled_style["blocked"] == True
        
        # Should have 4 allowed styles
        assert data["allowedCount"] == 4
        assert data["blockedCount"] == 1
        
        print(f"✓ HIGH_VOLATILITY regime: SCALED_ENTRY blocked")


class TestStyleRecommendation:
    """Tests for style recommendation endpoints"""
    
    def test_recommend_momentum_breakout_aggressive(self):
        """Test recommendation for MOMENTUM_BREAKOUT/AGGRESSIVE - entry=CLEAN, exit=TIME_EXIT"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/recommend/MOMENTUM_BREAKOUT/AGGRESSIVE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MOMENTUM_BREAKOUT"
        assert data["profile"] == "AGGRESSIVE"
        
        # Should recommend CLEAN_ENTRY (SCALED is blocked for momentum)
        assert data["recommendation"]["entryStyle"] == "CLEAN_ENTRY"
        
        # Should recommend TIME_EXIT for momentum
        assert data["recommendation"]["exitStyle"] == "TIME_EXIT"
        
        # Should always have DEFENSIVE_EXIT available
        assert data["recommendation"]["defensiveStyle"] == "DEFENSIVE_EXIT"
        
        print(f"✓ MOMENTUM_BREAKOUT/AGGRESSIVE recommendation:")
        print(f"  Entry: {data['recommendation']['entryStyle']}")
        print(f"  Exit: {data['recommendation']['exitStyle']}")
    
    def test_recommend_mean_reversion_balanced(self):
        """Test recommendation for MEAN_REVERSION/BALANCED - should prefer SCALED if allowed"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/recommend/MEAN_REVERSION/BALANCED")
        assert response.status_code == 200
        
        data = response.json()
        assert data["strategy"] == "MEAN_REVERSION"
        assert data["profile"] == "BALANCED"
        
        # Should recommend SCALED_ENTRY for mean reversion (optimal)
        assert data["recommendation"]["entryStyle"] == "SCALED_ENTRY"
        
        # Should have entry details
        assert data["entryDetails"] is not None
        assert data["entryDetails"]["styleType"] == "SCALED_ENTRY"
        
        print(f"✓ MEAN_REVERSION/BALANCED recommendation:")
        print(f"  Entry: {data['recommendation']['entryStyle']}")
        print(f"  Exit: {data['recommendation']['exitStyle']}")


class TestPolicyEvaluation:
    """Tests for policy evaluation endpoints"""
    
    def test_policy_scaled_entry_momentum_breakout(self):
        """Test policy for SCALED_ENTRY with MOMENTUM_BREAKOUT - should be blocked"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/policy/SCALED_ENTRY?strategy=MOMENTUM_BREAKOUT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["style"] == "SCALED_ENTRY"
        assert data["blocked"] == True
        assert data["allowed"] == False
        assert "MOMENTUM" in data["blockReason"].upper() or "momentum" in data["blockReason"].lower()
        
        print(f"✓ SCALED_ENTRY + MOMENTUM_BREAKOUT: blocked={data['blocked']}")
        print(f"  Reason: {data['blockReason']}")
    
    def test_policy_scaled_entry_high_volatility(self):
        """Test policy for SCALED_ENTRY with HIGH_VOLATILITY - should be blocked"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/policy/SCALED_ENTRY?regime=HIGH_VOLATILITY")
        assert response.status_code == 200
        
        data = response.json()
        assert data["style"] == "SCALED_ENTRY"
        assert data["blocked"] == True
        assert data["allowed"] == False
        
        print(f"✓ SCALED_ENTRY + HIGH_VOLATILITY: blocked={data['blocked']}")
        print(f"  Reason: {data['blockReason']}")
    
    def test_policy_clean_entry_momentum_breakout(self):
        """Test policy for CLEAN_ENTRY with MOMENTUM_BREAKOUT - should NOT be blocked"""
        response = requests.get(f"{BASE_URL}/api/execution-styles/policy/CLEAN_ENTRY?strategy=MOMENTUM_BREAKOUT")
        assert response.status_code == 200
        
        data = response.json()
        assert data["style"] == "CLEAN_ENTRY"
        assert data["blocked"] == False
        assert data["allowed"] == True
        
        print(f"✓ CLEAN_ENTRY + MOMENTUM_BREAKOUT: blocked={data['blocked']}, allowed={data['allowed']}")


class TestStrategyDoctrineRegression:
    """Regression tests for PHASE 1.1 Strategy Doctrine"""
    
    def test_strategy_doctrine_health(self):
        """Test PHASE 1.1 Strategy Doctrine health - should still work"""
        response = requests.get(f"{BASE_URL}/api/strategy-doctrine/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["strategiesLoaded"] == 3
        
        print(f"✓ Strategy Doctrine health: {data['status']}")
    
    def test_strategy_doctrine_strategies(self):
        """Test PHASE 1.1 Strategy Doctrine strategies - should still work"""
        response = requests.get(f"{BASE_URL}/api/strategy-doctrine/strategies")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        
        strategy_types = [s["strategyType"] for s in data["strategies"]]
        assert "TREND_CONFIRMATION" in strategy_types
        assert "MOMENTUM_BREAKOUT" in strategy_types
        assert "MEAN_REVERSION" in strategy_types
        
        print(f"✓ Strategy Doctrine strategies: {strategy_types}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
