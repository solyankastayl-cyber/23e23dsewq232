"""
PHASE 26.4 — Alpha Registry

Storage and tracking for alpha factors.

Collections:
- alpha_factor_registry: Current factor state
- alpha_factor_history: Historical metrics

Features:
- Store ACTIVE/DEPRECATED factors
- Track factor evolution over time
- Duplicate protection
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import os

from motor.motor_asyncio import AsyncIOMotorClient

from .factor_types import AlphaFactor, FactorCategory, FactorStatus


# ══════════════════════════════════════════════════════════════
# Registry Models
# ══════════════════════════════════════════════════════════════

class RegistryAlphaFactor(BaseModel):
    """Factor as stored in registry."""
    factor_id: str
    name: str
    category: FactorCategory
    lookback: int
    
    alpha_score: float
    signal_strength: float
    sharpe_score: float
    stability_score: float
    drawdown_score: float
    
    status: FactorStatus
    
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source: str = ""
    
    created_at: datetime
    last_updated: datetime


class AlphaFactorHistory(BaseModel):
    """Historical record of factor metrics."""
    factor_id: str
    alpha_score: float
    sharpe_score: float
    stability_score: float
    drawdown_score: float
    status: FactorStatus
    recorded_at: datetime


class RegistrySummary(BaseModel):
    """Summary of registry state."""
    total_factors: int
    active_factors: int
    deprecated_factors: int
    top_factor: Optional[str]
    average_alpha_score: float


# ══════════════════════════════════════════════════════════════
# Alpha Registry Engine
# ══════════════════════════════════════════════════════════════

class AlphaRegistry:
    """
    Alpha Factor Registry.
    
    Stores and tracks alpha factors in MongoDB.
    
    Collections:
    - alpha_factor_registry: Current state
    - alpha_factor_history: Historical metrics
    """
    
    REGISTRY_COLLECTION = "alpha_factor_registry"
    HISTORY_COLLECTION = "alpha_factor_history"
    
    def __init__(self, db=None):
        """
        Initialize registry.
        
        Args:
            db: MongoDB database instance. If None, connects to MONGO_URL.
        """
        self._db = db
        self._client = None
        self._initialized = False
        
        # In-memory cache for testing without DB
        self._cache: Dict[str, RegistryAlphaFactor] = {}
        self._history_cache: List[AlphaFactorHistory] = []
        self._use_cache = db is None
    
    async def _get_db(self):
        """Get or create database connection."""
        if self._db is not None:
            return self._db
        
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        if mongo_url:
            if self._client is None:
                self._client = AsyncIOMotorClient(mongo_url)
            return self._client[db_name]
        
        # No DB available, use cache
        self._use_cache = True
        return None
    
    # ═══════════════════════════════════════════════════════════
    # Core Operations
    # ═══════════════════════════════════════════════════════════
    
    async def register_factor(
        self,
        factor: AlphaFactor,
    ) -> RegistryAlphaFactor:
        """
        Register a new factor or update existing.
        
        If factor_id exists, updates instead.
        """
        now = datetime.utcnow()
        
        # Check if exists
        existing = await self.get_factor(factor.factor_id)
        
        if existing:
            # Update existing
            return await self.update_factor(factor)
        
        # Create new registry entry
        registry_factor = RegistryAlphaFactor(
            factor_id=factor.factor_id,
            name=factor.name,
            category=factor.category,
            lookback=factor.lookback,
            alpha_score=factor.alpha_score,
            signal_strength=factor.signal_strength,
            sharpe_score=factor.sharpe_score,
            stability_score=factor.stability_score,
            drawdown_score=factor.drawdown_score,
            status=factor.status,
            parameters=factor.parameters,
            source=factor.source,
            created_at=now,
            last_updated=now,
        )
        
        if self._use_cache:
            self._cache[factor.factor_id] = registry_factor
        else:
            db = await self._get_db()
            if db:
                await db[self.REGISTRY_COLLECTION].insert_one(
                    registry_factor.model_dump()
                )
        
        # Store initial history
        await self._store_history(registry_factor)
        
        return registry_factor
    
    async def update_factor(
        self,
        factor: AlphaFactor,
    ) -> RegistryAlphaFactor:
        """
        Update an existing factor's metrics.
        """
        now = datetime.utcnow()
        
        existing = await self.get_factor(factor.factor_id)
        
        if not existing:
            # Register if not exists
            return await self.register_factor(factor)
        
        # Update registry entry
        registry_factor = RegistryAlphaFactor(
            factor_id=factor.factor_id,
            name=factor.name,
            category=factor.category,
            lookback=factor.lookback,
            alpha_score=factor.alpha_score,
            signal_strength=factor.signal_strength,
            sharpe_score=factor.sharpe_score,
            stability_score=factor.stability_score,
            drawdown_score=factor.drawdown_score,
            status=factor.status,
            parameters=factor.parameters,
            source=factor.source,
            created_at=existing.created_at,  # Preserve original
            last_updated=now,
        )
        
        if self._use_cache:
            self._cache[factor.factor_id] = registry_factor
        else:
            db = await self._get_db()
            if db:
                await db[self.REGISTRY_COLLECTION].update_one(
                    {"factor_id": factor.factor_id},
                    {"$set": registry_factor.model_dump()}
                )
        
        # Store history
        await self._store_history(registry_factor)
        
        return registry_factor
    
    async def archive_factor(
        self,
        factor_id: str,
    ) -> Optional[RegistryAlphaFactor]:
        """
        Archive (deprecate) a factor.
        """
        existing = await self.get_factor(factor_id)
        
        if not existing:
            return None
        
        # Update status to DEPRECATED
        now = datetime.utcnow()
        
        archived = RegistryAlphaFactor(
            factor_id=existing.factor_id,
            name=existing.name,
            category=existing.category,
            lookback=existing.lookback,
            alpha_score=existing.alpha_score,
            signal_strength=existing.signal_strength,
            sharpe_score=existing.sharpe_score,
            stability_score=existing.stability_score,
            drawdown_score=existing.drawdown_score,
            status="DEPRECATED",
            parameters=existing.parameters,
            source=existing.source,
            created_at=existing.created_at,
            last_updated=now,
        )
        
        if self._use_cache:
            self._cache[factor_id] = archived
        else:
            db = await self._get_db()
            if db:
                await db[self.REGISTRY_COLLECTION].update_one(
                    {"factor_id": factor_id},
                    {"$set": {"status": "DEPRECATED", "last_updated": now}}
                )
        
        # Store history
        await self._store_history(archived)
        
        return archived
    
    async def register_factors_bulk(
        self,
        factors: List[AlphaFactor],
    ) -> List[RegistryAlphaFactor]:
        """
        Register multiple factors at once.
        """
        results = []
        for factor in factors:
            result = await self.register_factor(factor)
            results.append(result)
        return results
    
    # ═══════════════════════════════════════════════════════════
    # History
    # ═══════════════════════════════════════════════════════════
    
    async def _store_history(
        self,
        factor: RegistryAlphaFactor,
    ) -> None:
        """Store factor metrics in history."""
        history = AlphaFactorHistory(
            factor_id=factor.factor_id,
            alpha_score=factor.alpha_score,
            sharpe_score=factor.sharpe_score,
            stability_score=factor.stability_score,
            drawdown_score=factor.drawdown_score,
            status=factor.status,
            recorded_at=datetime.utcnow(),
        )
        
        if self._use_cache:
            self._history_cache.append(history)
        else:
            db = await self._get_db()
            if db:
                await db[self.HISTORY_COLLECTION].insert_one(
                    history.model_dump()
                )
    
    async def get_factor_history(
        self,
        factor_id: str,
        limit: int = 100,
    ) -> List[AlphaFactorHistory]:
        """
        Get historical metrics for a factor.
        """
        if self._use_cache:
            history = [h for h in self._history_cache if h.factor_id == factor_id]
            return sorted(history, key=lambda h: h.recorded_at, reverse=True)[:limit]
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.HISTORY_COLLECTION].find(
            {"factor_id": factor_id}
        ).sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(AlphaFactorHistory(**doc))
        
        return results
    
    # ═══════════════════════════════════════════════════════════
    # Retrieval
    # ═══════════════════════════════════════════════════════════
    
    async def get_factor(
        self,
        factor_id: str,
    ) -> Optional[RegistryAlphaFactor]:
        """Get factor by ID."""
        if self._use_cache:
            return self._cache.get(factor_id)
        
        db = await self._get_db()
        if not db:
            return None
        
        doc = await db[self.REGISTRY_COLLECTION].find_one(
            {"factor_id": factor_id}
        )
        
        if doc:
            doc.pop("_id", None)
            return RegistryAlphaFactor(**doc)
        
        return None
    
    async def get_all_factors(self) -> List[RegistryAlphaFactor]:
        """Get all factors."""
        if self._use_cache:
            return list(self._cache.values())
        
        db = await self._get_db()
        if not db:
            return []
        
        cursor = db[self.REGISTRY_COLLECTION].find()
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RegistryAlphaFactor(**doc))
        
        return results
    
    async def get_active_factors(self) -> List[RegistryAlphaFactor]:
        """Get only ACTIVE factors."""
        all_factors = await self.get_all_factors()
        return [f for f in all_factors if f.status == "ACTIVE"]
    
    async def get_deprecated_factors(self) -> List[RegistryAlphaFactor]:
        """Get only DEPRECATED factors."""
        all_factors = await self.get_all_factors()
        return [f for f in all_factors if f.status == "DEPRECATED"]
    
    async def get_top_factors(
        self,
        n: int = 10,
    ) -> List[RegistryAlphaFactor]:
        """Get top N factors by alpha_score."""
        all_factors = await self.get_all_factors()
        return sorted(
            all_factors,
            key=lambda f: f.alpha_score,
            reverse=True
        )[:n]
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(self) -> RegistrySummary:
        """Get registry summary."""
        all_factors = await self.get_all_factors()
        
        if not all_factors:
            return RegistrySummary(
                total_factors=0,
                active_factors=0,
                deprecated_factors=0,
                top_factor=None,
                average_alpha_score=0.0,
            )
        
        active = [f for f in all_factors if f.status == "ACTIVE"]
        deprecated = [f for f in all_factors if f.status == "DEPRECATED"]
        
        top_factor = max(all_factors, key=lambda f: f.alpha_score)
        avg_alpha = sum(f.alpha_score for f in all_factors) / len(all_factors)
        
        return RegistrySummary(
            total_factors=len(all_factors),
            active_factors=len(active),
            deprecated_factors=len(deprecated),
            top_factor=top_factor.name,
            average_alpha_score=round(avg_alpha, 4),
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_registry(self) -> None:
        """Clear all factors from registry (for testing)."""
        if self._use_cache:
            self._cache.clear()
            self._history_cache.clear()
        else:
            db = await self._get_db()
            if db:
                await db[self.REGISTRY_COLLECTION].delete_many({})
                await db[self.HISTORY_COLLECTION].delete_many({})
    
    def get_factor_count(self) -> int:
        """Get count of factors (cache only)."""
        return len(self._cache)


# Singleton
_registry: Optional[AlphaRegistry] = None


def get_alpha_registry() -> AlphaRegistry:
    """Get singleton instance of AlphaRegistry."""
    global _registry
    if _registry is None:
        _registry = AlphaRegistry()
    return _registry
