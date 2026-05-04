"""
Regime Intelligence v2 — Tests

Test suite for regime detection.

Required tests (16):
1. trend strength calculation
2. volatility calculation
3. liquidity calculation
4. trending classification
5. ranging classification
6. volatile classification
7. illiquid classification
8. regime confidence calculation
9. dominant driver detection
10. registry write
11. registry retrieval
12. current regime endpoint
13. history endpoint
14. summary endpoint
15. recompute endpoint
16. integration with TA engine
"""

import pytest
from datetime import datetime

from modules.regime_intelligence_v2.regime_types import (
    MarketRegime,
    RegimeHistoryRecord,
    RegimeSummary,
    RegimeInputMetrics,
    TREND_STRONG_THRESHOLD,
    TREND_WEAK_THRESHOLD,
    VOLATILITY_HIGH_THRESHOLD,
    LIQUIDITY_LOW_THRESHOLD,
)
from modules.regime_intelligence_v2.regime_detection_engine import (
    RegimeDetectionEngine,
    get_regime_detection_engine,
)
from modules.regime_intelligence_v2.regime_registry import (
    RegimeRegistry,
    get_regime_registry,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def regime_engine():
    """Create fresh regime detection engine."""
    return RegimeDetectionEngine()


@pytest.fixture
def regime_registry():
    """Create fresh regime registry."""
    return RegimeRegistry()


@pytest.fixture
def trending_metrics():
    """Metrics for TRENDING regime."""
    return RegimeInputMetrics(
        price=42000.0,
        ema_50=43000.0,  # Strong uptrend
        ema_200=40000.0,
        atr=1000.0,  # Low volatility
        orderbook_depth=0.8,
        volume_profile=0.7,
        spread_inverse=0.85,
    )


@pytest.fixture
def ranging_metrics():
    """Metrics for RANGING regime."""
    return RegimeInputMetrics(
        price=42000.0,
        ema_50=42100.0,  # Weak trend
        ema_200=41900.0,
        atr=800.0,  # Low volatility
        orderbook_depth=0.7,
        volume_profile=0.6,
        spread_inverse=0.8,
    )


@pytest.fixture
def volatile_metrics():
    """Metrics for VOLATILE regime."""
    return RegimeInputMetrics(
        price=42000.0,
        ema_50=42500.0,
        ema_200=41500.0,
        atr=4000.0,  # High volatility
        orderbook_depth=0.6,
        volume_profile=0.5,
        spread_inverse=0.7,
    )


@pytest.fixture
def illiquid_metrics():
    """Metrics for ILLIQUID regime."""
    return RegimeInputMetrics(
        price=42000.0,
        ema_50=42200.0,
        ema_200=41800.0,
        atr=1500.0,
        orderbook_depth=0.1,  # Very low
        volume_profile=0.15,  # Very low
        spread_inverse=0.2,  # Wide spread
    )


# ══════════════════════════════════════════════════════════════
# Test 1: Trend Strength Calculation
# ══════════════════════════════════════════════════════════════

def test_trend_strength_calculation(regime_engine):
    """Test 1: Trend strength is calculated correctly."""
    # |43000 - 40000| / 42000 = 3000/42000 ≈ 0.0714
    strength = regime_engine.calculate_trend_strength(43000, 40000, 42000)
    assert 0.7 <= strength <= 0.75  # Normalized


def test_trend_strength_zero_price(regime_engine):
    """Test trend strength handles zero price."""
    strength = regime_engine.calculate_trend_strength(100, 90, 0)
    assert strength == 0.0


def test_trend_strength_no_trend(regime_engine):
    """Test trend strength when EMAs are equal."""
    strength = regime_engine.calculate_trend_strength(100, 100, 100)
    assert strength == 0.0


# ══════════════════════════════════════════════════════════════
# Test 2: Volatility Calculation
# ══════════════════════════════════════════════════════════════

def test_volatility_calculation(regime_engine):
    """Test 2: Volatility is calculated correctly."""
    # ATR 2100 / price 42000 = 0.05
    vol = regime_engine.calculate_volatility(2100, 42000)
    assert abs(vol - 0.50) < 0.01  # Normalized to 0-1


def test_volatility_zero_price(regime_engine):
    """Test volatility handles zero price."""
    vol = regime_engine.calculate_volatility(100, 0)
    assert vol == 0.0


# ══════════════════════════════════════════════════════════════
# Test 3: Liquidity Calculation
# ══════════════════════════════════════════════════════════════

def test_liquidity_calculation(regime_engine):
    """Test 3: Liquidity is calculated correctly."""
    # (0.8 + 0.7 + 0.9) / 3 = 0.8
    liq = regime_engine.calculate_liquidity(0.8, 0.7, 0.9)
    assert abs(liq - 0.8) < 0.01


def test_liquidity_bounds(regime_engine):
    """Test liquidity is bounded 0-1."""
    liq = regime_engine.calculate_liquidity(1.5, 1.5, 1.5)
    assert liq == 1.0


# ══════════════════════════════════════════════════════════════
# Test 4: Trending Classification
# ══════════════════════════════════════════════════════════════

def test_trending_classification(regime_engine, trending_metrics):
    """Test 4: TRENDING regime is detected correctly."""
    regime = regime_engine.detect_regime(trending_metrics)
    assert regime.regime_type == "TRENDING"


def test_trending_strong_trend(regime_engine):
    """Test trending with strong trend strength."""
    regime_type = regime_engine.classify_regime(0.50, 0.30, 0.70)
    assert regime_type == "TRENDING"


# ══════════════════════════════════════════════════════════════
# Test 5: Ranging Classification
# ══════════════════════════════════════════════════════════════

def test_ranging_classification(regime_engine, ranging_metrics):
    """Test 5: RANGING regime is detected correctly."""
    regime = regime_engine.detect_regime(ranging_metrics)
    assert regime.regime_type == "RANGING"


def test_ranging_weak_trend(regime_engine):
    """Test ranging with weak trend."""
    regime_type = regime_engine.classify_regime(0.10, 0.20, 0.70)
    assert regime_type == "RANGING"


# ══════════════════════════════════════════════════════════════
# Test 6: Volatile Classification
# ══════════════════════════════════════════════════════════════

def test_volatile_classification(regime_engine, volatile_metrics):
    """Test 6: VOLATILE regime is detected correctly."""
    regime = regime_engine.detect_regime(volatile_metrics)
    assert regime.regime_type == "VOLATILE"


def test_volatile_high_volatility(regime_engine):
    """Test volatile with high volatility."""
    regime_type = regime_engine.classify_regime(0.30, 0.70, 0.70)
    assert regime_type == "VOLATILE"


# ══════════════════════════════════════════════════════════════
# Test 7: Illiquid Classification
# ══════════════════════════════════════════════════════════════

def test_illiquid_classification(regime_engine, illiquid_metrics):
    """Test 7: ILLIQUID regime is detected correctly."""
    regime = regime_engine.detect_regime(illiquid_metrics)
    assert regime.regime_type == "ILLIQUID"


def test_illiquid_low_liquidity(regime_engine):
    """Test illiquid with low liquidity."""
    regime_type = regime_engine.classify_regime(0.30, 0.30, 0.20)
    assert regime_type == "ILLIQUID"


# ══════════════════════════════════════════════════════════════
# Test 8: Regime Confidence Calculation
# ══════════════════════════════════════════════════════════════

def test_regime_confidence_calculation(regime_engine):
    """Test 8: Confidence is calculated correctly."""
    # 0.4 * 0.50 + 0.3 * (1-0.30) + 0.3 * 0.80
    # = 0.20 + 0.21 + 0.24 = 0.65
    conf = regime_engine.calculate_regime_confidence(0.50, 0.30, 0.80)
    assert 0.60 <= conf <= 0.70


def test_confidence_bounds(regime_engine):
    """Test confidence is bounded 0-1."""
    conf = regime_engine.calculate_regime_confidence(1.0, 0.0, 1.0)
    assert 0.0 <= conf <= 1.0


# ══════════════════════════════════════════════════════════════
# Test 9: Dominant Driver Detection
# ══════════════════════════════════════════════════════════════

def test_dominant_driver_detection(regime_engine):
    """Test 9: Dominant driver is detected correctly."""
    driver = regime_engine.detect_dominant_driver(0.80, 0.30, 0.70)
    assert driver == "TREND"


def test_dominant_driver_volatility(regime_engine):
    """Test volatility as dominant driver."""
    driver = regime_engine.detect_dominant_driver(0.20, 0.90, 0.70)
    assert driver == "VOLATILITY"


def test_dominant_driver_liquidity(regime_engine):
    """Test liquidity (low) as dominant driver."""
    driver = regime_engine.detect_dominant_driver(0.20, 0.30, 0.10)
    assert driver == "LIQUIDITY"


# ══════════════════════════════════════════════════════════════
# Test 10: Registry Write
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_write(regime_registry, regime_engine, trending_metrics):
    """Test 10: Regime can be stored in registry."""
    regime = regime_engine.detect_regime(trending_metrics)
    record = await regime_registry.store_regime(regime)
    
    assert record.regime_type == regime.regime_type
    assert record.confidence == regime.regime_confidence


# ══════════════════════════════════════════════════════════════
# Test 11: Registry Retrieval
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_registry_retrieval(regime_registry, regime_engine, trending_metrics):
    """Test 11: Regime can be retrieved from registry."""
    regime = regime_engine.detect_regime(trending_metrics)
    await regime_registry.store_regime(regime)
    
    history = await regime_registry.get_history("BTCUSDT", "1H")
    
    assert len(history) >= 1
    assert history[0].regime_type == regime.regime_type


# ══════════════════════════════════════════════════════════════
# Test 12: Current Regime Endpoint
# ══════════════════════════════════════════════════════════════

def test_current_regime_endpoint(regime_engine):
    """Test 12: Current regime can be detected."""
    regime = regime_engine.detect_regime_simulated()
    
    assert regime is not None
    assert regime.regime_type in ["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]


# ══════════════════════════════════════════════════════════════
# Test 13: History Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_history_endpoint(regime_registry, regime_engine):
    """Test 13: History can be retrieved."""
    # Store a few regimes
    for _ in range(3):
        regime = regime_engine.detect_regime_simulated()
        await regime_registry.store_regime(regime)
    
    history = await regime_registry.get_history("BTCUSDT", "1H")
    
    assert len(history) >= 3


# ══════════════════════════════════════════════════════════════
# Test 14: Summary Endpoint
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_summary_endpoint(regime_registry, regime_engine):
    """Test 14: Summary can be generated."""
    # Store some regimes
    for _ in range(5):
        regime = regime_engine.detect_regime_simulated()
        await regime_registry.store_regime(regime)
    
    summary = await regime_registry.get_summary("BTCUSDT", "1H")
    
    assert summary.total_records >= 5
    assert summary.current_regime in ["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]


# ══════════════════════════════════════════════════════════════
# Test 15: Recompute Endpoint
# ══════════════════════════════════════════════════════════════

def test_recompute_endpoint(regime_engine):
    """Test 15: Regime can be recomputed."""
    regime1 = regime_engine.detect_regime_simulated()
    regime2 = regime_engine.detect_regime_simulated()
    
    # Both should return valid regimes
    assert regime1.regime_type is not None
    assert regime2.regime_type is not None


# ══════════════════════════════════════════════════════════════
# Test 16: Integration with TA Engine
# ══════════════════════════════════════════════════════════════

def test_integration_ta_engine(regime_engine):
    """Test 16: Regime integrates with TA-like metrics."""
    # Create metrics similar to TA output
    metrics = RegimeInputMetrics(
        price=42000.0,
        ema_50=42500.0,
        ema_200=41000.0,  # Bullish cross
        atr=1500.0,
        orderbook_depth=0.75,
        volume_profile=0.65,
        spread_inverse=0.80,
        fractal_alignment=0.70,
    )
    
    regime = regime_engine.detect_regime(metrics)
    
    assert regime.regime_type in ["TRENDING", "RANGING", "VOLATILE", "ILLIQUID"]
    assert regime.dominant_driver in ["TREND", "VOLATILITY", "LIQUIDITY", "FRACTAL"]


# ══════════════════════════════════════════════════════════════
# Additional Tests
# ══════════════════════════════════════════════════════════════

def test_constants():
    """Test all constants are correct."""
    assert TREND_STRONG_THRESHOLD == 0.03
    assert TREND_WEAK_THRESHOLD == 0.02
    assert VOLATILITY_HIGH_THRESHOLD == 0.06
    assert LIQUIDITY_LOW_THRESHOLD == 0.30


def test_context_state_supportive(regime_engine):
    """Test SUPPORTIVE context state."""
    context = regime_engine.determine_context_state(0.50, 0.20, 0.80)
    assert context == "SUPPORTIVE"


def test_context_state_conflicted(regime_engine):
    """Test CONFLICTED context state."""
    context = regime_engine.determine_context_state(0.50, 0.70, 0.20)
    assert context == "CONFLICTED"


def test_context_state_neutral(regime_engine):
    """Test NEUTRAL context state."""
    context = regime_engine.determine_context_state(0.15, 0.35, 0.50)
    assert context == "NEUTRAL"


def test_market_regime_model():
    """Test MarketRegime model structure."""
    regime = MarketRegime(
        regime_type="TRENDING",
        trend_strength=0.41,
        volatility_level=0.32,
        liquidity_level=0.74,
        regime_confidence=0.69,
        dominant_driver="TREND",
        context_state="SUPPORTIVE",
    )
    
    assert regime.regime_type == "TRENDING"
    assert regime.dominant_driver == "TREND"


def test_singleton_pattern():
    """Test singleton pattern for engine."""
    engine1 = get_regime_detection_engine()
    engine2 = get_regime_detection_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_empty_registry_summary(regime_registry):
    """Test summary with empty registry."""
    summary = await regime_registry.get_summary("EMPTY", "1H")
    
    assert summary.total_records == 0
    assert summary.current_regime == "RANGING"
