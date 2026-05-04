"""
Service Locator for Runtime
"""

import logging
import sys

logger = logging.getLogger(__name__)

# ⚠️ Runtime Guard: Detect wrong import paths
_expected_module_name = "modules.runtime.service_locator"
if __name__ != _expected_module_name:
    logger.error(f"❌ CRITICAL: service_locator imported from WRONG path!")
    logger.error(f"   Expected: {_expected_module_name}")
    logger.error(f"   Got: {__name__}")
    logger.error("   This will break singleton! Fix all imports to use 'from modules.runtime...'")

_runtime_service = None


def init_runtime_service(service):
    """Initialize runtime service singleton (FAIL-FAST)."""
    global _runtime_service
    
    if _runtime_service is not None:
        logger.warning(f"⚠️ RuntimeService ALREADY initialized! Previous instance id: {id(_runtime_service)}")
    
    _runtime_service = service
    logger.info(f"[RuntimeServiceLocator] ✅ Service initialized (instance id: {id(_runtime_service)})")
    logger.info(f"[RuntimeServiceLocator] Module path: {__name__}")
    return _runtime_service


def get_runtime_service():
    """Get runtime service singleton (FAIL-FAST with debug)."""
    if _runtime_service is None:
        logger.error(f"❌ RuntimeService NOT initialized!")
        logger.error(f"   Module path: {__name__}")
        logger.error(f"   sys.modules keys containing 'service_locator': {[k for k in sys.modules if 'service_locator' in k]}")
        raise RuntimeError("Runtime service is not initialized")
    
    # Debug: Log every access with instance id
    logger.debug(f"[RuntimeServiceLocator] Returning service (instance id: {id(_runtime_service)})")
    return _runtime_service
