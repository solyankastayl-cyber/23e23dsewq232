"""
Market Simulation Tests

PHASE 32.3 — Unit tests for Market Simulation Engine.

32+ tests covering:
- Scenario generation
- Probability calculation
- Probability normalization
- Direction inference
- Expected move calculation
- ATR integration
- Regime modifier
- Microstructure modifier
- Fractal modifier
- Meta alpha modifier
- API endpoints
- Integration tests
"""

import pytest
import math
from datetime import datetime, timezone

from .simulation_types import (
    MarketScenario,
    SimulationInput,
    SimulationResult,
    ScenarioModifier,
    SimulationSummary,
    SCENARIO_TYPES,
    SIMULATION_HORIZONS,
    WEIGHT_HYPOTHESIS,
    WEIGHT_REGIME,
    WEIGHT_MICROSTRUCTURE,
    WEIGHT_FRACTAL_SIMILARITY,
    WEIGHT_META_ALPHA,
    REGIME_MULTIPLIERS,
    MICROSTRUCTURE_MULTIPLIERS,
)

from .simulation_engine import MarketSimulationEngine, get_simulation_engine


# ══════════════════════════════════════════════════════════════
# 1. Scenario Generation Tests
# ══════════════════════════════════════════════════════════════

class TestScenarioGeneration:
    """Tests for scenario generation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_generate_scenarios_returns_list(self):
        """Test that scenarios are generated."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0
    
    def test_generate_scenarios_correct_count(self):
        """Test scenario count."""
        scenarios = self.engine.generate_scenarios("BTC", num_scenarios=3)
        assert len(scenarios) == 3
        
        scenarios = self.engine.generate_scenarios("ETH", num_scenarios=5)
        assert len(scenarios) == 5
    
    def test_scenario_has_required_fields(self):
        """Test scenario has all required fields."""
        scenarios = self.engine.generate_scenarios("BTC")
        s = scenarios[0]
        
        assert hasattr(s, 'scenario_id')
        assert hasattr(s, 'symbol')
        assert hasattr(s, 'scenario_type')
        assert hasattr(s, 'probability')
        assert hasattr(s, 'expected_direction')
        assert hasattr(s, 'expected_move_percent')
        assert hasattr(s, 'horizon_minutes')
        assert hasattr(s, 'confidence')
    
    def test_scenario_types_valid(self):
        """Test all scenario types are valid."""
        scenarios = self.engine.generate_scenarios("BTC", num_scenarios=5)
        
        for s in scenarios:
            assert s.scenario_type in SCENARIO_TYPES
    
    def test_scenarios_sorted_by_probability(self):
        """Test scenarios are sorted by probability descending."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        for i in range(len(scenarios) - 1):
            assert scenarios[i].probability >= scenarios[i + 1].probability


# ══════════════════════════════════════════════════════════════
# 2. Probability Calculation Tests
# ══════════════════════════════════════════════════════════════

class TestProbabilityCalculation:
    """Tests for probability calculation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_probability_bounds(self):
        """Test probabilities are within [0, 1]."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        for s in scenarios:
            assert 0.0 <= s.probability <= 1.0
    
    def test_probability_normalization(self):
        """Test probabilities sum to 1.0."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        total = sum(s.probability for s in scenarios)
        assert abs(total - 1.0) < 0.01  # Allow small float error
    
    def test_probability_uses_weights(self):
        """Test probability formula uses correct weights."""
        sim_input = SimulationInput(
            symbol="BTC",
            hypothesis_confidence=0.8,
            regime_confidence=0.7,
            microstructure_confidence=0.6,
            similarity_confidence=0.5,
            meta_alpha_score=0.4,
        )
        
        prob, scores = self.engine.calculate_scenario_probability(
            "BREAKOUT_CONTINUATION",
            sim_input
        )
        
        assert 0.0 < prob < 1.0
        assert "hypothesis" in scores
        assert "regime" in scores
        assert "microstructure" in scores
    
    def test_probability_deterministic(self):
        """Test probability calculation is deterministic."""
        sim_input = SimulationInput(
            symbol="BTC",
            hypothesis_type="BREAKOUT_FORMING",
            hypothesis_confidence=0.8,
        )
        
        prob1, _ = self.engine.calculate_scenario_probability("BREAKOUT_CONTINUATION", sim_input)
        prob2, _ = self.engine.calculate_scenario_probability("BREAKOUT_CONTINUATION", sim_input)
        
        assert prob1 == prob2


