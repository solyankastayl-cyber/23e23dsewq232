"""
Market Data Seed Script
=======================
Bootstrap ta_engine with historical candles from Binance
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.market_data_live.binance_rest_client import BinanceRestClient


SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["1h", "4h", "1d"]
LIMIT = 500


async def seed():
    print("=" * 60)
    print("MARKET DATA SEED - Sprint A2")
    print("=" * 60)
    
    client = BinanceRestClient()
    
    # ⚠️  CRITICAL: TA Engine reads from "candles" collection with "timestamp" field
    # We bypass MarketDataRepository and write directly to match TA Engine schema
    
    from pymongo import MongoClient
    from datetime import datetime, timezone
    import os
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    mongo_client = MongoClient(mongo_url)
    db = mongo_client["ta_engine"]
    candles_collection = db["candles"]
    
    # Clear existing data to avoid duplicates
    print(f"[SEED] Clearing existing candles...")
    candles_collection.delete_many({})
    
    total_inserted = 0
    
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            print(f"\n[SEED] Fetching {symbol} {timeframe}...")
            
            try:
                candles_data = await client.get_klines(symbol, timeframe, LIMIT)
                
                if not candles_data:
                    print(f"  ⚠️  No data returned for {symbol} {timeframe}")
                    continue
                
                # Prepare bulk insert documents
                documents = []
                for c in candles_data:
                    # Convert millisecond timestamp to datetime
                    timestamp_dt = datetime.fromtimestamp(
                        c["open_time"] / 1000, 
                        tz=timezone.utc
                    )
                    
                    doc = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "timestamp": timestamp_dt,  # TA Engine expects this field
                        "open": float(c["open"]),
                        "high": float(c["high"]),
                        "low": float(c["low"]),
                        "close": float(c["close"]),
                        "volume": float(c["volume"]),
                    }
                    documents.append(doc)
                
                # Bulk insert
                if documents:
                    result = candles_collection.insert_many(documents)
                    inserted = len(result.inserted_ids)
                    total_inserted += inserted
                    print(f"  ✅ {symbol} {timeframe}: {inserted} candles inserted")
                
            except Exception as e:
                print(f"  ❌ Error for {symbol} {timeframe}: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"✅ SEED COMPLETE: {total_inserted} total candles")
    print("=" * 60)
    
    # Verify
    print("\n[VERIFY] Checking ta_engine.candles collection...")
    count = candles_collection.count_documents({})
    print(f"Total documents in candles: {count}")
    
    if count > 0:
        sample = candles_collection.find_one()
        print(f"Sample document fields: {list(sample.keys())}")
        print(f"Sample: symbol={sample.get('symbol')}, timeframe={sample.get('timeframe')}, timestamp={sample.get('timestamp')}")
    
    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(seed())
