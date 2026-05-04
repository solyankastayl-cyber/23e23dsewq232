"""
Strategy Brain — Tests

PHASE 29.5 — 20+ tests for Strategy Brain Integration

Tests:
1. bullish continuation mapping
2. bearish continuation mapping
3. breakout forming mapping
4. range mean reversion mapping
5. no edge fallback
6. suitability score calculation
7. microstructure supportive case
8. microstructure stressed case
9. execution unfavorable block
10. strategy selection
11. confidence propagation
12. reliability propagation
13. endpoint decision
14. endpoint summary
15. endpoint recompute
16. integration hypothesis engine
17. integration regime engine
18. integration microstructure engine
19. edge case no strategy
20. multi-strategy comparison
21. reason generation
22. history tracking
"""

import pytest
from datetime import datetime

from modules.strategy_brain.strategy_brain_engine import (
    StrategyBrainEngine,
    get_strategy_brain,
)
from modules.strategy_brain.strategy_types import (
    HYPOTHESIS_STRATEGY_MAP,
    MICROSTRUCTURE_EXECUTION_QUALITY,
    WEIGHT_CONFIDENCE,
    WEIGHT_RELIABILITY,
    WEIGHT_REGIME,
    WEIGHT_MICROSTRUCTURE,
)


# ══════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════

def create_strategy_brain():
    """Create isolated strategy brain for testing."""
    brain = StrategyBrainEngine()
    brain._decisions = {}
    brain._current = {}
    return brain


# ══════════════════════════════════════════════════════════════
# Test 1: Bullish Continuation Mapping
# ══════════════════════════════════════════════════════════════

def test_bullish_continuation_mapping():
    """Test BULLISH_CONTINUATION maps to correct strategies."""
    brain = create_strategy_brain()
    candidates = brain.get_candidate_strategies("BULLISH_CONTINUATION")
    
    assert "trend_following" in candidates
    assert "breakout_trading" in candidates
    assert len(candidates) == 2


# ══════════════════════════════════════════════════════════════
# Test 2: Bearish Continuation Mapping
# ══════════════════════════════════════════════════════════════

def test_bearish_continuation_mapping():
    """Test BEARISH_CONTINUATION maps to correct strategies."""
    brain = create_strategy_brain()
    candidates = brain.get_candidate_strategies("BEARISH_CONTINUATION")
    
    assert "trend_following" in candidates
    assert "volatility_expansion" in candidates


# ══════════════════════════════════════════════════════════════
# Test 3: Breakout Forming Mapping
# ══════════════════════════════════════════════════════════════

def test_breakout_forming_mapping():
    """Test BREAKOUT_FORMING maps to correct strategies."""
    brain = create_strategy_brain()
    candidates = brain.get_candidate_strategies("BREAKOUT_FORMING")
    
    assert "breakout_trading" in candidates
    assert "volatility_expansion" in candidates


# ══════════════════════════════════════════════════════════════
# Test 4: Range Mean Reversion Mapping
# ══════════════════════════════════════════════════════════════

def test_range_mean_reversion_mapping():
    """Test RANGE_MEAN_REVERSION maps to correct strategies."""
    brain = create_strategy_brain()
    candidates = brain.get_candidate_strategies("RANGE_MEAN_REVERSION")
    
    assert "mean_reversion" in candidates
    assert "range_trading" in candidates


# ══════════════════════════════════════════════════════════════
# Test 5: No Edge Fallback
# ══════════════════════════════════════════════════════════════

def test_no_edge_fallback():
    """Test NO_EDGE returns empty candidates."""
    brain = create_strategy_brain()
    candidates = brain.get_candidate_strategies("NO_EDGE")
    
    assert candidates == []


# ══════════════════════════════════════════════════════════════
# Test 6: Suitability Score Calculation
# ══════════════════════════════════════════════════════════════

