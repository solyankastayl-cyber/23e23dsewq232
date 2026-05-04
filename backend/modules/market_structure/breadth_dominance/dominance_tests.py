"""
PHASE 14.8 — Dominance & Breadth Tests
=======================================
Unit tests for market structure analysis.

Test cases:
1. BTC dominance regime
2. ALT dominance regime
3. Rotation BTC → ALTS
4. Strong breadth
5. Weak breadth
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.market_structure.breadth_dominance.dominance_types import (
    MarketDominanceState,
    MarketBreadthState,
    MarketStructureState,
    DominanceRegime,
    RotationState,
    BreadthState,
)
from modules.market_structure.breadth_dominance.dominance_engine import DominanceEngine
from modules.market_structure.breadth_dominance.breadth_engine import BreadthEngine
from modules.market_structure.breadth_dominance.market_structure_engine import (
    MarketStructureEngine,
    DOMINANCE_MODIFIERS,
    BREADTH_SIZE_MODIFIERS,
)


class MockDominanceEngine(DominanceEngine):
    """Mock dominance engine for testing."""
    
    def __init__(self):
        self._mock_dom = None
    
    def set_mock(self, btc: float, eth: float, btc_change: float = 0, alt_change: float = 0):
        self._mock_dom = {
            "btc": btc,
            "eth": eth,
            "btc_change": btc_change,
            "alt_change": alt_change,
        }
    
    def _get_current_dominance(self):
        if self._mock_dom:
            return {"btc": self._mock_dom["btc"], "eth": self._mock_dom["eth"]}
        return {"btc": 52.0, "eth": 17.0}
    
    def _get_historical_dominance(self, hours=24):
        if self._mock_dom:
            return {
                "btc": self._mock_dom["btc"] - self._mock_dom.get("btc_change", 0),
                "eth": self._mock_dom["eth"],
            }
        return None


class MockBreadthEngine(BreadthEngine):
    """Mock breadth engine for testing."""
    
    def __init__(self):
        self._mock_states = None
    
    def set_mock(self, advancing: int, declining: int, participation: float = 0.5):
        self._mock_states = {
            "advancing": advancing,
            "declining": declining,
            "participation": participation,
        }
    
    def _get_asset_states(self):
        if self._mock_states:
            # Generate states matching the mock counts
            states = []
            for i in range(self._mock_states["advancing"]):
                states.append({
                    "symbol": f"ADV{i}",
                    "change_24h": 2.0,
                    "near_high": i < 3,
                    "near_low": False,
                    "above_20d_ma": True,
                })
            for i in range(self._mock_states["declining"]):
                states.append({
                    "symbol": f"DEC{i}",
                    "change_24h": -2.0,
                    "near_high": False,
                    "near_low": i < 2,
                    "above_20d_ma": False,
                })
            return states
        return self._generate_mock_states()


def test_1_btc_dominance_regime():
    """Test 1: BTC dominance regime"""
    engine = MockDominanceEngine()
    engine.set_mock(btc=55.0, eth=15.0)
    
    result = engine.compute()
    
    assert result.dominance_regime == DominanceRegime.BTC_DOM
    assert result.btc_dominance == 55.0
    assert result.alt_dominance == 30.0  # 100 - 55 - 15
    
    # Check modifiers
    mods = DOMINANCE_MODIFIERS[DominanceRegime.BTC_DOM]
    assert mods["btc"] > 1.0  # BTC boosted
    assert mods["alt"] < 1.0  # ALTs penalized
    
    print(f"TEST 1 PASSED: regime={result.dominance_regime.value}")
    print(f"  btc_dom={result.btc_dominance}%, modifiers: btc={mods['btc']}, alt={mods['alt']}")
    return True


def test_2_alt_dominance_regime():
    """Test 2: ALT dominance regime"""
    engine = MockDominanceEngine()
    engine.set_mock(btc=42.0, eth=16.0)  # alt_dom = 42%
    
    result = engine.compute()
    
    assert result.dominance_regime == DominanceRegime.ALT_DOM
    assert result.alt_dominance == 42.0
    
    mods = DOMINANCE_MODIFIERS[DominanceRegime.ALT_DOM]
    assert mods["alt"] > 1.0  # ALTs boosted
    assert mods["btc"] < 1.0  # BTC penalized
    
    print(f"TEST 2 PASSED: regime={result.dominance_regime.value}")
    print(f"  alt_dom={result.alt_dominance}%, modifiers: alt={mods['alt']}, btc={mods['btc']}")
    return True


def test_3_rotation_btc_to_alts():
    """Test 3: Rotation BTC → ALTS"""
    engine = MockDominanceEngine()
    # BTC dropping 2%, alts gaining
    engine.set_mock(btc=50.0, eth=16.0, btc_change=-2.0, alt_change=2.0)
    
    result = engine.compute()
    
    assert result.rotation_state == RotationState.ROTATING_TO_ALTS
    assert result.btc_dom_change_24h < 0
    assert result.capital_flow_strength > 0
    
    print(f"TEST 3 PASSED: rotation={result.rotation_state.value}")
    print(f"  btc_change={result.btc_dom_change_24h}%, flow_strength={result.capital_flow_strength:.4f}")
    return True


def test_4_strong_breadth():
    """Test 4: Strong breadth"""
    engine = MockBreadthEngine()
    engine.set_mock(advancing=15, declining=5, participation=0.75)
    
    result = engine.compute()
    
    assert result.breadth_state == BreadthState.STRONG
    assert result.breadth_ratio >= 1.5
    assert result.advancing_assets > result.declining_assets
    
    size_mod = BREADTH_SIZE_MODIFIERS[BreadthState.STRONG]
    assert size_mod > 1.0  # Size up allowed
    
    print(f"TEST 4 PASSED: breadth={result.breadth_state.value}")
    print(f"  ratio={result.breadth_ratio:.2f}, adv={result.advancing_assets}, dec={result.declining_assets}")
    print(f"  size_modifier={size_mod}")
    return True


def test_5_weak_breadth():
    """Test 5: Weak breadth"""
    engine = MockBreadthEngine()
    engine.set_mock(advancing=4, declining=16, participation=0.25)
    
    result = engine.compute()
    
    assert result.breadth_state == BreadthState.WEAK
    assert result.breadth_ratio < 0.7
    assert result.advancing_assets < result.declining_assets
    
    size_mod = BREADTH_SIZE_MODIFIERS[BreadthState.WEAK]
    assert size_mod < 1.0  # Size down required
    
    print(f"TEST 5 PASSED: breadth={result.breadth_state.value}")
    print(f"  ratio={result.breadth_ratio:.2f}, adv={result.advancing_assets}, dec={result.declining_assets}")
    print(f"  size_modifier={size_mod}")
    return True


def test_6_integration_real_data():
    """Test 6: Integration with real engine"""
    from modules.market_structure.breadth_dominance.market_structure_engine import get_market_structure_engine
    
    engine = get_market_structure_engine()
    result = engine.compute()
    
    # Verify structure
    assert result.dominance is not None
    assert result.breadth is not None
    assert result.dominance.dominance_regime in DominanceRegime
    assert result.breadth.breadth_state in BreadthState
    assert 0 <= result.btc_confidence_modifier <= 2.0
    assert 0 <= result.size_modifier <= 2.0
    assert result.market_structure_quality in ["FAVORABLE", "NEUTRAL", "UNFAVORABLE"]
    
    print(f"TEST 6 PASSED: Integration test")
    print(f"  dominance: regime={result.dominance.dominance_regime.value}, btc={result.dominance.btc_dominance:.1f}%")
    print(f"  breadth: state={result.breadth.breadth_state.value}, ratio={result.breadth.breadth_ratio:.2f}")
    print(f"  quality={result.market_structure_quality}")
    print(f"  modifiers: btc_conf={result.btc_confidence_modifier:.3f}, size={result.size_modifier:.3f}")
    return True


def run_all_tests():
    """Run all market structure tests."""
    print("\n" + "=" * 60)
    print("PHASE 14.8 — Dominance & Breadth Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Test 1: BTC dominance regime", test_1_btc_dominance_regime),
        ("Test 2: ALT dominance regime", test_2_alt_dominance_regime),
        ("Test 3: Rotation BTC → ALTS", test_3_rotation_btc_to_alts),
        ("Test 4: Strong breadth", test_4_strong_breadth),
        ("Test 5: Weak breadth", test_5_weak_breadth),
        ("Test 6: Integration with real engine", test_6_integration_real_data),
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
