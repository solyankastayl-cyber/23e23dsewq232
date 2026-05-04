"""
State Reconciliation Layer - Repository
MongoDB persistence for reconciliation data.
"""

import os
from typing import List, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

from .recon_types import (
    ReconciliationRun,
    ReconciliationMismatch,
    ReconciliationStatus,
    MismatchSeverity
)


class ReconciliationRepository:
    """
    MongoDB repository for reconciliation data.
    
    Collections:
    - reconciliation_runs: History of reconciliation runs
    - reconciliation_mismatches: Individual mismatches detected
    - exchange_quarantine: Quarantined exchanges
    """
    
    def __init__(self):
        """Initialize MongoDB connection"""
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        self._client = MongoClient(mongo_url)
        self._db = self._client[db_name]
        
        # Collections
        self._runs: Collection = self._db["reconciliation_runs"]
        self._mismatches: Collection = self._db["reconciliation_mismatches"]
        self._quarantine: Collection = self._db["exchange_quarantine"]
        
        # Ensure indexes
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create necessary indexes"""
        # Runs collection
        self._runs.create_index("run_id", unique=True)
        self._runs.create_index([("started_at", DESCENDING)])
        self._runs.create_index("status")
        
        # Mismatches collection
        self._mismatches.create_index("mismatch_id", unique=True)
        self._mismatches.create_index("exchange")
        self._mismatches.create_index("mismatch_type")
        self._mismatches.create_index("severity")
        self._mismatches.create_index("resolved")
        self._mismatches.create_index([("detected_at", DESCENDING)])
        
        # Quarantine collection
        self._quarantine.create_index("exchange", unique=True)
    
    # ===========================================
    # Run Operations
    # ===========================================
    
    def save_run(self, run: ReconciliationRun) -> ReconciliationRun:
        """Save or update a reconciliation run"""
        doc = run.dict()
        self._runs.replace_one(
            {"run_id": run.run_id},
            doc,
            upsert=True
        )
        return run
    
    def get_run(self, run_id: str) -> Optional[ReconciliationRun]:
        """Get a run by ID"""
        doc = self._runs.find_one({"run_id": run_id}, {"_id": 0})
        if doc:
            return ReconciliationRun(**doc)
        return None
    
    def get_recent_runs(
        self,
        limit: int = 20,
        status: Optional[ReconciliationStatus] = None
    ) -> List[ReconciliationRun]:
        """Get recent reconciliation runs"""
        query = {}
        if status:
            query["status"] = status.value if isinstance(status, ReconciliationStatus) else status
        
        docs = self._runs.find(
            query,
            {"_id": 0}
        ).sort("started_at", DESCENDING).limit(limit)
        
        return [ReconciliationRun(**doc) for doc in docs]
    
    def get_last_run(self) -> Optional[ReconciliationRun]:
        """Get the most recent run"""
        runs = self.get_recent_runs(limit=1)
        return runs[0] if runs else None
    
    def count_runs_since(self, since: datetime) -> int:
        """Count runs since a timestamp"""
        return self._runs.count_documents({
            "started_at": {"$gte": since}
        })
    
    # ===========================================
    # Mismatch Operations
    # ===========================================
    
    def save_mismatch(self, mismatch: ReconciliationMismatch) -> ReconciliationMismatch:
        """Save or update a mismatch"""
        doc = mismatch.dict()
        self._mismatches.replace_one(
            {"mismatch_id": mismatch.mismatch_id},
            doc,
            upsert=True
        )
        return mismatch
    
    def save_mismatches_batch(self, mismatches: List[ReconciliationMismatch]):
        """Save multiple mismatches"""
        if not mismatches:
            return
        
        for mismatch in mismatches:
            self.save_mismatch(mismatch)
    
    def get_mismatch(self, mismatch_id: str) -> Optional[ReconciliationMismatch]:
        """Get a mismatch by ID"""
        doc = self._mismatches.find_one({"mismatch_id": mismatch_id}, {"_id": 0})
        if doc:
            return ReconciliationMismatch(**doc)
        return None
    
    def get_unresolved_mismatches(
        self,
        exchange: Optional[str] = None,
        severity: Optional[MismatchSeverity] = None,
        limit: int = 100
    ) -> List[ReconciliationMismatch]:
        """Get unresolved mismatches"""
        query = {"resolved": False}
        if exchange:
            query["exchange"] = exchange
        if severity:
            query["severity"] = severity.value if isinstance(severity, MismatchSeverity) else severity
        
        docs = self._mismatches.find(
            query,
            {"_id": 0}
        ).sort("detected_at", DESCENDING).limit(limit)
        
        return [ReconciliationMismatch(**doc) for doc in docs]
    
    def get_recent_mismatches(
        self,
        limit: int = 50,
        exchange: Optional[str] = None
    ) -> List[ReconciliationMismatch]:
        """Get recent mismatches"""
        query = {}
        if exchange:
            query["exchange"] = exchange
        
        docs = self._mismatches.find(
            query,
            {"_id": 0}
        ).sort("detected_at", DESCENDING).limit(limit)
        
        return [ReconciliationMismatch(**doc) for doc in docs]
    
    def resolve_mismatch(
        self,
        mismatch_id: str,
        resolution_notes: Optional[str] = None
    ) -> Optional[ReconciliationMismatch]:
        """Mark a mismatch as resolved"""
        result = self._mismatches.find_one_and_update(
            {"mismatch_id": mismatch_id},
            {
                "$set": {
                    "resolved": True,
                    "resolved_at": datetime.utcnow(),
                    "resolution_notes": resolution_notes
                }
            },
            return_document=True,
            projection={"_id": 0}
        )
        
        if result:
            return ReconciliationMismatch(**result)
        return None
    
    def count_unresolved_mismatches(
        self,
        exchange: Optional[str] = None
    ) -> int:
        """Count unresolved mismatches"""
        query = {"resolved": False}
        if exchange:
            query["exchange"] = exchange
        return self._mismatches.count_documents(query)
    
    def count_mismatches_since(self, since: datetime) -> int:
        """Count mismatches since a timestamp"""
        return self._mismatches.count_documents({
            "detected_at": {"$gte": since}
        })
    
    # ===========================================
    # Quarantine Operations
    # ===========================================
    
    def quarantine_exchange(
        self,
        exchange: str,
        reason: str,
        run_id: Optional[str] = None
    ) -> dict:
        """Add an exchange to quarantine"""
        doc = {
            "exchange": exchange,
            "reason": reason,
            "quarantined_at": datetime.utcnow(),
            "run_id": run_id,
            "active": True
        }
        
        self._quarantine.replace_one(
            {"exchange": exchange},
            doc,
            upsert=True
        )
        
        return doc
    
    def release_from_quarantine(self, exchange: str) -> bool:
        """Remove an exchange from quarantine"""
        result = self._quarantine.delete_one({"exchange": exchange})
        return result.deleted_count > 0
    
    def is_quarantined(self, exchange: str) -> bool:
        """Check if an exchange is quarantined"""
        return self._quarantine.count_documents({
            "exchange": exchange,
            "active": True
        }) > 0
    
    def get_quarantined_exchanges(self) -> List[dict]:
        """Get all quarantined exchanges"""
        docs = self._quarantine.find({"active": True}, {"_id": 0})
        return list(docs)
    
    def count_quarantined(self) -> int:
        """Count quarantined exchanges"""
        return self._quarantine.count_documents({"active": True})


# Singleton instance
_repository_instance = None

def get_recon_repository() -> ReconciliationRepository:
    """Get singleton ReconciliationRepository instance"""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = ReconciliationRepository()
    return _repository_instance
