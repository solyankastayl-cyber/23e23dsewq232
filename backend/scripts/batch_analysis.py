#!/usr/bin/env python3
"""
Batch Analysis Tools
====================

Tools for analyzing shadow trade batches and preparing data for quant review.
"""

import sys
sys.path.insert(0, '/app/backend')

from pymongo import MongoClient
from datetime import datetime, timezone
import json
from collections import Counter


def get_batch_raw_dump(experiment_id: str = "market_dynamic", output_file: str = None):
    """
    Export raw resolved shadow trades from batch.
    
    Args:
        experiment_id: Experiment to export
        output_file: Optional file path to save (default: stdout)
    
    Returns:
        List of raw trades
    """
    client = MongoClient("mongodb://localhost:27017")
    db = client["trading_os"]
    
    # Get all resolved trades
    cursor = db.shadow_trades.find({
        "experiment_id": experiment_id,
        "horizons.resolved": True
    })
    
    trades = []
    for trade in cursor:
        trade.pop('_id', None)  # Remove MongoDB ID
        trades.append(trade)
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(trades, f, indent=2, default=str)
        print(f"✅ Exported {len(trades)} trades to {output_file}")
    
    return trades


def analyze_concentration(experiment_id: str = "market_dynamic"):
    """
    Analyze data concentration to detect single-regime bias.
    
    Checks:
    - Symbol concentration
    - Cluster concentration
    - Timeframe concentration
    - Side concentration
    """
    client = MongoClient("mongodb://localhost:27017")
    db = client["trading_os"]
    
    # Get all resolved trades
    cursor = db.shadow_trades.find({
        "experiment_id": experiment_id,
        "horizons.resolved": True
    })
    
    symbols = []
    clusters = []
    timeframes = []
    sides = []
    
    for trade in cursor:
        symbols.append(trade.get("symbol"))
        clusters.append(trade.get("features", {}).get("cluster"))
        timeframes.append(trade.get("timeframe"))
        sides.append(trade.get("side"))
    
    total = len(symbols)
    
    print(f"\n{'='*70}")
    print(f"📊 CONCENTRATION ANALYSIS")
    print(f"{'='*70}")
    print(f"Total trades: {total}\n")
    
    # Symbol concentration
    print(f"By Symbol:")
    symbol_counts = Counter(symbols)
    for symbol, count in symbol_counts.most_common():
        pct = count / total * 100
        print(f"  {symbol:10s} {count:3d} ({pct:5.1f}%)")
    
    # Cluster concentration
    print(f"\nBy Cluster:")
    cluster_counts = Counter(clusters)
    for cluster, count in cluster_counts.most_common():
        pct = count / total * 100
        print(f"  {cluster:10s} {count:3d} ({pct:5.1f}%)")
    
    # Timeframe concentration
    print(f"\nBy Timeframe:")
    tf_counts = Counter(timeframes)
    for tf, count in tf_counts.most_common():
        pct = count / total * 100
        print(f"  {tf:10s} {count:3d} ({pct:5.1f}%)")
    
    # Side concentration
    print(f"\nBy Side:")
    side_counts = Counter(sides)
    for side, count in side_counts.most_common():
        pct = count / total * 100
        print(f"  {side:10s} {count:3d} ({pct:5.1f}%)")
    
    # Warnings
    print(f"\n{'─'*70}")
    print(f"⚠️  CONCENTRATION WARNINGS:")
    
    # Check for extreme concentration
    if symbol_counts.most_common(1)[0][1] / total > 0.5:
        print(f"  ⚠️  Single symbol dominance: {symbol_counts.most_common(1)[0][0]} ({symbol_counts.most_common(1)[0][1]/total*100:.0f}%)")
    
    if cluster_counts.most_common(1)[0][1] / total > 0.7:
        print(f"  ⚠️  Cluster imbalance: {cluster_counts.most_common(1)[0][0]} ({cluster_counts.most_common(1)[0][1]/total*100:.0f}%)")
    
    if tf_counts.most_common(1)[0][1] / total > 0.6:
        print(f"  ⚠️  Timeframe concentration: {tf_counts.most_common(1)[0][0]} ({tf_counts.most_common(1)[0][1]/total*100:.0f}%)")
    
    if len(side_counts) == 1:
        print(f"  ⚠️  Only one side: {list(side_counts.keys())[0]}")
    
    print(f"{'='*70}\n")
    
    return {
        "symbols": dict(symbol_counts),
        "clusters": dict(cluster_counts),
        "timeframes": dict(tf_counts),
        "sides": dict(side_counts),
    }