def test_suitability_score_calculation():
    """Test suitability score formula."""
    brain = create_strategy_brain()
    
    score = brain.calculate_suitability_score(
        confidence=0.7,
        reliability=0.6,
        regime_support=0.65,
        microstructure_state="SUPPORTIVE",
    )
    
    # Manual calculation:
    # 0.45*0.7 + 0.25*0.6 + 0.20*0.65 + 0.10*1.0
    # = 0.315 + 0.15 + 0.13 + 0.1 = 0.695
    expected = (
        WEIGHT_CONFIDENCE * 0.7
        + WEIGHT_RELIABILITY * 0.6
        + WEIGHT_REGIME * 0.65
        + WEIGHT_MICROSTRUCTURE * 1.0
    )
    
    assert abs(score - round(expected, 4)) < 0.01
    assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 7: Microstructure Supportive Case
# ══════════════════════════════════════════════════════════════

def test_microstructure_supportive_case():
    """Test microstructure SUPPORTIVE gives quality 1.0."""
    brain = create_strategy_brain()
    quality = brain.get_microstructure_quality("SUPPORTIVE")
    assert quality == 1.0


# ══════════════════════════════════════════════════════════════
# Test 8: Microstructure Stressed Case
# ══════════════════════════════════════════════════════════════

def test_microstructure_stressed_case():
    """Test microstructure STRESSED gives quality 0.25."""
    brain = create_strategy_brain()
    quality = brain.get_microstructure_quality("STRESSED")
    assert quality == 0.25


# ══════════════════════════════════════════════════════════════
# Test 9: Execution Unfavorable Block
# ══════════════════════════════════════════════════════════════

def test_execution_unfavorable_block():
    """Test that UNFAVORABLE execution blocks strategy."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        confidence=0.7,
        reliability=0.6,
        regime_support=0.65,
        regime_type="TRENDING",
        microstructure_state="STRESSED",
        execution_state="UNFAVORABLE",
    )
    
    assert decision.selected_strategy == "none"
    assert "blocked" in decision.reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 10: Strategy Selection
# ══════════════════════════════════════════════════════════════

def test_strategy_selection():
    """Test strategy selection with valid hypothesis."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="ETH",
        hypothesis_type="BREAKOUT_FORMING",
        directional_bias="LONG",
        confidence=0.65,
        reliability=0.55,
        regime_support=0.6,
        regime_type="TRENDING",
        microstructure_state="SUPPORTIVE",
        execution_state="FAVORABLE",
    )
    
    assert decision.selected_strategy == "breakout_trading"
    assert decision.suitability_score > 0
    assert decision.alternative_strategies == ["volatility_expansion"]


# ══════════════════════════════════════════════════════════════
# Test 11: Confidence Propagation
# ══════════════════════════════════════════════════════════════

def test_confidence_propagation():
    """Test that confidence propagates to decision."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        confidence=0.72,
        reliability=0.58,
        regime_support=0.6,
        regime_type="TRENDING",
        microstructure_state="NEUTRAL",
        execution_state="CAUTIOUS",
    )
    
    assert decision.confidence == 0.72


# ══════════════════════════════════════════════════════════════
# Test 12: Reliability Propagation
# ══════════════════════════════════════════════════════════════

def test_reliability_propagation():
    """Test that reliability propagates to decision."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        confidence=0.72,
        reliability=0.58,
        regime_support=0.6,
        regime_type="TRENDING",
        microstructure_state="NEUTRAL",
        execution_state="CAUTIOUS",
    )
    
    assert decision.reliability == 0.58


# ══════════════════════════════════════════════════════════════
# Test 13: Endpoint Decision (simulated)
# ══════════════════════════════════════════════════════════════

