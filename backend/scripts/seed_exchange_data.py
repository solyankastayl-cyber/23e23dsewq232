#!/usr/bin/env python3
"""
PHASE 13.8.B — Exchange Native Data Seeder
============================================
Seeds realistic exchange data into MongoDB collections for native binding.

Collections created:
- exchange_funding_context: Funding rates from TS FundingService
- exchange_oi_snapshots: Open interest snapshots
- exchange_liquidation_events: Liquidation events
- exchange_trade_flows: Order flow data
- exchange_symbol_snapshots: Derivatives market snapshots

Usage:
    python scripts/seed_exchange_data.py           # Seed all
    python scripts/seed_exchange_data.py --status  # Check status
    python scripts/seed_exchange_data.py --reset   # Reset and reseed
"""

import os
import sys
import random
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient, DESCENDING

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

# Symbols to seed
SYMBOLS = ["BTC", "ETH", "SOL"]

# Time range (last 30 days)
DAYS_BACK = 30
HOURS_INTERVAL = 1  # hourly data


def get_db():
    """Get MongoDB database."""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def generate_funding_data(symbol: str, candles: List[Dict]) -> List[Dict]:
    """
    Generate realistic funding rate data based on price action.
    Positive funding = longs pay shorts (bullish sentiment)
    Negative funding = shorts pay longs (bearish sentiment)
    """
    if not candles:
        return []
    
    data = []
    now = datetime.now(timezone.utc)
    
    # Use last 720 hours (30 days)
    for i, candle in enumerate(candles[-720:]):
        # Price momentum affects funding
        if i > 0:
            prev_close = candles[i-1].get("close", candle["close"])
            price_change = (candle["close"] - prev_close) / max(prev_close, 1e-8)
        else:
            price_change = 0
        
        # Base funding rate (8h rate, typically 0.01% = 0.0001)
        base_rate = 0.0001
        
        # Sentiment component from price action
        sentiment_component = price_change * 10  # Amplify
        
        # Random noise
        noise = random.uniform(-0.00015, 0.00015)
        
        funding_rate = base_rate + sentiment_component + noise
        funding_rate = max(min(funding_rate, 0.003), -0.003)  # Cap at 0.3%
        
        # Calculate next funding time (every 8 hours)
        hours_since_start = i * HOURS_INTERVAL
        timestamp = now - timedelta(hours=720 - hours_since_start)
        
        data.append({
            "symbol": symbol,
            "funding_rate": round(funding_rate, 8),
            "next_funding_time": (timestamp + timedelta(hours=8)).isoformat(),
            "timestamp": timestamp,
            "venue": "binance",
            "mark_price": candle.get("close", 0),
            "index_price": candle.get("close", 0) * 0.9998,  # Slight diff
        })
    
    return data


def generate_oi_data(symbol: str, candles: List[Dict]) -> List[Dict]:
    """
    Generate realistic open interest data.
    OI increases in trends, decreases in reversals.
    """
    if not candles:
        return []
    
    data = []
    now = datetime.now(timezone.utc)
    
    # Base OI (scaled to symbol)
    base_oi_usd = {
        "BTC": 15_000_000_000,  # $15B
        "ETH": 8_000_000_000,   # $8B
        "SOL": 2_000_000_000,   # $2B
    }.get(symbol, 1_000_000_000)
    
    oi_value = base_oi_usd
    
    for i, candle in enumerate(candles[-720:]):
        hours_since_start = i * HOURS_INTERVAL
        timestamp = now - timedelta(hours=720 - hours_since_start)
        
        # OI changes based on volume and trend
        volume = candle.get("volume", 0)
        volume_normalized = volume / max(candles[0].get("volume", 1), 1)
        
        # Price trend
        if i > 0:
            price_change = (candle["close"] - candles[i-1]["close"]) / max(candles[i-1]["close"], 1e-8)
        else:
            price_change = 0
        
        # OI change: trending = increase, reversal = decrease
        if abs(price_change) > 0.005:  # Strong move
            oi_change = random.uniform(0.01, 0.03)
        elif abs(price_change) > 0.002:  # Medium move
            oi_change = random.uniform(-0.01, 0.02)
        else:  # Chop
            oi_change = random.uniform(-0.015, 0.005)
        
        oi_value = oi_value * (1 + oi_change)
        oi_value = max(oi_value, base_oi_usd * 0.5)  # Floor
        oi_value = min(oi_value, base_oi_usd * 2.0)  # Cap
        
        data.append({
            "symbol": symbol,
            "oi_usd": round(oi_value, 2),
            "oi_contracts": round(oi_value / candle.get("close", 1), 2),
            "timestamp": timestamp,
            "source": "binance_futures",
        })
    
    return data


