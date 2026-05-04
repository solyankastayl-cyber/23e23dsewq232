"""
RISK GUARD TEST — Exercises all 5 guards and generates the report.
Run: python3 /app/backend/tests/test_risk_guard.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import uuid

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "trading_os"


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("=" * 70)
    print("  RISK GUARD REPORT — FOMO-Trade v1.2")
    print("  Generated:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    print("=" * 70)

    # ─── 1. Config ────────────────────────────────────────
    from modules.risk_guard import init_risk_guard, RiskGuard, get_risk_guard
    guard = init_risk_guard(db=db)
    status = guard.get_status()
    cfg = status["config"]

    print()
    print("  CONFIGURATION")
    print("  ─────────────────────────────────────────────")
    print(f"  MAX_POSITION_SIZE_USD   : ${cfg['max_position_size_usd']:.2f}")
    print(f"  MAX_OPEN_POSITIONS      : {cfg['max_open_positions']}")
    print(f"  KILL_SWITCH_THRESHOLD   : ${cfg['kill_switch_threshold_usd']:.2f}")
    print()

    results = []

    # ─── Guard 1: Max Position Size ──────────────────────
    print("  GUARD 1: Max Position Size ($100)")
    print("  ─────────────────────────────────────────────")
    # Test: $500 should be rejected
    r1a = await guard.check_pre_execution({
        "symbol": "BTCUSDT", "decision_id": "test-g1-500", "size_usd": 500
    })
    passed_1a = not r1a["allowed"]
    print(f"  [TEST] $500 order → {'REJECTED' if passed_1a else 'PASSED (BUG!)'}: {r1a.get('reason', 'allowed')}")

    # Test: $50 should pass
    r1b = await guard.check_pre_execution({
        "symbol": "BTCUSDT", "decision_id": f"test-g1-50-{uuid.uuid4().hex[:6]}", "size_usd": 50
    })
    passed_1b = r1b["allowed"]
    print(f"  [TEST] $50 order  → {'PASSED' if passed_1b else 'REJECTED (BUG!)'}: {'allowed' if r1b['allowed'] else r1b.get('reason')}")

    # Test: $100 exactly should pass
    r1c = await guard.check_pre_execution({
        "symbol": "ETHUSDT", "decision_id": f"test-g1-100-{uuid.uuid4().hex[:6]}", "size_usd": 100
    })
    passed_1c = r1c["allowed"]
    print(f"  [TEST] $100 order → {'PASSED' if passed_1c else 'REJECTED (BUG!)'}: {'allowed' if r1c['allowed'] else r1c.get('reason')}")

    # Test: $101 should be rejected
    r1d = await guard.check_pre_execution({
        "symbol": "SOLUSDT", "decision_id": f"test-g1-101-{uuid.uuid4().hex[:6]}", "size_usd": 101
    })
    passed_1d = not r1d["allowed"]
    print(f"  [TEST] $101 order → {'REJECTED' if passed_1d else 'PASSED (BUG!)'}: {r1d.get('reason', 'allowed')}")

    g1_pass = all([passed_1a, passed_1b, passed_1c, passed_1d])
    results.append(("Max Position Size ($100)", g1_pass))
    print(f"  RESULT: {'PASS' if g1_pass else 'FAIL'}")
    print()

    # ─── Guard 2: Max Open Positions ─────────────────────
    print("  GUARD 2: Max Open Positions (5)")
    print("  ─────────────────────────────────────────────")
    open_count = await db.portfolio_positions.count_documents({"status": "OPEN"})
    print(f"  Current open positions: {open_count}")

    # Create temporary positions to fill to max
    temp_ids = []
    needed = max(0, 5 - open_count)
    for i in range(needed):
        temp_id = f"test-maxpos-{uuid.uuid4().hex[:6]}"
        await db.portfolio_positions.insert_one({
            "symbol": f"TEST{i}USDT", "side": "LONG", "qty": 0.001,
            "entry_price": 100, "mark_price": 100, "unrealized_pnl": 0,
            "status": "OPEN", "test_temp": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        temp_ids.append(temp_id)

    open_after = await db.portfolio_positions.count_documents({"status": "OPEN"})
    print(f"  Open positions after fill: {open_after}")

    # Now try to add one more — should be rejected
    r2 = await guard.check_pre_execution({
        "symbol": "BTCUSDT", "decision_id": f"test-g2-{uuid.uuid4().hex[:6]}", "size_usd": 50
    })
    passed_2 = not r2["allowed"]
    print(f"  [TEST] 6th position → {'REJECTED' if passed_2 else 'PASSED (BUG!)'}: {r2.get('reason', 'allowed')}")

    # Clean up temp positions
    await db.portfolio_positions.delete_many({"test_temp": True})
    open_cleaned = await db.portfolio_positions.count_documents({"status": "OPEN"})
    print(f"  Cleaned up temp positions. Open now: {open_cleaned}")

    results.append(("Max Open Positions (5)", passed_2))
    print(f"  RESULT: {'PASS' if passed_2 else 'FAIL'}")
    print()

    # ─── Guard 3: Duplicate Protection ───────────────────
    print("  GUARD 3: Duplicate Protection (1 decision → 1 position)")
    print("  ─────────────────────────────────────────────")
    
    # Create a trading case with a known decision_id
    dup_decision_id = f"dup-test-{uuid.uuid4().hex[:8]}"
    await db.trading_cases.insert_one({
        "decision_id": dup_decision_id,
        "symbol": "BTCUSDT",
        "side": "LONG",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Try to execute with same decision_id — should be rejected
    r3 = await guard.check_pre_execution({
        "symbol": "BTCUSDT", "decision_id": dup_decision_id, "size_usd": 50
    })
    passed_3 = not r3["allowed"]
    print(f"  [TEST] Duplicate {dup_decision_id} → {'REJECTED' if passed_3 else 'PASSED (BUG!)'}: {r3.get('reason', 'allowed')}")

    # Clean up
    await db.trading_cases.delete_one({"decision_id": dup_decision_id})

    results.append(("Duplicate Protection", passed_3))
    print(f"  RESULT: {'PASS' if passed_3 else 'FAIL'}")
    print()

    # ─── Guard 4: Close Integrity (PnL Sanity Check) ─────
    print("  GUARD 4: Close Integrity — PnL Sanity Check")
    print("  ─────────────────────────────────────────────")

    # Test correct PnL
    verified_ok = RiskGuard.verify_close_pnl(
        symbol="BTCUSDT", side="LONG",
        entry_price=74000.0, exit_price=74100.0,
        qty=0.1, stored_pnl=10.0
    )
    print(f"  [TEST] LONG BTC entry=$74,000 exit=$74,100 qty=0.1 → calc=$10.00 stored=$10.00 → {'MATCH' if verified_ok else 'MISMATCH (BUG!)'}")

    # Test incorrect PnL
    verified_bad = RiskGuard.verify_close_pnl(
        symbol="ETHUSDT", side="SHORT",
        entry_price=2350.0, exit_price=2340.0,
        qty=2.0, stored_pnl=999.99  # Wrong!
    )
    print(f"  [TEST] SHORT ETH entry=$2,350 exit=$2,340 qty=2.0 → calc=$20.00 stored=$999.99 → {'MISMATCH' if not verified_bad else 'MATCH (BUG!)'}")

    # Test short correctly
    verified_short = RiskGuard.verify_close_pnl(
        symbol="SOLUSDT", side="SHORT",
        entry_price=85.0, exit_price=80.0,
        qty=10.0, stored_pnl=50.0
    )
    print(f"  [TEST] SHORT SOL entry=$85 exit=$80 qty=10 → calc=$50.00 stored=$50.00 → {'MATCH' if verified_short else 'MISMATCH (BUG!)'}")

    g4_pass = verified_ok and (not verified_bad) and verified_short
    results.append(("Close Integrity (PnL Sanity)", g4_pass))
    print(f"  RESULT: {'PASS' if g4_pass else 'FAIL'}")
    print()

    # ─── Guard 5: Kill Switch ────────────────────────────
    print("  GUARD 5: Kill Switch (Total PnL < -$10)")
    print("  ─────────────────────────────────────────────")

    # Reset kill switch first
    guard.reset_kill_switch()

    # Inject fake closed cases with big losses
    loss_ids = []
    for i in range(3):
        lid = f"killswitch-test-{uuid.uuid4().hex[:6]}"
        await db.trading_cases.insert_one({
            "decision_id": lid,
            "symbol": "BTCUSDT",
            "side": "LONG",
            "status": "CLOSED",
            "realized_pnl": -5.0,  # Each loses $5, total = -$15 (below -$10 threshold)
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        loss_ids.append(lid)

    # Now check — should trigger kill switch
    r5 = await guard.check_pre_execution({
        "symbol": "BTCUSDT", "decision_id": f"test-g5-{uuid.uuid4().hex[:6]}", "size_usd": 50
    })
    
    # Kill switch checks realised PnL of ALL closed cases, including the real ones (~+$17).
    # Total = real_pnl + fake_losses = ~$17 + (-15) = ~$2 → might NOT trigger.
    # Let me calculate the exact total and adjust
    pipeline = [
        {"$match": {"status": "CLOSED"}},
        {"$group": {"_id": None, "total": {"$sum": "$realized_pnl"}}}
    ]
    cursor = db.trading_cases.aggregate(pipeline)
    agg_results = await cursor.to_list(length=1)
    total_pnl = agg_results[0]["total"] if agg_results else 0
    print(f"  Total realized PnL (all closed): ${total_pnl:.4f}")

    # Clean up fake losses
    await db.trading_cases.delete_many({"decision_id": {"$in": loss_ids}})

    # If total wasn't negative enough, inject bigger losses
    if total_pnl >= -10:
        print(f"  PnL ${total_pnl:.2f} > -$10, injecting larger test losses...")
        guard.reset_kill_switch()
        big_loss_ids = []
        for i in range(5):
            lid = f"killswitch-big-{uuid.uuid4().hex[:6]}"
            await db.trading_cases.insert_one({
                "decision_id": lid,
                "symbol": "BTCUSDT",
                "side": "LONG",
                "status": "CLOSED",
                "realized_pnl": -10.0,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            big_loss_ids.append(lid)

        r5 = await guard.check_pre_execution({
            "symbol": "BTCUSDT", "decision_id": f"test-g5-big-{uuid.uuid4().hex[:6]}", "size_usd": 50
        })
        
        # Check new total
        cursor2 = db.trading_cases.aggregate(pipeline)
        agg2 = await cursor2.to_list(length=1)
        new_total = agg2[0]["total"] if agg2 else 0
        print(f"  New total realized PnL: ${new_total:.4f}")

        # Clean up
        await db.trading_cases.delete_many({"decision_id": {"$in": big_loss_ids}})

    passed_5 = not r5["allowed"] and "KILL SWITCH" in r5.get("reason", "")
    print(f"  [TEST] Order after kill switch → {'REJECTED' if passed_5 else 'PASSED (BUG!)'}: {r5.get('reason', 'allowed')}")
    
    # Reset kill switch for normal operation
    guard.reset_kill_switch()

    results.append(("Kill Switch (< -$10)", passed_5))
    print(f"  RESULT: {'PASS' if passed_5 else 'FAIL'}")
    print()

    # ─── Integrity Check ─────────────────────────────────
    print("  INTEGRITY CHECK")
    print("  ─────────────────────────────────────────────")
    integrity = await guard.integrity_check()
    print(f"  Orphaned outcomes     : {integrity['orphaned_outcomes']}")
    print(f"  Unclosed w/o PnL      : {integrity['unclosed_positions_without_pnl']}")
    print(f"  PnL mismatches        : {integrity['pnl_mismatches']}")
    print(f"  Checked at            : {integrity['checked_at']}")
    print()

    # ─── PnL VERIFICATION ────────────────────────────────
    print("  PnL VERIFICATION — Closed Cases")
    print("  ─────────────────────────────────────────────")
    closed_cases = await db.trading_cases.find(
        {"status": "CLOSED"},
        {"_id": 0, "symbol": 1, "side": 1, "avg_entry_price": 1,
         "current_price": 1, "qty": 1, "realized_pnl": 1, "decision_id": 1}
    ).to_list(length=100)

    total_realized = 0
    verified_count = 0
    mismatch_count = 0
    for c in closed_cases:
        entry = c.get("avg_entry_price", 0)
        exit_p = c.get("current_price", 0)
        qty = c.get("qty", 0)
        side = c.get("side", "LONG")
        stored = c.get("realized_pnl", 0)
        total_realized += stored

        direction = 1.0 if side == "LONG" else -1.0
        calc = (exit_p - entry) * qty * direction
        match = abs(calc - stored) <= 0.01
        if match:
            verified_count += 1
        else:
            mismatch_count += 1
        
        status = "OK" if match else "MISMATCH!"
        print(f"  {c.get('decision_id','?')[:25]:25s} {c['symbol']:10s} {side:5s} "
              f"entry=${entry:>10,.2f} exit=${exit_p:>10,.2f} qty={qty:.6f} "
              f"pnl=${stored:>8.4f} calc=${calc:>8.4f} [{status}]")

    print()
    print(f"  Total closed cases    : {len(closed_cases)}")
    print(f"  PnL verified (match)  : {verified_count}")
    print(f"  PnL mismatches        : {mismatch_count}")
    print(f"  Total realized PnL    : ${total_realized:.4f}")
    print()

    # ─── Final Stats ─────────────────────────────────────
    final_stats = guard.get_status()["stats"]
    print("  EXECUTION STATS (this test session)")
    print("  ─────────────────────────────────────────────")
    print(f"  Total checked         : {final_stats['total_checked']}")
    print(f"  Passed                : {final_stats['passed']}")
    print(f"  Rejected (max size)   : {final_stats['rejected_max_size']}")
    print(f"  Rejected (max pos)    : {final_stats['rejected_max_positions']}")
    print(f"  Rejected (duplicate)  : {final_stats['rejected_duplicate']}")
    print(f"  Rejected (kill switch): {final_stats['rejected_kill_switch']}")
    print()

    # ─── Summary ─────────────────────────────────────────
    print("=" * 70)
    print("  RISK GUARD SUMMARY")
    print("=" * 70)
    all_pass = True
    for name, passed in results:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}")
        if not passed:
            all_pass = False
    print()
    if all_pass:
        print("  ALL 5 GUARDS OPERATIONAL")
    else:
        print("  SOME GUARDS FAILED — SEE ABOVE")
    print("=" * 70)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
