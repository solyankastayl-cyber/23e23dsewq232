"""
PHASE 14.5 — Position Sizing Tests
===================================
Unit tests for Position Sizing Engine.

Test cases:
1. ALLOW_AGGRESSIVE + low vol + strong exchange → LARGE
2. ALLOW + neutral market → NORMAL
3. ALLOW_REDUCED + conflict → SMALL
4. BLOCK → NONE
5. WAIT → NONE
6. ALLOW but high volatility + squeeze → TINY/SMALL
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.position_sizing.position_sizing_types import (
    PositionSizingDecision,
    SizeBucket,
    DecisionInputSnapshot,
    TAInputSnapshot,
    ExchangeInputSnapshot,
    MarketStateInputSnapshot,
)
from modules.trading_decision.position_sizing.position_sizing_engine import PositionSizingEngine


class MockPositionSizingEngine(PositionSizingEngine):
    """Engine with mock inputs for testing."""
    
    def __init__(self):
        self._decision_input = None
        self._ta_input = None
        self._exchange_input = None
        self._market_state_input = None
    
    def set_mock_inputs(
        self,
        decision: DecisionInputSnapshot,
        ta: TAInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
    ):
        """Set mock inputs."""
        self._decision_input = decision
        self._ta_input = ta
        self._exchange_input = exchange
        self._market_state_input = market_state
    
    def _get_decision_input(self, symbol: str) -> DecisionInputSnapshot:
        return self._decision_input
    
    def _get_ta_input(self, symbol: str) -> TAInputSnapshot:
        return self._ta_input
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputSnapshot:
        return self._exchange_input
    
    def _get_market_state_input(self, symbol: str) -> MarketStateInputSnapshot:
        return self._market_state_input


def test_1_aggressive_low_vol_strong_exchange_large():
    """Test 1: ALLOW_AGGRESSIVE + low vol + strong exchange → LARGE"""
    engine = MockPositionSizingEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW_AGGRESSIVE",
        direction="LONG",
        confidence=0.88,
        position_multiplier=1.2,
        execution_mode="AGGRESSIVE",
    )
    
    ta = TAInputSnapshot(
        setup_quality=0.85,
        entry_quality=0.8,
        conviction=0.85,
        trend_strength=0.9,
    )
    
    exchange = ExchangeInputSnapshot(
        confidence=0.82,
        conflict_ratio=0.1,
        crowding_risk=0.2,
        squeeze_probability=0.15,
        bias="BULLISH",
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="LOW",
        derivatives_state="BALANCED",
        risk_state="RISK_ON",
        combined_state="TRENDING_LOW_VOL_BULLISH",
        confidence=0.85,
    )
    
    engine.set_mock_inputs(decision, ta, exchange, market_state)
    result = engine.compute("BTC")
    
    assert result.size_bucket == SizeBucket.LARGE
    assert result.final_size_pct > 1.05
    assert result.volatility_adjustment >= 1.0
    assert result.exchange_adjustment >= 1.0
    
    print(f"TEST 1 PASSED: bucket={result.size_bucket.value}, size={result.final_size_pct:.4f}")
    print(f"  Adjustments: vol={result.volatility_adjustment:.3f}, ex={result.exchange_adjustment:.3f}, mkt={result.market_adjustment:.3f}")
    return True


def test_2_allow_neutral_market_normal():
    """Test 2: ALLOW + neutral market → NORMAL"""
    engine = MockPositionSizingEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW",
        direction="LONG",
        confidence=0.65,
        position_multiplier=0.9,
        execution_mode="NORMAL",
    )
    
    ta = TAInputSnapshot(
        setup_quality=0.65,
        entry_quality=0.6,
        conviction=0.65,
        trend_strength=0.6,
    )
    
    exchange = ExchangeInputSnapshot(
        confidence=0.6,
        conflict_ratio=0.25,
        crowding_risk=0.25,
        squeeze_probability=0.2,
        bias="NEUTRAL",
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="NORMAL",
        derivatives_state="BALANCED",
        risk_state="NEUTRAL",
        combined_state="RANGE_LOW_VOL_NEUTRAL",
        confidence=0.6,
    )
    
    engine.set_mock_inputs(decision, ta, exchange, market_state)
    result = engine.compute("ETH")
    
    assert result.size_bucket == SizeBucket.NORMAL
    assert 0.70 <= result.final_size_pct <= 1.05
    
    print(f"TEST 2 PASSED: bucket={result.size_bucket.value}, size={result.final_size_pct:.4f}")
    print(f"  Adjustments: vol={result.volatility_adjustment:.3f}, ex={result.exchange_adjustment:.3f}, mkt={result.market_adjustment:.3f}")
    return True


def test_3_allow_reduced_conflict_small():
    """Test 3: ALLOW_REDUCED + conflict → SMALL"""
    engine = MockPositionSizingEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW_REDUCED",
        direction="LONG",
        confidence=0.55,
        position_multiplier=0.5,
        execution_mode="PASSIVE",
    )
    
    ta = TAInputSnapshot(
        setup_quality=0.55,
        entry_quality=0.5,
        conviction=0.55,
        trend_strength=0.5,
    )
    
    exchange = ExchangeInputSnapshot(
        confidence=0.55,
        conflict_ratio=0.5,
        crowding_risk=0.45,
        squeeze_probability=0.35,
        bias="BEARISH",
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="NORMAL",
        derivatives_state="BALANCED",
        risk_state="NEUTRAL",
        combined_state="RANGE_LOW_VOL_NEUTRAL",
        confidence=0.55,
    )
    
    engine.set_mock_inputs(decision, ta, exchange, market_state)
    result = engine.compute("SOL")
    
    assert result.size_bucket == SizeBucket.SMALL
    assert 0.35 <= result.final_size_pct <= 0.70
    
    print(f"TEST 3 PASSED: bucket={result.size_bucket.value}, size={result.final_size_pct:.4f}")
    print(f"  Adjustments: vol={result.volatility_adjustment:.3f}, ex={result.exchange_adjustment:.3f}, mkt={result.market_adjustment:.3f}")
    return True


def test_4_block_none():
    """Test 4: BLOCK → NONE"""
    engine = MockPositionSizingEngine()
    
    decision = DecisionInputSnapshot(
        action="BLOCK",
        direction="NEUTRAL",
        confidence=0.3,
        position_multiplier=0.0,
        execution_mode="NONE",
    )
    
    ta = TAInputSnapshot(
        setup_quality=0.5,
        entry_quality=0.5,
        conviction=0.4,
        trend_strength=0.4,
    )
    
    exchange = ExchangeInputSnapshot(
        confidence=0.7,
        conflict_ratio=0.7,
        crowding_risk=0.6,
        squeeze_probability=0.5,
        bias="BEARISH",
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="HIGH",
        derivatives_state="SQUEEZE",
        risk_state="RISK_OFF",
        combined_state="BEARISH_HIGH_VOL_SQUEEZE",
        confidence=0.65,
    )
    
    engine.set_mock_inputs(decision, ta, exchange, market_state)
    result = engine.compute("BTC")
    
    assert result.size_bucket == SizeBucket.NONE
    assert result.final_size_pct == 0.0
    assert result.risk_multiplier == 0.0
    
    print(f"TEST 4 PASSED: bucket={result.size_bucket.value}, size={result.final_size_pct:.4f}")
    return True


def test_5_wait_none():
    """Test 5: WAIT → NONE"""
    engine = MockPositionSizingEngine()
    
    decision = DecisionInputSnapshot(
        action="WAIT",
        direction="NEUTRAL",
        confidence=0.2,
        position_multiplier=0.0,
        execution_mode="WAIT",
    )
    
    ta = TAInputSnapshot(
        setup_quality=0.2,
        entry_quality=0.4,
        conviction=0.2,
        trend_strength=0.2,
    )
    
    exchange = ExchangeInputSnapshot(
        confidence=0.5,
        conflict_ratio=0.5,
        crowding_risk=0.3,
        squeeze_probability=0.2,
        bias="NEUTRAL",
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="LOW",
        derivatives_state="BALANCED",
        risk_state="NEUTRAL",
        combined_state="CHOP_CONFLICTED",
        confidence=0.4,
    )
    
    engine.set_mock_inputs(decision, ta, exchange, market_state)
    result = engine.compute("ETH")
    
    assert result.size_bucket == SizeBucket.NONE
    assert result.final_size_pct == 0.0
    
    print(f"TEST 5 PASSED: bucket={result.size_bucket.value}, size={result.final_size_pct:.4f}")
    return True


def test_6_allow_high_vol_squeeze_tiny():
    """Test 6: ALLOW but high volatility + squeeze → TINY/SMALL"""
    engine = MockPositionSizingEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW",
        direction="LONG",
        confidence=0.6,
        position_multiplier=0.85,
        execution_mode="PASSIVE",
    )
    
    ta = TAInputSnapshot(
        setup_quality=0.6,
        entry_quality=0.55,
        conviction=0.6,
        trend_strength=0.55,
    )
    
    exchange = ExchangeInputSnapshot(
        confidence=0.55,
        conflict_ratio=0.4,
        crowding_risk=0.55,
        squeeze_probability=0.6,  # High squeeze
        bias="NEUTRAL",
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="HIGH",  # High volatility
        derivatives_state="SQUEEZE",
        risk_state="NEUTRAL",
        combined_state="UNDEFINED",
        confidence=0.5,
    )
    
    engine.set_mock_inputs(decision, ta, exchange, market_state)
    result = engine.compute("SOL")
    
    assert result.size_bucket in (SizeBucket.TINY, SizeBucket.SMALL)
    assert result.final_size_pct < 0.70
    assert result.volatility_adjustment < 1.0  # Penalized
    assert result.exchange_adjustment < 1.0  # Penalized
    
    print(f"TEST 6 PASSED: bucket={result.size_bucket.value}, size={result.final_size_pct:.4f}")
    print(f"  Adjustments: vol={result.volatility_adjustment:.3f}, ex={result.exchange_adjustment:.3f}, mkt={result.market_adjustment:.3f}")
    return True


def run_all_tests():
    """Run all position sizing tests."""
    print("\n" + "=" * 60)
    print("PHASE 14.5 — Position Sizing Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: ALLOW_AGGRESSIVE + low vol + strong exchange → LARGE", test_1_aggressive_low_vol_strong_exchange_large),
        ("Test 2: ALLOW + neutral market → NORMAL", test_2_allow_neutral_market_normal),
        ("Test 3: ALLOW_REDUCED + conflict → SMALL", test_3_allow_reduced_conflict_small),
        ("Test 4: BLOCK → NONE", test_4_block_none),
        ("Test 5: WAIT → NONE", test_5_wait_none),
        ("Test 6: ALLOW + high vol + squeeze → TINY/SMALL", test_6_allow_high_vol_squeeze_tiny),
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
