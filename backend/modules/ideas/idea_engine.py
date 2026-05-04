"""
Idea Timeline Engine — History of Trading Thinking
===================================================

This is NOT another engine - this is THE PRODUCT LAYER.

Key concept:
- Idea = snapshot of analysis at a point in time
- Ideas evolve: V1 → V2 → V3
- System auto-evaluates outcomes
- User sees their thinking history + accuracy

Like TradingView Ideas, but automated.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import time
import uuid


def generate_idea_id() -> str:
    """Generate unique idea ID."""
    return str(uuid.uuid4())[:12]


def build_snapshot(
    pattern: Dict,
    context: Dict,
    watch_levels: List[Dict] = None,
    intelligence: Dict = None,
) -> Dict:
    """
    Build idea snapshot from current analysis.
    
    Captures:
    - Pattern type, lifecycle, confidence
    - Probability (up/down)
    - Key levels (top/bottom)
    - Market state
    """
    # Extract levels from watch_levels or pattern
    levels = {"top": None, "bottom": None}
    
    if watch_levels:
        for lvl in watch_levels:
            lvl_type = lvl.get("type", "")
            if "breakout" in lvl_type or "resistance" in lvl_type or "upper" in lvl_type:
                levels["top"] = lvl.get("price")
            if "breakdown" in lvl_type or "support" in lvl_type or "lower" in lvl_type:
                levels["bottom"] = lvl.get("price")
    
    # Fallback to pattern boundaries
    if not levels["top"] or not levels["bottom"]:
        boundaries = pattern.get("boundaries", [])
        for b in boundaries:
            bid = b.get("id", "")
            if "upper" in bid:
                levels["top"] = levels["top"] or b.get("y2") or b.get("y1")
            if "lower" in bid:
                levels["bottom"] = levels["bottom"] or b.get("y2") or b.get("y1")
    
    # Get probability
    prob = intelligence.get("live_probability", {}) if intelligence else {}
    if not prob:
        prob = intelligence.get("probabilities", {}) if intelligence else {}
    
    return {
        "pattern": pattern.get("type", "unknown"),
        "lifecycle": pattern.get("lifecycle", "forming"),
        "confidence": round(pattern.get("confidence", 0), 2),
        "bias": pattern.get("bias", "neutral"),
        "probability": {
            "up": round(prob.get("breakout_up", 0.5), 2),
            "down": round(prob.get("breakdown", 0.5), 2),
        },
        "levels": levels,
        "market_state": context.get("market_state", "unknown"),
        "geometry": pattern.get("boundaries", []),  # For rendering
    }


def create_idea(
    symbol: str,
    timeframe: str,
    pattern: Dict,
    context: Dict,
    watch_levels: List[Dict] = None,
    intelligence: Dict = None,
    user_id: str = None,
    horizon_days: int = 7,
    notes: str = None,
) -> Dict:
    """
    Create a new idea with initial snapshot.
    
    This is called when user clicks "Save Idea".
    """
    snapshot = build_snapshot(pattern, context, watch_levels, intelligence)
    
    return {
        "id": generate_idea_id(),
        "user_id": user_id or "anonymous",
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": time.time(),
        "horizon_days": horizon_days,
        "expires_at": time.time() + (horizon_days * 86400),
        
        "versions": [
            {
                "v": 1,
                "timestamp": time.time(),
                "snapshot": snapshot,
            }
        ],
        
        "status": "active",  # active | success_up | success_down | expired | invalidated
        "outcome": None,
        "outcome_at": None,
        "outcome_price": None,
        
        "score": 0,  # +1 correct, -1 wrong, 0 neutral
        "notes": notes,
        
        "auto_update": True,  # Auto-create new versions
    }


def evaluate_idea(idea: Dict, current_price: float) -> Dict:
    """
    Evaluate idea outcome based on current price.
    
    Returns updated idea with outcome if conditions met.
    """
    if idea["status"] != "active":
        return idea
    
    latest = idea["versions"][-1]["snapshot"]
    top = latest["levels"].get("top")
    bottom = latest["levels"].get("bottom")
    
    if not top or not bottom:
        return idea
    
    # Check breakout
    if current_price > top * 1.005:  # 0.5% buffer
        idea["status"] = "success_up"
        idea["outcome"] = "breakout_up"
        idea["outcome_at"] = datetime.now(timezone.utc).isoformat()
        idea["outcome_price"] = current_price
        idea["score"] = 1 if latest["bias"] == "bullish" else -1
    
    # Check breakdown
    elif current_price < bottom * 0.995:
        idea["status"] = "success_down"
        idea["outcome"] = "breakdown"
        idea["outcome_at"] = datetime.now(timezone.utc).isoformat()
        idea["outcome_price"] = current_price
        idea["score"] = 1 if latest["bias"] == "bearish" else -1
    
    return idea


def is_expired(idea: Dict) -> bool:
    """Check if idea has expired (past horizon)."""
    return time.time() > idea.get("expires_at", 0)


def expire_idea(idea: Dict) -> Dict:
    """Mark idea as expired."""
    if idea["status"] != "active":
        return idea
    
    idea["status"] = "expired"
    idea["outcome"] = "timeout"
    idea["outcome_at"] = datetime.now(timezone.utc).isoformat()
    idea["score"] = 0
    
    return idea


def add_version(
    idea: Dict,
    pattern: Dict,
    context: Dict,
    watch_levels: List[Dict] = None,
    intelligence: Dict = None,
) -> Dict:
    """
    Add new version to idea (evolution).
    
    Called when:
    - Auto-update triggered (horizon passed)
    - User clicks "Update Idea"
    """
    snapshot = build_snapshot(pattern, context, watch_levels, intelligence)
    
    new_version = {
        "v": len(idea["versions"]) + 1,
        "timestamp": time.time(),
        "snapshot": snapshot,
    }
    
    idea["versions"].append(new_version)
    
    # Reset expiration
    idea["expires_at"] = time.time() + (idea["horizon_days"] * 86400)
    
    # Compare direction
    old_bias = idea["versions"][-2]["snapshot"]["bias"]
    new_bias = snapshot["bias"]
    
    if old_bias == new_bias:
        idea["continuation"] = True
    else:
        idea["continuation"] = False
    
    return idea


def compare_versions(old_snapshot: Dict, new_snapshot: Dict) -> str:
    """
    Compare two versions to determine evolution.
    
    Returns: 'continuation' | 'reversal' | 'same'
    """
    old_bias = old_snapshot.get("bias", "neutral")
    new_bias = new_snapshot.get("bias", "neutral")
    old_pattern = old_snapshot.get("pattern", "")
    new_pattern = new_snapshot.get("pattern", "")
    
    if old_pattern == new_pattern and old_bias == new_bias:
        return "same"
    
    if old_bias == new_bias:
        return "continuation"
    
    return "reversal"


def compute_accuracy(ideas: List[Dict]) -> Dict:
    """
    Compute accuracy statistics from ideas.
    
    Returns:
    {
        "total": 50,
        "wins": 32,
        "losses": 10,
        "neutral": 8,
        "accuracy": 76,  # wins / (wins + losses)
        "streak": 3,  # current streak
    }
    """
    wins = sum(1 for i in ideas if i.get("score", 0) > 0)
    losses = sum(1 for i in ideas if i.get("score", 0) < 0)
    neutral = sum(1 for i in ideas if i.get("score", 0) == 0 and i.get("status") != "active")
    total = len(ideas)
    
    decided = wins + losses
    accuracy = round(wins / decided * 100) if decided > 0 else 0
    
    # Calculate streak
    streak = 0
    streak_type = None
    
    # Sort by outcome time (most recent first)
    sorted_ideas = sorted(
        [i for i in ideas if i.get("outcome_at")],
        key=lambda x: x.get("outcome_at", ""),
        reverse=True
    )
    
    for idea in sorted_ideas:
        score = idea.get("score", 0)
        if score == 0:
            continue
        
        if streak_type is None:
            streak_type = "win" if score > 0 else "loss"
            streak = 1
        elif (streak_type == "win" and score > 0) or (streak_type == "loss" and score < 0):
            streak += 1
        else:
            break
    
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "neutral": neutral,
        "accuracy": accuracy,
        "streak": streak,
        "streak_type": streak_type or "none",
    }


class IdeaManager:
    """
    Manages idea lifecycle with MongoDB persistence.
    """
    
    def __init__(self, db):
        self.db = db
        self.collection_name = "ideas"
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create necessary indexes."""
        if self.db is None:
            return
        
        try:
            self.db[self.collection_name].create_index([
                ("user_id", 1),
                ("status", 1),
            ])
            self.db[self.collection_name].create_index([
                ("symbol", 1),
                ("timeframe", 1),
            ])
            self.db[self.collection_name].create_index("timestamp")
        except Exception as e:
            print(f"[IdeaManager] Index error: {e}")
    
    def create(
        self,
        symbol: str,
        timeframe: str,
        pattern: Dict,
        context: Dict,
        watch_levels: List[Dict] = None,
        intelligence: Dict = None,
        user_id: str = None,
        horizon_days: int = 7,
    ) -> Optional[Dict]:
        """Create and store new idea."""
        if self.db is None:
            return None
        
        idea = create_idea(
            symbol=symbol,
            timeframe=timeframe,
            pattern=pattern,
            context=context,
            watch_levels=watch_levels,
            intelligence=intelligence,
            user_id=user_id,
            horizon_days=horizon_days,
        )
        
        try:
            self.db[self.collection_name].insert_one(idea)
            # Remove _id for JSON serialization
            idea.pop("_id", None)
            return idea
        except Exception as e:
            print(f"[IdeaManager] Create error: {e}")
            return None
    
    def get(self, idea_id: str) -> Optional[Dict]:
        """Get idea by ID."""
        if self.db is None:
            return None
        
        try:
            return self.db[self.collection_name].find_one(
                {"id": idea_id},
                {"_id": 0}
            )
        except Exception as e:
            print(f"[IdeaManager] Get error: {e}")
            return None
    
    def get_user_ideas(
        self,
        user_id: str,
        status: str = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Get ideas for a user."""
        if self.db is None:
            return []
        
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        try:
            return list(
                self.db[self.collection_name]
                .find(query, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
        except Exception as e:
            print(f"[IdeaManager] Get user ideas error: {e}")
            return []
    
    def get_active(self, symbol: str = None) -> List[Dict]:
        """Get all active ideas."""
        if self.db is None:
            return []
        
        query = {"status": "active"}
        if symbol:
            query["symbol"] = symbol.upper()
        
        try:
            return list(
                self.db[self.collection_name]
                .find(query, {"_id": 0})
            )
        except Exception as e:
            print(f"[IdeaManager] Get active error: {e}")
            return []
    
    def update(self, idea_id: str, updates: Dict):
        """Update idea."""
        if self.db is None:
            return
        
        try:
            self.db[self.collection_name].update_one(
                {"id": idea_id},
                {"$set": updates}
            )
        except Exception as e:
            print(f"[IdeaManager] Update error: {e}")
    
    def evaluate_all_active(self, current_prices: Dict[str, float]):
        """
        Evaluate all active ideas against current prices.
        
        Args:
            current_prices: {"BTCUSDT": 68500, "ETHUSDT": 3500, ...}
        """
        ideas = self.get_active()
        
        for idea in ideas:
            symbol = idea["symbol"]
            price = current_prices.get(symbol)
            
            if not price:
                continue
            
            # Check expiration
            if is_expired(idea):
                idea = expire_idea(idea)
                self.update(idea["id"], {
                    "status": idea["status"],
                    "outcome": idea["outcome"],
                    "outcome_at": idea["outcome_at"],
                    "score": idea["score"],
                })
                continue
            
            # Evaluate outcome
            updated = evaluate_idea(idea, price)
            
            if updated["status"] != "active":
                self.update(idea["id"], {
                    "status": updated["status"],
                    "outcome": updated["outcome"],
                    "outcome_at": updated["outcome_at"],
                    "outcome_price": updated["outcome_price"],
                    "score": updated["score"],
                })
    
    def add_version(
        self,
        idea_id: str,
        pattern: Dict,
        context: Dict,
        watch_levels: List[Dict] = None,
        intelligence: Dict = None,
    ) -> Optional[Dict]:
        """Add new version to existing idea."""
        idea = self.get(idea_id)
        if not idea:
            return None
        
        updated = add_version(idea, pattern, context, watch_levels, intelligence)
        
        self.update(idea_id, {
            "versions": updated["versions"],
            "expires_at": updated["expires_at"],
            "continuation": updated.get("continuation"),
        })
        
        return updated
    
    def get_accuracy(self, user_id: str) -> Dict:
        """Get accuracy stats for user."""
        ideas = self.get_user_ideas(user_id, limit=100)
        return compute_accuracy(ideas)


# Singleton
_idea_manager = None


def get_idea_manager(db=None):
    """Get singleton idea manager."""
    global _idea_manager
    if _idea_manager is None and db is not None:
        _idea_manager = IdeaManager(db)
    return _idea_manager


__all__ = [
    "generate_idea_id",
    "build_snapshot",
    "create_idea",
    "evaluate_idea",
    "is_expired",
    "expire_idea",
    "add_version",
    "compare_versions",
    "compute_accuracy",
    "IdeaManager",
    "get_idea_manager",
]
