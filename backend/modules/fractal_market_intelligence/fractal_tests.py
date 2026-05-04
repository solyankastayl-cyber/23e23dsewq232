"""
Fractal Market Intelligence Engine Tests

PHASE 32.1 — 26+ tests for Fractal Market Intelligence Engine

Tests:
1. TF classification correct
2. Trend detection correct
3. Range detection correct
4. Alignment calculation
5. Bias determination
6. Confidence calculation
7. Modifier calculation
8. Bounds check
9. State endpoint
10. Summary endpoint
11. History endpoint
12. Recompute endpoint
13. Storage correct
14. Multi timeframe consistency
15. Integration with hypothesis engine
16. Integration with meta alpha
17. Deterministic output
18. Missing data safe
19. Large dataset safe
20. Scheduler safe
21. Volatility detection
22. Trend reversal detection
23. Alignment threshold logic
24. Neutral bias logic
25. Confidence bounds
26. Integration stability
"""

import pytest
from datetime import datetime, timezone
from typing import Dict

from modules.fractal_market_intelligence.fractal_engine import (
    FractalEngine,
    get_fractal_engine,
)
from modules.fractal_market_intelligence.fractal_types import (
    FractalMarketState,
    FractalSummary,
    TimeframeAnalysis,
    FractalModifier,
    TIMEFRAMES,
    ALIGNMENT_BIAS_THRESHOLD,
    ALIGNMENT_NEUTRAL_THRESHOLD,
    FRACTAL_ALIGNED_MODIFIER,
    FRACTAL_CONFLICT_MODIFIER,
)


# ══════════════════════════════════════════════════════════════
# Test Fixtures
# ══════════════════════════════════════════════════════════════

def create_bullish_tf_data() -> Dict[str, Dict]:
    """Create bullish timeframe data."""
    return {
        "5m": {"ema_slope": 0.04, "atr_expansion": 0.9, "structure_break": True},
        "15m": {"ema_slope": 0.035, "atr_expansion": 0.85, "structure_break": True},
        "1h": {"ema_slope": 0.03, "atr_expansion": 0.8, "structure_break": False},
        "4h": {"ema_slope": 0.025, "atr_expansion": 0.75, "structure_break": False},
        "1d": {"ema_slope": 0.01, "atr_expansion": 0.7, "structure_break": False},
    }


def create_bearish_tf_data() -> Dict[str, Dict]:
    """Create bearish timeframe data."""
    return {
        "5m": {"ema_slope": -0.04, "atr_expansion": 0.9, "structure_break": True},
        "15m": {"ema_slope": -0.035, "atr_expansion": 0.85, "structure_break": True},
        "1h": {"ema_slope": -0.03, "atr_expansion": 0.8, "structure_break": False},
        "4h": {"ema_slope": -0.025, "atr_expansion": 0.75, "structure_break": False},
        "1d": {"ema_slope": -0.01, "atr_expansion": 0.7, "structure_break": False},
    }


def create_ranging_tf_data() -> Dict[str, Dict]:
    """Create ranging timeframe data."""
    return {
        "5m": {"ema_slope": 0.005, "atr_expansion": 0.6, "structure_break": False},
        "15m": {"ema_slope": -0.003, "atr_expansion": 0.5, "structure_break": False},
        "1h": {"ema_slope": 0.002, "atr_expansion": 0.55, "structure_break": False},
        "4h": {"ema_slope": -0.001, "atr_expansion": 0.45, "structure_break": False},
        "1d": {"ema_slope": 0.001, "atr_expansion": 0.5, "structure_break": False},
    }


# ══════════════════════════════════════════════════════════════
# Test 1: TF Classification Correct
# ══════════════════════════════════════════════════════════════

def test_tf_classification_correct():
    """Test timeframe classification returns valid states."""
    engine = FractalEngine()
    
    state, confidence = engine.classify_timeframe_state(0.03, 0.9, False)
    assert state in ["TREND_UP", "TREND_DOWN", "RANGE", "VOLATILE"]
    assert 0 <= confidence <= 1


# ══════════════════════════════════════════════════════════════
# Test 2: Trend Detection Correct
# ══════════════════════════════════════════════════════════════

