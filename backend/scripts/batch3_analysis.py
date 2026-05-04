#!/usr/bin/env python3
"""
Batch 3 Analysis - With Input Distribution
===========================================

Analyzes Batch 3 WITH signal generation distribution (not just results).
"""

import sys
sys.path.insert(0, '/app/backend')

from pymongo import MongoClient
from collections import Counter


def analyze_batch3(experiment_id: str = "batch3_with_trend_filter"):
    """
    Analyze Batch 3 with focus on:
    1. Signal counts (BUY vs SELL)
    2. Side performance
    3. Reject rate (from logs)
    4. Timeframe breakdown
    """
    client = MongoClient('mongodb://localhost:27017')
    db = client['trading_os']
    
    # Get resolved trades
    trades = list(db.shadow_trades.find({
        'experiment_id': experiment_id,
        'horizons.resolved': True
    }))
    
    total = len(trades)
    
    if total == 0:
        print("❌ No resolved trades yet")
        return
    
    print("═"*70)
    print(f"BATCH 3 ANALYSIS - {experiment_id}")
    print("═"*70)
    print(f"Total resolved: {total}\n")
    
    # 1. SIGNAL COUNTS
    print("─"*70)
    print("1️⃣ SIGNAL GENERATION DISTRIBUTION")
    print("─"*70)
    
    buy_trades = [t for t in trades if t.get('side') in ['BUY', 'LONG']]
    sell_trades = [t for t in trades if t.get('side') in ['SELL', 'SHORT']]
    
    buy_count = len(buy_trades)
    sell_count = len(sell_trades)
    
    print(f"BUY signals:  {buy_count:3d} ({buy_count/total*100:5.1f}%)")
    print(f"SELL signals: {sell_count:3d} ({sell_count/total*100:5.1f}%)")
    print(f"Total:        {total:3d}")
    
    if buy_count == 0:
        print("\n🔴 WARNING: NO BUY signals generated!")
        print("   → Trend filter TOO STRICT or wrong logic")
    elif buy_count < 5:
        print(f"\n⚠️  WARNING: Very few BUY signals ({buy_count})")
        print("   → May need more data for valid analysis")
    
    # 2. SIDE PERFORMANCE
    print("\n" + "─"*70)
    print("2️⃣ SIDE PERFORMANCE")
    print("─"*70)
    
    def calc_perf(trades_list):
        if not trades_list:
            return {'count': 0, 'wins': 0, 'winrate': 0, 'avg_pnl': 0, 'total_pnl': 0}
        pnls = [t['horizons'][0]['pnl'] for t in trades_list]
        wins = sum(1 for p in pnls if p > 0)
        return {
            'count': len(trades_list),
            'wins': wins,
            'winrate': wins / len(trades_list),
            'avg_pnl': sum(pnls) / len(pnls),
            'total_pnl': sum(pnls)
        }
    
    buy_perf = calc_perf(buy_trades)
    sell_perf = calc_perf(sell_trades)
    
    print(f"\nBUY:")
    print(f"  Count:     {buy_perf['count']}")
    print(f"  Wins:      {buy_perf['wins']}")
    print(f"  Winrate:   {buy_perf['winrate']*100:5.1f}%")
    print(f"  Avg PnL:   {buy_perf['avg_pnl']*100:+6.2f}%")
    print(f"  Total PnL: {buy_perf['total_pnl']*100:+6.2f}%")
    
    print(f"\nSELL:")
    print(f"  Count:     {sell_perf['count']}")
    print(f"  Wins:      {sell_perf['wins']}")
    print(f"  Winrate:   {sell_perf['winrate']*100:5.1f}%")
    print(f"  Avg PnL:   {sell_perf['avg_pnl']*100:+6.2f}%")
    print(f"  Total PnL: {sell_perf['total_pnl']*100:+6.2f}%")
    
    # 3. VERDICT
    print("\n" + "─"*70)
    print("3️⃣ FIX VALIDATION")
    print("─"*70)
    
    print(f"\nBatch 2 Reference:")
    print(f"  BUY:  0.0% winrate (0/29) ← BROKEN")
    print(f"  SELL: 98.3% winrate (59/60)")
    
    print(f"\nBatch 3 Results:")
    print(f"  BUY:  {buy_perf['winrate']*100:.1f}% winrate ({buy_perf['wins']}/{buy_perf['count']})")
    print(f"  SELL: {sell_perf['winrate']*100:.1f}% winrate ({sell_perf['wins']}/{sell_perf['count']})")
    
    print(f"\n{'─'*70}")
    print("VERDICT:")
    print("─"*70)
    
    # Success criteria
    if buy_count == 0:
        print("❌ FAIL: No BUY signals (trend filter too strict)")
    elif buy_perf['winrate'] == 0:
        print("❌ FAIL: BUY still 0% winrate (P0 insufficient → need P1)")
    elif buy_perf['winrate'] < 0.25:
        print(f"⚠️  MARGINAL: BUY {buy_perf['winrate']*100:.0f}% < 25% threshold")
        print("   → P0 helped but not enough → implement P1")
    elif buy_perf['winrate'] < 0.35:
        print(f"✅ MINIMUM SUCCESS: BUY {buy_perf['winrate']*100:.0f}% > 25%")
        print("   → P0 fixed structural issue")
        print("   → Consider P1 for improvement")
    else:
        print(f"✅ GOOD SUCCESS: BUY {buy_perf['winrate']*100:.0f}% > 35%")
        print("   → Trend filter working well")
        print("   → Ready for P1 asymmetry if needed")
    
    # Check SELL stability
    if sell_perf['count'] > 0:
        if sell_perf['winrate'] < 0.50:
            print(f"\n⚠️  WARNING: SELL dropped to {sell_perf['winrate']*100:.0f}%")
            print("   → Trend filter may be too strict")
        else:
            print(f"\n✅ SELL stable: {sell_perf['winrate']*100:.0f}% winrate")
    
    # Overall
    overall_pnl = buy_perf['total_pnl'] + sell_perf['total_pnl']
    overall_winrate = (buy_perf['wins'] + sell_perf['wins']) / total
    
    print(f"\n📊 Overall:")
    print(f"   Winrate: {overall_winrate*100:.1f}%")
    print(f"   Total PnL: {overall_pnl*100:+.2f}%")
    print(f"   Avg PnL: {(overall_pnl/total)*100:+.2f}%")
    
    # 4. TIMEFRAME BREAKDOWN
    print("\n" + "─"*70)
    print("4️⃣ TIMEFRAME BREAKDOWN")
    print("─"*70)
    
    for tf in ['1H', '4H', '1D']:
        tf_trades = [t for t in trades if t.get('timeframe') == tf]
        if tf_trades:
            perf = calc_perf(tf_trades)
            print(f"\n{tf}:")
            print(f"  Count: {perf['count']:2d}")
            print(f"  WR:    {perf['winrate']*100:5.1f}%")
            print(f"  Avg:   {perf['avg_pnl']*100:+6.2f}%")
    
    print("\n" + "═"*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default="batch3_with_trend_filter")
    args = parser.parse_args()
    
    analyze_batch3(args.experiment)
