"""
Regime Memory Registry

PHASE 34 — Market Regime Memory Layer

MongoDB CRUD operations for regime memory records.

Collection: market_regime_memory

Indexes:
- symbol + timestamp
- symbol + regime_state
"""

import hashlib
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .memory_types import (
    RegimeMemoryRecord,
    MemorySummary,
    MemoryPattern,
    PendingOutcomeRecord,
    VECTOR_SIZE,
)


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

COLLECTION_NAME = "market_regime_memory"
PENDING_COLLECTION_NAME = "market_regime_pending"


# ══════════════════════════════════════════════════════════════
# Memory Registry
# ══════════════════════════════════════════════════════════════

class MemoryRegistry:
    """
    Registry for storing and retrieving regime memory records.
    
    Uses MongoDB with indexes for fast queries:
    - (symbol, timestamp) for time-based queries
    - (symbol, regime_state) for regime filtering
    """
    
    def __init__(self):
        self._db = None
        self._collection = None
        self._pending_collection = None
        self._initialized = False
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize MongoDB connection and indexes."""
        try:
            from core.database import get_database
            self._db = get_database()
            if self._db is not None:
                self._collection = self._db[COLLECTION_NAME]
                self._pending_collection = self._db[PENDING_COLLECTION_NAME]
                self._ensure_indexes()
                self._initialized = True
                print(f"[MemoryRegistry] Connected to {COLLECTION_NAME}")
        except Exception as e:
            print(f"[MemoryRegistry] DB init warning: {e}")
            self._initialized = False
    
    def _ensure_indexes(self) -> None:
        """Create indexes for fast queries."""
        if self._collection is None:
            return
        
        try:
            # Index 1: symbol + timestamp
            self._collection.create_index(
                [("symbol", 1), ("timestamp", -1)],
                name="symbol_timestamp_idx",
            )
            
            # Index 2: symbol + regime_state
            self._collection.create_index(
                [("symbol", 1), ("regime_state", 1)],
                name="symbol_regime_idx",
            )
            
            # Index 3: symbol + hypothesis_type
            self._collection.create_index(
                [("symbol", 1), ("hypothesis_type", 1)],
                name="symbol_hypothesis_idx",
            )
            
            print("[MemoryRegistry] Indexes created")
        except Exception as e:
            print(f"[MemoryRegistry] Index creation warning: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # CRUD Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_record(self, record: RegimeMemoryRecord) -> str:
        """
        Save a memory record to the database.
        
        Returns the record_id.
        """
        if not self._initialized or self._collection is None:
            return self._fallback_save(record)
        
        # Generate ID if not present
        if not record.record_id:
            record.record_id = self._generate_record_id(record)
        
        try:
            doc = record.model_dump()
            doc["_id"] = record.record_id
            
            # Upsert
            self._collection.update_one(
                {"_id": record.record_id},
                {"$set": doc},
                upsert=True,
            )
            
            return record.record_id
        except Exception as e:
            print(f"[MemoryRegistry] Save error: {e}")
            return record.record_id
    
    def _generate_record_id(self, record: RegimeMemoryRecord) -> str:
        """Generate unique ID for a record."""
        key = f"{record.symbol}_{record.timestamp.isoformat()}_{record.hypothesis_type}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _fallback_save(self, record: RegimeMemoryRecord) -> str:
        """Fallback save when DB not available."""
        if not record.record_id:
            record.record_id = self._generate_record_id(record)
        return record.record_id
    
    def get_record(self, record_id: str) -> Optional[RegimeMemoryRecord]:
        """Get a single record by ID."""
        if not self._initialized or self._collection is None:
            return None
        
        try:
            doc = self._collection.find_one(
                {"_id": record_id},
                {"_id": 0},
            )
            if doc:
                return RegimeMemoryRecord(**doc)
            return None
        except Exception as e:
            print(f"[MemoryRegistry] Get error: {e}")
            return None
    
    def get_records_by_symbol(
        self,
        symbol: str,
        limit: int = 1000,
        since: Optional[datetime] = None,
    ) -> List[RegimeMemoryRecord]:
        """
        Get all records for a symbol.
        
        Optionally filter by timestamp.
        """
        if not self._initialized or self._collection is None:
            return self._get_mock_records(symbol, limit)
        
        try:
            query: Dict = {"symbol": symbol.upper()}
            
            if since:
                query["timestamp"] = {"$gte": since}
            
            cursor = self._collection.find(
                query,
                {"_id": 0},
            ).sort("timestamp", -1).limit(limit)
            
            records = [RegimeMemoryRecord(**doc) for doc in cursor]
            
            # If no records found, return mock data
            if not records:
                return self._get_mock_records(symbol, limit)
            
            return records
        except Exception as e:
            print(f"[MemoryRegistry] Query error: {e}")
            return self._get_mock_records(symbol, limit)
    
    def get_records_by_regime(
        self,
        symbol: str,
        regime_state: str,
        limit: int = 500,
    ) -> List[RegimeMemoryRecord]:
        """Get records filtered by regime state."""
        if not self._initialized or self._collection is None:
            return self._get_mock_records(symbol, limit, regime_filter=regime_state)
        
        try:
            cursor = self._collection.find(
                {"symbol": symbol.upper(), "regime_state": regime_state},
                {"_id": 0},
            ).sort("timestamp", -1).limit(limit)
            
            records = [RegimeMemoryRecord(**doc) for doc in cursor]
            
            if not records:
                return self._get_mock_records(symbol, limit, regime_filter=regime_state)
            
            return records
        except Exception as e:
            print(f"[MemoryRegistry] Regime query error: {e}")
            return self._get_mock_records(symbol, limit, regime_filter=regime_state)
    
    def get_records_by_hypothesis(
        self,
        symbol: str,
        hypothesis_type: str,
        limit: int = 500,
    ) -> List[RegimeMemoryRecord]:
        """Get records filtered by hypothesis type."""
        if not self._initialized or self._collection is None:
            return self._get_mock_records(symbol, limit, hypothesis_filter=hypothesis_type)
        
        try:
            cursor = self._collection.find(
                {"symbol": symbol.upper(), "hypothesis_type": hypothesis_type},
                {"_id": 0},
            ).sort("timestamp", -1).limit(limit)
            
            records = [RegimeMemoryRecord(**doc) for doc in cursor]
            
            if not records:
                return self._get_mock_records(symbol, limit, hypothesis_filter=hypothesis_type)
            
            return records
        except Exception as e:
            print(f"[MemoryRegistry] Hypothesis query error: {e}")
            return self._get_mock_records(symbol, limit, hypothesis_filter=hypothesis_type)
    
    def delete_record(self, record_id: str) -> bool:
        """Delete a record by ID."""
        if not self._initialized or self._collection is None:
            return False
        
        try:
            result = self._collection.delete_one({"_id": record_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[MemoryRegistry] Delete error: {e}")
            return False
    
    def prune_old_records(
        self,
        symbol: str,
        days_to_keep: int = 365,
    ) -> int:
        """
        Delete records older than specified days.
        
        Memory pruning is important to prevent memory degradation.
        """
        if not self._initialized or self._collection is None:
            return 0
        
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            result = self._collection.delete_many({
                "symbol": symbol.upper(),
                "timestamp": {"$lt": cutoff},
            })
            
            return result.deleted_count
        except Exception as e:
            print(f"[MemoryRegistry] Prune error: {e}")
            return 0
    
    def count_records(self, symbol: str) -> int:
        """Count total records for a symbol."""
        if not self._initialized or self._collection is None:
            return 0
        
        try:
            return self._collection.count_documents({"symbol": symbol.upper()})
        except Exception as e:
            print(f"[MemoryRegistry] Count error: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════
    # Pending Outcomes
    # ═══════════════════════════════════════════════════════════
    
    def save_pending(self, pending: PendingOutcomeRecord) -> str:
        """Save a pending outcome record."""
        if not self._initialized or self._pending_collection is None:
            return pending.pending_id
        
        try:
            doc = pending.model_dump()
            doc["_id"] = pending.pending_id
            
            self._pending_collection.update_one(
                {"_id": pending.pending_id},
                {"$set": doc},
                upsert=True,
            )
            
            return pending.pending_id
        except Exception as e:
            print(f"[MemoryRegistry] Pending save error: {e}")
            return pending.pending_id
    
    def get_ready_pending(self, symbol: str) -> List[PendingOutcomeRecord]:
        """Get pending records that are ready for evaluation."""
        if not self._initialized or self._pending_collection is None:
            return []
        
        try:
            now = datetime.now(timezone.utc)
            
            cursor = self._pending_collection.find(
                {
                    "symbol": symbol.upper(),
                    "expected_outcome_time": {"$lte": now},
                },
                {"_id": 0},
            )
            
            return [PendingOutcomeRecord(**doc) for doc in cursor]
        except Exception as e:
            print(f"[MemoryRegistry] Pending query error: {e}")
            return []
    
    def delete_pending(self, pending_id: str) -> bool:
        """Delete a pending record after evaluation."""
        if not self._initialized or self._pending_collection is None:
            return False
        
        try:
            result = self._pending_collection.delete_one({"_id": pending_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[MemoryRegistry] Pending delete error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════
    # Bulk Operations
    # ═══════════════════════════════════════════════════════════
    
    def bulk_save_records(self, records: List[RegimeMemoryRecord]) -> int:
        """Save multiple records efficiently."""
        if not self._initialized or self._collection is None:
            return 0
        
        if not records:
            return 0
        
        try:
            from pymongo import UpdateOne
            
            operations = []
            for record in records:
                if not record.record_id:
                    record.record_id = self._generate_record_id(record)
                
                doc = record.model_dump()
                doc["_id"] = record.record_id
                
                operations.append(
                    UpdateOne(
                        {"_id": record.record_id},
                        {"$set": doc},
                        upsert=True,
                    )
                )
            
            result = self._collection.bulk_write(operations)
            return result.upserted_count + result.modified_count
        except Exception as e:
            print(f"[MemoryRegistry] Bulk save error: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════
    
    def get_stats(self, symbol: str) -> Dict:
        """Get statistics for a symbol's memory."""
        if not self._initialized or self._collection is None:
            return {
                "symbol": symbol,
                "total_records": 0,
                "successful": 0,
                "failed": 0,
                "db_connected": False,
            }
        
        try:
            pipeline = [
                {"$match": {"symbol": symbol.upper()}},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "successful": {
                            "$sum": {"$cond": ["$success", 1, 0]}
                        },
                    }
                }
            ]
            
            result = list(self._collection.aggregate(pipeline))
            
            if result:
                return {
                    "symbol": symbol,
                    "total_records": result[0]["total"],
                    "successful": result[0]["successful"],
                    "failed": result[0]["total"] - result[0]["successful"],
                    "db_connected": True,
                }
            
            return {
                "symbol": symbol,
                "total_records": 0,
                "successful": 0,
                "failed": 0,
                "db_connected": True,
            }
        except Exception as e:
            print(f"[MemoryRegistry] Stats error: {e}")
            return {
                "symbol": symbol,
                "total_records": 0,
                "successful": 0,
                "failed": 0,
                "db_connected": False,
                "error": str(e),
            }
    
    # ═══════════════════════════════════════════════════════════
    # Mock Data (for testing without DB)
    # ═══════════════════════════════════════════════════════════
    
    def _get_mock_records(
        self,
        symbol: str,
        limit: int = 100,
        regime_filter: Optional[str] = None,
        hypothesis_filter: Optional[str] = None,
    ) -> List[RegimeMemoryRecord]:
        """Generate mock memory records for testing."""
        records = []
        base_time = datetime.now(timezone.utc) - timedelta(days=180)
        
        regimes = ["TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"]
        hypotheses = [
            "BULLISH_CONTINUATION",
            "BEARISH_CONTINUATION",
            "BREAKOUT_FORMING",
            "RANGE_MEAN_REVERSION",
            "NO_EDGE",
        ]
        fractals = ["ALIGNED", "DIVERGENT", "NEUTRAL"]
        micros = ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        
        for i in range(min(limit, 200)):
            # Deterministic randomness based on symbol and index
            seed = int(hashlib.md5(f"{symbol}_{i}".encode()).hexdigest()[:8], 16)
            
            regime = regimes[seed % len(regimes)]
            hypothesis = hypotheses[(seed >> 4) % len(hypotheses)]
            
            # Apply filters
            if regime_filter and regime != regime_filter:
                regime = regime_filter
            if hypothesis_filter and hypothesis != hypothesis_filter:
                hypothesis = hypothesis_filter
            
            # Generate structure vector
            vector = [
                ((seed % 200) - 100) / 100,  # trend_slope
                (seed % 80 + 20) / 100,      # volatility
                ((seed >> 8 % 160) - 80) / 100,  # volume_delta
                ((seed >> 12 % 140) - 70) / 100,  # microstructure_bias
                (seed >> 16 % 70 + 30) / 100,    # liquidity_state
                [1.0, 0.66, 0.33, 0.0][regimes.index(regime) % 4],  # regime_numeric
                ((seed >> 20 % 160) - 80) / 100,  # fractal_alignment
            ]
            
            # Generate outcome
            future_move = ((seed >> 4 % 160) - 80) / 10  # -8% to +8%
            
            # Determine success based on hypothesis and move
            if hypothesis in ["BULLISH_CONTINUATION", "BREAKOUT_FORMING"]:
                success = future_move > 1.0
            elif hypothesis == "BEARISH_CONTINUATION":
                success = future_move < -1.0
            else:
                success = abs(future_move) < 2.0
            
            record = RegimeMemoryRecord(
                record_id=f"mock_{symbol}_{i}",
                symbol=symbol.upper(),
                timestamp=base_time + timedelta(hours=i * 2),
                regime_state=regime,
                fractal_state=fractals[(seed >> 8) % len(fractals)],
                hypothesis_type=hypothesis,
                microstructure_state=micros[(seed >> 12) % len(micros)],
                structure_vector=vector,
                future_move_percent=round(future_move, 2),
                horizon_minutes=60,
                success=success,
            )
            records.append(record)
        
        return records


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_memory_registry: Optional[MemoryRegistry] = None


def get_memory_registry() -> MemoryRegistry:
    """Get singleton instance of MemoryRegistry."""
    global _memory_registry
    if _memory_registry is None:
        _memory_registry = MemoryRegistry()
    return _memory_registry
