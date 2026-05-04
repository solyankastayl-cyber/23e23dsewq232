"""
Phase 2.3 Test Script
=====================

Tests:
1. Phase 2.3: Multi-signal generation
2. Symbol+timeframe key verification
3. Deduplication check
4. Pool size control
5. Dominant symbol detection

IMPORTANT: This script temporarily enables market_dynamic for testing,
then disables it immediately after.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient


async def test_phase_2_3_signal_generation():
    """Test Phase 2.3: Multi-signal generation"""
    print("\n" + "="*60)
    print("TEST: Phase 2.3 - Multi-Signal Generation")
    print("="*60)
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    try:
        # Step 1: Check current experiment status
        print("\n[1] Checking market_dynamic experiment status...")
        exp = await db.experiments.find_one({"experiment_id": "market_dynamic"})
        
        if not exp:
            print("  ❌ market_dynamic experiment not found in DB")
            return False
        
        original_status = exp.get("status", "disabled")
        print(f"  ℹ️  Current status: {original_status}")
        
        # Step 2: Temporarily enable for testing
        print("\n[2] Temporarily enabling market_dynamic experiment...")
        await db.experiments.update_one(
            {"experiment_id": "market_dynamic"},
            {"$set": {"status": "enabled"}}
        )
        print("  ✅ Enabled (temporary, for test)")
        
        # Step 3: Start market_dynamic runner with market_data
        print("\n[3] Starting market_dynamic runner with signal generation...")
        
        from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner
        from modules.market_data_live import get_market_data_service
        
        market_data_svc = get_market_data_service()
        runner = get_market_dynamic_runner(market_data_service=market_data_svc)
        await runner.start()
        print("  ✅ Runner started (with market_data)")
        
        # Step 4: Wait for one full cycle (60s + buffer)
        print("\n[4] Waiting 65 seconds for scan + signal generation cycle...")
        for i in range(13):
            await asyncio.sleep(5)
            print(f"  ⏳ {(i+1)*5}s / 65s elapsed...")
        
        # Step 5: Check scan results
        print("\n[5] Checking scan results...")
        latest_scan = runner.get_latest_scan()
        
        if not latest_scan:
            print("  ❌ No scan results found")
            await runner.stop()
            await db.experiments.update_one(
                {"experiment_id": "market_dynamic"},
                {"$set": {"status": original_status}}
            )
            return False
        
        eligible_count = latest_scan['eligible_count']
        print(f"  ✅ Scan complete: {eligible_count} eligible assets")
        
        # Step 6: Check signal generation results
        print("\n[6] Checking signal generation results...")
        latest_signal_result = runner.get_latest_signal_result()
        
        if not latest_signal_result:
            print("  ❌ No signal results found")
            await runner.stop()
            await db.experiments.update_one(
                {"experiment_id": "market_dynamic"},
                {"$set": {"status": original_status}}
            )
            return False
        
        print(f"\n  📊 SIGNAL GENERATION RESULTS:")
        print(f"     Eligible assets: {eligible_count}")
        print(f"     Signals generated: {latest_signal_result['signals_generated']}")
        print(f"     Unique symbols: {latest_signal_result['unique_symbols']}")
        print(f"     Pool size: {latest_signal_result['pool_size']}")
        print(f"     Unique keys (cycle): {latest_signal_result['unique_keys_this_cycle']}")
        print(f"     Generation duration: {latest_signal_result['generation_duration_ms']}ms")
        
        print(f"\n  🎯 TOP SIGNALS:")
        for i, sig in enumerate(latest_signal_result['top_signals'][:5], 1):
            print(f"     {i}. {sig['symbol']}:{sig['timeframe']} - "
                  f"{sig['side']}, conf={sig['confidence']}, price=${sig['price']:.2f}")
        
        print(f"\n  🚫 SKIPPED:")
        for reason, count in latest_signal_result['skipped'].items():
            print(f"     {reason}: {count}")
        
        print(f"\n  📈 SYMBOL DISTRIBUTION:")
        for symbol, count in latest_signal_result['symbol_distribution'].items():
            pct = (count / latest_signal_result['signals_generated'] * 100) if latest_signal_result['signals_generated'] > 0 else 0
            print(f"     {symbol}: {count} signals ({pct:.1f}%)")
        
        # Check for dominant symbol
        if latest_signal_result['dominant_symbol']:
            print(f"\n  ⚠️  DOMINANT SYMBOL DETECTED:")
            print(f"     {latest_signal_result['dominant_symbol']} = {latest_signal_result['dominant_percentage']}% of signals")
        else:
            print(f"\n  ✅ No single symbol dominates (>50%)")
        
        # Verify expectations
        print("\n[7] Verifying expectations...")
        
        signals_generated = latest_signal_result['signals_generated']
        unique_symbols = latest_signal_result['unique_symbols']
        pool_size = latest_signal_result['pool_size']
        unique_keys = latest_signal_result['unique_keys_this_cycle']
        duplicates = latest_signal_result['skipped']['duplicate']
        
        checks = []
        
        # Check 1: signals_generated should be between 8-17 (not 0 and not 100)
        if 8 <= signals_generated <= 17:
            checks.append(("signals_generated in range [8-17]", True))
        else:
            checks.append(("signals_generated in range [8-17]", False))
        
        # Check 2: unique_symbols should be >= 3-5
        if unique_symbols >= 3:
            checks.append(("unique_symbols >= 3", True))
        else:
            checks.append(("unique_symbols >= 3", False))
        
        # Check 3: duplicates should be 0
        if duplicates == 0:
            checks.append(("duplicates = 0", True))
        else:
            checks.append(("duplicates = 0", False))
        
        # Check 4: pool_size ≈ unique_keys (no leak)
        if abs(pool_size - unique_keys) <= 2:  # Allow small variance
            checks.append(("pool_size ≈ unique_keys (no leak)", True))
        else:
            checks.append(("pool_size ≈ unique_keys (no leak)", False))
        
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        all_passed = all(c[1] for c in checks)
        
        # Step 8: Stop runner
        print("\n[8] Stopping runner...")
        await runner.stop()
        print("  ✅ Runner stopped")
        
        # Step 9: Restore original experiment status
        print(f"\n[9] Restoring original status: {original_status}...")
        await db.experiments.update_one(
            {"experiment_id": "market_dynamic"},
            {"$set": {"status": original_status}}
        )
        print("  ✅ Status restored")
        
        # Step 10: Check baseline untouched
        print("\n[10] Verifying baseline_btc untouched...")
        baseline_exp = await db.experiments.find_one({"experiment_id": "baseline_btc"})
        if baseline_exp and baseline_exp.get("status") == "enabled":
            print("  ✅ baseline_btc still enabled and untouched")
            checks.append(("baseline_btc untouched", True))
        else:
            print("  ❌ baseline_btc status changed!")
            checks.append(("baseline_btc untouched", False))
        
        if all_passed:
            print("\n✅ PHASE 2.3 VERIFIED: Multi-signal generation works!")
            return True
        else:
            print("\n⚠️  PHASE 2.3 PARTIAL: Some checks failed")
            return False
        
    except Exception as e:
        print(f"\n❌ Phase 2.3 test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup: restore status
        try:
            await db.experiments.update_one(
                {"experiment_id": "market_dynamic"},
                {"$set": {"status": original_status}}
            )
            print("\n  ℹ️  Status restored after error")
        except:
            pass
        
        return False


async def main():
    print("\n" + "="*60)
    print("Phase 2.3 Integration Test Suite")
    print("="*60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    # Wait for backend to be ready
    print("\n⏳ Waiting 5s for backend initialization...")
    await asyncio.sleep(5)
    
    result = await test_phase_2_3_signal_generation()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Phase 2.3 (Multi-Signal): {'✅ PASS' if result else '❌ FAIL'}")
    print("="*60)
    
    return 0 if result else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
