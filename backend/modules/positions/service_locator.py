"""
Position Sync Service Locator
Sprint A5: Singleton for global access
Sprint A7: Added ProtectionWatcher singleton
"""

import logging

logger = logging.getLogger(__name__)

_position_sync_service = None
_protection_watcher = None


def init_position_sync_service(service):
    global _position_sync_service
    
    if _position_sync_service is not None:
        logger.warning("⚠️ PositionSyncService already initialized")
    
    _position_sync_service = service
    logger.info(f"✅ PositionSyncService initialized: {id(service)}")


def get_position_sync_service():
    if _position_sync_service is None:
        raise RuntimeError("PositionSyncService not initialized")
    
    return _position_sync_service


def init_protection_watcher(watcher):
    global _protection_watcher
    
    if _protection_watcher is not None:
        logger.warning("⚠️ ProtectionWatcher already initialized")
    
    _protection_watcher = watcher
    logger.info(f"✅ ProtectionWatcher initialized: {id(watcher)}")


def get_protection_watcher():
    if _protection_watcher is None:
        raise RuntimeError("ProtectionWatcher not initialized")
    
    return _protection_watcher