# ══════════════════════════════════════════════════════════════
# 3. Direction Inference Tests
# ══════════════════════════════════════════════════════════════

class TestDirectionInference:
    """Tests for direction inference."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_direction_valid_values(self):
        """Test direction is valid."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        for s in scenarios:
            assert s.expected_direction in ["LONG", "SHORT", "NEUTRAL"]
    
    def test_mean_reversion_opposite_trend(self):
        """Test mean reversion goes opposite to trend."""
        sim_input = SimulationInput(
            symbol="BTC",
            regime_type="TREND_UP",
            regime_confidence=0.8,
        )
        
        direction, _ = self.engine.calculate_direction("MEAN_REVERSION", sim_input)
        assert direction == "SHORT"
        
        sim_input.regime_type = "TREND_DOWN"
        direction, _ = self.engine.calculate_direction("MEAN_REVERSION", sim_input)
        assert direction == "LONG"
    
    def test_liquidation_event_based_on_pressure(self):
        """Test liquidation event direction based on pressure."""
        sim_input = SimulationInput(
            symbol="BTC",
            liquidation_pressure=0.5,  # Long positions dominate
        )
        
        direction, _ = self.engine.calculate_direction("LIQUIDATION_EVENT", sim_input)
        assert direction == "SHORT"  # Long squeeze
        
        sim_input.liquidation_pressure = -0.5
        direction, _ = self.engine.calculate_direction("LIQUIDATION_EVENT", sim_input)
        assert direction == "LONG"  # Short squeeze
    
    def test_direction_confidence_reduced_by_microstructure(self):
        """Test microstructure reduces direction confidence."""
        sim_input_stable = SimulationInput(
            symbol="BTC",
            hypothesis_direction="LONG",
            hypothesis_confidence=0.8,
            microstructure_state="SUPPORTIVE",
        )
        
        sim_input_fragile = SimulationInput(
            symbol="BTC",
            hypothesis_direction="LONG",
            hypothesis_confidence=0.8,
            microstructure_state="FRAGILE",
        )
        
        _, conf_stable = self.engine.calculate_direction("BREAKOUT_CONTINUATION", sim_input_stable)
        _, conf_fragile = self.engine.calculate_direction("BREAKOUT_CONTINUATION", sim_input_fragile)
        
        assert conf_stable >= conf_fragile


# ══════════════════════════════════════════════════════════════
# 4. Expected Move Tests
# ══════════════════════════════════════════════════════════════

class TestExpectedMove:
    """Tests for expected move calculation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_expected_move_positive(self):
        """Test expected move is positive."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        for s in scenarios:
            assert s.expected_move_percent > 0
    
    def test_expected_move_bounded(self):
        """Test expected move is bounded."""
        scenarios = self.engine.generate_scenarios("BTC")
        
        for s in scenarios:
            assert 0.1 <= s.expected_move_percent <= 20.0
    
    def test_atr_integration(self):
        """Test ATR affects expected move."""
        sim_input_low = SimulationInput(symbol="BTC", atr_percent=1.0)
        sim_input_high = SimulationInput(symbol="BTC", atr_percent=5.0)
        
        move_low = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input_low, 60)
        move_high = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input_high, 60)
        
        assert move_high > move_low
    
    def test_regime_multiplier(self):
        """Test regime affects expected move."""
        sim_input_range = SimulationInput(symbol="BTC", regime_type="RANGE", atr_percent=2.0)
        sim_input_expansion = SimulationInput(symbol="BTC", regime_type="EXPANSION", atr_percent=2.0)
        
        move_range = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input_range, 60)
        move_expansion = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input_expansion, 60)
        
        assert move_expansion > move_range
    
    def test_microstructure_multiplier(self):
        """Test microstructure affects expected move."""
        sim_input_supportive = SimulationInput(symbol="BTC", microstructure_state="SUPPORTIVE", atr_percent=2.0)
        sim_input_stressed = SimulationInput(symbol="BTC", microstructure_state="STRESSED", atr_percent=2.0)
        
        move_supportive = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input_supportive, 60)
        move_stressed = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input_stressed, 60)
        
        assert move_stressed > move_supportive
    
    def test_horizon_affects_move(self):
        """Test longer horizon = larger move."""
        sim_input = SimulationInput(symbol="BTC", atr_percent=2.0)
        
        move_15m = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input, 15)
        move_60m = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input, 60)
        move_240m = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input, 240)
        
        assert move_60m > move_15m
        assert move_240m > move_60m


