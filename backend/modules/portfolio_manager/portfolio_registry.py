"""
Portfolio Registry

PHASE 38 — Portfolio Manager

MongoDB persistence for portfolio state and history.

Collections:
- portfolio_state: Current portfolio state
- portfolio_history: Historical snapshots for performance analysis
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from core.database import get_database

from .portfolio_types import (
    PortfolioState,
    PortfolioPosition,
    PortfolioTarget,
    PortfolioHistoryEntry,
    RebalanceResult,
)


# ══════════════════════════════════════════════════════════════
# Portfolio Registry
# ══════════════════════════════════════════════════════════════

class PortfolioRegistry:
    """
    MongoDB registry for portfolio management.
    
    Collections:
    - portfolio_state: Latest state snapshot
    - portfolio_history: Historical performance data
    - portfolio_rebalances: Rebalance events
    """
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db
    
    # ═══════════════════════════════════════════════════════════
    # Portfolio State
    # ═══════════════════════════════════════════════════════════
    
    async def save_state(self, state: PortfolioState) -> str:
        """
        Save portfolio state snapshot.
        
        Uses upsert to maintain single current state document.
        """
        if self.db is None:
            return ""
        
        # Convert to dict, excluding _id issues
        state_dict = state.model_dump()
        
        # Convert datetime to string for MongoDB
        state_dict["timestamp"] = state.timestamp.isoformat()
        
        # Convert positions and targets
        state_dict["positions"] = [
            self._position_to_dict(p) for p in state.positions
        ]
        state_dict["target_positions"] = [
            self._target_to_dict(t) for t in state.target_positions
        ]
        
        # Add metadata
        state_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Upsert - always update the single state document
        result = self.db.portfolio_state.update_one(
            {"type": "current"},
            {"$set": {**state_dict, "type": "current"}},
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        
        return "updated"
    
    async def get_state(self) -> Optional[PortfolioState]:
        """Get current portfolio state from database."""
        if self.db is None:
            return None
        
        doc = self.db.portfolio_state.find_one(
            {"type": "current"},
            {"_id": 0}
        )
        
        if not doc:
            return None
        
        return self._dict_to_state(doc)
    
    def _position_to_dict(self, position: PortfolioPosition) -> Dict:
        """Convert position to MongoDB-safe dict."""
        d = position.model_dump()
        d["opened_at"] = position.opened_at.isoformat()
        return d
    
    def _target_to_dict(self, target: PortfolioTarget) -> Dict:
        """Convert target to MongoDB-safe dict."""
        d = target.model_dump()
        d["generated_at"] = target.generated_at.isoformat()
        return d
    
    def _dict_to_state(self, doc: Dict) -> PortfolioState:
        """Convert MongoDB doc to PortfolioState."""
        # Parse timestamps
        if isinstance(doc.get("timestamp"), str):
            doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
        
        # Parse positions
        positions = []
        for p_dict in doc.get("positions", []):
            if isinstance(p_dict.get("opened_at"), str):
                p_dict["opened_at"] = datetime.fromisoformat(p_dict["opened_at"])
            positions.append(PortfolioPosition(**p_dict))
        doc["positions"] = positions
        
        # Parse targets
        targets = []
        for t_dict in doc.get("target_positions", []):
            if isinstance(t_dict.get("generated_at"), str):
                t_dict["generated_at"] = datetime.fromisoformat(t_dict["generated_at"])
            targets.append(PortfolioTarget(**t_dict))
        doc["target_positions"] = targets
        
        # Remove non-model fields
        doc.pop("type", None)
        doc.pop("updated_at", None)
        
        return PortfolioState(**doc)
    
    # ═══════════════════════════════════════════════════════════
    # Portfolio History
    # ═══════════════════════════════════════════════════════════
    
    async def save_history_entry(self, entry: PortfolioHistoryEntry) -> str:
        """Save portfolio history entry."""
        if self.db is None:
            return ""
        
        entry_dict = entry.model_dump()
        entry_dict["timestamp"] = entry.timestamp.isoformat()
        
        result = self.db.portfolio_history.insert_one(entry_dict)
        return str(result.inserted_id)
    
    async def save_history_batch(self, entries: List[PortfolioHistoryEntry]) -> int:
        """Save multiple history entries."""
        if not self.db or not entries:
            return 0
        
        docs = []
        for entry in entries:
            d = entry.model_dump()
            d["timestamp"] = entry.timestamp.isoformat()
            docs.append(d)
        
        result = self.db.portfolio_history.insert_many(docs)
        return len(result.inserted_ids)
    
    async def get_history(
        self,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[PortfolioHistoryEntry]:
        """Get portfolio history entries."""
        if self.db is None:
            return []
        
        query = {}
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date.isoformat()
            if end_date:
                query["timestamp"]["$lte"] = end_date.isoformat()
        
        cursor = self.db.portfolio_history.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        entries = []
        for doc in cursor:
            if isinstance(doc.get("timestamp"), str):
                doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
            entries.append(PortfolioHistoryEntry(**doc))
        
        return entries
    
    async def get_history_stats(
        self,
        period_days: int = 30,
    ) -> Dict:
        """Get aggregated history statistics."""
        if self.db is None:
            return {}
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff.isoformat()}}},
            {"$group": {
                "_id": None,
                "avg_risk": {"$avg": "$portfolio_risk"},
                "max_risk": {"$max": "$portfolio_risk"},
                "min_risk": {"$min": "$portfolio_risk"},
                "avg_pnl_percent": {"$avg": "$total_pnl_percent"},
                "max_pnl_percent": {"$max": "$total_pnl_percent"},
                "min_pnl_percent": {"$min": "$total_pnl_percent"},
                "avg_diversification": {"$avg": "$diversification_score"},
                "avg_correlation": {"$avg": "$avg_correlation"},
                "entry_count": {"$sum": 1},
            }},
        ]
        
        results = list(self.db.portfolio_history.aggregate(pipeline))
        
        if not results:
            return {
                "period_days": period_days,
                "entry_count": 0,
            }
        
        stats = results[0]
        stats.pop("_id", None)
        stats["period_days"] = period_days
        
        # Round values
        for key, value in stats.items():
            if isinstance(value, float):
                stats[key] = round(value, 4)
        
        return stats
    
    # ═══════════════════════════════════════════════════════════
    # Rebalance Events
    # ═══════════════════════════════════════════════════════════
    
    async def save_rebalance(self, result: RebalanceResult) -> str:
        """Save rebalance event."""
        if self.db is None:
            return ""
        
        doc = result.model_dump()
        doc["timestamp"] = result.timestamp.isoformat()
        
        insert_result = self.db.portfolio_rebalances.insert_one(doc)
        return str(insert_result.inserted_id)
    
    async def get_rebalances(
        self,
        limit: int = 50,
        triggered_only: bool = True,
    ) -> List[Dict]:
        """Get rebalance history."""
        if self.db is None:
            return []
        
        query = {}
        if triggered_only:
            query["rebalance_triggered"] = True
        
        cursor = self.db.portfolio_rebalances.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return list(cursor)
    
    # ═══════════════════════════════════════════════════════════
    # Positions (Separate collection for quick access)
    # ═══════════════════════════════════════════════════════════
    
    async def save_positions(self, positions: List[PortfolioPosition]) -> int:
        """
        Save all positions to dedicated collection.
        
        Replaces all existing positions.
        """
        if self.db is None:
            return 0
        
        # Clear existing
        self.db.portfolio_positions.delete_many({})
        
        if not positions:
            return 0
        
        docs = []
        for pos in positions:
            d = pos.model_dump()
            d["opened_at"] = pos.opened_at.isoformat()
            docs.append(d)
        
        result = self.db.portfolio_positions.insert_many(docs)
        return len(result.inserted_ids)
    
    async def get_positions(self) -> List[PortfolioPosition]:
        """Get all positions from dedicated collection."""
        if self.db is None:
            return []
        
        cursor = self.db.portfolio_positions.find({}, {"_id": 0})
        
        positions = []
        for doc in cursor:
            if isinstance(doc.get("opened_at"), str):
                doc["opened_at"] = datetime.fromisoformat(doc["opened_at"])
            positions.append(PortfolioPosition(**doc))
        
        return positions
    
    async def get_position(self, symbol: str) -> Optional[PortfolioPosition]:
        """Get specific position."""
        if self.db is None:
            return None
        
        doc = self.db.portfolio_positions.find_one(
            {"symbol": symbol.upper()},
            {"_id": 0}
        )
        
        if not doc:
            return None
        
        if isinstance(doc.get("opened_at"), str):
            doc["opened_at"] = datetime.fromisoformat(doc["opened_at"])
        
        return PortfolioPosition(**doc)
    
    # ═══════════════════════════════════════════════════════════
    # Targets (Separate collection for quick access)
    # ═══════════════════════════════════════════════════════════
    
    async def save_targets(self, targets: List[PortfolioTarget]) -> int:
        """
        Save all targets to dedicated collection.
        
        Replaces all existing targets.
        """
        if self.db is None:
            return 0
        
        # Clear existing
        self.db.portfolio_targets.delete_many({})
        
        if not targets:
            return 0
        
        docs = []
        for target in targets:
            d = target.model_dump()
            d["generated_at"] = target.generated_at.isoformat()
            docs.append(d)
        
        result = self.db.portfolio_targets.insert_many(docs)
        return len(result.inserted_ids)
    
    async def get_targets(self) -> List[PortfolioTarget]:
        """Get all targets from dedicated collection."""
        if self.db is None:
            return []
        
        cursor = self.db.portfolio_targets.find({}, {"_id": 0})
        
        targets = []
        for doc in cursor:
            if isinstance(doc.get("generated_at"), str):
                doc["generated_at"] = datetime.fromisoformat(doc["generated_at"])
            targets.append(PortfolioTarget(**doc))
        
        return targets
    
    # ═══════════════════════════════════════════════════════════
    # Cleanup
    # ═══════════════════════════════════════════════════════════
    
    async def cleanup_old_history(self, days_to_keep: int = 90) -> int:
        """Remove history entries older than specified days."""
        if self.db is None:
            return 0
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = self.db.portfolio_history.delete_many({
            "timestamp": {"$lt": cutoff.isoformat()}
        })
        
        return result.deleted_count
    
    async def cleanup_old_rebalances(self, days_to_keep: int = 90) -> int:
        """Remove old rebalance events."""
        if self.db is None:
            return 0
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = self.db.portfolio_rebalances.delete_many({
            "timestamp": {"$lt": cutoff.isoformat()}
        })
        
        return result.deleted_count


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_portfolio_registry: Optional[PortfolioRegistry] = None


def get_portfolio_registry() -> PortfolioRegistry:
    """Get singleton instance of PortfolioRegistry."""
    global _portfolio_registry
    if _portfolio_registry is None:
        _portfolio_registry = PortfolioRegistry()
    return _portfolio_registry
