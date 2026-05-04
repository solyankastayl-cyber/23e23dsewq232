"""
Sprint 7.1: Adaptation Repository
==================================

Stores:
- adaptation_configs: Versioned configurations
- adaptation_changes: Change proposals and applications
"""

from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
import uuid


class AdaptationRepository:
    """
    Repository for adaptation configs and changes.
    
    Collections:
    - adaptation_configs: Versioned configuration states
    - adaptation_changes: Change proposals/applications
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.configs_col = db["adaptation_configs"]
        self.changes_col = db["adaptation_changes"]
    
    async def get_active_config(self) -> Optional[Dict]:
        """
        Get currently active configuration.
        
        Returns:
            Active config or None if no config exists
        """
        config = await self.configs_col.find_one(
            {"is_active": True},
            sort=[("version", -1)]
        )
        return config
    
    async def create_config_version(self, config_data: Dict, created_by: str) -> Dict:
        """
        Create new configuration version.
        
        Steps:
        1. Deactivate current active config
        2. Create new version
        3. Set as active
        
        Args:
            config_data: Configuration payload
            created_by: Operator who created this
        
        Returns:
            New config document
        """
        # Deactivate current active
        await self.configs_col.update_many(
            {"is_active": True},
            {"$set": {"is_active": False}}
        )
        
        # Get next version number
        latest = await self.configs_col.find_one(
            {},
            sort=[("version", -1)]
        )
        next_version = (latest.get("version", 0) + 1) if latest else 1
        
        # Create new config
        new_config = {
            "version": next_version,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "created_by": created_by,
            "config": config_data
        }
        
        result = await self.configs_col.insert_one(new_config)
        new_config["_id"] = result.inserted_id
        
        return new_config
    
    async def get_default_config(self) -> Dict:
        """
        Get default (empty) configuration.
        
        Used when no config exists yet.
        """
        return {
            "confidence_bucket_adjustments": {},
            "r2_drawdown_overrides": {}
        }
    
    async def create_change(self, change_type: str, payload: Dict) -> Dict:
        """
        Create new change proposal.
        
        Args:
            change_type: Type of change (e.g., CONFIDENCE_BUCKET_ADJUSTMENT)
            payload: Change data
        
        Returns:
            Change document
        """
        change = {
            "change_id": str(uuid.uuid4()),
            "type": change_type,
            "status": "PROPOSED",
            "created_at": datetime.now(timezone.utc),
            "applied_at": None,
            "applied_by": None,
            "rejected_at": None,
            "rejected_by": None,
            "payload": payload
        }
        
        result = await self.changes_col.insert_one(change)
        change["_id"] = result.inserted_id
        
        return change
    
    async def get_pending_changes(self) -> List[Dict]:
        """Get all pending (PROPOSED) changes"""
        changes = await self.changes_col.find(
            {"status": "PROPOSED"}
        ).to_list(length=100)
        return changes
    
    async def mark_change_applied(self, change_id: str, applied_by: str) -> bool:
        """
        Mark change as applied.
        
        Args:
            change_id: Change ID
            applied_by: Operator who applied
        
        Returns:
            True if updated successfully
        """
        result = await self.changes_col.update_one(
            {"change_id": change_id, "status": "PROPOSED"},
            {
                "$set": {
                    "status": "APPLIED",
                    "applied_at": datetime.now(timezone.utc),
                    "applied_by": applied_by
                }
            }
        )
        return result.modified_count > 0
    
    async def mark_change_rejected(self, change_id: str, rejected_by: str) -> bool:
        """
        Mark change as rejected.
        
        Args:
            change_id: Change ID
            rejected_by: Operator who rejected
        
        Returns:
            True if updated successfully
        """
        result = await self.changes_col.update_one(
            {"change_id": change_id, "status": "PROPOSED"},
            {
                "$set": {
                    "status": "REJECTED",
                    "rejected_at": datetime.now(timezone.utc),
                    "rejected_by": rejected_by
                }
            }
        )
        return result.modified_count > 0
    
    async def get_change_by_id(self, change_id: str) -> Optional[Dict]:
        """Get change by ID"""
        return await self.changes_col.find_one({"change_id": change_id})
    
    async def get_change_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent change history.
        
        Returns both applied and rejected changes.
        """
        changes = await self.changes_col.find(
            {},
            sort=[("created_at", -1)]
        ).limit(limit).to_list(length=limit)
        return changes
