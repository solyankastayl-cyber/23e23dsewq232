"""
Observability Module
====================

Phase 2.8: System self-awareness and degradation detection.

Components:
  - alert_engine: Core alert evaluation logic
  - alert_rules: Alert rule definitions (5 types)
  - alert_storage: MongoDB storage with anti-spam
  - health_service: Health status aggregation

Architecture:
  Decisions → Outcomes → Validation → ALERTS → Awareness

CRITICAL: This is observation-only. NO auto-adaptation.
"""

from .alert_engine import AlertEngine, get_alert_engine
from .alert_storage import AlertStorage
from .health_service import HealthService, get_health_service

__all__ = [
    "AlertEngine",
    "get_alert_engine",
    "AlertStorage",
    "HealthService",
    "get_health_service",
]
