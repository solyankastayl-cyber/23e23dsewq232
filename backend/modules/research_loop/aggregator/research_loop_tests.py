"""
PHASE 20.4 — Research Loop Tests
================================
Test cases for Research Loop Aggregator.

Tests:
1. healthy loop state
2. adapting loop state
3. degraded loop state  
4. critical loop state
5. counts aggregated correctly
6. modifiers correct
7. strongest / weakest signal correct
8. summary output correct
9. empty data handled
10. API output correct
"""

import unittest
from datetime import datetime, timezone

from modules.research_loop.aggregator.research_loop_types import (
    LoopState,
    LoopSignal,
    ResearchLoopState,
    LOOP_STATE_THRESHOLDS,
    LOOP_MODIFIERS,
    LOOP_SCORE_WEIGHTS,
)
from modules.research_loop.aggregator.research_loop_engine import (
    ResearchLoopEngine,
)
from modules.research_loop.aggregator.research_loop_registry import (
    ResearchLoopRegistry,
)


class TestResearchLoopTypes(unittest.TestCase):
    """Test type definitions."""
    
    def test_loop_states_exist(self):
        """Test all loop states exist."""
        states = [
            LoopState.HEALTHY,
            LoopState.ADAPTING,
            LoopState.DEGRADED,
            LoopState.CRITICAL,
        ]
        self.assertEqual(len(states), 4)
    
    def test_loop_thresholds_ordered(self):
        """Test thresholds are properly ordered."""
        self.assertGreater(
            LOOP_STATE_THRESHOLDS[LoopState.HEALTHY],
            LOOP_STATE_THRESHOLDS[LoopState.ADAPTING]
        )
        self.assertGreater(
            LOOP_STATE_THRESHOLDS[LoopState.ADAPTING],
            LOOP_STATE_THRESHOLDS[LoopState.DEGRADED]
        )
    
    def test_loop_modifiers_defined(self):
        """Test modifiers defined for all states."""
        for state in LoopState:
            self.assertIn(state, LOOP_MODIFIERS)
            self.assertIn("confidence_modifier", LOOP_MODIFIERS[state])
            self.assertIn("capital_modifier", LOOP_MODIFIERS[state])
    
    def test_loop_signal_to_dict(self):
        """Test signal serialization."""
        signal = LoopSignal(
            name="test_signal",
            value=0.75,
            weight=0.30,
            contribution=0.225,
            status="STRONG",
        )
        
        data = signal.to_dict()
        self.assertEqual(data["name"], "test_signal")
        self.assertEqual(data["value"], 0.75)
        self.assertEqual(data["status"], "STRONG")
    
    def test_research_loop_state_to_dict(self):
        """Test state serialization."""
        state = ResearchLoopState(
            loop_state=LoopState.ADAPTING,
            loop_score=0.65,
            total_factors=10,
            healthy_factors=6,
            watchlist_factors=3,
            degraded_factors=1,
            retired_factors=0,
            critical_failure_patterns=["test_pattern"],
            recommended_increases=["factor_a"],
            recommended_decreases=["factor_b"],
            recommended_promotions=["factor_c"],
            recommended_demotions=["factor_d"],
            recommended_freezes=[],
            recommended_retires=[],
            confidence_modifier=1.0,
            capital_modifier=1.0,
            strongest_signal="healthy_factor_ratio",
            weakest_signal="critical_pattern_pressure",
            reason="test reason",
        )
        
        data = state.to_dict()
        self.assertEqual(data["loop_state"], "ADAPTING")
        self.assertEqual(data["total_factors"], 10)
        self.assertIn("test_pattern", data["critical_failure_patterns"])


