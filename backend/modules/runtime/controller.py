"""
Runtime Controller — State Owner (R2 version)
"""

import time
import logging
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_RUNTIME_STATE = {
    "config_id": "main",
    "enabled": False,
    "mode": "MANUAL",
    "status": "IDLE",
    "loop_interval_sec": 60,
    "symbols": ["BTCUSDT"],
    "last_run_at": None,
    "next_run_at": None,
    "last_error": None,
    "updated_at": None,
}


class RuntimeController:
    """Manages runtime state and configuration."""
    
    def __init__(self, db):
        self.db = db
        self.col = db.runtime_config
        logger.info("[RuntimeController] Initialized")
    
    async def _get_or_create(self) -> Dict[str, Any]:
        """Get or create runtime config."""
        doc = await self.col.find_one({"config_id": "main"})
        if doc:
            return doc
        
        state = DEFAULT_RUNTIME_STATE.copy()
        state["updated_at"] = int(time.time())
        await self.col.insert_one(state)
        return await self.col.find_one({"config_id": "main"})
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current runtime state."""
        doc = await self._get_or_create()
        # Remove MongoDB _id to avoid FastAPI serialization error
        if "_id" in doc:
            del doc["_id"]
        return doc
    
    async def _patch(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Patch runtime state."""
        patch["updated_at"] = int(time.time())
        await self.col.update_one(
            {"config_id": "main"},
            {"$set": patch},
            upsert=True
        )
        return await self.get_state()
    
    async def start(self) -> Dict[str, Any]:
        """Enable runtime."""
        logger.info("[RuntimeController] Runtime started")
        return await self._patch({"enabled": True, "status": "IDLE"})
    
    async def stop(self) -> Dict[str, Any]:
        """Disable runtime."""
        logger.info("[RuntimeController] Runtime stopped")
        return await self._patch({"enabled": False, "status": "STOPPED"})
    
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set runtime mode."""
        if mode not in ["MANUAL", "SEMI_AUTO", "AUTO"]:
            raise ValueError(f"Invalid mode: {mode}")
        logger.info(f"[RuntimeController] Mode set to {mode}")
        return await self._patch({"mode": mode})
    
    async def set_symbols(self, symbols: list) -> Dict[str, Any]:
        """Update symbols universe."""
        logger.info(f"[RuntimeController] Symbols updated: {symbols}")
        return await self._patch({"symbols": symbols})
    
    async def set_interval(self, interval_sec: int) -> Dict[str, Any]:
        """Update loop interval."""
        logger.info(f"[RuntimeController] Interval set to {interval_sec}s")
        return await self._patch({"loop_interval_sec": interval_sec})
    
    async def mark_running(self) -> Dict[str, Any]:
        """Mark runtime as running."""
        return await self._patch({"status": "RUNNING"})
    
    async def mark_idle(self) -> Dict[str, Any]:
        """Mark runtime as idle after successful run."""
        state = await self.get_state()
        now = int(time.time())
        interval_sec = state.get("loop_interval_sec", 60)
        return await self._patch({
            "status": "IDLE",
            "last_run_at": now,
            "next_run_at": now + interval_sec,
            "last_error": None
        })
    
    async def mark_error(self, error: str) -> Dict[str, Any]:
        """Mark runtime error."""
        logger.error(f"[RuntimeController] Runtime error: {error}")
        return await self._patch({"status": "ERROR", "last_error": error})
