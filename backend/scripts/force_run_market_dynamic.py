#!/usr/bin/env python3
"""
Force Run Market Dynamic - Phase 3.2
=====================================

Runs market_dynamic pipeline manually 30 times to generate shadow_trades.
No waiting - simulates time by forcing iterations.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone


async def force_run_market_dynamic(iterations: int = 30):
    """
    Force run market_dynamic pipeline N times.
    
    Each iteration:
    1. Scans market universe
    2. Generates signals for eligible assets
    3. Creates shadow trades
    4. Saves to DB
    """
    
    print(f"\n{'='*60}")
    print(f"🚀 FORCE RUN: market_dynamic x{iterations} iterations")
    print(f"{'='*60}\n")
    
    # Connect to DB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    # Import runner
    from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner
    from modules.market_intelligence.universe_scanner import scan_market_universe
    from modules.signal_generator.multi_asset_generator import get_multi_generator
    from modules.strategy.snapshot_storage import save_snapshot
    from modules.strategy.shadow_trade_service import ShadowTradeService
    
    # Initialize runner
    runner = get_market_dynamic_runner(db=db)
    shadow_service = ShadowTradeService(db)
    
    print(f"✅ Runner initialized")
    print(f"✅ Database connected: {mongo_url}")
    print(f"\nStarting forced iterations...\n")
    
    total_signals = 0
    total_shadow_trades = 0
    
    for i in range(iterations):
        try:
            print(f"[{i+1}/{iterations}] Running iteration...")
            
            # Step 1: Scan universe
            scan_result = await scan_market_universe()
            eligible = [s for s in scan_result["snapshots"] if s.get("eligible", False)]
            
            print(f"  └─ Scanned: {len(scan_result['snapshots'])} assets, {len(eligible)} eligible")
            
            if not eligible:
                print(f"  └─ ⚠️  No eligible assets, skipping")
                continue
            
            # Step 2: Generate signals
            signals_generated = await runner._generate_signals(eligible)
            signals = signals_generated.get("signals", [])
            
            print(f"  └─ Signals: {len(signals)} generated")
            total_signals += len(signals)
            
            if not signals:
                continue
            
            # Step 3: Rank and select (simplified - take top 5)
            from modules.strategy.signal_ranking import rank_signals
            from modules.trading_core.portfolio_service import get_portfolio_service
            
            portfolio_service = get_portfolio_service()
            portfolio = await portfolio_service.get_portfolio_state()
            
            # Get open positions
            positions = await db.positions.find({"status": "OPEN"}).to_list(100)
            
            ranked = rank_signals(
                signals=signals,
                stats_map={},  # Empty stats for now
                execution_map={},
                regime="trend",
                portfolio={"risk_heat": 0.0, "equity": 10000.0},
                open_positions=positions,
                min_score=0.45
            )
            
            # Select top signals (accepted ones)
            selected = [r for r in ranked if r.accepted][:5]
            
            print(f"  └─ Ranked: {len(ranked)}, Accepted: {len(selected)}")
            
            if not selected:
                continue
            
            # Step 4: Create snapshot
            snapshot_data = {
                "experiment_id": "market_dynamic",
                "timestamp": datetime.now(timezone.utc),
                "scan_result": scan_result,
                "selected_signals": [
                    {
                        "symbol": s.symbol,
                        "timeframe": "4h",  # Default timeframe
                        "side": s.side,
                        "price": s.entry,
                        "score": s.final_score,
                        "confidence": s.confidence,
                        "cluster": "majors" if s.symbol in ["BTCUSDT", "ETHUSDT"] else "alts",
                        "alignment": "aligned" if s.final_score > 0.6 else "divergent"
                    }
                    for s in selected
                ]
            }
            
            snapshot = await save_snapshot(
                db,
                snapshot_data,
                scan_metadata={"eligible_count": len(eligible)},
                signal_metadata=signals_generated
            )
            
            # Step 5: Create shadow trades
            trade_ids = await shadow_service.create_from_snapshot(snapshot)
            
            print(f"  └─ ✅ Created {len(trade_ids)} shadow trades")
            total_shadow_trades += len(trade_ids)
            
        except Exception as e:
            print(f"  └─ ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS:")
    print(f"{'='*60}")
    print(f"Iterations completed: {iterations}")
    print(f"Total signals: {total_signals}")
    print(f"Total shadow trades: {total_shadow_trades}")
    print(f"\n✅ Force run complete!")
    print(f"\nNext step:")
    print(f"  curl http://localhost:8001/api/debug/features-from-shadow\n")
    
    client.close()


if __name__ == "__main__":
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(force_run_market_dynamic(iterations))
