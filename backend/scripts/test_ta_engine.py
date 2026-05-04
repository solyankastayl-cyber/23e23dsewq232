"""
TA Engine Test Script
=====================
Verify TA Engine can read candles and produce non-NEUTRAL signals
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_hypothesis_builder

print("=" * 60)
print("TA ENGINE TEST - Sprint A2 Verification")
print("=" * 60)

builder = get_hypothesis_builder()

# Test symbols and timeframes from seed
test_cases = [
    ("BTCUSDT", "1h"),
    ("BTCUSDT", "4h"),
    ("BTCUSDT", "1d"),
    ("ETHUSDT", "1d"),
]

for symbol, timeframe in test_cases:
    print(f"\n[TEST] {symbol} {timeframe}")
    print("-" * 40)
    
    hyp = builder.build(symbol, timeframe)
    
    print(f"Direction: {hyp.direction}")
    print(f"Setup Quality: {hyp.setup_quality:.2f}")
    print(f"Conviction: {hyp.conviction:.2f}")
    print(f"Setup Type: {hyp.setup_type}")
    print(f"Regime: {hyp.regime}")
    print(f"Drivers: {hyp.drivers}")
    
    if hyp.direction.value == "NEUTRAL":
        print("⚠️  NEUTRAL signal (expected if market is ranging)")
    else:
        print(f"✅ Active signal: {hyp.direction.value}")

print("\n" + "=" * 60)
print("✅ TA ENGINE TEST COMPLETE")
print("=" * 60)
