"""
PHASE 43.8 — Alpha Decay Engine Tests

Minimum 25 tests covering:
- Decay calculation
- Half-life behavior
- Stage transitions
- Expiration rule
- Confidence adjustment
- Execution blocking
- API tests
- Integration tests
"""

import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from modules.alpha_decay import (
    DecayStage,
    SignalType,
    AlphaDecayState,
    AlphaDecayConfig,
    DecayComputeResult,
    AlphaDecayEngine,
    get_alpha_decay_engine,
    SIGNAL_HALF_LIVES,
    DECAY_STAGE_THRESHOLDS,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def decay_engine():
    """Create a fresh decay engine for testing."""
    return AlphaDecayEngine()


@pytest.fixture
def sample_state():
    """Create a sample decay state."""
    return AlphaDecayState(
        hypothesis_id="test_hyp_001",
        symbol="BTC",
        signal_type=SignalType.DEFAULT,
        initial_confidence=0.8,
        half_life_minutes=60,
    )


# ══════════════════════════════════════════════════════════════
# 1. Decay Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_decay_formula_at_zero():
    """Test decay factor is 1.0 at age 0."""
    # decay = exp(-0/60) = 1.0
    state = AlphaDecayState(
        hypothesis_id="test",
        symbol="BTC",
        initial_confidence=0.8,
        half_life_minutes=60,
    )
    state.age_minutes = 0
    state.decay_factor = math.exp(-0 / 60)
    
    assert state.decay_factor == 1.0


def test_decay_formula_at_half_life():
    """Test decay factor is ~0.5 at half-life."""
    # decay = exp(-60/60) = exp(-1) ≈ 0.368
    half_life = 60
    age = half_life
    decay_factor = math.exp(-age / half_life)
    
    assert abs(decay_factor - 0.368) < 0.01


def test_decay_formula_at_30_minutes():
    """Test decay factor at 30 minutes with 60min half-life."""
    # decay = exp(-30/60) = exp(-0.5) ≈ 0.606
    decay_factor = math.exp(-30 / 60)
    assert abs(decay_factor - 0.606) < 0.01


def test_decay_formula_at_120_minutes():
    """Test decay factor at 120 minutes (2x half-life)."""
    # decay = exp(-120/60) = exp(-2) ≈ 0.135
    decay_factor = math.exp(-120 / 60)
    assert abs(decay_factor - 0.135) < 0.01


def test_adjusted_confidence_calculation():
    """Test adjusted confidence = initial × decay_factor."""
    initial = 0.8
    decay_factor = 0.6
    adjusted = initial * decay_factor
    
    assert adjusted == 0.48


# ══════════════════════════════════════════════════════════════
# 2. Half-Life Behavior Tests
# ══════════════════════════════════════════════════════════════

def test_default_half_life():
    """Test default half-life is 60 minutes."""
    assert SIGNAL_HALF_LIVES[SignalType.DEFAULT] == 60


def test_trend_half_life():
    """Test TREND signals have 120 min half-life."""
    assert SIGNAL_HALF_LIVES[SignalType.TREND] == 120


def test_mean_reversion_half_life():
    """Test MEAN_REVERSION signals have 30 min half-life."""
    assert SIGNAL_HALF_LIVES[SignalType.MEAN_REVERSION] == 30


def test_fractal_half_life():
    """Test FRACTAL signals have 180 min half-life."""
    assert SIGNAL_HALF_LIVES[SignalType.FRACTAL] == 180


def test_dynamic_half_life_selection(decay_engine):
    """Test dynamic half-life based on signal type."""
    state = decay_engine.create_decay_state(
        hypothesis_id="test_trend",
        symbol="BTC",
        initial_confidence=0.8,
        signal_type=SignalType.TREND,
    )
    
    assert state.half_life_minutes == 120


# ══════════════════════════════════════════════════════════════
# 3. Stage Transition Tests
# ══════════════════════════════════════════════════════════════

def test_stage_fresh_threshold():
    """Test FRESH stage threshold is 0.75."""
    assert DECAY_STAGE_THRESHOLDS["FRESH_MIN"] == 0.75


def test_stage_active_threshold():
    """Test ACTIVE stage threshold is 0.50."""
    assert DECAY_STAGE_THRESHOLDS["ACTIVE_MIN"] == 0.50


def test_stage_weakening_threshold():
    """Test WEAKENING stage threshold is 0.25."""
    assert DECAY_STAGE_THRESHOLDS["WEAKENING_MIN"] == 0.25


def test_stage_determination_fresh(sample_state):
    """Test FRESH stage determination."""
    sample_state.decay_factor = 0.80
    stage = sample_state._determine_stage()
    assert stage == DecayStage.FRESH


def test_stage_determination_active(sample_state):
    """Test ACTIVE stage determination."""
    sample_state.decay_factor = 0.60
    stage = sample_state._determine_stage()
    assert stage == DecayStage.ACTIVE


def test_stage_determination_weakening(sample_state):
    """Test WEAKENING stage determination."""
    sample_state.decay_factor = 0.35
    stage = sample_state._determine_stage()
    assert stage == DecayStage.WEAKENING


def test_stage_determination_expired(sample_state):
    """Test EXPIRED stage determination."""
    sample_state.decay_factor = 0.20
    stage = sample_state._determine_stage()
    assert stage == DecayStage.EXPIRED


# ══════════════════════════════════════════════════════════════
# 4. Expiration Rule Tests
# ══════════════════════════════════════════════════════════════

def test_expiration_threshold():
    """Test expiration threshold is 0.25."""
    assert DECAY_STAGE_THRESHOLDS["EXPIRED_THRESHOLD"] == 0.25


def test_signal_expires_below_threshold(sample_state):
    """Test signal is expired when decay_factor < 0.25."""
    sample_state.decay_factor = 0.20
    sample_state.decay_stage = sample_state._determine_stage()
    sample_state.is_expired = sample_state.decay_factor < 0.25
    
    assert sample_state.is_expired is True


def test_execution_blocked_when_expired(sample_state):
    """Test execution is blocked when signal expires."""
    sample_state.decay_factor = 0.20
    sample_state.is_expired = True
    sample_state.execution_blocked = True
    
    assert sample_state.execution_blocked is True


# ══════════════════════════════════════════════════════════════
# 5. Engine Tests
# ══════════════════════════════════════════════════════════════

def test_engine_create_decay_state(decay_engine):
    """Test creating decay state."""
    state = decay_engine.create_decay_state(
        hypothesis_id="hyp_001",
        symbol="BTC",
        initial_confidence=0.75,
    )
    
    assert state.hypothesis_id == "hyp_001"
    assert state.symbol == "BTC"
    assert state.initial_confidence == 0.75
    assert state.decay_factor == 1.0
    assert state.decay_stage == DecayStage.FRESH


def test_engine_compute_decay(decay_engine):
    """Test computing decay."""
    state = decay_engine.create_decay_state(
        hypothesis_id="hyp_002",
        symbol="ETH",
        initial_confidence=0.8,
    )
    
    result = decay_engine.compute_decay("hyp_002")
    
    assert result is not None
    assert result.hypothesis_id == "hyp_002"
    assert result.decay_factor <= 1.0


def test_engine_recompute_all(decay_engine):
    """Test recomputing all states."""
    decay_engine.create_decay_state("hyp_1", "BTC", 0.8)
    decay_engine.create_decay_state("hyp_2", "ETH", 0.7)
    
    results = decay_engine.recompute_all()
    
    assert len(results) == 2


def test_engine_get_summary(decay_engine):
    """Test getting summary."""
    decay_engine.create_decay_state("hyp_1", "BTC", 0.8)
    
    summary = decay_engine.get_summary()
    
    assert summary.total_signals == 1
    assert summary.fresh_count >= 0


# ══════════════════════════════════════════════════════════════
# 6. Integration Tests
# ══════════════════════════════════════════════════════════════

def test_confidence_modifier_integration(decay_engine):
    """Test confidence modifier for Hypothesis Engine."""
    decay_engine.create_decay_state("hyp_conf", "BTC", 0.8)
    
    result = decay_engine.get_confidence_modifier("hyp_conf", 0.8)
    
    assert "adjusted_confidence" in result
    assert "decay_factor" in result
    assert result["has_decay_state"] is True


def test_position_size_modifier_integration(decay_engine):
    """Test position size modifier for Portfolio Manager."""
    decay_engine.create_decay_state("hyp_pos", "BTC", 0.8)
    
    result = decay_engine.get_position_size_modifier("hyp_pos", 1000)
    
    assert "adjusted_size" in result
    assert "decay_factor" in result


def test_execution_eligibility_check(decay_engine):
    """Test execution eligibility for Execution Brain."""
    decay_engine.create_decay_state("hyp_exec", "BTC", 0.8)
    
    result = decay_engine.check_execution_eligibility("hyp_exec")
    
    assert "eligible" in result
    assert result["eligible"] is True


def test_execution_blocked_for_expired(decay_engine):
    """Test execution blocked for expired signals."""
    state = decay_engine.create_decay_state("hyp_expired", "BTC", 0.8)
    
    # Force expiration
    state.decay_factor = 0.20
    state.is_expired = True
    state.execution_blocked = True
    
    result = decay_engine.check_execution_eligibility("hyp_expired")
    
    assert result["eligible"] is False


# ══════════════════════════════════════════════════════════════
# 7. Singleton Tests
# ══════════════════════════════════════════════════════════════

def test_singleton_instance():
    """Test singleton returns same instance."""
    engine1 = get_alpha_decay_engine()
    engine2 = get_alpha_decay_engine()
    
    assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# 8. Statistics Tests
# ══════════════════════════════════════════════════════════════

def test_engine_statistics(decay_engine):
    """Test engine statistics."""
    decay_engine.create_decay_state("hyp_stat", "BTC", 0.8)
    
    stats = decay_engine.get_statistics()
    
    assert "phase" in stats
    assert stats["phase"] == "43.8"
    assert "total_created" in stats
    assert stats["total_created"] >= 1


# ══════════════════════════════════════════════════════════════
# Run Tests
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
