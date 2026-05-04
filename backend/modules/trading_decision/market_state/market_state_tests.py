"""
PHASE 14.3 — Market State Matrix Tests
========================================
Unit tests for Market State Matrix builder.

Test cases:
1. Strong bullish trend + bullish exchange
2. Strong bearish trend + bearish exchange
3. Range + conflicted exchange
4. Trend up + bearish exchange conflict
5. High vol + squeeze regime
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.market_state.market_state_types import (
    MarketStateMatrix,
    TrendState,
    VolatilityState,
    ExchangeState,
    DerivativesState,
    BreadthState,
    RiskState,
    CombinedState,
    TAInputSnapshot,
    ExchangeInputSnapshot,
    VolatilityInputSnapshot,
)
from modules.trading_decision.market_state.market_state_builder import MarketStateBuilder


class MockMarketStateBuilder(MarketStateBuilder):
    """Builder with mock inputs for testing."""
    
    def __init__(self):
        self._ta_input = None
        self._exchange_input = None
        self._volatility_input = None
    
    def set_mock_inputs(
        self,
        ta: TAInputSnapshot,
        exchange: ExchangeInputSnapshot,
        vol: VolatilityInputSnapshot,
    ):
        """Set mock inputs."""
        self._ta_input = ta
        self._exchange_input = exchange
        self._volatility_input = vol
    
    def _get_ta_input(self, symbol: str) -> TAInputSnapshot:
        return self._ta_input
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputSnapshot:
        return self._exchange_input
    
    def _get_volatility_input(self, symbol: str) -> VolatilityInputSnapshot:
        return self._volatility_input


def test_1_strong_bullish_trend_bullish_exchange():
    """Test 1: Strong bullish trend + bullish exchange."""
    builder = MockMarketStateBuilder()
    
    ta = TAInputSnapshot(
        direction="LONG",
        regime="TREND_UP",
        setup_quality=0.8,
        trend_strength=0.85,
        conviction=0.82,
        entry_quality=0.75,
        regime_fit=0.9,
    )
    
    exchange = ExchangeInputSnapshot(
        bias="BULLISH",
        dominant_signal="flow",
        confidence=0.78,
        conflict_ratio=0.1,
        crowding_risk=0.3,
        squeeze_probability=0.2,
        cascade_probability=0.1,
        derivatives_pressure=0.4,
        flow_pressure=0.6,
    )
    
    vol = VolatilityInputSnapshot(
        atr_normalized=0.025,
        volatility_percentile=0.65,
        volatility_regime="NORMAL",
        recent_range=0.08,
    )
    
    builder.set_mock_inputs(ta, exchange, vol)
    result = builder.build("BTC")
    
    assert result.trend_state == TrendState.TREND_UP
    assert result.exchange_state == ExchangeState.BULLISH
    assert result.risk_state == RiskState.RISK_ON
    assert result.confidence > 0.7
    
    print(f"TEST 1 PASSED: {result.to_dict()}")
    return True


def test_2_strong_bearish_trend_bearish_exchange():
    """Test 2: Strong bearish trend + bearish exchange."""
    builder = MockMarketStateBuilder()
    
    ta = TAInputSnapshot(
        direction="SHORT",
        regime="TREND_DOWN",
        setup_quality=0.75,
        trend_strength=0.8,
        conviction=0.78,
        entry_quality=0.7,
        regime_fit=0.85,
    )
    
    exchange = ExchangeInputSnapshot(
        bias="BEARISH",
        dominant_signal="liquidation",
        confidence=0.8,
        conflict_ratio=0.15,
        crowding_risk=0.4,
        squeeze_probability=0.3,
        cascade_probability=0.5,
        derivatives_pressure=-0.5,
        flow_pressure=-0.4,
    )
    
    vol = VolatilityInputSnapshot(
        atr_normalized=0.035,
        volatility_percentile=0.85,
        volatility_regime="HIGH",
        recent_range=0.12,
    )
    
    builder.set_mock_inputs(ta, exchange, vol)
    result = builder.build("BTC")
    
    assert result.trend_state == TrendState.TREND_DOWN
    assert result.exchange_state == ExchangeState.BEARISH
    assert result.risk_state == RiskState.RISK_OFF
    
    print(f"TEST 2 PASSED: {result.to_dict()}")
    return True


def test_3_range_conflicted_exchange():
    """Test 3: Range + conflicted exchange."""
    builder = MockMarketStateBuilder()
    
    ta = TAInputSnapshot(
        direction="NEUTRAL",
        regime="RANGE",
        setup_quality=0.4,
        trend_strength=0.2,
        conviction=0.35,
        entry_quality=0.5,
        regime_fit=0.6,
    )
    
    exchange = ExchangeInputSnapshot(
        bias="NEUTRAL",
        dominant_signal="none",
        confidence=0.5,
        conflict_ratio=0.7,  # High conflict
        crowding_risk=0.2,
        squeeze_probability=0.15,
        cascade_probability=0.2,
        derivatives_pressure=0.1,
        flow_pressure=-0.05,
    )
    
    vol = VolatilityInputSnapshot(
        atr_normalized=0.015,
        volatility_percentile=0.2,
        volatility_regime="LOW",
        recent_range=0.03,
    )
    
    builder.set_mock_inputs(ta, exchange, vol)
    result = builder.build("ETH")
    
    assert result.trend_state == TrendState.RANGE
    assert result.exchange_state == ExchangeState.CONFLICTED
    assert result.combined_state == CombinedState.CHOP_CONFLICTED
    
    print(f"TEST 3 PASSED: {result.to_dict()}")
    return True


def test_4_trend_up_bearish_exchange_conflict():
    """Test 4: Trend up + bearish exchange = conflict scenario."""
    builder = MockMarketStateBuilder()
    
    ta = TAInputSnapshot(
        direction="LONG",
        regime="TREND_UP",
        setup_quality=0.7,
        trend_strength=0.65,
        conviction=0.6,
        entry_quality=0.65,
        regime_fit=0.7,
    )
    
    exchange = ExchangeInputSnapshot(
        bias="BEARISH",
        dominant_signal="funding",
        confidence=0.65,
        conflict_ratio=0.4,
        crowding_risk=0.55,
        squeeze_probability=0.4,
        cascade_probability=0.35,
        derivatives_pressure=-0.3,
        flow_pressure=-0.2,
    )
    
    vol = VolatilityInputSnapshot(
        atr_normalized=0.028,
        volatility_percentile=0.7,
        volatility_regime="NORMAL",
        recent_range=0.09,
    )
    
    builder.set_mock_inputs(ta, exchange, vol)
    result = builder.build("SOL")
    
    # TA says LONG but exchange is BEARISH - this is a warning
    assert result.trend_state == TrendState.TREND_UP
    assert result.exchange_state == ExchangeState.BEARISH
    # Risk should be NEUTRAL due to conflict
    assert result.risk_state == RiskState.NEUTRAL
    
    print(f"TEST 4 PASSED: {result.to_dict()}")
    return True


def test_5_high_vol_squeeze_regime():
    """Test 5: High volatility + squeeze regime."""
    builder = MockMarketStateBuilder()
    
    ta = TAInputSnapshot(
        direction="SHORT",
        regime="TREND_DOWN",
        setup_quality=0.65,
        trend_strength=0.7,
        conviction=0.68,
        entry_quality=0.6,
        regime_fit=0.75,
    )
    
    exchange = ExchangeInputSnapshot(
        bias="BEARISH",
        dominant_signal="derivatives",
        confidence=0.75,
        conflict_ratio=0.2,
        crowding_risk=0.7,  # High crowding
        squeeze_probability=0.65,  # High squeeze probability
        cascade_probability=0.55,
        derivatives_pressure=-0.6,
        flow_pressure=-0.3,
    )
    
    vol = VolatilityInputSnapshot(
        atr_normalized=0.045,
        volatility_percentile=0.92,
        volatility_regime="HIGH",
        recent_range=0.15,
    )
    
    builder.set_mock_inputs(ta, exchange, vol)
    result = builder.build("BTC")
    
    assert result.volatility_state == VolatilityState.HIGH
    assert result.derivatives_state == DerivativesState.SQUEEZE
    assert result.combined_state == CombinedState.BEARISH_HIGH_VOL_SQUEEZE
    
    print(f"TEST 5 PASSED: {result.to_dict()}")
    return True


def run_all_tests():
    """Run all market state tests."""
    print("\n" + "=" * 60)
    print("PHASE 14.3 — Market State Matrix Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Strong bullish trend + bullish exchange", test_1_strong_bullish_trend_bullish_exchange),
        ("Test 2: Strong bearish trend + bearish exchange", test_2_strong_bearish_trend_bearish_exchange),
        ("Test 3: Range + conflicted exchange", test_3_range_conflicted_exchange),
        ("Test 4: Trend up + bearish exchange conflict", test_4_trend_up_bearish_exchange_conflict),
        ("Test 5: High vol + squeeze regime", test_5_high_vol_squeeze_regime),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
        except AssertionError as e:
            print(f"FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name}")
            print(f"  Exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)
    
    return passed == len(tests)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
