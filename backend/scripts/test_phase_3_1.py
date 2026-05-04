"""
Phase 3.1 Test Script
=====================

Test execution quality validation layer.

Flow:
  1. Ensure sufficient shadow trades exist (with resolved 24h horizon)
  2. Ensure sufficient paper positions exist (CLOSED)
  3. Call GET /api/experiments/market_dynamic/execution-quality
  4. Validate gates and verdict
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import random

# Add parent to path
sys.path.insert(0, "/app/backend")

# Config
EXPERIMENT_ID = "market_dynamic"
HORIZON = "24h"
MIN_REQUIRED_PAIRS = 20

# Symbols for testing
TEST_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
TIMEFRAMES = ["4h", "1h"]
SIDES = ["LONG", "SHORT"]


async def setup_test_data(db):
    """
    Setup sufficient test data for Phase 3.1.
    
    Creates:
      - 30 shadow trades (with resolved 24h horizon)
      - 25 paper positions (CLOSED)
      - 20+ matched pairs
    """
    print("\n=== Phase 3.1 Test Data Setup ===\n")
    
    # Check existing data
    shadow_count = await count_shadow_trades(db)
    paper_count = await count_paper_positions(db)
    
    print(f"Existing shadow trades (24h resolved): {shadow_count}")
    print(f"Existing paper positions (CLOSED): {paper_count}")
    
    # Generate paper positions to match shadow trades
    if shadow_count < MIN_REQUIRED_PAIRS:
        print(f"\n⚠️  Warning: Only {shadow_count} shadow trades available (need {MIN_REQUIRED_PAIRS})")
        print("    Phase 3.1 requires more shadow trades to be generated first.")
        target_positions = shadow_count
    else:
        target_positions = min(shadow_count, 25)  # Match up to 25 shadow trades
    
    if paper_count < target_positions:
        print(f"\n→ Generating {target_positions - paper_count} paper positions...")
        await generate_paper_positions(db, target_positions - paper_count)
    
    # Verify final counts
    final_shadow = await count_shadow_trades(db)
    final_paper = await count_paper_positions(db)
    
    print(f"\n✓ Final shadow trades: {final_shadow}")
    print(f"✓ Final paper positions: {final_paper}")
    print(f"✓ Expected matched pairs: ~{min(final_shadow, final_paper)}")


async def count_shadow_trades(db) -> int:
    """Count shadow trades with resolved 24h horizon."""
    pipeline = [
        {"$unwind": "$horizons"},
        {"$match": {
            "experiment_id": EXPERIMENT_ID,
            "horizons.name": HORIZON,
            "horizons.resolved": True
        }},
        {"$count": "total"}
    ]
    
    result = await db.shadow_trades.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


async def count_paper_positions(db) -> int:
    """Count closed paper positions."""
    return await db.paper_positions.count_documents({
        "experiment_id": EXPERIMENT_ID,
        "status": "CLOSED"
    })


async def generate_paper_positions(db, count: int):
    """
    Generate closed paper positions that match existing shadow trades.
    
    Fetches real shadow trades and creates matching paper positions.
    """
    # First, delete any test paper positions
    delete_result = await db.paper_positions.delete_many({
        "experiment_id": EXPERIMENT_ID,
        "paper_decision_id": {"$regex": "^decision_"}
    })
    
    if delete_result.deleted_count > 0:
        print(f"  ✓ Deleted {delete_result.deleted_count} old test positions")
    
    # Get real shadow trades with resolved 24h horizon
    pipeline = [
        {"$unwind": "$horizons"},
        {"$match": {
            "experiment_id": EXPERIMENT_ID,
            "horizons.name": HORIZON,
            "horizons.resolved": True
        }},
        {"$project": {
            "snapshot_id": 1,
            "symbol": 1,
            "timeframe": 1,
            "side": 1,
            "entry_price": 1,
            "entry_time": 1,
            "pnl": "$horizons.pnl",
            "exit_price": "$horizons.exit_price"
        }},
        {"$limit": count}
    ]
    
    shadow_trades = await db.shadow_trades.aggregate(pipeline).to_list(length=count)
    
    if not shadow_trades:
        print("  ❌ No shadow trades found to match")
        return
    
    print(f"  → Found {len(shadow_trades)} shadow trades to match")
    
    positions = []
    
    for i, shadow in enumerate(shadow_trades):
        # Use exact snapshot_id from shadow trade
        snapshot_id = shadow["snapshot_id"]
        symbol = shadow["symbol"]
        timeframe = shadow["timeframe"]
        side = shadow["side"]
        
        # Use shadow entry price with slight slippage
        shadow_entry = shadow["entry_price"]
        slippage = random.uniform(0.0005, 0.0020)  # 0.05% to 0.20%
        
        if side == "LONG":
            actual_entry = shadow_entry * (1 + slippage)
        else:
            actual_entry = shadow_entry * (1 - slippage)
        
        # Calculate exit price with similar PnL to shadow (with slight degradation)
        shadow_pnl = shadow["pnl"]
        degradation = random.uniform(-0.002, 0.001)  # -0.2% to +0.1%
        paper_pnl = shadow_pnl + degradation
        
        if side == "LONG":
            exit_price = actual_entry * (1 + paper_pnl)
        else:
            exit_price = actual_entry * (1 - paper_pnl)
        
        entry_time = shadow.get("entry_time", datetime.now(timezone.utc) - timedelta(hours=48))
        exit_time = entry_time + timedelta(hours=24)
        
        size_usd = 100.0
        qty = size_usd / actual_entry
        pnl_usd = paper_pnl * size_usd
        
        position = {
            "experiment_id": EXPERIMENT_ID,
            "paper_decision_id": f"decision_{i:04d}",
            "snapshot_id": snapshot_id,  # Exact match with shadow
            "symbol": symbol,
            "timeframe": timeframe,
            "side": side,
            "entry_price": actual_entry,
            "entry_time": entry_time,
            "size_usd": size_usd,
            "qty": qty,
            "status": "CLOSED",
            "close_after": exit_time,
            "exit_price": exit_price,
            "exit_time": exit_time,
            "pnl_pct": round(paper_pnl, 6),
            "pnl_usd": round(pnl_usd, 2)
        }
        
        positions.append(position)
    
    if positions:
        await db.paper_positions.insert_many(positions)
        print(f"  ✓ Created {len(positions)} paper positions matched to shadow trades")


async def test_execution_quality_endpoint():
    """
    Test execution quality endpoint.
    
    Makes HTTP request and validates response.
    """
    import aiohttp
    
    print("\n=== Testing Execution Quality Endpoint ===\n")
    
    url = "http://localhost:8001/api/experiments/market_dynamic/execution-quality"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"horizon": HORIZON}) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"❌ HTTP {response.status}: {text}")
                    return None
                
                data = await response.json()
                
                if not data.get("ok"):
                    print(f"❌ API returned ok=False: {data}")
                    return None
                
                print("✓ Endpoint responded successfully\n")
                return data.get("report")
    
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def validate_report(report):
    """
    Validate execution quality report.
    
    Checks:
      - All required fields present
      - Matched pairs >= 20
      - Verdict state is valid
      - Gates evaluated correctly
    """
    print("=== Validating Report ===\n")
    
    if not report:
        print("❌ No report to validate")
        return False
    
    # Check structure
    required_keys = ["summary", "frictions", "verdict", "thresholds"]
    for key in required_keys:
        if key not in report:
            print(f"❌ Missing key: {key}")
            return False
    
    print("✓ Report structure valid")
    
    # Check summary
    summary = report["summary"]
    print(f"\n📊 Summary:")
    print(f"  • Matched pairs: {summary.get('matched_pairs', 0)}")
    print(f"  • Shadow trades: {summary.get('shadow_trades', 0)}")
    print(f"  • Paper positions: {summary.get('paper_positions', 0)}")
    print(f"  • Match coverage: {summary.get('match_coverage', 0):.2%}")
    print(f"  • Execution quality: {summary.get('execution_quality', 0):.6f}")
    print(f"  • Shadow winrate: {summary.get('shadow_winrate', 0):.2%}")
    print(f"  • Paper winrate: {summary.get('paper_winrate', 0):.2%}")
    print(f"  • Winrate delta: {summary.get('winrate_delta', 0):.2%}")
    
    # Check frictions
    frictions = report["frictions"]
    print(f"\n⚠️  Frictions:")
    print(f"  • Policy rejection rate: {frictions.get('policy_rejection_rate', 0):.2%}")
    print(f"  • Cooldown miss rate: {frictions.get('cooldown_miss_rate', 0):.2%}")
    print(f"  • Avg entry delay: {frictions.get('avg_entry_delay_pct', 0):.4%}")
    print(f"  • Max entry delay: {frictions.get('max_entry_delay_pct', 0):.4%}")
    
    # Check verdict
    verdict = report["verdict"]
    state = verdict.get("state", "unknown")
    reason = verdict.get("reason", "N/A")
    gates_passed = verdict.get("gates_passed", [])
    gates_failed = verdict.get("gates_failed", [])
    
    print(f"\n🚦 Verdict: {state.upper()}")
    print(f"  Reason: {reason}")
    print(f"  Gates passed: {len(gates_passed)}/6")
    print(f"  Gates failed: {len(gates_failed)}/6")
    
    if gates_passed:
        print(f"\n  ✓ Passed gates:")
        for gate in gates_passed:
            print(f"    - {gate}")
    
    if gates_failed:
        print(f"\n  ✗ Failed gates:")
        for gate in gates_failed:
            print(f"    - {gate}")
    
    # Validate minimum pairs
    matched_pairs = summary.get("matched_pairs", 0)
    if matched_pairs < MIN_REQUIRED_PAIRS:
        print(f"\n❌ Insufficient matched pairs: {matched_pairs} < {MIN_REQUIRED_PAIRS}")
        return False
    
    print(f"\n✓ Sufficient matched pairs: {matched_pairs} >= {MIN_REQUIRED_PAIRS}")
    
    # Validate verdict state
    valid_states = ["ready", "limited", "blocked"]
    if state not in valid_states:
        print(f"\n❌ Invalid verdict state: {state}")
        return False
    
    print(f"✓ Valid verdict state: {state}")
    
    return True


async def main():
    """Main test flow."""
    print("\n" + "=" * 60)
    print("PHASE 3.1 — Execution Validation Layer")
    print("Test Script")
    print("=" * 60)
    
    # Connect to DB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    try:
        # 1. Setup test data
        await setup_test_data(db)
        
        # 2. Test endpoint
        report = await test_execution_quality_endpoint()
        
        # 3. Validate report
        if report:
            success = validate_report(report)
            
            print("\n" + "=" * 60)
            if success:
                print("✅ PHASE 3.1 VALIDATION PASSED")
            else:
                print("❌ PHASE 3.1 VALIDATION FAILED")
            print("=" * 60 + "\n")
        else:
            print("\n" + "=" * 60)
            print("❌ ENDPOINT TEST FAILED")
            print("=" * 60 + "\n")
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
