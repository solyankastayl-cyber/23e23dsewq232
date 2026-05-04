#!/usr/bin/env python3
"""
Create Manual Decision for E2E Test
"""

import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import time
from uuid import uuid4

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

async def create_manual_decision():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["trading_os"]
    
    print("🎯 Creating manual decision for E2E test...")
    
    # Create decision
    decision_id = f"dec_{uuid4().hex[:12]}"
    now = int(time.time())
    
    decision = {
        "decision_id": decision_id,
        "symbol": "ETHUSDT",
        "side": "BUY",  # Changed from LONG to BUY (execution engine expects BUY/SELL)
        "entry_price": 2350.0,
        "stop_price": 2320.0,
        "target_price": 2420.0,
        "confidence": 0.72,
        "source": "MANUAL_E2E_TEST",
        "status": "PENDING",
        "created_at": now,
        "expires_at": now + 1800,  # 30 minutes
        "reason": "E2E test decision - manual entry"
    }
    
    await db.pending_decisions.insert_one(decision)
    print(f"✅ Created decision: {decision_id}")
    print(f"   Symbol: {decision['symbol']}")
    print(f"   Side: {decision['side']}")
    print(f"   Entry: ${decision['entry_price']}")
    print(f"   Stop: ${decision['stop_price']}")
    print(f"   Target: ${decision['target_price']}")
    print(f"   Confidence: {decision['confidence']}")
    print(f"   Status: {decision['status']}")
    
    client.close()
    print(f"\n🎉 Decision ready! ID: {decision_id}")
    print(f"\n👉 Next step: Go to /trading?tab=decisions and APPROVE it")

if __name__ == "__main__":
    asyncio.run(create_manual_decision())
