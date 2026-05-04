"""
System Status Endpoint
======================

Minimal observability for first 50 trades.

Metrics:
- Total decisions
- Approved
- Executed
- Positions opened
- Positions closed
- Flow integrity %
"""

from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
import os

router = APIRouter()


@router.get("/status")
async def get_system_status():
    """
    Get minimal system status for observability.
    
    Returns flow integrity and key counts.
    """
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    # Count decisions
    total_decisions = await db["pending_decisions"].count_documents({})
    auto_decisions = await db["pending_decisions"].count_documents({"auto_generated": True})
    
    # Count by status
    approved = await db["pending_decisions"].count_documents({"status": "EXECUTED"})
    pending = await db["pending_decisions"].count_documents({"status": "PENDING"})
    
    # Count positions
    positions_total = await db["trading_cases"].count_documents({})
    positions_active = await db["trading_cases"].count_documents({"status": "ACTIVE"})
    positions_closed = await db["trading_cases"].count_documents({"status": "CLOSED"})
    
    # Calculate flow integrity
    if approved > 0:
        # Check how many approved decisions have positions
        approved_with_positions = 0
        async for decision in db["pending_decisions"].find({"status": "EXECUTED"}):
            position = await db["trading_cases"].find_one({"decision_id": decision["decision_id"]})
            if position:
                approved_with_positions += 1
        
        flow_integrity = (approved_with_positions / approved) * 100
    else:
        flow_integrity = 0.0
    
    # CRITICAL: Flow integrity for RECENT decisions (last 10, last 20)
    # This filters out legacy data
    recent_approved_10 = await db["pending_decisions"].find(
        {"status": "EXECUTED"}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    recent_approved_20 = await db["pending_decisions"].find(
        {"status": "EXECUTED"}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    # Check flow for last 10
    flow_last_10_count = 0
    for dec in recent_approved_10:
        pos = await db["trading_cases"].find_one({"decision_id": dec["decision_id"]})
        if pos:
            flow_last_10_count += 1
    
    flow_integrity_last_10 = (flow_last_10_count / len(recent_approved_10) * 100) if recent_approved_10 else 0.0
    
    # Check flow for last 20
    flow_last_20_count = 0
    for dec in recent_approved_20:
        pos = await db["trading_cases"].find_one({"decision_id": dec["decision_id"]})
        if pos:
            flow_last_20_count += 1
    
    flow_integrity_last_20 = (flow_last_20_count / len(recent_approved_20) * 100) if recent_approved_20 else 0.0
    
    return {
        "decisions": {
            "total": total_decisions,
            "auto_generated": auto_decisions,
            "approved": approved,
            "pending": pending
        },
        "positions": {
            "total": positions_total,
            "active": positions_active,
            "closed": positions_closed
        },
        "flow_integrity": {
            "overall_pct": round(flow_integrity, 1),
            "last_10_pct": round(flow_integrity_last_10, 1),
            "last_20_pct": round(flow_integrity_last_20, 1)
        },
        "adaptation_disabled": os.getenv("DISABLE_ADAPTATION", "false") == "true"
    }


@router.get("/recent-trades")
async def get_recent_trades(limit: int = 5):
    """
    Get last N closed trades with PnL.
    
    Step C: Loss Visibility - simple list without charts.
    """
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["trading_os"]
    
    # Get recent closed positions
    closed_positions = await db["trading_cases"].find(
        {"status": "CLOSED"}
    ).sort("closed_at", -1).limit(limit).to_list(limit)
    
    trades = []
    
    for pos in closed_positions:
        pnl = pos.get("realized_pnl", 0.0)
        
        trades.append({
            "symbol": pos.get("symbol"),
            "side": pos.get("side"),
            "pnl_usd": round(pnl, 2),
            "is_win": pnl > 0,
            "closed_at": pos.get("closed_at")
        })
    
    return {
        "recent_trades": trades,
        "count": len(trades)
    }
