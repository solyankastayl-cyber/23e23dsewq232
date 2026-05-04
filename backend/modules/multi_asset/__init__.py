"""
Multi-Asset Scaling — PHASE 2.8

Transforms the system from 3-asset toy to 50+ asset trading engine:
- Universe registry (centralized asset list)
- Cluster/sector mapping
- Multi-asset backtest runner (single portfolio stream)
- Cross-asset constraints
- Symbol diagnostics & ranking
"""

from .universe_registry import UniverseRegistry
from .asset_classifier import AssetClassifier
from .cluster_engine import ClusterEngine
from .multi_asset_runner import MultiAssetRunner
from .cross_asset_constraints import CrossAssetConstraints
from .symbol_diagnostics import SymbolDiagnostics
from .symbol_ranker import SymbolRanker
