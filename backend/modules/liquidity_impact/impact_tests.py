"""
Liquidity Impact Engine Tests

PHASE 37 Sublayer — Liquidity Impact Engine

Minimum 24 tests as per requirements.
"""

import pytest
from datetime import datetime, timezone

from .impact_types import (
    LiquidityImpactEstimate,
    OrderBookDepth,
    ImpactSummary,
    SLIPPAGE_THRESHOLDS,
    IMPACT_MODIFIERS,
)
from .impact_engine import LiquidityImpactEngine


@pytest.fixture
def engine():
    return LiquidityImpactEngine()


@pytest.fixture
def sample_depth():
    return OrderBookDepth(
        symbol="BTC",
        bid_depth_1pct=5000000,
        ask_depth_1pct=5000000,
        spread_bps=5,
        imbalance_ratio=0.1,
    )


# ══════════════════════════════════════════════════════════════
# 1. Slippage Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_slippage_calculation_basic(engine):
    """Test basic slippage calculation."""
    slippage = engine.calculate_slippage(100000, 5000000)
    # 100k / 5M = 0.02, * 10000 = 200 bps, but capped at 100
    assert slippage == 100.0  # Capped at max


def test_slippage_zero_depth(engine):
    """Test slippage with zero depth."""
    slippage = engine.calculate_slippage(100000, 0)
    assert slippage == 100.0  # Max


def test_slippage_large_order(engine):
    """Test slippage for large order."""
    slippage = engine.calculate_slippage(10000000, 5000000)
    assert slippage > 50


# ══════════════════════════════════════════════════════════════
# 2. Market Impact Calculation Tests
# ══════════════════════════════════════════════════════════════

def test_market_impact_calculation(engine):
    """Test market impact formula."""
    impact = engine.calculate_market_impact(10, 5, 3)
    expected = 0.50 * 10 + 0.30 * 5 + 0.20 * 3
    assert impact == expected


def test_market_impact_zero_penalties(engine):
    """Test impact with zero penalties."""
    impact = engine.calculate_market_impact(5, 0, 0)
    assert impact == 2.5  # 0.50 * 5


# ══════════════════════════════════════════════════════════════
# 3. Fill Quality Tests
# ══════════════════════════════════════════════════════════════

def test_fill_quality_low_impact(engine):
    """Test fill quality for low impact."""
    quality = engine.calculate_fill_quality(3)
    assert quality >= 0.9  # Excellent


def test_fill_quality_high_impact(engine):
    """Test fill quality for high impact."""
    quality = engine.calculate_fill_quality(25)
    assert quality < 0.2


def test_fill_quality_max_impact(engine):
    """Test fill quality for max impact."""
    quality = engine.calculate_fill_quality(50)
    assert quality == 0.0


# ══════════════════════════════════════════════════════════════
# 4. Liquidity Bucket Classification Tests
# ══════════════════════════════════════════════════════════════

def test_liquidity_bucket_deep(engine):
    """Test DEEP liquidity classification."""
    bucket = engine.classify_liquidity_bucket(10000000, 3)
    assert bucket == "DEEP"


def test_liquidity_bucket_normal(engine):
    """Test NORMAL liquidity classification."""
    bucket = engine.classify_liquidity_bucket(2000000, 7)
    assert bucket == "NORMAL"


def test_liquidity_bucket_thin(engine):
    """Test THIN liquidity classification."""
    bucket = engine.classify_liquidity_bucket(500000, 15)
    assert bucket == "THIN"


def test_liquidity_bucket_fragile(engine):
    """Test FRAGILE liquidity classification."""
    bucket = engine.classify_liquidity_bucket(50000, 30)
    assert bucket == "FRAGILE"


# ══════════════════════════════════════════════════════════════
# 5. Impact State Classification Tests
# ══════════════════════════════════════════════════════════════

def test_impact_state_low(engine):
    """Test LOW_IMPACT classification."""
    state = engine.classify_impact_state(3)
    assert state == "LOW_IMPACT"


def test_impact_state_manageable(engine):
    """Test MANAGEABLE classification."""
    state = engine.classify_impact_state(10)
    assert state == "MANAGEABLE"


def test_impact_state_high(engine):
    """Test HIGH_IMPACT classification."""
    state = engine.classify_impact_state(20)
    assert state == "HIGH_IMPACT"


def test_impact_state_untradeable(engine):
    """Test UNTRADEABLE classification."""
    state = engine.classify_impact_state(50)
    assert state == "UNTRADEABLE"


# ══════════════════════════════════════════════════════════════
# 6. Recommendation Mapping Tests
# ══════════════════════════════════════════════════════════════

