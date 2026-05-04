"""
Snapshot Storage
================

Phase 2.5: Persistent storage of market_dynamic decision cycles.

Every cycle, system records:
- Market bias + structure
- Signals generated/filtered/selected
- Scores, clusters, rejections
- Metadata (duration, etc.)

Purpose: Create dataset for ML + historical analysis.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def save_snapshot(
    db: AsyncIOMotorDatabase,
    preview_data: Dict[str, Any],
    scan_metadata: Optional[Dict[str, Any]] = None,
    signal_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Save market_dynamic cycle snapshot to database.
    
    Args:
        db: MongoDB database
        preview_data: Preview result from ranking/allocation
        scan_metadata: Optional scan metadata
        signal_metadata: Optional signal generation metadata
        
    Returns:
        Saved snapshot document (with _id)
    """
    snapshot = {
        "timestamp": preview_data["timestamp"],
        "experiment_id": preview_data["experiment_id"],
        
        # Market state
        "market_bias": preview_data["market_bias"],
        "market_structure": preview_data["market_structure"],
        "long_ratio": preview_data["long_ratio"],
        "short_ratio": preview_data["short_ratio"],
        
        # Signal flow
        "signals_total": preview_data["signals_total"],
        "signals_filtered": preview_data["signals_filtered"],
        "selected_count": preview_data["selected_count"],
        
        # Distribution
        "cluster_distribution": preview_data["cluster_distribution"],
        "avg_confidence": preview_data["avg_confidence"],
        
        # Selected signals (lightweight - only essential fields)
        "selected_signals": [
            {
                "symbol": s["symbol"],
                "timeframe": s["timeframe"],
                "side": s["side"],
                "score": s["score"],
                "confidence": s["confidence"],
                "price": s["price"],
                "cluster": s["cluster"],
            }
            for s in preview_data["selected_signals"]
        ],
        
        # Rejections
        "rejected": preview_data["rejected"],
        
        # Metadata
        "meta": {
            "ranking_duration_ms": preview_data.get("ranking_duration_ms", 0),
            "scan_duration_ms": scan_metadata.get("scan_duration_ms", 0) if scan_metadata else 0,
            "signal_duration_ms": signal_metadata.get("generation_duration_ms", 0) if signal_metadata else 0,
        },
        
        # For future querying
        "created_at": datetime.now(timezone.utc),
    }
    
    result = await db.market_dynamic_snapshots.insert_one(snapshot)
    snapshot["_id"] = result.inserted_id
    
    logger.info(
        f"[Snapshot] Saved: {preview_data['selected_count']} selected, "
        f"bias={preview_data['market_bias']}, "
        f"structure={preview_data['market_structure']['alignment']}"
    )
    
    return snapshot  # Return full snapshot with _id


async def get_latest_snapshots(
    db: AsyncIOMotorDatabase,
    limit: int = 20,
    experiment_id: str = "market_dynamic"
) -> List[Dict[str, Any]]:
    """Get recent snapshots."""
    cursor = db.market_dynamic_snapshots.find(
        {"experiment_id": experiment_id}
    ).sort("created_at", -1).limit(limit)
    
    snapshots = await cursor.to_list(length=limit)
    
    # Convert ObjectId to str
    for snap in snapshots:
        snap["_id"] = str(snap["_id"])
    
    return snapshots


async def get_snapshot_statistics(
    db: AsyncIOMotorDatabase,
    experiment_id: str = "market_dynamic",
    lookback_hours: int = 24
) -> Dict[str, Any]:
    """
    Calculate statistics from recent snapshots.
    
    Returns:
        - avg_selected
        - avg_signals
        - dominant_bias
        - bias_distribution
    """
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    
    cursor = db.market_dynamic_snapshots.find({
        "experiment_id": experiment_id,
        "created_at": {"$gte": cutoff}
    })
    
    snapshots = await cursor.to_list(length=1000)
    
    if not snapshots:
        return {
            "total_snapshots": 0,
            "avg_selected": 0.0,
            "avg_signals": 0.0,
            "dominant_bias": "neutral",
            "bias_distribution": {},
        }
    
    total_selected = sum(s["selected_count"] for s in snapshots)
    total_signals = sum(s["signals_total"] for s in snapshots)
    
    # Bias distribution
    bias_counts = {}
    for snap in snapshots:
        bias = snap["market_bias"]
        bias_counts[bias] = bias_counts.get(bias, 0) + 1
    
    # Dominant bias
    dominant_bias = max(bias_counts.items(), key=lambda x: x[1])[0] if bias_counts else "neutral"
    
    return {
        "total_snapshots": len(snapshots),
        "avg_selected": round(total_selected / len(snapshots), 2),
        "avg_signals": round(total_signals / len(snapshots), 2),
        "dominant_bias": dominant_bias,
        "bias_distribution": bias_counts,
        "lookback_hours": lookback_hours,
    }
