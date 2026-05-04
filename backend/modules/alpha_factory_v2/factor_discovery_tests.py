"""
PHASE 26.1 — Factor Discovery Engine Tests

Test suite for factor discovery functionality.

Tests:
1. Discovery creates candidates
2. Each category generates factors
3. Factor IDs are unique
4. Lookbacks are applied correctly
5. Raw signals are bounded
6. Category filtering works
"""

import pytest
from datetime import datetime

from modules.alpha_factory_v2.factor_discovery_engine import (
    FactorDiscoveryEngine,
    get_factor_discovery_engine,
)
from modules.alpha_factory_v2.factor_types import (
    FactorCandidate,
    DEFAULT_LOOKBACKS,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create fresh engine instance."""
    return FactorDiscoveryEngine()


# ══════════════════════════════════════════════════════════════
# Test 1: Discovery Creates Candidates
# ══════════════════════════════════════════════════════════════

def test_discovery_creates_candidates(engine):
    """Test 1: discover_all creates candidate factors."""
    candidates = engine.discover_all()
    
    assert len(candidates) > 0
    assert all(isinstance(c, FactorCandidate) for c in candidates)


# ══════════════════════════════════════════════════════════════
# Test 2: TA Factors Generated
# ══════════════════════════════════════════════════════════════

def test_ta_factors_generated(engine):
    """Test 2: TA category generates factors."""
    candidates = engine.discover_ta_factors()
    
    assert len(candidates) > 0
    assert all(c.category == "TA" for c in candidates)
    
    # Should have momentum, breakout, trend, mean_reversion
    names = [c.name for c in candidates]
    assert any("momentum" in n for n in names)
    assert any("breakout" in n for n in names)
    assert any("trend" in n for n in names)
    assert any("mean_reversion" in n for n in names)


# ══════════════════════════════════════════════════════════════
# Test 3: Exchange Factors Generated
# ══════════════════════════════════════════════════════════════

def test_exchange_factors_generated(engine):
    """Test 3: EXCHANGE category generates factors."""
    candidates = engine.discover_exchange_factors()
    
    assert len(candidates) > 0
    assert all(c.category == "EXCHANGE" for c in candidates)
    
    # Should have orderbook, liquidation, funding, oi
    names = [c.name for c in candidates]
    assert any("orderbook" in n for n in names)
    assert any("liquidation" in n for n in names)
    assert any("funding" in n for n in names)
    assert any("oi_delta" in n for n in names)


# ══════════════════════════════════════════════════════════════
# Test 4: Fractal Factors Generated
# ══════════════════════════════════════════════════════════════

def test_fractal_factors_generated(engine):
    """Test 4: FRACTAL category generates factors."""
    candidates = engine.discover_fractal_factors()
    
    assert len(candidates) > 0
    assert all(c.category == "FRACTAL" for c in candidates)
    
    # Should have pattern, phase, horizon
    names = [c.name for c in candidates]
    assert any("pattern" in n for n in names)
    assert any("phase" in n for n in names)
    assert any("horizon" in n for n in names)


# ══════════════════════════════════════════════════════════════
# Test 5: Regime Factors Generated
# ══════════════════════════════════════════════════════════════

def test_regime_factors_generated(engine):
    """Test 5: REGIME category generates factors."""
    candidates = engine.discover_regime_factors()
    
    assert len(candidates) > 0
    assert all(c.category == "REGIME" for c in candidates)
    
    # Should have trend_strength, volatility, liquidity
    names = [c.name for c in candidates]
    assert any("trend_strength" in n for n in names)
    assert any("volatility" in n for n in names)
    assert any("liquidity" in n for n in names)


# ══════════════════════════════════════════════════════════════
# Test 6: Factor IDs Are Unique
# ══════════════════════════════════════════════════════════════

def test_factor_ids_unique(engine):
    """Test 6: All factor IDs are unique."""
    candidates = engine.discover_all()
    
    ids = [c.factor_id for c in candidates]
    assert len(ids) == len(set(ids)), "Factor IDs must be unique"


# ══════════════════════════════════════════════════════════════
# Test 7: Lookbacks Applied Correctly
# ══════════════════════════════════════════════════════════════

def test_lookbacks_applied(engine):
    """Test 7: Lookbacks match DEFAULT_LOOKBACKS."""
    candidates = engine.discover_ta_factors()
    
    ta_lookbacks = set(DEFAULT_LOOKBACKS["TA"])
    candidate_lookbacks = set(c.lookback for c in candidates)
    
    # All TA lookbacks should be present
    assert ta_lookbacks.issubset(candidate_lookbacks)


# ══════════════════════════════════════════════════════════════
# Test 8: Raw Signals Bounded
# ══════════════════════════════════════════════════════════════

def test_raw_signals_bounded(engine):
    """Test 8: Raw signals are in [-1, 1]."""
    candidates = engine.discover_all()
    
    for c in candidates:
        assert -1.0 <= c.raw_signal <= 1.0, f"Signal out of bounds: {c.raw_signal}"


# ══════════════════════════════════════════════════════════════
# Test 9: Category Filtering Works
# ══════════════════════════════════════════════════════════════

def test_category_filtering(engine):
    """Test 9: get_factors_by_category filters correctly."""
    engine.discover_all()
    
    ta_factors = engine.get_factors_by_category("TA")
    exchange_factors = engine.get_factors_by_category("EXCHANGE")
    
    assert all(f.category == "TA" for f in ta_factors)
    assert all(f.category == "EXCHANGE" for f in exchange_factors)
    assert len(ta_factors) > 0
    assert len(exchange_factors) > 0


# ══════════════════════════════════════════════════════════════
# Test 10: Discovery Count Correct
# ══════════════════════════════════════════════════════════════

def test_discovery_count(engine):
    """Test 10: Discovery count matches total factors."""
    candidates = engine.discover_all()
    
    assert engine.get_discovery_count() == len(candidates)


# ══════════════════════════════════════════════════════════════
# Test 11: Last Discovery Timestamp
# ══════════════════════════════════════════════════════════════

def test_last_discovery_timestamp(engine):
    """Test 11: Last discovery timestamp is updated."""
    assert engine.last_discovery is None
    
    engine.discover_all()
    
    assert engine.last_discovery is not None
    assert isinstance(engine.last_discovery, datetime)


# ══════════════════════════════════════════════════════════════
# Test 12: Factor Candidate Structure
# ══════════════════════════════════════════════════════════════

def test_factor_candidate_structure(engine):
    """Test 12: Factor candidates have all required fields."""
    candidates = engine.discover_all()
    
    for c in candidates:
        assert hasattr(c, 'factor_id')
        assert hasattr(c, 'name')
        assert hasattr(c, 'category')
        assert hasattr(c, 'lookback')
        assert hasattr(c, 'raw_signal')
        assert hasattr(c, 'source')
        assert hasattr(c, 'parameters')
        assert hasattr(c, 'discovered_at')
        
        # Check types
        assert isinstance(c.factor_id, str)
        assert len(c.factor_id) == 12  # MD5 hash truncated
        assert isinstance(c.lookback, int)
        assert c.lookback >= 1


# ══════════════════════════════════════════════════════════════
# Test 13: Singleton Pattern
# ══════════════════════════════════════════════════════════════

def test_singleton_pattern():
    """Test 13: Singleton pattern works."""
    engine1 = get_factor_discovery_engine()
    engine2 = get_factor_discovery_engine()
    
    assert engine1 is engine2


# ══════════════════════════════════════════════════════════════
# Test 14: Source Attribution
# ══════════════════════════════════════════════════════════════

def test_source_attribution(engine):
    """Test 14: Factors have correct source attribution."""
    engine.discover_all()
    
    ta_factors = engine.get_factors_by_category("TA")
    exchange_factors = engine.get_factors_by_category("EXCHANGE")
    fractal_factors = engine.get_factors_by_category("FRACTAL")
    regime_factors = engine.get_factors_by_category("REGIME")
    
    assert all(f.source == "ta_engine" for f in ta_factors)
    assert all(f.source == "exchange_intelligence" for f in exchange_factors)
    assert all(f.source == "fractal_intelligence" for f in fractal_factors)
    assert all(f.source == "regime_engine" for f in regime_factors)


# ══════════════════════════════════════════════════════════════
# Test 15: Parameters Stored
# ══════════════════════════════════════════════════════════════

def test_parameters_stored(engine):
    """Test 15: Factor parameters are stored correctly."""
    candidates = engine.discover_all()
    
    for c in candidates:
        assert isinstance(c.parameters, dict)
        assert "period" in c.parameters or "type" in c.parameters


# ══════════════════════════════════════════════════════════════
# Test 16: Multiple Discovery Runs
# ══════════════════════════════════════════════════════════════

def test_multiple_discovery_runs(engine):
    """Test 16: Multiple discovery runs are idempotent."""
    candidates1 = engine.discover_all()
    candidates2 = engine.discover_all()
    
    # Same number of factors
    assert len(candidates1) == len(candidates2)
    
    # Same factor IDs
    ids1 = set(c.factor_id for c in candidates1)
    ids2 = set(c.factor_id for c in candidates2)
    assert ids1 == ids2


# ══════════════════════════════════════════════════════════════
# Test 17: Expected Factor Count
# ══════════════════════════════════════════════════════════════

def test_expected_factor_count(engine):
    """Test 17: Verify expected number of factors."""
    candidates = engine.discover_all()
    
    # TA: 4 types × 4 lookbacks = 16
    # EXCHANGE: 4 types × 3 lookbacks = 12
    # FRACTAL: 3 types × 3 lookbacks = 9
    # REGIME: 3 types × 3 lookbacks = 9
    # Total: 46
    
    expected_min = 40
    expected_max = 50
    
    assert expected_min <= len(candidates) <= expected_max
