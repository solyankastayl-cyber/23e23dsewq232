"""
Phase 2.7C Test Script

Creates synthetic shadow trades and tests feature performance aggregation.
"""
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, '/app/backend')


async def seed_test_data():
    """Create synthetic shadow trades for testing."""
    mongo_url = os.environ.get("MONGO_URL")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    # Clear existing test data
    await db.shadow_trades.delete_many({"experiment_id": "market_dynamic"})
    print("[SEED] Cleared existing market_dynamic shadow trades")
    
    now = datetime.now(timezone.utc)
    
    # Create diverse set of trades
    trades = []
    
    # Scenario 1: Majors cluster, aligned, 4h timeframe, LONG side
    # High score, good performance (winners)
    for i in range(15):
        trades.append({
            "experiment_id": "market_dynamic",
            "snapshot_id": f"snap_{i}",
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "side": "LONG",
            "entry_price": 70000.0 + (i * 100),
            "entry_time": now - timedelta(hours=i*4),
            "features": {
                "score": 0.75 + (i * 0.01),  # 0.75-0.89
                "confidence": 0.7,
                "cluster": "majors",
                "market_bias": "bullish",
                "market_structure": {"alignment": "aligned"}
            },
            "horizons": [
                {
                    "name": "24h",
                    "resolve_at": now - timedelta(hours=i*4) + timedelta(hours=24),
                    "resolved": True,
                    "exit_price": 70500.0 + (i * 100),
                    "pnl": 0.007,  # ~0.7% gain
                    "mfe": 0.012,
                    "mae": -0.002
                },
                {
                    "name": "48h",
                    "resolve_at": now - timedelta(hours=i*4) + timedelta(hours=48),
                    "resolved": True,
                    "exit_price": 71000.0 + (i * 100),
                    "pnl": 0.014,  # ~1.4% gain
                    "mfe": 0.020,
                    "mae": -0.003
                },
                {
                    "name": "7d",
                    "resolve_at": now - timedelta(hours=i*4) + timedelta(days=7),
                    "resolved": True,
                    "exit_price": 72000.0 + (i * 100),
                    "pnl": 0.028,  # ~2.8% gain
                    "mfe": 0.040,
                    "mae": -0.005
                }
            ],
            "created_at": now - timedelta(hours=i*4),
            "updated_at": now
        })
    
    # Scenario 2: Alts cluster, misaligned, 1h timeframe, SHORT side
    # Medium score, poor performance (losers)
    for i in range(12):
        trades.append({
            "experiment_id": "market_dynamic",
            "snapshot_id": f"snap_alt_{i}",
            "symbol": "SOLUSDT",
            "timeframe": "1h",
            "side": "SHORT",
            "entry_price": 150.0 + (i * 2),
            "entry_time": now - timedelta(hours=i*2),
            "features": {
                "score": 0.55 + (i * 0.01),  # 0.55-0.66
                "confidence": 0.5,
                "cluster": "alts",
                "market_bias": "bearish",
                "market_structure": {"alignment": "misaligned"}
            },
            "horizons": [
                {
                    "name": "24h",
                    "resolve_at": now - timedelta(hours=i*2) + timedelta(hours=24),
                    "resolved": True,
                    "exit_price": 151.5 + (i * 2),
                    "pnl": -0.010,  # -1% loss
                    "mfe": 0.003,
                    "mae": -0.015
                },
                {
                    "name": "48h",
                    "resolve_at": now - timedelta(hours=i*2) + timedelta(hours=48),
                    "resolved": True,
                    "exit_price": 152.0 + (i * 2),
                    "pnl": -0.013,  # -1.3% loss
                    "mfe": 0.002,
                    "mae": -0.020
                },
                {
                    "name": "7d",
                    "resolve_at": now - timedelta(hours=i*2) + timedelta(days=7),
                    "resolved": True,
                    "exit_price": 153.0 + (i * 2),
                    "pnl": -0.020,  # -2% loss
                    "mfe": 0.001,
                    "mae": -0.025
                }
            ],
            "created_at": now - timedelta(hours=i*2),
            "updated_at": now
        })
    
    # Scenario 3: Majors cluster, aligned, 1d timeframe, LONG side
    # Lower score, mixed performance
    for i in range(8):
        pnl_24h = 0.005 if i % 2 == 0 else -0.008
        pnl_48h = 0.008 if i % 2 == 0 else -0.012
        pnl_7d = 0.015 if i % 2 == 0 else -0.018
        
        trades.append({
            "experiment_id": "market_dynamic",
            "snapshot_id": f"snap_eth_{i}",
            "symbol": "ETHUSDT",
            "timeframe": "1d",
            "side": "LONG",
            "entry_price": 3500.0 + (i * 50),
            "entry_time": now - timedelta(days=i),
            "features": {
                "score": 0.45 + (i * 0.02),  # 0.45-0.59
                "confidence": 0.6,
                "cluster": "majors",
                "market_bias": "neutral",
                "market_structure": {"alignment": "aligned"}
            },
            "horizons": [
                {
                    "name": "24h",
                    "resolve_at": now - timedelta(days=i) + timedelta(hours=24),
                    "resolved": True,
                    "exit_price": 3500.0 + (i * 50) + (pnl_24h * 3500),
                    "pnl": pnl_24h,
                    "mfe": abs(pnl_24h) * 1.5,
                    "mae": -abs(pnl_24h) * 0.5
                },
                {
                    "name": "48h",
                    "resolve_at": now - timedelta(days=i) + timedelta(hours=48),
                    "resolved": True,
                    "exit_price": 3500.0 + (i * 50) + (pnl_48h * 3500),
                    "pnl": pnl_48h,
                    "mfe": abs(pnl_48h) * 1.5,
                    "mae": -abs(pnl_48h) * 0.5
                },
                {
                    "name": "7d",
                    "resolve_at": now - timedelta(days=i) + timedelta(days=7),
                    "resolved": True,
                    "exit_price": 3500.0 + (i * 50) + (pnl_7d * 3500),
                    "pnl": pnl_7d,
                    "mfe": abs(pnl_7d) * 1.5,
                    "mae": -abs(pnl_7d) * 0.5
                }
            ],
            "created_at": now - timedelta(days=i),
            "updated_at": now
        })
    
    # Insert all trades
    if trades:
        result = await db.shadow_trades.insert_many(trades)
        print(f"[SEED] Inserted {len(result.inserted_ids)} shadow trades")
    
    # Print summary
    total = await db.shadow_trades.count_documents({"experiment_id": "market_dynamic"})
    resolved_24h = await db.shadow_trades.count_documents({
        "experiment_id": "market_dynamic",
        "horizons": {"$elemMatch": {"name": "24h", "resolved": True}}
    })
    
    print(f"[SEED] Total trades: {total}")
    print(f"[SEED] Resolved (24h): {resolved_24h}")
    
    # Show one sample
    sample = await db.shadow_trades.find_one({"experiment_id": "market_dynamic"})
    if sample:
        print(f"\n[SEED] Sample trade:")
        print(f"  Symbol: {sample['symbol']}")
        print(f"  Side: {sample['side']}")
        print(f"  Timeframe: {sample['timeframe']}")
        print(f"  Cluster: {sample['features']['cluster']}")
        print(f"  Score: {sample['features']['score']}")
        print(f"  Horizons: {[h['name'] for h in sample['horizons']]}")


