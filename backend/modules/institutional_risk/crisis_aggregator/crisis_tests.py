"""
PHASE 22.5 — Crisis Exposure Tests
==================================
Test suite for Crisis Exposure Aggregator.

Tests:
1. All low states -> NORMAL
2. Mixed elevated -> GUARDED
3. High tail + high correlation -> STRESSED
4. All critical/systemic -> CRISIS
5. Crisis score calculation correct
6. Modifiers use min() correctly
7. Strongest risk detected correctly
8. Weakest risk detected correctly
9. Recommended action correct
10. API output correct
"""

import pytest
from .crisis_types import (
    CrisisState,
    CrisisAction,
    CrisisExposureState,
    STATE_SCORES,
    CRISIS_SCORE_WEIGHTS,
)
from .crisis_exposure_engine import CrisisExposureEngine


class TestCrisisExposureEngine:
    """Tests for Crisis Exposure Engine."""
    
    @pytest.fixture
    def engine(self):
        return CrisisExposureEngine()
    
    # ═══════════════════════════════════════════════════════════
    # TEST 1: All low states -> NORMAL
    # ═══════════════════════════════════════════════════════════
    
    def test_all_low_normal(self, engine):
        """All low risk states should produce NORMAL crisis state."""
        state = engine.calculate(
            var_state="NORMAL",
            tail_state="LOW",
            contagion_state="LOW",
            correlation_state="NORMAL",
        )
        
        assert state.crisis_state == CrisisState.NORMAL
        assert state.crisis_score < 0.30
        assert state.recommended_action == CrisisAction.HOLD
        assert state.confidence_modifier == 1.0
        assert state.capital_modifier == 1.0
    
    # ═══════════════════════════════════════════════════════════
    # TEST 2: Mixed elevated -> GUARDED
    # ═══════════════════════════════════════════════════════════
    
    def test_mixed_elevated_guarded(self, engine):
        """Mixed elevated states should produce GUARDED crisis state."""
        state = engine.calculate(
            var_state="ELEVATED",
            tail_state="ELEVATED",
            contagion_state="LOW",
            correlation_state="ELEVATED",
        )
        
        assert state.crisis_state == CrisisState.GUARDED
        assert 0.30 <= state.crisis_score < 0.50
        assert state.recommended_action == CrisisAction.REDUCE_RISK
    
    # ═══════════════════════════════════════════════════════════
    # TEST 3: High tail + high correlation -> STRESSED
    # ═══════════════════════════════════════════════════════════
    
    def test_high_tail_correlation_stressed(self, engine):
        """High tail risk and correlation should produce STRESSED state."""
        state = engine.calculate(
            var_state="ELEVATED",
            tail_state="HIGH",
            contagion_state="ELEVATED",
            correlation_state="HIGH",
        )
        
        assert state.crisis_state == CrisisState.STRESSED
        assert 0.50 <= state.crisis_score < 0.70
        assert state.recommended_action == CrisisAction.DELEVER
    
    # ═══════════════════════════════════════════════════════════
    # TEST 4: All critical/systemic -> CRISIS
    # ═══════════════════════════════════════════════════════════
    
    def test_all_critical_crisis(self, engine):
        """All critical/systemic states should produce CRISIS state."""
        state = engine.calculate(
            var_state="CRITICAL",
            tail_state="EXTREME",
            contagion_state="SYSTEMIC",
            correlation_state="SYSTEMIC",
        )
        
        assert state.crisis_state == CrisisState.CRISIS
        assert state.crisis_score >= 0.70
        assert state.recommended_action == CrisisAction.EMERGENCY_MODE
    
    # ═══════════════════════════════════════════════════════════
    # TEST 5: Crisis score calculation correct
    # ═══════════════════════════════════════════════════════════
    
    def test_crisis_score_calculation(self, engine):
        """Crisis score should be weighted sum of normalized states."""
        state = engine.calculate(
            var_state="HIGH",           # 0.70
            tail_state="ELEVATED",      # 0.45
            contagion_state="LOW",      # 0.20
            correlation_state="HIGH",   # 0.70
        )
        
        # Expected: 0.30*0.70 + 0.25*0.45 + 0.25*0.20 + 0.20*0.70
        expected = 0.30*0.70 + 0.25*0.45 + 0.25*0.20 + 0.20*0.70
        
        assert abs(state.crisis_score - expected) < 0.01
    
    # ═══════════════════════════════════════════════════════════
    # TEST 6: Modifiers use min() correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_modifiers_use_min(self, engine):
        """Combined modifiers should use min() logic."""
        state = engine.calculate(
            var_state="NORMAL",
            var_confidence_modifier=1.0,
            var_capital_modifier=1.0,
            
            tail_state="LOW",
            tail_confidence_modifier=0.95,
            tail_capital_modifier=0.90,
            
            contagion_state="LOW",
            contagion_confidence_modifier=0.85,
            contagion_capital_modifier=0.75,
            
            correlation_state="NORMAL",
            correlation_confidence_modifier=0.90,
            correlation_capital_modifier=0.80,
        )
        
        # Should be min of all
        assert state.confidence_modifier == 0.85  # min(1.0, 0.95, 0.85, 0.90)
        assert state.capital_modifier == 0.75     # min(1.0, 0.90, 0.75, 0.80)
    
    # ═══════════════════════════════════════════════════════════
    # TEST 7: Strongest risk detected correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_strongest_risk_detected(self, engine):
        """Strongest risk should be dimension with highest score."""
        state = engine.calculate(
            var_state="ELEVATED",      # 0.45
            tail_state="HIGH",         # 0.70 <- highest
            contagion_state="LOW",     # 0.20
            correlation_state="NORMAL", # 0.20
        )
        
        assert state.strongest_risk == "tail"
        assert state.tail_score == 0.70
    
    # ═══════════════════════════════════════════════════════════
    # TEST 8: Weakest risk detected correctly
    # ═══════════════════════════════════════════════════════════
    
    def test_weakest_risk_detected(self, engine):
        """Weakest risk should be dimension with lowest score."""
        state = engine.calculate(
            var_state="HIGH",          # 0.70
            tail_state="HIGH",         # 0.70
            contagion_state="LOW",     # 0.20 <- lowest
            correlation_state="HIGH",  # 0.70
        )
        
        assert state.weakest_risk == "contagion"
        assert state.contagion_score == 0.20
    
    # ═══════════════════════════════════════════════════════════
    # TEST 9: Recommended action correct
    # ═══════════════════════════════════════════════════════════
    
    def test_recommended_actions(self, engine):
        """Recommended actions should match crisis states."""
        # NORMAL -> HOLD
        state_normal = engine.calculate(
            var_state="NORMAL",
            tail_state="LOW",
            contagion_state="LOW",
            correlation_state="NORMAL",
        )
        assert state_normal.recommended_action == CrisisAction.HOLD
        
        # GUARDED -> REDUCE_RISK
        state_guarded = engine.calculate(
            var_state="ELEVATED",
            tail_state="ELEVATED",
            contagion_state="LOW",
            correlation_state="ELEVATED",
        )
        assert state_guarded.recommended_action == CrisisAction.REDUCE_RISK
        
        # STRESSED -> DELEVER
        state_stressed = engine.calculate(
            var_state="HIGH",
            tail_state="HIGH",
            contagion_state="ELEVATED",
            correlation_state="HIGH",
        )
        assert state_stressed.recommended_action == CrisisAction.DELEVER
        
        # CRISIS -> EMERGENCY_MODE
        state_crisis = engine.calculate(
            var_state="CRITICAL",
            tail_state="EXTREME",
            contagion_state="SYSTEMIC",
            correlation_state="SYSTEMIC",
        )
        assert state_crisis.recommended_action == CrisisAction.EMERGENCY_MODE
    
    # ═══════════════════════════════════════════════════════════
    # TEST 10: API output correct
    # ═══════════════════════════════════════════════════════════
    
    def test_api_output_format(self, engine):
        """API output should have correct format."""
        state = engine.calculate(
            var_state="ELEVATED",
            tail_state="HIGH",
            contagion_state="LOW",
            correlation_state="HIGH",
        )
        
        output = state.to_dict()
        
        # Check required fields
        assert "var_state" in output
        assert "tail_state" in output
        assert "contagion_state" in output
        assert "correlation_state" in output
        assert "crisis_score" in output
        assert "crisis_state" in output
        assert "recommended_action" in output
        assert "confidence_modifier" in output
        assert "capital_modifier" in output
        assert "strongest_risk" in output
        assert "weakest_risk" in output
        assert "reason" in output
        assert "timestamp" in output
        
        # Check types
        assert isinstance(output["crisis_score"], float)
        assert isinstance(output["crisis_state"], str)
        assert isinstance(output["recommended_action"], str)
        
        # Check ranges
        assert 0 <= output["crisis_score"] <= 1
        assert 0 <= output["confidence_modifier"] <= 1
        assert 0 <= output["capital_modifier"] <= 1
        
        # Check full dict has scores
        full_output = state.to_full_dict()
        assert "scores" in full_output
        assert "component_modifiers" in full_output


