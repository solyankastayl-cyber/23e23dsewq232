"""
Strategy Profiles Module (STR1)
===============================

Strategy Profile Engine for trading mode management.

Profiles: CONSERVATIVE, BALANCED, AGGRESSIVE

Each profile controls:
- Risk parameters
- Position sizing
- Signal thresholds
- Holding periods
- Leverage limits
- Stop loss / take profit

Usage:
- Switch profile in admin panel
- All trading adapts automatically
"""

from .profile_types import (
    StrategyProfile,
    ProfileMode,
    MarketMode,
    HoldingHorizon,
    RiskLevel,
    ProfileSwitchEvent,
    ProfileValidationResult,
    ProfileSummary
)

from .profile_registry import (
    CONSERVATIVE_PROFILE,
    BALANCED_PROFILE,
    AGGRESSIVE_PROFILE,
    PROFILE_REGISTRY,
    get_profile,
    get_all_profiles,
    get_profile_by_name,
    compare_profiles
)

from .profile_service import strategy_profile_service
from .profile_router import profile_router

__all__ = [
    # Types
    "StrategyProfile",
    "ProfileMode",
    "MarketMode",
    "HoldingHorizon",
    "RiskLevel",
    "ProfileSwitchEvent",
    "ProfileValidationResult",
    "ProfileSummary",
    
    # Profiles
    "CONSERVATIVE_PROFILE",
    "BALANCED_PROFILE",
    "AGGRESSIVE_PROFILE",
    "PROFILE_REGISTRY",
    
    # Functions
    "get_profile",
    "get_all_profiles",
    "get_profile_by_name",
    "compare_profiles",
    
    # Services
    "strategy_profile_service",
    "profile_router"
]