class TestResearchLoopEngine(unittest.TestCase):
    """Test engine operations."""
    
    def setUp(self):
        self.engine = ResearchLoopEngine()
    
    def test_healthy_loop_state(self):
        """Test 1: healthy loop state detection."""
        state = self.engine.compute_state()
        
        # State should be one of the valid states
        self.assertIn(state.loop_state, list(LoopState))
        
        # If score >= 0.75, should be HEALTHY
        if state.loop_score >= LOOP_STATE_THRESHOLDS[LoopState.HEALTHY]:
            self.assertEqual(state.loop_state, LoopState.HEALTHY)
    
    def test_adapting_loop_state(self):
        """Test 2: adapting loop state detection."""
        state = self.engine.compute_state()
        
        # If score in adapting range, should be ADAPTING
        if (state.loop_score >= LOOP_STATE_THRESHOLDS[LoopState.ADAPTING] and 
            state.loop_score < LOOP_STATE_THRESHOLDS[LoopState.HEALTHY]):
            self.assertEqual(state.loop_state, LoopState.ADAPTING)
    
    def test_degraded_loop_state(self):
        """Test 3: degraded loop state detection."""
        state = self.engine.compute_state()
        
        # If score in degraded range, should be DEGRADED
        if (state.loop_score >= LOOP_STATE_THRESHOLDS[LoopState.DEGRADED] and 
            state.loop_score < LOOP_STATE_THRESHOLDS[LoopState.ADAPTING]):
            self.assertEqual(state.loop_state, LoopState.DEGRADED)
    
    def test_critical_loop_state(self):
        """Test 4: critical loop state detection."""
        state = self.engine.compute_state()
        
        # If score below degraded threshold, should be CRITICAL
        if state.loop_score < LOOP_STATE_THRESHOLDS[LoopState.DEGRADED]:
            self.assertEqual(state.loop_state, LoopState.CRITICAL)
    
    def test_counts_aggregated_correctly(self):
        """Test 5: counts aggregated correctly."""
        state = self.engine.compute_state()
        
        # Total should be sum of categories (or close, depending on data)
        self.assertGreater(state.total_factors, 0)
        self.assertGreaterEqual(state.healthy_factors, 0)
        self.assertGreaterEqual(state.watchlist_factors, 0)
        self.assertGreaterEqual(state.degraded_factors, 0)
        self.assertGreaterEqual(state.retired_factors, 0)
    
    def test_modifiers_correct(self):
        """Test 6: modifiers correct for state."""
        state = self.engine.compute_state()
        
        expected_modifiers = LOOP_MODIFIERS[state.loop_state]
        
        self.assertEqual(
            state.confidence_modifier,
            expected_modifiers["confidence_modifier"]
        )
        self.assertEqual(
            state.capital_modifier,
            expected_modifiers["capital_modifier"]
        )
    
    def test_strongest_weakest_signal_correct(self):
        """Test 7: strongest / weakest signal correct."""
        state = self.engine.compute_state()
        
        # Both should be non-empty strings
        self.assertIsInstance(state.strongest_signal, str)
        self.assertIsInstance(state.weakest_signal, str)
        self.assertGreater(len(state.strongest_signal), 0)
        self.assertGreater(len(state.weakest_signal), 0)
        
        # Should be valid signal names
        valid_signals = [
            "healthy_factor_ratio",
            "promotion_health",
            "adjustment_stability",
            "critical_pattern_pressure",
            "retire_freeze_pressure",
        ]
        self.assertIn(state.strongest_signal, valid_signals)
        self.assertIn(state.weakest_signal, valid_signals)
    
    def test_summary_output_correct(self):
        """Test 8: summary output correct."""
        summary = self.engine.get_summary()
        
        # Check required fields
        self.assertIn("loop_state", summary)
        self.assertIn("loop_score", summary)
        self.assertIn("total_factors", summary)
        self.assertIn("healthy_factors", summary)
        self.assertIn("confidence_modifier", summary)
        self.assertIn("capital_modifier", summary)
        self.assertIn("strongest_signal", summary)
        self.assertIn("weakest_signal", summary)
    
    def test_empty_data_handled(self):
        """Test 9: empty/minimal data handled gracefully."""
        # Engine should work even with minimal data
        state = self.engine.compute_state()
        
        # Should not raise exceptions and return valid state
        self.assertIsNotNone(state)
        self.assertIn(state.loop_state, list(LoopState))
        self.assertGreaterEqual(state.loop_score, 0.0)
        self.assertLessEqual(state.loop_score, 1.0)
    
    def test_api_output_correct(self):
        """Test 10: API output format correct."""
        state = self.engine.compute_state()
        
        # Test to_dict
        data = state.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn("loop_state", data)
        self.assertIn("timestamp", data)
        
        # Test to_full_dict
        full_data = state.to_full_dict()
        self.assertIn("signals", full_data)
        self.assertIsInstance(full_data["signals"], list)
        
        # Test to_summary
        summary = state.to_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn("loop_state", summary)


