#!/usr/bin/env python3
"""
Manual Resolver для Batch 6
============================

Цель: Зарезолвить 43 pending trades, получить ПЕРВЫЕ реальные данные.

НЕ для продакшн.
Для ИЗВЛЕЧЕНИЯ ПРАВДЫ из Batch 6.
"""

import sys
sys.path.insert(0, '/app/backend')

import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
import os

# Market data
from modules.scanner.market_data.binance_provider import get_market_data_provider


async def manual_resolve_batch6():
    """Зарезолвить все pending trades из Batch 6."""
    
    print("="*70)
    print("MANUAL RESOLVER — BATCH 6")
    print("="*70)
    
    # Setup
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = MongoClient(mongo_url)
    db = client['trading_os']
    
    market_data = get_market_data_provider()
    
    # Find all pending trades
    pending = list(db.shadow_trades.find({
        'experiment_id': 'batch6_short_only',
        'horizons.resolved': False
    }))
    
    total_pending = len(pending)
    print(f"\n📊 Found {total_pending} pending trades")
    
    if total_pending == 0:
        print("✅ No pending trades to resolve")
        return
    
    now = datetime.now(timezone.utc)
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Resolve each trade
    resolved_count = 0
    failed_count = 0
    
    print(f"\n🔄 Resolving trades...\n")
    
    for i, trade in enumerate(pending, 1):
        trade_id = trade['_id']
        symbol = trade['symbol']
        timeframe = trade['timeframe']
        side = trade['side']
        entry_price = trade['entry_price']
        entry_time = trade.get('entry_time')
        
        # Get current price
        try:
            exit_price = market_data.get_last_price(symbol, timeframe)
            
            if exit_price is None:
                print(f"[{i}/{total_pending}] ⚠️  {symbol} {timeframe} — No price available")
                failed_count += 1
                continue
            
            # Calculate PnL (SHORT logic)
            if side == "SELL" or side == "SHORT":
                pnl = (entry_price - exit_price) / entry_price
            else:
                # Should not happen (BUY freeze), but handle it
                pnl = (exit_price - entry_price) / entry_price
            
            # Update trade
            db.shadow_trades.update_one(
                {'_id': trade_id},
                {
                    '$set': {
                        'horizons.0.resolved': True,
                        'horizons.0.exit_price': exit_price,
                        'horizons.0.pnl': pnl,
                        'horizons.0.resolved_at': now,
                        'horizons.0.resolution_method': 'manual'
                    }
                }
            )
            
            status = "WIN" if pnl > 0 else "LOSS"
            print(f"[{i}/{total_pending}] ✅ {symbol:8s} {timeframe:3s} {side:4s} | "
                  f"${entry_price:.2f}→${exit_price:.2f} | {pnl*100:+.2f}% {status}")
            
            resolved_count += 1
            
        except Exception as e:
            print(f"[{i}/{total_pending}] ❌ {symbol} {timeframe} — Error: {e}")
            failed_count += 1
    
    print(f"\n{'='*70}")
    print(f"RESOLUTION COMPLETE")
    print(f"{'='*70}")
    print(f"Total pending: {total_pending}")
    print(f"Resolved: {resolved_count}")
    print(f"Failed: {failed_count}")
    
    # Summary stats
    if resolved_count > 0:
        resolved_trades = list(db.shadow_trades.find({
            'experiment_id': 'batch6_short_only',
            'horizons.resolved': True
        }))
        
        wins = sum(1 for t in resolved_trades if t['horizons'][0]['pnl'] > 0)
        losses = len(resolved_trades) - wins
        winrate = (wins / len(resolved_trades) * 100) if resolved_trades else 0
        
        pnls = [t['horizons'][0]['pnl'] for t in resolved_trades]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        
        print(f"\n📊 IMMEDIATE STATS")
        print(f"Winrate: {wins}/{len(resolved_trades)} = {winrate:.1f}%")
        print(f"Avg PnL: {avg_pnl*100:.2f}%")
        print(f"Best: {max(pnls)*100:.2f}%")
        print(f"Worst: {min(pnls)*100:.2f}%")
    
    client.close()
    print(f"\n✅ Resolution complete. Run analysis script for full report.")


if __name__ == "__main__":
    asyncio.run(manual_resolve_batch6())
