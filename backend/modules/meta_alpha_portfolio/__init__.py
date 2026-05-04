"""Meta-Alpha Portfolio Module — PHASE 45"""

from .meta_portfolio_types import (
    AlphaFamily,
    PatternClass,
    MetaAlphaWeight,
    MetaAlphaPortfolioState,
    MetaAlphaConfig,
    TradeOutcome,
    META_SCORE_WEIGHTS,
    PATTERN_THRESHOLDS,
)
from .meta_portfolio_engine import MetaAlphaPortfolioEngine, get_meta_alpha_engine
from .meta_portfolio_routes import router as meta_alpha_router

__all__ = [
    "AlphaFamily",
    "PatternClass",
    "MetaAlphaWeight",
    "MetaAlphaPortfolioState",
    "MetaAlphaConfig",
    "TradeOutcome",
    "META_SCORE_WEIGHTS",
    "PATTERN_THRESHOLDS",
    "MetaAlphaPortfolioEngine",
    "get_meta_alpha_engine",
    "meta_alpha_router",
]
