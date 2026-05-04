"""
PHASE 11.6 - Adaptive Safety Layer
===================================
Critical layer preventing over-adaptation and self-destruction.

Components:
- Change Guard (validates changes)
- Cooldown Manager (prevents rapid changes)
- Shadow Mode Engine (parallel testing)
- OOS Gate (out-of-sample validation)
- Change Audit (tracking all changes)

This layer MUST be between Adaptive Intelligence and actual changes!
"""

from .change_guard import ChangeGuard
from .cooldown_manager import CooldownManager
from .shadow_mode_engine import ShadowModeEngine
from .oos_gate import OOSGate
from .change_audit import ChangeAudit
from .adaptive_limits import AdaptiveLimits

__all__ = [
    'ChangeGuard',
    'CooldownManager',
    'ShadowModeEngine',
    'OOSGate',
    'ChangeAudit',
    'AdaptiveLimits'
]
