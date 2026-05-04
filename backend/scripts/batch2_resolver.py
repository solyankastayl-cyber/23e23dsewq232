#!/usr/bin/env python3
"""
Batch 2 Manual Resolver
========================

Manually resolve expired shadow trades (for when collection loop stops).
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from modules.scanner.market_data.binance_provider import get_market_data_provider


async def resolve_expired_trades(experiment_id: str = "batch2_4h"):
    """
    Resolve shadow trades that reached their horizon.
    
    Uses current market price to calculate PnL.
    """
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    market_data = get_market_data_provider()
    
    now = datetime.now(timezone.utc)
    
    print(f"\n{'='*70}")
    print(f"🔄 RESOLVING EXPIRED TRADES")
    print(f"{'='*70}")
    print(f"Experiment: {experiment_id}")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*70}\n")
    
    # Find unresolved trades past their exit time
    cursor = db.shadow_trades.find({
        "experiment_id": experiment_id,
        "horizons.resolved": False,
        "horizons.target_exit_time": {"$lte": now}
    })
    
    resolved_count = 0
    failed_count = 0
    
    async for trade in cursor:
        symbol = trade["symbol"]
        timeframe = trade["timeframe"]
        
        # Get current price
        exit_price = market_data.get_last_price(symbol, timeframe)
        
        if exit_price is None:
            print(f"❌ Could not get price for {symbol} {timeframe}")
            failed_count += 1
            continue
        
        # Calculate PnL
        entry_price = trade["entry_price"]
        side = trade["side"]
        
        if side == "BUY" or side == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SHORT/SELL
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
        print(f"✅ {symbol:10s} {timeframe:3s} {side:4s} entry=${entry_price:.2f} exit=${exit_price:.2f} pnl={pnl_pct:+.2%}")
    
    print(f"\n{'='*70}")
    print(f"✅ RESOLUTION COMPLETE")
    print(f"{'='*70}")
    print(f"Resolved: {resolved_count}")
    print(f"Failed:   {failed_count}")
    print(f"{'='*70}\n")
    
    # Status
    total = await db.shadow_trades.count_documents({"experiment_id": experiment_id})
    resolved_total = await db.shadow_trades.count_documents({
        "experiment_id": experiment_id,
        "horizons.resolved": True
    })
    
    print(f"📊 Status:")
    print(f"   Total:    {total}")
    print(f"   Resolved: {resolved_total}")
    print(f"   Pending:  {total - resolved_total}")
    print(f"   Progress: {resolved_total}/35 ({resolved_total/35*100:.0f}%)")
    
    return resolved_count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manually resolve expired shadow trades")
    parser.add_argument("--experiment", default="batch2_4h", help="Experiment ID")
    
    args = parser.parse_args()
    
    asyncio.run(resolve_expired_trades(args.experiment))