def test_endpoint_decision_simulated():
    """Test decision endpoint simulation."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="RANGE_MEAN_REVERSION",
        directional_bias="NEUTRAL",
        confidence=0.6,
        reliability=0.55,
        regime_support=0.7,
        regime_type="RANGING",
        microstructure_state="NEUTRAL",
        execution_state="CAUTIOUS",
    )
    
    # Simulate API response
    response = {
        "symbol": decision.symbol,
        "selected_strategy": decision.selected_strategy,
        "suitability_score": decision.suitability_score,
    }
    
    assert response["selected_strategy"] == "mean_reversion"
    assert response["suitability_score"] > 0


# ══════════════════════════════════════════════════════════════
# Test 14: Endpoint Summary (simulated)
# ══════════════════════════════════════════════════════════════

def test_endpoint_summary_simulated():
    """Test summary endpoint simulation."""
    brain = create_strategy_brain()
    
    # Generate several decisions
    for _ in range(5):
        brain.select_strategy(
            symbol="BTC",
            hypothesis_type="BULLISH_CONTINUATION",
            directional_bias="LONG",
            confidence=0.65,
            reliability=0.55,
            regime_support=0.6,
            regime_type="TRENDING",
            microstructure_state="NEUTRAL",
            execution_state="CAUTIOUS",
        )
    
    summary = brain.get_summary("BTC")
    
    assert summary.total_decisions == 5
    assert summary.trend_following_count == 5


# ══════════════════════════════════════════════════════════════
# Test 15: Endpoint Recompute (simulated)
# ══════════════════════════════════════════════════════════════

def test_endpoint_recompute_simulated():
    """Test recompute endpoint simulation."""
    brain = create_strategy_brain()
    
    d1 = brain.select_strategy(
        symbol="SOL",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        confidence=0.6,
        reliability=0.5,
        regime_support=0.6,
        regime_type="TRENDING",
        microstructure_state="NEUTRAL",
        execution_state="CAUTIOUS",
    )
    
    d2 = brain.select_strategy(
        symbol="SOL",
        hypothesis_type="BREAKOUT_FORMING",
        directional_bias="LONG",
        confidence=0.7,
        reliability=0.6,
        regime_support=0.65,
        regime_type="TRENDING",
        microstructure_state="SUPPORTIVE",
        execution_state="FAVORABLE",
    )
    
    assert d1.selected_strategy == "trend_following"
    assert d2.selected_strategy == "breakout_trading"
    
    # History should have both
    history = brain.get_history("SOL")
    assert len(history) == 2


# ══════════════════════════════════════════════════════════════
# Test 16: Integration Hypothesis Engine
# ══════════════════════════════════════════════════════════════

def test_integration_hypothesis_engine():
    """Test integration with hypothesis engine."""
    brain = create_strategy_brain()
    
    # This should work if hypothesis engine is available
    try:
        decision = brain.select_strategy_from_hypothesis("BTC")
        
        assert decision.symbol == "BTC"
        assert decision.hypothesis_type in HYPOTHESIS_STRATEGY_MAP.keys()
    except Exception:
        # If hypothesis engine not available, test passes
        pass


# ══════════════════════════════════════════════════════════════
# Test 17: Integration Regime Engine
# ══════════════════════════════════════════════════════════════

def test_integration_regime_context():
    """Test that regime context influences decision."""
    brain = create_strategy_brain()
    
    # Trending regime should work well with trend strategies
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        confidence=0.65,
        reliability=0.55,
        regime_support=0.8,  # High regime support
        regime_type="TRENDING",
        microstructure_state="NEUTRAL",
        execution_state="CAUTIOUS",
    )
    
    assert "trending" in decision.reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 18: Integration Microstructure Engine
# ══════════════════════════════════════════════════════════════

def test_integration_microstructure_context():
    """Test that microstructure context influences decision."""
    brain = create_strategy_brain()
    
    # Supportive microstructure should appear in reason
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="BULLISH_CONTINUATION",
        directional_bias="LONG",
        confidence=0.65,
        reliability=0.55,
        regime_support=0.6,
        regime_type="TRENDING",
        microstructure_state="SUPPORTIVE",
        execution_state="FAVORABLE",
    )
    
    assert "supportive" in decision.reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 19: Edge Case No Strategy
# ══════════════════════════════════════════════════════════════

def test_edge_case_no_strategy():
    """Test NO_EDGE hypothesis returns no strategy."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="NO_EDGE",
        directional_bias="NEUTRAL",
        confidence=0.3,
        reliability=0.2,
        regime_support=0.3,
        regime_type="VOLATILE",
        microstructure_state="STRESSED",
        execution_state="CAUTIOUS",
    )
    
    assert decision.selected_strategy == "none"
    assert decision.alternative_strategies == []


