"""
Phase 2.2 Test Script
=====================

Tests:
1. P0 fix: RiskGuard AttributeError resolved
2. Phase 2.2: Market Dynamic scanner plumbing

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
from modules.risk_guard import get_risk_guard, init_risk_guard
from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner


async def test_p0_riskguard_fix():
    """Test P0: RiskGuard AttributeError fix"""
    print("\n" + "="*60)
    print("TEST 1: P0 - RiskGuard AttributeError Fix")
    print("="*60)
    
    try:
        # Initialize DB connection
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        # Initialize RiskGuard if not already
        risk_guard = get_risk_guard()
        if risk_guard is None:
            print("  ℹ️  Initializing RiskGuard...")
            risk_guard = init_risk_guard(db)
        
        if risk_guard is None:
            print("❌ RiskGuard initialization failed")
            return False
        
        # Test 1A: get_status should work without AttributeError
        print("\n[1A] Testing get_status() for baseline_btc...")
        status_baseline = await risk_guard.get_status(experiment_id="baseline_btc")
        print(f"  ✅ baseline_btc status: {status_baseline['experiment_id']}, "
              f"kill_switch={status_baseline['kill_switch_active']}")
        
        # Test 1B: get_status for market_dynamic
        print("\n[1B] Testing get_status() for market_dynamic...")
        status_dynamic = await risk_guard.get_status(experiment_id="market_dynamic")
        print(f"  ✅ market_dynamic status: {status_dynamic['experiment_id']}, "
              f"kill_switch={status_dynamic['kill_switch_active']}")
        
        # Test 1C: get_stats should work
        print("\n[1C] Testing get_stats()...")
        stats_baseline = risk_guard.get_stats(experiment_id="baseline_btc")
        print(f"  ✅ baseline_btc stats: {stats_baseline}")
        
        stats_dynamic = risk_guard.get_stats(experiment_id="market_dynamic")
        print(f"  ✅ market_dynamic stats: {stats_dynamic}")
        
        print("\n✅ P0 FIX VERIFIED: No AttributeError!")
        return True
        
    except AttributeError as e:
        print(f"\n❌ P0 FIX FAILED: AttributeError still present: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase_2_2_scanner():
    """Test Phase 2.2: Market Dynamic Scanner"""
    print("\n" + "="*60)
    print("TEST 2: Phase 2.2 - Market Dynamic Scanner Plumbing")
    print("="*60)
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    try:
        # Step 1: Check current experiment status
        print("\n[2A] Checking market_dynamic experiment status...")
        exp = await db.experiments.find_one({"experiment_id": "market_dynamic"})
        
        if not exp:
            print("  ❌ market_dynamic experiment not found in DB")
            return False
        
        original_status = exp.get("status", "disabled")
        print(f"  ℹ️  Current status: {original_status}")
        
        # Step 2: Temporarily enable for testing
        print("\n[2B] Temporarily enabling market_dynamic experiment...")
        await db.experiments.update_one(
            {"experiment_id": "market_dynamic"},
            {"$set": {"status": "enabled"}}
        )
        print("  ✅ Enabled (temporary, for test)")
        
        # Step 3: Start market_dynamic runner manually
        print("\n[2C] Starting market_dynamic runner...")
        runner = get_market_dynamic_runner()
        await runner.start()
        print("  ✅ Runner started")
        
        # Step 4: Wait for one scan cycle (60s interval + buffer)
        print("\n[2D] Waiting 65 seconds for scan cycle...")
        for i in range(13):
            await asyncio.sleep(5)
            print(f"  ⏳ {(i+1)*5}s / 65s elapsed...")
        
        # Step 5: Check scan results
        print("\n[2E] Checking scan results...")
        latest_scan = runner.get_latest_scan()
        
        if not latest_scan:
            print("  ❌ No scan results found")
            await runner.stop()
            # Restore original status
            await db.experiments.update_one(
                {"experiment_id": "market_dynamic"},
                {"$set": {"status": original_status}}
            )
            return False
        
        print(f"\n  📊 SCAN METADATA:")
        print(f"     Timestamp: {latest_scan['timestamp']}")
        print(f"     Eligible count: {latest_scan['eligible_count']}")
        print(f"     Total scanned: {latest_scan['total_scanned']}")
        print(f"     Scan duration: {latest_scan['scan_duration_ms']}ms")
        
        print(f"\n  🎯 TOP ELIGIBLE ASSETS:")
        for i, asset in enumerate(latest_scan['top_assets'][:5], 1):
            print(f"     {i}. {asset['symbol']} ({asset['timeframe']}) - "
                  f"vol=${asset['volume_24h']:,.0f}, "
                  f"atr={asset['atr_pct']:.4f}, "
                  f"spread={asset['spread_bps']:.2f}bps")
        
        print(f"\n  🚫 FILTERED OUT REASONS:")
        for reason, count in latest_scan['filtered_out_reasons'].items():
            print(f"     {reason}: {count}")
        
        # Step 6: Stop runner
        print("\n[2F] Stopping runner...")
        await runner.stop()
        print("  ✅ Runner stopped")
        
        # Step 7: Restore original experiment status
        print(f"\n[2G] Restoring original status: {original_status}...")
        await db.experiments.update_one(
            {"experiment_id": "market_dynamic"},
            {"$set": {"status": original_status}}
        )
        print("  ✅ Status restored")
        
        print("\n✅ PHASE 2.2 VERIFIED: Scanner plumbing works!")
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 2.2 test failed: {e}")
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
    print("Phase 2.2 Integration Test Suite")
    print("="*60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    
    # Wait for backend to be ready
    print("\n⏳ Waiting 5s for backend initialization...")
    await asyncio.sleep(5)
    
    results = {}
    
    # Test 1: P0 fix
    results['p0_fix'] = await test_p0_riskguard_fix()
    
    # Test 2: Phase 2.2
    if results['p0_fix']:
        results['phase_2_2'] = await test_phase_2_2_scanner()
    else:
        print("\n⚠️  Skipping Phase 2.2 test due to P0 failure")
        results['phase_2_2'] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"P0 Fix (RiskGuard): {'✅ PASS' if results['p0_fix'] else '❌ FAIL'}")
    print(f"Phase 2.2 (Scanner): {'✅ PASS' if results['phase_2_2'] else '❌ FAIL'}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