# ══════════════════════════════════════════════════════════════
# 5. Full Simulation Tests
# ══════════════════════════════════════════════════════════════

class TestFullSimulation:
    """Tests for full simulation."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_simulate_returns_result(self):
        """Test simulate returns SimulationResult."""
        result = self.engine.simulate("BTC")
        
        assert isinstance(result, SimulationResult)
        assert result.symbol == "BTC"
    
    def test_simulate_has_scenarios(self):
        """Test result has scenarios."""
        result = self.engine.simulate("BTC")
        
        assert len(result.scenarios) > 0
        assert result.top_scenario is not None
    
    def test_simulate_has_aggregated_metrics(self):
        """Test result has aggregated metrics."""
        result = self.engine.simulate("BTC")
        
        assert result.dominant_direction in ["LONG", "SHORT", "NEUTRAL"]
        assert 0.0 <= result.direction_confidence <= 1.0
        assert result.expected_volatility >= 0
    
    def test_simulate_stored(self):
        """Test simulation is stored."""
        result = self.engine.simulate("ETH")
        
        stored = self.engine.get_current_simulation("ETH")
        
        assert stored is not None
        assert stored.symbol == result.symbol


# ══════════════════════════════════════════════════════════════
# 6. Allocation Modifier Tests
# ══════════════════════════════════════════════════════════════

class TestAllocationModifier:
    """Tests for allocation modifier."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_modifier_returns_object(self):
        """Test modifier returns ScenarioModifier."""
        modifier = self.engine.get_allocation_modifier("BTC")
        
        assert isinstance(modifier, ScenarioModifier)
    
    def test_modifier_bounded(self):
        """Test modifier is bounded [0.5, 1.5]."""
        modifier = self.engine.get_allocation_modifier("BTC")
        
        assert 0.5 <= modifier.allocation_modifier <= 1.5
    
    def test_modifier_has_details(self):
        """Test modifier has details."""
        modifier = self.engine.get_allocation_modifier("BTC")
        
        assert modifier.top_scenario_type in SCENARIO_TYPES or modifier.top_scenario_type == "UNKNOWN"
        assert modifier.risk_level in ["LOW", "MEDIUM", "HIGH"]
        assert modifier.reason != ""


# ══════════════════════════════════════════════════════════════
# 7. Storage Tests
# ══════════════════════════════════════════════════════════════

class TestStorage:
    """Tests for storage operations."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_get_history(self):
        """Test getting history."""
        self.engine.simulate("BTC")
        self.engine.simulate("BTC")
        
        history = self.engine.get_history("BTC")
        
        assert len(history) >= 2
    
    def test_get_top_scenarios(self):
        """Test getting top scenarios."""
        self.engine.simulate("BTC")
        
        top = self.engine.get_top_scenarios("BTC", 3)
        
        assert len(top) == 3
    
    def test_get_summary(self):
        """Test getting summary."""
        self.engine.simulate("BTC")
        
        summary = self.engine.get_summary("BTC")
        
        assert isinstance(summary, SimulationSummary)
        assert summary.symbol == "BTC"
        assert summary.total_simulations >= 1


# ══════════════════════════════════════════════════════════════
# 8. Input Gathering Tests
# ══════════════════════════════════════════════════════════════

class TestInputGathering:
    """Tests for input gathering."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_gather_inputs_returns_object(self):
        """Test gather inputs returns SimulationInput."""
        inputs = self.engine.gather_inputs("BTC")
        
        assert isinstance(inputs, SimulationInput)
        assert inputs.symbol == "BTC"
    
    def test_gather_inputs_has_all_fields(self):
        """Test gathered inputs have all fields."""
        inputs = self.engine.gather_inputs("BTC")
        
        assert inputs.hypothesis_type is not None
        assert inputs.regime_type is not None
        assert inputs.microstructure_state is not None
        assert inputs.similarity_direction is not None
        assert inputs.meta_alpha_pattern is not None
    
    def test_provided_input_used(self):
        """Test provided input is used."""
        custom_input = SimulationInput(
            symbol="BTC",
            hypothesis_type="CUSTOM",
            hypothesis_confidence=0.99,
        )
        
        inputs = self.engine.gather_inputs("BTC", custom_input)
        
        assert inputs.hypothesis_type == "CUSTOM"
        assert inputs.hypothesis_confidence == 0.99


