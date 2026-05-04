"""
Strategy Regime Mapping — Tests

Test suite for strategy-regime mapping.

Required tests (16):
1. trending -> trend_following favored
2. trending -> mean_reversion disfavored
3. ranging -> mean_reversion favored
4. ranging -> breakout disfavored
5. volatile -> volatility_expansion favored
6. volatile -> funding_arb disfavored
7. illiquid -> basis_trade favored
8. illiquid -> breakout disfavored
9. suitability scaling by regime_confidence
10. favored modifiers correct
11. neutral modifiers correct
12. disfavored modifiers correct
13. registry write
14. summary endpoint
15. single strategy endpoint
16. recompute endpoint
"""

import pytest
from datetime import datetime

from modules.regime_intelligence_v2.strategy_regime_types import (
    StrategyRegimeMapping,
    RegimeStrategySummary,
    STRATEGY_LIST,
    SUITABILITY_RANGES,
    STATE_MODIFIERS,
    REGIME_STRATEGY_MATRIX,
)
from modules.regime_intelligence_v2.strategy_regime_mapping_engine import (
    StrategyRegimeMappingEngine,
    get_strategy_regime_mapping_engine,
)
from modules.regime_intelligence_v2.strategy_regime_registry import (
    StrategyRegimeRegistry,
    get_strategy_regime_registry,
)
from modules.regime_intelligence_v2.regime_types import MarketRegime


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def mapping_engine():
    """Create fresh mapping engine."""
    return StrategyRegimeMappingEngine()


@pytest.fixture
def mapping_registry():
    """Create fresh mapping registry."""
    return StrategyRegimeRegistry()


@pytest.fixture
def trending_regime():
    """Create TRENDING regime."""
    return MarketRegime(
        regime_type="TRENDING",
        trend_strength=0.45,
        volatility_level=0.30,
        liquidity_level=0.75,
        regime_confidence=0.70,
        dominant_driver="TREND",
        context_state="SUPPORTIVE",
    )


@pytest.fixture
def ranging_regime():
    """Create RANGING regime."""
    return MarketRegime(
        regime_type="RANGING",
        trend_strength=0.15,
        volatility_level=0.25,
        liquidity_level=0.70,
        regime_confidence=0.65,
        dominant_driver="VOLATILITY",
        context_state="NEUTRAL",
    )


@pytest.fixture
def volatile_regime():
    """Create VOLATILE regime."""
    return MarketRegime(
        regime_type="VOLATILE",
        trend_strength=0.30,
        volatility_level=0.70,
        liquidity_level=0.55,
        regime_confidence=0.60,
        dominant_driver="VOLATILITY",
        context_state="CONFLICTED",
    )


@pytest.fixture
def illiquid_regime():
    """Create ILLIQUID regime."""
    return MarketRegime(
        regime_type="ILLIQUID",
        trend_strength=0.20,
        volatility_level=0.40,
        liquidity_level=0.20,
        regime_confidence=0.55,
        dominant_driver="LIQUIDITY",
        context_state="CONFLICTED",
    )


# ══════════════════════════════════════════════════════════════
# Test 1: TRENDING -> trend_following FAVORED
# ══════════════════════════════════════════════════════════════

def test_trending_trend_following_favored(mapping_engine, trending_regime):
    """Test 1: trend_following is favored in TRENDING regime."""
    mapping = mapping_engine.map_strategy("trend_following", trending_regime)
    
    assert mapping.state == "FAVORED"
    assert mapping.suitability >= SUITABILITY_RANGES["FAVORED"][0]


# ══════════════════════════════════════════════════════════════
# Test 2: TRENDING -> mean_reversion DISFAVORED
# ══════════════════════════════════════════════════════════════

def test_trending_mean_reversion_disfavored(mapping_engine, trending_regime):
    """Test 2: mean_reversion is disfavored in TRENDING regime."""
    mapping = mapping_engine.map_strategy("mean_reversion", trending_regime)
    
    assert mapping.state == "DISFAVORED"
    assert mapping.suitability <= SUITABILITY_RANGES["DISFAVORED"][1]


# ══════════════════════════════════════════════════════════════
# Test 3: RANGING -> mean_reversion FAVORED
# ══════════════════════════════════════════════════════════════

def test_ranging_mean_reversion_favored(mapping_engine, ranging_regime):
    """Test 3: mean_reversion is favored in RANGING regime."""
    mapping = mapping_engine.map_strategy("mean_reversion", ranging_regime)
    
    assert mapping.state == "FAVORED"


# ══════════════════════════════════════════════════════════════
# Test 4: RANGING -> breakout DISFAVORED
# ══════════════════════════════════════════════════════════════

def test_ranging_breakout_disfavored(mapping_engine, ranging_regime):
    """Test 4: breakout is disfavored in RANGING regime."""
    mapping = mapping_engine.map_strategy("breakout", ranging_regime)
    
    assert mapping.state == "DISFAVORED"


