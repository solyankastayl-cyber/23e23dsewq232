"""
Outcome Repository

Database operations for prediction outcomes and resolutions.
"""

import time
from typing import Dict, Any, Optional, List
from bson import ObjectId


def mark_prediction_resolved(
    db,
    prediction_id: str,
    resolution: Dict[str, Any]
) -> bool:
    """
    Mark a prediction as resolved with outcome data.
    
    Args:
        db: MongoDB database
        prediction_id: Prediction document ID
        resolution: Resolution dict from resolution_rules
    
    Returns:
        True if update succeeded
    """
    try:
        # Handle both string and ObjectId
        if isinstance(prediction_id, str):
            try:
                pid = ObjectId(prediction_id)
            except:
                pid = prediction_id
        else:
            pid = prediction_id
        
        result = db.prediction_snapshots.update_one(
            {"_id": pid},
            {
                "$set": {
                    "status": "resolved",
                    "resolution": {
                        **resolution,
                        "resolved_at": int(time.time()),
                    }
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"[OutcomeRepo] Error marking resolved: {e}")
        return False


def get_pending_predictions(db, limit: int = 100) -> List[Dict[str, Any]]:
    """Get predictions awaiting resolution."""
    try:
        cursor = db.prediction_snapshots.find(
            {"status": "pending", "latest": True}
        ).limit(limit)
        return list(cursor)
    except Exception:
        return []


def get_resolved_predictions(
    db,
    limit: int = 500,
    regime: Optional[str] = None,
    model: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get resolved predictions for metrics calculation."""
    try:
        query = {"status": "resolved"}
        if regime:
            query["regime"] = regime
        if model:
            query["model"] = model
        
        cursor = db.prediction_snapshots.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return list(cursor)
    except Exception:
        return []


def count_predictions_by_status(db) -> Dict[str, int]:
    """Count predictions by status."""
    try:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        result = list(db.prediction_snapshots.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in result if r["_id"]}
    except Exception:
        return {}


def log_resolution_event(
    db,
    prediction_id: str,
    symbol: str,
    timeframe: str,
    event_type: str,
    details: Dict[str, Any]
):
    """Log resolution event for debugging."""
    try:
        db.prediction_resolution_events.insert_one({
            "prediction_id": str(prediction_id),
            "symbol": symbol,
            "timeframe": timeframe,
            "created_at": int(time.time()),
            "event_type": event_type,
            "details": details,
        })
    except Exception as e:
        print(f"[OutcomeRepo] Error logging event: {e}")
