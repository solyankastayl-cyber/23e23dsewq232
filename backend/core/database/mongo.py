"""
MongoDB Singleton Connection Manager
=====================================
Provides unified MongoDB connection for all repositories.

Usage:
    from core.database import get_database, MongoRepository
    
    # Get database instance
    db = get_database()
    
    # Or extend MongoRepository
    class MyRepository(MongoRepository):
        def __init__(self):
            super().__init__()
            self.collection_name = "my_collection"
"""

import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

# Load .env file FIRST before any other imports
from dotenv import load_dotenv

# Find and load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[MongoDB] Loaded environment from {env_path}")
else:
    print(f"[MongoDB] Warning: .env file not found at {env_path}")

try:
    from pymongo import MongoClient, DESCENDING, ASCENDING
    from pymongo.database import Database
    from pymongo.collection import Collection
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    print("[MongoDB] Warning: pymongo not installed")


# Singleton instances
_mongo_client: Optional["MongoClient"] = None
_database: Optional["Database"] = None
_connection_checked: bool = False


def get_mongo_client() -> Optional["MongoClient"]:
    """
    Get singleton MongoDB client.
    
    Returns:
        MongoClient instance or None if connection fails
    """
    global _mongo_client, _connection_checked
    
    if not PYMONGO_AVAILABLE:
        return None
    
    if _mongo_client is not None:
        return _mongo_client
    
    try:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        
        _mongo_client = MongoClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
            maxPoolSize=50,
            minPoolSize=5
        )
        
        # Verify connection
        _mongo_client.admin.command('ping')
        _connection_checked = True
        print(f"[MongoDB] Connected to {mongo_url}")
        
        return _mongo_client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"[MongoDB] Connection failed: {e}")
        _mongo_client = None
        return None
    except Exception as e:
        print(f"[MongoDB] Unexpected error: {e}")
        _mongo_client = None
        return None


def get_database() -> Optional["Database"]:
    """
    Get singleton database instance.
    
    Returns:
        Database instance or None if connection fails
    """
    global _database
    
    if _database is not None:
        return _database
    
    client = get_mongo_client()
    if client is None:
        return None
    
    db_name = os.environ.get("DB_NAME", "ta_engine")
    _database = client[db_name]
    print(f"[MongoDB] Using database: {db_name}")
    
    return _database


def mongo_health_check() -> Dict[str, Any]:
    """
    Perform MongoDB health check.
    
    Returns:
        Health status dictionary
    """
    result = {
        "status": "unknown",
        "connected": False,
        "latency_ms": None,
        "database": None,
        "collections_count": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if not PYMONGO_AVAILABLE:
        result["status"] = "pymongo_not_installed"
        return result
    
    client = get_mongo_client()
    if client is None:
        result["status"] = "connection_failed"
        return result
    
    try:
        # Measure ping latency
        start = time.time()
        client.admin.command('ping')
        latency = (time.time() - start) * 1000
        
        db = get_database()
        collections = db.list_collection_names() if db is not None else []
        
        result["status"] = "healthy"
        result["connected"] = True
        result["latency_ms"] = round(latency, 2)
        result["database"] = os.environ.get("DB_NAME", "ta_engine")
        result["collections_count"] = len(collections)
        result["collections"] = collections[:20]  # First 20 collections
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


class MongoRepository:
    """
    Base class for MongoDB repositories.
    
    Usage:
        class MyRepository(MongoRepository):
            def __init__(self):
                super().__init__()
                self.collection_name = "my_collection"
            
            def save(self, doc):
                return self._insert_one(doc)
    """
    
    def __init__(self):
        self._db = get_database()
        self.collection_name: Optional[str] = None
    
    @property
    def db(self) -> Optional["Database"]:
        """Get database instance."""
        if self._db is None:
            self._db = get_database()
        return self._db
    
    @property
    def connected(self) -> bool:
        """Check if connected to database."""
        return self.db is not None
    
    def collection(self, name: Optional[str] = None) -> Optional["Collection"]:
        """Get collection by name."""
        if self.db is None:
            return None
        col_name = name or self.collection_name
        if col_name is None:
            raise ValueError("Collection name not specified")
        return self.db[col_name]
    
    def _insert_one(self, doc: Dict, collection: Optional[str] = None) -> bool:
        """Insert single document."""
        col = self.collection(collection)
        if col is None:
            return False
        try:
            doc["_created_at"] = datetime.now(timezone.utc)
            col.insert_one(doc)
            return True
        except Exception as e:
            print(f"[MongoRepository] Insert error: {e}")
            return False
    
    def _insert_many(self, docs: List[Dict], collection: Optional[str] = None) -> int:
        """Insert multiple documents."""
        col = self.collection(collection)
        if col is None or not docs:
            return 0
        try:
            now = datetime.now(timezone.utc)
            for doc in docs:
                doc["_created_at"] = now
            result = col.insert_many(docs)
            return len(result.inserted_ids)
        except Exception as e:
            print(f"[MongoRepository] Insert many error: {e}")
            return 0
    
    def _find_one(
        self, 
        query: Dict, 
        collection: Optional[str] = None,
        projection: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Find single document."""
        col = self.collection(collection)
        if col is None:
            return None
        try:
            # Exclude _id by default
            proj = projection or {"_id": 0}
            return col.find_one(query, proj)
        except Exception as e:
            print(f"[MongoRepository] Find error: {e}")
            return None
    
    def _find_many(
        self,
        query: Dict,
        collection: Optional[str] = None,
        projection: Optional[Dict] = None,
        sort: Optional[List] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Find multiple documents."""
        col = self.collection(collection)
        if col is None:
            return []
        try:
            proj = projection or {"_id": 0}
            cursor = col.find(query, proj)
            if sort:
                cursor = cursor.sort(sort)
            cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"[MongoRepository] Find many error: {e}")
            return []
    
    def _update_one(
        self,
        query: Dict,
        update: Dict,
        collection: Optional[str] = None,
        upsert: bool = False
    ) -> bool:
        """Update single document."""
        col = self.collection(collection)
        if col is None:
            return False
        try:
            update_doc = {"$set": update, "$currentDate": {"_updated_at": True}}
            result = col.update_one(query, update_doc, upsert=upsert)
            return result.modified_count > 0 or (upsert and result.upserted_id is not None)
        except Exception as e:
            print(f"[MongoRepository] Update error: {e}")
            return False
    
    def _delete_one(self, query: Dict, collection: Optional[str] = None) -> bool:
        """Delete single document."""
        col = self.collection(collection)
        if col is None:
            return False
        try:
            result = col.delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            print(f"[MongoRepository] Delete error: {e}")
            return False
    
    def _count(self, query: Dict = None, collection: Optional[str] = None) -> int:
        """Count documents."""
        col = self.collection(collection)
        if col is None:
            return 0
        try:
            return col.count_documents(query or {})
        except Exception as e:
            print(f"[MongoRepository] Count error: {e}")
            return 0
    
    def _create_index(
        self,
        keys: List[tuple],
        collection: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Create index."""
        col = self.collection(collection)
        if col is None:
            return False
        try:
            col.create_index(keys, **kwargs)
            return True
        except Exception as e:
            print(f"[MongoRepository] Index error: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            col = self.collection()
            count = col.count_documents({}) if col is not None else 0
            return {
                "connected": True,
                "collection": self.collection_name,
                "document_count": count
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
