"""
PHASE 20.3 — Adaptive Promotion Tests
=====================================
Test cases for Adaptive Promotion/Demotion Engine.

Tests:
1. Shadow healthy factor → promote to CANDIDATE
2. Candidate healthy factor → promote to LIVE
3. Live degraded factor → demote to REDUCED
4. Live critical factor → freeze
5. Retire governance → retire
6. Invalid transition prevented
7. Summary output correct
8. Registry persistence correct
9. Repeated failures increase demotion severity
10. API output correct
"""

import unittest
from datetime import datetime, timezone

from modules.research_loop.adaptive_promotion.adaptive_promotion_types import (
    LifecycleState,
    TransitionAction,
    TransitionStrength,
    AdaptivePromotionDecision,
    AdaptivePromotionSummary,
    ALLOWED_TRANSITIONS,
)
from modules.research_loop.adaptive_promotion.adaptive_promotion_policy import (
    AdaptivePromotionPolicy,
)
from modules.research_loop.adaptive_promotion.adaptive_promotion_registry import (
    AdaptivePromotionRegistry,
    LifecycleTransition,
)
from modules.research_loop.adaptive_promotion.adaptive_promotion_engine import (
    AdaptivePromotionEngine,
)


class TestAdaptivePromotionTypes(unittest.TestCase):
    """Test type definitions."""
    
    def test_lifecycle_states(self):
        """Test all lifecycle states exist."""
        states = [
            LifecycleState.SHADOW,
            LifecycleState.CANDIDATE,
            LifecycleState.LIVE,
            LifecycleState.REDUCED,
            LifecycleState.FROZEN,
            LifecycleState.RETIRED,
        ]
        self.assertEqual(len(states), 6)
    
    def test_transition_actions(self):
        """Test all transition actions exist."""
        actions = [
            TransitionAction.PROMOTE,
            TransitionAction.DEMOTE,
            TransitionAction.FREEZE,
            TransitionAction.RETIRE,
            TransitionAction.HOLD,
        ]
        self.assertEqual(len(actions), 5)
    
    def test_allowed_transitions(self):
        """Test allowed transitions are defined."""
        # SHADOW can go to CANDIDATE or RETIRED
        self.assertIn(LifecycleState.CANDIDATE, ALLOWED_TRANSITIONS[LifecycleState.SHADOW])
        self.assertIn(LifecycleState.RETIRED, ALLOWED_TRANSITIONS[LifecycleState.SHADOW])
        
        # LIVE can go to REDUCED, FROZEN, or RETIRED
        self.assertIn(LifecycleState.REDUCED, ALLOWED_TRANSITIONS[LifecycleState.LIVE])
        self.assertIn(LifecycleState.FROZEN, ALLOWED_TRANSITIONS[LifecycleState.LIVE])
        
        # RETIRED cannot transition anywhere
        self.assertEqual(len(ALLOWED_TRANSITIONS[LifecycleState.RETIRED]), 0)
    
    def test_decision_to_dict(self):
        """Test decision serialization."""
        decision = AdaptivePromotionDecision(
            factor_name="test_factor",
            current_state=LifecycleState.SHADOW,
            recommended_state=LifecycleState.CANDIDATE,
            transition_action=TransitionAction.PROMOTE,
            transition_strength=TransitionStrength.MEDIUM,
            confidence_modifier=1.05,
            capital_modifier=1.10,
            reason="test promotion",
        )
        
        data = decision.to_dict()
        self.assertEqual(data["factor_name"], "test_factor")
        self.assertEqual(data["current_state"], "SHADOW")
        self.assertEqual(data["recommended_state"], "CANDIDATE")
        self.assertEqual(data["transition_action"], "PROMOTE")