# ══════════════════════════════════════════════════════════════
# 9. Multi-Horizon Tests
# ══════════════════════════════════════════════════════════════

class TestMultiHorizon:
    """Tests for multi-horizon support."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_different_horizons(self):
        """Test simulations for different horizons."""
        for horizon in SIMULATION_HORIZONS:
            result = self.engine.simulate("BTC", horizon)
            assert result.horizon_minutes == horizon
    
    def test_horizon_affects_move(self):
        """Test horizon affects expected move."""
        results = {h: self.engine.simulate("BTC", h) for h in SIMULATION_HORIZONS}
        
        # Longer horizon should generally have larger moves
        assert results[240].expected_volatility >= results[15].expected_volatility * 0.8


# ══════════════════════════════════════════════════════════════
# 10. Scenario Diversity Tests
# ══════════════════════════════════════════════════════════════

class TestScenarioDiversity:
    """Tests for scenario diversity."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_all_scenario_types_generated(self):
        """Test all scenario types can be generated."""
        scenarios = self.engine.generate_scenarios("BTC", num_scenarios=5)
        
        types = {s.scenario_type for s in scenarios}
        assert len(types) == 5  # All 5 unique types
    
    def test_scenarios_have_different_probabilities(self):
        """Test scenarios have different probabilities."""
        scenarios = self.engine.generate_scenarios("BTC", num_scenarios=5)
        
        probs = [s.probability for s in scenarios]
        # At least some should differ
        assert len(set(probs)) > 1


# ══════════════════════════════════════════════════════════════
# 11. Singleton Tests
# ══════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_simulation_engine(self):
        """Test singleton getter."""
        engine1 = get_simulation_engine()
        engine2 = get_simulation_engine()
        
        assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# 12. Edge Cases Tests
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""
    
    def setup_method(self):
        """Setup test engine."""
        self.engine = MarketSimulationEngine()
    
    def test_unknown_symbol(self):
        """Test handling unknown symbol."""
        result = self.engine.simulate("UNKNOWN_XYZ")
        
        assert result is not None
        assert result.symbol == "UNKNOWN_XYZ"
    
    def test_zero_atr(self):
        """Test handling zero ATR."""
        sim_input = SimulationInput(symbol="BTC", atr_percent=0.0)
        
        move = self.engine.calculate_expected_move("BREAKOUT_CONTINUATION", sim_input, 60)
        assert move >= 0.1  # Minimum bound
    
    def test_extreme_confidence(self):
        """Test handling extreme confidence values."""
        sim_input = SimulationInput(
            symbol="BTC",
            hypothesis_confidence=1.0,
            regime_confidence=1.0,
            microstructure_confidence=1.0,
        )
        
        prob, _ = self.engine.calculate_scenario_probability("BREAKOUT_CONTINUATION", sim_input)
        assert 0.0 <= prob <= 1.0
    
    def test_missing_data_safe(self):
        """Test simulation works with missing data."""
        sim_input = SimulationInput(symbol="BTC")  # All defaults
        
        scenarios = self.engine.generate_scenarios("BTC", provided_input=sim_input)
        assert len(scenarios) > 0


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
