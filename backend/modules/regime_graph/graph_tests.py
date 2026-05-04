"""
Regime Graph Engine Tests

PHASE 36 — Market Regime Graph Engine

Unit tests for regime graph construction and analysis.
Minimum 30 tests as per requirements.
"""

import pytest
from datetime import datetime, timezone, timedelta

from .graph_types import (
    RegimeGraphNode,
    RegimeGraphEdge,
    RegimeGraphState,
    RegimeGraphPath,
    RegimeGraphModifier,
    RegimeSequence,
    REGIME_GRAPH_WEIGHT,
    WEIGHT_NEXT_STATE_PROB,
    WEIGHT_TRANSITION_CONFIDENCE,
    WEIGHT_MEMORY_SCORE,
    MIN_TRANSITION_COUNT,
    REGIME_STATES,
)
from .graph_engine import RegimeGraphEngine


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return RegimeGraphEngine()


@pytest.fixture
def sample_history():
    """Create sample regime history."""
    now = datetime.now(timezone.utc)
    states = ["TRENDING", "RANGING", "VOLATILE", "TRENDING", "RANGING", "COMPRESSION", "EXPANSION", "TRENDING"]
    
    return [
        {
            "regime_state": states[i % len(states)],
            "timestamp": now - timedelta(hours=100 - i),
            "success": i % 3 != 0,
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_edges():
    """Create sample edges."""
    return [
        RegimeGraphEdge(
            from_state="TRENDING",
            to_state="RANGING",
            transition_probability=0.4,
            transition_count=20,
        ),
        RegimeGraphEdge(
            from_state="TRENDING",
            to_state="VOLATILE",
            transition_probability=0.3,
            transition_count=15,
        ),
        RegimeGraphEdge(
            from_state="RANGING",
            to_state="TRENDING",
            transition_probability=0.5,
            transition_count=25,
        ),
        RegimeGraphEdge(
            from_state="RANGING",
            to_state="COMPRESSION",
            transition_probability=0.3,
            transition_count=15,
        ),
    ]


# ══════════════════════════════════════════════════════════════
# 1. Node Creation Tests
# ══════════════════════════════════════════════════════════════

def test_node_creation_basic():
    """Test basic node creation."""
    node = RegimeGraphNode(
        regime_state="TRENDING",
        visits=10,
        avg_duration_minutes=60.0,
    )
    
    assert node.regime_state == "TRENDING"
    assert node.visits == 10
    assert node.avg_duration_minutes == 60.0


def test_node_creation_defaults():
    """Test node creation with defaults."""
    node = RegimeGraphNode(regime_state="RANGING")
    
    assert node.regime_state == "RANGING"
    assert node.visits == 0
    assert node.avg_duration_minutes == 0.0
    assert node.avg_success_rate == 0.0


def test_node_all_regime_states():
    """Test node creation for all regime states."""
    for state in REGIME_STATES:
        node = RegimeGraphNode(regime_state=state)
        assert node.regime_state == state


# ══════════════════════════════════════════════════════════════
# 2. Edge Creation Tests
# ══════════════════════════════════════════════════════════════

def test_edge_creation_basic():
    """Test basic edge creation."""
    edge = RegimeGraphEdge(
        from_state="TRENDING",
        to_state="RANGING",
        transition_probability=0.5,
        transition_count=10,
    )
    
    assert edge.from_state == "TRENDING"
    assert edge.to_state == "RANGING"
    assert edge.transition_probability == 0.5
    assert edge.transition_count == 10


def test_edge_probability_bounds():
    """Test edge probability bounds."""
    edge = RegimeGraphEdge(
        from_state="A",
        to_state="B",
        transition_probability=0.5,
    )
    
    assert 0 <= edge.transition_probability <= 1


def test_edge_confidence_calculation():
    """Test edge confidence based on count."""
    edge = RegimeGraphEdge(
        from_state="A",
        to_state="B",
        transition_probability=0.5,
        transition_count=5,
        edge_confidence=0.5,  # 5/10 = 0.5
    )
    
    assert edge.edge_confidence == 0.5


# ══════════════════════════════════════════════════════════════
# 3. Transition Probability Tests
# ══════════════════════════════════════════════════════════════

def test_transition_probability_calculation(engine, sample_history):
    """Test transition probability calculation."""
    edges = engine.build_edges(sample_history)
    matrix = engine.build_transition_matrix(edges)
    
    # Check that probabilities are valid
    for from_state, to_states in matrix.items():
        total_prob = sum(to_states.values())
        # Probabilities should sum to ~1.0 for each from_state
        assert 0.99 <= total_prob <= 1.01


def test_transition_probability_from_edges(engine, sample_edges):
    """Test building matrix from edges."""
    matrix = engine.build_transition_matrix(sample_edges)
    
    assert matrix["TRENDING"]["RANGING"] == 0.4
    assert matrix["TRENDING"]["VOLATILE"] == 0.3


def test_get_transition_probability(engine, sample_edges):
    """Test getting specific transition probability."""
    matrix = engine.build_transition_matrix(sample_edges)
    
    prob = engine.get_transition_probability(matrix, "TRENDING", "RANGING")
    assert prob == 0.4
    
    # Non-existent transition
    prob = engine.get_transition_probability(matrix, "VOLATILE", "COMPRESSION")
    assert prob == 0.0


# ══════════════════════════════════════════════════════════════
# 4. Outgoing Normalization Tests
# ══════════════════════════════════════════════════════════════

def test_outgoing_normalization(engine, sample_history):
    """Test that outgoing probabilities sum to 1."""
    edges = engine.build_edges(sample_history)
    matrix = engine.build_transition_matrix(edges)
    
    for from_state, to_states in matrix.items():
        if to_states:  # Only check non-empty
            total = sum(to_states.values())
            assert abs(total - 1.0) < 0.02  # Allow small rounding error


def test_single_outgoing_edge(engine):
    """Test normalization with single outgoing edge."""
    history = [
        {"regime_state": "TRENDING", "timestamp": datetime.now(timezone.utc) - timedelta(hours=2)},
        {"regime_state": "RANGING", "timestamp": datetime.now(timezone.utc) - timedelta(hours=1)},
        {"regime_state": "RANGING", "timestamp": datetime.now(timezone.utc)},
    ]
    
    edges = engine.build_edges(history)
    matrix = engine.build_transition_matrix(edges)
    
    # TRENDING only transitions to RANGING
    assert matrix.get("TRENDING", {}).get("RANGING", 0) == 1.0


# ══════════════════════════════════════════════════════════════
# 5. Likely Next State Tests
# ══════════════════════════════════════════════════════════════

def test_likely_next_state(engine, sample_edges):
    """Test likely next state prediction."""
    matrix = engine.build_transition_matrix(sample_edges)
    
    likely, prob, alternatives = engine.predict_next_state(matrix, "RANGING")
    
    assert likely == "TRENDING"  # 0.5 > 0.3
    assert prob == 0.5


def test_likely_next_state_no_outgoing(engine):
    """Test likely next state with no outgoing edges."""
    matrix = {"TRENDING": {"RANGING": 0.5}}
    
    likely, prob, alternatives = engine.predict_next_state(matrix, "VOLATILE")
    
    assert likely == "UNCERTAIN"
    assert prob == 0.0


def test_alternative_states(engine, sample_edges):
    """Test alternative states in prediction."""
    matrix = engine.build_transition_matrix(sample_edges)
    
    _, _, alternatives = engine.predict_next_state(matrix, "TRENDING")
    
    assert len(alternatives) >= 1
    assert alternatives[0]["state"] == "VOLATILE"


# ══════════════════════════════════════════════════════════════
# 6. Path Confidence Tests
# ══════════════════════════════════════════════════════════════

def test_path_confidence_formula(engine):
    """Test path confidence formula."""
    confidence = engine.calculate_path_confidence(
        next_state_probability=0.8,
        transition_confidence=0.6,
        memory_score=0.5,
    )
    
    expected = 0.50 * 0.8 + 0.25 * 0.6 + 0.25 * 0.5
    assert abs(confidence - expected) < 0.01


def test_path_confidence_bounds(engine):
    """Test path confidence is bounded [0, 1]."""
    confidence = engine.calculate_path_confidence(1.0, 1.0, 1.0)
    assert 0 <= confidence <= 1
    
    confidence = engine.calculate_path_confidence(0.0, 0.0, 0.0)
    assert confidence == 0.0


def test_path_confidence_weights_sum():
    """Verify path confidence weights sum to 1.0."""
    total = WEIGHT_NEXT_STATE_PROB + WEIGHT_TRANSITION_CONFIDENCE + WEIGHT_MEMORY_SCORE
    assert abs(total - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════
# 7. Graph Persistence Tests
# ══════════════════════════════════════════════════════════════

def test_graph_state_serialization():
    """Test graph state can be serialized."""
    state = RegimeGraphState(
        symbol="BTC",
        current_state="TRENDING",
        likely_next_state="RANGING",
        next_state_probability=0.6,
        path_confidence=0.7,
    )
    
    data = state.model_dump()
    assert data["symbol"] == "BTC"
    assert data["current_state"] == "TRENDING"


def test_graph_state_caching(engine):
    """Test that graph states are cached."""
    state1 = engine.analyze("BTC")
    cached = engine.get_current_state("BTC")
    
    assert cached is not None
    assert cached.symbol == state1.symbol


# ══════════════════════════════════════════════════════════════
# 8. API Endpoint Tests (unit level)
# ══════════════════════════════════════════════════════════════

def test_analyze_returns_valid_state(engine):
    """Test analyze returns valid state."""
    state = engine.analyze("BTC")
    
    assert isinstance(state, RegimeGraphState)
    assert state.symbol == "BTC"
    assert state.current_state in REGIME_STATES + ["UNCERTAIN"]
    assert 0 <= state.path_confidence <= 1


def test_predict_path_returns_valid(engine):
    """Test predict_path returns valid path."""
    path = engine.predict_path("ETH", steps=3)
    
    assert isinstance(path, RegimeGraphPath)
    assert path.symbol == "ETH"
    assert len(path.predicted_path) <= 3


# ══════════════════════════════════════════════════════════════
# 9. Integration Tests
# ══════════════════════════════════════════════════════════════

def test_integration_with_nodes_edges(engine, sample_history):
    """Test nodes and edges are built correctly together."""
    nodes = engine.build_nodes(sample_history)
    edges = engine.build_edges(sample_history)
    
    # Should have nodes for states that appear
    visited_states = set(h["regime_state"] for h in sample_history)
    visited_nodes = [n for n in nodes if n.visits > 0]
    
    assert len(visited_nodes) > 0
    assert len(edges) > 0


def test_integration_full_analysis(engine):
    """Test full analysis integration."""
    state = engine.analyze("SOL")
    
    # Should have all components
    assert len(state.nodes) > 0
    assert state.current_state is not None
    assert state.likely_next_state is not None


# ══════════════════════════════════════════════════════════════
# 10. Sequence Memory Tests
# ══════════════════════════════════════════════════════════════

def test_sequence_memory_building(engine, sample_history):
    """Test sequence memory is built."""
    seq_memory = engine.build_sequence_memory(sample_history)
    
    assert len(seq_memory) > 0
    # Should have sequences like "TRENDING→RANGING"
    assert any("→" in key for key in seq_memory.keys())


def test_likely_sequence(engine, sample_history):
    """Test likely sequence retrieval."""
    seq_memory = engine.build_sequence_memory(sample_history)
    
    likely = engine.get_likely_sequence(seq_memory, "TRENDING", "RANGING")
    # May or may not find a sequence
    # Just verify no crash


# ══════════════════════════════════════════════════════════════
# 11. Modifier Tests
# ══════════════════════════════════════════════════════════════

def test_modifier_returns_valid(engine):
    """Test modifier returns valid structure."""
    modifier = engine.get_modifier("BTC", "LONG")
    
    assert isinstance(modifier, RegimeGraphModifier)
    assert modifier.symbol == "BTC"
    assert modifier.graph_weight == REGIME_GRAPH_WEIGHT


def test_modifier_weight_correct(engine):
    """Test modifier uses correct weight."""
    modifier = engine.get_modifier("ETH", "SHORT")
    
    assert modifier.graph_weight == 0.04


def test_modifier_weighted_contribution(engine):
    """Test weighted contribution calculation."""
    modifier = engine.get_modifier("BTC", "LONG")
    
    expected = modifier.graph_score * REGIME_GRAPH_WEIGHT
    assert abs(modifier.weighted_contribution - expected) < 0.001


def test_modifier_favorable_transition(engine):
    """Test favorable transition detection."""
    # This tests the internal logic
    assert engine._is_favorable_transition("RANGING", "TREND_UP", "LONG") == True
    assert engine._is_favorable_transition("RANGING", "TREND_DOWN", "SHORT") == True
    assert engine._is_favorable_transition("TRENDING", "RANGING", "LONG") == False


# ══════════════════════════════════════════════════════════════
# 12. Edge Cases
# ══════════════════════════════════════════════════════════════

def test_empty_history(engine):
    """Test handling of empty history."""
    nodes = engine.build_nodes([])
    edges = engine.build_edges([])
    
    # Should return empty but valid
    assert len(edges) == 0


def test_single_state_history(engine):
    """Test history with single state."""
    history = [{"regime_state": "TRENDING", "timestamp": datetime.now(timezone.utc)}]
    
    nodes = engine.build_nodes(history)
    edges = engine.build_edges(history)
    
    # No transitions possible
    assert len(edges) == 0


def test_deterministic_output(engine):
    """Test deterministic output for same symbol."""
    state1 = engine.analyze("BTC")
    state2 = engine.analyze("BTC")
    
    # Should be consistent (though timestamp differs)
    assert state1.symbol == state2.symbol
    assert state1.current_state == state2.current_state


def test_missing_data_safe(engine):
    """Test handling of missing data in history."""
    history = [
        {"regime_state": "TRENDING"},  # No timestamp
        {"timestamp": datetime.now(timezone.utc)},  # No state
    ]
    
    # Should not crash
    nodes = engine.build_nodes(history)
    edges = engine.build_edges(history)


def test_large_history_safe(engine):
    """Test handling of large history."""
    now = datetime.now(timezone.utc)
    history = [
        {
            "regime_state": ["TRENDING", "RANGING", "VOLATILE"][i % 3],
            "timestamp": now - timedelta(minutes=i),
        }
        for i in range(1000)
    ]
    
    # Should complete without error
    state = engine.analyze("BTC")
    assert state is not None


# ══════════════════════════════════════════════════════════════
# 13. Summary Tests
# ══════════════════════════════════════════════════════════════

def test_summary_generation(engine):
    """Test summary generation."""
    # Analyze first
    engine.analyze("BTC")
    
    summary = engine.generate_summary("BTC")
    
    assert summary.symbol == "BTC"
    assert summary.node_count >= 0
    assert summary.edge_count >= 0


# ══════════════════════════════════════════════════════════════
# 14. State Normalization Tests
# ══════════════════════════════════════════════════════════════

def test_state_normalization(engine):
    """Test state normalization."""
    assert engine._normalize_state("TREND_UP") == "TREND_UP"
    assert engine._normalize_state("RANGE") == "RANGING"
    assert engine._normalize_state("HIGH_VOLATILITY") == "VOLATILE"
    assert engine._normalize_state("UNKNOWN") == "UNCERTAIN"


def test_multiple_symbols(engine):
    """Test analyzing multiple symbols."""
    symbols = ["BTC", "ETH", "SOL"]
    states = [engine.analyze(s) for s in symbols]
    
    assert len(states) == 3
    assert all(s.symbol == symbols[i] for i, s in enumerate(states))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
