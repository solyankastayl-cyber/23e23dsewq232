#!/usr/bin/env python3
"""
Seed Execution Events for Demo
Creates sample execution events to test Execution Feed UI
"""

import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

async def seed_execution_events():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["trading_os"]
    
    print("🌱 Seeding execution events...")
    
    # Clear existing demo events
    await db.execution_events.delete_many({"demo": True})
    
    # Create execution sequence for 3 orders
    events = []
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    # Order 1: BTCUSDT LONG - Successfully filled
    events.extend([
        {
            "event_id": "demo_event_1",
            "type": "ORDER_SUBMIT_REQUESTED",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.1,
            "order_type": "MARKET",
            "timestamp": (base_time + timedelta(seconds=0)).isoformat(),
            "demo": True
        },
        {
            "event_id": "demo_event_2",
            "type": "ORDER_ACKNOWLEDGED",
            "symbol": "BTCUSDT",
            "order_id": "demo_order_1",
            "timestamp": (base_time + timedelta(seconds=1)).isoformat(),
            "demo": True
        },
        {
            "event_id": "demo_event_3",
            "type": "ORDER_FILLED",
            "symbol": "BTCUSDT",
            "order_id": "demo_order_1",
            "fill_price": 44000.0,
            "fill_quantity": 0.1,
            "timestamp": (base_time + timedelta(seconds=3)).isoformat(),
            "demo": True
        }
    ])
    
    # Order 2: ETHUSDT SHORT - Successfully filled
    events.extend([
        {
            "event_id": "demo_event_4",
            "type": "ORDER_SUBMIT_REQUESTED",
            "symbol": "ETHUSDT",
            "side": "SELL",
            "quantity": 2.0,
            "order_type": "MARKET",
            "timestamp": (base_time + timedelta(minutes=2, seconds=0)).isoformat(),
            "demo": True
        },
        {
            "event_id": "demo_event_5",
            "type": "ORDER_ACKNOWLEDGED",
            "symbol": "ETHUSDT",
            "order_id": "demo_order_2",
            "timestamp": (base_time + timedelta(minutes=2, seconds=1)).isoformat(),
            "demo": True
        },
        {
            "event_id": "demo_event_6",
            "type": "ORDER_FILLED",
            "symbol": "ETHUSDT",
            "order_id": "demo_order_2",
            "fill_price": 2350.0,
            "fill_quantity": 2.0,
            "timestamp": (base_time + timedelta(minutes=2, seconds=2)).isoformat(),
            "demo": True
        }
    ])
    
    # Order 3: SOLUSDT LONG - Acknowledged but not yet filled (pending)
    events.extend([
        {
            "event_id": "demo_event_7",
            "type": "ORDER_SUBMIT_REQUESTED",
            "symbol": "SOLUSDT",
            "side": "BUY",
            "quantity": 10.0,
            "order_type": "LIMIT",
            "price": 105.0,
            "timestamp": (base_time + timedelta(minutes=5, seconds=0)).isoformat(),
            "demo": True
        },
        {
            "event_id": "demo_event_8",
            "type": "ORDER_ACKNOWLEDGED",
            "symbol": "SOLUSDT",
            "order_id": "demo_order_3",
            "timestamp": (base_time + timedelta(minutes=5, seconds=1)).isoformat(),
            "demo": True
        }
    ])
    
    # Order 4: BTCUSDT - Rejected (for error case demo)
    events.extend([
        {
            "event_id": "demo_event_9",
            "type": "ORDER_SUBMIT_REQUESTED",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 100.0,  # Too large
            "order_type": "MARKET",
            "timestamp": (base_time + timedelta(minutes=7, seconds=0)).isoformat(),
            "demo": True
        },
        {
            "event_id": "demo_event_10",
            "type": "ORDER_REJECTED",
            "symbol": "BTCUSDT",
            "reason": "Insufficient balance",
            "timestamp": (base_time + timedelta(minutes=7, seconds=1)).isoformat(),
            "demo": True
        }
    ])
    
    await db.execution_events.insert_many(events)
    print(f"✅ Created {len(events)} demo execution events")
    print(f"   - 2 successful fills (BTC, ETH)")
    print(f"   - 1 pending order (SOL)")
    print(f"   - 1 rejected order (BTC)")
    
    client.close()
    print("🎉 Execution events seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_execution_events())
