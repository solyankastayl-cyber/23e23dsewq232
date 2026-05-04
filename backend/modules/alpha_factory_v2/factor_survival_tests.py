"""
PHASE 26.3 — Factor Survival Engine Tests

Test suite for survival filtering.

Required tests (16):
1. survival threshold correct
2. factor becomes ACTIVE
3. factor becomes DEPRECATED
4. sharpe filter works
5. stability filter works
6. drawdown filter works
7. overfit cap works
8. strongest factor detection
9. weakest factor detection
10. average score calculation
11. survival summary endpoint
12. active endpoint
13. deprecated endpoint
14. empty list handling
15. duplicate factor protection
16. integration with scoring engine
"""

import pytest
from datetime import datetime

from modules.alpha_factory_v2.factor_survival_engine import (
    FactorSurvivalEngine,
    get_factor_survival_engine,
    SurvivalSummary,
    ALPHA_THRESHOLD,
    SHARPE_THRESHOLD,
    STABILITY_THRESHOLD,
    DRAWDOWN_THRESHOLD,
    OVERFIT_CAP,
)
from modules.alpha_factory_v2.factor_discovery_engine import FactorDiscoveryEngine
from modules.alpha_factory_v2.alpha_scoring_engine import AlphaScoringEngine
from modules.alpha_factory_v2.factor_types import AlphaFactor


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def survival_engine():
    """Create fresh survival engine instance."""
    return FactorSurvivalEngine()


@pytest.fixture
def discovery_engine():
    """Create fresh discovery engine instance."""
    return FactorDiscoveryEngine()


@pytest.fixture
def scoring_engine():
    """Create fresh scoring engine instance."""
    return AlphaScoringEngine()


@pytest.fixture
def strong_factor():
    """Create a factor that should survive."""
    return AlphaFactor(
        factor_id="strong_001",
        name="strong_momentum",
        category="TA",
        lookback=14,
        signal_strength=0.70,
        sharpe_score=0.65,
        stability_score=0.60,
        drawdown_score=0.55,
        alpha_score=0.64,  # Above threshold
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )


@pytest.fixture
def weak_factor():
    """Create a factor that should be deprecated."""
    return AlphaFactor(
        factor_id="weak_001",
        name="weak_signal",
        category="TA",
        lookback=14,
        signal_strength=0.30,
        sharpe_score=0.25,
        stability_score=0.35,
        drawdown_score=0.40,
        alpha_score=0.32,  # Below threshold
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )


@pytest.fixture
def low_sharpe_factor():
    """Create a factor with low sharpe (should fail sharpe filter)."""
    return AlphaFactor(
        factor_id="low_sharpe_001",
        name="low_sharpe",
        category="TA",
        lookback=14,
        signal_strength=0.70,
        sharpe_score=0.30,  # Below sharpe threshold
        stability_score=0.60,
        drawdown_score=0.55,
        alpha_score=0.57,  # Above alpha threshold
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )


@pytest.fixture
def low_stability_factor():
    """Create a factor with low stability."""
    return AlphaFactor(
        factor_id="low_stability_001",
        name="low_stability",
        category="TA",
        lookback=14,
        signal_strength=0.70,
        sharpe_score=0.50,
        stability_score=0.25,  # Below stability threshold
        drawdown_score=0.55,
        alpha_score=0.56,
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )


@pytest.fixture
def low_drawdown_factor():
    """Create a factor with low drawdown score."""
    return AlphaFactor(
        factor_id="low_dd_001",
        name="low_drawdown",
        category="TA",
        lookback=14,
        signal_strength=0.70,
        sharpe_score=0.50,
        stability_score=0.50,
        drawdown_score=0.20,  # Below drawdown threshold
        alpha_score=0.56,
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )


