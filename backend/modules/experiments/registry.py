"""
Experiment Registry

Manages experiment configurations and status.
"""
from typing import Optional, Dict, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from .config import ExperimentConfig, ExperimentStatus, EXPERIMENT_BASELINE_BTC, EXPERIMENT_MARKET_DYNAMIC


class ExperimentRegistry:
    """
    Central registry for experiments
    
    Manages:
    - Experiment configs
    - Experiment status (enabled/disabled)
    - Experiment metadata
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["experiments"]
    
    async def initialize_defaults(self):
        """Initialize default experiments if not exist"""
        # Check if experiments already exist
        existing = await self.collection.count_documents({})
        
        if existing == 0:
            # Insert default experiments
            await self.collection.insert_many([
                EXPERIMENT_BASELINE_BTC.to_dict(),
                EXPERIMENT_MARKET_DYNAMIC.to_dict(),
            ])
            print("[ExperimentRegistry] ✅ Initialized default experiments")
        else:
            print(f"[ExperimentRegistry] ℹ️  {existing} experiments already exist")
    
    async def get_experiment(self, experiment_id: str) -> Optional[ExperimentConfig]:
        """Get experiment config by ID"""
        doc = await self.collection.find_one({"experiment_id": experiment_id})
        if not doc:
            return None
        return ExperimentConfig.from_dict(doc)
    
    async def get_all_experiments(self) -> List[ExperimentConfig]:
        """Get all experiments"""
        cursor = self.collection.find({})
        docs = await cursor.to_list(None)
        return [ExperimentConfig.from_dict(doc) for doc in docs]
    
    async def get_enabled_experiments(self) -> List[ExperimentConfig]:
        """Get only enabled experiments"""
        cursor = self.collection.find({"status": ExperimentStatus.ENABLED.value})
        docs = await cursor.to_list(None)
        return [ExperimentConfig.from_dict(doc) for doc in docs]
    
    async def update_experiment(self, config: ExperimentConfig):
        """Update experiment config"""
        config.updated_at = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"experiment_id": config.experiment_id},
            {"$set": config.to_dict()},
            upsert=True,
        )
    
    async def set_status(self, experiment_id: str, status: ExperimentStatus):
        """Change experiment status"""
        await self.collection.update_one(
            {"experiment_id": experiment_id},
            {"$set": {"status": status.value}},
        )
    
    async def enable_experiment(self, experiment_id: str):
        """Enable experiment"""
        await self.set_status(experiment_id, ExperimentStatus.ENABLED)
    
    async def disable_experiment(self, experiment_id: str):
        """Disable experiment"""
        await self.set_status(experiment_id, ExperimentStatus.DISABLED)
    
    async def get_stats(self) -> Dict[str, int]:
        """Get experiment statistics"""
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        results = await self.collection.aggregate(pipeline).to_list(None)
        
        stats = {r["_id"]: r["count"] for r in results}
        stats["total"] = await self.collection.count_documents({})
        
        return stats


# Global registry instance
_registry: Optional[ExperimentRegistry] = None


def init_experiment_registry(db: AsyncIOMotorDatabase):
    """Initialize experiment registry"""
    global _registry
    _registry = ExperimentRegistry(db)
    return _registry


def get_experiment_registry() -> ExperimentRegistry:
    """Get experiment registry instance"""
    if _registry is None:
        raise RuntimeError("ExperimentRegistry not initialized")
    return _registry