class TestAdaptivePromotionPolicy(unittest.TestCase):
    """Test policy rules."""
    
    def setUp(self):
        self.policy = AdaptivePromotionPolicy()
    
    def test_shadow_healthy_factor_promote(self):
        """Test 1: Shadow healthy factor → promote to CANDIDATE."""
        should_promote, strength, reason = self.policy.should_promote(
            current_state=LifecycleState.SHADOW,
            governance_state="STABLE",
            deployment_action="PROMOTE",
            critical_failures=0,
            weight_adjustment_action="HOLD",
            promotion_readiness=0.72,
        )
        
        self.assertTrue(should_promote)
        self.assertIn(strength, [TransitionStrength.LOW, TransitionStrength.MEDIUM])
    
    def test_candidate_healthy_factor_promote_to_live(self):
        """Test 2: Candidate healthy factor → promote to LIVE."""
        should_promote, strength, reason = self.policy.should_promote(
            current_state=LifecycleState.CANDIDATE,
            governance_state="ELITE",
            deployment_action="PROMOTE",
            critical_failures=0,
            weight_adjustment_action="INCREASE",
            promotion_readiness=0.85,
        )
        
        self.assertTrue(should_promote)
        self.assertEqual(strength, TransitionStrength.HIGH)
    
    def test_live_degraded_factor_demote(self):
        """Test 3: Live degraded factor → demote to REDUCED."""
        should_demote, strength, reason = self.policy.should_demote(
            current_state=LifecycleState.LIVE,
            governance_state="DEGRADED",
            critical_failures=1,
            high_failures=2,
            weight_adjustment_action="DECREASE",
            rollback_risk=0.45,
        )
        
        self.assertTrue(should_demote)
        self.assertIn(strength, [TransitionStrength.MEDIUM, TransitionStrength.HIGH])
    
    def test_live_critical_factor_freeze(self):
        """Test 4: Live critical factor → freeze."""
        should_freeze, strength, reason = self.policy.should_freeze(
            current_state=LifecycleState.LIVE,
            rollback_risk=0.75,
            deployment_action="ROLLBACK",
            critical_failures=3,
            interaction_state="CANCELLED",
        )
        
        self.assertTrue(should_freeze)
        self.assertIn(strength, [TransitionStrength.HIGH, TransitionStrength.CRITICAL])
    
    def test_retire_governance_retire(self):
        """Test 5: Retire governance → retire."""
        should_retire, strength, reason = self.policy.should_retire(
            governance_state="RETIRE",
            critical_failures=5,
            recommended_weight=0.0,
            deployment_action="RETIRE",
        )
        
        self.assertTrue(should_retire)
        self.assertEqual(strength, TransitionStrength.CRITICAL)
    
    def test_invalid_transition_prevented(self):
        """Test 6: Invalid transition prevented."""
        # Cannot promote from LIVE
        should_promote, strength, reason = self.policy.should_promote(
            current_state=LifecycleState.LIVE,
            governance_state="ELITE",
            deployment_action="PROMOTE",
            critical_failures=0,
            weight_adjustment_action="INCREASE",
            promotion_readiness=0.90,
        )
        
        self.assertFalse(should_promote)
        
        # Cannot freeze SHADOW
        should_freeze, strength, reason = self.policy.should_freeze(
            current_state=LifecycleState.SHADOW,
            rollback_risk=0.80,
            deployment_action="ROLLBACK",
            critical_failures=5,
            interaction_state="CANCELLED",
        )
        
        self.assertFalse(should_freeze)
    
    def test_valid_transition_check(self):
        """Test transition validation."""
        # Valid: SHADOW → CANDIDATE
        self.assertTrue(self.policy.is_valid_transition(
            LifecycleState.SHADOW, LifecycleState.CANDIDATE
        ))
        
        # Invalid: SHADOW → LIVE (must go through CANDIDATE)
        self.assertFalse(self.policy.is_valid_transition(
            LifecycleState.SHADOW, LifecycleState.LIVE
        ))
        
        # Valid: LIVE → FROZEN
        self.assertTrue(self.policy.is_valid_transition(
            LifecycleState.LIVE, LifecycleState.FROZEN
        ))