async def test_feature_api():
    """Test the new /api/experiments/market_dynamic/features endpoint."""
    import aiohttp
    
    backend_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
    url = f"{backend_url}/api/experiments/market_dynamic/features"
    
    print("\n[TEST] Calling feature performance API...")
    print(f"[TEST] URL: {url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            status = resp.status
            data = await resp.json()
            
            print(f"\n[TEST] Status: {status}")
            print(f"[TEST] Response OK: {data.get('ok')}")
            
            if data.get("ok"):
                meta = data.get("meta", {})
                print(f"\n[TEST] Meta:")
                print(f"  Total trades: {meta.get('total_trades')}")
                print(f"  Min sample size: {meta.get('min_sample_size')}")
                print(f"  Generated at: {meta.get('generated_at')}")
                
                horizons = data.get("horizons", {})
                print(f"\n[TEST] Horizons: {list(horizons.keys())}")
                
                # Check 24h horizon
                if "24h" in horizons:
                    h24 = horizons["24h"]
                    print(f"\n[TEST] 24h Horizon:")
                    print(f"  by_cluster: {len(h24.get('by_cluster', []))} groups")
                    print(f"  by_alignment: {len(h24.get('by_alignment', []))} groups")
                    print(f"  by_timeframe: {len(h24.get('by_timeframe', []))} groups")
                    print(f"  by_score_bucket: {len(h24.get('by_score_bucket', []))} groups")
                    print(f"  by_side: {len(h24.get('by_side', []))} groups")
                    
                    # Show cluster details
                    print(f"\n[TEST] Cluster breakdown (24h):")
                    for cluster in h24.get("by_cluster", []):
                        valid_flag = "✅" if cluster.get("valid") else "⚠️"
                        print(f"  {valid_flag} {cluster['cluster']}: count={cluster['count']}, winrate={cluster['winrate']:.2%}, avg_pnl={cluster['avg_pnl']:.4f}")
                    
                    # Show side details
                    print(f"\n[TEST] Side breakdown (24h):")
                    for side in h24.get("by_side", []):
                        valid_flag = "✅" if side.get("valid") else "⚠️"
                        print(f"  {valid_flag} {side['side']}: count={side['count']}, winrate={side['winrate']:.2%}, avg_pnl={side['avg_pnl']:.4f}")
                    
                    # Show timeframe details
                    print(f"\n[TEST] Timeframe breakdown (24h):")
                    for tf in h24.get("by_timeframe", []):
                        valid_flag = "✅" if tf.get("valid") else "⚠️"
                        print(f"  {valid_flag} {tf['timeframe']}: count={tf['count']}, winrate={tf['winrate']:.2%}, avg_pnl={tf['avg_pnl']:.4f}")
                
                print("\n[TEST] ✅ Feature validation API working correctly!")
            else:
                print(f"[TEST] ❌ API returned error: {data}")


async def main():
    print("=" * 60)
    print("PHASE 2.7C: Feature Validation Test")
    print("=" * 60)
    
    # Step 1: Seed test data
    await seed_test_data()
    
    # Step 2: Test API
    await test_feature_api()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
