"""
Strategy Config Repository (STR2)
=================================

Data persistence for strategy configurations.
"""

import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .config_types import (
    StrategyConfiguration,
    StrategyConfigVersion,
    ConfigStatus,
    ConfigActivationEvent
)


class StrategyConfigRepository:
    """
    Repository for Strategy Configurations.
    
    Thread-safe singleton with MongoDB support.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # In-memory storage
        self._configs: Dict[str, StrategyConfiguration] = {}
        self._versions: Dict[str, List[StrategyConfigVersion]] = {}
        self._active_config_id: Optional[str] = None
        self._activation_history: List[ConfigActivationEvent] = []
        
        # MongoDB (lazy init)
        self._db = None
        self._configs_col = None
        self._versions_col = None
        
        self._initialized = True
        print("[StrategyConfigRepository] Initialized")
    
    def _get_collections(self):
        """Get MongoDB collections"""
        if self._configs_col is None:
            try:
                from pymongo import MongoClient
                
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "trading_capsule")
                
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._configs_col = self._db["strategy_configs"]
                self._versions_col = self._db["strategy_config_versions"]
                
                self._configs_col.create_index("config_id", unique=True)
                self._versions_col.create_index([("config_id", 1), ("version_number", -1)])
                
                print("[StrategyConfigRepository] MongoDB connected")
            except Exception as e:
                print(f"[StrategyConfigRepository] MongoDB error: {e}")
                self._configs_col = None
                self._versions_col = None
        
        return self._configs_col, self._versions_col
    
    # ===========================================
    # Config CRUD
    # ===========================================
    
    def save_config(self, config: StrategyConfiguration) -> StrategyConfiguration:
        """Save or update configuration"""
        config.updated_at = datetime.now(timezone.utc)
        self._configs[config.config_id] = config
        
        # Save to MongoDB
        configs_col, _ = self._get_collections()
        if configs_col is not None:
            try:
                configs_col.replace_one(
                    {"config_id": config.config_id},
                    config.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[StrategyConfigRepository] Save error: {e}")
        
        return config
    
    def get_config(self, config_id: str) -> Optional[StrategyConfiguration]:
        """Get configuration by ID"""
        return self._configs.get(config_id)
    
    def list_configs(
        self,
        status: Optional[ConfigStatus] = None,
        limit: int = 50
    ) -> List[StrategyConfiguration]:
        """List configurations with optional status filter"""
        configs = list(self._configs.values())
        
        if status:
            configs = [c for c in configs if c.status == status]
        
        configs.sort(key=lambda c: c.created_at, reverse=True)
        return configs[:limit]
    
    def delete_config(self, config_id: str) -> bool:
        """Delete configuration"""
        if config_id == self._active_config_id:
            return False  # Can't delete active config
        
        self._configs.pop(config_id, None)
        self._versions.pop(config_id, None)
        
        configs_col, versions_col = self._get_collections()
        if configs_col is not None:
            try:
                configs_col.delete_one({"config_id": config_id})
                if versions_col is not None:
                    versions_col.delete_many({"config_id": config_id})
            except Exception as e:
                print(f"[StrategyConfigRepository] Delete error: {e}")
        
        return True
    
    # ===========================================
    # Active Config
    # ===========================================
    
    def get_active_config_id(self) -> Optional[str]:
        """Get active configuration ID"""
        return self._active_config_id
    
    def get_active_config(self) -> Optional[StrategyConfiguration]:
        """Get active configuration"""
        if self._active_config_id:
            return self._configs.get(self._active_config_id)
        return None
    
    def set_active_config(
        self,
        config_id: str,
        activated_by: str = "admin",
        reason: str = ""
    ) -> bool:
        """Set configuration as active"""
        config = self._configs.get(config_id)
        if not config:
            return False
        
        # Record event
        event = ConfigActivationEvent(
            from_config_id=self._active_config_id or "",
            to_config_id=config_id,
            activated_by=activated_by,
            reason=reason
        )
        self._activation_history.append(event)
        
        # Deactivate old
        if self._active_config_id:
            old_config = self._configs.get(self._active_config_id)
            if old_config:
                old_config.is_active = False
                old_config.status = ConfigStatus.VALIDATED
                self.save_config(old_config)
        
        # Activate new
        config.is_active = True
        config.status = ConfigStatus.ACTIVE
        config.activated_at = datetime.now(timezone.utc)
        self.save_config(config)
        
        self._active_config_id = config_id
        
        return True
    
    # ===========================================
    # Versions
    # ===========================================
    
    def save_version(self, version: StrategyConfigVersion) -> StrategyConfigVersion:
        """Save configuration version"""
        if version.config_id not in self._versions:
            self._versions[version.config_id] = []
        self._versions[version.config_id].append(version)
        
        _, versions_col = self._get_collections()
        if versions_col is not None:
            try:
                versions_col.insert_one(version.to_dict())
            except Exception as e:
                print(f"[StrategyConfigRepository] Version save error: {e}")
        
        return version
    
    def get_versions(self, config_id: str) -> List[StrategyConfigVersion]:
        """Get all versions for a configuration"""
        return self._versions.get(config_id, [])
    
    def get_latest_version(self, config_id: str) -> Optional[StrategyConfigVersion]:
        """Get latest version for a configuration"""
        versions = self._versions.get(config_id, [])
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_number)
    
    # ===========================================
    # History
    # ===========================================
    
    def get_activation_history(self, limit: int = 50) -> List[ConfigActivationEvent]:
        """Get activation history"""
        return list(reversed(self._activation_history[-limit:]))
    
    # ===========================================
    # Stats
    # ===========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        return {
            "total_configs": len(self._configs),
            "active_config_id": self._active_config_id,
            "versions_count": sum(len(v) for v in self._versions.values()),
            "status_breakdown": {
                status.value: len([c for c in self._configs.values() if c.status == status])
                for status in ConfigStatus
            }
        }


# Global singleton
strategy_config_repository = StrategyConfigRepository()