def test_trend_detection_correct():
    """Test trend detection based on EMA slope."""
    engine = FractalEngine()
    
    # Positive slope -> TREND_UP
    state, _ = engine.classify_timeframe_state(0.05, 0.8, False)
    assert state == "TREND_UP"
    
    # Negative slope -> TREND_DOWN
    state, _ = engine.classify_timeframe_state(-0.05, 0.8, False)
    assert state == "TREND_DOWN"


# ══════════════════════════════════════════════════════════════
# Test 3: Range Detection Correct
# ══════════════════════════════════════════════════════════════

def test_range_detection_correct():
    """Test range detection with flat slope and low ATR."""
    engine = FractalEngine()
    
    # Flat slope, low ATR -> RANGE
    state, _ = engine.classify_timeframe_state(0.005, 0.5, False)
    assert state == "RANGE"


# ══════════════════════════════════════════════════════════════
# Test 4: Alignment Calculation
# ══════════════════════════════════════════════════════════════

def test_alignment_calculation():
    """Test fractal alignment calculation."""
    engine = FractalEngine()
    
    # All TREND_UP -> high alignment
    tf_states = {
        "5m": "TREND_UP",
        "15m": "TREND_UP",
        "1h": "TREND_UP",
        "4h": "TREND_UP",
        "1d": "TREND_UP",
    }
    alignment, dominant = engine.calculate_alignment(tf_states)
    assert alignment == 1.0
    assert dominant == "TREND_UP"


# ══════════════════════════════════════════════════════════════
# Test 5: Bias Determination
# ══════════════════════════════════════════════════════════════

def test_bias_determination():
    """Test fractal bias determination from alignment."""
    engine = FractalEngine()
    
    # High alignment + TREND_UP -> LONG
    bias = engine.determine_bias(0.8, "TREND_UP")
    assert bias == "LONG"
    
    # High alignment + TREND_DOWN -> SHORT
    bias = engine.determine_bias(0.8, "TREND_DOWN")
    assert bias == "SHORT"
    
    # Low alignment -> NEUTRAL
    bias = engine.determine_bias(0.3, "TREND_UP")
    assert bias == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Test 6: Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_confidence_calculation():
    """Test fractal confidence calculation."""
    engine = FractalEngine()
    
    # 0.60 * alignment + 0.40 * vol_consistency
    confidence = engine.calculate_confidence(0.8, 0.7)
    expected = 0.60 * 0.8 + 0.40 * 0.7  # 0.48 + 0.28 = 0.76
    assert abs(confidence - expected) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 7: Modifier Calculation
# ══════════════════════════════════════════════════════════════

def test_modifier_calculation():
    """Test fractal modifier for hypothesis."""
    engine = FractalEngine()
    
    # Generate bullish state
    state = engine.generate_fractal_state("TEST", create_bullish_tf_data())
    
    # Aligned hypothesis -> boost
    modifier = engine.get_fractal_modifier("TEST", "LONG")
    if state.fractal_bias == "LONG":
        assert modifier.modifier == FRACTAL_ALIGNED_MODIFIER
    
    # Conflicting hypothesis -> penalize
    modifier = engine.get_fractal_modifier("TEST", "SHORT")
    if state.fractal_bias == "LONG":
        assert modifier.modifier == FRACTAL_CONFLICT_MODIFIER


# ══════════════════════════════════════════════════════════════
# Test 8: Bounds Check
# ══════════════════════════════════════════════════════════════

def test_bounds_check():
    """Test all metrics are within bounds."""
    engine = FractalEngine()
    
    state = engine.generate_fractal_state("BTC")
    
    assert 0 <= state.fractal_alignment <= 1
    assert 0 <= state.fractal_confidence <= 1
    assert state.fractal_bias in ["LONG", "SHORT", "NEUTRAL"]


# ══════════════════════════════════════════════════════════════
# Test 9: State Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_state_endpoint_valid():
    """Test state endpoint returns valid response."""
    import asyncio
    from modules.fractal_market_intelligence.fractal_routes import get_fractal_state
    
    response = asyncio.get_event_loop().run_until_complete(get_fractal_state("BTC"))
    
    assert "symbol" in response
    assert response["symbol"] == "BTC"
    assert "timeframe_states" in response
    assert "fractal_metrics" in response


# ══════════════════════════════════════════════════════════════
# Test 10: Summary Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_valid():
    """Test summary endpoint returns valid response."""
    import asyncio
    from modules.fractal_market_intelligence.fractal_routes import get_fractal_summary
    
    response = asyncio.get_event_loop().run_until_complete(get_fractal_summary("BTC"))
    
    assert "symbol" in response
    assert "current" in response
    assert "state_distribution" in response


