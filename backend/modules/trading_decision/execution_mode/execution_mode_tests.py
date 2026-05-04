"""
PHASE 14.6 — Execution Mode Tests
==================================
Unit tests for Execution Mode Engine.

Test cases:
1. ALLOW_AGGRESSIVE + high confidence + low conflict → AGGRESSIVE
2. ALLOW + neutral state → NORMAL
3. ALLOW_REDUCED + conflict → PASSIVE
4. ALLOW + high squeeze risk → PARTIAL_ENTRY
5. ALLOW + expanding volatility + hostile market → DELAYED
6. BLOCK / WAIT → NONE
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.execution_mode.execution_mode_types import (
    ExecutionModeDecision,
    ExecutionMode,
    EntryStyle,
    DecisionInputSnapshot,
    SizingInputSnapshot,
    ExchangeInputSnapshot,
    MarketStateInputSnapshot,
)
from modules.trading_decision.execution_mode.execution_mode_engine import ExecutionModeEngine


class MockExecutionModeEngine(ExecutionModeEngine):
    """Engine with mock inputs for testing."""
    
    def __init__(self):
        self._decision_input = None
        self._sizing_input = None
        self._exchange_input = None
        self._market_state_input = None
    
    def set_mock_inputs(
        self,
        decision: DecisionInputSnapshot,
        sizing: SizingInputSnapshot,
        exchange: ExchangeInputSnapshot,
        market_state: MarketStateInputSnapshot,
    ):
        """Set mock inputs."""
        self._decision_input = decision
        self._sizing_input = sizing
        self._exchange_input = exchange
        self._market_state_input = market_state
    
    def _get_decision_input(self, symbol: str) -> DecisionInputSnapshot:
        return self._decision_input
    
    def _get_sizing_input(self, symbol: str) -> SizingInputSnapshot:
        return self._sizing_input
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputSnapshot:
        return self._exchange_input
    
    def _get_market_state_input(self, symbol: str) -> MarketStateInputSnapshot:
        return self._market_state_input


def test_1_aggressive_high_confidence():
    """Test 1: ALLOW_AGGRESSIVE + high confidence + low conflict → AGGRESSIVE"""
    engine = MockExecutionModeEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW_AGGRESSIVE",
        direction="LONG",
        confidence=0.85,
        execution_mode_hint="AGGRESSIVE",
    )
    
    sizing = SizingInputSnapshot(
        final_size_pct=1.25,
        size_bucket="LARGE",
        risk_multiplier=1.2,
    )
    
    exchange = ExchangeInputSnapshot(
        conflict_ratio=0.15,
        dominant_signal="flow",
        squeeze_probability=0.2,
        confidence=0.8,
        crowding_risk=0.25,
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="LOW",
        exchange_state="BULLISH",
        derivatives_state="BALANCED",
        combined_state="TRENDING_LOW_VOL_BULLISH",
        risk_state="RISK_ON",
    )
    
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("BTC")
    
    assert result.execution_mode == ExecutionMode.AGGRESSIVE
    assert result.entry_style == EntryStyle.MARKET
    assert result.partial_ratio == 1.0
    assert result.urgency_score > 0.6
    
    print(f"TEST 1 PASSED: mode={result.execution_mode.value}, urgency={result.urgency_score:.4f}")
    print(f"  slippage={result.slippage_tolerance:.4f}, entry_style={result.entry_style.value}")
    return True


def test_2_allow_neutral_normal():
    """Test 2: ALLOW + neutral state → NORMAL"""
    engine = MockExecutionModeEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW",
        direction="LONG",
        confidence=0.65,
        execution_mode_hint="NORMAL",
    )
    
    sizing = SizingInputSnapshot(
        final_size_pct=0.85,
        size_bucket="NORMAL",
        risk_multiplier=0.9,
    )
    
    exchange = ExchangeInputSnapshot(
        conflict_ratio=0.25,
        dominant_signal="volume",
        squeeze_probability=0.3,
        confidence=0.6,
        crowding_risk=0.3,
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="NORMAL",
        exchange_state="NEUTRAL",
        derivatives_state="BALANCED",
        combined_state="RANGE_LOW_VOL_NEUTRAL",
        risk_state="NEUTRAL",
    )
    
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("ETH")
    
    assert result.execution_mode == ExecutionMode.NORMAL
    assert result.entry_style == EntryStyle.LIMIT
    assert result.partial_ratio == 1.0
    
    print(f"TEST 2 PASSED: mode={result.execution_mode.value}, urgency={result.urgency_score:.4f}")
    print(f"  slippage={result.slippage_tolerance:.4f}, entry_style={result.entry_style.value}")
    return True


def test_3_allow_reduced_conflict_passive():
    """Test 3: ALLOW_REDUCED + conflict → PASSIVE"""
    engine = MockExecutionModeEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW_REDUCED",
        direction="LONG",
        confidence=0.55,
        execution_mode_hint="PASSIVE",
    )
    
    sizing = SizingInputSnapshot(
        final_size_pct=0.45,
        size_bucket="SMALL",
        risk_multiplier=0.5,
    )
    
    exchange = ExchangeInputSnapshot(
        conflict_ratio=0.45,
        dominant_signal="funding",
        squeeze_probability=0.35,
        confidence=0.55,
        crowding_risk=0.4,
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="NORMAL",
        exchange_state="BEARISH",
        derivatives_state="BALANCED",
        combined_state="RANGE_LOW_VOL_NEUTRAL",
        risk_state="NEUTRAL",
    )
    
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("SOL")
    
    assert result.execution_mode == ExecutionMode.PASSIVE
    assert result.entry_style == EntryStyle.LIMIT
    assert result.partial_ratio == 1.0
    
    print(f"TEST 3 PASSED: mode={result.execution_mode.value}, urgency={result.urgency_score:.4f}")
    print(f"  slippage={result.slippage_tolerance:.4f}, entry_style={result.entry_style.value}")
    return True


def test_4_allow_high_squeeze_partial():
    """Test 4: ALLOW + high squeeze risk → PARTIAL_ENTRY"""
    engine = MockExecutionModeEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW",
        direction="LONG",
        confidence=0.65,
        execution_mode_hint="NORMAL",
    )
    
    sizing = SizingInputSnapshot(
        final_size_pct=0.75,
        size_bucket="NORMAL",
        risk_multiplier=0.85,
    )
    
    exchange = ExchangeInputSnapshot(
        conflict_ratio=0.35,
        dominant_signal="liquidations",
        squeeze_probability=0.65,  # High squeeze
        confidence=0.6,
        crowding_risk=0.55,
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="NORMAL",
        exchange_state="NEUTRAL",
        derivatives_state="SQUEEZE",
        combined_state="UNDEFINED",
        risk_state="NEUTRAL",
    )
    
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("BTC")
    
    assert result.execution_mode == ExecutionMode.PARTIAL_ENTRY
    assert result.entry_style == EntryStyle.STAGED
    assert 0.3 <= result.partial_ratio <= 0.6
    
    print(f"TEST 4 PASSED: mode={result.execution_mode.value}, partial_ratio={result.partial_ratio:.4f}")
    print(f"  slippage={result.slippage_tolerance:.4f}, entry_style={result.entry_style.value}")
    return True


def test_5_allow_hostile_delayed():
    """Test 5: ALLOW + expanding volatility + hostile market → DELAYED"""
    engine = MockExecutionModeEngine()
    
    decision = DecisionInputSnapshot(
        action="ALLOW",
        direction="LONG",
        confidence=0.5,  # Lower confidence
        execution_mode_hint="NORMAL",
    )
    
    sizing = SizingInputSnapshot(
        final_size_pct=0.6,
        size_bucket="SMALL",
        risk_multiplier=0.7,
    )
    
    exchange = ExchangeInputSnapshot(
        conflict_ratio=0.55,
        dominant_signal="liquidations",
        squeeze_probability=0.45,
        confidence=0.5,
        crowding_risk=0.5,
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="EXPANDING",  # Hostile
        exchange_state="BEARISH",
        derivatives_state="SQUEEZE",
        combined_state="BEARISH_HIGH_VOL_SQUEEZE",  # Hostile state
        risk_state="RISK_OFF",
    )
    
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("ETH")
    
    assert result.execution_mode == ExecutionMode.DELAYED
    assert result.entry_style == EntryStyle.WAIT
    assert result.partial_ratio == 0.0
    assert result.urgency_score == 0.0
    
    print(f"TEST 5 PASSED: mode={result.execution_mode.value}, urgency={result.urgency_score:.4f}")
    print(f"  partial_ratio={result.partial_ratio:.4f}, entry_style={result.entry_style.value}")
    return True


def test_6_block_wait_none():
    """Test 6: BLOCK / WAIT → NONE"""
    engine = MockExecutionModeEngine()
    
    # Test BLOCK
    decision = DecisionInputSnapshot(
        action="BLOCK",
        direction="NEUTRAL",
        confidence=0.3,
        execution_mode_hint="NONE",
    )
    
    sizing = SizingInputSnapshot(
        final_size_pct=0.0,
        size_bucket="NONE",
        risk_multiplier=0.0,
    )
    
    exchange = ExchangeInputSnapshot(
        conflict_ratio=0.7,
        dominant_signal="liquidations",
        squeeze_probability=0.6,
        confidence=0.6,
        crowding_risk=0.6,
    )
    
    market_state = MarketStateInputSnapshot(
        volatility_state="HIGH",
        exchange_state="BEARISH",
        derivatives_state="SQUEEZE",
        combined_state="BEARISH_HIGH_VOL_SQUEEZE",
        risk_state="RISK_OFF",
    )
    
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("BTC")
    
    assert result.execution_mode == ExecutionMode.NONE
    assert result.entry_style == EntryStyle.WAIT
    assert result.partial_ratio == 0.0
    
    print(f"TEST 6a (BLOCK) PASSED: mode={result.execution_mode.value}")
    
    # Test WAIT
    decision.action = "WAIT"
    engine.set_mock_inputs(decision, sizing, exchange, market_state)
    result = engine.compute("BTC")
    
    assert result.execution_mode == ExecutionMode.NONE
    
    print(f"TEST 6b (WAIT) PASSED: mode={result.execution_mode.value}")
    return True


def run_all_tests():
    """Run all execution mode tests."""
    print("\n" + "=" * 60)
    print("PHASE 14.6 — Execution Mode Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: ALLOW_AGGRESSIVE + high confidence → AGGRESSIVE", test_1_aggressive_high_confidence),
        ("Test 2: ALLOW + neutral state → NORMAL", test_2_allow_neutral_normal),
        ("Test 3: ALLOW_REDUCED + conflict → PASSIVE", test_3_allow_reduced_conflict_passive),
        ("Test 4: ALLOW + high squeeze → PARTIAL_ENTRY", test_4_allow_high_squeeze_partial),
        ("Test 5: ALLOW + expanding vol + hostile → DELAYED", test_5_allow_hostile_delayed),
        ("Test 6: BLOCK / WAIT → NONE", test_6_block_wait_none),
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
