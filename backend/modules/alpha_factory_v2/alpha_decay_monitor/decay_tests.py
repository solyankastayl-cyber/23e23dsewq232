"""
Alpha Decay Monitor — Tests

Test suite for decay monitoring.

Required tests (14):
1. alpha_drift calculation
2. decay_rate calculation
3. stable classification
4. decaying classification
5. critical classification
6. keep action
7. reduce action
8. deprecate action
9. modifiers for stable
10. modifiers for decaying
11. modifiers for critical
12. registry write
13. critical endpoint
14. recompute endpoint
"""

import pytest
from datetime import datetime

from modules.alpha_factory_v2.alpha_decay_monitor.decay_types import (
    AlphaDecayState,
    DecayHistoryRecord,
    DecaySummary,
    DRIFT_STABLE_MAX,
    DRIFT_DECAYING_MAX,
    DECAY_RATE_STABLE_MAX,
    DECAY_RATE_DECAYING_MAX,
    MODIFIERS,
)
from modules.alpha_factory_v2.alpha_decay_monitor.decay_engine import (
    AlphaDecayEngine,
    get_alpha_decay_engine,
)
from modules.alpha_factory_v2.alpha_decay_monitor.decay_registry import (
    AlphaDecayRegistry,
    get_alpha_decay_registry,
)
from modules.alpha_factory_v2.alpha_registry import AlphaRegistry


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def decay_engine():
    """Create fresh decay engine."""
    registry = AlphaRegistry()
    return AlphaDecayEngine(registry=registry)


@pytest.fixture
def decay_registry():
    """Create fresh decay registry."""
    return AlphaDecayRegistry()


# ══════════════════════════════════════════════════════════════
# Test 1: Alpha Drift Calculation
# ══════════════════════════════════════════════════════════════

def test_alpha_drift_calculation(decay_engine):
    """Test 1: Alpha drift is calculated correctly."""
    drift = decay_engine.calculate_alpha_drift(0.70, 0.60)
    assert abs(drift - 0.10) < 0.0001
    
    drift2 = decay_engine.calculate_alpha_drift(0.50, 0.70)
    assert abs(drift2 - 0.20) < 0.0001


def test_alpha_drift_zero():
    """Test drift is zero when no change."""
    engine = AlphaDecayEngine()
    drift = engine.calculate_alpha_drift(0.60, 0.60)
    assert drift == 0.0


# ══════════════════════════════════════════════════════════════
# Test 2: Decay Rate Calculation
# ══════════════════════════════════════════════════════════════

def test_decay_rate_calculation(decay_engine):
    """Test 2: Decay rate is calculated correctly."""
    # Alpha dropped from 0.80 to 0.60
    rate = decay_engine.calculate_decay_rate(0.60, 0.80)
    assert abs(rate - 0.25) < 0.0001


def test_decay_rate_improving():
    """Test decay rate is 0 when alpha improves."""
    engine = AlphaDecayEngine()
    rate = engine.calculate_decay_rate(0.70, 0.60)  # Improved
    assert rate == 0.0


def test_decay_rate_zero_previous():
    """Test decay rate handles zero previous score."""
    engine = AlphaDecayEngine()
    rate = engine.calculate_decay_rate(0.50, 0.0)
    assert rate == 0.0


# ══════════════════════════════════════════════════════════════
# Test 3: Stable Classification
# ══════════════════════════════════════════════════════════════

def test_stable_classification(decay_engine):
    """Test 3: STABLE classification when drift and rate are low."""
    state = decay_engine.classify_decay_state(
        alpha_drift=0.05,
        decay_rate=0.05,
    )
    assert state == "STABLE"


def test_stable_boundary():
    """Test STABLE at boundary."""
    engine = AlphaDecayEngine()
    state = engine.classify_decay_state(0.09, 0.09)
    assert state == "STABLE"


# ══════════════════════════════════════════════════════════════
# Test 4: Decaying Classification
# ══════════════════════════════════════════════════════════════

