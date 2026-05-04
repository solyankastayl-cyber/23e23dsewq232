"""
Analytics Module
Phase 4: Operational Analytics Layer
"""

from .service import AnalyticsService, get_analytics_service, init_analytics_service
from .routes import router

__all__ = [
    "AnalyticsService",
    "get_analytics_service",
    "init_analytics_service",
    "router"
]
