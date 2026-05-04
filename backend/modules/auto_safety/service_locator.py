"""
Auto Safety Service Locator
============================
Sprint A4: Singleton pattern for global access
"""

from __future__ import annotations

import logging
from typing import Optional

from .service import AutoSafetyService

logger = logging.getLogger(__name__)

_auto_safety_service: Optional[AutoSafetyService] = None


def init_auto_safety_service(service: AutoSafetyService) -> None:
    """Initialize auto safety service singleton"""
    global _auto_safety_service
    _auto_safety_service = service
    logger.info("[AutoSafety] Service locator initialized")


def get_auto_safety_service() -> AutoSafetyService:
    """Get auto safety service singleton"""
    if _auto_safety_service is None:
        raise RuntimeError("AutoSafetyService not initialized")
    return _auto_safety_service