def generate_liquidation_data(symbol: str, candles: List[Dict]) -> List[Dict]:
    """
    Generate liquidation events based on price moves.
    Sharp moves trigger liquidations.
    """
    if not candles:
        return []
    
    data = []
    now = datetime.now(timezone.utc)
    
    for i, candle in enumerate(candles[-720:]):
        hours_since_start = i * HOURS_INTERVAL
        timestamp = now - timedelta(hours=720 - hours_since_start)
        
        # Calculate price move
        if i > 0:
            price_change = (candle["close"] - candles[i-1]["close"]) / max(candles[i-1]["close"], 1e-8)
        else:
            price_change = 0
        
        # Sharp moves trigger liquidations
        if abs(price_change) > 0.01:  # >1% move
            # Number of liquidations
            liq_count = random.randint(50, 500)
            
            # Side: down move = long liqs, up move = short liqs
            side = "LONG" if price_change < 0 else "SHORT"
            
            # Size scaled to symbol
            base_size = {
                "BTC": 1_000_000,
                "ETH": 500_000,
                "SOL": 100_000,
            }.get(symbol, 100_000)
            
            for _ in range(min(liq_count, 20)):  # Max 20 events per hour
                size = random.uniform(base_size * 0.1, base_size) * abs(price_change) * 10
                
                data.append({
                    "symbol": symbol,
                    "side": side,
                    "size": round(size, 2),
                    "price": candle["close"] * (1 + random.uniform(-0.005, 0.005)),
                    "timestamp": timestamp + timedelta(minutes=random.randint(0, 59)),
                    "exchange": "binance",
                })
    
    return data


def generate_orderflow_data(symbol: str, candles: List[Dict]) -> List[Dict]:
    """
    Generate order flow data (taker buy/sell).
    """
    if not candles:
        return []
    
    data = []
    now = datetime.now(timezone.utc)
    
    for i, candle in enumerate(candles[-720:]):
        hours_since_start = i * HOURS_INTERVAL
        timestamp = now - timedelta(hours=720 - hours_since_start)
        
        volume = candle.get("volume", 0)
        close = candle.get("close", 0)
        open_price = candle.get("open", close)
        
        # Buy/sell ratio based on candle direction
        if close > open_price:
            buy_ratio = random.uniform(0.52, 0.65)
        elif close < open_price:
            buy_ratio = random.uniform(0.35, 0.48)
        else:
            buy_ratio = random.uniform(0.48, 0.52)
        
        buy_volume = volume * buy_ratio
        sell_volume = volume * (1 - buy_ratio)
        
        data.append({
            "symbol": symbol,
            "taker_buy_volume": round(buy_volume, 2),
            "taker_sell_volume": round(sell_volume, 2),
            "taker_buy_ratio": round(buy_ratio, 4),
            "total_volume": round(volume, 2),
            "trade_count": random.randint(1000, 50000),
            "timestamp": timestamp,
        })
    
    return data


def generate_symbol_snapshot(symbol: str, candles: List[Dict]) -> Dict:
    """
    Generate current derivatives market snapshot.
    """
    if not candles:
        return {}
    
    latest = candles[-1]
    recent = candles[-24:]  # Last 24 hours
    
    # Calculate momentum for L/S ratio
    price_change = (latest["close"] - recent[0]["close"]) / max(recent[0]["close"], 1e-8)
    
    # Long/Short ratio (bullish momentum = more longs)
    if price_change > 0.02:
        ls_ratio = random.uniform(1.2, 1.8)
    elif price_change < -0.02:
        ls_ratio = random.uniform(0.6, 0.9)
    else:
        ls_ratio = random.uniform(0.9, 1.1)
    
    # Leverage index (volatility based)
    volatility = sum(abs(c["high"] - c["low"]) / max(c["close"], 1e-8) for c in recent) / len(recent)
    leverage_index = min(volatility * 10, 1.0)
    
    # Perp premium (funding proxy)
    perp_premium = random.uniform(-0.002, 0.002)
    
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc),
        "long_short_ratio": round(ls_ratio, 4),
        "leverage_index": round(leverage_index, 4),
        "perp_premium": round(perp_premium, 6),
        "mark_price": latest["close"],
        "index_price": latest["close"] * 0.9998,
        "funding_rate": random.uniform(-0.0002, 0.0003),
    }


