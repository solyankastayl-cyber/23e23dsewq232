"""
Pattern Performance Engine — Outcome Tracking & Learning
=========================================================

Tracks pattern outcomes to enable:
1. Performance measurement (win rate)
2. Self-learning weights
3. Pattern quality scoring

Flow:
Detection → Entry → Outcome → Learning → Better Weights
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import time


def store_setup(
    pattern: Dict,
    setup: Dict,
    symbol: str,
    timeframe: str,
    current_price: float = None,
) -> Dict:
    """
    Store a new setup when Entry conditions are met.
    
    Called when:
    - Pattern is detected
    - Entry setup is generated
    - Lifecycle = confirmed_up/confirmed_down
    """
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "pattern_type": pattern.get("type", "unknown"),
        "lifecycle": pattern.get("lifecycle", "forming"),
        "bias": pattern.get("bias", "neutral"),
        "confidence": pattern.get("confidence", 0),
        
        # Entry levels
        "entry": setup.get("entry"),
        "stop": setup.get("stop"),
        "target": setup.get("target"),
        "side": setup.get("side", "LONG"),
        
        # Pattern boundaries (for breakout validation)
        "pattern_top": pattern.get("resistance") or pattern.get("breakout_level"),
        "pattern_bottom": pattern.get("support") or pattern.get("invalidation"),
        
        # Market context
        "regime": pattern.get("regime", "unknown"),
        "market_state": pattern.get("market_state", "unknown"),
        "entry_price": current_price,
        
        # Timestamps
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": time.time(),
        
        # Tracking
        "status": "active",  # active → win | loss | expired | invalidated
        "result": None,  # target_hit | stop_hit | breakout_up | breakdown | timeout
        "closed_at": None,
        "closed_price": None,
        "pnl_pct": None,
    }


def evaluate_setup(setup: Dict, current_price: float) -> Dict:
    """
    Evaluate setup outcome based on current price.
    
    Called periodically (each candle or tick).
    """
    if setup["status"] != "active":
        return setup
    
    entry = setup.get("entry")
    stop = setup.get("stop")
    target = setup.get("target")
    side = setup.get("side", "LONG")
    
    # Skip if no entry defined
    if not entry:
        return setup
    
    # LONG setup evaluation
    if side == "LONG":
        # Target hit = WIN
        if target and current_price >= target:
            setup["status"] = "win"
            setup["result"] = "target_hit"
            setup["closed_price"] = current_price
            setup["closed_at"] = datetime.now(timezone.utc).isoformat()
            if entry > 0:
                setup["pnl_pct"] = round((current_price - entry) / entry * 100, 2)
        
        # Stop hit = LOSS
        elif stop and current_price <= stop:
            setup["status"] = "loss"
            setup["result"] = "stop_hit"
            setup["closed_price"] = current_price
            setup["closed_at"] = datetime.now(timezone.utc).isoformat()
            if entry > 0:
                setup["pnl_pct"] = round((current_price - entry) / entry * 100, 2)
    
    # SHORT setup evaluation
    elif side == "SHORT":
        # Target hit = WIN (price goes down)
        if target and current_price <= target:
            setup["status"] = "win"
            setup["result"] = "target_hit"
            setup["closed_price"] = current_price
            setup["closed_at"] = datetime.now(timezone.utc).isoformat()
            if entry > 0:
                setup["pnl_pct"] = round((entry - current_price) / entry * 100, 2)
        
        # Stop hit = LOSS (price goes up)
        elif stop and current_price >= stop:
            setup["status"] = "loss"
            setup["result"] = "stop_hit"
            setup["closed_price"] = current_price
            setup["closed_at"] = datetime.now(timezone.utc).isoformat()
            if entry > 0:
                setup["pnl_pct"] = round((entry - current_price) / entry * 100, 2)
    
    return setup


def evaluate_pattern_outcome(pattern: Dict, current_price: float) -> str:
    """
    Evaluate pattern outcome (breakout direction).
    
    Used for patterns without specific entry setups.
    """
    top = pattern.get("pattern_top") or pattern.get("resistance") or pattern.get("breakout_level")
    bottom = pattern.get("pattern_bottom") or pattern.get("support") or pattern.get("invalidation")
    
    if not top or not bottom:
        return "unknown"
    
    # Price above resistance = breakout up
    if current_price > top * 1.005:  # 0.5% buffer
        return "breakout_up"
    
    # Price below support = breakdown
    if current_price < bottom * 0.995:
        return "breakdown"
    
    return "neutral"


def timeout_check(setup: Dict, max_hours: int = 48) -> Dict:
    """
    Auto-close setup if it's been active too long.
    
    Prevents stale setups from polluting statistics.
    """
    if setup["status"] != "active":
        return setup
    
    age_hours = (time.time() - setup.get("timestamp", 0)) / 3600
    
    if age_hours > max_hours:
        setup["status"] = "expired"
        setup["result"] = "timeout"
        setup["closed_at"] = datetime.now(timezone.utc).isoformat()
    
    return setup


def invalidate_setup(setup: Dict, reason: str = "pattern_invalidated") -> Dict:
    """
    Mark setup as invalidated (pattern broke before entry).
    """
    if setup["status"] != "active":
        return setup
    
    setup["status"] = "invalidated"
    setup["result"] = reason
    setup["closed_at"] = datetime.now(timezone.utc).isoformat()
    
    return setup


class PatternPerformanceTracker:
    """
    Manages setup tracking and performance calculation.
    
    Uses MongoDB for persistence.
    """
    
    def __init__(self, db):
        self.db = db
        self.collection_name = "pattern_performance"
    
    def get_collection(self):
        if self.db is None:
            return None
        return self.db[self.collection_name]
    
    def store_new_setup(
        self,
        pattern: Dict,
        setup: Dict,
        symbol: str,
        timeframe: str,
        current_price: float = None,
    ) -> Optional[str]:
        """Store new setup and return its ID."""
        collection = self.get_collection()
        if collection is None:
            return None
        
        doc = store_setup(pattern, setup, symbol, timeframe, current_price)
        
        try:
            result = collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"[Performance] Error storing setup: {e}")
            return None
    
    def get_active_setups(self, symbol: str = None) -> List[Dict]:
        """Get all active setups, optionally filtered by symbol."""
        collection = self.get_collection()
        if collection is None:
            return []
        
        query = {"status": "active"}
        if symbol:
            query["symbol"] = symbol
        
        try:
            return list(collection.find(query, {"_id": 0}))
        except Exception as e:
            print(f"[Performance] Error fetching setups: {e}")
            return []
    
    def update_setup(self, symbol: str, pattern_type: str, timestamp: float, updates: Dict):
        """Update existing setup."""
        collection = self.get_collection()
        if collection is None:
            return
        
        try:
            collection.update_one(
                {
                    "symbol": symbol,
                    "pattern_type": pattern_type,
                    "timestamp": timestamp,
                },
                {"$set": updates}
            )
        except Exception as e:
            print(f"[Performance] Error updating setup: {e}")
    
    def evaluate_all_active(self, symbol: str, current_price: float):
        """Evaluate all active setups for a symbol."""
        setups = self.get_active_setups(symbol)
        
        for setup in setups:
            # Check timeout
            setup = timeout_check(setup)
            
            # Evaluate outcome
            if setup["status"] == "active":
                setup = evaluate_setup(setup, current_price)
            
            # Update if status changed
            if setup["status"] != "active":
                self.update_setup(
                    setup["symbol"],
                    setup["pattern_type"],
                    setup["timestamp"],
                    {
                        "status": setup["status"],
                        "result": setup["result"],
                        "closed_at": setup.get("closed_at"),
                        "closed_price": setup.get("closed_price"),
                        "pnl_pct": setup.get("pnl_pct"),
                    }
                )
    
    def get_performance_stats(
        self,
        symbol: str = None,
        pattern_type: str = None,
        timeframe: str = None,
        regime: str = None,
        limit: int = 100,
    ) -> Dict:
        """
        Get aggregated performance statistics.
        
        Returns:
            {
                "total": 50,
                "wins": 32,
                "losses": 15,
                "expired": 3,
                "win_rate": 68,
                "avg_pnl": 2.3,
                "by_pattern": {...}
            }
        """
        collection = self.get_collection()
        if collection is None:
            return {"total": 0, "win_rate": 50}
        
        # Build query
        query = {"status": {"$in": ["win", "loss", "expired"]}}
        if symbol:
            query["symbol"] = symbol
        if pattern_type:
            query["pattern_type"] = pattern_type
        if timeframe:
            query["timeframe"] = timeframe
        if regime:
            query["regime"] = regime
        
        try:
            setups = list(collection.find(query, {"_id": 0}).limit(limit))
        except Exception as e:
            print(f"[Performance] Error fetching stats: {e}")
            return {"total": 0, "win_rate": 50}
        
        if not setups:
            return {"total": 0, "win_rate": 50}
        
        # Calculate stats
        total = len(setups)
        wins = sum(1 for s in setups if s.get("status") == "win")
        losses = sum(1 for s in setups if s.get("status") == "loss")
        expired = sum(1 for s in setups if s.get("status") == "expired")
        
        pnls = [s.get("pnl_pct", 0) for s in setups if s.get("pnl_pct") is not None]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        
        # Group by pattern type
        by_pattern = {}
        for s in setups:
            pt = s.get("pattern_type", "unknown")
            if pt not in by_pattern:
                by_pattern[pt] = {"wins": 0, "total": 0}
            by_pattern[pt]["total"] += 1
            if s.get("status") == "win":
                by_pattern[pt]["wins"] += 1
        
        # Calculate winrate per pattern
        for pt in by_pattern:
            w = by_pattern[pt]["wins"]
            t = by_pattern[pt]["total"]
            by_pattern[pt]["win_rate"] = round(w / t * 100) if t > 0 else 50
        
        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "expired": expired,
            "win_rate": round(wins / total * 100) if total > 0 else 50,
            "avg_pnl": round(avg_pnl, 2),
            "by_pattern": by_pattern,
        }


# Singleton instance
_tracker_instance = None


def get_performance_tracker(db=None):
    """Get singleton performance tracker instance."""
    global _tracker_instance
    if _tracker_instance is None and db is not None:
        _tracker_instance = PatternPerformanceTracker(db)
    return _tracker_instance


__all__ = [
    "store_setup",
    "evaluate_setup",
    "evaluate_pattern_outcome",
    "timeout_check",
    "invalidate_setup",
    "PatternPerformanceTracker",
    "get_performance_tracker",
]
