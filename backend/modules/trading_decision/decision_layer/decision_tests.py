"""
PHASE 14.4 — Trading Decision Tests
=====================================
Unit tests for Trading Decision Engine.

Test cases:
1. TA LONG + Exchange LONG + supportive market → ALLOW_AGGRESSIVE
2. TA LONG + Exchange NEUTRAL → ALLOW
3. TA LONG + weak Exchange SHORT conflict → ALLOW_REDUCED
4. TA LONG + strong Exchange SHORT conflict → BLOCK
5. TA LONG + hostile squeeze context → REVERSE_CANDIDATE
6. No setup + unclear market → WAIT
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.decision_layer.decision_types import (
    TradingDecision,
    DecisionAction,
    ExecutionMode,
    TradeDirection,
    DecisionRule,
    TADecisionInput,
    ExchangeDecisionInput,
    MarketStateDecisionInput,
)
from modules.trading_decision.decision_layer.decision_engine import DecisionEngine


class MockDecisionEngine(DecisionEngine):
    """Engine with mock inputs for testing."""
    
    def __init__(self):
        self._ta_input = None
        self._exchange_input = None
        self._market_state_input = None
    
    def set_mock_inputs(
        self,
        ta: TADecisionInput,
        exchange: ExchangeDecisionInput,
        market_state: MarketStateDecisionInput,
    ):
        """Set mock inputs."""
        self._ta_input = ta
        self._exchange_input = exchange
        self._market_state_input = market_state
    
    def _get_ta_input(self, symbol: str) -> TADecisionInput:
        return self._ta_input
    
    def _get_exchange_input(self, symbol: str) -> ExchangeDecisionInput:
        return self._exchange_input
    
    def _get_market_state_input(self, symbol: str) -> MarketStateDecisionInput:
        return self._market_state_input


def test_1_strong_agreement_allow_aggressive():
    """Test 1: TA LONG + Exchange LONG + supportive market → ALLOW_AGGRESSIVE"""
    engine = MockDecisionEngine()
    
    ta = TADecisionInput(
        direction="LONG",
        setup_quality=0.8,
        trend_strength=0.85,
        entry_quality=0.75,
        regime_fit=0.9,
        conviction=0.82,
        setup_type="BREAKOUT",
        has_valid_setup=True,
    )
    
    exchange = ExchangeDecisionInput(
        bias="BULLISH",
        confidence=0.78,
        conflict_ratio=0.1,
        dominant_signal="flow",
        crowding_risk=0.3,
        squeeze_probability=0.2,
        cascade_probability=0.1,
        derivatives_pressure=0.4,
        flow_pressure=0.6,
    )
    
    market_state = MarketStateDecisionInput(
        trend_state="TREND_UP",
        volatility_state="NORMAL",
        exchange_state="BULLISH",
        derivatives_state="BALANCED",
        risk_state="RISK_ON",
        combined_state="TRENDING_LOW_VOL_BULLISH",
        confidence=0.8,
        is_hostile=False,
        is_supportive=True,
    )
    
    engine.set_mock_inputs(ta, exchange, market_state)
    decision = engine.decide("BTC")
    
    assert decision.action == DecisionAction.ALLOW_AGGRESSIVE
    assert decision.direction == TradeDirection.LONG
    assert decision.position_multiplier >= 1.10
    assert decision.execution_mode in (ExecutionMode.AGGRESSIVE, ExecutionMode.NORMAL)
    
    print(f"TEST 1 PASSED: {decision.to_dict()}")
    return True


def test_2_mild_agreement_allow():
    """Test 2: TA LONG + Exchange NEUTRAL → ALLOW"""
    engine = MockDecisionEngine()
    
    ta = TADecisionInput(
        direction="LONG",
        setup_quality=0.65,
        trend_strength=0.6,
        entry_quality=0.65,
        regime_fit=0.7,
        conviction=0.6,
        setup_type="PULLBACK",
        has_valid_setup=True,
    )
    
    exchange = ExchangeDecisionInput(
        bias="NEUTRAL",
        confidence=0.6,
        conflict_ratio=0.2,
        dominant_signal="volume",
        crowding_risk=0.2,
        squeeze_probability=0.15,
        cascade_probability=0.1,
        derivatives_pressure=0.1,
        flow_pressure=0.05,
    )
    
    market_state = MarketStateDecisionInput(
        trend_state="TREND_UP",
        volatility_state="NORMAL",
        exchange_state="NEUTRAL",
        derivatives_state="BALANCED",
        risk_state="NEUTRAL",
        combined_state="RANGE_LOW_VOL_NEUTRAL",
        confidence=0.65,
        is_hostile=False,
        is_supportive=False,
    )
    
    engine.set_mock_inputs(ta, exchange, market_state)
    decision = engine.decide("ETH")
    
    assert decision.action == DecisionAction.ALLOW
    assert decision.direction == TradeDirection.LONG
    assert 0.8 <= decision.position_multiplier <= 1.0
    assert decision.execution_mode == ExecutionMode.NORMAL
    
    print(f"TEST 2 PASSED: {decision.to_dict()}")
    return True


def test_3_weak_conflict_allow_reduced():
    """Test 3: TA LONG + weak Exchange SHORT conflict → ALLOW_REDUCED"""
    engine = MockDecisionEngine()
    
    ta = TADecisionInput(
        direction="LONG",
        setup_quality=0.6,
        trend_strength=0.55,
        entry_quality=0.6,
        regime_fit=0.65,
        conviction=0.55,
        setup_type="CONTINUATION",
        has_valid_setup=True,
    )
    
    exchange = ExchangeDecisionInput(
        bias="BEARISH",
        confidence=0.55,
        conflict_ratio=0.35,  # Weak conflict
        dominant_signal="funding",
        crowding_risk=0.4,
        squeeze_probability=0.3,
        cascade_probability=0.25,
        derivatives_pressure=-0.25,
        flow_pressure=-0.15,
    )
    
    market_state = MarketStateDecisionInput(
        trend_state="TREND_UP",
        volatility_state="NORMAL",
        exchange_state="BEARISH",
        derivatives_state="BALANCED",
        risk_state="NEUTRAL",
        combined_state="RANGE_LOW_VOL_NEUTRAL",
        confidence=0.6,
        is_hostile=False,
        is_supportive=False,
    )
    
    engine.set_mock_inputs(ta, exchange, market_state)
    decision = engine.decide("SOL")
    
    assert decision.action == DecisionAction.ALLOW_REDUCED
    assert decision.direction == TradeDirection.LONG
    assert 0.35 <= decision.position_multiplier <= 0.65
    assert decision.execution_mode == ExecutionMode.PASSIVE
    
    print(f"TEST 3 PASSED: {decision.to_dict()}")
    return True


def test_4_strong_conflict_block():
    """Test 4: TA LONG + strong Exchange SHORT conflict → BLOCK"""
    engine = MockDecisionEngine()
    
    ta = TADecisionInput(
        direction="LONG",
        setup_quality=0.6,
        trend_strength=0.55,
        entry_quality=0.55,
        regime_fit=0.6,
        conviction=0.5,
        setup_type="PULLBACK",
        has_valid_setup=True,
    )
    
    exchange = ExchangeDecisionInput(
        bias="BEARISH",
        confidence=0.7,
        conflict_ratio=0.65,  # Strong conflict
        dominant_signal="liquidation",
        crowding_risk=0.6,
        squeeze_probability=0.45,
        cascade_probability=0.4,
        derivatives_pressure=-0.5,
        flow_pressure=-0.35,
    )
    
    market_state = MarketStateDecisionInput(
        trend_state="TREND_DOWN",
        volatility_state="HIGH",
        exchange_state="BEARISH",
        derivatives_state="BALANCED",
        risk_state="RISK_OFF",
        combined_state="BEARISH_EXPANSION_RISK_OFF",
        confidence=0.65,
        is_hostile=False,
        is_supportive=False,
    )
    
    engine.set_mock_inputs(ta, exchange, market_state)
    decision = engine.decide("BTC")
    
    assert decision.action == DecisionAction.BLOCK
    assert decision.direction == TradeDirection.NEUTRAL
    assert decision.position_multiplier == 0.0
    assert decision.execution_mode == ExecutionMode.NONE
    
    print(f"TEST 4 PASSED: {decision.to_dict()}")
    return True


def test_5_extreme_conflict_reverse_candidate():
    """Test 5: TA LONG + hostile squeeze context → REVERSE_CANDIDATE"""
    engine = MockDecisionEngine()
    
    ta = TADecisionInput(
        direction="LONG",
        setup_quality=0.55,
        trend_strength=0.5,
        entry_quality=0.5,
        regime_fit=0.5,
        conviction=0.45,
        setup_type="REVERSAL",
        has_valid_setup=True,
    )
    
    exchange = ExchangeDecisionInput(
        bias="BEARISH",
        confidence=0.8,
        conflict_ratio=0.75,  # Extreme conflict
        dominant_signal="liquidation",
        crowding_risk=0.75,
        squeeze_probability=0.7,  # High squeeze
        cascade_probability=0.6,  # High cascade
        derivatives_pressure=-0.7,
        flow_pressure=-0.5,
    )
    
    market_state = MarketStateDecisionInput(
        trend_state="TREND_DOWN",
        volatility_state="HIGH",
        exchange_state="BEARISH",
        derivatives_state="SQUEEZE",
        risk_state="RISK_OFF",
        combined_state="BEARISH_HIGH_VOL_SQUEEZE",  # Hostile
        confidence=0.75,
        is_hostile=True,
        is_supportive=False,
    )
    
    engine.set_mock_inputs(ta, exchange, market_state)
    decision = engine.decide("BTC")
    
    assert decision.action == DecisionAction.REVERSE_CANDIDATE
    assert decision.direction == TradeDirection.SHORT  # Flipped
    assert decision.position_multiplier == 0.0
    assert decision.execution_mode == ExecutionMode.WAIT
    
    print(f"TEST 5 PASSED: {decision.to_dict()}")
    return True


def test_6_no_setup_wait():
    """Test 6: No setup + unclear market → WAIT"""
    engine = MockDecisionEngine()
    
    ta = TADecisionInput(
        direction="NEUTRAL",
        setup_quality=0.2,  # Below threshold
        trend_strength=0.2,
        entry_quality=0.4,
        regime_fit=0.5,
        conviction=0.15,  # Very low
        setup_type="NO_SETUP",
        has_valid_setup=False,
    )
    
    exchange = ExchangeDecisionInput(
        bias="NEUTRAL",
        confidence=0.5,
        conflict_ratio=0.5,
        dominant_signal="none",
        crowding_risk=0.3,
        squeeze_probability=0.2,
        cascade_probability=0.2,
        derivatives_pressure=0.0,
        flow_pressure=0.0,
    )
    
    market_state = MarketStateDecisionInput(
        trend_state="RANGE",
        volatility_state="LOW",
        exchange_state="CONFLICTED",
        derivatives_state="BALANCED",
        risk_state="NEUTRAL",
        combined_state="CHOP_CONFLICTED",
        confidence=0.4,
        is_hostile=True,
        is_supportive=False,
    )
    
    engine.set_mock_inputs(ta, exchange, market_state)
    decision = engine.decide("ETH")
    
    assert decision.action == DecisionAction.WAIT
    assert decision.direction == TradeDirection.NEUTRAL
    assert decision.position_multiplier == 0.0
    assert decision.execution_mode == ExecutionMode.WAIT
    
    print(f"TEST 6 PASSED: {decision.to_dict()}")
    return True


def run_all_tests():
    """Run all decision engine tests."""
    print("\n" + "=" * 60)
    print("PHASE 14.4 — Trading Decision Engine Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Strong agreement → ALLOW_AGGRESSIVE", test_1_strong_agreement_allow_aggressive),
        ("Test 2: Mild agreement → ALLOW", test_2_mild_agreement_allow),
        ("Test 3: Weak conflict → ALLOW_REDUCED", test_3_weak_conflict_allow_reduced),
        ("Test 4: Strong conflict → BLOCK", test_4_strong_conflict_block),
        ("Test 5: Extreme conflict + squeeze → REVERSE_CANDIDATE", test_5_extreme_conflict_reverse_candidate),
        ("Test 6: No setup → WAIT", test_6_no_setup_wait),
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
