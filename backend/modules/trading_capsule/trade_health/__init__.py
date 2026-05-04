"""
PHASE 3.2 - Advanced Trade Health Engine
=========================================

Modules:
- trade_health_engine.py - Core health monitoring
- health_event_engine.py - Event detection and tracking
- health_decay_engine.py - Health decay over time
- health_alert_engine.py - Alert generation
- health_repository.py - Data persistence
- health_routes.py - API endpoints

Health Flow:
Position -> Health Engine -> Events -> Decay -> Alerts -> Actions
"""

from .trade_health_engine import AdvancedTradeHealthEngine, advanced_trade_health_engine
from .health_event_engine import HealthEventEngine, health_event_engine
from .health_decay_engine import HealthDecayEngine, health_decay_engine
from .health_alert_engine import HealthAlertEngine, health_alert_engine
from .health_repository import health_repository

__all__ = [
    "AdvancedTradeHealthEngine",
    "advanced_trade_health_engine",
    "HealthEventEngine",
    "health_event_engine", 
    "HealthDecayEngine",
    "health_decay_engine",
    "HealthAlertEngine",
    "health_alert_engine",
    "health_repository"
]
