"""
Strategy Configuration Module (STR2)
====================================

Strategy Configuration Engine for dynamic parameter management.

Features:
- Create/update configurations without code changes
- Parameter validation with bounds checking
- Configuration versioning
- Rollback capability
- Risk assessment
- Config comparison

Pipeline:
Signal → Strategy Runtime → Config Engine → Execution
"""

from .config_types import (
    StrategyConfiguration,
    StrategyConfigVersion,
    ConfigValidationResult,
    ConfigComparison,
    ConfigActivationEvent,
    ConfigStatus,
    MarketMode,
    HoldingHorizon,
    PARAMETER_BOUNDS
)

from .config_repository import strategy_config_repository
from .config_service import strategy_config_service

__all__ = [
    # Types
    "StrategyConfiguration",
    "StrategyConfigVersion",
    "ConfigValidationResult",
    "ConfigComparison",
    "ConfigActivationEvent",
    "ConfigStatus",
    "MarketMode",
    "HoldingHorizon",
    "PARAMETER_BOUNDS",
    
    # Services
    "strategy_config_repository",
    "strategy_config_service"
]