def seed_exchange_data():
    """Seed all exchange data collections."""
    db = get_db()
    
    print("\n" + "=" * 50)
    print("EXCHANGE NATIVE DATA SEEDER")
    print("=" * 50)
    
    for symbol in SYMBOLS:
        print(f"\n📊 Seeding {symbol}...")
        
        # Get candles
        candles = list(db.candles.find(
            {"symbol": symbol, "timeframe": "1d"},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(720))
        candles = list(reversed(candles))
        
        if not candles:
            print(f"  ⚠ No candles for {symbol}, skipping")
            continue
        
        print(f"  ✓ Found {len(candles)} candles")
        
        # Funding data
        funding = generate_funding_data(symbol, candles)
        if funding:
            db.exchange_funding_context.delete_many({"symbol": symbol})
            db.exchange_funding_context.insert_many(funding)
            print(f"  ✓ Funding: {len(funding)} records")
        
        # OI data
        oi = generate_oi_data(symbol, candles)
        if oi:
            db.exchange_oi_snapshots.delete_many({"symbol": symbol})
            db.exchange_oi_snapshots.insert_many(oi)
            print(f"  ✓ OI: {len(oi)} records")
        
        # Liquidation data
        liqs = generate_liquidation_data(symbol, candles)
        if liqs:
            db.exchange_liquidation_events.delete_many({"symbol": symbol})
            db.exchange_liquidation_events.insert_many(liqs)
            print(f"  ✓ Liquidations: {len(liqs)} events")
        
        # Order flow data
        flows = generate_orderflow_data(symbol, candles)
        if flows:
            db.exchange_trade_flows.delete_many({"symbol": symbol})
            db.exchange_trade_flows.insert_many(flows)
            print(f"  ✓ Order flow: {len(flows)} records")
        
        # Symbol snapshot
        snapshot = generate_symbol_snapshot(symbol, candles)
        if snapshot:
            db.exchange_symbol_snapshots.update_one(
                {"symbol": symbol},
                {"$set": snapshot},
                upsert=True
            )
            print(f"  ✓ Snapshot: L/S={snapshot['long_short_ratio']:.2f}")
    
    # Create indexes
    print("\n📦 Creating indexes...")
    db.exchange_funding_context.create_index([("symbol", 1), ("timestamp", DESCENDING)])
    db.exchange_oi_snapshots.create_index([("symbol", 1), ("timestamp", DESCENDING)])
    db.exchange_liquidation_events.create_index([("symbol", 1), ("timestamp", DESCENDING)])
    db.exchange_trade_flows.create_index([("symbol", 1), ("timestamp", DESCENDING)])
    db.exchange_symbol_snapshots.create_index([("symbol", 1)])
    print("  ✓ Indexes created")
    
    print("\n" + "=" * 50)
    print("✅ EXCHANGE DATA SEEDING COMPLETE")
    print("=" * 50)


def check_status():
    """Check status of exchange data collections."""
    db = get_db()
    
    print("\n" + "=" * 50)
    print("EXCHANGE DATA STATUS")
    print("=" * 50)
    
    collections = [
        "exchange_funding_context",
        "exchange_oi_snapshots",
        "exchange_liquidation_events",
        "exchange_trade_flows",
        "exchange_symbol_snapshots",
    ]
    
    for col_name in collections:
        count = db[col_name].count_documents({})
        symbols = db[col_name].distinct("symbol")
        print(f"\n{col_name}:")
        print(f"  Total: {count}")
        print(f"  Symbols: {symbols}")


def reset_data():
    """Reset and reseed all data."""
    db = get_db()
    
    print("\n⚠️  Resetting exchange data...")
    
    collections = [
        "exchange_funding_context",
        "exchange_oi_snapshots",
        "exchange_liquidation_events",
        "exchange_trade_flows",
        "exchange_symbol_snapshots",
    ]
    
    for col_name in collections:
        db[col_name].drop()
        print(f"  ✓ Dropped {col_name}")
    
    seed_exchange_data()


def main():
    parser = argparse.ArgumentParser(description="Exchange Native Data Seeder")
    parser.add_argument("--status", action="store_true", help="Check status")
    parser.add_argument("--reset", action="store_true", help="Reset and reseed")
    args = parser.parse_args()
    
    if args.status:
        check_status()
    elif args.reset:
        reset_data()
    else:
        seed_exchange_data()


if __name__ == "__main__":
    main()
