"""
Runtime Module Init (R2)
"""

from modules.runtime.service_locator import init_runtime_service, get_runtime_service
from modules.runtime.routes import router

__all__ = ["init_runtime_service", "get_runtime_service", "router"]