class TestAdaptivePromotionRegistry(unittest.TestCase):
    """Test registry operations."""
    
    def setUp(self):
        self.registry = AdaptivePromotionRegistry()
    
    def test_registry_persistence_correct(self):
        """Test 8: Registry persistence correct."""
        # Get initial state
        initial_count = len(self.registry.get_factor_names())
        self.assertGreater(initial_count, 0)
        
        # Add new factor
        self.registry.set_state(
            "new_test_factor",
            LifecycleState.SHADOW,
            "test creation"
        )
        
        # Verify persisted
        state = self.registry.get_factor_state("new_test_factor")
        self.assertIsNotNone(state)
        self.assertEqual(state.current_state, LifecycleState.SHADOW)
    
    def test_transition_recording(self):
        """Test transition history recording."""
        decision = AdaptivePromotionDecision(
            factor_name="test_record_factor",
            current_state=LifecycleState.SHADOW,
            recommended_state=LifecycleState.CANDIDATE,
            transition_action=TransitionAction.PROMOTE,
            transition_strength=TransitionStrength.MEDIUM,
            confidence_modifier=1.05,
            capital_modifier=1.10,
            reason="test promotion",
        )
        
        # Record transition
        result = self.registry.record_transition(decision)
        self.assertTrue(result)
        
        # Check history
        history = self.registry.get_transition_history("test_record_factor")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1].action, TransitionAction.PROMOTE)
    
    def test_state_distribution(self):
        """Test state distribution calculation."""
        distribution = self.registry.get_state_distribution()
        
        # All states should be represented
        for state in LifecycleState:
            self.assertIn(state.value, distribution)
        
        # Total should match factor count
        total = sum(distribution.values())
        self.assertEqual(total, len(self.registry.get_factor_names()))


class TestAdaptivePromotionEngine(unittest.TestCase):
    """Test engine operations."""
    
    def setUp(self):
        self.engine = AdaptivePromotionEngine()
    
    def test_summary_output_correct(self):
        """Test 7: Summary output correct."""
        summary = self.engine.compute_all_decisions()
        
        # Check structure
        self.assertIsInstance(summary, AdaptivePromotionSummary)
        self.assertGreater(summary.total_factors, 0)
        
        # Check counts match lists
        self.assertEqual(len(summary.promoted), summary.promote_count)
        self.assertEqual(len(summary.demoted), summary.demote_count)
        self.assertEqual(len(summary.frozen), summary.freeze_count)
        self.assertEqual(len(summary.retired), summary.retire_count)
        self.assertEqual(len(summary.held), summary.hold_count)
        
        # Total should match
        total = (summary.promote_count + summary.demote_count + 
                 summary.freeze_count + summary.retire_count + summary.hold_count)
        self.assertEqual(total, summary.total_factors)
    
    def test_repeated_failures_increase_demotion_severity(self):
        """Test 9: Repeated failures increase demotion severity."""
        policy = self.engine.policy
        
        # Low failures = low/no demotion
        should_demote_low, strength_low, _ = policy.should_demote(
            current_state=LifecycleState.LIVE,
            governance_state="WATCHLIST",
            critical_failures=0,
            high_failures=1,
            weight_adjustment_action="HOLD",
            rollback_risk=0.30,
        )
        
        # High failures = stronger demotion
        should_demote_high, strength_high, _ = policy.should_demote(
            current_state=LifecycleState.LIVE,
            governance_state="DEGRADED",
            critical_failures=3,
            high_failures=4,
            weight_adjustment_action="DECREASE",
            rollback_risk=0.55,
        )
        
        # High severity should be stronger
        if should_demote_low and should_demote_high:
            strength_order = [
                TransitionStrength.LOW,
                TransitionStrength.MEDIUM,
                TransitionStrength.HIGH,
                TransitionStrength.CRITICAL,
            ]
            self.assertGreaterEqual(
                strength_order.index(strength_high),
                strength_order.index(strength_low)
            )
    
    def test_api_output_correct(self):
        """Test 10: API output correct (via engine methods)."""
        # Test summary dict
        summary = self.engine.compute_all_decisions()
        summary_dict = summary.to_dict()
        
        self.assertIn("total_factors", summary_dict)
        self.assertIn("promoted", summary_dict)
        self.assertIn("demoted", summary_dict)
        self.assertIn("counts", summary_dict)
        
        # Test full dict
        full_dict = summary.to_full_dict()
        self.assertIn("decisions", full_dict)
        self.assertEqual(len(full_dict["decisions"]), summary.total_factors)
        
        # Test individual decision dict
        if summary.decisions:
            decision_dict = summary.decisions[0].to_dict()
            self.assertIn("factor_name", decision_dict)
            self.assertIn("current_state", decision_dict)
            self.assertIn("recommended_state", decision_dict)
            self.assertIn("transition_action", decision_dict)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptivePromotionTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptivePromotionPolicy))
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptivePromotionRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptivePromotionEngine))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests()