# ══════════════════════════════════════════════════════════════
# Test 5: VOLATILE -> volatility_expansion FAVORED
# ══════════════════════════════════════════════════════════════

def test_volatile_volatility_expansion_favored(mapping_engine, volatile_regime):
    """Test 5: volatility_expansion is favored in VOLATILE regime."""
    mapping = mapping_engine.map_strategy("volatility_expansion", volatile_regime)
    
    assert mapping.state == "FAVORED"


# ══════════════════════════════════════════════════════════════
# Test 6: VOLATILE -> funding_arb DISFAVORED
# ══════════════════════════════════════════════════════════════

def test_volatile_funding_arb_disfavored(mapping_engine, volatile_regime):
    """Test 6: funding_arb is disfavored in VOLATILE regime."""
    mapping = mapping_engine.map_strategy("funding_arb", volatile_regime)
    
    assert mapping.state == "DISFAVORED"


# ══════════════════════════════════════════════════════════════
# Test 7: ILLIQUID -> basis_trade FAVORED
# ══════════════════════════════════════════════════════════════

def test_illiquid_basis_trade_favored(mapping_engine, illiquid_regime):
    """Test 7: basis_trade is favored in ILLIQUID regime."""
    mapping = mapping_engine.map_strategy("basis_trade", illiquid_regime)
    
    assert mapping.state == "FAVORED"


# ══════════════════════════════════════════════════════════════
# Test 8: ILLIQUID -> breakout DISFAVORED
# ══════════════════════════════════════════════════════════════

def test_illiquid_breakout_disfavored(mapping_engine, illiquid_regime):
    """Test 8: breakout is disfavored in ILLIQUID regime."""
    mapping = mapping_engine.map_strategy("breakout", illiquid_regime)
    
    assert mapping.state == "DISFAVORED"


# ══════════════════════════════════════════════════════════════
# Test 9: Suitability Scaling by Regime Confidence
# ══════════════════════════════════════════════════════════════

def test_suitability_scaling_by_regime_confidence(mapping_engine):
    """Test 9: Suitability is scaled by regime confidence."""
    # High confidence
    high_conf_regime = MarketRegime(
        regime_type="TRENDING",
        trend_strength=0.50,
        volatility_level=0.30,
        liquidity_level=0.75,
        regime_confidence=1.0,  # Max confidence
        dominant_driver="TREND",
        context_state="SUPPORTIVE",
    )
    
    # Low confidence
    low_conf_regime = MarketRegime(
        regime_type="TRENDING",
        trend_strength=0.50,
        volatility_level=0.30,
        liquidity_level=0.75,
        regime_confidence=0.0,  # Min confidence
        dominant_driver="TREND",
        context_state="SUPPORTIVE",
    )
    
    high_mapping = mapping_engine.map_strategy("trend_following", high_conf_regime)
    low_mapping = mapping_engine.map_strategy("trend_following", low_conf_regime)
    
    # High confidence should give higher suitability
    assert high_mapping.suitability > low_mapping.suitability


def test_adjusted_suitability_formula(mapping_engine):
    """Test adjusted suitability formula: base * (0.7 + 0.3 * conf)."""
    base = 0.825  # Mid of FAVORED range
    
    # At confidence = 1.0: 0.825 * (0.7 + 0.3) = 0.825
    high = mapping_engine.calculate_adjusted_suitability(base, 1.0)
    assert abs(high - 0.825) < 0.01
    
    # At confidence = 0.0: 0.825 * 0.7 = 0.5775
    low = mapping_engine.calculate_adjusted_suitability(base, 0.0)
    assert abs(low - 0.5775) < 0.01


# ══════════════════════════════════════════════════════════════
# Test 10: FAVORED Modifiers
# ══════════════════════════════════════════════════════════════

def test_favored_modifiers_correct(mapping_engine, trending_regime):
    """Test 10: FAVORED state has correct modifiers."""
    mapping = mapping_engine.map_strategy("trend_following", trending_regime)
    
    assert mapping.confidence_modifier == 1.08
    assert mapping.capital_modifier == 1.12


# ══════════════════════════════════════════════════════════════
# Test 11: NEUTRAL Modifiers
# ══════════════════════════════════════════════════════════════

def test_neutral_modifiers_correct(mapping_engine, trending_regime):
    """Test 11: NEUTRAL state has correct modifiers."""
    mapping = mapping_engine.map_strategy("volatility_expansion", trending_regime)
    
    assert mapping.confidence_modifier == 1.00
    assert mapping.capital_modifier == 1.00


# ══════════════════════════════════════════════════════════════
# Test 12: DISFAVORED Modifiers
# ══════════════════════════════════════════════════════════════

def test_disfavored_modifiers_correct(mapping_engine, trending_regime):
    """Test 12: DISFAVORED state has correct modifiers."""
    mapping = mapping_engine.map_strategy("mean_reversion", trending_regime)
    
    assert mapping.confidence_modifier == 0.90
    assert mapping.capital_modifier == 0.82


