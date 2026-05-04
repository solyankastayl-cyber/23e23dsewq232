"""
OrderBook State Manager
Maintains synchronized orderbook state from Binance WebSocket updates.
Handles snapshot initialization and incremental updates with proper sync.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrderBookState:
    """
    Manages orderbook state with proper Binance synchronization.
    
    Binance requires:
    1. Get REST snapshot first
    2. Buffer WebSocket updates during snapshot fetch
    3. Apply updates where u >= lastUpdateId + 1 from snapshot
    4. Discard older updates
    """
    
    symbol: str = ""
    bids: Dict[float, float] = field(default_factory=dict)  # price -> quantity
    asks: Dict[float, float] = field(default_factory=dict)  # price -> quantity
    
    last_update_id: int = 0
    first_update_id: int = 0
    
    initialized: bool = False
    last_update_time: Optional[datetime] = None
    update_count: int = 0
    
    # Buffer for updates while waiting for snapshot
    _update_buffer: List[Dict] = field(default_factory=list)
    _buffer_max_size: int = 1000
    
    def initialize_from_snapshot(self, snapshot: Dict) -> bool:
        """
        Initialize orderbook from REST API snapshot.
        
        snapshot format:
        {
            "lastUpdateId": 123456,
            "bids": [["price", "qty"], ...],
            "asks": [["price", "qty"], ...]
        }
        """
        try:
            self.last_update_id = snapshot.get("lastUpdateId", 0)
            
            # Parse bids
            self.bids.clear()
            for bid in snapshot.get("bids", []):
                price = float(bid[0])
                qty = float(bid[1])
                if qty > 0:
                    self.bids[price] = qty
            
            # Parse asks
            self.asks.clear()
            for ask in snapshot.get("asks", []):
                price = float(ask[0])
                qty = float(ask[1])
                if qty > 0:
                    self.asks[price] = qty
            
            self.initialized = True
            self.last_update_time = datetime.now(timezone.utc)
            
            logger.info(f"[OrderBook] Initialized {self.symbol} with {len(self.bids)} bids, {len(self.asks)} asks, lastUpdateId={self.last_update_id}")
            
            # Process buffered updates
            self._process_buffer()
            
            return True
            
        except Exception as e:
            logger.error(f"[OrderBook] Snapshot init error: {e}")
            return False
    
    def update(self, data: Dict) -> bool:
        """
        Apply depth update from WebSocket.
        
        data format:
        {
            "e": "depthUpdate",
            "E": 123456789,     # Event time
            "s": "BTCUSDT",     # Symbol
            "U": 157,           # First update ID
            "u": 160,           # Final update ID
            "b": [["price", "qty"], ...],  # Bids
            "a": [["price", "qty"], ...]   # Asks
        }
        """
        first_update_id = data.get("U", 0)
        final_update_id = data.get("u", 0)
        
        # Buffer if not initialized
        if not self.initialized:
            if len(self._update_buffer) < self._buffer_max_size:
                self._update_buffer.append(data)
            return False
        
        # Sync check: drop old updates
        # First update should be <= lastUpdateId + 1
        # Final update should be >= lastUpdateId + 1
        if final_update_id <= self.last_update_id:
            return False  # Old update, skip
        
        # Apply bid updates
        for bid in data.get("b", []):
            price = float(bid[0])
            qty = float(bid[1])
            if qty == 0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = qty
        
        # Apply ask updates
        for ask in data.get("a", []):
            price = float(ask[0])
            qty = float(ask[1])
            if qty == 0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = qty
        
        self.last_update_id = final_update_id
        self.first_update_id = first_update_id
        self.last_update_time = datetime.now(timezone.utc)
        self.update_count += 1
        
        return True
    
    def _process_buffer(self):
        """Process buffered updates after snapshot initialization"""
        valid_updates = 0
        for update in self._update_buffer:
            if self.update(update):
                valid_updates += 1
        
        logger.info(f"[OrderBook] Processed {valid_updates}/{len(self._update_buffer)} buffered updates")
        self._update_buffer.clear()
    
    def top_n(self, n: int = 10) -> Dict:
        """Get top N levels of orderbook"""
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:n]
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])[:n]
        
        return {
            "bids": sorted_bids,
            "asks": sorted_asks
        }
    
    def get_best_bid(self) -> Tuple[float, float]:
        """Get best bid (highest price)"""
        if not self.bids:
            return (0.0, 0.0)
        best_price = max(self.bids.keys())
        return (best_price, self.bids[best_price])
    
    def get_best_ask(self) -> Tuple[float, float]:
        """Get best ask (lowest price)"""
        if not self.asks:
            return (0.0, 0.0)
        best_price = min(self.asks.keys())
        return (best_price, self.asks[best_price])
    
    def get_mid_price(self) -> float:
        """Get mid price"""
        best_bid = self.get_best_bid()[0]
        best_ask = self.get_best_ask()[0]
        if best_bid == 0 or best_ask == 0:
            return 0.0
        return (best_bid + best_ask) / 2
    
    def get_spread(self) -> Tuple[float, float]:
        """Get spread in absolute and basis points"""
        best_bid = self.get_best_bid()[0]
        best_ask = self.get_best_ask()[0]
        
        if best_bid == 0 or best_ask == 0:
            return (0.0, 0.0)
        
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2
        spread_bps = (spread / mid) * 10000 if mid > 0 else 0
        
        return (spread, spread_bps)
    
    def get_depth(self, levels: int = 10) -> Tuple[float, float]:
        """Get total depth (in quote currency) for top N levels"""
        top = self.top_n(levels)
        bid_depth = sum(price * qty for price, qty in top["bids"])
        ask_depth = sum(price * qty for price, qty in top["asks"])
        return (bid_depth, ask_depth)
    
    def get_imbalance(self, levels: int = 10) -> float:
        """
        Calculate orderbook imbalance.
        Returns value between -1 (all asks) and +1 (all bids)
        """
        top = self.top_n(levels)
        bid_vol = sum(qty for _, qty in top["bids"])
        ask_vol = sum(qty for _, qty in top["asks"])
        
        total = bid_vol + ask_vol
        if total == 0:
            return 0.0
        
        return (bid_vol - ask_vol) / total
    
    def get_summary(self) -> Dict:
        """Get full orderbook summary"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        spread, spread_bps = self.get_spread()
        bid_depth, ask_depth = self.get_depth()
        
        return {
            "symbol": self.symbol,
            "initialized": self.initialized,
            "best_bid": {"price": best_bid[0], "qty": best_bid[1]},
            "best_ask": {"price": best_ask[0], "qty": best_ask[1]},
            "mid_price": self.get_mid_price(),
            "spread": spread,
            "spread_bps": round(spread_bps, 2),
            "imbalance": round(self.get_imbalance(), 4),
            "bid_depth_usd": round(bid_depth, 2),
            "ask_depth_usd": round(ask_depth, 2),
            "last_update_id": self.last_update_id,
            "update_count": self.update_count,
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None
        }
