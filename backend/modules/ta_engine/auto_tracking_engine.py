"""
Auto-Tracking Engine — Automatic Setup Recording
=================================================

Automatically records confirmed setups for performance learning.

ONLY tracks when:
1. Pattern lifecycle = confirmed_up OR confirmed_down
2. Confidence > threshold (default 0.40)
3. Valid entry/stop/target levels exist
4. Setup not already tracked (dedupe)

Dedupe key:
  symbol + timeframe + pattern_type + lifecycle + breakout_level + timestamp_bucket

This feeds the self-learning weights system with real outcomes.
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone
import time
import hashlib


# Configuration
AUTO_TRACK_CONFIG = {
    "min_confidence": 0.40,
    "require_levels": True,  # Require valid entry/stop/target
    "timestamp_bucket_hours": 4,  # Group events within 4h window
    "allowed_lifecycles": ["confirmed_up", "confirmed_down"],
    "exclude_ghost": True,
}


def generate_dedupe_key(
    symbol: str,
    timeframe: str,
    pattern_type: str,
    lifecycle: str,
    breakout_level: float,
    timestamp: float,
    bucket_hours: int = 4,
) -> str:
    """
    Generate dedupe key for setup tracking.
    
    Uses timestamp bucket to prevent duplicate tracking
    of the same pattern confirmation.
    """
    # Round timestamp to bucket
    bucket_size = bucket_hours * 3600
    timestamp_bucket = int(timestamp // bucket_size) * bucket_size
    
    # Round breakout level to reduce noise
    breakout_rounded = round(breakout_level, -1) if breakout_level else 0
    
    # Create key string
    key_string = f"{symbol}|{timeframe}|{pattern_type}|{lifecycle}|{breakout_rounded}|{timestamp_bucket}"
    
    # Hash for shorter storage
    return hashlib.md5(key_string.encode()).hexdigest()[:16]


def should_auto_track(
    pattern: Dict,
    setup: Dict = None,
    config: Dict = None,
) -> tuple[bool, str]:
    """
    Determine if setup should be auto-tracked.
    
    Returns:
        (should_track: bool, reason: str)
    """
    cfg = config or AUTO_TRACK_CONFIG
    
    if not pattern:
        return False, "no_pattern"
    
    lifecycle = pattern.get("lifecycle", "forming")
    
    # Check lifecycle
    if lifecycle not in cfg.get("allowed_lifecycles", []):
        return False, f"lifecycle_not_allowed:{lifecycle}"
    
    # Check confidence
    confidence = pattern.get("confidence", 0)
    min_conf = cfg.get("min_confidence", 0.40)
    if confidence < min_conf:
        return False, f"confidence_too_low:{confidence}<{min_conf}"
    
    # Check ghost patterns
    if cfg.get("exclude_ghost", True):
        if pattern.get("is_ghost") or pattern.get("ghost"):
            return False, "ghost_pattern"
    
    # Check levels (if required)
    if cfg.get("require_levels", True) and setup:
        entry = setup.get("entry")
        stop = setup.get("stop")
        target = setup.get("target")
        
        if not entry or not stop or not target:
            return False, "missing_levels"
        
        # Validate levels make sense
        if entry <= 0 or stop <= 0 or target <= 0:
            return False, "invalid_levels"
    
    return True, "ok"


def extract_setup_from_pattern(pattern: Dict, current_price: float = None) -> Dict:
    """
    Extract tradeable setup from pattern data.
    
    Derives entry/stop/target from pattern boundaries if not provided.
    """
    lifecycle = pattern.get("lifecycle", "forming")
    
    # Get levels from pattern
    breakout_level = pattern.get("breakout_level") or pattern.get("resistance")
    invalidation = pattern.get("invalidation") or pattern.get("support")
    
    # Try boundaries (V4 format)
    if not breakout_level or not invalidation:
        boundaries = pattern.get("boundaries", [])
        for b in boundaries:
            bid = b.get("id", "")
            if "upper" in bid and not breakout_level:
                breakout_level = b.get("y2") or b.get("y1")
            if "lower" in bid and not invalidation:
                invalidation = b.get("y2") or b.get("y1")
    
    if not breakout_level or not invalidation:
        return {}
    
    # Determine side and levels based on lifecycle
    if lifecycle == "confirmed_up":
        # Long setup
        entry = breakout_level
        stop = invalidation
        range_size = entry - stop
        target = entry + (range_size * 2)  # 1:2 R:R
        side = "LONG"
    elif lifecycle == "confirmed_down":
        # Short setup
        entry = invalidation
        stop = breakout_level
        range_size = stop - entry
        target = entry - (range_size * 2)  # 1:2 R:R
        side = "SHORT"
    else:
        return {}
    
    # Calculate R:R
    risk = abs(entry - stop)
    reward = abs(target - entry)
    rr_ratio = round(reward / risk, 1) if risk > 0 else 0
    
    return {
        "entry": entry,
        "stop": stop,
        "target": target,
        "side": side,
        "rr_ratio": rr_ratio,
        "entry_type": "breakout",
    }


class AutoTracker:
    """
    Manages automatic setup tracking.
    
    Integrates with PerTF builder to automatically record
    confirmed setups for performance learning.
    """
    
    def __init__(self, db):
        self.db = db
        self.collection_name = "pattern_performance"
        self.dedupe_collection = "auto_track_dedupe"
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Ensure necessary indexes exist."""
        if self.db is None:
            return
        
        try:
            # Dedupe index
            self.db[self.dedupe_collection].create_index("dedupe_key", unique=True)
            
            # Performance indexes
            self.db[self.collection_name].create_index([
                ("symbol", 1),
                ("status", 1),
            ])
            self.db[self.collection_name].create_index([
                ("pattern_type", 1),
                ("status", 1),
            ])
        except Exception as e:
            print(f"[AutoTracker] Index creation error: {e}")
    
    def get_collection(self):
        if self.db is None:
            return None
        return self.db[self.collection_name]
    
    def is_duplicate(self, dedupe_key: str) -> bool:
        """Check if this setup was already tracked."""
        if self.db is None:
            return False
        
        try:
            result = self.db[self.dedupe_collection].find_one({"dedupe_key": dedupe_key})
            return result is not None
        except Exception as e:
            print(f"[AutoTracker] Dedupe check error: {e}")
            return False
    
    def mark_tracked(self, dedupe_key: str, setup_id: str):
        """Mark setup as tracked (insert dedupe record)."""
        if self.db is None:
            return
        
        try:
            self.db[self.dedupe_collection].insert_one({
                "dedupe_key": dedupe_key,
                "setup_id": setup_id,
                "tracked_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            # Duplicate key is expected if concurrent
            if "duplicate key" not in str(e).lower():
                print(f"[AutoTracker] Mark tracked error: {e}")
    
    def track_confirmed_pattern(
        self,
        symbol: str,
        timeframe: str,
        pattern: Dict,
        current_price: float = None,
        market_state: str = None,
    ) -> Optional[str]:
        """
        Auto-track a confirmed pattern.
        
        Returns setup_id if tracked, None otherwise.
        """
        if self.db is None:
            return None
        
        # Extract setup from pattern
        setup = extract_setup_from_pattern(pattern, current_price)
        
        # Check if should track
        should_track, reason = should_auto_track(pattern, setup)
        
        if not should_track:
            return None
        
        # Generate dedupe key
        breakout_level = setup.get("entry") or pattern.get("breakout_level", 0)
        dedupe_key = generate_dedupe_key(
            symbol=symbol,
            timeframe=timeframe,
            pattern_type=pattern.get("type", "unknown"),
            lifecycle=pattern.get("lifecycle", "unknown"),
            breakout_level=breakout_level,
            timestamp=time.time(),
        )
        
        # Check dedupe
        if self.is_duplicate(dedupe_key):
            return None
        
        # Build setup document
        from modules.ta_engine.pattern_performance_engine import store_setup
        
        setup_doc = store_setup(
            pattern=pattern,
            setup=setup,
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
        )
        
        # Add auto-track metadata
        setup_doc["auto_tracked"] = True
        setup_doc["dedupe_key"] = dedupe_key
        setup_doc["market_state"] = market_state
        setup_doc["regime"] = market_state.lower() if market_state else "unknown"
        
        # Store
        try:
            collection = self.get_collection()
            result = collection.insert_one(setup_doc)
            setup_id = str(result.inserted_id)
            
            # Mark as tracked
            self.mark_tracked(dedupe_key, setup_id)
            
            print(f"[AutoTracker] Tracked: {symbol}/{timeframe} {pattern.get('type')} {pattern.get('lifecycle')}")
            
            return setup_id
            
        except Exception as e:
            print(f"[AutoTracker] Store error: {e}")
            return None
    
    def get_auto_tracked_count(self, symbol: str = None) -> int:
        """Get count of auto-tracked setups."""
        if self.db is None:
            return 0
        
        try:
            query = {"auto_tracked": True}
            if symbol:
                query["symbol"] = symbol
            
            return self.db[self.collection_name].count_documents(query)
        except Exception as e:
            print(f"[AutoTracker] Count error: {e}")
            return 0
    
    def get_recent_auto_tracked(self, limit: int = 10) -> List[Dict]:
        """Get recently auto-tracked setups."""
        if self.db is None:
            return []
        
        try:
            return list(
                self.db[self.collection_name]
                .find({"auto_tracked": True}, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
        except Exception as e:
            print(f"[AutoTracker] Fetch error: {e}")
            return []


# Singleton instance
_auto_tracker_instance = None


def get_auto_tracker(db=None):
    """Get singleton auto-tracker instance."""
    global _auto_tracker_instance
    if _auto_tracker_instance is None and db is not None:
        _auto_tracker_instance = AutoTracker(db)
    return _auto_tracker_instance


def auto_track_if_confirmed(
    symbol: str,
    timeframe: str,
    pattern: Dict,
    current_price: float = None,
    market_state: str = None,
    db=None,
) -> Optional[str]:
    """
    Convenience function to auto-track if pattern is confirmed.
    
    Can be called directly from per_tf_builder.
    """
    if not pattern:
        return None
    
    lifecycle = pattern.get("lifecycle", "forming")
    
    # Only track confirmed patterns
    if lifecycle not in ["confirmed_up", "confirmed_down"]:
        return None
    
    # Get tracker
    tracker = get_auto_tracker(db)
    if not tracker and db:
        tracker = AutoTracker(db)
        global _auto_tracker_instance
        _auto_tracker_instance = tracker
    
    if not tracker:
        return None
    
    return tracker.track_confirmed_pattern(
        symbol=symbol,
        timeframe=timeframe,
        pattern=pattern,
        current_price=current_price,
        market_state=market_state,
    )


__all__ = [
    "AUTO_TRACK_CONFIG",
    "generate_dedupe_key",
    "should_auto_track",
    "extract_setup_from_pattern",
    "AutoTracker",
    "get_auto_tracker",
    "auto_track_if_confirmed",
]
