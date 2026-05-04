"""
PHASE 16.6 — Interaction Aggregator API Tests
==============================================
Tests for the Interaction Aggregator API endpoints.

Endpoints:
- GET /api/v1/alpha-interaction/aggregate/{symbol} - Full aggregate analysis
- GET /api/v1/alpha-interaction/aggregate/summary/{symbol} - Compact summary
- GET /api/v1/alpha-interaction/aggregate/modifiers/{symbol} - Modifiers for Position Sizing/Execution Mode
- GET /api/v1/alpha-interaction/aggregate/snapshot/{symbol} - Snapshot for Trading Product
- GET /api/v1/alpha-interaction/health - Health check including aggregator info

Key Test Cases:
1. All API endpoints return expected structure
2. State thresholds work correctly
3. Cancellation override (cancellation_strength > 0.7 → CRITICAL)
4. Modifiers are correct per state
5. Force ranking is accurate
6. Integration with PositionSizingEngine and ExecutionModeEngine
"""

import pytest
import requests
import os
import sys
from pathlib import Path

# Add backend to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tech-analysis-core-1.preview.emergentagent.com').rstrip('/')


class TestAggregatorHealthEndpoint:
    """Test health endpoint includes aggregator info."""
    
    def test_health_shows_aggregator_capability(self):
        """Health endpoint shows interaction_aggregation capability."""
        response = requests.get(f"{BASE_URL}/api/v1/alpha-interaction/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["phase"] == "16.6"
        assert "interaction_aggregation" in data["capabilities"]
        
        # Check aggregator result is present
        assert "aggregator_result" in data
        agg_result = data["aggregator_result"]
        assert "aggregate_state" in agg_result
        assert "aggregate_score" in agg_result
        assert "strongest_force" in agg_result
        assert "execution_modifier" in agg_result
        print("✓ Health endpoint shows aggregator info correctly")


class TestAggregateFullEndpoint:
    """Test GET /api/v1/alpha-interaction/aggregate/{symbol}"""
    
    def test_aggregate_btc_returns_full_data(self):
        """Full aggregate endpoint returns all expected fields."""
        response = requests.get(f"{BASE_URL}/api/v1/alpha-interaction/aggregate/BTC")
        assert response.status_code == 200
        
        result = response.json()
        assert result["status"] == "ok"
        
        data = result["data"]
        
        # Required fields
        assert "symbol" in data
        assert data["symbol"] == "BTC"
        assert "timestamp" in data
        
        # Input strengths
        assert "reinforcement_strength" in data
        assert "conflict_strength" in data
        assert "synergy_strength" in data
        assert "cancellation_strength" in data
        
        # Output fields
        assert "interaction_score" in data
        assert "interaction_state" in data
        assert "confidence_modifier" in data
        assert "size_modifier" in data
        assert "execution_modifier" in data
        
        # Force ranking
        assert "strongest_force" in data
        assert "weakest_force" in data
        
        # Override flag
        assert "cancellation_override" in data
        assert isinstance(data["cancellation_override"], bool)
        
        # Drivers
        assert "drivers" in data
        drivers = data["drivers"]
        assert "reinforcement_contribution" in drivers
        assert "synergy_contribution" in drivers
        assert "conflict_contribution" in drivers
        assert "cancellation_contribution" in drivers
        
        print("✓ Aggregate endpoint returns complete data structure")
    
    def test_aggregate_multiple_symbols(self):
        """Test aggregate for ETH and SOL."""
        for symbol in ["ETH", "SOL"]:
            response = requests.get(f"{BASE_URL}/api/v1/alpha-interaction/aggregate/{symbol}")
            assert response.status_code == 200
            
            result = response.json()
            assert result["status"] == "ok"
            assert result["data"]["symbol"] == symbol
            
        print("✓ Aggregate works for multiple symbols")


class TestAggregateSummaryEndpoint:
    """Test GET /api/v1/alpha-interaction/aggregate/summary/{symbol}"""
    
    def test_summary_compact_structure(self):
        """Summary endpoint returns compact structure."""
        response = requests.get(f"{BASE_URL}/api/v1/alpha-interaction/aggregate/summary/BTC")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["symbol"] == "BTC"
        
        # Core fields
        assert "interaction_state" in data
        assert "interaction_score" in data
        assert "confidence_modifier" in data
        assert "size_modifier" in data
        assert "execution_modifier" in data
        
        # Force info
        assert "strongest_force" in data
        assert "weakest_force" in data
        
        # Override flag
        assert "cancellation_override" in data
        
        print("✓ Summary endpoint returns compact structure")


class TestAggregateModifiersEndpoint:
    """Test GET /api/v1/alpha-interaction/aggregate/modifiers/{symbol}"""
    
    def test_modifiers_for_integration(self):
        """Modifiers endpoint returns fields for Position Sizing / Execution Mode."""
        response = requests.get(f"{BASE_URL}/api/v1/alpha-interaction/aggregate/modifiers/BTC")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["symbol"] == "BTC"
        
        # Key integration fields
        assert "interaction_confidence_modifier" in data
        assert "interaction_size_modifier" in data
        assert "interaction_execution_modifier" in data
        assert "interaction_state" in data
        assert "interaction_score" in data
        
        # Force analysis
        assert "strongest_force" in data
        assert "weakest_force" in data
        
        # Override and raw strengths
        assert "cancellation_override" in data
        assert "reinforcement_strength" in data
        assert "conflict_strength" in data
        assert "synergy_strength" in data
        assert "cancellation_strength" in data
        
        print("✓ Modifiers endpoint returns integration-ready data")


class TestAggregateSnapshotEndpoint:
    """Test GET /api/v1/alpha-interaction/aggregate/snapshot/{symbol}"""
    
    def test_snapshot_minimal_structure(self):
        """Snapshot endpoint returns minimal structure."""
        response = requests.get(f"{BASE_URL}/api/v1/alpha-interaction/aggregate/snapshot/ETH")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["symbol"] == "ETH"
        
        # Interaction object
        assert "interaction" in data
        interaction = data["interaction"]
        
        # Snapshot should have exactly 6 fields
        assert len(interaction) == 6
        assert "state" in interaction
        assert "score" in interaction
        assert "strongest_force" in interaction
        assert "confidence_modifier" in interaction
        assert "size_modifier" in interaction
        assert "execution_modifier" in interaction
        
        print("✓ Snapshot endpoint returns minimal structure (6 fields)")


class TestStateThresholds:
    """Test interaction state thresholds via aggregate_from_inputs method."""
    
    def test_state_classification_via_unit_tests(self):
        """Verify state thresholds work correctly via direct engine testing."""
        from modules.alpha_interactions.interaction_aggregator import (
            InteractionAggregator,
            AggregateInteractionState,
            ExecutionModifier,
            STATE_THRESHOLDS,
        )
        
        aggregator = InteractionAggregator()
        
        # Test STRONG_POSITIVE (score > 0.50)
        result_sp = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=1.0,
            conflict_strength=0.0,
            synergy_strength=1.0,
            cancellation_strength=0.0,
        )
        # Score: 0.30*1.0 + 0.25*1.0 - 0 - 0 = 0.55
        assert result_sp.interaction_state == AggregateInteractionState.STRONG_POSITIVE
        assert result_sp.interaction_score > STATE_THRESHOLDS["strong_positive_min"]
        assert result_sp.confidence_modifier == 1.12
        assert result_sp.size_modifier == 1.10
        assert result_sp.execution_modifier == ExecutionModifier.BOOST
        print("✓ STRONG_POSITIVE state thresholds correct")
        
        # Test NEUTRAL (score between -0.20 and 0.20)
        result_n = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=0.0,
            conflict_strength=0.0,
            synergy_strength=0.0,
            cancellation_strength=0.0,
        )
        assert result_n.interaction_state == AggregateInteractionState.NEUTRAL
        assert result_n.interaction_score == 0.0
        assert result_n.confidence_modifier == 1.0
        assert result_n.size_modifier == 1.0
        assert result_n.execution_modifier == ExecutionModifier.NORMAL
        print("✓ NEUTRAL state thresholds correct")
        
        # Test NEGATIVE (score between -0.50 and -0.20)
        result_neg = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=0.1,
            conflict_strength=0.9,
            synergy_strength=0.05,
            cancellation_strength=0.5,
        )
        # Score: 0.30*0.1 + 0.25*0.05 - 0.25*0.9 - 0.20*0.5 = 0.03 + 0.0125 - 0.225 - 0.1 = -0.2825
        assert result_neg.interaction_state in [
            AggregateInteractionState.NEGATIVE,
            AggregateInteractionState.CRITICAL,
        ]
        assert result_neg.interaction_score < STATE_THRESHOLDS["neutral_min"]
        print("✓ NEGATIVE state thresholds correct")


