"""
SEC2 - Vault Repository
MongoDB persistence layer for vault data.
"""

import os
from typing import List, Optional
from datetime import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

from .vault_types import (
    APIKeyRecord,
    VaultAuditEvent,
    KeyStatus,
    AuditAction
)


class VaultRepository:
    """
    MongoDB repository for API Key Vault.
    
    Collections:
    - vault_keys: Encrypted API key records
    - vault_audit: Audit trail of all operations
    """
    
    def __init__(self):
        """Initialize MongoDB connection"""
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        self._client = MongoClient(mongo_url)
        self._db = self._client[db_name]
        
        # Collections
        self._keys: Collection = self._db["vault_keys"]
        self._audit: Collection = self._db["vault_audit"]
        
        # Ensure indexes
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create necessary indexes for performance"""
        # Keys collection
        self._keys.create_index("key_id", unique=True)
        self._keys.create_index("exchange")
        self._keys.create_index("status")
        self._keys.create_index([("exchange", 1), ("account_name", 1)])
        
        # Audit collection
        self._audit.create_index("event_id", unique=True)
        self._audit.create_index("key_id")
        self._audit.create_index("action")
        self._audit.create_index([("created_at", DESCENDING)])
        self._audit.create_index([("key_id", 1), ("created_at", DESCENDING)])
    
    # ===========================================
    # Key Operations
    # ===========================================
    
    def create_key(self, key: APIKeyRecord) -> APIKeyRecord:
        """Store a new API key record"""
        doc = key.dict()
        self._keys.insert_one(doc)
        return key
    
    def get_key(self, key_id: str) -> Optional[APIKeyRecord]:
        """Get a key by ID"""
        doc = self._keys.find_one({"key_id": key_id}, {"_id": 0})
        if doc:
            return APIKeyRecord(**doc)
        return None
    
    def get_key_by_exchange_account(
        self, 
        exchange: str, 
        account_name: str
    ) -> Optional[APIKeyRecord]:
        """Get a key by exchange and account name"""
        doc = self._keys.find_one(
            {"exchange": exchange, "account_name": account_name},
            {"_id": 0}
        )
        if doc:
            return APIKeyRecord(**doc)
        return None
    
    def get_all_keys(
        self, 
        status: Optional[KeyStatus] = None,
        exchange: Optional[str] = None
    ) -> List[APIKeyRecord]:
        """Get all keys with optional filters"""
        query = {}
        if status:
            query["status"] = status.value if isinstance(status, KeyStatus) else status
        if exchange:
            query["exchange"] = exchange
        
        docs = self._keys.find(query, {"_id": 0})
        return [APIKeyRecord(**doc) for doc in docs]
    
    def get_active_keys(self) -> List[APIKeyRecord]:
        """Get all active keys"""
        return self.get_all_keys(status=KeyStatus.ACTIVE)
    
    def update_key(self, key_id: str, updates: dict) -> Optional[APIKeyRecord]:
        """Update a key record"""
        updates["updated_at"] = datetime.utcnow()
        
        result = self._keys.find_one_and_update(
            {"key_id": key_id},
            {"$set": updates},
            return_document=True,
            projection={"_id": 0}
        )
        
        if result:
            return APIKeyRecord(**result)
        return None
    
    def update_key_status(self, key_id: str, status: KeyStatus) -> Optional[APIKeyRecord]:
        """Update key status"""
        return self.update_key(key_id, {"status": status.value})
    
    def update_last_used(self, key_id: str) -> bool:
        """Update last used timestamp and increment access count"""
        result = self._keys.update_one(
            {"key_id": key_id},
            {
                "$set": {"last_used_at": datetime.utcnow()},
                "$inc": {"access_count": 1}
            }
        )
        return result.modified_count > 0
    
    def delete_key(self, key_id: str) -> bool:
        """Delete a key record (use with caution)"""
        result = self._keys.delete_one({"key_id": key_id})
        return result.deleted_count > 0
    
    def count_keys(self, status: Optional[KeyStatus] = None) -> int:
        """Count keys with optional status filter"""
        query = {}
        if status:
            query["status"] = status.value if isinstance(status, KeyStatus) else status
        return self._keys.count_documents(query)
    
    # ===========================================
    # Audit Operations
    # ===========================================
    
    def log_audit_event(self, event: VaultAuditEvent) -> VaultAuditEvent:
        """Log an audit event"""
        doc = event.dict()
        self._audit.insert_one(doc)
        return event
    
    def get_audit_events(
        self,
        key_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100
    ) -> List[VaultAuditEvent]:
        """Get audit events with optional filters"""
        query = {}
        if key_id:
            query["key_id"] = key_id
        if action:
            query["action"] = action.value if isinstance(action, AuditAction) else action
        
        docs = self._audit.find(
            query, 
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return [VaultAuditEvent(**doc) for doc in docs]
    
    def get_key_audit_history(
        self, 
        key_id: str, 
        limit: int = 50
    ) -> List[VaultAuditEvent]:
        """Get audit history for a specific key"""
        return self.get_audit_events(key_id=key_id, limit=limit)
    
    def get_recent_failed_access(
        self, 
        limit: int = 20
    ) -> List[VaultAuditEvent]:
        """Get recent failed access attempts"""
        docs = self._audit.find(
            {"action": AuditAction.FAILED_ACCESS.value},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return [VaultAuditEvent(**doc) for doc in docs]
    
    def count_audit_events(
        self,
        key_id: Optional[str] = None,
        action: Optional[AuditAction] = None
    ) -> int:
        """Count audit events"""
        query = {}
        if key_id:
            query["key_id"] = key_id
        if action:
            query["action"] = action.value if isinstance(action, AuditAction) else action
        return self._audit.count_documents(query)


# Singleton instance
_repository_instance = None

def get_vault_repository() -> VaultRepository:
    """Get singleton VaultRepository instance"""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = VaultRepository()
    return _repository_instance
