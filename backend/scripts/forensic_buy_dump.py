#!/usr/bin/env python3
"""
Batch 4 - Forensic BUY Analysis Dump
=====================================

Extracts ALL BUY trades with complete context for deep analysis.
"""

import sys
import json
sys.path.insert(0, '/app/backend')

from pymongo import MongoClient
from datetime import datetime


def forensic_buy_dump(experiment_id: str = "batch4_p05_validation"):
    """
    Extract ALL BUY trades with full context.
    
    No filtering, no selection - raw truth only.
    """
    client = MongoClient('mongodb://localhost:27017')
    db = client['trading_os']
    
    # Get ALL BUY trades
    buy_trades = list(db.shadow_trades.find({
        'experiment_id': experiment_id,
        'horizons.resolved': True,
        'side': {'$in': ['BUY', 'LONG']}
    }).sort('entry_time', 1))
    
    print("═"*70)
    print("🔬 FORENSIC BUY ANALYSIS - RAW DATA DUMP")
    print("═"*70)
    print(f"Total BUY trades: {len(buy_trades)}\n")
    
    if len(buy_trades) == 0:
        print("⚠️  NO BUY TRADES FOUND")
        print("\nThis means:")
        print("  - System is NOT generating BUY signals")
        print("  - Filters are TOO AGGRESSIVE")
        print("  - System is ONE-SIDED (sell-only)")
        print("\n→ CRITICAL: System is AMPUTATED, not FIXED")
        return
    
    # Prepare forensic data
    forensic_data = []
    
    for i, trade in enumerate(buy_trades, 1):
        horizon = trade['horizons'][0]
        
        forensic_record = {
            "trade_id": i,
            "symbol": trade['symbol'],
            "timeframe": trade['timeframe'],
            "side": trade['side'],
            
            # Entry
            "entry_time": trade['entry_time'].isoformat() if hasattr(trade['entry_time'], 'isoformat') else str(trade['entry_time']),
            "entry_price": trade['entry_price'],
            
            # Exit
            "exit_time": horizon.get('resolve_at', '').isoformat() if hasattr(horizon.get('resolve_at', ''), 'isoformat') else str(horizon.get('resolve_at', '')),
            "exit_price": horizon['exit_price'],
            
            # Outcome
            "pnl": horizon['pnl'],
            "pnl_pct": f"{horizon['pnl']*100:+.2f}%",
            "won": horizon['pnl'] > 0,
            
            # Signal quality
            "confidence": trade.get('features', {}).get('score', 'N/A'),
            "cluster": trade.get('features', {}).get('cluster', 'N/A'),
            "alignment": trade.get('features', {}).get('alignment', 'N/A'),
            
            # Context (for manual analysis)
            "price_change": f"{((horizon['exit_price'] - trade['entry_price']) / trade['entry_price'])*100:+.2f}%",
        }
        
        forensic_data.append(forensic_record)
    
    # Print summary table
    print("ID | Symbol     | TF  | Entry     | Exit      | PnL      | Conf  | Align")
    print("─"*70)
    for record in forensic_data:
        conf_str = record['confidence'] if isinstance(record['confidence'], str) else f"{record['confidence']:.2f}"
        print(
            f"{record['trade_id']:2d} | "
            f"{record['symbol']:10s} | "
            f"{record['timeframe']:3s} | "
            f"${record['entry_price']:8.2f} | "
            f"${record['exit_price']:8.2f} | "
            f"{record['pnl_pct']:8s} | "
            f"{conf_str:5s} | "
            f"{record['alignment']}"
        )
    
    # Statistical snapshot
    print("\n" + "─"*70)
    print("STATISTICAL SNAPSHOT")
    print("─"*70)
    
    wins = sum(1 for r in forensic_data if r['won'])
    losses = len(forensic_data) - wins
    avg_pnl = sum(r['pnl'] for r in forensic_data) / len(forensic_data)
    
    print(f"Wins:      {wins}/{len(forensic_data)}")
    print(f"Losses:    {losses}/{len(forensic_data)}")
    print(f"Winrate:   {wins/len(forensic_data)*100:.1f}%")
    print(f"Avg PnL:   {avg_pnl*100:+.2f}%")
    
    # Timeframe breakdown
    from collections import Counter
    tf_dist = Counter(r['timeframe'] for r in forensic_data)
    print(f"\nTimeframe distribution:")
    for tf, count in sorted(tf_dist.items()):
        print(f"  {tf}: {count}")
    
    # Confidence distribution
    conf_values = [r['confidence'] for r in forensic_data if r['confidence'] != 'N/A']
    if conf_values:
        print(f"\nConfidence range:")
        print(f"  Min: {min(conf_values):.3f}")
        print(f"  Max: {max(conf_values):.3f}")
        print(f"  Avg: {sum(conf_values)/len(conf_values):.3f}")
    
    # Save to JSON
    output_file = f"/tmp/forensic_buy_{experiment_id}.json"
    with open(output_file, 'w') as f:
        json.dump(forensic_data, f, indent=2)
    
    print(f"\n✅ Full data saved to: {output_file}")
    print("\n" + "═"*70)
    print("FORENSIC DATA READY FOR DEEP ANALYSIS")
    print("═"*70)
    print("\nNext: Send ALL BUY trades (JSON or table above) for forensic review")
    print("DO NOT filter, DO NOT cherry-pick - send everything")
    print("═"*70)
    
    return forensic_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default="batch4_p05_validation")
    args = parser.parse_args()
    
    forensic_buy_dump(args.experiment)
