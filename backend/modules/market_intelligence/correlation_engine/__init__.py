# PHASE 7 Correlation Intelligence
# Cross-asset correlation analysis and regime detection

from .correlation_types import (
    CorrelationMethod, CorrelationStrength, CorrelationRegime,
    AssetClass, AssetPair, CorrelationValue, RollingCorrelation,
    LeadLagResult, RegimeState, CrossAssetSignal,
    DEFAULT_PAIRS, REGIME_THRESHOLDS
)
from .correlation_matrix import CorrelationMatrixEngine
from .rolling_correlation import RollingCorrelationEngine
from .lead_lag_detector import LeadLagDetector
from .regime_classifier import RegimeClassifier
from .cross_asset_signals import CrossAssetSignalGenerator
from .correlation_repository import CorrelationRepository
from .correlation_routes import router

__all__ = [
    # Types
    "CorrelationMethod", "CorrelationStrength", "CorrelationRegime",
    "AssetClass", "AssetPair", "CorrelationValue", "RollingCorrelation",
    "LeadLagResult", "RegimeState", "CrossAssetSignal",
    "DEFAULT_PAIRS", "REGIME_THRESHOLDS",
    # Engines
    "CorrelationMatrixEngine", "RollingCorrelationEngine",
    "LeadLagDetector", "RegimeClassifier", "CrossAssetSignalGenerator",
    # Repository
    "CorrelationRepository",
    # Router
    "router"
]
