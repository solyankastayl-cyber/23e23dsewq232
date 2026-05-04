#!/usr/bin/env python3
"""
Shadow-Only Data Collection - Phase A.3
========================================

Pure discovery → shadow trades collection.
NO execution layer, NO filters contamination, NO bias.

Goal: Collect 50-100 REAL shadow trades to understand market truth.

Rules:
- Save EVERYTHING (even "bad" signals)
- NO filtering
- NO optimization
- Accelerated horizon (1-2h instead of 24h) for faster collection
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from modules.market_intelligence.universe_scanner import scan_market_universe
from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner
from modules.scanner.market_data.binance_provider import get_market_data_provider
from modules.strategy.signal_ranking import rank_signals


async def create_shadow_trade(db, signal: Dict[str, Any], horizon_hours: int = 1, experiment_id: str = "market_dynamic") -> str:
    """
    Create a pure shadow trade (no execution layer involved).
    
    Args:
        db: MongoDB database
        signal: Signal from discovery
        horizon_hours: Hours until exit (1-2h for accelerated collection)
        experiment_id: Experiment ID for isolation
    
    Returns:
        trade_id
    """
    now = datetime.now(timezone.utc)
    exit_time = now + timedelta(hours=horizon_hours)
    
    trade = {
        # Identity
        "experiment_id": experiment_id,
        "symbol": signal["symbol"],
        "timeframe": signal["timeframe"],
        "side": signal["side"],
        
        # Entry
        "entry_price": signal.get("price", signal.get("entry")),
        "entry_time": now,
        
        # Features (CRITICAL for analysis)
        "features": {
            "cluster": signal.get("cluster", "unknown"),
            "alignment": signal.get("alignment", "unknown"),  # WARNING: provisional (confidence threshold, not true alignment)
            "score": signal.get("confidence", 0.5),
        },
        
        # Exit (to be resolved)
        "horizons": [{
            "name": f"{horizon_hours}h",
            "target_exit_time": exit_time,
            "resolved": False,
            "exit_price": None,
            "pnl": None,
        }],
        
        # Metadata
        "created_at": now,
        "source": "shadow_collection_loop",
    }
    
    result = await db.shadow_trades.insert_one(trade)
    return str(result.inserted_id)


async def resolve_expired_trades(db, market_data):
    """
    Resolve shadow trades that reached their horizon.
    
    Uses current market price to calculate PnL.
    """
    now = datetime.now(timezone.utc)
    
    # Find unresolved trades past their exit time
    cursor = db.shadow_trades.find({
        "horizons.resolved": False,
        "horizons.target_exit_time": {"$lte": now}
    })
    
    resolved_count = 0
    
    async for trade in cursor:
        symbol = trade["symbol"]
        timeframe = trade["timeframe"]
        
        # Get current price
        exit_price = market_data.get_last_price(symbol, timeframe)
        
        if exit_price is None:
            continue
        
        # Calculate PnL
        entry_price = trade["entry_price"]
        side = trade["side"]
        
        if side == "BUY" or side == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SHORT
            pnl_pct = (entry_price - exit_price) / entry_price
        
        # Update trade
        await db.shadow_trades.update_one(
            {"_id": trade["_id"]},
            {
                "$set": {
                    "horizons.0.resolved": True,
                    "horizons.0.exit_price": exit_price,
                    "horizons.0.pnl": pnl_pct,
                    "horizons.0.resolve_at": now,
                }
            }
        )
        
        resolved_count += 1
    
    return resolved_count


async def shadow_collection_loop(
    target_trades: int = 50,
    horizon_hours: int = 1,
    cycle_interval_minutes: int = 5,
    experiment_id: str = "market_dynamic"
):
    """
    Main shadow collection loop.
    
    Args:
        target_trades: Stop after collecting this many trades
        horizon_hours: Trade duration (1-2h for fast collection)
        cycle_interval_minutes: Time between cycles
        experiment_id: Experiment ID for isolation (e.g., "batch2_4h")
    """
    
    print("\n" + "="*70)
    print("🔬 SHADOW-ONLY DATA COLLECTION")
    print("="*70)
    print(f"Experiment: {experiment_id}")
    print(f"Target: {target_trades} trades")
    print(f"Horizon: {horizon_hours}h")
    print(f"Cycle interval: {cycle_interval_minutes} minutes")
    print(f"Mode: PURE DISCOVERY (no execution layer)")
    print("="*70 + "\n")
    
    # Setup
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    market_data = get_market_data_provider()
    
    runner = get_market_dynamic_runner(market_data_service=market_data, db=db)
    
    cycle = 0
    total_created = 0
    total_resolved = 0
    
    while True:
        cycle += 1
        cycle_start = datetime.now(timezone.utc)
        
        print(f"\n{'─'*70}")
        print(f"🔄 Cycle {cycle} - {cycle_start.strftime('%H:%M:%S')}")
        print(f"{'─'*70}")
        
        try:
            # Step 1: Resolve expired trades
            print(f"[1/4] Resolving expired trades...")
            resolved = await resolve_expired_trades(db, market_data)
            total_resolved += resolved
            if resolved > 0:
                print(f"      ✅ Resolved {resolved} trades")
            
            # Step 2: Scan universe
            print(f"[2/4] Scanning universe...")
            scan_result = await scan_market_universe()
            eligible = [s for s in scan_result if s.get("eligible")]
            print(f"      ✅ Found {len(eligible)} eligible assets")
            
            if not eligible:
                print(f"      ⚠️  No eligible assets, skipping cycle")
                await asyncio.sleep(cycle_interval_minutes * 60)
                continue
            
            # Step 3: Generate signals (pure discovery)
            print(f"[3/4] Generating signals...")
            signals_result = await runner._generate_signals(eligible)
            signals = signals_result.get("signals", [])
            print(f"      ✅ Generated {len(signals)} signals")
            
            if not signals:
                print(f"      ⚠️  No signals generated")
                await asyncio.sleep(cycle_interval_minutes * 60)
                continue
            
            # Step 4: Rank signals (but DON'T filter - save all)
            print(f"[4/4] Ranking signals (no filtering)...")
            ranked = rank_signals(
                signals=signals,
                stats_map={},
                execution_map={},
                regime="trend",
                portfolio={"risk_heat": 0.0},
                open_positions=[],
                min_score=0.0  # Accept ALL signals for truth collection
            )
            
            # CRITICAL: Save ALL signals, even rejected ones
            # We want to see what fails, not hide it
            
            # CORRECTION 1: Prevent top-N bias
            # Use random sampling if limiting, NOT top-N ranking
            import random
            
            # BATCH 2 CORRECTION: Max 5-7 per cycle
            max_per_cycle = min(7, max(5, len(signals) // 3))  # Adaptive 5-7 range
            
            if len(signals) > max_per_cycle:
                # Random sample to prevent ranking bias
                signals_to_save = random.sample(signals, k=max_per_cycle)
                print(f"      ⚠️  Limited to random {max_per_cycle}/{len(signals)} signals (prevent bias)")
            else:
                signals_to_save = signals
            
            # CORRECTION 2: Limit 1 trade per symbol per cycle
            # Prevents correlation contamination (BTCUSDT 1H+4H+1D = same market)
            seen_symbols = set()
            deduped_signals = []
            for signal in signals_to_save:
                symbol = signal["symbol"]
                if symbol not in seen_symbols:
                    deduped_signals.append(signal)
                    seen_symbols.add(symbol)
            
            if len(deduped_signals) < len(signals_to_save):
                print(f"      ⚠️  Deduplicated: {len(signals_to_save)} → {len(deduped_signals)} (1 per symbol)")
            
            signals_to_save = deduped_signals
            
            print(f"      ✅ Ranked {len(ranked)} signals")
            
            # Step 5: Create shadow trades for deduplicated signals
            created_this_cycle = 0
            for signal in signals_to_save:
                trade_id = await create_shadow_trade(db, signal, horizon_hours, experiment_id)
                created_this_cycle += 1
                total_created += 1
            
            print(f"      ✅ Created {created_this_cycle} shadow trades")
            
            # Status update
            current_total = await db.shadow_trades.count_documents({"experiment_id": experiment_id})
            resolved_total = await db.shadow_trades.count_documents({
                "experiment_id": experiment_id,
                "horizons.resolved": True
            })
            
            print(f"\n📊 Status:")
            print(f"   Total shadow trades: {current_total}")
            print(f"   Resolved: {resolved_total}")
            print(f"   Pending: {current_total - resolved_total}")
            print(f"   Progress: {resolved_total}/{target_trades} ({resolved_total/target_trades*100:.0f}%)")
            
            # Check if target reached
            if resolved_total >= target_trades:
                print(f"\n{'='*70}")
                print(f"🎯 TARGET REACHED: {resolved_total} trades collected!")
                print(f"{'='*70}")
                print(f"\nNext step:")
                print(f"  curl http://localhost:8001/api/debug/features-from-shadow")
                break
            
        except Exception as e:
            print(f"❌ Error in cycle {cycle}: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait before next cycle
        cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        sleep_time = max(1, cycle_interval_minutes * 60 - cycle_duration)
        print(f"\n⏳ Sleeping {sleep_time:.0f}s until next cycle...")
        await asyncio.sleep(sleep_time)
    
    print(f"\n{'='*70}")
    print(f"✅ COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"Total cycles: {cycle}")
    print(f"Total trades created: {total_created}")
    print(f"Total trades resolved: {total_resolved}")
    print(f"\nData ready for analysis!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Shadow-only data collection")
    parser.add_argument("--target", type=int, default=35, help="Target number of trades")
    parser.add_argument("--horizon", type=int, default=4, help="Trade horizon in hours")
    parser.add_argument("--interval", type=int, default=15, help="Minutes between cycles")
    parser.add_argument("--experiment", type=str, default="batch2_4h", help="Experiment ID for isolation")
    
    args = parser.parse_args()
    
    asyncio.run(shadow_collection_loop(
        target_trades=args.target,
        horizon_hours=args.horizon,
        cycle_interval_minutes=args.interval,
        experiment_id=args.experiment
    ))
