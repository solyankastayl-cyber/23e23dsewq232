"""
Metrics Module (S1.4)
=====================

Post-simulation metrics and trade analysis.

S1.4A - Trade Normalization:
- Trade Builder (fills → trades)
- Trade Normalizer Service
- Trade Statistics

S1.4B - Performance Metrics:
- Sharpe Ratio, Sortino Ratio
- Total Return, Annual Return (CAGR)
- Profit Factor, Expectancy
- Volatility, Downside Deviation

S1.4C - Risk Metrics:
- Max Drawdown, Avg Drawdown
- Drawdown Duration
- Recovery Factor, Calmar Ratio

S1.4D - Combined Metrics API:
- Unified metrics endpoint
- Full metrics snapshot
"""

from .trade_types import (
    TradeSide,
    TradeStatus,
    ClosedTrade,
    OpenPosition,
    TradeStats
)

from .trade_builder import (
    TradeBuilder,
    compute_trade_stats
)

from .trade_normalizer_service import (
    TradeNormalizerService,
    trade_normalizer_service
)

from .performance_types import (
    PerformanceMetrics,
    MetricsConfig,
    EquityPoint,
    ReturnSeries
)

from .performance_metrics_service import (
    PerformanceMetricsService,
    performance_metrics_service
)

from .risk_types import (
    RiskMetrics,
    DrawdownInfo,
    MetricsSnapshot
)

from .risk_metrics_service import (
    RiskMetricsService,
    risk_metrics_service
)

from .metrics_store import (
    MetricsStoreService,
    metrics_store_service
)

from .metrics_routes import router as metrics_router


__all__ = [
    # Trade Types
    "TradeSide",
    "TradeStatus",
    "ClosedTrade",
    "OpenPosition",
    "TradeStats",
    
    # Trade Builder
    "TradeBuilder",
    "compute_trade_stats",
    
    # Trade Normalizer Service
    "TradeNormalizerService",
    "trade_normalizer_service",
    
    # Performance Types
    "PerformanceMetrics",
    "MetricsConfig",
    "EquityPoint",
    "ReturnSeries",
    
    # Performance Service
    "PerformanceMetricsService",
    "performance_metrics_service",
    
    # Risk Types
    "RiskMetrics",
    "DrawdownInfo",
    "MetricsSnapshot",
    
    # Risk Service
    "RiskMetricsService",
    "risk_metrics_service",
    
    # Metrics Store
    "MetricsStoreService",
    "metrics_store_service",
    
    # Routes
    "metrics_router"
]


print("[Metrics] Module loaded - S1.4A/S1.4B/S1.4C/S1.4D Ready")