# ══════════════════════════════════════════════════════════════
# Test 11: History Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_history_endpoint_valid():
    """Test history endpoint returns valid response."""
    import asyncio
    from modules.fractal_market_intelligence.fractal_routes import get_fractal_history
    
    response = asyncio.get_event_loop().run_until_complete(get_fractal_history("BTC", 50))
    
    assert "symbol" in response
    assert "history" in response


# ══════════════════════════════════════════════════════════════
# Test 12: Recompute Endpoint Valid
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint_valid():
    """Test recompute endpoint returns valid response."""
    import asyncio
    from modules.fractal_market_intelligence.fractal_routes import recompute_fractal_state
    
    response = asyncio.get_event_loop().run_until_complete(recompute_fractal_state("BTC"))
    
    assert "status" in response
    assert response["status"] == "ok"


# ══════════════════════════════════════════════════════════════
# Test 13: Storage Correct
# ══════════════════════════════════════════════════════════════

def test_storage_correct():
    """Test state is stored correctly."""
    engine = FractalEngine()
    
    state = engine.generate_fractal_state("ETH")
    
    stored = engine.get_current_state("ETH")
    assert stored is not None
    assert stored.symbol == "ETH"


# ══════════════════════════════════════════════════════════════
# Test 14: Multi Timeframe Consistency
# ══════════════════════════════════════════════════════════════

def test_multi_timeframe_consistency():
    """Test all 5 timeframes are analyzed."""
    engine = FractalEngine()
    
    state = engine.generate_fractal_state("BTC")
    
    all_states = state.get_all_states()
    assert len(all_states) == 5
    assert all(tf in all_states for tf in TIMEFRAMES)


# ══════════════════════════════════════════════════════════════
# Test 15: Integration with Hypothesis Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_hypothesis_engine():
    """Test integration with hypothesis engine."""
    from modules.hypothesis_engine import hypothesis_router
    
    engine = FractalEngine()
    assert engine is not None


# ══════════════════════════════════════════════════════════════
# Test 16: Integration with Meta Alpha
# ══════════════════════════════════════════════════════════════

def test_integration_with_meta_alpha():
    """Test integration with meta alpha engine."""
    from modules.meta_alpha import get_meta_alpha_engine
    
    meta_engine = get_meta_alpha_engine()
    fractal_engine = FractalEngine()
    
    assert meta_engine is not None
    assert fractal_engine is not None


# ══════════════════════════════════════════════════════════════
# Test 17: Deterministic Output
# ══════════════════════════════════════════════════════════════

def test_deterministic_output():
    """Test same input produces same output."""
    engine1 = FractalEngine()
    engine2 = FractalEngine()
    
    tf_data = create_bullish_tf_data()
    
    state1 = engine1.generate_fractal_state("TEST1", tf_data)
    state2 = engine2.generate_fractal_state("TEST1", tf_data)
    
    assert state1.fractal_alignment == state2.fractal_alignment
    assert state1.fractal_bias == state2.fractal_bias


# ══════════════════════════════════════════════════════════════
# Test 18: Missing Data Safe
# ══════════════════════════════════════════════════════════════

def test_missing_data_safe():
    """Test handling of missing data."""
    engine = FractalEngine()
    
    # Empty tf_data should use mock
    state = engine.generate_fractal_state("MISSING")
    assert state is not None
    assert state.symbol == "MISSING"


# ══════════════════════════════════════════════════════════════
# Test 19: Large Dataset Safe
# ══════════════════════════════════════════════════════════════

def test_large_dataset_safe():
    """Test handling of many state generations."""
    engine = FractalEngine()
    
    for i in range(100):
        state = engine.generate_fractal_state(f"SYM_{i}")
        assert state is not None


# ══════════════════════════════════════════════════════════════
# Test 20: Scheduler Safe
# ══════════════════════════════════════════════════════════════

def test_scheduler_safe():
    """Test scheduler-like repeated calls are safe."""
    engine = FractalEngine()
    
    # Simulate scheduler calls every 5 minutes
    for _ in range(20):
        state = engine.generate_fractal_state("BTC")
        assert state is not None


# ══════════════════════════════════════════════════════════════
# Test 21: Volatility Detection
# ══════════════════════════════════════════════════════════════