class TestCancellationOverride:
    """
    CRITICAL TEST: Cancellation override forces CRITICAL state.
    
    Key Rule: When cancellation_strength > 0.7, state MUST be CRITICAL
    even with high reinforcement and synergy.
    """
    
    def test_cancellation_override_forces_critical(self):
        """
        When cancellation > 0.7, state MUST be CRITICAL.
        
        This is the key protection mechanism of the aggregator.
        """
        from modules.alpha_interactions.interaction_aggregator import (
            InteractionAggregator,
            AggregateInteractionState,
            ExecutionModifier,
            CANCELLATION_OVERRIDE_THRESHOLD,
            STATE_MODIFIERS,
        )
        
        aggregator = InteractionAggregator()
        
        # Test with HIGH reinforcement + synergy BUT cancellation > 0.7
        result = aggregator.aggregate_from_inputs(
            symbol="TEST_OVERRIDE",
            reinforcement_strength=0.95,  # Very high
            conflict_strength=0.1,         # Low
            synergy_strength=0.90,         # Very high
            cancellation_strength=0.75,    # Above threshold!
        )
        
        # CRITICAL ASSERTION: State MUST be CRITICAL
        assert result.interaction_state == AggregateInteractionState.CRITICAL, \
            f"Expected CRITICAL but got {result.interaction_state.value}"
        
        # Cancellation override flag must be True
        assert result.cancellation_override is True, \
            "Cancellation override flag should be True"
        
        # Modifiers must be most restrictive
        assert result.confidence_modifier == STATE_MODIFIERS[AggregateInteractionState.CRITICAL]["confidence_modifier"], \
            f"Expected confidence_modifier 0.70, got {result.confidence_modifier}"
        assert result.size_modifier == STATE_MODIFIERS[AggregateInteractionState.CRITICAL]["size_modifier"], \
            f"Expected size_modifier 0.65, got {result.size_modifier}"
        assert result.execution_modifier == ExecutionModifier.RESTRICT, \
            f"Expected RESTRICT, got {result.execution_modifier.value}"
        
        print("✓ CRITICAL TEST PASSED: Cancellation override forces CRITICAL state")
        print(f"  - cancellation_strength: {result.cancellation_strength} (> {CANCELLATION_OVERRIDE_THRESHOLD})")
        print(f"  - interaction_state: {result.interaction_state.value}")
        print(f"  - cancellation_override: {result.cancellation_override}")
        print(f"  - confidence_modifier: {result.confidence_modifier}")
        print(f"  - size_modifier: {result.size_modifier}")
        print(f"  - execution_modifier: {result.execution_modifier.value}")
    
    def test_no_override_below_threshold(self):
        """State should NOT be overridden when cancellation <= 0.7."""
        from modules.alpha_interactions.interaction_aggregator import (
            InteractionAggregator,
            AggregateInteractionState,
        )
        
        aggregator = InteractionAggregator()
        
        # Test with HIGH reinforcement + synergy and cancellation = 0.7 (exactly at threshold)
        result = aggregator.aggregate_from_inputs(
            symbol="TEST_NO_OVERRIDE",
            reinforcement_strength=0.95,
            conflict_strength=0.1,
            synergy_strength=0.90,
            cancellation_strength=0.70,  # Exactly at threshold (not above)
        )
        
        # Should NOT be overridden (only > 0.7 triggers override)
        assert result.cancellation_override is False, \
            "Cancellation override should be False at threshold"
        
        # State should be based on score, not overridden
        # Score: 0.30*0.95 + 0.25*0.90 - 0.25*0.1 - 0.20*0.70
        # = 0.285 + 0.225 - 0.025 - 0.14 = 0.345 → POSITIVE
        assert result.interaction_state != AggregateInteractionState.CRITICAL or result.cancellation_override, \
            "State should not be CRITICAL without override"
        
        print("✓ No override at threshold (0.70)")


