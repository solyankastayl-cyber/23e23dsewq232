"""
Cross-Asset Similarity Module

PHASE 32.4 — Cross-Asset Similarity Engine

Finds patterns across different assets:
- BTC now ≈ ETH 2021
- BTC now ≈ SPX 2018
- ETH now ≈ BTC 2020
"""

from .cross_similarity_engine import (
    CrossAssetSimilarityEngine,
    get_cross_similarity_engine,
)

from .cross_similarity_types import (
    StructureVector,
    CrossAssetMatch,
    CrossAssetAnalysis,
    CrossAssetModifier,
    CrossAssetSummary,
    ASSET_UNIVERSE,
    CRYPTO_ASSETS,
    TRADITIONAL_ASSETS,
    SIMILARITY_THRESHOLD,
)

from .cross_similarity_routes import router as cross_similarity_router

__all__ = [
    "CrossAssetSimilarityEngine",
    "get_cross_similarity_engine",
    "StructureVector",
    "CrossAssetMatch",
    "CrossAssetAnalysis",
    "CrossAssetModifier",
    "CrossAssetSummary",
    "ASSET_UNIVERSE",
    "CRYPTO_ASSETS",
    "TRADITIONAL_ASSETS",
    "SIMILARITY_THRESHOLD",
    "cross_similarity_router",
]