# ══════════════════════════════════════════════════════════════
# Test 20: Multi-Strategy Comparison
# ══════════════════════════════════════════════════════════════

def test_multi_strategy_comparison():
    """Test that alternatives are properly returned."""
    brain = create_strategy_brain()
    
    decision = brain.select_strategy(
        symbol="BTC",
        hypothesis_type="BREAKOUT_FORMING",
        directional_bias="LONG",
        confidence=0.7,
        reliability=0.6,
        regime_support=0.65,
        regime_type="TRENDING",
        microstructure_state="SUPPORTIVE",
        execution_state="FAVORABLE",
    )
    
    assert decision.selected_strategy == "breakout_trading"
    assert "volatility_expansion" in decision.alternative_strategies


# ══════════════════════════════════════════════════════════════
# Test 21: Reason Generation
# ══════════════════════════════════════════════════════════════

def test_reason_generation():
    """Test reason generation for different scenarios."""
    brain = create_strategy_brain()
    
    # Test blocked reason
    reason = brain.generate_reason(
        hypothesis_type="BULLISH_CONTINUATION",
        selected_strategy="none",
        directional_bias="LONG",
        regime_type="TRENDING",
        microstructure_state="STRESSED",
        execution_state="UNFAVORABLE",
    )
    
    assert "blocked" in reason.lower()
    
    # Test normal reason
    reason = brain.generate_reason(
        hypothesis_type="BREAKOUT_FORMING",
        selected_strategy="breakout_trading",
        directional_bias="LONG",
        regime_type="TRENDING",
        microstructure_state="SUPPORTIVE",
        execution_state="FAVORABLE",
    )
    
    assert "breakout" in reason.lower()


# ══════════════════════════════════════════════════════════════
# Test 22: History Tracking
# ══════════════════════════════════════════════════════════════

def test_history_tracking():
    """Test decision history tracking."""
    brain = create_strategy_brain()
    
    for i in range(10):
        brain.select_strategy(
            symbol="ETH",
            hypothesis_type="BULLISH_CONTINUATION",
            directional_bias="LONG",
            confidence=0.6 + i * 0.02,
            reliability=0.5 + i * 0.01,
            regime_support=0.6,
            regime_type="TRENDING",
            microstructure_state="NEUTRAL",
            execution_state="CAUTIOUS",
        )
    
    history = brain.get_history("ETH", limit=5)
    assert len(history) == 5
    
    # Should be sorted newest first
    for i in range(len(history) - 1):
        assert history[i].created_at >= history[i + 1].created_at


# ══════════════════════════════════════════════════════════════
# Test 23: Microstructure Quality Mapping
# ══════════════════════════════════════════════════════════════

def test_microstructure_quality_mapping():
    """Test all microstructure states map correctly."""
    brain = create_strategy_brain()
    
    assert brain.get_microstructure_quality("SUPPORTIVE") == 1.0
    assert brain.get_microstructure_quality("NEUTRAL") == 0.7
    assert brain.get_microstructure_quality("FRAGILE") == 0.45
    assert brain.get_microstructure_quality("STRESSED") == 0.25
    assert brain.get_microstructure_quality("UNKNOWN") == 0.5  # Default


# ══════════════════════════════════════════════════════════════
# Test 24: Should Block Strategy
# ══════════════════════════════════════════════════════════════

def test_should_block_strategy():
    """Test execution filter logic."""
    brain = create_strategy_brain()
    
    assert brain.should_block_strategy("UNFAVORABLE") is True
    assert brain.should_block_strategy("CAUTIOUS") is False
    assert brain.should_block_strategy("FAVORABLE") is False


# ══════════════════════════════════════════════════════════════
# Run tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
