"""
PHASE 14.7 — Trading Product Tests
===================================
Integration tests for Trading Product Engine.

Test cases:
1. Bullish full path → READY
2. Bearish full path → READY
3. Conflict path → CONFLICTED
4. Blocked path → BLOCKED
5. Delayed path → WAIT
6. Multi-symbol batch → mixed outputs
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.trading_product.trading_product_types import (
    TradingProductSnapshot,
    ProductStatus,
    OverlayEffect,
)
from modules.trading_product.trading_product_engine import TradingProductEngine


class MockTradingProductEngine(TradingProductEngine):
    """Engine with mock module outputs for testing."""
    
    def __init__(self):
        self._ta_output = None
        self._exchange_output = None
        self._market_state_output = None
        self._decision_output = None
        self._sizing_output = None
        self._execution_output = None
        self._overlay_output = None  # PHASE 14.9
    
    def set_mock_outputs(
        self,
        ta: dict,
        exchange: dict,
        market_state: dict,
        decision: dict,
        sizing: dict,
        execution: dict,
        overlay: dict = None,  # PHASE 14.9
    ):
        """Set mock outputs for all modules."""
        self._ta_output = ta
        self._exchange_output = exchange
        self._market_state_output = market_state
        self._decision_output = decision
        self._sizing_output = sizing
        self._execution_output = execution
        # PHASE 14.9: Default overlay
        self._overlay_output = overlay or {
            "confidence_modifier": 1.0,
            "size_modifier": 1.0,
            "dominance_regime": "BALANCED",
            "breadth_state": "MIXED",
            "rotation_state": "STABLE",
        }
    
    def _get_ta_hypothesis(self, symbol: str):
        return self._ta_output
    
    def _get_exchange_context(self, symbol: str):
        return self._exchange_output
    
    def _get_market_state(self, symbol: str):
        return self._market_state_output
    
    def _get_trading_decision(self, symbol: str):
        return self._decision_output
    
    def _get_position_sizing(self, symbol: str):
        return self._sizing_output
    
    def _get_execution_mode(self, symbol: str):
        return self._execution_output
    
    def _get_overlay_data(self, symbol: str):
        """PHASE 14.9: Get mock overlay data."""
        return self._overlay_output


def test_1_bullish_full_path_ready():
    """Test 1: Bullish full path → READY"""
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "LONG",
            "regime": "TREND_UP",
            "setup_type": "BREAKOUT",
            "setup_quality": 0.8,
            "conviction": 0.82,
        },
        exchange={
            "bias": "BULLISH",
            "confidence": 0.78,
            "crowding_risk": 0.3,
            "squeeze_probability": 0.2,
        },
        market_state={
            "combined_state": "TRENDING_LOW_VOL_BULLISH",
            "trend_state": "TREND_UP",
            "risk_state": "RISK_ON",
            "confidence": 0.8,
        },
        decision={
            "action": "ALLOW_AGGRESSIVE",
            "direction": "LONG",
            "confidence": 0.85,
            "position_multiplier": 1.2,
        },
        sizing={
            "final_size_pct": 1.25,
            "size_bucket": "LARGE",
            "risk_multiplier": 1.2,
        },
        execution={
            "execution_mode": "AGGRESSIVE",
            "urgency_score": 0.85,
            "entry_style": "MARKET",
            "partial_ratio": 1.0,
        },
    )
    
    result = engine.compute("BTC")
    
    assert result.product_status == ProductStatus.READY
    assert result.final_action == "ALLOW_AGGRESSIVE"
    assert result.final_direction == "LONG"
    assert result.final_execution_mode == "AGGRESSIVE"
    
    print(f"TEST 1 PASSED: status={result.product_status.value}")
    print(f"  action={result.final_action}, direction={result.final_direction}")
    return True


def test_2_bearish_full_path_ready():
    """Test 2: Bearish full path → READY"""
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "SHORT",
            "regime": "TREND_DOWN",
            "setup_type": "BREAKDOWN",
            "setup_quality": 0.75,
            "conviction": 0.78,
        },
        exchange={
            "bias": "BEARISH",
            "confidence": 0.75,
            "crowding_risk": 0.35,
            "squeeze_probability": 0.25,
        },
        market_state={
            "combined_state": "BEARISH_EXPANSION_RISK_OFF",
            "trend_state": "TREND_DOWN",
            "risk_state": "RISK_OFF",
            "confidence": 0.75,
        },
        decision={
            "action": "ALLOW",
            "direction": "SHORT",
            "confidence": 0.77,
            "position_multiplier": 0.95,
        },
        sizing={
            "final_size_pct": 0.85,
            "size_bucket": "NORMAL",
            "risk_multiplier": 0.95,
        },
        execution={
            "execution_mode": "NORMAL",
            "urgency_score": 0.72,
            "entry_style": "LIMIT",
            "partial_ratio": 1.0,
        },
    )
    
    result = engine.compute("BTC")
    
    assert result.product_status == ProductStatus.READY
    assert result.final_action == "ALLOW"
    assert result.final_direction == "SHORT"
    assert result.final_execution_mode == "NORMAL"
    
    print(f"TEST 2 PASSED: status={result.product_status.value}")
    print(f"  action={result.final_action}, direction={result.final_direction}")
    return True


def test_3_conflict_path_conflicted():
    """Test 3: Conflict path → CONFLICTED"""
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "LONG",
            "regime": "TREND_UP",
            "setup_type": "PULLBACK",
            "setup_quality": 0.6,
            "conviction": 0.55,
        },
        exchange={
            "bias": "BEARISH",
            "confidence": 0.6,
            "crowding_risk": 0.5,
            "squeeze_probability": 0.45,
            "conflict_ratio": 0.5,
        },
        market_state={
            "combined_state": "UNDEFINED",
            "trend_state": "MIXED",
            "risk_state": "NEUTRAL",
            "confidence": 0.55,
        },
        decision={
            "action": "ALLOW_REDUCED",
            "direction": "LONG",
            "confidence": 0.55,
            "position_multiplier": 0.5,
        },
        sizing={
            "final_size_pct": 0.45,
            "size_bucket": "SMALL",
            "risk_multiplier": 0.5,
        },
        execution={
            "execution_mode": "PASSIVE",
            "urgency_score": 0.4,
            "entry_style": "LIMIT",
            "partial_ratio": 1.0,
        },
    )
    
    result = engine.compute("ETH")
    
    assert result.product_status == ProductStatus.CONFLICTED
    assert result.final_action == "ALLOW_REDUCED"
    
    print(f"TEST 3 PASSED: status={result.product_status.value}")
    print(f"  action={result.final_action}, reason={result.reason}")
    return True


def test_4_blocked_path():
    """Test 4: Blocked path → BLOCKED"""
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "LONG",
            "regime": "TREND_DOWN",
            "setup_type": "REVERSAL",
            "setup_quality": 0.5,
            "conviction": 0.45,
        },
        exchange={
            "bias": "BEARISH",
            "confidence": 0.75,
            "crowding_risk": 0.7,
            "squeeze_probability": 0.6,
        },
        market_state={
            "combined_state": "BEARISH_HIGH_VOL_SQUEEZE",
            "trend_state": "TREND_DOWN",
            "risk_state": "RISK_OFF",
            "confidence": 0.7,
        },
        decision={
            "action": "BLOCK",
            "direction": "NEUTRAL",
            "confidence": 0.35,
            "position_multiplier": 0.0,
        },
        sizing={
            "final_size_pct": 0.0,
            "size_bucket": "NONE",
            "risk_multiplier": 0.0,
        },
        execution={
            "execution_mode": "NONE",
            "urgency_score": 0.0,
            "entry_style": "WAIT",
            "partial_ratio": 0.0,
        },
    )
    
    result = engine.compute("SOL")
    
    assert result.product_status == ProductStatus.BLOCKED
    assert result.final_action == "BLOCK"
    assert result.final_size_pct == 0.0
    
    print(f"TEST 4 PASSED: status={result.product_status.value}")
    print(f"  action={result.final_action}, size={result.final_size_pct}")
    return True


def test_5_delayed_path_wait():
    """Test 5: Delayed path → WAIT"""
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "LONG",
            "regime": "RANGE",
            "setup_type": "NO_SETUP",
            "setup_quality": 0.3,
            "conviction": 0.25,
        },
        exchange={
            "bias": "NEUTRAL",
            "confidence": 0.5,
            "crowding_risk": 0.3,
            "squeeze_probability": 0.2,
        },
        market_state={
            "combined_state": "CHOP_CONFLICTED",
            "trend_state": "RANGE",
            "risk_state": "NEUTRAL",
            "confidence": 0.45,
        },
        decision={
            "action": "WAIT",
            "direction": "NEUTRAL",
            "confidence": 0.25,
            "position_multiplier": 0.0,
        },
        sizing={
            "final_size_pct": 0.0,
            "size_bucket": "NONE",
            "risk_multiplier": 0.0,
        },
        execution={
            "execution_mode": "DELAYED",
            "urgency_score": 0.0,
            "entry_style": "WAIT",
            "partial_ratio": 0.0,
        },
    )
    
    result = engine.compute("ETH")
    
    assert result.product_status == ProductStatus.WAIT
    assert result.final_action == "WAIT"
    
    print(f"TEST 5 PASSED: status={result.product_status.value}")
    print(f"  action={result.final_action}, reason={result.reason}")
    return True


def test_6_multi_symbol_batch():
    """Test 6: Multi-symbol batch → mixed outputs"""
    # This test uses the real engine with actual data
    from modules.trading_product.trading_product_engine import get_trading_product_engine
    
    engine = get_trading_product_engine()
    symbols = ["BTC", "ETH", "SOL"]
    
    results = engine.compute_batch(symbols)
    
    assert len(results) == 3
    
    # Check each result has required fields
    for result in results:
        assert result.symbol in symbols
        assert result.product_status in ProductStatus
        assert result.final_action in ["ALLOW", "ALLOW_AGGRESSIVE", "ALLOW_REDUCED", "BLOCK", "WAIT", "REVERSE_CANDIDATE"]
        assert 0.0 <= result.final_confidence <= 1.0
        assert result.final_size_pct >= 0.0
    
    print(f"TEST 6 PASSED: batch of {len(results)} symbols")
    for r in results:
        print(f"  {r.symbol}: status={r.product_status.value}, action={r.final_action}")
    
    return True


# ══════════════════════════════════════════════════════════════
# PHASE 14.9 TESTS — Overlay Integration
# ══════════════════════════════════════════════════════════════

def test_7_overlay_does_not_break_signal():
    """
    PHASE 14.9: Test that overlay DOES NOT break a valid signal.
    
    Scenario:
    - ALT trade (SOL)
    - BTC_DOM regime (hostile for alts)
    - WEAK breadth (hostile)
    
    Expected:
    - action = ALLOW (NOT BLOCK)
    - size = reduced
    - execution = PASSIVE (downgraded)
    - overlay_effect = HOSTILE
    """
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "LONG",
            "regime": "TREND_UP",
            "setup_type": "BREAKOUT",
            "setup_quality": 0.75,
            "conviction": 0.72,
        },
        exchange={
            "bias": "BULLISH",
            "confidence": 0.65,
            "crowding_risk": 0.3,
            "squeeze_probability": 0.2,
        },
        market_state={
            "combined_state": "TRENDING_LOW_VOL_BULLISH",
            "trend_state": "TREND_UP",
            "risk_state": "RISK_ON",
            "confidence": 0.7,
        },
        decision={
            "action": "ALLOW",  # Valid signal
            "direction": "LONG",
            "confidence": 0.64,  # Reduced by dominance
            "position_multiplier": 0.9,
            "execution_mode": "NORMAL",
        },
        sizing={
            "base_risk": 1.0,
            "risk_multiplier": 1.0,
            "volatility_adjustment": 1.0,
            "exchange_adjustment": 1.0,
            "market_adjustment": 1.0,
            "dominance_adjustment": 0.85,  # Penalized
            "breadth_adjustment": 0.80,    # Penalized
            "final_size_pct": 0.42,        # Reduced
            "size_bucket": "SMALL",
        },
        execution={
            "execution_mode": "PASSIVE",   # Downgraded from NORMAL
            "urgency_score": 0.5,
            "slippage_tolerance": 0.002,
            "entry_style": "LIMIT",
            "partial_ratio": 1.0,
            "reason": "standard_execution__weak_breadth_passive",
        },
    )
    
    # Override overlay method for test
    engine._get_overlay_data = lambda s: {
        "confidence_modifier": 0.85,
        "size_modifier": 0.80,
        "dominance_regime": "BTC_DOM",
        "breadth_state": "WEAK",
        "rotation_state": "STABLE",
    }
    
    result = engine.compute("SOL")
    
    # KEY ASSERTION: action is ALLOW, not BLOCK
    assert result.final_action == "ALLOW", \
        f"Overlay should NOT block signal. Got: {result.final_action}"
    
    # Size should be reduced
    assert result.final_size_pct < 0.5, \
        f"Size should be reduced by overlay. Got: {result.final_size_pct}"
    
    # Execution should be passive (downgraded)
    assert result.final_execution_mode == "PASSIVE", \
        f"Execution should be downgraded to PASSIVE. Got: {result.final_execution_mode}"
    
    # Overlay effect should be hostile
    assert result.overlay_effect.value == "HOSTILE", \
        f"Overlay effect should be HOSTILE. Got: {result.overlay_effect}"
    
    # Dominance state should be captured
    assert result.dominance_state == "BTC_DOM", \
        f"Dominance state should be BTC_DOM. Got: {result.dominance_state}"
    
    print("✓ Test 7: Overlay does NOT break signal - PASSED")
    print(f"  → action={result.final_action}, size={result.final_size_pct:.2f}, exec={result.final_execution_mode}")
    print(f"  → dominance={result.dominance_state}, breadth={result.breadth_state}, overlay={result.overlay_effect.value}")
    
    return True


def test_8_overlay_supportive_btc_in_btc_dom():
    """
    PHASE 14.9: Test that BTC trade in BTC_DOM is SUPPORTIVE.
    """
    engine = MockTradingProductEngine()
    
    engine.set_mock_outputs(
        ta={
            "direction": "LONG",
            "regime": "TREND_UP",
            "setup_type": "BREAKOUT",
            "setup_quality": 0.85,
            "conviction": 0.88,
        },
        exchange={
            "bias": "BULLISH",
            "confidence": 0.82,
            "crowding_risk": 0.2,
            "squeeze_probability": 0.15,
        },
        market_state={
            "combined_state": "TRENDING_LOW_VOL_BULLISH",
            "trend_state": "TREND_UP",
            "risk_state": "RISK_ON",
            "confidence": 0.85,
        },
        decision={
            "action": "ALLOW_AGGRESSIVE",
            "direction": "LONG",
            "confidence": 0.90,
            "position_multiplier": 1.2,
            "execution_mode": "AGGRESSIVE",
        },
        sizing={
            "base_risk": 1.0,
            "risk_multiplier": 1.2,
            "volatility_adjustment": 1.0,
            "exchange_adjustment": 1.05,
            "market_adjustment": 1.0,
            "dominance_adjustment": 1.15,  # Boosted
            "breadth_adjustment": 1.10,    # Boosted
            "final_size_pct": 1.35,
            "size_bucket": "LARGE",
        },
        execution={
            "execution_mode": "AGGRESSIVE",
            "urgency_score": 0.85,
            "slippage_tolerance": 0.005,
            "entry_style": "MARKET",
            "partial_ratio": 1.0,
            "reason": "strong_setup_aggressive_entry",
        },
    )
    
    # Override overlay method for test
    engine._get_overlay_data = lambda s: {
        "confidence_modifier": 1.15,
        "size_modifier": 1.10,
        "dominance_regime": "BTC_DOM",
        "breadth_state": "STRONG",
        "rotation_state": "STABLE",
    }
    
    result = engine.compute("BTC")
    
    # BTC in BTC_DOM with STRONG breadth should be SUPPORTIVE
    assert result.overlay_effect.value == "SUPPORTIVE", \
        f"BTC in BTC_DOM should be SUPPORTIVE. Got: {result.overlay_effect.value}"
    
    # Action should be aggressive
    assert result.final_action == "ALLOW_AGGRESSIVE"
    
    # Execution should remain aggressive
    assert result.final_execution_mode == "AGGRESSIVE"
    
    print("✓ Test 8: BTC in BTC_DOM is SUPPORTIVE - PASSED")
    print(f"  → action={result.final_action}, exec={result.final_execution_mode}, overlay={result.overlay_effect.value}")
    
    return True


def run_all_tests():
    """Run all trading product tests."""
    print("\n" + "=" * 60)
    print("PHASE 14.7/14.9 — Trading Product Integration Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: Bullish full path → READY", test_1_bullish_full_path_ready),
        ("Test 2: Bearish full path → READY", test_2_bearish_full_path_ready),
        ("Test 3: Conflict path → CONFLICTED", test_3_conflict_path_conflicted),
        ("Test 4: Blocked path → BLOCKED", test_4_blocked_path),
        ("Test 5: Delayed path → WAIT", test_5_delayed_path_wait),
        ("Test 6: Multi-symbol batch → mixed", test_6_multi_symbol_batch),
        # PHASE 14.9 tests
        ("Test 7: Overlay does NOT break signal", test_7_overlay_does_not_break_signal),
        ("Test 8: BTC in BTC_DOM is SUPPORTIVE", test_8_overlay_supportive_btc_in_btc_dom),
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
