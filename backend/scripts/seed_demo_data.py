#!/usr/bin/env python3
"""
Demo Data Seeder for Trading Terminal
Creates sample positions and decision traces for testing
"""

import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

async def seed_demo_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["trading_os"]
    
    print("🌱 Seeding demo data...")
    
    # Clear existing demo data
    await db.positions.delete_many({"demo": True})
    await db.decision_outcomes.delete_many({"demo": True})
    
    # Create 3 demo positions
    positions = [
        {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "size": 0.1,
            "entry_price": 44000.0,
            "current_price": 44550.0,
            "unrealized_pnl": 55.0,
            "realized_pnl": 0.0,
            "status": "open",
            "entry_time": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "tp": 45000.0,
            "sl": 43500.0,
            "demo": True
        },
        {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "size": 2.0,
            "entry_price": 2350.0,
            "current_price": 2340.0,
            "unrealized_pnl": 20.0,
            "realized_pnl": 0.0,
            "status": "open",
            "entry_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "tp": 2300.0,
            "sl": 2370.0,
            "demo": True
        },
        {
            "symbol": "SOLUSDT",
            "side": "LONG",
            "size": 10.0,
            "entry_price": 105.0,
            "current_price": 106.5,
            "unrealized_pnl": 15.0,
            "realized_pnl": 0.0,
            "status": "open",
            "entry_time": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
            "tp": 110.0,
            "sl": 103.0,
            "demo": True
        }
    ]
    
    await db.positions.insert_many(positions)
    print(f"✅ Created {len(positions)} demo positions")
    
    # Create 10 demo decision outcomes
    decisions = []
    for i in range(10):
        outcome = "win" if i % 3 != 0 else "loss"
        pnl = (50.0 + i * 10) if outcome == "win" else -(20.0 + i * 5)
        
        decisions.append({
            "decision_id": str(uuid.uuid4()),
            "symbol": ["BTCUSDT", "ETHUSDT", "SOLUSDT"][i % 3],
            "direction": ["LONG", "SHORT"][i % 2],
            "confidence": 0.6 + (i % 5) * 0.05,
            "outcome": outcome,
            "pnl": pnl,
            "entry_price": 100.0 + i * 10,
            "exit_price": 100.0 + i * 10 + (5 if outcome == "win" else -3),
            "entry_time": (datetime.now(timezone.utc) - timedelta(hours=24-i)).isoformat(),
            "exit_time": (datetime.now(timezone.utc) - timedelta(hours=22-i)).isoformat(),
            "hold_duration_hours": 2.0,
            "demo": True
        })
    
    await db.decision_outcomes.insert_many(decisions)
    print(f"✅ Created {len(decisions)} demo decision outcomes")
    
    client.close()
    print("🎉 Demo data seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
