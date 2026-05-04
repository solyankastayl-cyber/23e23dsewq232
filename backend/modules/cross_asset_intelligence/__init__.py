"""
PHASE 25.3 — Cross-Asset Intelligence Module

Implements the causal chain: Macro → DXY → SPX → BTC
"""

from .cross_asset_types import (
    CrossAssetBridge,
    CrossAssetAlignment,
    CrossAssetSummary,
    CrossAssetHealthStatus,
    AlignmentType,
    InfluenceDirection,
    AlignmentStateType,
    FinalBiasType,
    ALIGNMENT_MULTIPLIERS,
    ALIGNMENT_STATE_THRESHOLDS,
    BRIDGE_WEIGHTS,
)
from .macro_dxy_bridge import MacroDxyBridge, get_macro_dxy_bridge
from .dxy_spx_bridge import DxySpxBridge, get_dxy_spx_bridge
from .spx_btc_bridge import SpxBtcBridge, get_spx_btc_bridge
from .cross_asset_engine import CrossAssetEngine, get_cross_asset_engine
from .cross_asset_routes import router as cross_asset_router

__all__ = [
    # Types
    "CrossAssetBridge",
    "CrossAssetAlignment",
    "CrossAssetSummary",
    "CrossAssetHealthStatus",
    "AlignmentType",
    "InfluenceDirection",
    "AlignmentStateType",
    "FinalBiasType",
    # Constants
    "ALIGNMENT_MULTIPLIERS",
    "ALIGNMENT_STATE_THRESHOLDS",
    "BRIDGE_WEIGHTS",
    # Bridges
    "MacroDxyBridge",
    "get_macro_dxy_bridge",
    "DxySpxBridge",
    "get_dxy_spx_bridge",
    "SpxBtcBridge",
    "get_spx_btc_bridge",
    # Engine
    "CrossAssetEngine",
    "get_cross_asset_engine",
    # Routes
    "cross_asset_router",
]
