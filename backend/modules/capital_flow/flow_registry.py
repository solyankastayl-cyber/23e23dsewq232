"""
Flow Registry

PHASE 42 — Capital Flow Engine

MongoDB persistence for flow snapshots, rotations, and scores.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .flow_types import (
    CapitalFlowSnapshot,
    RotationState,
    FlowScore,
)


class FlowRegistry:
    """MongoDB persistence for capital flow data."""

    def __init__(self):
        self._db = None
        self._init_db()

    def _init_db(self):
        try:
            from core.database import get_database
            self._db = get_database()
            if self._db is not None:
                self._db.capital_flow_snapshots.create_index("timestamp")
                self._db.capital_flow_rotations.create_index("timestamp")
                self._db.capital_flow_scores.create_index("timestamp")
                self._db.capital_flow_scores.create_index("flow_bias")
        except Exception:
            pass

    def save_snapshot(self, snapshot: CapitalFlowSnapshot):
        if self._db is None:
            return
        doc = snapshot.model_dump()
        doc["flow_state"] = doc["flow_state"].value if hasattr(doc["flow_state"], "value") else str(doc["flow_state"])
        doc["timestamp"] = doc["timestamp"].isoformat() if isinstance(doc["timestamp"], datetime) else doc["timestamp"]
        self._db.capital_flow_snapshots.insert_one(doc)

    def save_rotation(self, rotation: RotationState):
        if self._db is None:
            return
        doc = rotation.model_dump()
        doc["rotation_type"] = doc["rotation_type"].value if hasattr(doc["rotation_type"], "value") else str(doc["rotation_type"])
        doc["from_bucket"] = doc["from_bucket"].value if hasattr(doc["from_bucket"], "value") else str(doc["from_bucket"])
        doc["to_bucket"] = doc["to_bucket"].value if hasattr(doc["to_bucket"], "value") else str(doc["to_bucket"])
        doc["timestamp"] = doc["timestamp"].isoformat() if isinstance(doc["timestamp"], datetime) else doc["timestamp"]
        self._db.capital_flow_rotations.insert_one(doc)

    def save_score(self, score: FlowScore):
        if self._db is None:
            return
        doc = score.model_dump()
        doc["flow_bias"] = doc["flow_bias"].value if hasattr(doc["flow_bias"], "value") else str(doc["flow_bias"])
        doc["dominant_rotation"] = doc["dominant_rotation"].value if hasattr(doc["dominant_rotation"], "value") else str(doc["dominant_rotation"])
        doc["timestamp"] = doc["timestamp"].isoformat() if isinstance(doc["timestamp"], datetime) else doc["timestamp"]
        self._db.capital_flow_scores.insert_one(doc)

    def get_latest_snapshots(self, limit: int = 50) -> List[Dict]:
        if self._db is None:
            return []
        cursor = self._db.capital_flow_snapshots.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return list(cursor)

    def get_latest_rotations(self, limit: int = 50) -> List[Dict]:
        if self._db is None:
            return []
        cursor = self._db.capital_flow_rotations.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return list(cursor)

    def get_latest_scores(self, limit: int = 50) -> List[Dict]:
        if self._db is None:
            return []
        cursor = self._db.capital_flow_scores.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return list(cursor)

    def get_scores_by_bias(self, bias: str, limit: int = 50) -> List[Dict]:
        if self._db is None:
            return []
        cursor = self._db.capital_flow_scores.find(
            {"flow_bias": bias}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return list(cursor)


# Singleton
_registry: Optional[FlowRegistry] = None


def get_flow_registry() -> FlowRegistry:
    global _registry
    if _registry is None:
        _registry = FlowRegistry()
    return _registry
