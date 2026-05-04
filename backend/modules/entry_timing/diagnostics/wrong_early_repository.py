"""
PHASE 4.1 — Wrong Early Repository

Stores classified wrong early cases for aggregation and analysis.
Supports both in-memory and MongoDB storage.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict


@dataclass
class WrongEarlyRecord:
    """A single wrong early record."""
    id: str
    symbol: str
    timeframe: str
    direction: str
    execution_type: str
    reason: str
    confidence: float
    severity: str
    details: Dict
    pnl: float
    classified_at: str
    trade_timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class WrongEarlyRepository:
    """
    Repository for wrong early classifications.
    
    Supports:
    - In-memory storage (default)
    - MongoDB storage (when db available)
    """
    
    def __init__(self, use_mongo: bool = True):
        self._records: List[Dict] = []
        self._use_mongo = use_mongo
        self._db = None
        self._collection = None
        
        if use_mongo:
            self._init_mongo()
    
    def _init_mongo(self):
        """Initialize MongoDB connection."""
        try:
            from core.database import get_database
            self._db = get_database()
            if self._db:
                self._collection = self._db.wrong_early_records
        except Exception:
            self._use_mongo = False
    
    def save(self, classification: Dict) -> str:
        """
        Save a classification result.
        
        Returns: Record ID
        """
        record_id = self._generate_id()
        
        record = {
            "id": record_id,
            "symbol": classification.get("symbol", "UNKNOWN"),
            "timeframe": classification.get("timeframe", "4H"),
            "direction": classification.get("direction", "UNKNOWN"),
            "execution_type": classification.get("execution_type", "UNKNOWN"),
            "reason": classification.get("reason", "unknown"),
            "confidence": classification.get("confidence", 0.5),
            "severity": classification.get("severity", "low"),
            "details": classification.get("details", {}),
            "pnl": classification.get("pnl", 0.0),
            "classified_at": classification.get("classified_at", datetime.now(timezone.utc).isoformat()),
            "trade_timestamp": classification.get("trade_timestamp")
        }
        
        # Save to MongoDB if available
        if self._use_mongo and self._collection is not None:
            try:
                self._collection.insert_one(record)
            except Exception:
                pass
        
        # Always keep in memory
        self._records.append(record)
        
        # Trim memory if too large
        if len(self._records) > 1000:
            self._records = self._records[-500:]
        
        return record_id
    
    def save_batch(self, classifications: List[Dict]) -> List[str]:
        """Save multiple classifications."""
        return [self.save(c) for c in classifications]
    
    def list_all(self, limit: int = 100) -> List[Dict]:
        """Get all records."""
        if self._use_mongo and self._collection is not None:
            try:
                records = list(
                    self._collection.find({}, {"_id": 0})
                    .sort("classified_at", -1)
                    .limit(limit)
                )
                return records
            except Exception:
                pass
        
        return self._records[-limit:]
    
    def find_by_reason(self, reason: str, limit: int = 50) -> List[Dict]:
        """Find records by reason."""
        if self._use_mongo and self._collection is not None:
            try:
                return list(
                    self._collection.find({"reason": reason}, {"_id": 0})
                    .sort("classified_at", -1)
                    .limit(limit)
                )
            except Exception:
                pass
        
        return [r for r in self._records if r.get("reason") == reason][-limit:]
    
    def find_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Find records by symbol."""
        if self._use_mongo and self._collection is not None:
            try:
                return list(
                    self._collection.find({"symbol": symbol}, {"_id": 0})
                    .sort("classified_at", -1)
                    .limit(limit)
                )
            except Exception:
                pass
        
        return [r for r in self._records if r.get("symbol") == symbol][-limit:]
    
    def count_by_reason(self) -> Dict[str, int]:
        """Count records by reason."""
        if self._use_mongo and self._collection is not None:
            try:
                pipeline = [
                    {"$group": {"_id": "$reason", "count": {"$sum": 1}}}
                ]
                result = list(self._collection.aggregate(pipeline))
                return {r["_id"]: r["count"] for r in result}
            except Exception:
                pass
        
        counts = {}
        for r in self._records:
            reason = r.get("reason", "unknown")
            counts[reason] = counts.get(reason, 0) + 1
        return counts
    
    def get_total_count(self) -> int:
        """Get total record count."""
        if self._use_mongo and self._collection is not None:
            try:
                return self._collection.count_documents({})
            except Exception:
                pass
        return len(self._records)
    
    def clear(self):
        """Clear all records (for testing)."""
        self._records = []
        if self._use_mongo and self._collection is not None:
            try:
                self._collection.delete_many({})
            except Exception:
                pass
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        import hashlib
        import time
        data = f"{time.time()}-{len(self._records)}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
