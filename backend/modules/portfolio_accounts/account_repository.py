"""
Account Repository - PHASE 5.4
==============================

Persistence layer for portfolio account data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os

from pymongo import MongoClient, DESCENDING


class AccountRepository:
    """
    Repository for portfolio account data persistence.
    
    Collections:
    - portfolio_states
    - portfolio_snapshots
    - portfolio_history
    """
    
    def __init__(self):
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        self._client = MongoClient(mongo_url)
        self._db = self._client[db_name]
        
        # Collections
        self._states = self._db["portfolio_states"]
        self._snapshots = self._db["portfolio_snapshots"]
        self._history = self._db["portfolio_history"]
        
        # Ensure indexes
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create necessary indexes"""
        try:
            self._states.create_index([("timestamp", DESCENDING)])
            self._snapshots.create_index([("timestamp", DESCENDING)])
            self._snapshots.create_index([("exchange", 1)])
            self._history.create_index([("timestamp", DESCENDING)])
        except Exception as e:
            print(f"Index creation error: {e}")
    
    def save_state(self, state: Dict[str, Any]) -> str:
        """Save portfolio state"""
        doc = {
            **state,
            "timestamp": datetime.utcnow()
        }
        
        # Remove _id if present
        doc.pop("_id", None)
        
        result = self._states.insert_one(doc)
        return str(result.inserted_id)
    
    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        """Get latest portfolio state"""
        doc = self._states.find_one(
            {},
            {"_id": 0},
            sort=[("timestamp", DESCENDING)]
        )
        return doc
    
    def get_state_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get state history"""
        cursor = self._states.find(
            {},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def save_snapshot(self, exchange: str, snapshot: Dict[str, Any]) -> str:
        """Save exchange snapshot"""
        doc = {
            "exchange": exchange,
            **snapshot,
            "timestamp": datetime.utcnow()
        }
        
        doc.pop("_id", None)
        
        result = self._snapshots.insert_one(doc)
        return str(result.inserted_id)
    
    def get_exchange_snapshots(
        self,
        exchange: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get snapshots for exchange"""
        cursor = self._snapshots.find(
            {"exchange": exchange.upper()},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def save_history_entry(self, entry: Dict[str, Any]) -> str:
        """Save history entry"""
        doc = {
            **entry,
            "timestamp": datetime.utcnow()
        }
        
        doc.pop("_id", None)
        
        result = self._history.insert_one(doc)
        return str(result.inserted_id)
    
    def get_equity_history(
        self,
        days: int = 7,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get equity history"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        cursor = self._history.find(
            {"timestamp": {"$gte": cutoff}},
            {"_id": 0, "total_equity": 1, "timestamp": 1}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_pnl_history(
        self,
        days: int = 7,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get PnL history"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        cursor = self._history.find(
            {"timestamp": {"$gte": cutoff}},
            {"_id": 0, "total_pnl": 1, "unrealized_pnl": 1, "realized_pnl": 1, "timestamp": 1}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get portfolio analytics"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get states in period
        states = list(self._states.find(
            {"timestamp": {"$gte": cutoff}},
            {"_id": 0}
        ).sort("timestamp", DESCENDING))
        
        if not states:
            return {
                "period_days": days,
                "no_data": True
            }
        
        # Calculate analytics
        equities = [s.get("total_equity", 0) for s in states if "total_equity" in s]
        pnls = [s.get("total_unrealized_pnl", 0) for s in states if "total_unrealized_pnl" in s]
        
        return {
            "period_days": days,
            "snapshots_count": len(states),
            "equity": {
                "start": equities[-1] if equities else 0,
                "end": equities[0] if equities else 0,
                "min": min(equities) if equities else 0,
                "max": max(equities) if equities else 0,
                "avg": sum(equities) / len(equities) if equities else 0
            },
            "pnl": {
                "min": min(pnls) if pnls else 0,
                "max": max(pnls) if pnls else 0,
                "avg": sum(pnls) / len(pnls) if pnls else 0
            }
        }
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted = 0
        
        # Clean states (keep last 7 days)
        result = self._states.delete_many({"timestamp": {"$lt": cutoff}})
        deleted += result.deleted_count
        
        # Clean snapshots
        result = self._snapshots.delete_many({"timestamp": {"$lt": cutoff}})
        deleted += result.deleted_count
        
        # Clean history (keep last 30 days)
        result = self._history.delete_many({"timestamp": {"$lt": cutoff}})
        deleted += result.deleted_count
        
        return deleted
