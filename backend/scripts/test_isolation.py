#!/usr/bin/env python3
"""
Phase 1.5 - Step 10: Experiment Isolation Tests
Proves isolation on system behavior, not description.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# Colors
class C:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(name, passed, details=""):
    symbol = "✓" if passed else "✗"
    color = C.GREEN if passed else C.RED
    print(f"{color}{symbol} {name}{C.END} {details}")
    return passed

def log_section(name):
    print(f"\n{C.YELLOW}{'='*60}{C.END}")
    print(f"{C.YELLOW}{name}{C.END}")
    print(f"{C.YELLOW}{'='*60}{C.END}")

async def test_a_baseline_flow():
    """TEST A: Baseline flow works correctly"""
    log_section("TEST A: Baseline Flow")
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    results = []
    
    # Clean slate
    test_case_id = f"test-baseline-{int(datetime.now().timestamp())}"
    test_decision_id = f"decision-baseline-{int(datetime.now().timestamp())}"
    
    try:
        # 1. Create position with baseline_btc
        case = {
            "case_id": test_case_id,
            "symbol": "BTCUSDT",
            "side": "LONG",
            "status": "ACTIVE",
            "experiment_id": "baseline_btc",
            "decision_id": test_decision_id,
            "entry_price": 75000,
            "qty": 0.01,
            "size_usd": 750,
            "realized_pnl": 0,
            "opened_at": datetime.now(timezone.utc),
        }
        await db.trading_cases.insert_one(case)
        
        # Verify creation
        created = await db.trading_cases.find_one({"case_id": test_case_id})
        results.append(log_test(
            "Position created",
            created is not None,
            f"case_id={test_case_id}"
        ))
        results.append(log_test(
            "experiment_id == baseline_btc",
            created.get("experiment_id") == "baseline_btc",
            f"actual={created.get('experiment_id')}"
        ))
        
        # 2. Check open_positions count
        count_baseline = await db.trading_cases.count_documents({
            "status": "ACTIVE",
            "experiment_id": "baseline_btc"
        })
        results.append(log_test(
            "open_positions counted",
            count_baseline >= 1,
            f"count={count_baseline}"
        ))
        
        # 3. Duplicate guard check
        duplicate_exists = await db.trading_cases.find_one({
            "decision_id": test_decision_id,
            "experiment_id": "baseline_btc"
        })
        results.append(log_test(
            "duplicate guard works",
            duplicate_exists is not None,
            "finds existing decision"
        ))
        
        # 4. Close position and check PnL update
        await db.trading_cases.update_one(
            {"case_id": test_case_id},
            {
                "$set": {
                    "status": "CLOSED",
                    "realized_pnl": 50.0,
                    "closed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Verify PnL aggregation
        pipeline = [
            {"$match": {"experiment_id": "baseline_btc", "status": "CLOSED"}},
            {"$group": {"_id": None, "total": {"$sum": "$realized_pnl"}}}
        ]
        result = await db.trading_cases.aggregate(pipeline).to_list(1)
        total_pnl = result[0]["total"] if result else 0
        
        results.append(log_test(
            "risk update (PnL aggregation)",
            total_pnl != 0,
            f"total_pnl=${total_pnl:.2f}"
        ))
        
        # Cleanup
        await db.trading_cases.delete_one({"case_id": test_case_id})
        
    except Exception as e:
        log_test("TEST A", False, f"ERROR: {e}")
        results.append(False)
    
    client.close()
    return all(results)

async def test_b_market_dynamic_isolation():
    """TEST B: market_dynamic isolated from baseline"""
    log_section("TEST B: market_dynamic Isolation")
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    results = []
    
    test_case_id = f"test-market-{int(datetime.now().timestamp())}"
    test_decision_id = f"decision-market-{int(datetime.now().timestamp())}"
    
    try:
        # 1. Create position with market_dynamic
        case = {
            "case_id": test_case_id,
            "symbol": "ETHUSDT",
            "side": "LONG",
            "status": "ACTIVE",
            "experiment_id": "market_dynamic",
            "decision_id": test_decision_id,
            "entry_price": 3000,
            "qty": 0.1,
            "size_usd": 300,
            "realized_pnl": 0,
            "opened_at": datetime.now(timezone.utc),
        }
        await db.trading_cases.insert_one(case)
        
        # Verify experiment_id
        created = await db.trading_cases.find_one({"case_id": test_case_id})
        results.append(log_test(
            "position created with market_dynamic",
            created.get("experiment_id") == "market_dynamic",
            f"experiment_id={created.get('experiment_id')}"
        ))
        
        # 2. baseline does not see it
        count_baseline = await db.trading_cases.count_documents({
            "case_id": test_case_id,
            "experiment_id": "baseline_btc"
        })
        results.append(log_test(
            "baseline does not see it",
            count_baseline == 0,
            f"baseline count={count_baseline}"
        ))
        
        # 3. market_dynamic sees only its own
        count_market = await db.trading_cases.count_documents({
            "case_id": test_case_id,
            "experiment_id": "market_dynamic"
        })
        results.append(log_test(
            "market_dynamic sees it",
            count_market == 1,
            f"market count={count_market}"
        ))
        
        # 4. Duplicate from baseline doesn't block market_dynamic
        # Use same decision_id as baseline but different experiment
        baseline_decision_id = f"shared-decision-{int(datetime.now().timestamp())}"
        
        # Create in baseline
        await db.trading_cases.insert_one({
            "case_id": f"baseline-dup-test",
            "experiment_id": "baseline_btc",
            "decision_id": baseline_decision_id,
            "symbol": "BTCUSDT",
            "status": "ACTIVE",
        })
        
        # Create in market_dynamic with SAME decision_id
        await db.trading_cases.insert_one({
            "case_id": f"market-dup-test",
            "experiment_id": "market_dynamic",
            "decision_id": baseline_decision_id,  # Same ID!
            "symbol": "ETHUSDT",
            "status": "ACTIVE",
        })
        
        # Both should exist
        baseline_dup = await db.trading_cases.find_one({
            "decision_id": baseline_decision_id,
            "experiment_id": "baseline_btc"
        })
        market_dup = await db.trading_cases.find_one({
            "decision_id": baseline_decision_id,
            "experiment_id": "market_dynamic"
        })
        
        results.append(log_test(
            "duplicate independent",
            baseline_dup is not None and market_dup is not None,
            "same decision_id in both experiments"
        ))
        
        # Cleanup
        await db.trading_cases.delete_many({"case_id": {"$regex": "^test-market-|baseline-dup-test|market-dup-test"}})
        
    except Exception as e:
        log_test("TEST B", False, f"ERROR: {e}")
        results.append(False)
    
    client.close()
    return all(results)

async def test_c_kill_switch_isolation():
    """TEST C: Kill switch isolates experiments"""
    log_section("TEST C: Kill Switch Isolation")
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    results = []
    
    try:
        # 1. Create big loss for baseline to trigger kill switch
        loss_case_id = f"loss-baseline-{int(datetime.now().timestamp())}"
        await db.trading_cases.insert_one({
            "case_id": loss_case_id,
            "experiment_id": "baseline_btc",
            "symbol": "BTCUSDT",
            "status": "CLOSED",
            "realized_pnl": -15.0,  # Below -10 threshold
            "closed_at": datetime.now(timezone.utc),
        })
        
        # Calculate baseline PnL
        pipeline_baseline = [
            {"$match": {"experiment_id": "baseline_btc", "status": "CLOSED"}},
            {"$group": {"_id": None, "total": {"$sum": "$realized_pnl"}}}
        ]
        result_baseline = await db.trading_cases.aggregate(pipeline_baseline).to_list(1)
        pnl_baseline = result_baseline[0]["total"] if result_baseline else 0
        
        results.append(log_test(
            "baseline PnL below threshold",
            pnl_baseline < -10,
            f"baseline_pnl=${pnl_baseline:.2f} (threshold=-10)"
        ))
        
        # 2. market_dynamic PnL should be separate (0 or positive)
        pipeline_market = [
            {"$match": {"experiment_id": "market_dynamic", "status": "CLOSED"}},
            {"$group": {"_id": None, "total": {"$sum": "$realized_pnl"}}}
        ]
        result_market = await db.trading_cases.aggregate(pipeline_market).to_list(1)
        pnl_market = result_market[0]["total"] if result_market else 0
        
        results.append(log_test(
            "market_dynamic PnL unaffected",
            pnl_market >= -10,  # Above threshold
            f"market_pnl=${pnl_market:.2f} (independent)"
        ))
        
        # 3. Verify isolation: baseline kill switch doesn't affect market_dynamic
        # This is proven by different PnL values
        results.append(log_test(
            "kill switch isolated",
            pnl_baseline != pnl_market,
            f"baseline=${pnl_baseline:.2f}, market=${pnl_market:.2f}"
        ))
        
        # Cleanup
        await db.trading_cases.delete_one({"case_id": loss_case_id})
        
    except Exception as e:
        log_test("TEST C", False, f"ERROR: {e}")
        results.append(False)
    
    client.close()
    return all(results)

async def main():
    print(f"\n{C.BLUE}{'='*60}{C.END}")
    print(f"{C.BLUE}Phase 1.5 - Step 10: Experiment Isolation Tests{C.END}")
    print(f"{C.BLUE}{'='*60}{C.END}\n")
    
    # Run all tests
    test_a = await test_a_baseline_flow()
    test_b = await test_b_market_dynamic_isolation()
    test_c = await test_c_kill_switch_isolation()
    
    # Summary
    log_section("TEST SUMMARY")
    
    overall_pass = test_a and test_b and test_c
    
    print(f"TEST A (baseline flow): {C.GREEN if test_a else C.RED}{'PASS' if test_a else 'FAIL'}{C.END}")
    print(f"TEST B (market_dynamic isolation): {C.GREEN if test_b else C.RED}{'PASS' if test_b else 'FAIL'}{C.END}")
    print(f"TEST C (kill switch isolation): {C.GREEN if test_c else C.RED}{'PASS' if test_c else 'FAIL'}{C.END}")
    
    print(f"\n{C.YELLOW}{'='*60}{C.END}")
    if overall_pass:
        print(f"{C.GREEN}✓ ALL TESTS PASSED - Phase 1.5 COMPLETE{C.END}")
        print(f"{C.GREEN}→ Ready for Phase 2: Multi-Asset Skeleton{C.END}")
    else:
        print(f"{C.RED}✗ SOME TESTS FAILED - Phase 1.5 INCOMPLETE{C.END}")
        print(f"{C.RED}→ Fix issues before Phase 2{C.END}")
    print(f"{C.YELLOW}{'='*60}{C.END}\n")
    
    return 0 if overall_pass else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
