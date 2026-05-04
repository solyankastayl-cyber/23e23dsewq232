"""
Pattern History Engine — Market Evolution Snapshots
====================================================

Stores significant pattern state changes for:
- Market evolution tracking
- History overlay rendering
- Replay / scrubber functionality

Storage rules:
- Only store on CHANGE events (not every tick)
- Maximum 100 snapshots per symbol/timeframe
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def should_store(prev: Optional[Dict], new: Dict, conf_delta: float = 0.08) -> bool:
    """
    Determine if we should store a new snapshot.
    Only store on meaningful changes.
    """
    if not prev:
        return True

    prev_dom = prev.get("dominant") or {}
    new_dom = new.get("dominant") or {}

    # 1. Dominant type changed
    if prev_dom.get("type") != new_dom.get("type"):
        return True

    # 2. Lifecycle state changed
    if prev_dom.get("lifecycle") != new_dom.get("lifecycle"):
        return True

    # 3. Market state changed
    if prev.get("market_state") != new.get("market_state"):
        return True

    # 4. Significant confidence shift
    prev_conf = prev_dom.get("confidence", 0)
    new_conf = new_dom.get("confidence", 0)
    if abs(prev_conf - new_conf) > conf_delta:
        return True

    return False


def build_snapshot(
    symbol: str,
    timeframe: str,
    market_state: str,
    dominant: Dict,
    alternatives: List[Dict],
    render_contract: Optional[Dict] = None,
) -> Dict:
    """
    Build a history snapshot document.
    """
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),

        "market_state": market_state,

        "dominant": {
            "type": dominant.get("type"),
            "confidence": round(dominant.get("confidence", 0), 3),
            "lifecycle": dominant.get("lifecycle"),
            "bias": dominant.get("bias"),
        },

        "alternatives": [
            {
                "type": p.get("type"),
                "confidence": round(p.get("confidence", 0), 3),
                "lifecycle": p.get("lifecycle"),
            }
            for p in (alternatives or [])[:2]
        ],

        # Store render contract for overlay
        "render_contract": render_contract,
    }


def get_event_type(prev: Optional[Dict], new: Dict) -> str:
    """
    Determine the type of change event.
    """
    if not prev:
        return "initial"

    prev_dom = prev.get("dominant") or {}
    new_dom = new.get("dominant") or {}

    new_lc = new_dom.get("lifecycle")
    prev_lc = prev_dom.get("lifecycle")

    if new_lc in ("confirmed_up", "confirmed_down") and prev_lc == "forming":
        return "breakout" if new_lc == "confirmed_up" else "breakdown"

    if new_lc == "invalidated" and prev_lc != "invalidated":
        return "invalidation"

    if prev_dom.get("type") != new_dom.get("type"):
        return "pattern_change"

    return "update"


class PatternHistoryManager:
    """
    Manages pattern history storage and retrieval.
    """

    def __init__(self, db):
        self.collection = db["pattern_history"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient queries."""
        try:
            self.collection.create_index([
                ("symbol", 1),
                ("timeframe", 1),
                ("timestamp", -1)
            ])
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    def get_last_snapshot(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get the most recent snapshot."""
        doc = self.collection.find_one(
            {"symbol": symbol.upper(), "timeframe": timeframe},
            sort=[("timestamp", -1)],
            projection={"_id": 0}
        )
        return doc

    def save_snapshot(self, snapshot: Dict) -> bool:
        """Save a new snapshot, enforce max limit."""
        try:
            # Insert new
            self.collection.insert_one(snapshot)

            # Cleanup old (keep max 100 per symbol/timeframe)
            symbol = snapshot["symbol"]
            timeframe = snapshot["timeframe"]

            count = self.collection.count_documents({
                "symbol": symbol,
                "timeframe": timeframe
            })

            if count > 100:
                # Delete oldest
                oldest = self.collection.find(
                    {"symbol": symbol, "timeframe": timeframe},
                    sort=[("timestamp", 1)],
                    limit=count - 100
                )
                oldest_ids = [d["_id"] for d in oldest]
                if oldest_ids:
                    self.collection.delete_many({"_id": {"$in": oldest_ids}})

            return True
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return False

    def get_history(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent history snapshots."""
        cursor = self.collection.find(
            {"symbol": symbol.upper(), "timeframe": timeframe},
            sort=[("timestamp", -1)],
            limit=limit,
            projection={"_id": 0}
        )
        return list(cursor)

    def get_timeline(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get timeline for replay (ascending order)."""
        cursor = self.collection.find(
            {"symbol": symbol.upper(), "timeframe": timeframe},
            sort=[("timestamp", 1)],  # Ascending for replay
            limit=limit,
            projection={"_id": 0}
        )
        return list(cursor)

    def process_analysis_result(
        self,
        symbol: str,
        timeframe: str,
        market_state: str,
        dominant: Dict,
        alternatives: List[Dict],
        render_contract: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Process a new analysis result and store if significant.
        Returns the snapshot if stored, None otherwise.
        """
        if not dominant:
            return None

        # Build new snapshot
        new_snapshot = build_snapshot(
            symbol=symbol,
            timeframe=timeframe,
            market_state=market_state,
            dominant=dominant,
            alternatives=alternatives,
            render_contract=render_contract,
        )

        # Check if we should store
        prev = self.get_last_snapshot(symbol, timeframe)
        if should_store(prev, new_snapshot):
            # Add event type
            new_snapshot["event_type"] = get_event_type(prev, new_snapshot)
            self.save_snapshot(new_snapshot)
            logger.info(f"Stored history snapshot: {symbol}/{timeframe} - {new_snapshot['event_type']}")
            return new_snapshot

        return None


# Singleton instance
_manager_instance = None


def get_history_manager(db) -> PatternHistoryManager:
    """Get or create the history manager singleton."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PatternHistoryManager(db)
    return _manager_instance
