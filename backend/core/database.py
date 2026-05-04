"""
MongoDB Database Connection
"""
import os
from pymongo import MongoClient
from typing import Optional

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

_client: Optional[MongoClient] = None
_db = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return _client

def get_database():
    global _db
    if _db is None:
        _db = get_client()[DB_NAME]
    return _db

def mongo_health_check():
    try:
        client = get_client()
        client.admin.command('ping')
        db = get_database()
        return {
            "status": "ok",
            "connected": True,
            "database": DB_NAME,
            "collections": db.list_collection_names()
        }
    except Exception as e:
        return {"status": "error", "connected": False, "error": str(e)}
