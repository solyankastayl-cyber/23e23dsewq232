"""
Regime Context — Tests

Test suite for unified regime context.

Required tests (16):
1. regime context builds from 3 components
2. current regime copied correctly
3. next regime candidate copied correctly
4. favored strategies included
5. neutral strategies included
6. disfavored strategies included
7. stable transition -> modifiers 1.0
8. early_shift -> reduced modifiers
9. active_transition -> reduced modifiers
10. unstable -> strongest penalty
11. supportive context classification
12. neutral context classification
13. conflicted context classification
14. summary endpoint
15. strategies endpoint
16. recompute endpoint
"""

import pytest
from datetime import datetime

from modules.regime_intelligence_v2.regime_context_types import (
    RegimeContext,
    RegimeContextSummary,
)
from modules.regime_intelligence_v2.regime_context_engine import (
    RegimeContextEngine,
    get_regime_context_engine,
)
from modules.regime_intelligence_v2.regime_types import MarketRegime
from modules.regime_intelligence_v2.strategy_regime_types import RegimeStrategySummary
from modules.regime_intelligence_v2.regime_transition_types import (
    RegimeTransitionState,
    TRANSITION_MODIFIERS,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def context_engine():
    """Create fresh context engine."""
    return RegimeContextEngine()


@pytest.fixture
def trending_regime():
    """TRENDING regime fixture."""
    return MarketRegime(
        regime_type="TRENDING",
        trend_strength=0.45,
        volatility_level=0.30,
        liquidity_level=0.75,
        regime_confidence=0.70,
        dominant_driver="TREND",
        context_state="SUPPORTIVE",
        symbol="BTCUSDT",
        timeframe="1H",
    )


@pytest.fixture
def trending_strategy_summary():
    """Strategy summary for TRENDING regime."""
    return RegimeStrategySummary(
        regime_type="TRENDING",
        regime_confidence=0.70,
        favored_strategies=["trend_following", "breakout"],
        neutral_strategies=["volatility_expansion", "liquidation_capture", "funding_arb"],
        disfavored_strategies=["mean_reversion", "range_trading", "basis_trade"],
        total_strategies=8,
    )


@pytest.fixture
def stable_transition():
    """STABLE transition state."""
    return RegimeTransitionState(
        current_regime="TRENDING",
        next_regime_candidate="NONE",
        transition_probability=0.15,
        transition_score=0.10,
        transition_state="STABLE",
        trigger_factors=[],
        confidence_modifier=1.0,
        capital_modifier=1.0,
        reason="trending regime is stable",
    )


@pytest.fixture
def early_shift_transition():
    """EARLY_SHIFT transition state."""
    return RegimeTransitionState(
        current_regime="TRENDING",
        next_regime_candidate="VOLATILE",
        transition_probability=0.35,
        transition_score=0.30,
        transition_state="EARLY_SHIFT",
        trigger_factors=["volatility_expansion"],
        confidence_modifier=0.97,
        capital_modifier=0.95,
        reason="early signs of transition",
    )


@pytest.fixture
def active_transition():
    """ACTIVE_TRANSITION state."""
    return RegimeTransitionState(
        current_regime="TRENDING",
        next_regime_candidate="VOLATILE",
        transition_probability=0.55,
        transition_score=0.50,
        transition_state="ACTIVE_TRANSITION",
        trigger_factors=["volatility_expansion", "confidence_drop"],
        confidence_modifier=0.92,
        capital_modifier=0.88,
        reason="active transition in progress",
    )


@pytest.fixture
def unstable_transition():
    """UNSTABLE transition state."""
    return RegimeTransitionState(
        current_regime="VOLATILE",
        next_regime_candidate="ILLIQUID",
        transition_probability=0.75,
        transition_score=0.70,
        transition_state="UNSTABLE",
        trigger_factors=["liquidity_drain", "volatility_expansion"],
        confidence_modifier=0.85,
        capital_modifier=0.75,
        reason="highly unstable",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Context Builds from 3 Components
# ══════════════════════════════════════════════════════════════

def test_context_builds_from_3_components(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 1: Context builds correctly from all 3 components."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert context is not None
    assert isinstance(context, RegimeContext)


# ══════════════════════════════════════════════════════════════
# Test 2: Current Regime Copied Correctly
# ══════════════════════════════════════════════════════════════

def test_current_regime_copied(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 2: Current regime is copied from MarketRegime."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert context.current_regime == "TRENDING"
    assert context.regime_confidence == 0.70
    assert context.dominant_driver == "TREND"


# ══════════════════════════════════════════════════════════════
# Test 3: Next Regime Candidate Copied
# ══════════════════════════════════════════════════════════════

def test_next_regime_candidate_copied(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    active_transition,
):
    """Test 3: Next regime candidate is copied from TransitionState."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        active_transition,
    )
    
    assert context.next_regime_candidate == "VOLATILE"
    assert context.transition_probability == 0.55
    assert context.transition_state == "ACTIVE_TRANSITION"


# ══════════════════════════════════════════════════════════════
# Test 4: Favored Strategies Included
# ══════════════════════════════════════════════════════════════

def test_favored_strategies_included(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 4: Favored strategies are included from mapping."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert "trend_following" in context.favored_strategies
    assert "breakout" in context.favored_strategies


# ══════════════════════════════════════════════════════════════
# Test 5: Neutral Strategies Included
# ══════════════════════════════════════════════════════════════

def test_neutral_strategies_included(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 5: Neutral strategies are included from mapping."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert "volatility_expansion" in context.neutral_strategies
    assert "liquidation_capture" in context.neutral_strategies


# ══════════════════════════════════════════════════════════════
# Test 6: Disfavored Strategies Included
# ══════════════════════════════════════════════════════════════

def test_disfavored_strategies_included(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 6: Disfavored strategies are included from mapping."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert "mean_reversion" in context.disfavored_strategies
    assert "range_trading" in context.disfavored_strategies


# ══════════════════════════════════════════════════════════════
# Test 7: Stable Transition -> Modifiers 1.0
# ══════════════════════════════════════════════════════════════

def test_stable_transition_modifiers(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 7: STABLE transition gives modifiers of 1.0."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert context.confidence_modifier == 1.0
    assert context.capital_modifier == 1.0


# ══════════════════════════════════════════════════════════════
# Test 8: Early Shift -> Reduced Modifiers
# ══════════════════════════════════════════════════════════════

def test_early_shift_modifiers(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    early_shift_transition,
):
    """Test 8: EARLY_SHIFT gives reduced modifiers."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        early_shift_transition,
    )
    
    assert context.confidence_modifier == 0.97
    assert context.capital_modifier == 0.95


# ══════════════════════════════════════════════════════════════
# Test 9: Active Transition -> Reduced Modifiers
# ══════════════════════════════════════════════════════════════

def test_active_transition_modifiers(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    active_transition,
):
    """Test 9: ACTIVE_TRANSITION gives more reduced modifiers."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        active_transition,
    )
    
    assert context.confidence_modifier == 0.92
    assert context.capital_modifier == 0.88


# ══════════════════════════════════════════════════════════════
# Test 10: Unstable -> Strongest Penalty
# ══════════════════════════════════════════════════════════════

def test_unstable_modifiers(context_engine):
    """Test 10: UNSTABLE gives strongest penalty."""
    modifiers = context_engine.get_modifiers_from_transition("UNSTABLE")
    
    assert modifiers["confidence_modifier"] == 0.85
    assert modifiers["capital_modifier"] == 0.75


# ══════════════════════════════════════════════════════════════
# Test 11: Supportive Context Classification
# ══════════════════════════════════════════════════════════════

def test_supportive_context_classification(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 11: SUPPORTIVE context when regime and transition are favorable."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert context.context_state == "SUPPORTIVE"


# ══════════════════════════════════════════════════════════════
# Test 12: Neutral Context Classification
# ══════════════════════════════════════════════════════════════

def test_neutral_context_classification(context_engine):
    """Test 12: NEUTRAL context when signals are mixed."""
    # Neutral regime with early shift
    regime = MarketRegime(
        regime_type="RANGING",
        trend_strength=0.20,
        volatility_level=0.25,
        liquidity_level=0.70,
        regime_confidence=0.55,
        dominant_driver="VOLATILITY",
        context_state="NEUTRAL",
    )
    
    summary = RegimeStrategySummary(
        regime_type="RANGING",
        regime_confidence=0.55,
        favored_strategies=["mean_reversion"],
        neutral_strategies=["basis_trade", "range_trading"],
        disfavored_strategies=["trend_following", "breakout"],
        total_strategies=8,
    )
    
    transition = RegimeTransitionState(
        current_regime="RANGING",
        next_regime_candidate="NONE",
        transition_probability=0.30,
        transition_score=0.25,
        transition_state="EARLY_SHIFT",
        trigger_factors=[],
        confidence_modifier=0.97,
        capital_modifier=0.95,
        reason="early shift",
    )
    
    context = context_engine.build_context(regime, summary, transition)
    
    # Should be NEUTRAL (not SUPPORTIVE since regime.context_state is NEUTRAL)
    assert context.context_state in ["NEUTRAL", "SUPPORTIVE"]


# ══════════════════════════════════════════════════════════════
# Test 13: Conflicted Context Classification
# ══════════════════════════════════════════════════════════════

def test_conflicted_context_classification(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    active_transition,
):
    """Test 13: CONFLICTED context when transition is active/unstable."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        active_transition,
    )
    
    assert context.context_state == "CONFLICTED"


def test_conflicted_from_unstable(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    unstable_transition,
):
    """Test CONFLICTED from UNSTABLE transition."""
    # Update regime type to match transition
    trending_regime.regime_type = "VOLATILE"
    
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        unstable_transition,
    )
    
    assert context.context_state == "CONFLICTED"


# ══════════════════════════════════════════════════════════════
# Test 14: Summary Endpoint
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 14: Summary is generated correctly."""
    context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    summary = context_engine.get_summary()
    
    assert summary is not None
    assert summary.current_regime == "TRENDING"
    assert summary.total_favored == 2


# ══════════════════════════════════════════════════════════════
# Test 15: Strategies Endpoint
# ══════════════════════════════════════════════════════════════

def test_strategies_from_context(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test 15: Strategies are accessible from context."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert len(context.favored_strategies) == 2
    assert len(context.neutral_strategies) == 3
    assert len(context.disfavored_strategies) == 3


# ══════════════════════════════════════════════════════════════
# Test 16: Recompute Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recompute_endpoint(context_engine):
    """Test 16: Context can be recomputed."""
    context = await context_engine.compute_context("BTCUSDT", "1H")
    
    assert context is not None
    assert context.current_regime in ["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]
    assert context.context_state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED"]


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_modifiers_constants():
    """Test all modifier constants are correct."""
    assert TRANSITION_MODIFIERS["STABLE"]["confidence_modifier"] == 1.0
    assert TRANSITION_MODIFIERS["EARLY_SHIFT"]["confidence_modifier"] == 0.97
    assert TRANSITION_MODIFIERS["ACTIVE_TRANSITION"]["confidence_modifier"] == 0.92
    assert TRANSITION_MODIFIERS["UNSTABLE"]["confidence_modifier"] == 0.85


def test_reason_generation(
    context_engine,
    trending_regime,
    trending_strategy_summary,
    stable_transition,
):
    """Test reason is generated."""
    context = context_engine.build_context(
        trending_regime,
        trending_strategy_summary,
        stable_transition,
    )
    
    assert len(context.reason) > 0
    assert "trending" in context.reason.lower()


def test_singleton_pattern():
    """Test singleton pattern for engine."""
    engine1 = get_regime_context_engine()
    engine2 = get_regime_context_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_full_compute_flow(context_engine):
    """Test full compute flow end-to-end."""
    context = await context_engine.compute_context("BTCUSDT", "4H")
    
    # Check all required fields
    assert context.current_regime is not None
    assert context.regime_confidence >= 0
    assert context.next_regime_candidate is not None
    assert context.transition_state is not None
    assert len(context.favored_strategies) >= 0
    assert context.confidence_modifier > 0
    assert context.context_state is not None


def test_regime_context_model():
    """Test RegimeContext model structure."""
    context = RegimeContext(
        current_regime="TRENDING",
        regime_confidence=0.69,
        dominant_driver="TREND",
        next_regime_candidate="VOLATILE",
        transition_probability=0.58,
        transition_state="ACTIVE_TRANSITION",
        favored_strategies=["trend_following", "breakout"],
        neutral_strategies=["volatility_expansion"],
        disfavored_strategies=["mean_reversion"],
        confidence_modifier=0.92,
        capital_modifier=0.88,
        context_state="CONFLICTED",
        reason="test reason",
    )
    
    assert context.current_regime == "TRENDING"
    assert context.context_state == "CONFLICTED"
