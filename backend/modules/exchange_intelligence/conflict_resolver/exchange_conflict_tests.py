#!/usr/bin/env python3
"""
Exchange Conflict Resolver Tests
=================================
Phase 14.1 — Unit tests for conflict resolution.

Tests:
1. All bullish signals
2. All bearish signals
3. Mixed/conflicting signals
4. Strong liquidation dominance
5. Neutral market
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.exchange_intelligence.conflict_resolver.exchange_conflict_types import (
    ExchangeSignal,
    ExchangeContext,
    ExchangeDirection,
    DominantSignalType,
)
from modules.exchange_intelligence.conflict_resolver.exchange_conflict_weights import (
    get_weights,
    BASE_WEIGHTS,
    BIAS_THRESHOLD,
)


def test_weights():
    """Test weight configurations."""
    print("\n[TEST] Weight Configurations")
    
    # Normal weights
    normal = get_weights("normal")
    assert normal["liquidations"] == 1.30
    assert normal["flow"] == 1.00
    print("  ✓ Normal weights correct")
    
    # Squeeze regime
    squeeze = get_weights("squeeze")
    assert squeeze["liquidations"] > normal["liquidations"]
    assert squeeze["flow"] < normal["flow"]
    print("  ✓ Squeeze weights boost liquidations")
    
    # Cascade regime
    cascade = get_weights("cascade")
    assert cascade["liquidations"] > squeeze["liquidations"]
    print("  ✓ Cascade weights maximize liquidations")
    
    return True


def test_signal_scoring():
    """Test signal weighted score calculation."""
    print("\n[TEST] Signal Scoring")
    
    # LONG signal
    signal = ExchangeSignal(
        engine="flow",
        direction=ExchangeDirection.LONG,
        strength=0.8,
        confidence=0.9,
    )
    
    score = signal.weighted_score(1.0)
    expected = 1.0 * 0.8 * 1.0 * 0.9  # direction * strength * weight * confidence
    assert abs(score - expected) < 0.001
    print(f"  ✓ LONG score: {score:.4f} (expected {expected:.4f})")
    
    # SHORT signal
    signal = ExchangeSignal(
        engine="funding",
        direction=ExchangeDirection.SHORT,
        strength=0.6,
        confidence=0.8,
    )
    
    score = signal.weighted_score(0.85)
    expected = -1.0 * 0.6 * 0.85 * 0.8
    assert abs(score - expected) < 0.001
    print(f"  ✓ SHORT score: {score:.4f} (expected {expected:.4f})")
    
    return True


def test_resolver_integration():
    """Test full resolver with real data."""
    print("\n[TEST] Resolver Integration (Real Data)")
    
    from modules.exchange_intelligence.conflict_resolver import (
        ExchangeConflictResolver,
    )
    
    resolver = ExchangeConflictResolver()
    
    # Test each symbol
    for symbol in ["BTC", "ETH", "SOL"]:
        context = resolver.resolve(symbol)
        
        assert context.symbol == symbol
        assert context.bias in [ExchangeDirection.LONG, ExchangeDirection.SHORT, ExchangeDirection.NEUTRAL]
        assert 0 <= context.confidence <= 1
        assert 0 <= context.conflict_ratio <= 1
        assert isinstance(context.dominant_signal, DominantSignalType)
        
        print(f"  ✓ {symbol}: bias={context.bias.value}, conf={context.confidence:.3f}, conflict={context.conflict_ratio:.3f}")
    
    return True


def test_detailed_analysis():
    """Test detailed analysis output."""
    print("\n[TEST] Detailed Analysis")
    
    from modules.exchange_intelligence.conflict_resolver import (
        ExchangeConflictResolver,
    )
    
    resolver = ExchangeConflictResolver()
    analysis = resolver.get_detailed_analysis("BTC")
    
    assert "context" in analysis
    assert "conflict_analysis" in analysis
    assert "weights_used" in analysis
    assert "raw_signals" in analysis
    
    print(f"  ✓ Context: {analysis['context']['bias']}")
    print(f"  ✓ Conflict ratio: {analysis['conflict_analysis']['conflict_ratio']:.3f}")
    print(f"  ✓ Signals collected: {list(analysis['raw_signals'].keys())}")
    
    return True


def test_regime_weights():
    """Test regime-specific weight adjustments."""
    print("\n[TEST] Regime Weight Adjustments")
    
    from modules.exchange_intelligence.conflict_resolver import (
        ExchangeConflictResolver,
    )
    
    resolver = ExchangeConflictResolver()
    
    # Normal regime
    normal = resolver.get_detailed_analysis("BTC", regime="normal")
    
    # Cascade regime
    cascade = resolver.get_detailed_analysis("BTC", regime="cascade")
    
    # In cascade, liquidation weight should be higher
    assert cascade["weights_used"]["liquidations"] > normal["weights_used"]["liquidations"]
    print(f"  ✓ Normal liq weight: {normal['weights_used']['liquidations']:.2f}")
    print(f"  ✓ Cascade liq weight: {cascade['weights_used']['liquidations']:.2f}")
    
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("EXCHANGE CONFLICT RESOLVER TESTS")
    print("=" * 60)
    
    tests = [
        ("Weights", test_weights),
        ("Signal Scoring", test_signal_scoring),
        ("Resolver Integration", test_resolver_integration),
        ("Detailed Analysis", test_detailed_analysis),
        ("Regime Weights", test_regime_weights),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"\n[FAIL] {name}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed")
    print("=" * 60)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