def test_decaying_classification_drift(decay_engine):
    """Test 4: DECAYING classification when drift is elevated."""
    state = decay_engine.classify_decay_state(
        alpha_drift=0.15,  # 0.10 ≤ x < 0.20
        decay_rate=0.05,
    )
    assert state == "DECAYING"


def test_decaying_classification_rate():
    """Test DECAYING when decay rate is elevated."""
    engine = AlphaDecayEngine()
    state = engine.classify_decay_state(0.05, 0.20)  # 0.10 ≤ x < 0.25
    assert state == "DECAYING"


# ══════════════════════════════════════════════════════════════
# Test 5: Critical Classification
# ══════════════════════════════════════════════════════════════

def test_critical_classification_drift(decay_engine):
    """Test 5: CRITICAL classification when drift is high."""
    state = decay_engine.classify_decay_state(
        alpha_drift=0.25,  # ≥ 0.20
        decay_rate=0.05,
    )
    assert state == "CRITICAL"


def test_critical_classification_rate():
    """Test CRITICAL when decay rate is high."""
    engine = AlphaDecayEngine()
    state = engine.classify_decay_state(0.05, 0.30)  # ≥ 0.25
    assert state == "CRITICAL"


# ══════════════════════════════════════════════════════════════
# Test 6: Keep Action
# ══════════════════════════════════════════════════════════════

def test_keep_action(decay_engine):
    """Test 6: KEEP action for STABLE state."""
    action = decay_engine.get_recommended_action("STABLE")
    assert action == "KEEP"


# ══════════════════════════════════════════════════════════════
# Test 7: Reduce Action
# ══════════════════════════════════════════════════════════════

def test_reduce_action(decay_engine):
    """Test 7: REDUCE action for DECAYING state."""
    action = decay_engine.get_recommended_action("DECAYING")
    assert action == "REDUCE"


# ══════════════════════════════════════════════════════════════
# Test 8: Deprecate Action
# ══════════════════════════════════════════════════════════════

def test_deprecate_action(decay_engine):
    """Test 8: DEPRECATE action for CRITICAL state."""
    action = decay_engine.get_recommended_action("CRITICAL")
    assert action == "DEPRECATE"


# ══════════════════════════════════════════════════════════════
# Test 9: Modifiers for Stable
# ══════════════════════════════════════════════════════════════

def test_modifiers_stable(decay_engine):
    """Test 9: Modifiers for STABLE state are 1.0."""
    mods = decay_engine.get_modifiers("STABLE")
    assert mods["confidence_modifier"] == 1.00
    assert mods["capital_modifier"] == 1.00


# ══════════════════════════════════════════════════════════════
# Test 10: Modifiers for Decaying
# ══════════════════════════════════════════════════════════════

def test_modifiers_decaying(decay_engine):
    """Test 10: Modifiers for DECAYING state are reduced."""
    mods = decay_engine.get_modifiers("DECAYING")
    assert mods["confidence_modifier"] == 0.90
    assert mods["capital_modifier"] == 0.85


# ══════════════════════════════════════════════════════════════
# Test 11: Modifiers for Critical
# ══════════════════════════════════════════════════════════════

def test_modifiers_critical(decay_engine):
    """Test 11: Modifiers for CRITICAL state are heavily reduced."""
    mods = decay_engine.get_modifiers("CRITICAL")
    assert mods["confidence_modifier"] == 0.70
    assert mods["capital_modifier"] == 0.50


# ══════════════════════════════════════════════════════════════
# Test 12: Registry Write
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_write(decay_registry, decay_engine):
    """Test 12: Decay state can be stored in registry."""
    state = decay_engine.analyze_factor(
        factor_id="test_factor",
        factor_name="Test Factor",
        current_score=0.55,
        previous_score=0.70,
    )
    
    record = await decay_registry.store_decay_state(state)
    
    assert record.factor_id == "test_factor"
    assert record.decay_state == state.decay_state