def run_all_tests():
    """Run all tests and return results."""
    test_class = TestCrisisExposureEngine()
    engine = CrisisExposureEngine()
    
    results = []
    
    tests = [
        ("test_1_all_low_normal", lambda: test_class.test_all_low_normal(engine)),
        ("test_2_mixed_elevated_guarded", lambda: test_class.test_mixed_elevated_guarded(engine)),
        ("test_3_high_tail_correlation_stressed", lambda: test_class.test_high_tail_correlation_stressed(engine)),
        ("test_4_all_critical_crisis", lambda: test_class.test_all_critical_crisis(engine)),
        ("test_5_crisis_score_calculation", lambda: test_class.test_crisis_score_calculation(engine)),
        ("test_6_modifiers_use_min", lambda: test_class.test_modifiers_use_min(engine)),
        ("test_7_strongest_risk_detected", lambda: test_class.test_strongest_risk_detected(engine)),
        ("test_8_weakest_risk_detected", lambda: test_class.test_weakest_risk_detected(engine)),
        ("test_9_recommended_actions", lambda: test_class.test_recommended_actions(engine)),
        ("test_10_api_output", lambda: test_class.test_api_output_format(engine)),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            results.append({"test": name, "status": "PASSED"})
            passed += 1
        except AssertionError as e:
            results.append({"test": name, "status": "FAILED", "error": str(e)})
            failed += 1
        except Exception as e:
            results.append({"test": name, "status": "ERROR", "error": str(e)})
            failed += 1
    
    return {
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


if __name__ == "__main__":
    results = run_all_tests()
    print(f"\n{'='*60}")
    print(f"CRISIS EXPOSURE AGGREGATOR TESTS")
    print(f"{'='*60}")
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Failed: {results['failed']}")
    print(f"\nResults:")
    for r in results["results"]:
        status = "✅" if r["status"] == "PASSED" else "❌"
        print(f"  {status} {r['test']}")
        if r["status"] != "PASSED" and "error" in r:
            print(f"     Error: {r['error']}")
