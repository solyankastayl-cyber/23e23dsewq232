"""
Kill Switch — Emergency Stop

CRITICAL: Global trading control.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class KillSwitch:
    """
    Global kill switch for trading.
    
    When activated:
    - All strategy loops stop
    - No new positions
    - Existing positions remain (manual close required)
    """
    
    def __init__(self, db):
        self.db = db
        self._state_collection = db.kill_switch_state
        logger.info("[KillSwitch] Initialized")
    
    async def is_active(self) -> bool:
        """
        Check if kill switch is active.
        
        Returns:
            True if trading is STOPPED
        """
        state = await self._state_collection.find_one({"_id": "global"})
        
        if not state:
            return False
        
        return state.get("active", False)
    
    async def activate(self, reason: str = "Manual stop") -> dict:
        """
        Activate kill switch (STOP ALL TRADING).
        
        Args:
            reason: Reason for activation
        
        Returns:
            Status dict
        """
        await self._state_collection.update_one(
            {"_id": "global"},
            {
                "$set": {
                    "active": True,
                    "reason": reason,
                    "activated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True
        )
        
        logger.error(f"[KillSwitch] 🔴 ACTIVATED: {reason}")
        
        return {
            "ok": True,
            "active": True,
            "reason": reason,
            "message": "All trading STOPPED"
        }
    
    async def deactivate(self) -> dict:
        """
        Deactivate kill switch (RESUME TRADING).
        
        Returns:
            Status dict
        """
        await self._state_collection.update_one(
            {"_id": "global"},
            {
                "$set": {
                    "active": False,
                    "reason": None,
                    "deactivated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True
        )
        
        logger.info("[KillSwitch] ✅ DEACTIVATED: Trading resumed")
        
        return {
            "ok": True,
            "active": False,
            "message": "Trading RESUMED"
        }
    
    async def get_status(self) -> dict:
        """
        Get kill switch status.
        
        Returns:
            Status dict
        """
        state = await self._state_collection.find_one({"_id": "global"})
        
        if not state:
            return {
                "active": False,
                "reason": None,
                "activated_at": None
            }
        
        return {
            "active": state.get("active", False),
            "reason": state.get("reason"),
            "activated_at": state.get("activated_at"),
            "deactivated_at": state.get("deactivated_at")
        }


# Singleton instance
_kill_switch = None


def init_kill_switch(db):
    """Initialize kill switch singleton."""
    global _kill_switch
    _kill_switch = KillSwitch(db)
    logger.info("[KillSwitch] Singleton initialized")


def get_kill_switch() -> KillSwitch:
    """Get kill switch singleton."""
    if _kill_switch is None:
        raise RuntimeError("KillSwitch not initialized. Call init_kill_switch() first.")
    return _kill_switch
