"""
Regime Graph Registry

PHASE 36 — Market Regime Graph Engine

MongoDB persistence layer for regime graphs.

Collections:
- market_regime_graph: Historical graph snapshots
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .graph_types import (
    RegimeGraphState,
    RegimeGraphNode,
    RegimeGraphEdge,
    RegimeGraphSummary,
    RegimeGraphPath,
)


# ══════════════════════════════════════════════════════════════
# Regime Graph Registry
# ══════════════════════════════════════════════════════════════

class RegimeGraphRegistry:
    """
    MongoDB registry for regime graphs.
    
    Provides persistence and query capabilities.
    """
    
    COLLECTION_NAME = "market_regime_graph"
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Get database connection."""
        if self._db is None:
            try:
                from core.database import get_database
                self._db = get_database()
            except Exception:
                pass
        return self._db
    
    @property
    def collection(self):
        """Get collection."""
        if self.db is None:
            return None
        return self.db[self.COLLECTION_NAME]
    
    # ═══════════════════════════════════════════════════════════
    # 1. Write Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_state(self, state: RegimeGraphState) -> bool:
        """Save regime graph state to MongoDB."""
        if self.collection is None:
            return False
        
        try:
            doc = {
                "symbol": state.symbol,
                "current_state": state.current_state,
                "previous_state": state.previous_state,
                "likely_next_state": state.likely_next_state,
                "next_state_probability": state.next_state_probability,
                "alternative_states": state.alternative_states,
                "path_confidence": state.path_confidence,
                "recent_sequence": state.recent_sequence,
                "total_transitions": state.total_transitions,
                "unique_states_visited": state.unique_states_visited,
                "reason": state.reason,
                "created_at": state.created_at,
                # Store nodes summary
                "nodes_summary": [
                    {
                        "regime_state": n.regime_state,
                        "visits": n.visits,
                        "avg_duration_minutes": n.avg_duration_minutes,
                    }
                    for n in state.nodes if n.visits > 0
                ],
                # Store edges summary
                "edges_summary": [
                    {
                        "from_state": e.from_state,
                        "to_state": e.to_state,
                        "probability": e.transition_probability,
                        "count": e.transition_count,
                    }
                    for e in state.edges[:20]  # Top 20 edges
                ],
            }
            
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"[RegimeGraphRegistry] Save error: {e}")
            return False
    
    def save_states_batch(self, states: List[RegimeGraphState]) -> int:
        """Save multiple states in batch."""
        if self.collection is None or not states:
            return 0
        
        saved = 0
        for state in states:
            if self.save_state(state):
                saved += 1
        return saved
    
    # ═══════════════════════════════════════════════════════════
    # 2. Read Operations
    # ═══════════════════════════════════════════════════════════
    
    def get_latest_state(self, symbol: str) -> Optional[Dict]:
        """Get most recent graph state for symbol."""
        if self.collection is None:
            return None
        
        try:
            doc = self.collection.find_one(
                {"symbol": symbol.upper()},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            return doc
        except Exception as e:
            print(f"[RegimeGraphRegistry] Get latest error: {e}")
            return None
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
        hours_back: Optional[int] = None,
    ) -> List[Dict]:
        """Get historical graph states."""
        if self.collection is None:
            return []
        
        try:
            query = {"symbol": symbol.upper()}
            
            if hours_back:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                query["created_at"] = {"$gte": cutoff}
            
            docs = list(self.collection.find(
                query,
                {"_id": 0}
            ).sort("created_at", -1).limit(limit))
            
            return docs
        except Exception as e:
            print(f"[RegimeGraphRegistry] Get history error: {e}")
            return []
    
    def get_by_current_state(
        self,
        symbol: str,
        current_state: str,
        limit: int = 50,
    ) -> List[Dict]:
        """Get records by current state."""
        if self.collection is None:
            return []
        
        try:
            docs = list(self.collection.find(
                {"symbol": symbol.upper(), "current_state": current_state},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit))
            
            return docs
        except Exception as e:
            print(f"[RegimeGraphRegistry] Get by state error: {e}")
            return []
    
    def get_transition_stats(self, symbol: str) -> Dict:
        """Get aggregated transition statistics."""
        if self.collection is None:
            return {}
        
        try:
            pipeline = [
                {"$match": {"symbol": symbol.upper()}},
                {"$unwind": "$edges_summary"},
                {"$group": {
                    "_id": {
                        "from": "$edges_summary.from_state",
                        "to": "$edges_summary.to_state"
                    },
                    "total_count": {"$sum": "$edges_summary.count"},
                    "avg_probability": {"$avg": "$edges_summary.probability"},
                }},
                {"$sort": {"total_count": -1}},
                {"$limit": 20}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            return {
                "symbol": symbol.upper(),
                "transitions": [
                    {
                        "from_state": r["_id"]["from"],
                        "to_state": r["_id"]["to"],
                        "total_count": r["total_count"],
                        "avg_probability": round(r["avg_probability"], 4),
                    }
                    for r in results
                ]
            }
        except Exception as e:
            print(f"[RegimeGraphRegistry] Get stats error: {e}")
            return {"symbol": symbol.upper(), "transitions": []}
    
    # ═══════════════════════════════════════════════════════════
    # 3. Aggregation Operations
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> Optional[RegimeGraphSummary]:
        """Get aggregated summary for symbol."""
        if self.collection is None:
            return None
        
        try:
            symbol = symbol.upper()
            
            # Get total count
            total = self.collection.count_documents({"symbol": symbol})
            if total == 0:
                return RegimeGraphSummary(symbol=symbol)
            
            # Get latest
            latest = self.get_latest_state(symbol)
            
            # State distribution
            pipeline = [
                {"$match": {"symbol": symbol}},
                {"$group": {
                    "_id": "$current_state",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            state_dist = list(self.collection.aggregate(pipeline))
            most_visited = state_dist[0] if state_dist else {"_id": "UNCERTAIN", "count": 0}
            
            # Transition distribution
            trans_stats = self.get_transition_stats(symbol)
            most_common_trans = trans_stats.get("transitions", [{}])[0] if trans_stats.get("transitions") else {}
            
            return RegimeGraphSummary(
                symbol=symbol,
                node_count=len(state_dist),
                edge_count=len(trans_stats.get("transitions", [])),
                most_visited_state=most_visited["_id"],
                most_visited_count=most_visited["count"],
                most_common_transition=f"{most_common_trans.get('from_state', '')} → {most_common_trans.get('to_state', '')}" if most_common_trans else "",
                most_common_transition_count=most_common_trans.get("total_count", 0),
                current_state=latest.get("current_state", "UNCERTAIN") if latest else "UNCERTAIN",
                likely_next_state=latest.get("likely_next_state", "UNCERTAIN") if latest else "UNCERTAIN",
                total_transitions=latest.get("total_transitions", 0) if latest else 0,
                last_updated=datetime.now(timezone.utc),
            )
        except Exception as e:
            print(f"[RegimeGraphRegistry] Get summary error: {e}")
            return RegimeGraphSummary(symbol=symbol)
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols with graph data."""
        if self.collection is None:
            return []
        
        try:
            return self.collection.distinct("symbol")
        except Exception:
            return []
    
    # ═══════════════════════════════════════════════════════════
    # 4. Maintenance Operations
    # ═══════════════════════════════════════════════════════════
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> int:
        """Remove records older than specified days."""
        if self.collection is None:
            return 0
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            result = self.collection.delete_many({"created_at": {"$lt": cutoff}})
            return result.deleted_count
        except Exception as e:
            print(f"[RegimeGraphRegistry] Cleanup error: {e}")
            return 0
    
    def ensure_indexes(self) -> bool:
        """Create indexes for efficient queries."""
        if self.collection is None:
            return False
        
        try:
            self.collection.create_index([("symbol", 1), ("created_at", -1)])
            self.collection.create_index([("symbol", 1), ("current_state", 1)])
            self.collection.create_index([("symbol", 1), ("likely_next_state", 1)])
            return True
        except Exception as e:
            print(f"[RegimeGraphRegistry] Index error: {e}")
            return False


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_graph_registry: Optional[RegimeGraphRegistry] = None


def get_regime_graph_registry() -> RegimeGraphRegistry:
    """Get singleton instance of RegimeGraphRegistry."""
    global _graph_registry
    if _graph_registry is None:
        _graph_registry = RegimeGraphRegistry()
    return _graph_registry
