"""
P0.2: Health/Readiness Consistency Analysis
============================================

Analyze rассинхрон between health and readiness layers.

Issue:
  Health:    UNKNOWN (no critical alerts)
  Readiness: BLOCKED (9 critical alerts)

Purpose:
  - Find source of 9 critical alerts
  - Check consistency between layers
  - Identify root cause of BLOCKED state
"""

import sys
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")


async def analyze_alerts(db):
    """Analyze alerts from database."""
    print("\n" + "="*60)
    print("ALERTS ANALYSIS")
    print("="*60)
    
    # Check alerts collection
    alerts_count = await db.alerts.count_documents({})
    print(f"\nTotal alerts in DB: {alerts_count}")
    
    if alerts_count > 0:
        # Get recent alerts
        alerts = await db.alerts.find().sort("created_at", -1).limit(20).to_list(length=20)
        
        print(f"\nRecent alerts (last 20):")
        for alert in alerts:
            severity = alert.get("severity", "unknown")
            alert_type = alert.get("type", "unknown")
            message = alert.get("message", "N/A")
            resolved = alert.get("resolved", False)
            
            status = "✓ Resolved" if resolved else "✗ Active"
            print(f"  [{severity.upper()}] {alert_type}: {message[:60]}... ({status})")
        
        # Count by severity and status
        critical_active = await db.alerts.count_documents({
            "severity": "critical",
            "resolved": False
        })
        warning_active = await db.alerts.count_documents({
            "severity": "warning",
            "resolved": False
        })
        
        print(f"\nActive alerts:")
        print(f"  Critical: {critical_active}")
        print(f"  Warning: {warning_active}")
    
    return alerts_count


async def analyze_health_service(db):
    """Analyze health service state."""
    print("\n" + "="*60)
    print("HEALTH SERVICE ANALYSIS")
    print("="*60)
    
    try:
        from modules.strategy.observability.health_service import HealthService
        
        service = HealthService(db)
        health_data = await service.get_system_health("market_dynamic")
        
        print(f"\nHealth Status: {health_data.get('health_status', 'unknown')}")
        print(f"Active Alerts: {len(health_data.get('active_alerts', []))}")
        
        if health_data.get('active_alerts'):
            print("\nAlerts from HealthService:")
            for alert in health_data['active_alerts']:
                print(f"  [{alert.get('severity', 'unknown')}] {alert.get('type', 'unknown')}: {alert.get('message', 'N/A')}")
        
        return health_data
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


async def analyze_readiness_service(db):
    """Analyze readiness service state."""
    print("\n" + "="*60)
    print("READINESS SERVICE ANALYSIS")
    print("="*60)
    
    try:
        from modules.strategy.execution_readiness.execution_readiness_service import ExecutionReadinessService
        
        service = ExecutionReadinessService(db)
        readiness_data = await service.get_execution_readiness("market_dynamic")
        
        print(f"\nReadiness State: {readiness_data.get('state', 'unknown')}")
        print(f"Reason: {readiness_data.get('reason', 'N/A')}")
        
        context = readiness_data.get('context', {})
        print(f"\nContext:")
        print(f"  Health: {context.get('health', 'unknown')}")
        print(f"  Critical Alerts: {context.get('critical_alerts', 0)}")
        print(f"  Warning Alerts: {context.get('warning_alerts', 0)}")
        print(f"  Winrate: {context.get('winrate', 0):.2%}")
        print(f"  Total Trades: {context.get('total_trades', 0)}")
        
        return readiness_data
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


async def check_consistency(health_data, readiness_data, alerts_count):
    """Check consistency between layers."""
    print("\n" + "="*60)
    print("CONSISTENCY CHECK")
    print("="*60)
    
    # Extract values
    health_status = health_data.get('health_status', 'unknown') if health_data else 'unknown'
    health_alerts_count = len(health_data.get('active_alerts', [])) if health_data else 0
    
    readiness_state = readiness_data.get('state', 'unknown') if readiness_data else 'unknown'
    readiness_context = readiness_data.get('context', {}) if readiness_data else {}
    readiness_critical = readiness_context.get('critical_alerts', 0)
    readiness_health = readiness_context.get('health', 'unknown')
    
    print(f"\nLayer comparison:")
    print(f"  DB alerts:                {alerts_count}")
    print(f"  Health API alerts:        {health_alerts_count}")
    print(f"  Readiness critical:       {readiness_critical}")
    
    print(f"\nHealth status:")
    print(f"  Health Service:           {health_status}")
    print(f"  Readiness Context:        {readiness_health}")
    
    print(f"\nReadiness state:          {readiness_state}")
    
    # Check consistency
    issues = []
    
    if readiness_critical > 0 and health_alerts_count == 0:
        issues.append(f"❌ INCONSISTENT: Readiness reports {readiness_critical} critical alerts, but Health Service reports {health_alerts_count}")
    
    if readiness_health == "critical" and health_status != "critical":
        issues.append(f"❌ INCONSISTENT: Readiness health={readiness_health}, but Health Service={health_status}")
    
    if alerts_count == 0 and readiness_critical > 0:
        issues.append(f"⚠️  WARNING: Readiness reports {readiness_critical} alerts, but DB has {alerts_count}")
    
    if issues:
        print(f"\n{'='*60}")
        print("INCONSISTENCIES FOUND:")
        print('='*60)
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ All layers consistent")
    
    return len(issues) == 0


async def main():
    """Main analysis."""
    print("\n" + "="*60)
    print("P0.2: HEALTH/READINESS CONSISTENCY ANALYSIS")
    print("="*60)
    
    # Connect to DB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    try:
        # Analyze each layer
        alerts_count = await analyze_alerts(db)
        health_data = await analyze_health_service(db)
        readiness_data = await analyze_readiness_service(db)
        
        # Check consistency
        consistent = await check_consistency(health_data, readiness_data, alerts_count)
        
        # Final verdict
        print("\n" + "="*60)
        if consistent:
            print("✅ LAYERS CONSISTENT")
        else:
            print("❌ LAYERS INCONSISTENT - P0 ISSUE")
        print("="*60 + "\n")
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
