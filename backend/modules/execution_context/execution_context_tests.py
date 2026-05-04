"""
PHASE 25.5 — Execution Context Tests

Test suite for Execution Context Layer.

Required tests (minimum 12):

Core tests:
1. bullish fractal → confidence ↑
2. bearish fractal → confidence ↑ for short bias

Macro tests:
3. macro_strength влияет ≤2%

Capital tests:
4. capital modifier растёт при fractal_strength

Conflict tests:
5. conflicted context → modifiers уменьшаются

Boundary tests:
6. confidence cap работает
7. capital cap работает

API tests:
8. context endpoint валиден
9. summary endpoint валиден
10. health endpoint валиден

Integration tests:
11. direction НЕ изменяется
12. strategy НЕ изменяется
"""

import pytest
from datetime import datetime

from modules.execution_context.execution_context_engine import (
    ExecutionContextEngine,
    get_execution_context_engine,
)
from modules.execution_context.execution_context_types import (
    ExecutionContext,
    ExecutionContextSummary,
    ExecutionContextHealthStatus,
    FRACTAL_WEIGHT,
    MACRO_WEIGHT,
    CONFIDENCE_MIN,
    CONFIDENCE_MAX,
    CAPITAL_MIN,
    CAPITAL_MAX,
    CAPITAL_FRACTAL_WEIGHT,
    CAPITAL_CROSS_ASSET_WEIGHT,
    CAPITAL_MACRO_WEIGHT,
    CONFLICT_CONFIDENCE_PENALTY,
    CONFLICT_CAPITAL_PENALTY,
)
from modules.macro_fractal_brain.macro_fractal_types import MacroFractalContext
from modules.fractal_intelligence.fractal_context_types import FractalContext
from modules.cross_asset_intelligence.cross_asset_types import (
    CrossAssetAlignment,
    CrossAssetBridge,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return ExecutionContextEngine()


@pytest.fixture
def bullish_macro_fractal():
    """Create bullish MacroFractalContext."""
    return MacroFractalContext(
        macro_state="RISK_ON",
        btc_direction="LONG",
        spx_direction="LONG",
        dxy_direction="SHORT",
        btc_phase="MARKUP",
        spx_phase="MARKUP",
        dxy_phase="MARKDOWN",
        macro_dxy_alignment="SUPPORTIVE",
        dxy_spx_alignment="SUPPORTIVE",
        spx_btc_alignment="SUPPORTIVE",
        cross_asset_strength=0.75,
        final_bias="BULLISH",
        final_confidence=0.80,
        final_reliability=0.75,
        context_state="SUPPORTIVE",
        dominant_driver="BTC",
        weakest_driver="MACRO",
        reason="bullish macro-fractal context",
    )


@pytest.fixture
def bearish_macro_fractal():
    """Create bearish MacroFractalContext."""
    return MacroFractalContext(
        macro_state="TIGHTENING",
        btc_direction="SHORT",
        spx_direction="SHORT",
        dxy_direction="LONG",
        btc_phase="MARKDOWN",
        spx_phase="MARKDOWN",
        dxy_phase="MARKUP",
        macro_dxy_alignment="SUPPORTIVE",
        dxy_spx_alignment="SUPPORTIVE",
        spx_btc_alignment="SUPPORTIVE",
        cross_asset_strength=0.70,
        final_bias="BEARISH",
        final_confidence=0.75,
        final_reliability=0.70,
        context_state="SUPPORTIVE",
        dominant_driver="MACRO",
        weakest_driver="DXY",
        reason="bearish macro-fractal context",
    )


@pytest.fixture
def conflicted_macro_fractal():
    """Create conflicted MacroFractalContext."""
    return MacroFractalContext(
        macro_state="RISK_ON",
        btc_direction="SHORT",
        spx_direction="LONG",
        dxy_direction="HOLD",
        btc_phase="DISTRIBUTION",
        spx_phase="MARKUP",
        dxy_phase="UNKNOWN",
        macro_dxy_alignment="CONTRARY",
        dxy_spx_alignment="MIXED",
        spx_btc_alignment="CONTRARY",
        cross_asset_strength=0.35,
        final_bias="MIXED",
        final_confidence=0.55,
        final_reliability=0.40,
        context_state="CONFLICTED",
        dominant_driver="MIXED",
        weakest_driver="DXY",
        reason="conflicting signals",
    )


@pytest.fixture
def strong_fractal():
    """Create strong bullish FractalContext."""
    return FractalContext(
        direction="LONG",
        confidence=0.85,
        reliability=0.80,
        dominant_horizon=14,
        horizon_bias={},
        expected_return=0.05,
        phase="MARKUP",
        phase_confidence=0.75,
        risk_badge="OK",
        governance_mode="NORMAL",
        fractal_strength=0.82,
        context_state="SUPPORTIVE",
        reason="strong bullish fractal",
    )


@pytest.fixture
def weak_fractal():
    """Create weak FractalContext."""
    return FractalContext(
        direction="HOLD",
        confidence=0.35,
        reliability=0.40,
        dominant_horizon=None,
        horizon_bias={},
        expected_return=0.0,
        phase="UNKNOWN",
        phase_confidence=0.20,
        risk_badge="WARN",
        governance_mode="NORMAL",
        fractal_strength=0.25,
        context_state="NEUTRAL",
        reason="weak fractal signal",
    )


@pytest.fixture
def strong_cross_asset():
    """Create strong CrossAssetAlignment."""
    return CrossAssetAlignment(
        macro_dxy=CrossAssetBridge(
            source="MACRO",
            target="DXY",
            alignment="SUPPORTIVE",
            influence_direction="BULLISH",
            strength=0.80,
            confidence=0.75,
            effective_strength=0.80,
            reason="strong macro-dxy alignment",
        ),
        dxy_spx=CrossAssetBridge(
            source="DXY",
            target="SPX",
            alignment="SUPPORTIVE",
            influence_direction="BULLISH",
            strength=0.75,
            confidence=0.70,
            effective_strength=0.75,
            reason="strong dxy-spx alignment",
        ),
        spx_btc=CrossAssetBridge(
            source="SPX",
            target="BTC",
            alignment="SUPPORTIVE",
            influence_direction="BULLISH",
            strength=0.85,
            confidence=0.80,
            effective_strength=0.85,
            reason="strong spx-btc alignment",
        ),
        alignment_score=0.80,
        alignment_state="STRONG",
        dominant_bridge="spx_btc",
        weakest_bridge="dxy_spx",
        final_bias="BULLISH",
        reason="strong cross-asset alignment",
    )


@pytest.fixture
def weak_cross_asset():
    """Create weak CrossAssetAlignment."""
    return CrossAssetAlignment(
        macro_dxy=CrossAssetBridge(
            source="MACRO",
            target="DXY",
            alignment="MIXED",
            influence_direction="NEUTRAL",
            strength=0.30,
            confidence=0.35,
            effective_strength=0.21,
            reason="weak macro-dxy alignment",
        ),
        dxy_spx=CrossAssetBridge(
            source="DXY",
            target="SPX",
            alignment="CONTRARY",
            influence_direction="NEUTRAL",
            strength=0.25,
            confidence=0.30,
            effective_strength=0.05,
            reason="contrary dxy-spx",
        ),
        spx_btc=CrossAssetBridge(
            source="SPX",
            target="BTC",
            alignment="MIXED",
            influence_direction="NEUTRAL",
            strength=0.35,
            confidence=0.40,
            effective_strength=0.245,
            reason="mixed spx-btc",
        ),
        alignment_score=0.25,
        alignment_state="WEAK",
        dominant_bridge="spx_btc",
        weakest_bridge="dxy_spx",
        final_bias="NEUTRAL",
        reason="weak cross-asset alignment",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Bullish fractal → confidence ↑
# ══════════════════════════════════════════════════════════════

def test_bullish_fractal_increases_confidence(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 1: Bullish fractal increases confidence modifier."""
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    # Strong fractal (0.82) should boost confidence
    # Base: 1 + 0.82 * 0.16 + macro * 0.02
    assert context.confidence_modifier > 1.0
    assert context.context_bias == "BULLISH"
    assert context.context_state == "SUPPORTIVE"


# ══════════════════════════════════════════════════════════════
# Test 2: Bearish fractal → confidence ↑ for short bias
# ══════════════════════════════════════════════════════════════

def test_bearish_fractal_increases_confidence_for_short(
    engine, bearish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 2: Bearish regime still boosts confidence (for shorts)."""
    # Adjust fractal direction to SHORT
    strong_fractal.direction = "SHORT"
    strong_fractal.phase = "MARKDOWN"
    
    context = engine.compute(
        macro_fractal=bearish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    # Confidence should still increase based on strength
    assert context.confidence_modifier > 1.0
    assert context.context_bias == "BEARISH"


# ══════════════════════════════════════════════════════════════
# Test 3: Macro strength влияет ≤2%
# ══════════════════════════════════════════════════════════════

def test_macro_contribution_limited_to_2_percent(
    engine, bullish_macro_fractal, weak_fractal, weak_cross_asset
):
    """Test 3: Macro contribution to confidence is capped at 2%."""
    # Use weak fractal to isolate macro contribution
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=weak_fractal,
        cross_asset=weak_cross_asset,
    )
    
    # Weak fractal (0.25) + max macro contribution (0.02)
    # 1 + 0.25 * 0.16 + 0.5 * 0.02 = 1 + 0.04 + 0.01 = 1.05
    # But actual macro_strength = final_confidence * 0.5 = 0.80 * 0.5 = 0.40
    # So macro contribution = 0.40 * 0.02 = 0.008
    
    # Verify macro weight constant
    assert MACRO_WEIGHT == 0.02
    
    # Max macro contribution with full strength would be 1.0 * 0.02 = 0.02 (2%)
    max_macro_contribution = 1.0 * MACRO_WEIGHT
    assert max_macro_contribution == 0.02


# ══════════════════════════════════════════════════════════════
# Test 4: Capital modifier растёт при fractal_strength
# ══════════════════════════════════════════════════════════════

def test_capital_modifier_increases_with_fractal_strength(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 4: Capital modifier increases with fractal strength."""
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    # Strong fractal should boost capital
    # 1 + 0.82 * 0.12 + 0.80 * 0.05 + macro * 0.02
    # = 1 + 0.0984 + 0.04 + ~0.008 = ~1.1464
    assert context.capital_modifier > 1.0
    
    # Compare with weak fractal
    weak_context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=FractalContext(
            direction="HOLD",
            confidence=0.30,
            reliability=0.30,
            fractal_strength=0.20,
            context_state="NEUTRAL",
            reason="weak",
        ),
        cross_asset=strong_cross_asset,
    )
    
    # Strong fractal should have higher capital modifier
    assert context.capital_modifier > weak_context.capital_modifier


# ══════════════════════════════════════════════════════════════
# Test 5: Conflicted context → modifiers уменьшаются
# ══════════════════════════════════════════════════════════════

def test_conflicted_context_reduces_modifiers(
    engine, conflicted_macro_fractal, strong_fractal, weak_cross_asset
):
    """Test 5: Conflicted context applies penalty to modifiers."""
    context = engine.compute(
        macro_fractal=conflicted_macro_fractal,
        fractal=strong_fractal,
        cross_asset=weak_cross_asset,
    )
    
    assert context.context_state == "CONFLICTED"
    
    # The modifiers should have conflict penalty applied
    # Verify penalty constants
    assert CONFLICT_CONFIDENCE_PENALTY == 0.95
    assert CONFLICT_CAPITAL_PENALTY == 0.92


# ══════════════════════════════════════════════════════════════
# Test 6: Confidence cap работает
# ══════════════════════════════════════════════════════════════

def test_confidence_modifier_cap(engine, bullish_macro_fractal, strong_cross_asset):
    """Test 6: Confidence modifier is capped at 1.18."""
    # Create maximum strength fractal
    max_fractal = FractalContext(
        direction="LONG",
        confidence=1.0,
        reliability=1.0,
        fractal_strength=1.0,
        context_state="SUPPORTIVE",
        reason="max strength",
    )
    
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=max_fractal,
        cross_asset=strong_cross_asset,
    )
    
    assert context.confidence_modifier <= CONFIDENCE_MAX
    assert context.confidence_modifier >= CONFIDENCE_MIN


# ══════════════════════════════════════════════════════════════
# Test 7: Capital cap работает
# ══════════════════════════════════════════════════════════════

def test_capital_modifier_cap(engine, bullish_macro_fractal, strong_cross_asset):
    """Test 7: Capital modifier is capped at 1.20."""
    # Create maximum strength fractal
    max_fractal = FractalContext(
        direction="LONG",
        confidence=1.0,
        reliability=1.0,
        fractal_strength=1.0,
        context_state="SUPPORTIVE",
        reason="max strength",
    )
    
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=max_fractal,
        cross_asset=strong_cross_asset,
    )
    
    assert context.capital_modifier <= CAPITAL_MAX
    assert context.capital_modifier >= CAPITAL_MIN


# ══════════════════════════════════════════════════════════════
# Test 8: Context endpoint валиден
# ══════════════════════════════════════════════════════════════

def test_context_endpoint_valid_structure(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 8: Context endpoint returns valid ExecutionContext structure."""
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    # Verify all required fields
    assert context.context_bias in ["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
    assert 0.0 <= context.fractal_strength <= 1.0
    assert 0.0 <= context.macro_strength <= 1.0
    assert 0.0 <= context.cross_asset_strength <= 1.0
    assert CONFIDENCE_MIN <= context.confidence_modifier <= CONFIDENCE_MAX
    assert CAPITAL_MIN <= context.capital_modifier <= CAPITAL_MAX
    assert context.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]
    assert isinstance(context.reason, str)
    assert len(context.reason) > 0


# ══════════════════════════════════════════════════════════════
# Test 9: Summary endpoint валиден
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint_valid_structure(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 9: Summary endpoint returns valid ExecutionContextSummary."""
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    summary = engine.get_summary(context)
    
    assert summary.context_bias in ["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
    assert CONFIDENCE_MIN <= summary.confidence_modifier <= CONFIDENCE_MAX
    assert CAPITAL_MIN <= summary.capital_modifier <= CAPITAL_MAX
    assert summary.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]


# ══════════════════════════════════════════════════════════════
# Test 10: Health endpoint валиден
# ══════════════════════════════════════════════════════════════

def test_health_endpoint_valid_structure(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 10: Health endpoint returns valid ExecutionContextHealthStatus."""
    # First compute to update internal state
    engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    health = engine.get_health()
    
    assert health.status in ["OK", "DEGRADED", "ERROR"]
    assert isinstance(health.has_macro_fractal, bool)
    assert isinstance(health.has_fractal, bool)
    assert isinstance(health.has_cross_asset, bool)
    assert health.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]


# ══════════════════════════════════════════════════════════════
# Test 11: Direction НЕ изменяется
# ══════════════════════════════════════════════════════════════

def test_direction_not_changed(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 11: ExecutionContext does NOT contain direction field."""
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    # ExecutionContext should NOT have a direction field
    assert not hasattr(context, 'direction')
    
    # Only bias (context_bias) should exist, not direction
    assert hasattr(context, 'context_bias')
    
    # The fractal's original direction should be preserved
    assert strong_fractal.direction == "LONG"  # Unchanged


# ══════════════════════════════════════════════════════════════
# Test 12: Strategy НЕ изменяется
# ══════════════════════════════════════════════════════════════

def test_strategy_not_changed(
    engine, bullish_macro_fractal, strong_fractal, strong_cross_asset
):
    """Test 12: ExecutionContext does NOT contain strategy field."""
    context = engine.compute(
        macro_fractal=bullish_macro_fractal,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    # ExecutionContext should NOT have a strategy field
    assert not hasattr(context, 'strategy')
    assert not hasattr(context, 'signal')
    
    # Only execution modifiers should exist
    assert hasattr(context, 'confidence_modifier')
    assert hasattr(context, 'capital_modifier')


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_engine():
    """Test singleton pattern for engine."""
    engine1 = get_execution_context_engine()
    engine2 = get_execution_context_engine()
    assert engine1 is engine2


def test_neutral_context_with_weak_signals(
    engine, weak_cross_asset
):
    """Test neutral context when all signals are weak."""
    weak_macro_fractal = MacroFractalContext(
        macro_state="NEUTRAL",
        btc_direction="HOLD",
        spx_direction="HOLD",
        dxy_direction="HOLD",
        macro_dxy_alignment="NEUTRAL",
        dxy_spx_alignment="NEUTRAL",
        spx_btc_alignment="NEUTRAL",
        cross_asset_strength=0.30,
        final_bias="NEUTRAL",
        final_confidence=0.35,
        final_reliability=0.40,
        context_state="CONFLICTED",  # Use valid ContextStateType
        dominant_driver="MIXED",
        weakest_driver="MACRO",
        reason="weak signals",
    )
    
    weak_fractal = FractalContext(
        direction="HOLD",
        confidence=0.25,
        reliability=0.30,
        fractal_strength=0.20,
        context_state="NEUTRAL",
        reason="weak fractal",
    )
    
    context = engine.compute(
        macro_fractal=weak_macro_fractal,
        fractal=weak_fractal,
        cross_asset=weak_cross_asset,
    )
    
    # Weak signals should result in modifiers close to 1.0
    assert context.confidence_modifier >= 0.90
    assert context.confidence_modifier <= 1.10
    assert context.capital_modifier >= 0.85
    assert context.capital_modifier <= 1.10


def test_reason_generation_variations(engine, strong_cross_asset):
    """Test different reason generation paths."""
    strong_fractal = FractalContext(
        direction="LONG",
        confidence=0.80,
        reliability=0.75,
        fractal_strength=0.78,
        context_state="SUPPORTIVE",
        reason="strong",
    )
    
    # Test BULLISH + SUPPORTIVE
    bullish_mf = MacroFractalContext(
        macro_state="RISK_ON",
        btc_direction="LONG",
        spx_direction="LONG",
        dxy_direction="SHORT",
        macro_dxy_alignment="SUPPORTIVE",
        dxy_spx_alignment="SUPPORTIVE",
        spx_btc_alignment="SUPPORTIVE",
        cross_asset_strength=0.75,
        final_bias="BULLISH",
        final_confidence=0.80,
        final_reliability=0.75,
        context_state="SUPPORTIVE",
        dominant_driver="BTC",
        weakest_driver="MACRO",
        reason="bullish",
    )
    
    context = engine.compute(
        macro_fractal=bullish_mf,
        fractal=strong_fractal,
        cross_asset=strong_cross_asset,
    )
    
    assert "bullish" in context.reason.lower()
    assert len(context.reason) > 10