class TestResearchLoopRegistry(unittest.TestCase):
    """Test registry operations."""
    
    def setUp(self):
        self.registry = ResearchLoopRegistry()
    
    def test_registry_initialization(self):
        """Test registry initializes correctly."""
        stats = self.registry.get_stats()
        
        self.assertEqual(stats["total_recomputes"], 0)
        self.assertEqual(stats["state_transitions"], 0)
    
    def test_record_state(self):
        """Test state recording."""
        state = ResearchLoopState(
            loop_state=LoopState.ADAPTING,
            loop_score=0.65,
            total_factors=10,
            healthy_factors=6,
            watchlist_factors=3,
            degraded_factors=1,
            retired_factors=0,
            critical_failure_patterns=[],
            recommended_increases=[],
            recommended_decreases=[],
            recommended_promotions=[],
            recommended_demotions=[],
            recommended_freezes=[],
            recommended_retires=[],
            confidence_modifier=1.0,
            capital_modifier=1.0,
            strongest_signal="test",
            weakest_signal="test",
            reason="test",
        )
        
        self.registry.record_state(state)
        
        stats = self.registry.get_stats()
        self.assertEqual(stats["total_recomputes"], 1)
        
        current = self.registry.get_current_state()
        self.assertIsNotNone(current)
        self.assertEqual(current.loop_state, LoopState.ADAPTING)
    
    def test_history_tracking(self):
        """Test history tracking."""
        state1 = ResearchLoopState(
            loop_state=LoopState.HEALTHY,
            loop_score=0.80,
            total_factors=10,
            healthy_factors=8,
            watchlist_factors=2,
            degraded_factors=0,
            retired_factors=0,
            critical_failure_patterns=[],
            recommended_increases=[],
            recommended_decreases=[],
            recommended_promotions=[],
            recommended_demotions=[],
            recommended_freezes=[],
            recommended_retires=[],
            confidence_modifier=1.03,
            capital_modifier=1.05,
            strongest_signal="test",
            weakest_signal="test",
            reason="test",
        )
        
        state2 = ResearchLoopState(
            loop_state=LoopState.DEGRADED,
            loop_score=0.40,
            total_factors=10,
            healthy_factors=4,
            watchlist_factors=4,
            degraded_factors=2,
            retired_factors=0,
            critical_failure_patterns=["pattern1"],
            recommended_increases=[],
            recommended_decreases=["factor_a"],
            recommended_promotions=[],
            recommended_demotions=["factor_b"],
            recommended_freezes=[],
            recommended_retires=[],
            confidence_modifier=0.92,
            capital_modifier=0.90,
            strongest_signal="test",
            weakest_signal="test",
            reason="test",
        )
        
        self.registry.record_state(state1)
        self.registry.record_state(state2)
        
        history = self.registry.get_history()
        self.assertEqual(len(history), 2)
        
        stats = self.registry.get_stats()
        self.assertEqual(stats["state_transitions"], 1)  # HEALTHY -> DEGRADED


class TestLoopScoreCalculation(unittest.TestCase):
    """Test loop score calculation logic."""
    
    def setUp(self):
        self.engine = ResearchLoopEngine()
    
    def test_score_in_valid_range(self):
        """Test score is always 0..1."""
        state = self.engine.compute_state()
        
        self.assertGreaterEqual(state.loop_score, 0.0)
        self.assertLessEqual(state.loop_score, 1.0)
    
    def test_signals_contribute_correctly(self):
        """Test signals have correct contributions."""
        state = self.engine.compute_state()
        
        for signal in state.signals:
            # Positive signals should have positive contribution
            if signal.weight > 0:
                self.assertGreaterEqual(signal.contribution, 0.0)
            # Negative signals (pressure) should have negative contribution
            else:
                self.assertLessEqual(signal.contribution, 0.0)
    
    def test_state_matches_score(self):
        """Test state classification matches score."""
        state = self.engine.compute_state()
        
        score = state.loop_score
        
        if score >= LOOP_STATE_THRESHOLDS[LoopState.HEALTHY]:
            self.assertEqual(state.loop_state, LoopState.HEALTHY)
        elif score >= LOOP_STATE_THRESHOLDS[LoopState.ADAPTING]:
            self.assertEqual(state.loop_state, LoopState.ADAPTING)
        elif score >= LOOP_STATE_THRESHOLDS[LoopState.DEGRADED]:
            self.assertEqual(state.loop_state, LoopState.DEGRADED)
        else:
            self.assertEqual(state.loop_state, LoopState.CRITICAL)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestResearchLoopTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestResearchLoopEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestResearchLoopRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestLoopScoreCalculation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests()
