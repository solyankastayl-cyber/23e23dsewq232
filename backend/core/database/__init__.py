"""
Database infrastructure.
"""
from .mongo import get_database, get_mongo_client, MongoRepository, mongo_health_check
