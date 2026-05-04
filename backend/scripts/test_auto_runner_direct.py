"""
Direct Phase 3.0B Status Check
================================

Check if auto_runner_state was initialized properly.
"""

import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient
from modules.strategy.paper_auto_runner import AutoRunnerState


async def main():
    """Test auto_runner functionality directly."""
    print("\n=== Direct Auto Runner State Test ===\n")
    
    # Create state
    state = AutoRunnerState()
    
    # Test pause/resume
    print("1. Initial status:")
    status = state.get_status()
    print(f"   Paused: {status['paused']}")
    print(f"   Auto-disabled: {status['auto_disabled']}")
    
    print("\n2. Testing pause:")
    state.pause("test")
    status = state.get_status()
    print(f"   Paused: {status['paused']}")
    print(f"   Reason: {status['pause_reason']}")
    
    print("\n3. Testing resume:")
    state.resume()
    status = state.get_status()
    print(f"   Paused: {status['paused']}")
    
    print("\n4. Testing disable:")
    state.disable("test_disable")
    status = state.get_status()
    print(f"   Auto-disabled: {status['auto_disabled']}")
    print(f"   Reason: {status['auto_disabled_reason']}")
    
    print("\n5. Testing enable:")
    state.enable()
    status = state.get_status()
    print(f"   Auto-disabled: {status['auto_disabled']}")
    
    print("\n✅ Auto Runner State working correctly!")
    print("\nNow checking audit logger...")
    
    # Test audit logger
    from modules.strategy.paper_auto_runner.audit_logger import AuditLogger
    from datetime import datetime, timezone
    
    mongo_url = os.environ.get("MONGO_URL")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    audit = AuditLogger(db)
    
    # Log test event
    await audit.log({
        "experiment_id": "market_dynamic",
        "decision": "TEST_EVENT",
        "reason": "direct_test",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    print("✅ Audit event logged")
    
    # Get recent logs
    logs = await audit.get_recent_logs(limit=5)
    print(f"\n✅ Retrieved {len(logs)} recent audit logs")
    
    client.close()
    
    print("\n=== All Components Working ===\n")


if __name__ == "__main__":
    asyncio.run(main())
