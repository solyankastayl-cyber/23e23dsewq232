#!/usr/bin/env python3
"""
Phase A.8 - BUY Freeze Validation Test
========================================

Tests that ALL BUY signal generation is frozen.

Expected behavior:
- Test 1: Bearish falling knife → NO BUY (was already blocked by trend filter)
- Test 2: Bullish pullback → NO BUY (NOW blocked by Phase A.8 freeze) ✅
- Test 3: Bearish continuation → SELL OK (SHORT side unchanged)
- Test 4: Perfect BUY setup → NO BUY (Phase A.8 freeze active) ✅

SUCCESS CRITERIA: 0 BUY signals generated in ANY scenario
"""

import sys
sys.path.insert(0, '/app/backend')

from modules.signal_generator.multi_asset_generator import MultiAssetGenerator


def test_falling_knife_no_buy():
    """
    Scenario: Bearish downtrend with small bounce
    Expected: NO BUY signal (blocked by trend filter + A.8)
    """
    print("═"*70)
    print("TEST 1: Falling knife scenario")
    print("═"*70)
    
    gen = MultiAssetGenerator("TEST_FALL", short_period=3, long_period=5, trend_period=20, timeframe="1H")
    
    prices = [
        100, 99, 98, 97, 96, 95, 94, 93, 92, 91,
        90, 89, 88, 87, 86, 85, 84, 83, 82, 81,
        80, 81, 82  # Small bounce
    ]
    
    signal = None
    for price in prices:
        signal = gen.generate_signal(price)
    
    print(f"Final price: ${prices[-1]:.2f}")
    print(f"MA3: {gen.calculate_ma(3):.2f}, MA5: {gen.calculate_ma(5):.2f}, MA20: {gen.calculate_ma(20):.2f}")
    
    if signal is None:
        print("✅ PASS: NO signal generated (correctly rejected)")
        return True
    elif signal['side'] == 'BUY':
        print("❌ FAIL: BUY signal created (freeze not working!)")
        print(f"   Signal: {signal}")
        return False
    else:
        print("✅ PASS: SELL signal (no BUY)")
        return True


def test_perfect_buy_setup_frozen():
    """
    Scenario: Perfect bullish setup (uptrend + pullback + bounce)
    Expected: NO BUY signal (blocked by Phase A.8 freeze)
    
    THIS IS THE KEY TEST - even perfect setups should be frozen.
    """
    print("\n" + "═"*70)
    print("TEST 2: PERFECT BUY setup (should be FROZEN by A.8)")
    print("═"*70)
    
    gen = MultiAssetGenerator("TEST_PERFECT", short_period=3, long_period=5, trend_period=20, timeframe="4H")
    
    # Create ideal bullish scenario
    prices = [
        100, 101, 102, 103, 104, 105, 106, 107, 108, 109,  # Strong uptrend
        110, 111, 112, 113, 114, 115, 116, 117, 118, 119,  # Continuing up
        118, 117, 116, 117, 118, 119  # Pullback then strong bounce
    ]
    
    signal = None
    for price in prices:
        signal = gen.generate_signal(price)
    
    print(f"Final price: ${prices[-1]:.2f}")
    print(f"MA3: {gen.calculate_ma(3):.2f}, MA5: {gen.calculate_ma(5):.2f}, MA20: {gen.calculate_ma(20):.2f}")
    print(f"MA3 > MA5: {gen.calculate_ma(3) > gen.calculate_ma(5)}")
    print(f"Price > MA20: {prices[-1]} > {gen.calculate_ma(20):.2f}")
    
    if signal and signal['side'] == 'BUY':
        print("❌ FAIL: BUY signal created (Phase A.8 freeze NOT working!)")
        print(f"   Signal: {signal}")
        return False
    else:
        print("✅ PASS: BUY signal FROZEN (Phase A.8 active)")
        return True


def test_bearish_sell_unchanged():
    """
    Scenario: Bearish downtrend continuation
    Expected: SELL signal (SHORT side should work normally)
    """
    print("\n" + "═"*70)
    print("TEST 3: Bearish continuation (SELL should work)")
    print("═"*70)
    
    gen = MultiAssetGenerator("TEST_BEAR", short_period=3, long_period=5, trend_period=20, timeframe="1H")
    
    prices = [
        100, 99, 98, 97, 96, 95, 94, 93, 92, 91,
        90, 89, 88, 87, 86, 85, 84, 83, 82, 81,
        80, 79, 78  # Continuing down
    ]
    
    signal = None
    for price in prices:
        signal = gen.generate_signal(price)
    
    print(f"Final price: ${prices[-1]:.2f}")
    if signal:
        print(f"Signal: {signal['side']}")
        print(f"MA3: {gen.calculate_ma(3):.2f}, MA5: {gen.calculate_ma(5):.2f}, MA20: {gen.calculate_ma(20):.2f}")
    
    if signal and signal['side'] == 'SELL':
        print("✅ PASS: SELL signal working (SHORT side unchanged)")
        return True
    else:
        print("❌ FAIL: No SELL signal in clear downtrend")
        return False


def test_strong_uptrend_no_buy():
    """
    Scenario: Strong continuous uptrend (best BUY conditions)
    Expected: NO BUY signal (Phase A.8 freeze active)
    """
    print("\n" + "═"*70)
    print("TEST 4: Strong uptrend (should NOT generate BUY)")
    print("═"*70)
    
    gen = MultiAssetGenerator("TEST_UP", short_period=3, long_period=5, trend_period=20, timeframe="4H")
    
    prices = [
        100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
        110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
        120, 121, 122, 123, 124  # Strong rally
    ]
    
    signal = None
    for price in prices:
        signal = gen.generate_signal(price)
    
    print(f"Final price: ${prices[-1]:.2f}")
    print(f"MA3: {gen.calculate_ma(3):.2f}, MA5: {gen.calculate_ma(5):.2f}, MA20: {gen.calculate_ma(20):.2f}")
    
    if signal and signal['side'] == 'BUY':
        print("❌ FAIL: BUY signal created in uptrend (freeze not working!)")
        print(f"   Signal: {signal}")
        return False
    else:
        print("✅ PASS: No BUY signal (Phase A.8 freeze active)")
        return True


if __name__ == "__main__":
    print("\n" + "═"*70)
    print("PHASE A.8 - BUY FREEZE VALIDATION TEST")
    print("═"*70)
    print("\n🎯 Goal: Confirm 0 BUY signals generated in ANY scenario")
    print("   (SHORT side should continue working normally)\n")
    
    results = []
    
    results.append(("Falling knife (no BUY)", test_falling_knife_no_buy()))
    results.append(("Perfect BUY setup FROZEN", test_perfect_buy_setup_frozen()))
    results.append(("SELL working normally", test_bearish_sell_unchanged()))
    results.append(("Strong uptrend (no BUY)", test_strong_uptrend_no_buy()))
    
    print("\n" + "═"*70)
    print("TEST SUMMARY")
    print("═"*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - BUY FREEZE WORKING!")
        print("\n✅ Phase A.8 validated")
        print("📊 Next: Launch Batch 6 (SHORT-only validation)")
        print("\n   Command:")
        print("   cd /app/backend")
        print("   nohup python3 scripts/shadow_collection.py \\")
        print("     --target 35 --horizon 4 --interval 15 \\")
        print("     --experiment batch6_short_only \\")
        print("     > /tmp/batch6.log 2>&1 &")
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED")
        print("   Review Phase A.8 implementation in multi_asset_generator.py")
    
    print("═"*70 + "\n")