class TestModifiersPerState:
    """Test that modifiers are correct for each state."""
    
    def test_modifier_values(self):
        """Verify all modifier values match specification."""
        from modules.alpha_interactions.interaction_aggregator import (
            AggregateInteractionState,
            ExecutionModifier,
            STATE_MODIFIERS,
        )
        
        # STRONG_POSITIVE
        sp = STATE_MODIFIERS[AggregateInteractionState.STRONG_POSITIVE]
        assert sp["confidence_modifier"] == 1.12
        assert sp["size_modifier"] == 1.10
        assert sp["execution_modifier"] == ExecutionModifier.BOOST
        
        # POSITIVE
        pos = STATE_MODIFIERS[AggregateInteractionState.POSITIVE]
        assert pos["confidence_modifier"] == 1.05
        assert pos["size_modifier"] == 1.03
        assert pos["execution_modifier"] == ExecutionModifier.NORMAL
        
        # NEUTRAL
        neu = STATE_MODIFIERS[AggregateInteractionState.NEUTRAL]
        assert neu["confidence_modifier"] == 1.00
        assert neu["size_modifier"] == 1.00
        assert neu["execution_modifier"] == ExecutionModifier.NORMAL
        
        # NEGATIVE
        neg = STATE_MODIFIERS[AggregateInteractionState.NEGATIVE]
        assert neg["confidence_modifier"] == 0.88
        assert neg["size_modifier"] == 0.85
        assert neg["execution_modifier"] == ExecutionModifier.CAUTION
        
        # CRITICAL
        crit = STATE_MODIFIERS[AggregateInteractionState.CRITICAL]
        assert crit["confidence_modifier"] == 0.70
        assert crit["size_modifier"] == 0.65
        assert crit["execution_modifier"] == ExecutionModifier.RESTRICT
        
        print("✓ All modifier values correct per specification")


