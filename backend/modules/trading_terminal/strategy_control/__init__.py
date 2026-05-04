"""
Strategy Control Module (TR5)
=============================

Admin terminal control for trading strategies.

Features:
- Profile switching (manual override)
- Config switching
- Trading pause/resume
- Kill switch (soft/hard)
- Override mode

Architecture:
    TR5 Strategy Control
    ├── control_types.py        # Type definitions
    ├── control_repository.py   # DB operations
    ├── control_service.py      # Main service
    ├── profile_switch_service.py
    ├── config_switch_service.py
    ├── trading_pause_service.py
    ├── kill_switch_service.py
    ├── override_service.py
    └── control_routes.py       # API routes
"""

from .control_service import strategy_control_service
from .control_types import (
    ControlMode,
    KillSwitchMode,
    StrategyControlState,
    StrategyControlEvent,
    KillSwitchConfig
)

__all__ = [
    "strategy_control_service",
    "ControlMode",
    "KillSwitchMode", 
    "StrategyControlState",
    "StrategyControlEvent",
    "KillSwitchConfig"
]
