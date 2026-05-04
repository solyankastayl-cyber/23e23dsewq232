"""
PHASE 13.7 - Alpha Deployment Module
======================================
Converts approved factors into live alpha signals.

Components:
- deployment_types: Core data types
- deployment_registry: Manages deployed factors
- deployment_selector: Selects factors for deployment
- alpha_signal_engine: Generates live signals
- deployment_safety: Safety layer
- deployment_repository: MongoDB persistence
- deployment_routes: API endpoints
"""

from .deployment_types import (
    DeployedAlpha,
    AlphaSignal,
    DeploymentDecision,
    DeploymentStatus,
    DeploymentMode,
    SignalDirection,
    SignalQuality
)
from .deployment_registry import DeploymentRegistry, get_deployment_registry
from .deployment_selector import DeploymentSelector
from .alpha_signal_engine import AlphaSignalEngine, get_signal_engine
from .deployment_safety import DeploymentSafety

__all__ = [
    'DeployedAlpha',
    'AlphaSignal',
    'DeploymentDecision',
    'DeploymentStatus',
    'DeploymentMode',
    'SignalDirection',
    'SignalQuality',
    'DeploymentRegistry',
    'get_deployment_registry',
    'DeploymentSelector',
    'AlphaSignalEngine',
    'get_signal_engine',
    'DeploymentSafety'
]
