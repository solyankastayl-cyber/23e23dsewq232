"""
Live Microstructure Manager
Orchestrates WebSocket connections and provides unified microstructure API.
Singleton pattern - one manager per symbol.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from collections import deque

from .ws_client import BinanceWSClient
from .orderbook_state import OrderBookState
from .trade_stream import TradeStream
from .micro_features import MicroFeatures, MicroSnapshot

logger = logging.getLogger(__name__)


class LiveMicroManager:
    """
    Manages live microstructure data for a single symbol.
    Coordinates WebSocket client, orderbook, and trade stream.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        
        # Components
        self.ws_client = BinanceWSClient(symbol)
        self.orderbook = OrderBookState(symbol=self.symbol)
        self.trade_stream = TradeStream(symbol=self.symbol)
        self.features = MicroFeatures()
        
        # Snapshot history
        self.snapshots: deque = deque(maxlen=100)
        self.last_snapshot: Optional[MicroSnapshot] = None
        
        # State
        self.running = False
        self.initialized = False
        self._task: Optional[asyncio.Task] = None
        
        # Register callbacks
        self.ws_client.on_depth(self._on_depth)
        self.ws_client.on_trade(self._on_trade)
        self.ws_client.on_ticker(self._on_ticker)
        self.ws_client.on_connect(self._on_connect)
        self.ws_client.on_disconnect(self._on_disconnect)
    
    async def start(self):
        """Start live data feed"""
        if self.running:
            logger.warning(f"[LiveMicro] {self.symbol} already running")
            return
        
        self.running = True
        logger.info(f"[LiveMicro] Starting {self.symbol}")
        
        # Start WebSocket in background task
        self._task = asyncio.create_task(self.ws_client.connect())
    
    async def stop(self):
        """Stop live data feed"""
        self.running = False
        await self.ws_client.disconnect()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"[LiveMicro] Stopped {self.symbol}")
    
    async def _on_connect(self):
        """Handle WebSocket connection"""
        logger.info(f"[LiveMicro] {self.symbol} connected, fetching snapshot...")
        
        # Get orderbook snapshot
        snapshot = await self.ws_client.get_orderbook_snapshot(limit=100)
        if snapshot:
            self.orderbook.initialize_from_snapshot(snapshot)
            self.initialized = True
            logger.info(f"[LiveMicro] {self.symbol} initialized")
    
    async def _on_disconnect(self):
        """Handle WebSocket disconnection"""
        logger.warning(f"[LiveMicro] {self.symbol} disconnected")
        self.initialized = False
    
    async def _on_depth(self, data: Dict):
        """Handle depth update"""
        self.orderbook.update(data)
        
        # Create snapshot periodically (every 10 updates)
        if self.orderbook.update_count % 10 == 0:
            await self._create_snapshot()
    
    async def _on_trade(self, data: Dict):
        """Handle trade update"""
        self.trade_stream.process_trade(data)
    
    async def _on_ticker(self, data: Dict):
        """Handle ticker update (best bid/ask)"""
        # Could use for faster best bid/ask updates
        pass
    
    async def _create_snapshot(self):
        """Create microstructure snapshot"""
        try:
            ob = self.orderbook
            ts = self.trade_stream
            
            # Get orderbook data
            best_bid, bid_qty = ob.get_best_bid()
            best_ask, ask_qty = ob.get_best_ask()
            mid_price = ob.get_mid_price()
            spread, spread_bps = ob.get_spread()
            imbalance = ob.get_imbalance()
            bid_depth, ask_depth = ob.get_depth()
            
            # Get trade data
            bs_ratio = ts.get_buy_sell_ratio(60)
            vwap = ts.get_vwap(60)
            sweep = ts.detect_sweep()
            
            # Compute features
            liquidity_score = self.features.compute_liquidity_score(bid_depth, ask_depth)
            liquidity_state = self.features.get_liquidity_state(imbalance, liquidity_score)
            micro_state = self.features.compute_micro_state(
                imbalance, spread_bps, liquidity_score, bs_ratio["pressure"]
            )
            
            # Create snapshot
            snapshot = MicroSnapshot(
                timestamp=datetime.now(timezone.utc),
                symbol=self.symbol,
                best_bid=best_bid,
                best_ask=best_ask,
                mid_price=mid_price,
                spread=spread,
                spread_bps=spread_bps,
                imbalance=imbalance,
                bid_depth_usd=bid_depth,
                ask_depth_usd=ask_depth,
                liquidity_score=liquidity_score,
                liquidity_state=liquidity_state,
                buy_volume=bs_ratio["buy_volume"],
                sell_volume=bs_ratio["sell_volume"],
                trade_pressure=bs_ratio["pressure"],
                vwap=vwap,
                state=micro_state["state"],
                confidence=micro_state["confidence"],
                sweep_detected=sweep
            )
            
            self.snapshots.append(snapshot)
            self.last_snapshot = snapshot
            
        except Exception as e:
            logger.error(f"[LiveMicro] Snapshot error: {e}")
    
    def get_current_state(self) -> Dict:
        """Get current microstructure state"""
        if not self.initialized or not self.last_snapshot:
            # Return mock data if not initialized
            return self._get_fallback_state()
        
        return self.last_snapshot.to_dict()
    
    def _get_fallback_state(self) -> Dict:
        """Fallback state when not connected"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": self.symbol,
            "connected": False,
            "initialized": self.initialized,
            "orderbook": {
                "best_bid": 0,
                "best_ask": 0,
                "mid_price": 0,
                "spread": 0,
                "spread_bps": 0,
                "imbalance": 0
            },
            "liquidity": {
                "score": 0,
                "state": "unknown"
            },
            "trade_flow": {
                "buy_volume": 0,
                "sell_volume": 0,
                "pressure": "unknown"
            },
            "micro": {
                "state": "disconnected",
                "confidence": 0
            }
        }
    
    def get_stats(self) -> Dict:
        """Get manager statistics"""
        return {
            "symbol": self.symbol,
            "running": self.running,
            "initialized": self.initialized,
            "ws_stats": self.ws_client.get_stats(),
            "orderbook": {
                "bid_levels": len(self.orderbook.bids),
                "ask_levels": len(self.orderbook.asks),
                "update_count": self.orderbook.update_count
            },
            "trades": {
                "total": self.trade_stream.total_trades,
                "recent_1m": len(self.trade_stream.get_recent_trades(60))
            },
            "snapshots": len(self.snapshots)
        }


# Global manager instances
_managers: Dict[str, LiveMicroManager] = {}
_manager_lock = asyncio.Lock()


async def get_manager(symbol: str) -> LiveMicroManager:
    """Get or create manager for symbol"""
    symbol = symbol.upper()
    
    async with _manager_lock:
        if symbol not in _managers:
            manager = LiveMicroManager(symbol)
            _managers[symbol] = manager
            await manager.start()
        
        return _managers[symbol]


async def stop_all_managers():
    """Stop all managers gracefully"""
    async with _manager_lock:
        for symbol, manager in _managers.items():
            await manager.stop()
        _managers.clear()


def get_active_symbols() -> list:
    """Get list of active symbols"""
    return list(_managers.keys())
