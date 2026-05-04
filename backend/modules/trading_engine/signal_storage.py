"""
Signal Storage — MongoDB Persistence for Trading Signals

Collections:
- trading_signals: Signal history and tracking
- signal_alerts: Alert queue
- signal_performance: Aggregated performance metrics

Provides:
- Signal CRUD operations
- Status tracking
- Performance analytics
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
import os

from .signal_engine import (
    TradingSignal,
    SignalAlert,
    SignalStatus,
    SignalDirection,
)


# ═══════════════════════════════════════════════════════════════
# Signal Storage Service
# ═══════════════════════════════════════════════════════════════

class SignalStorageService:
    """
    MongoDB storage for trading signals.
    """
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db = None
        self._signals_collection: Optional[Collection] = None
        self._alerts_collection: Optional[Collection] = None
    
    def _get_db(self):
        """Get MongoDB database connection."""
        if self._db is None:
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "ta_engine")
            self._client = MongoClient(mongo_url)
            self._db = self._client[db_name]
            self._signals_collection = self._db["trading_signals"]
            self._alerts_collection = self._db["signal_alerts"]
            
            # Create indexes
            self._signals_collection.create_index([("symbol", 1), ("status", 1)])
            self._signals_collection.create_index([("created_at", DESCENDING)])
            self._signals_collection.create_index([("signal_id", 1)], unique=True)
            
            self._alerts_collection.create_index([("created_at", DESCENDING)])
            self._alerts_collection.create_index([("read", 1)])
        
        return self._db
    
    # ═══════════════════════════════════════════════════════════════
    # Signal Operations
    # ═══════════════════════════════════════════════════════════════
    
    def save_signal(self, signal: TradingSignal) -> str:
        """Save or update a trading signal."""
        self._get_db()
        
        doc = signal.model_dump()
        
        # Convert enums to strings
        doc["direction"] = signal.direction.value
        doc["strength"] = signal.strength.value
        doc["status"] = signal.status.value
        
        # Convert take_profit
        doc["take_profit"] = [tp.model_dump() for tp in signal.take_profit]
        
        self._signals_collection.update_one(
            {"signal_id": signal.signal_id},
            {"$set": doc},
            upsert=True
        )
        
        return signal.signal_id
    
    def get_signal(self, signal_id: str) -> Optional[TradingSignal]:
        """Get signal by ID."""
        self._get_db()
        
        doc = self._signals_collection.find_one({"signal_id": signal_id})
        if not doc:
            return None
        
        return self._doc_to_signal(doc)
    
    def get_signals(
        self,
        symbol: Optional[str] = None,
        status: Optional[SignalStatus] = None,
        direction: Optional[SignalDirection] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[TradingSignal]:
        """Get signals with filters."""
        self._get_db()
        
        query = {}
        if symbol:
            query["symbol"] = symbol.upper()
        if status:
            query["status"] = status.value
        if direction:
            query["direction"] = direction.value
        
        cursor = self._signals_collection.find(query).sort(
            "created_at", DESCENDING
        ).skip(skip).limit(limit)
        
        return [self._doc_to_signal(doc) for doc in cursor]
    
    def get_active_signals(self, symbol: Optional[str] = None) -> List[TradingSignal]:
        """Get all active (non-closed) signals."""
        self._get_db()
        
        query = {
            "status": {"$in": [
                SignalStatus.PENDING.value,
                SignalStatus.ACTIVE.value,
                SignalStatus.TP1_HIT.value,
                SignalStatus.TP2_HIT.value,
            ]}
        }
        if symbol:
            query["symbol"] = symbol.upper()
        
        cursor = self._signals_collection.find(query).sort("created_at", DESCENDING)
        
        return [self._doc_to_signal(doc) for doc in cursor]
    
    def update_signal_status(
        self,
        signal_id: str,
        status: SignalStatus,
        exit_price: Optional[float] = None,
        exit_reason: Optional[str] = None,
        pnl_pct: Optional[float] = None,
    ) -> bool:
        """Update signal status."""
        self._get_db()
        
        update = {
            "$set": {
                "status": status.value,
                "closed_at": datetime.now(timezone.utc).isoformat() if status in [
                    SignalStatus.TP3_HIT, SignalStatus.SL_HIT, 
                    SignalStatus.EXPIRED, SignalStatus.CANCELLED
                ] else None,
            }
        }
        
        if exit_price is not None:
            update["$set"]["exit_price"] = exit_price
        if exit_reason is not None:
            update["$set"]["exit_reason"] = exit_reason
        if pnl_pct is not None:
            update["$set"]["pnl_pct"] = pnl_pct
        
        result = self._signals_collection.update_one(
            {"signal_id": signal_id},
            update
        )
        
        return result.modified_count > 0
    
    def delete_signal(self, signal_id: str) -> bool:
        """Delete a signal."""
        self._get_db()
        result = self._signals_collection.delete_one({"signal_id": signal_id})
        return result.deleted_count > 0
    
    # ═══════════════════════════════════════════════════════════════
    # Alert Operations
    # ═══════════════════════════════════════════════════════════════
    
    def save_alert(self, alert: SignalAlert) -> str:
        """Save an alert."""
        self._get_db()
        
        doc = alert.model_dump()
        self._alerts_collection.insert_one(doc)
        
        return alert.alert_id
    
    def get_alerts(
        self,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[SignalAlert]:
        """Get alerts."""
        self._get_db()
        
        query = {}
        if unread_only:
            query["read"] = False
        
        cursor = self._alerts_collection.find(query).sort(
            "created_at", DESCENDING
        ).limit(limit)
        
        alerts = []
        for doc in cursor:
            doc.pop("_id", None)
            alerts.append(SignalAlert(**doc))
        
        return alerts
    
    def mark_alerts_read(self, alert_ids: List[str]) -> int:
        """Mark alerts as read."""
        self._get_db()
        
        result = self._alerts_collection.update_many(
            {"alert_id": {"$in": alert_ids}},
            {"$set": {"read": True}}
        )
        
        return result.modified_count
    
    def clear_old_alerts(self, days: int = 7) -> int:
        """Clear alerts older than specified days."""
        self._get_db()
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = self._alerts_collection.delete_many({
            "created_at": {"$lt": cutoff.isoformat()}
        })
        
        return result.deleted_count
    
    # ═══════════════════════════════════════════════════════════════
    # Performance Analytics
    # ═══════════════════════════════════════════════════════════════
    
    def get_signal_stats(
        self,
        symbol: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get signal performance statistics."""
        self._get_db()
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = {"created_at": {"$gte": cutoff.isoformat()}}
        if symbol:
            query["symbol"] = symbol.upper()
        
        signals = list(self._signals_collection.find(query))
        
        if not signals:
            return {
                "total_signals": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "by_status": {},
                "by_direction": {},
            }
        
        # Count by status
        status_counts = {}
        direction_counts = {"long": 0, "short": 0}
        wins = 0
        losses = 0
        total_pnl = 0
        closed_count = 0
        
        for sig in signals:
            status = sig.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            direction = sig.get("direction", "long")
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
            
            pnl = sig.get("pnl_pct")
            if pnl is not None:
                closed_count += 1
                total_pnl += pnl
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
        
        win_rate = wins / closed_count if closed_count > 0 else 0
        avg_pnl = total_pnl / closed_count if closed_count > 0 else 0
        
        return {
            "total_signals": len(signals),
            "closed_signals": closed_count,
            "win_rate": round(win_rate, 3),
            "avg_pnl": round(avg_pnl, 4),
            "total_wins": wins,
            "total_losses": losses,
            "by_status": status_counts,
            "by_direction": direction_counts,
            "period_days": days,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════
    
    def _doc_to_signal(self, doc: Dict) -> TradingSignal:
        """Convert MongoDB document to TradingSignal."""
        doc.pop("_id", None)
        
        # Convert string enums back
        doc["direction"] = SignalDirection(doc.get("direction", "long"))
        doc["status"] = SignalStatus(doc.get("status", "pending"))
        
        # Handle strength
        from .signal_engine import SignalStrength
        strength_val = doc.get("strength", "medium")
        if isinstance(strength_val, str):
            doc["strength"] = SignalStrength(strength_val)
        
        return TradingSignal(**doc)


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_storage_service: Optional[SignalStorageService] = None

def get_signal_storage() -> SignalStorageService:
    """Get singleton instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = SignalStorageService()
    return _storage_service
