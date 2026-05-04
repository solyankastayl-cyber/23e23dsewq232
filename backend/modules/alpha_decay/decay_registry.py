"""
Alpha Decay Registry

PHASE 43.8 — Alpha Decay Engine

MongoDB persistence for decay states.

Collections:
- alpha_decay_states

Indexes:
- hypothesis_id
- symbol
- created_at
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import os

from .decay_types import (
    AlphaDecayState,
    DecayStage,
    SignalType,
)


class AlphaDecayRegistry:
    """
    Alpha Decay Registry — PHASE 43.8
    
    MongoDB persistence for decay states.
    """
    
    def __init__(self):
        self._collection_name = "alpha_decay_states"
        self._client = None
        self._db = None
    
    async def _get_collection(self):
        """Get MongoDB collection."""
        if self._client is None:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "fomo_trading")
            
            self._client = AsyncIOMotorClient(mongo_url)
            self._db = self._client[db_name]
            
            # Create indexes
            collection = self._db[self._collection_name]
            await collection.create_index("hypothesis_id", unique=True)
            await collection.create_index("symbol")
            await collection.create_index("created_at")
            await collection.create_index("decay_stage")
            await collection.create_index([("symbol", 1), ("created_at", -1)])
        
        return self._db[self._collection_name]
    
    # ═══════════════════════════════════════════════════════════
    # CRUD Operations
    # ═══════════════════════════════════════════════════════════
    
    async def create_decay_state(self, state: AlphaDecayState) -> str:
        """Create a new decay state."""
        collection = await self._get_collection()
        
        doc = state.model_dump()
        # Convert enums to strings
        doc["signal_type"] = state.signal_type.value
        doc["decay_stage"] = state.decay_stage.value
        
        await collection.insert_one(doc)
        return state.decay_id
    
    async def get_decay_state(self, hypothesis_id: str) -> Optional[AlphaDecayState]:
        """Get decay state by hypothesis ID."""
        collection = await self._get_collection()
        
        doc = await collection.find_one({"hypothesis_id": hypothesis_id})
        if not doc:
            return None
        
        # Remove MongoDB _id
        doc.pop("_id", None)
        
        # Convert strings back to enums
        doc["signal_type"] = SignalType(doc.get("signal_type", "DEFAULT"))
        doc["decay_stage"] = DecayStage(doc.get("decay_stage", "FRESH"))
        
        return AlphaDecayState(**doc)
    
    async def update_decay_state(self, state: AlphaDecayState) -> bool:
        """Update an existing decay state."""
        collection = await self._get_collection()
        
        doc = state.model_dump()
        doc["signal_type"] = state.signal_type.value
        doc["decay_stage"] = state.decay_stage.value
        doc["updated_at"] = datetime.now(timezone.utc)
        
        result = await collection.update_one(
            {"hypothesis_id": state.hypothesis_id},
            {"$set": doc}
        )
        
        return result.modified_count > 0
    
    async def upsert_decay_state(self, state: AlphaDecayState) -> bool:
        """Upsert decay state."""
        collection = await self._get_collection()
        
        doc = state.model_dump()
        doc["signal_type"] = state.signal_type.value
        doc["decay_stage"] = state.decay_stage.value
        doc["updated_at"] = datetime.now(timezone.utc)
        
        result = await collection.update_one(
            {"hypothesis_id": state.hypothesis_id},
            {"$set": doc},
            upsert=True
        )
        
        return result.upserted_id is not None or result.modified_count > 0
    
    async def delete_decay_state(self, hypothesis_id: str) -> bool:
        """Delete a decay state."""
        collection = await self._get_collection()
        
        result = await collection.delete_one({"hypothesis_id": hypothesis_id})
        return result.deleted_count > 0
    
    # ═══════════════════════════════════════════════════════════
    # Query Operations
    # ═══════════════════════════════════════════════════════════
    
    async def get_states_by_symbol(self, symbol: str, limit: int = 100) -> List[AlphaDecayState]:
        """Get decay states for a symbol."""
        collection = await self._get_collection()
        
        cursor = collection.find({"symbol": symbol}).sort("created_at", -1).limit(limit)
        
        states = []
        async for doc in cursor:
            doc.pop("_id", None)
            doc["signal_type"] = SignalType(doc.get("signal_type", "DEFAULT"))
            doc["decay_stage"] = DecayStage(doc.get("decay_stage", "FRESH"))
            states.append(AlphaDecayState(**doc))
        
        return states
    
    async def get_active_states(self, limit: int = 500) -> List[AlphaDecayState]:
        """Get all non-expired decay states."""
        collection = await self._get_collection()
        
        cursor = collection.find({
            "is_expired": False,
            "execution_blocked": False
        }).sort("created_at", -1).limit(limit)
        
        states = []
        async for doc in cursor:
            doc.pop("_id", None)
            doc["signal_type"] = SignalType(doc.get("signal_type", "DEFAULT"))
            doc["decay_stage"] = DecayStage(doc.get("decay_stage", "FRESH"))
            states.append(AlphaDecayState(**doc))
        
        return states
    
    async def get_expired_states(self, limit: int = 100) -> List[AlphaDecayState]:
        """Get expired decay states."""
        collection = await self._get_collection()
        
        cursor = collection.find({
            "$or": [
                {"is_expired": True},
                {"execution_blocked": True}
            ]
        }).sort("created_at", -1).limit(limit)
        
        states = []
        async for doc in cursor:
            doc.pop("_id", None)
            doc["signal_type"] = SignalType(doc.get("signal_type", "DEFAULT"))
            doc["decay_stage"] = DecayStage(doc.get("decay_stage", "FRESH"))
            states.append(AlphaDecayState(**doc))
        
        return states
    
    async def get_states_by_stage(self, stage: DecayStage, limit: int = 100) -> List[AlphaDecayState]:
        """Get states by decay stage."""
        collection = await self._get_collection()
        
        cursor = collection.find({"decay_stage": stage.value}).limit(limit)
        
        states = []
        async for doc in cursor:
            doc.pop("_id", None)
            doc["signal_type"] = SignalType(doc.get("signal_type", "DEFAULT"))
            doc["decay_stage"] = DecayStage(doc.get("decay_stage", "FRESH"))
            states.append(AlphaDecayState(**doc))
        
        return states
    
    # ═══════════════════════════════════════════════════════════
    # Bulk Operations
    # ═══════════════════════════════════════════════════════════
    
    async def expire_old_states(self, max_age_hours: int = 24) -> int:
        """Mark old states as expired."""
        collection = await self._get_collection()
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        result = await collection.update_many(
            {
                "created_at": {"$lt": cutoff},
                "is_expired": False
            },
            {
                "$set": {
                    "is_expired": True,
                    "execution_blocked": True,
                    "decay_stage": DecayStage.EXPIRED.value,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return result.modified_count
    
    async def delete_expired_states(self, older_than_hours: int = 48) -> int:
        """Delete old expired states."""
        collection = await self._get_collection()
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        result = await collection.delete_many({
            "is_expired": True,
            "created_at": {"$lt": cutoff}
        })
        
        return result.deleted_count
    
    async def count_by_stage(self) -> Dict[str, int]:
        """Count states by stage."""
        collection = await self._get_collection()
        
        pipeline = [
            {"$group": {"_id": "$decay_stage", "count": {"$sum": 1}}}
        ]
        
        counts = {}
        async for doc in collection.aggregate(pipeline):
            counts[doc["_id"]] = doc["count"]
        
        return counts
    
    async def get_summary_stats(self) -> Dict:
        """Get summary statistics."""
        collection = await self._get_collection()
        
        total = await collection.count_documents({})
        active = await collection.count_documents({"is_expired": False})
        expired = await collection.count_documents({"is_expired": True})
        blocked = await collection.count_documents({"execution_blocked": True})
        
        counts = await self.count_by_stage()
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "blocked": blocked,
            "by_stage": counts,
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_decay_registry: Optional[AlphaDecayRegistry] = None


def get_alpha_decay_registry() -> AlphaDecayRegistry:
    """Get singleton instance."""
    global _decay_registry
    if _decay_registry is None:
        _decay_registry = AlphaDecayRegistry()
    return _decay_registry