# ══════════════════════════════════════════════════════════════
# Test 13: Registry Write
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_write(mapping_registry, mapping_engine, trending_regime):
    """Test 13: Mapping can be stored in registry."""
    mapping = mapping_engine.map_strategy("trend_following", trending_regime)
    record = await mapping_registry.store_mapping(mapping)
    
    assert record.strategy == "trend_following"
    assert record.state == "FAVORED"


@pytest.mark.asyncio
async def test_registry_bulk_write(mapping_registry, mapping_engine, trending_regime):
    """Test bulk write to registry."""
    mappings = mapping_engine.map_all_strategies(trending_regime)
    records = await mapping_registry.store_mappings_bulk(mappings)
    
    assert len(records) == 8


# ══════════════════════════════════════════════════════════════
# Test 14: Summary Endpoint
# ══════════════════════════════════════════════════════════════

def test_summary_endpoint(mapping_engine, trending_regime):
    """Test 14: Summary groups strategies correctly."""
    summary = mapping_engine.get_summary(trending_regime)
    
    assert "trend_following" in summary.favored_strategies
    assert "breakout" in summary.favored_strategies
    assert "mean_reversion" in summary.disfavored_strategies


def test_summary_regime_type(mapping_engine, ranging_regime):
    """Test summary returns correct regime type."""
    summary = mapping_engine.get_summary(ranging_regime)
    
    assert summary.regime_type == "RANGING"
    assert "mean_reversion" in summary.favored_strategies


# ══════════════════════════════════════════════════════════════
# Test 15: Single Strategy Endpoint
# ══════════════════════════════════════════════════════════════

def test_single_strategy_endpoint(mapping_engine, volatile_regime):
    """Test 15: Single strategy mapping works."""
    mapping = mapping_engine.map_strategy("liquidation_capture", volatile_regime)
    
    assert mapping.strategy == "liquidation_capture"
    assert mapping.regime_type == "VOLATILE"
    assert mapping.state == "FAVORED"


# ══════════════════════════════════════════════════════════════
# Test 16: Recompute Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recompute_endpoint(mapping_engine):
    """Test 16: Recompute generates all mappings."""
    mappings = await mapping_engine.compute_mappings("BTCUSDT", "1H")
    
    assert len(mappings) == 8
    assert all(m.strategy in STRATEGY_LIST for m in mappings)


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_all_strategies_covered():
    """Test all 8 strategies are in the list."""
    assert len(STRATEGY_LIST) == 8
    assert "trend_following" in STRATEGY_LIST
    assert "breakout" in STRATEGY_LIST
    assert "mean_reversion" in STRATEGY_LIST
    assert "liquidation_capture" in STRATEGY_LIST
    assert "funding_arb" in STRATEGY_LIST
    assert "basis_trade" in STRATEGY_LIST
    assert "volatility_expansion" in STRATEGY_LIST
    assert "range_trading" in STRATEGY_LIST


def test_all_regimes_have_matrix():
    """Test all regimes have mapping matrix."""
    assert "TRENDING" in REGIME_STRATEGY_MATRIX
    assert "RANGING" in REGIME_STRATEGY_MATRIX
    assert "VOLATILE" in REGIME_STRATEGY_MATRIX
    assert "ILLIQUID" in REGIME_STRATEGY_MATRIX


def test_modifiers_constants():
    """Test modifier constants are correct."""
    assert STATE_MODIFIERS["FAVORED"]["confidence_modifier"] == 1.08
    assert STATE_MODIFIERS["FAVORED"]["capital_modifier"] == 1.12
    assert STATE_MODIFIERS["NEUTRAL"]["confidence_modifier"] == 1.00
    assert STATE_MODIFIERS["DISFAVORED"]["capital_modifier"] == 0.82


def test_suitability_ranges():
    """Test suitability ranges are correct."""
    assert SUITABILITY_RANGES["FAVORED"] == (0.75, 0.90)
    assert SUITABILITY_RANGES["NEUTRAL"] == (0.45, 0.65)
    assert SUITABILITY_RANGES["DISFAVORED"] == (0.10, 0.35)


def test_reason_generation(mapping_engine, trending_regime):
    """Test reason is generated."""
    mapping = mapping_engine.map_strategy("trend_following", trending_regime)
    
    assert len(mapping.reason) > 0
    assert "trend" in mapping.reason.lower()


def test_singleton_pattern():
    """Test singleton pattern for engine."""
    engine1 = get_strategy_regime_mapping_engine()
    engine2 = get_strategy_regime_mapping_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_strategy_history(mapping_registry, mapping_engine, trending_regime):
    """Test strategy history retrieval."""
    mapping = mapping_engine.map_strategy("trend_following", trending_regime)
    await mapping_registry.store_mapping(mapping)
    
    history = await mapping_registry.get_strategy_history("trend_following")
    
    assert len(history) >= 1
    assert history[0].strategy == "trend_following"