def generate_batch_summary(experiment_id: str = "market_dynamic", batch_name: str = "Batch 1"):
    """
    Generate structured summary for quant review.
    
    Template format:
    - Total resolved trades
    - Unique symbols
    - Distribution counts
    - Worst/best segments
    - Outliers
    - BATCH 2 ADDITIONS: score buckets, side breakdown, time spread
    """
    client = MongoClient("mongodb://localhost:27017")
    db = client["trading_os"]
    
    # Get all resolved trades
    cursor = db.shadow_trades.find({
        "experiment_id": experiment_id,
        "horizons.resolved": True
    })
    
    trades = list(cursor)
    total = len(trades)
    
    # Get ALL trades (including pending) for time spread
    all_cursor = db.shadow_trades.find({
        "experiment_id": experiment_id
    })
    all_trades = list(all_cursor)
    
    if total == 0:
        print("❌ No resolved trades found")
        return
    
    # Extract data
    symbols = set(t.get("symbol") for t in trades)
    clusters = [t.get("features", {}).get("cluster") for t in trades]
    timeframes = [t.get("timeframe") for t in trades]
    sides = [t.get("side") for t in trades]
    
    # Calculate performance by segment
    def calc_perf(trades_subset):
        if not trades_subset:
            return {"winrate": 0, "avg_pnl": 0, "count": 0}
        wins = sum(1 for t in trades_subset if t.get("horizons", [{}])[0].get("pnl", 0) > 0)
        pnls = [t.get("horizons", [{}])[0].get("pnl", 0) for t in trades_subset]
        return {
            "winrate": wins / len(trades_subset),
            "avg_pnl": sum(pnls) / len(pnls),
            "count": len(trades_subset)
        }
    
    # By cluster
    cluster_perf = {}
    for cluster in set(clusters):
        subset = [t for t in trades if t.get("features", {}).get("cluster") == cluster]
        cluster_perf[cluster] = calc_perf(subset)
    
    # By timeframe
    tf_perf = {}
    for tf in set(timeframes):
        subset = [t for t in trades if t.get("timeframe") == tf]
        tf_perf[tf] = calc_perf(subset)
    
    # By side
    side_perf = {}
    for side in set(sides):
        subset = [t for t in trades if t.get("side") == side]
        side_perf[side] = calc_perf(subset)
    
    # Find worst/best
    worst_cluster = min(cluster_perf.items(), key=lambda x: x[1]["winrate"])[0] if cluster_perf else "N/A"
    worst_tf = min(tf_perf.items(), key=lambda x: x[1]["winrate"])[0] if tf_perf else "N/A"
    best_candidate = max(tf_perf.items(), key=lambda x: x[1]["winrate"])[0] if tf_perf else "N/A"
    
    # Detect outliers
    pnls = [t.get("horizons", [{}])[0].get("pnl", 0) for t in trades]
    avg_pnl = sum(pnls) / len(pnls)
    std_pnl = (sum((p - avg_pnl)**2 for p in pnls) / len(pnls)) ** 0.5
    outliers = [t for t in trades if abs(t.get("horizons", [{}])[0].get("pnl", 0) - avg_pnl) > 2 * std_pnl]
    
    # Generate summary
    print(f"\n{'='*70}")
    print(f"📊 {batch_name.upper()} SUMMARY")
    print(f"{'='*70}\n")
    
    print(f"Total resolved trades: {total}")
    print(f"Unique symbols: {len(symbols)} ({', '.join(sorted(symbols))})")
    
    print(f"\nBy cluster counts:")
    for cluster, count in Counter(clusters).most_common():
        print(f"  {cluster:10s} {count:3d} ({count/total*100:5.1f}%)")
    
    print(f"\nBy timeframe counts:")
    for tf, count in Counter(timeframes).most_common():
        print(f"  {tf:10s} {count:3d} ({count/total*100:5.1f}%)")
    
    print(f"\nBy side counts:")
    for side, count in Counter(sides).most_common():
        print(f"  {side:10s} {count:3d} ({count/total*100:5.1f}%)")
    
    # BATCH 2 ADDITION: Score buckets
    print(f"\n{'─'*70}")
    print(f"By Score Buckets (BATCH 2):")
    print(f"{'─'*70}")
    
    score_buckets = {
        "0.5-0.6": [],
        "0.6-0.7": [],
        "0.7-0.8": [],
        "0.8-0.9": [],
        "0.9-1.0": []
    }
    
    for t in trades:
        score = t.get("features", {}).get("score", 0.5)
        if 0.5 <= score < 0.6:
            score_buckets["0.5-0.6"].append(t)
        elif 0.6 <= score < 0.7:
            score_buckets["0.6-0.7"].append(t)
        elif 0.7 <= score < 0.8:
            score_buckets["0.7-0.8"].append(t)
        elif 0.8 <= score < 0.9:
            score_buckets["0.8-0.9"].append(t)
        elif 0.9 <= score <= 1.0:
            score_buckets["0.9-1.0"].append(t)
    
    for bucket, bucket_trades in score_buckets.items():
        if not bucket_trades:
            print(f"  {bucket}: n=0")
            continue
        perf = calc_perf(bucket_trades)
        print(f"  {bucket}: n={perf['count']:2d}, wr={perf['winrate']:5.1%}, pnl={perf['avg_pnl']:+6.2%}")
    
    # BATCH 2 ADDITION: Side breakdown
    print(f"\n{'─'*70}")
    print(f"Side Breakdown (BATCH 2):")
    print(f"{'─'*70}")
    
    for side in sorted(side_perf.keys()):
        perf = side_perf[side]
        print(f"{side}:")
        print(f"  winrate: {perf['winrate']:5.1%}")
        print(f"  pnl:     {perf['avg_pnl']:+6.2%}")
        print(f"  count:   {perf['count']}")
    
    # BATCH 2 ADDITION: Time spread
    print(f"\n{'─'*70}")
    print(f"Time Spread (BATCH 2):")
    print(f"{'─'*70}")
    
    if all_trades:
        entry_times = [t.get("entry_time") for t in all_trades if t.get("entry_time")]
        if entry_times:
            start_time = min(entry_times)
            end_time = max(entry_times)
            duration = end_time - start_time
            
            print(f"start_time: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"end_time:   {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"duration:   {duration.total_seconds() / 3600:.1f} hours")
        else:
            print(f"⚠️  No entry_time data available")
    else:
        print(f"⚠️  No trades found")
    
    print(f"\n{'─'*70}")
    print(f"Key Findings:")
    print(f"{'─'*70}")
    print(f"Worst cluster: {worst_cluster} (wr={cluster_perf[worst_cluster]['winrate']:.1%}, pnl={cluster_perf[worst_cluster]['avg_pnl']:.3%}, n={cluster_perf[worst_cluster]['count']})")
    print(f"Worst timeframe: {worst_tf} (wr={tf_perf[worst_tf]['winrate']:.1%}, pnl={tf_perf[worst_tf]['avg_pnl']:.3%}, n={tf_perf[worst_tf]['count']})")
    print(f"Best candidate: {best_candidate} (wr={tf_perf[best_candidate]['winrate']:.1%}, pnl={tf_perf[best_candidate]['avg_pnl']:.3%}, n={tf_perf[best_candidate]['count']})")
    
    if len(outliers) > 0:
        print(f"\nSuspicious segment: {len(outliers)} outliers detected (>2σ from mean)")
        for outlier in outliers[:3]:
            pnl = outlier.get("horizons", [{}])[0].get("pnl", 0)
            print(f"  {outlier['symbol']} {outlier['timeframe']} {outlier['side']}: {pnl:+.2%}")
    else:
        print(f"\nSuspicious segment: None (no significant outliers)")
    
    print(f"\nNotes on outliers:")
    if len(outliers) > total * 0.1:
        print(f"  ⚠️  High outlier rate ({len(outliers)/total*100:.0f}%) - check data quality")
    else:
        print(f"  ✅ Normal outlier rate ({len(outliers)/total*100:.0f}%)")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze shadow trade batch")
    parser.add_argument("--action", choices=["dump", "concentration", "summary", "all"], default="all")
    parser.add_argument("--experiment", default="market_dynamic")
    parser.add_argument("--output", help="Output file for raw dump")
    
    args = parser.parse_args()
    
    if args.action in ["dump", "all"]:
        print("\n🔍 Generating raw dump...")
        output = args.output or f"batch1_raw_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        get_batch_raw_dump(args.experiment, output)
    
    if args.action in ["concentration", "all"]:
        print("\n🔍 Analyzing concentration...")
        analyze_concentration(args.experiment)
    
    if args.action in ["summary", "all"]:
        print("\n🔍 Generating summary...")
        generate_batch_summary(args.experiment)
