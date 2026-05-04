"""
PHASE 13.2 - Alpha Feature Library
===================================
Base features for Alpha Factory.

300-500 features across 8 categories:
- Price Features (~70)
- Volatility Features (~60)
- Volume Features (~50)
- Liquidity Features (~50)
- Structure Features (~40)
- Microstructure Features (~50)
- Correlation Features (~40)
- Context Features (~40)
"""

from .feature_types import (
    Feature, FeatureCategory, FeatureTransform,
    FeatureStatus, DEFAULT_FEATURES
)
from .feature_registry import FeatureRegistry, get_feature_registry
from .feature_transforms import FeatureTransformer

__all__ = [
    "Feature",
    "FeatureCategory",
    "FeatureTransform",
    "FeatureStatus",
    "FeatureRegistry",
    "get_feature_registry",
    "FeatureTransformer",
    "DEFAULT_FEATURES"
]
