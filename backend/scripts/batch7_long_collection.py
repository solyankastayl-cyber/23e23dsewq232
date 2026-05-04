#!/usr/bin/env python3
"""
Batch 7: BUY-Only Collection (Trend Pullback Long)
===================================================

Phase A.9: Test NEW BUY engine in isolation.

Generator: trend_pullback_long_v1
Side: BUY ONLY
Target: 25-35 resolved trades
Horizon: 4h

Goal: Prove viability of new BUY architecture (NOT perfection).
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from modules.market_intelligence.universe_scanner import scan_market_universe
from modules.scanner.market_data.binance_provider import get_market_data_provider
from modules.signal_generator.trend_pullback_long_generator import TrendPullbackLongGenerator


async def create_shadow_trade(db, signal: Dict[str, Any], horizon_hours: int = 4, experiment_id: str = "batch7_buy_pullback_only") -> str:
    """Create shadow trade for BUY signal."""
    now = datetime.now(timezone.utc)
    exit_time = now + timedelta(hours=horizon_hours)
    
    trade = {
        # Identity
        "experiment_id": experiment_id,
        "symbol": signal["symbol"],
        "timeframe": signal["timeframe"],
        "side": signal["side"],
        
        # Entry
        "entry_price": signal["price"],
        "entry_time": now,
        
        # Features
        "features": signal.get("features", {}),
        
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
        "source": "batch7_long_pullback",
    }
    
    result = await db.shadow_trades.insert_one(trade)
    return str(result.inserted_id)


async def resolve_expired_trades(db, market_data):
    """Resolve shadow trades that reached their horizon."""
    now = datetime.now(timezone.utc)
    
    cursor = db.shadow_trades.find({
        "horizons.resolved": False,
        "horizons.target_exit_time": {"$lte": now}
    })
    
    resolved_count = 0
    
    async for trade in cursor:
        try:
            symbol = trade["symbol"]
            timeframe = trade.get("timeframe", "1H")
            entry_price = trade["entry_price"]
            side = trade["side"]
            
            # Get current price
            exit_price = market_data.get_last_price(symbol, timeframe)
            if exit_price is None:
                continue
            
            # Calculate PnL (BUY logic)
            if side == "BUY":
                pnl = (exit_price - entry_price) / entry_price
            else:
                # Should not happen, but handle it
                pnl = (entry_price - exit_price) / entry_price
            
            # Update trade
            await db.shadow_trades.update_one(
                {"_id": trade["_id"]},
                {
                    "$set": {
                        "horizons.0.resolved": True,
                        "horizons.0.exit_price": exit_price,
                        "horizons.0.pnl": pnl,
                        "horizons.0.resolved_at": now,
                    }
                }
            )
            
            resolved_count += 1
        
        except Exception as e:
            print(f"    ⚠️  Failed to resolve trade {trade['_id']}: {e}")
    
    return resolved_count


async def generate_long_signals(eligible: List[Dict[str, Any]], market_data) -> List[Dict[str, Any]]:
    """Generate BUY signals using trend pullback logic."""
    signals = []
    
    for asset in eligible:
        try:
            symbol = asset["symbol"]
            timeframe = asset["timeframe"]
            
            # Get candles
            candles = market_data.get_candles(symbol, timeframe, limit=60)
            if not candles or len(candles) < 50:
                continue
            
            # Create generator
            generator = TrendPullbackLongGenerator(symbol=symbol, timeframe=timeframe)
            generator.preload_history(candles)
            
            # Generate signal
            signal = generator.generate_signal()
            if signal:
                signals.append(signal)
        
        except Exception as e:
            print(f"      ⚠️  Error generating signal for {asset['symbol']}: {e}")
    
    return signals


async def batch7_collection_loop(
    target_trades: int = 30,
    horizon_hours: int = 4,
    cycle_interval_minutes: int = 15,
    experiment_id: str = "batch7_buy_pullback_only"
):
    """
    Batch 7 collection loop: BUY-only with trend pullback generator.
    """
    print("="*70)
    print("🔬 BATCH 7: BUY-ONLY COLLECTION (Trend Pullback Long)")
    print("="*70)
    print(f"Experiment: {experiment_id}")
    print(f"Target: {target_trades} trades")
    print(f"Horizon: {horizon_hours}h")
    print(f"Cycle interval: {cycle_interval_minutes} minutes")
    print(f"Generator: trend_pullback_long_v1")
    print(f"Mode: BUY ONLY (test new architecture)")
    print("="*70)
    print()
    
    # Setup
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client['trading_os']
    market_data = get_market_data_provider()
    
    cycle = 0
    total_created = 0
    total_resolved = 0
    
    while True:
        cycle += 1
        cycle_start = datetime.now(timezone.utc)
        
        print("─"*70)
        print(f"🔄 Cycle {cycle} - {cycle_start.strftime('%H:%M:%S')}")
        print("─"*70)
        
        try:
            # Step 1: Resolve expired trades
            print(f"[1/4] Resolving expired trades...")
            resolved_this_cycle = await resolve_expired_trades(db, market_data)
            if resolved_this_cycle > 0:
                print(f"      ✅ Resolved {resolved_this_cycle} trades")
                total_resolved += resolved_this_cycle
            
            # Step 2: Scan universe
            print(f"[2/4] Scanning universe...")
            universe = await scan_market_universe()
            eligible = [asset for asset in universe if asset.get("eligible", False)]
            print(f"      ✅ Found {len(eligible)} eligible assets")
            
            if not eligible:
                print(f"      ⚠️  No eligible assets")
                await asyncio.sleep(cycle_interval_minutes * 60)
                continue
            
            # Step 3: Generate BUY signals (trend pullback)
            print(f"[3/4] Generating BUY signals (trend pullback)...")
            signals = await generate_long_signals(eligible, market_data)
            print(f"      ✅ Generated {len(signals)} BUY signals")
            
            if not signals:
                print(f"      ⚠️  No BUY signals generated")
                await asyncio.sleep(cycle_interval_minutes * 60)
                continue
            
            # Step 4: Sample and create trades
            print(f"[4/4] Creating shadow trades...")
            
            # Sample: max 5-7 per cycle
            import random
            max_per_cycle = min(7, max(5, len(signals) // 3))
            
            if len(signals) > max_per_cycle:
                signals_to_save = random.sample(signals, k=max_per_cycle)
                print(f"      ⚠️  Limited to random {max_per_cycle}/{len(signals)} signals")
            else:
                signals_to_save = signals
            
            # Deduplicate: 1 per symbol
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
            
            # Create trades
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
                print(f"🎯 TARGET REACHED: {resolved_total} BUY trades collected!")
                print(f"{'='*70}")
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
    print(f"✅ BATCH 7 COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"Total cycles: {cycle}")
    print(f"Total BUY trades created: {total_created}")
    print(f"Total BUY trades resolved: {total_resolved}")
    print(f"\nNext: Analyze BUY viability!")
    
    client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch 7: BUY-only collection")
    parser.add_argument("--target", type=int, default=30, help="Target number of resolved BUY trades")
    parser.add_argument("--horizon", type=int, default=4, help="Trade horizon in hours")
    parser.add_argument("--interval", type=int, default=15, help="Minutes between cycles")
    parser.add_argument("--experiment", type=str, default="batch7_buy_pullback_only", help="Experiment ID")
    
    args = parser.parse_args()
    
    asyncio.run(batch7_collection_loop(
        target_trades=args.target,
        horizon_hours=args.horizon,
        cycle_interval_minutes=args.interval,
        experiment_id=args.experiment
    ))