class TestForceRanking:
    """Test strongest/weakest force detection."""
    
    def test_force_ranking_accuracy(self):
        """Test force ranking correctly identifies strongest and weakest."""
        from modules.alpha_interactions.interaction_aggregator import InteractionAggregator
        
        aggregator = InteractionAggregator()
        
        # Test with reinforcement dominant
        result1 = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=0.9,
            conflict_strength=0.1,
            synergy_strength=0.3,
            cancellation_strength=0.2,
        )
        assert result1.strongest_force == "reinforcement"
        assert result1.weakest_force == "conflict"
        print("✓ Reinforcement dominant detected correctly")
        
        # Test with cancellation dominant
        result2 = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=0.2,
            conflict_strength=0.3,
            synergy_strength=0.1,
            cancellation_strength=0.95,
        )
        assert result2.strongest_force == "cancellation"
        assert result2.weakest_force == "synergy"
        print("✓ Cancellation dominant detected correctly")
        
        # Test with synergy dominant
        result3 = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=0.5,
            conflict_strength=0.2,
            synergy_strength=0.85,
            cancellation_strength=0.1,
        )
        assert result3.strongest_force == "synergy"
        print("✓ Synergy dominant detected correctly")


class TestIntegrationWithPositionSizing:
    """Test integration with Position Sizing Engine."""
    
    def test_position_sizing_uses_interaction_modifier(self):
        """Position Sizing Engine should apply interaction_size_modifier."""
        from modules.trading_decision.position_sizing.position_sizing_engine import get_position_sizing_engine
        
        engine = get_position_sizing_engine()
        result = engine.compute("BTC")
        
        # Check drivers include interaction info
        assert "interaction_state" in result.drivers
        assert "interaction_score" in result.drivers
        assert "interaction_strongest_force" in result.drivers
        
        # The interaction_adjustment should affect final_size_pct
        # This is verified by checking that drivers contain interaction data
        print("✓ Position Sizing Engine includes interaction modifiers")
        print(f"  - interaction_state: {result.drivers.get('interaction_state')}")
        print(f"  - interaction_score: {result.drivers.get('interaction_score')}")


class TestIntegrationWithExecutionMode:
    """Test integration with Execution Mode Engine."""
    
    def test_execution_mode_uses_interaction_modifier(self):
        """Execution Mode Engine should apply interaction_execution_modifier."""
        from modules.trading_decision.execution_mode.execution_mode_engine import get_execution_mode_engine
        
        engine = get_execution_mode_engine()
        result = engine.compute("BTC")
        
        # Check drivers include interaction info
        assert "interaction_state" in result.drivers
        assert "interaction_score" in result.drivers
        assert "interaction_execution_modifier" in result.drivers
        assert "interaction_strongest_force" in result.drivers
        
        print("✓ Execution Mode Engine includes interaction modifiers")
        print(f"  - interaction_state: {result.drivers.get('interaction_state')}")
        print(f"  - interaction_execution_modifier: {result.drivers.get('interaction_execution_modifier')}")


class TestAggregationFormula:
    """Test the aggregation formula is correct."""
    
    def test_formula_weights(self):
        """Verify formula: score = 0.30*r + 0.25*s - 0.25*c - 0.20*x"""
        from modules.alpha_interactions.interaction_aggregator import (
            InteractionAggregator,
            AGGREGATION_WEIGHTS,
        )
        
        # Verify weights
        assert AGGREGATION_WEIGHTS["reinforcement"] == 0.30
        assert AGGREGATION_WEIGHTS["synergy"] == 0.25
        assert AGGREGATION_WEIGHTS["conflict"] == -0.25
        assert AGGREGATION_WEIGHTS["cancellation"] == -0.20
        print("✓ Aggregation weights correct")
        
        aggregator = InteractionAggregator()
        
        # Test calculation
        result = aggregator.aggregate_from_inputs(
            symbol="TEST",
            reinforcement_strength=0.5,
            conflict_strength=0.3,
            synergy_strength=0.4,
            cancellation_strength=0.2,
        )
        
        # Expected: 0.30*0.5 + 0.25*0.4 - 0.25*0.3 - 0.20*0.2
        #         = 0.15 + 0.10 - 0.075 - 0.04 = 0.135
        expected = 0.30*0.5 + 0.25*0.4 - 0.25*0.3 - 0.20*0.2
        assert abs(result.interaction_score - expected) < 0.001, \
            f"Expected {expected}, got {result.interaction_score}"
        
        print(f"✓ Formula calculation verified: {result.interaction_score}")


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