@pytest.fixture
def overfit_factor():
    """Create a factor with suspiciously high alpha (overfit)."""
    return AlphaFactor(
        factor_id="overfit_001",
        name="overfit_signal",
        category="TA",
        lookback=14,
        signal_strength=0.95,
        sharpe_score=0.90,
        stability_score=0.85,
        drawdown_score=0.80,
        alpha_score=0.90,  # Above overfit cap
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Survival Threshold Correct
# ══════════════════════════════════════════════════════════════

def test_survival_threshold_correct():
    """Test 1: Verify survival threshold is 0.55."""
    assert ALPHA_THRESHOLD == 0.55


# ══════════════════════════════════════════════════════════════
# Test 2: Factor Becomes ACTIVE
# ══════════════════════════════════════════════════════════════

def test_factor_becomes_active(survival_engine, strong_factor):
    """Test 2: Strong factor becomes ACTIVE."""
    factors = survival_engine.apply_survival([strong_factor])
    
    assert len(factors) == 1
    assert factors[0].status == "ACTIVE"


# ══════════════════════════════════════════════════════════════
# Test 3: Factor Becomes DEPRECATED
# ══════════════════════════════════════════════════════════════

def test_factor_becomes_deprecated(survival_engine, weak_factor):
    """Test 3: Weak factor becomes DEPRECATED."""
    factors = survival_engine.apply_survival([weak_factor])
    
    assert len(factors) == 1
    assert factors[0].status == "DEPRECATED"


# ══════════════════════════════════════════════════════════════
# Test 4: Sharpe Filter Works
# ══════════════════════════════════════════════════════════════

def test_sharpe_filter_works(survival_engine, low_sharpe_factor):
    """Test 4: Factor with low sharpe is deprecated despite good alpha."""
    factors = survival_engine.apply_survival([low_sharpe_factor])
    
    assert factors[0].status == "DEPRECATED"
    
    summary = survival_engine.get_summary()
    assert summary.failed_sharpe_filter >= 1


# ══════════════════════════════════════════════════════════════
# Test 5: Stability Filter Works
# ══════════════════════════════════════════════════════════════

def test_stability_filter_works(survival_engine, low_stability_factor):
    """Test 5: Factor with low stability is deprecated."""
    factors = survival_engine.apply_survival([low_stability_factor])
    
    assert factors[0].status == "DEPRECATED"
    
    summary = survival_engine.get_summary()
    assert summary.failed_stability_filter >= 1


# ══════════════════════════════════════════════════════════════
# Test 6: Drawdown Filter Works
# ══════════════════════════════════════════════════════════════

def test_drawdown_filter_works(survival_engine, low_drawdown_factor):
    """Test 6: Factor with low drawdown score is deprecated."""
    factors = survival_engine.apply_survival([low_drawdown_factor])
    
    assert factors[0].status == "DEPRECATED"
    
    summary = survival_engine.get_summary()
    assert summary.failed_drawdown_filter >= 1


# ══════════════════════════════════════════════════════════════
# Test 7: Overfit Cap Works
# ══════════════════════════════════════════════════════════════

def test_overfit_cap_works(survival_engine, overfit_factor):
    """Test 7: Overfit factor gets capped at 0.85."""
    factors = survival_engine.apply_survival([overfit_factor])
    
    # Alpha should be capped
    assert factors[0].alpha_score <= OVERFIT_CAP
    assert factors[0].alpha_score == OVERFIT_CAP


# ══════════════════════════════════════════════════════════════
# Test 8: Strongest Factor Detection
# ══════════════════════════════════════════════════════════════

def test_strongest_factor_detection(survival_engine, strong_factor, weak_factor):
    """Test 8: Strongest factor is detected correctly."""
    factors = survival_engine.apply_survival([strong_factor, weak_factor])
    
    strongest = survival_engine.get_strongest_factor()
    assert strongest is not None
    assert strongest.name == "strong_momentum"


# ══════════════════════════════════════════════════════════════
# Test 9: Weakest Factor Detection
# ══════════════════════════════════════════════════════════════

def test_weakest_factor_detection(survival_engine, strong_factor, weak_factor):
    """Test 9: Weakest factor is detected correctly."""
    factors = survival_engine.apply_survival([strong_factor, weak_factor])
    
    weakest = survival_engine.get_weakest_factor()
    assert weakest is not None
    assert weakest.name == "weak_signal"


# ══════════════════════════════════════════════════════════════
# Test 10: Average Score Calculation
# ══════════════════════════════════════════════════════════════

def test_average_score_calculation(survival_engine, strong_factor, weak_factor):
    """Test 10: Average alpha score is calculated correctly."""
    factors = survival_engine.apply_survival([strong_factor, weak_factor])
    
    summary = survival_engine.get_summary()
    expected_avg = (strong_factor.alpha_score + weak_factor.alpha_score) / 2
    
    assert summary.average_alpha_score == pytest.approx(expected_avg, rel=0.01)


# ══════════════════════════════════════════════════════════════
# Test 11: Survival Summary Endpoint
# ══════════════════════════════════════════════════════════════

def test_survival_summary_endpoint(survival_engine, strong_factor, weak_factor):
    """Test 11: Survival summary is generated correctly."""
    survival_engine.apply_survival([strong_factor, weak_factor])
    
    summary = survival_engine.get_summary()
    
    assert isinstance(summary, SurvivalSummary)
    assert summary.total_factors == 2
    assert summary.active_factors == 1
    assert summary.deprecated_factors == 1


# ══════════════════════════════════════════════════════════════
# Test 12: Active Endpoint
# ══════════════════════════════════════════════════════════════

def test_active_endpoint(survival_engine, strong_factor, weak_factor):
    """Test 12: get_active_factors returns only ACTIVE factors."""
    survival_engine.apply_survival([strong_factor, weak_factor])
    
    active = survival_engine.get_active_factors()
    
    assert len(active) == 1
    assert all(f.status == "ACTIVE" for f in active)


# ══════════════════════════════════════════════════════════════
# Test 13: Deprecated Endpoint
# ══════════════════════════════════════════════════════════════

def test_deprecated_endpoint(survival_engine, strong_factor, weak_factor):
    """Test 13: get_deprecated_factors returns only DEPRECATED factors."""
    survival_engine.apply_survival([strong_factor, weak_factor])
    
    deprecated = survival_engine.get_deprecated_factors()
    
    assert len(deprecated) == 1
    assert all(f.status == "DEPRECATED" for f in deprecated)


# ══════════════════════════════════════════════════════════════
# Test 14: Empty List Handling
# ══════════════════════════════════════════════════════════════

def test_empty_list_handling(survival_engine):
    """Test 14: Empty list returns empty result with valid summary."""
    factors = survival_engine.apply_survival([])
    
    assert factors == []
    
    summary = survival_engine.get_summary()
    assert summary.total_factors == 0
    assert summary.active_factors == 0
    assert summary.deprecated_factors == 0


# ══════════════════════════════════════════════════════════════
# Test 15: Duplicate Factor Protection
# ══════════════════════════════════════════════════════════════

def test_duplicate_factor_protection(survival_engine, strong_factor):
    """Test 15: Same factor survives consistently."""
    factors1 = survival_engine.apply_survival([strong_factor])
    factors2 = survival_engine.apply_survival([strong_factor])
    
    assert factors1[0].status == factors2[0].status
    assert factors1[0].alpha_score == factors2[0].alpha_score


# ══════════════════════════════════════════════════════════════
# Test 16: Integration with Scoring Engine
# ══════════════════════════════════════════════════════════════

def test_integration_with_scoring(survival_engine, discovery_engine, scoring_engine):
    """Test 16: Full integration: discover → score → survive."""
    # Discover
    candidates = discovery_engine.discover_all()
    
    # Score
    scored = scoring_engine.score_candidates(candidates)
    
    # Survive
    survived = survival_engine.apply_survival(scored)
    
    # All factors should have final status
    for factor in survived:
        assert factor.status in ["ACTIVE", "DEPRECATED"]
    
    # Should have some active and some deprecated
    summary = survival_engine.get_summary()
    assert summary.total_factors == len(candidates)


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_pattern():
    """Test singleton pattern for survival engine."""
    engine1 = get_factor_survival_engine()
    engine2 = get_factor_survival_engine()
    assert engine1 is engine2


def test_last_survival_timestamp(survival_engine, strong_factor):
    """Test last_survival timestamp is updated."""
    assert survival_engine.last_survival is None
    
    survival_engine.apply_survival([strong_factor])
    
    assert survival_engine.last_survival is not None
    assert isinstance(survival_engine.last_survival, datetime)


def test_threshold_constants():
    """Test threshold constants are correct."""
    assert ALPHA_THRESHOLD == 0.55
    assert SHARPE_THRESHOLD == 0.40
    assert STABILITY_THRESHOLD == 0.35
    assert DRAWDOWN_THRESHOLD == 0.30
    assert OVERFIT_CAP == 0.85


def test_borderline_factor_passes(survival_engine):
    """Test factor exactly at threshold passes."""
    borderline = AlphaFactor(
        factor_id="borderline_001",
        name="borderline",
        category="TA",
        lookback=14,
        signal_strength=0.55,
        sharpe_score=0.40,
        stability_score=0.35,
        drawdown_score=0.30,
        alpha_score=0.55,  # Exactly at threshold
        status="CANDIDATE",
        parameters={},
        source="ta_engine",
    )
    
    factors = survival_engine.apply_survival([borderline])
    assert factors[0].status == "ACTIVE"
