"""
Market Data Engine - PHASE 5.2
==============================

Main orchestrator for live market data.
Connects to exchange WebSocket feeds and distributes data to processors.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from collections import defaultdict
import asyncio

from .market_data_types import (
    MarketTick,
    MarketCandle,
    MarketOrderbook,
    MarketSnapshot,
    MarketFeedConfig,
    MarketFeedStatus,
    VolumeMetrics
)
from .market_data_normalizer import MarketDataNormalizer
from .candle_builder import get_candle_builder
from .stream_processors import (
    get_ticker_processor,
    get_orderbook_processor,
    get_volume_processor
)
from .market_snapshot_builder import get_snapshot_builder

# Import exchange layer
import sys
sys.path.append('/app/backend')
from modules.exchanges.exchange_router import get_exchange_router
from modules.exchanges.ws_manager import get_ws_manager, StreamConfig
from modules.exchanges.exchange_types import ExchangeId, StreamType


class MarketDataEngine:
    """
    Main market data orchestrator.
    
    Responsibilities:
    - Connect to exchange WebSocket feeds
    - Normalize incoming data
    - Distribute to processors
    - Build and cache snapshots
    - Provide unified API
    """
    
    def __init__(self):
        # Components
        self._normalizer = MarketDataNormalizer()
        self._candle_builder = get_candle_builder()
        self._ticker_processor = get_ticker_processor()
        self._orderbook_processor = get_orderbook_processor()
        self._volume_processor = get_volume_processor()
        self._snapshot_builder = get_snapshot_builder()
        
        # Feed status per exchange
        self._feed_status: Dict[str, MarketFeedStatus] = {}
        
        # Active subscriptions
        self._subscriptions: Dict[str, List[str]] = defaultdict(list)
        
        # Snapshot update task
        self._snapshot_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Data simulation for demo
        self._sim_task: Optional[asyncio.Task] = None
    
    # ============================================
    # Feed Management
    # ============================================
    
    async def start_feed(self, config: MarketFeedConfig) -> bool:
        """Start market data feed for exchange/symbols"""
        exchange = config.exchange.upper()
        symbols = config.symbols
        
        # Initialize status
        self._feed_status[exchange] = MarketFeedStatus(
            exchange=exchange,
            symbols=symbols,
            is_active=True,
            connected_at=datetime.utcnow(),
            ticker_subscribed=config.subscribe_ticker,
            orderbook_subscribed=config.subscribe_orderbook,
            candles_subscribed=config.subscribe_candles
        )
        
        # Store subscriptions
        self._subscriptions[exchange] = list(set(
            self._subscriptions[exchange] + symbols
        ))
        
        # Get WebSocket manager
        ws_manager = get_ws_manager()
        
        # Subscribe to streams
        try:
            exchange_id = ExchangeId(exchange)
            
            if config.subscribe_ticker:
                await ws_manager.start_stream(
                    StreamConfig(
                        exchange=exchange_id,
                        stream_type=StreamType.TICKER,
                        symbols=symbols
                    ),
                    callback=self._on_ticker_update
                )
                self._feed_status[exchange].ticker_subscribed = True
            
            if config.subscribe_orderbook:
                await ws_manager.start_stream(
                    StreamConfig(
                        exchange=exchange_id,
                        stream_type=StreamType.ORDERBOOK,
                        symbols=symbols
                    ),
                    callback=self._on_orderbook_update
                )
                self._feed_status[exchange].orderbook_subscribed = True
            
            if config.subscribe_candles:
                # Set candle timeframes
                self._candle_builder.set_timeframes(config.candle_timeframes)
                self._feed_status[exchange].candles_subscribed = True
            
        except Exception as e:
            print(f"Error starting feed for {exchange}: {e}")
            # Fallback to simulation
            pass
        
        # Start snapshot update loop
        if not self._running:
            self._running = True
            self._snapshot_task = asyncio.create_task(self._snapshot_loop())
            self._sim_task = asyncio.create_task(self._simulate_data(exchange, symbols))
        
        return True
    
    async def stop_feed(self, exchange: str, symbols: Optional[List[str]] = None) -> bool:
        """Stop market data feed"""
        exchange = exchange.upper()
        
        if symbols:
            # Remove specific symbols
            self._subscriptions[exchange] = [
                s for s in self._subscriptions[exchange] if s not in symbols
            ]
        else:
            # Remove all symbols for exchange
            self._subscriptions[exchange] = []
        
        # Update status
        if exchange in self._feed_status:
            self._feed_status[exchange].is_active = len(self._subscriptions[exchange]) > 0
            self._feed_status[exchange].symbols = self._subscriptions[exchange]
        
        # Stop WebSocket streams
        ws_manager = get_ws_manager()
        try:
            exchange_id = ExchangeId(exchange)
            await ws_manager.stop_stream(exchange_id, StreamType.TICKER, symbols)
            await ws_manager.stop_stream(exchange_id, StreamType.ORDERBOOK, symbols)
        except:
            pass
        
        return True
    
    async def stop_all(self) -> bool:
        """Stop all feeds"""
        self._running = False
        
        if self._snapshot_task:
            self._snapshot_task.cancel()
        if self._sim_task:
            self._sim_task.cancel()
        
        for exchange in list(self._subscriptions.keys()):
            await self.stop_feed(exchange)
        
        return True
    
    # ============================================
    # Data Access
    # ============================================
    
    def get_live_snapshot(self, symbol: str) -> MarketSnapshot:
        """Get live market snapshot for symbol"""
        return self._snapshot_builder.build_snapshot(symbol)
    
    def get_live_ticker(self, exchange: str, symbol: str) -> Optional[MarketTick]:
        """Get live ticker"""
        return self._ticker_processor.get_latest_tick(exchange.upper(), symbol)
    
    def get_live_orderbook(self, exchange: str, symbol: str) -> Optional[MarketOrderbook]:
        """Get live orderbook"""
        return self._orderbook_processor.get_orderbook(exchange.upper(), symbol)
    
    def get_live_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[MarketCandle]:
        """Get live candles including current open"""
        return self._candle_builder.get_latest_candles(
            exchange.upper(), symbol, timeframe, limit
        )
    
    def get_current_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str
    ) -> Optional[MarketCandle]:
        """Get current open candle"""
        return self._candle_builder.get_current_candle(
            exchange.upper(), symbol, timeframe
        )
    
    def get_volume_metrics(self, exchange: str, symbol: str) -> Optional[VolumeMetrics]:
        """Get volume metrics"""
        return self._volume_processor.get_volume_metrics(exchange.upper(), symbol)
    
    def get_spread_info(self, exchange: str, symbol: str) -> Dict:
        """Get spread information"""
        return self._ticker_processor.get_spread(exchange.upper(), symbol)
    
    def get_price(self, exchange: str, symbol: str) -> float:
        """Get latest price"""
        return self._ticker_processor.get_latest_price(exchange.upper(), symbol)
    
    # ============================================
    # Status
    # ============================================
    
    def get_feed_status(self, exchange: Optional[str] = None) -> Dict:
        """Get feed status"""
        if exchange:
            status = self._feed_status.get(exchange.upper())
            return status.dict() if status else {"error": "Feed not found"}
        
        return {
            ex: status.dict() for ex, status in self._feed_status.items()
        }
    
    def get_active_feeds(self) -> List[str]:
        """Get list of active feed exchanges"""
        return [
            ex for ex, status in self._feed_status.items()
            if status.is_active
        ]
    
    def get_subscribed_symbols(self, exchange: Optional[str] = None) -> Dict[str, List[str]]:
        """Get subscribed symbols"""
        if exchange:
            return {exchange.upper(): self._subscriptions.get(exchange.upper(), [])}
        return dict(self._subscriptions)
    
    def get_engine_status(self) -> Dict:
        """Get overall engine status"""
        return {
            "running": self._running,
            "active_feeds": len(self.get_active_feeds()),
            "total_symbols": sum(len(s) for s in self._subscriptions.values()),
            "feeds": self.get_feed_status(),
            "candle_builder": self._candle_builder.get_status(),
            "ticker_processor": self._ticker_processor.get_status(),
            "orderbook_processor": self._orderbook_processor.get_status(),
            "volume_processor": self._volume_processor.get_status(),
            "snapshot_builder": self._snapshot_builder.get_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================
    # Internal Callbacks
    # ============================================
    
    async def _on_ticker_update(self, data: Dict[str, Any]) -> None:
        """Handle ticker update from WebSocket"""
        try:
            exchange = data.get("exchange", "BINANCE")
            
            # Normalize
            tick = self._normalizer.normalize_ticker(exchange, data)
            
            # Process
            self._ticker_processor.process_tick(tick)
            
            # Build candles from ticks
            self._candle_builder.process_tick(tick)
            
            # Update feed status
            if exchange in self._feed_status:
                self._feed_status[exchange].tick_count += 1
                self._feed_status[exchange].last_update = datetime.utcnow()
            
        except Exception as e:
            print(f"Ticker processing error: {e}")
            if exchange in self._feed_status:
                self._feed_status[exchange].errors += 1
    
    async def _on_orderbook_update(self, data: Dict[str, Any]) -> None:
        """Handle orderbook update from WebSocket"""
        try:
            exchange = data.get("exchange", "BINANCE")
            
            # Normalize
            orderbook = self._normalizer.normalize_orderbook(exchange, data)
            
            # Process
            self._orderbook_processor.process_orderbook(orderbook)
            
            # Update feed status
            if exchange in self._feed_status:
                self._feed_status[exchange].orderbook_updates += 1
                self._feed_status[exchange].last_update = datetime.utcnow()
            
        except Exception as e:
            print(f"Orderbook processing error: {e}")
    
    async def _on_trade_update(self, data: Dict[str, Any]) -> None:
        """Handle trade update from WebSocket"""
        try:
            exchange = data.get("exchange", "BINANCE")
            
            # Normalize
            trade = self._normalizer.normalize_trade(exchange, data)
            
            # Process for volume
            self._volume_processor.process_trade(trade)
            
            # Record for VWAP
            self._snapshot_builder.record_trade(trade.symbol, trade.price, trade.volume)
            
        except Exception as e:
            print(f"Trade processing error: {e}")
    
    async def _snapshot_loop(self) -> None:
        """Periodically update snapshots"""
        while self._running:
            try:
                # Build snapshots for all subscribed symbols
                for exchange, symbols in self._subscriptions.items():
                    for symbol in symbols:
                        self._snapshot_builder.build_snapshot(symbol)
                
                await asyncio.sleep(1)  # Update every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Snapshot loop error: {e}")
                await asyncio.sleep(1)
    
    async def _simulate_data(self, exchange: str, symbols: List[str]) -> None:
        """Simulate market data for demo purposes"""
        import random
        
        base_prices = {
            "BTCUSDT": 69000.0,
            "ETHUSDT": 3500.0,
            "SOLUSDT": 150.0,
            "BNBUSDT": 600.0,
            "XRPUSDT": 0.55
        }
        
        while self._running:
            try:
                for symbol in symbols:
                    if symbol not in self._subscriptions.get(exchange, []):
                        continue
                    
                    base = base_prices.get(symbol, 100.0)
                    
                    # Random price movement
                    change = random.uniform(-0.001, 0.001)
                    new_price = base * (1 + change)
                    base_prices[symbol] = new_price
                    
                    # Create tick
                    spread = new_price * 0.0001
                    tick = MarketTick(
                        exchange=exchange,
                        symbol=symbol,
                        price=round(new_price, 2),
                        bid=round(new_price - spread/2, 2),
                        ask=round(new_price + spread/2, 2),
                        spread=round(spread, 4),
                        volume=round(random.uniform(0.1, 10), 4),
                        side=random.choice(["BUY", "SELL"]),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Process tick
                    self._ticker_processor.process_tick(tick)
                    self._candle_builder.process_tick(tick)
                    self._volume_processor.process_trade(tick)
                    self._snapshot_builder.record_trade(symbol, tick.price, tick.volume)
                    
                    # Create orderbook
                    bids = []
                    asks = []
                    for i in range(10):
                        bid_price = new_price * (1 - 0.0001 * (i + 1))
                        ask_price = new_price * (1 + 0.0001 * (i + 1))
                        bids.append({"price": round(bid_price, 2), "size": round(random.uniform(0.5, 5), 3)})
                        asks.append({"price": round(ask_price, 2), "size": round(random.uniform(0.5, 5), 3)})
                    
                    orderbook = self._normalizer.normalize_orderbook(exchange, {
                        "symbol": symbol,
                        "bids": [[b["price"], b["size"]] for b in bids],
                        "asks": [[a["price"], a["size"]] for a in asks]
                    })
                    self._orderbook_processor.process_orderbook(orderbook)
                    
                    # Update feed status
                    if exchange in self._feed_status:
                        self._feed_status[exchange].tick_count += 1
                        self._feed_status[exchange].orderbook_updates += 1
                        self._feed_status[exchange].last_update = datetime.utcnow()
                
                await asyncio.sleep(0.5)  # Update every 500ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Simulation error: {e}")
                await asyncio.sleep(1)


# Global instance
_market_data_engine: Optional[MarketDataEngine] = None


def get_market_data_engine() -> MarketDataEngine:
    """Get or create global market data engine"""
    global _market_data_engine
    if _market_data_engine is None:
        _market_data_engine = MarketDataEngine()
    return _market_data_engine
