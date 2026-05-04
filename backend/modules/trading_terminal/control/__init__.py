"""
TT5 - Operator Control Layer
=============================
Control layer between Alpha Factory and Adaptive Layer.

Provides:
- Global Trading State (ACTIVE/PAUSED/SOFT_KILL/HARD_KILL/EMERGENCY)
- Entry Control (new_entries_enabled, position_management_enabled)
- Alpha Mode Control (AUTO/MANUAL/OFF)
- Pending Actions Queue (approve/reject)
- Kill switches and overrides
"""

from .control_routes import router

__all__ = ["router"]
