"""
Phase 2.3 Test Script (Simplified)
===================================

Tests Phase 2.3 by:
1. Temporarily enabling market_dynamic experiment
2. Waiting for runner cycle
3. Checking stats via API
4. Restoring status
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
import httpx

# Add backend to path
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient


async def test_phase_2_3():
    """Test Phase 2.3"""
    print("\n" + "="*60)
    print("TEST: Phase 2.3 - Multi-Signal Generation")
    print("="*60)
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    backend_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
    
    client_db = AsyncIOMotorClient(mongo_url)
    db = client_db["trading_os"]
    
    try:
        # Step 1: Get original status
        print("\n[1] Checking original status...")
        exp = await db.experiments.find_one({"experiment_id": "market_dynamic"})
        original_status = exp.get("status", "disabled") if exp else "disabled"
        print(f"  ℹ️  Original status: {original_status}")
        
        # Step 2: Enable experiment
        print("\n[2] Enabling market_dynamic temporarily...")
        await db.experiments.update_one(
            {"experiment_id": "market_dynamic"},
            {"$set": {"status": "enabled"}}
        )
        print("  ✅ Enabled")
        
        # Step 3: Restart backend to pick up change
        print("\n[3] Restarting backend to activate runner...")
        os.system("supervisorctl restart backend > /dev/null 2>&1")
        await asyncio.sleep(10)
        print("  ✅ Backend restarted")
        
        # Step 4: Wait for full cycle (65s)
        print("\n[4] Waiting 70 seconds for scan + signal generation...")
        for i in range(14):
            await asyncio.sleep(5)
            print(f"  ⏳ {(i+1)*5}s / 70s...")
        
        # Step 5: Check stats via API
        print("\n[5] Fetching stats via API...")
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{backend_url}/api/experiments/market_dynamic/stats",
                timeout=10.0
            )
            
            if response.status_code != 200:
                print(f"  ❌ API returned status {response.status_code}")
                raise Exception(f"API error: {response.status_code}")
            
            stats = response.json()
        
        print("  ✅ Stats fetched")
        
        # Step 6: Display results
        print("\n[6] RESULTS:")
        print(f"  Runner active: {stats.get('runner_active', False)}")
        
        latest_scan = stats.get('latest_scan')
        if latest_scan:
            print(f"\n  📊 SCAN:")
            print(f"     Eligible: {latest_scan['eligible_count']}")
            print(f"     Total scanned: {latest_scan['total_scanned']}")
        
        latest_signals = stats.get('latest_signals')
        if latest_signals:
            print(f"\n  🎯 SIGNALS:")
            print(f"     eligible_assets = {latest_scan['eligible_count']}")
            print(f"     signals_generated = {latest_signals['signals_generated']}")
            print(f"     unique_symbols = {latest_signals['unique_symbols']}")
            print(f"     pool_size = {latest_signals['pool_size']}")
            print(f"     unique_keys_this_cycle = {latest_signals['unique_keys_this_cycle']}")
            
            print(f"\n  🏆 TOP SIGNALS:")
            for i, sig in enumerate(latest_signals['top_signals'][:5], 1):
                print(f"     {i}. {sig['symbol']}:{sig['timeframe']} - {sig['side']}, "
                      f"conf={sig['confidence']}, price=${sig['price']:.2f}")
            
            print(f"\n  🚫 SKIPPED:")
            for reason, count in latest_signals['skipped'].items():
                print(f"     {reason}: {count}")
            
            print(f"\n  📈 SYMBOL DISTRIBUTION:")
            for sym, count in latest_signals['symbol_distribution'].items():
                pct = (count / latest_signals['signals_generated'] * 100) if latest_signals['signals_generated'] > 0 else 0
                print(f"     {sym}: {count} ({pct:.1f}%)")
            
            # Check dominance
            dominant = latest_signals.get('dominant_symbol')
            if dominant:
                print(f"\n  ⚠️  DOMINANT SYMBOL: {dominant} ({latest_signals['dominant_percentage']}%)")
            else:
                print(f"\n  ✅ No dominant symbol (>50%)")
            
            # Verify DoD
            print(f"\n[7] VERIFICATION:")
            sigs = latest_signals['signals_generated']
            unique = latest_signals['unique_symbols']
            pool = latest_signals['pool_size']
            keys = latest_signals['unique_keys_this_cycle']
            dups = latest_signals['skipped']['duplicate']
            
            checks = [
                ("signals_generated in range [8-17]", 8 <= sigs <= 17),
                ("unique_symbols >= 3", unique >= 3),
                ("duplicates = 0", dups == 0),
                ("pool_size ≈ unique_keys", abs(pool - keys) <= 2),
            ]
            
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"  {status} {check_name}")
            
            all_passed = all(c[1] for c in checks)
        else:
            print("  ❌ No signal data available")
            all_passed = False
        
        # Step 7: Disable experiment
        print(f"\n[8] Restoring status to {original_status}...")
        await db.experiments.update_one(
            {"experiment_id": "market_dynamic"},
            {"$set": {"status": original_status}}
        )
        print("  ✅ Status restored")
        
        # Step 8: Restart backend again
        print("\n[9] Restarting backend...")
        os.system("supervisorctl restart backend > /dev/null 2>&1")
        await asyncio.sleep(5)
        print("  ✅ Backend restarted")
        
        # Step 9: Check baseline
        print("\n[10] Verifying baseline_btc...")
        baseline = await db.experiments.find_one({"experiment_id": "baseline_btc"})
        baseline_ok = baseline and baseline.get("status") == "enabled"
        print(f"  {'✅' if baseline_ok else '❌'} baseline_btc = {baseline.get('status') if baseline else 'not found'}")
        
        if all_passed and baseline_ok:
            print("\n✅ PHASE 2.3 PASSED")
            return True
        else:
            print("\n⚠️  PHASE 2.3 PARTIAL")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup
        try:
            await db.experiments.update_one(
                {"experiment_id": "market_dynamic"},
                {"$set": {"status": original_status}}
            )
            os.system("supervisorctl restart backend > /dev/null 2>&1")
        except:
            pass
        
        return False


async def main():
    print("="*60)
    print("Phase 2.3 Test Suite")
    print("="*60)
    
    result = await test_phase_2_3()
    
    print("\n" + "="*60)
    print(f"Result: {'✅ PASS' if result else '❌ FAIL'}")
    print("="*60)
    
    return 0 if result else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