def test_recommendation_low_impact(engine):
    """Test recommendation for low impact."""
    rec = engine.get_execution_recommendation("LOW_IMPACT")
    assert rec == "MARKET_OK"


def test_recommendation_manageable(engine):
    """Test recommendation for manageable."""
    rec = engine.get_execution_recommendation("MANAGEABLE")
    assert rec == "LIMIT_PREFERRED"


def test_recommendation_high_impact(engine):
    """Test recommendation for high impact."""
    rec = engine.get_execution_recommendation("HIGH_IMPACT")
    assert rec == "TWAP_REQUIRED"


def test_recommendation_untradeable(engine):
    """Test recommendation for untradeable."""
    rec = engine.get_execution_recommendation("UNTRADEABLE")
    assert rec == "BLOCK_TRADE"


# ══════════════════════════════════════════════════════════════
# 7. Size Modifier Tests
# ══════════════════════════════════════════════════════════════

def test_size_modifier_values():
    """Test size modifier values."""
    assert IMPACT_MODIFIERS["LOW_IMPACT"] == 1.0
    assert IMPACT_MODIFIERS["MANAGEABLE"] == 0.85
    assert IMPACT_MODIFIERS["HIGH_IMPACT"] == 0.60
    assert IMPACT_MODIFIERS["UNTRADEABLE"] == 0.0


# ══════════════════════════════════════════════════════════════
# 8. Full Estimate Tests
# ══════════════════════════════════════════════════════════════

def test_estimate_impact_returns_valid(engine):
    """Test full impact estimate."""
    estimate = engine.estimate_impact("BTC", 100000, "BUY")
    
    assert isinstance(estimate, LiquidityImpactEstimate)
    assert estimate.symbol == "BTC"
    assert estimate.intended_size_usd == 100000
    assert estimate.side == "BUY"
    assert estimate.expected_slippage_bps >= 0
    assert 0 <= estimate.expected_fill_quality <= 1


def test_estimate_impact_sell(engine):
    """Test estimate for SELL side."""
    estimate = engine.estimate_impact("ETH", 50000, "SELL")
    
    assert estimate.side == "SELL"


# ══════════════════════════════════════════════════════════════
# 9. Execution Plan Adjustment Tests
# ══════════════════════════════════════════════════════════════

def test_adjust_execution_plan(engine):
    """Test execution plan adjustment."""
    result = engine.adjust_execution_plan("BTC", 100000, "BUY", "MARKET")
    
    assert "adjusted_size_usd" in result
    assert "adjusted_execution_type" in result
    assert "impact_estimate" in result


def test_size_reduction_applied(engine):
    """Test size reduction is applied."""
    result = engine.adjust_execution_plan("BTC", 100000, "BUY", "MARKET")
    
    assert result["adjusted_size_usd"] <= 100000


# ══════════════════════════════════════════════════════════════
# 10. Caching Tests
# ══════════════════════════════════════════════════════════════

def test_estimate_cached(engine):
    """Test estimate is cached."""
    estimate1 = engine.estimate_impact("BTC", 100000, "BUY")
    cached = engine.get_current_estimate("BTC")
    
    assert cached is not None
    assert cached.symbol == estimate1.symbol


def test_history_stored(engine):
    """Test history is stored."""
    engine.estimate_impact("BTC", 100000, "BUY")
    engine.estimate_impact("BTC", 200000, "SELL")
    
    history = engine.get_history("BTC")
    assert len(history) >= 2


# ══════════════════════════════════════════════════════════════
# 11. Summary Tests
# ══════════════════════════════════════════════════════════════

def test_summary_generation(engine):
    """Test summary generation."""
    engine.estimate_impact("BTC", 100000, "BUY")
    
    summary = engine.generate_summary("BTC")
    
    assert summary.symbol == "BTC"
    assert summary.total_estimates >= 1


# ══════════════════════════════════════════════════════════════
# 12. Edge Cases
# ══════════════════════════════════════════════════════════════

def test_missing_data_safe(engine):
    """Test handling of missing data."""
    estimate = engine.estimate_impact("UNKNOWN", 100000, "BUY")
    
    assert estimate is not None
    assert estimate.symbol == "UNKNOWN"


def test_deterministic_output(engine):
    """Test deterministic output."""
    e1 = engine.estimate_impact("BTC", 100000, "BUY")
    e2 = engine.estimate_impact("BTC", 100000, "BUY")
    
    # Slippage should be same for same inputs
    assert e1.expected_slippage_bps == e2.expected_slippage_bps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
