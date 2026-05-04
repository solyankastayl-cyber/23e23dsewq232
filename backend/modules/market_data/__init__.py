"""
Market Data Module - PHASE 5.2
==============================

Live Market Data Engine for real-time market feeds.

Components:
- market_data_types: Unified types for ticks, candles, orderbooks, snapshots
- market_data_engine: Main orchestrator
- market_data_normalizer: Exchange data normalization
- candle_builder: Builds live candles from ticks
- stream_processors: Ticker, Orderbook, Volume processors
- market_snapshot_builder: Aggregated market snapshots
- market_data_repository: Persistence layer
- market_data_routes: REST API endpoints
"""

from .market_data_types import (
    Timeframe,
    MarketDataSource,
    MarketTick,
    MarketCandle,
    MarketOrderbook,
    OrderbookLevel,
    MarketSnapshot,
    VolumeMetrics,
    MarketFeedConfig,
    MarketFeedStatus
)

from .market_data_engine import MarketDataEngine, get_market_data_engine
from .market_data_normalizer import MarketDataNormalizer
from .candle_builder import CandleBuilder, get_candle_builder
from .stream_processors import (
    TickerStreamProcessor,
    OrderbookStreamProcessor,
    VolumeStreamProcessor,
    get_ticker_processor,
    get_orderbook_processor,
    get_volume_processor
)
from .market_snapshot_builder import MarketSnapshotBuilder, get_snapshot_builder

__all__ = [
    # Types
    "Timeframe",
    "MarketDataSource",
    "MarketTick",
    "MarketCandle",
    "MarketOrderbook",
    "OrderbookLevel",
    "MarketSnapshot",
    "VolumeMetrics",
    "MarketFeedConfig",
    "MarketFeedStatus",
    
    # Engine
    "MarketDataEngine",
    "get_market_data_engine",
    
    # Components
    "MarketDataNormalizer",
    "CandleBuilder",
    "get_candle_builder",
    "TickerStreamProcessor",
    "OrderbookStreamProcessor",
    "VolumeStreamProcessor",
    "get_ticker_processor",
    "get_orderbook_processor",
    "get_volume_processor",
    "MarketSnapshotBuilder",
    "get_snapshot_builder"
]