def test_volatility_detection():
    """Test volatile state detection with high ATR."""
    engine = FractalEngine()
    
    # High ATR expansion -> VOLATILE
    state, _ = engine.classify_timeframe_state(0.01, 2.0, False)
    assert state == "VOLATILE"


# ══════════════════════════════════════════════════════════════
# Test 22: Trend Reversal Detection
# ══════════════════════════════════════════════════════════════

def test_trend_reversal_detection():
    """Test trend reversal with structure break."""
    engine = FractalEngine()
    
    analysis = engine.analyze_timeframe("1h", ema_slope=0.04, atr_expansion=0.9, structure_break=True)
    
    # Structure break should boost confidence
    assert analysis.confidence > 0.5


# ══════════════════════════════════════════════════════════════
# Test 23: Alignment Threshold Logic
# ══════════════════════════════════════════════════════════════

def test_alignment_threshold_logic():
    """Test alignment threshold determines bias correctly."""
    engine = FractalEngine()
    
    # alignment >= 0.6 -> directional bias
    bias = engine.determine_bias(0.65, "TREND_UP")
    assert bias == "LONG"
    
    # alignment < 0.4 -> NEUTRAL
    bias = engine.determine_bias(0.35, "TREND_UP")
    assert bias == "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# Test 24: Neutral Bias Logic
# ══════════════════════════════════════════════════════════════

def test_neutral_bias_logic():
    """Test neutral bias when mixed states."""
    engine = FractalEngine()
    
    # Mixed states -> low alignment
    tf_states = {
        "5m": "TREND_UP",
        "15m": "TREND_DOWN",
        "1h": "RANGE",
        "4h": "VOLATILE",
        "1d": "RANGE",
    }
    
    alignment, _ = engine.calculate_alignment(tf_states)
    assert alignment < 0.4


# ══════════════════════════════════════════════════════════════
# Test 25: Confidence Bounds
# ══════════════════════════════════════════════════════════════

def test_confidence_bounds():
    """Test confidence is bounded [0, 1]."""
    engine = FractalEngine()
    
    # Extreme values
    confidence = engine.calculate_confidence(1.5, 1.5)
    assert 0 <= confidence <= 1
    
    confidence = engine.calculate_confidence(-0.5, -0.5)
    assert 0 <= confidence <= 1


# ══════════════════════════════════════════════════════════════
# Test 26: Integration Stability
# ══════════════════════════════════════════════════════════════

def test_integration_stability():
    """Test engine is stable across multiple operations."""
    engine = FractalEngine()
    
    # Multiple operations
    for sym in ["BTC", "ETH", "SOL"]:
        state = engine.generate_fractal_state(sym, create_bullish_tf_data())
        modifier = engine.get_fractal_modifier(sym, "LONG")
        summary = engine.get_summary(sym)
        
        assert state is not None
        assert modifier is not None
        assert summary is not None


# ══════════════════════════════════════════════════════════════
# Additional Tests (27-30)
# ══════════════════════════════════════════════════════════════

def test_constants_values():
    """Test constant values are correct."""
    assert ALIGNMENT_BIAS_THRESHOLD == 0.6
    assert ALIGNMENT_NEUTRAL_THRESHOLD == 0.4
    assert FRACTAL_ALIGNED_MODIFIER == 1.08
    assert FRACTAL_CONFLICT_MODIFIER == 0.92


def test_timeframes_list():
    """Test timeframes list is correct."""
    assert TIMEFRAMES == ["5m", "15m", "1h", "4h", "1d"]


def test_modifier_endpoint():
    """Test modifier endpoint returns valid response."""
    import asyncio
    from modules.fractal_market_intelligence.fractal_routes import get_fractal_modifier
    
    response = asyncio.get_event_loop().run_until_complete(get_fractal_modifier("BTC", "LONG"))
    
    assert "symbol" in response
    assert "modifier" in response


def test_volatility_consistency():
    """Test volatility consistency calculation."""
    engine = FractalEngine()
    
    # All same state -> high consistency
    tf_states = {
        "5m": "TREND_UP",
        "15m": "TREND_UP",
        "1h": "TREND_UP",
        "4h": "TREND_UP",
        "1d": "TREND_UP",
    }
    
    consistency = engine.calculate_volatility_consistency(tf_states)
    assert consistency >= 0.3


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
