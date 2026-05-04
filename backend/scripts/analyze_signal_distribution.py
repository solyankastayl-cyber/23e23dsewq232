#!/usr/bin/env python3
"""
Exchange Signal Distribution Analysis
======================================
Analyzes signal distribution across BTC, ETH, SOL to prepare for Conflict Resolver.

Usage:
    python scripts/analyze_signal_distribution.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

SYMBOLS = ["BTC", "ETH", "SOL"]


def get_db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def analyze_funding_distribution(db):
    """Analyze funding rate distribution."""
    print("\n" + "=" * 60)
    print("FUNDING RATE DISTRIBUTION")
    print("=" * 60)
    
    for symbol in SYMBOLS:
        data = list(db.exchange_funding_context.find(
            {"symbol": symbol},
            {"_id": 0, "funding_rate": 1}
        ).limit(720))
        
        if not data:
            print(f"\n{symbol}: No data")
            continue
        
        rates = [d["funding_rate"] for d in data]
        
        # Classify
        extreme_long = sum(1 for r in rates if r > 0.0005)  # >0.05%
        crowded_long = sum(1 for r in rates if 0.0002 < r <= 0.0005)
        neutral = sum(1 for r in rates if -0.0002 <= r <= 0.0002)
        crowded_short = sum(1 for r in rates if -0.0005 <= r < -0.0002)
        extreme_short = sum(1 for r in rates if r < -0.0005)
        
        total = len(rates)
        
        print(f"\n{symbol}:")
        print(f"  Extreme Long:  {extreme_long:4d} ({extreme_long/total*100:5.1f}%)")
        print(f"  Crowded Long:  {crowded_long:4d} ({crowded_long/total*100:5.1f}%)")
        print(f"  Neutral:       {neutral:4d} ({neutral/total*100:5.1f}%)")
        print(f"  Crowded Short: {crowded_short:4d} ({crowded_short/total*100:5.1f}%)")
        print(f"  Extreme Short: {extreme_short:4d} ({extreme_short/total*100:5.1f}%)")
        print(f"  Avg Rate:      {sum(rates)/len(rates)*100:.4f}%")


def analyze_liquidation_distribution(db):
    """Analyze liquidation distribution."""
    print("\n" + "=" * 60)
    print("LIQUIDATION DISTRIBUTION")
    print("=" * 60)
    
    for symbol in SYMBOLS:
        data = list(db.exchange_liquidation_events.find(
            {"symbol": symbol},
            {"_id": 0, "side": 1, "size": 1}
        ))
        
        if not data:
            print(f"\n{symbol}: No data")
            continue
        
        long_liqs = [d for d in data if d.get("side") == "LONG"]
        short_liqs = [d for d in data if d.get("side") == "SHORT"]
        
        long_vol = sum(d.get("size", 0) for d in long_liqs)
        short_vol = sum(d.get("size", 0) for d in short_liqs)
        total_vol = long_vol + short_vol
        
        print(f"\n{symbol}:")
        print(f"  Total Events:  {len(data):,}")
        print(f"  Long Liqs:     {len(long_liqs):,} ({len(long_liqs)/len(data)*100:.1f}%)")
        print(f"  Short Liqs:    {len(short_liqs):,} ({len(short_liqs)/len(data)*100:.1f}%)")
        print(f"  Long Volume:   ${long_vol:,.0f} ({long_vol/total_vol*100:.1f}%)")
        print(f"  Short Volume:  ${short_vol:,.0f} ({short_vol/total_vol*100:.1f}%)")


def analyze_flow_distribution(db):
    """Analyze order flow distribution."""
    print("\n" + "=" * 60)
    print("ORDER FLOW DISTRIBUTION")
    print("=" * 60)
    
    for symbol in SYMBOLS:
        data = list(db.exchange_trade_flows.find(
            {"symbol": symbol},
            {"_id": 0, "taker_buy_ratio": 1, "total_volume": 1}
        ).limit(720))
        
        if not data:
            print(f"\n{symbol}: No data")
            continue
        
        ratios = [d.get("taker_buy_ratio", 0.5) for d in data]
        
        # Classify
        aggressive_buy = sum(1 for r in ratios if r > 0.6)
        slight_buy = sum(1 for r in ratios if 0.52 < r <= 0.6)
        neutral = sum(1 for r in ratios if 0.48 <= r <= 0.52)
        slight_sell = sum(1 for r in ratios if 0.4 <= r < 0.48)
        aggressive_sell = sum(1 for r in ratios if r < 0.4)
        
        total = len(ratios)
        avg_ratio = sum(ratios) / len(ratios)
        
        print(f"\n{symbol}:")
        print(f"  Aggressive Buy:  {aggressive_buy:4d} ({aggressive_buy/total*100:5.1f}%)")
        print(f"  Slight Buy:      {slight_buy:4d} ({slight_buy/total*100:5.1f}%)")
        print(f"  Neutral:         {neutral:4d} ({neutral/total*100:5.1f}%)")
        print(f"  Slight Sell:     {slight_sell:4d} ({slight_sell/total*100:5.1f}%)")
        print(f"  Aggressive Sell: {aggressive_sell:4d} ({aggressive_sell/total*100:5.1f}%)")
        print(f"  Avg Buy Ratio:   {avg_ratio:.3f}")


def analyze_derivatives_distribution(db):
    """Analyze derivatives positioning."""
    print("\n" + "=" * 60)
    print("DERIVATIVES POSITIONING")
    print("=" * 60)
    
    for symbol in SYMBOLS:
        snapshot = db.exchange_symbol_snapshots.find_one(
            {"symbol": symbol},
            {"_id": 0}
        )
        
        if not snapshot:
            print(f"\n{symbol}: No snapshot")
            continue
        
        ls_ratio = snapshot.get("long_short_ratio", 1.0)
        leverage = snapshot.get("leverage_index", 0.5)
        premium = snapshot.get("perp_premium", 0.0)
        
        # Interpret
        if ls_ratio > 1.5:
            ls_state = "EXTREME_LONG"
        elif ls_ratio > 1.2:
            ls_state = "LONG_BIAS"
        elif ls_ratio < 0.67:
            ls_state = "EXTREME_SHORT"
        elif ls_ratio < 0.8:
            ls_state = "SHORT_BIAS"
        else:
            ls_state = "BALANCED"
        
        print(f"\n{symbol}:")
        print(f"  L/S Ratio:       {ls_ratio:.3f} ({ls_state})")
        print(f"  Leverage Index:  {leverage:.3f}")
        print(f"  Perp Premium:    {premium*100:.4f}%")


def compute_dominant_signals(db):
    """Determine which signal dominates for each symbol."""
    print("\n" + "=" * 60)
    print("DOMINANT SIGNAL ANALYSIS (for Conflict Resolver)")
    print("=" * 60)
    
    # Import engines
    sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))
    from exchange_intelligence.exchange_context_aggregator import ExchangeContextAggregator
    from exchange_intelligence.exchange_intel_repository import ExchangeIntelRepository
    
    repo = ExchangeIntelRepository()
    aggregator = ExchangeContextAggregator(repo)
    
    for symbol in SYMBOLS:
        ctx = aggregator.compute(symbol)
        
        # Score each signal
        scores = {
            "funding": abs(ctx.funding_signal.funding_annualized) / 0.05 if ctx.funding_signal else 0,
            "derivatives": abs(ctx.derivatives_pressure),
            "liquidation": ctx.cascade_probability,
            "flow": abs(ctx.flow_pressure),
            "volume": ctx.volume_signal.anomaly_score if ctx.volume_signal else 0,
        }
        
        # Find dominant
        dominant = max(scores, key=scores.get)
        dominant_score = scores[dominant]
        
        print(f"\n{symbol}:")
        for sig, score in sorted(scores.items(), key=lambda x: -x[1]):
            marker = "◄ DOMINANT" if sig == dominant else ""
            print(f"  {sig:12s}: {score:.3f} {marker}")
        
        print(f"\n  → Resolver should prioritize: {dominant.upper()}")


def main():
    print("=" * 60)
    print("EXCHANGE SIGNAL DISTRIBUTION ANALYSIS")
    print("Preparing for Phase 13.9 Conflict Resolver")
    print("=" * 60)
    
    db = get_db()
    
    analyze_funding_distribution(db)
    analyze_liquidation_distribution(db)
    analyze_flow_distribution(db)
    analyze_derivatives_distribution(db)
    compute_dominant_signals(db)
    
    print("\n" + "=" * 60)
    print("SUMMARY FOR CONFLICT RESOLVER")
    print("=" * 60)
    print("""
Key observations for resolver weights:

1. LIQUIDATION tends to have highest impact during volatility
   → Should dominate when cascade_probability > 0.5

2. FUNDING shows extreme states frequently
   → Should dominate when funding is extreme AND oi_expanding

3. FLOW is most balanced signal
   → Good baseline, should be default dominant

4. DERIVATIVES varies significantly by symbol
   → Context-dependent weighting needed

Recommended resolver logic:
  if liquidation.cascade_prob > 0.6: liquidation dominates
  elif funding.extreme AND derivatives.squeeze > 0.5: derivatives dominates
  elif flow.intensity > 0.3: flow dominates
  else: blended signal
""")


if __name__ == "__main__":
    main()