@pytest.mark.asyncio
async def test_registry_history(decay_registry, decay_engine):
    """Test registry can retrieve history."""
    state = decay_engine.analyze_factor(
        factor_id="test_factor_2",
        factor_name="Test Factor 2",
        current_score=0.40,
        previous_score=0.60,
    )
    
    await decay_registry.store_decay_state(state)
    history = await decay_registry.get_factor_history("test_factor_2")
    
    assert len(history) >= 1
    assert history[0].factor_id == "test_factor_2"


# ══════════════════════════════════════════════════════════════
# Test 13: Critical Endpoint
# ══════════════════════════════════════════════════════════════

def test_critical_factors_retrieval(decay_engine):
    """Test 13: Critical factors can be retrieved."""
    # Manually add some decay states
    stable_state = decay_engine.analyze_factor("stable_1", "Stable", 0.65, 0.66)
    critical_state = decay_engine.analyze_factor("critical_1", "Critical", 0.40, 0.80)
    
    decay_engine._decay_states["stable_1"] = stable_state
    decay_engine._decay_states["critical_1"] = critical_state
    
    critical = decay_engine.get_critical_factors()
    
    assert len(critical) >= 1
    assert any(s.factor_id == "critical_1" for s in critical)


# ══════════════════════════════════════════════════════════════
# Test 14: Recompute Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recompute_decay(decay_engine):
    """Test 14: Decay can be recomputed."""
    # Empty registry means no factors
    states = await decay_engine.recompute_decay()
    
    # Should return empty list for empty registry
    assert isinstance(states, list)


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_constants():
    """Test all constants are correct."""
    assert DRIFT_STABLE_MAX == 0.10
    assert DRIFT_DECAYING_MAX == 0.20
    assert DECAY_RATE_STABLE_MAX == 0.10
    assert DECAY_RATE_DECAYING_MAX == 0.25


def test_modifiers_constant():
    """Test modifiers constant structure."""
    assert "STABLE" in MODIFIERS
    assert "DECAYING" in MODIFIERS
    assert "CRITICAL" in MODIFIERS


def test_analyze_factor_full(decay_engine):
    """Test full factor analysis."""
    state = decay_engine.analyze_factor(
        factor_id="funding_rate_15",
        factor_name="Funding Rate 15",
        current_score=0.54,
        previous_score=0.71,
    )
    
    assert state.factor_id == "funding_rate_15"
    assert state.decay_state in ["STABLE", "DECAYING", "CRITICAL"]
    assert state.recommended_action in ["KEEP", "REDUCE", "DEPRECATE"]
    assert 0.0 <= state.confidence_modifier <= 1.0
    assert 0.0 <= state.capital_modifier <= 1.0
    assert len(state.reason) > 0


def test_summary(decay_engine):
    """Test summary generation."""
    summary = decay_engine.get_summary()
    
    assert isinstance(summary, DecaySummary)
    assert summary.total_factors >= 0


def test_singleton_pattern():
    """Test singleton pattern for engine."""
    engine1 = get_alpha_decay_engine()
    engine2 = get_alpha_decay_engine()
    assert engine1 is engine2


def test_reason_generation(decay_engine):
    """Test reason generation for each state."""
    reason_stable = decay_engine.generate_reason("STABLE", 0.05, 0.05)
    assert "stable" in reason_stable.lower()
    
    reason_decaying = decay_engine.generate_reason("DECAYING", 0.15, 0.15)
    assert "losing" in reason_decaying.lower() or "approaching" in reason_decaying.lower()
    
    reason_critical = decay_engine.generate_reason("CRITICAL", 0.25, 0.30)
    assert "critical" in reason_critical.lower()


def test_decay_state_model():
    """Test AlphaDecayState model structure."""
    state = AlphaDecayState(
        factor_id="test",
        factor_name="Test",
        current_alpha_score=0.54,
        previous_alpha_score=0.71,
        alpha_drift=0.17,
        decay_rate=0.24,
        decay_state="DECAYING",
        recommended_action="REDUCE",
        confidence_modifier=0.90,
        capital_modifier=0.85,
        reason="test reason",
    )
    
    assert state.factor_id == "test"
    assert state.decay_state == "DECAYING"
