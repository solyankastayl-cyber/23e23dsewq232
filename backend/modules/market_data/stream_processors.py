"""
Stream Processors - PHASE 5.2
=============================

Processors for different market data stream types:
- Ticker Stream Processor
- Orderbook Stream Processor
- Volume Stream Processor
"""

from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import statistics

from .market_data_types import (
    MarketTick,
    MarketOrderbook,
    OrderbookLevel,
    VolumeMetrics
)


class TickerStreamProcessor:
    """
    Processes ticker stream updates.
    
    Maintains:
    - Latest price per symbol
    - Bid/Ask tracking
    - Spread monitoring
    - Price change calculations
    """
    
    def __init__(self, max_ticks: int = 1000):
        # Latest tick per exchange/symbol
        self._latest: Dict[str, Dict[str, MarketTick]] = defaultdict(dict)
        
        # Tick history for analysis
        self._tick_history: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=max_ticks))
        )
        
        # 24h tracking
        self._price_24h_ago: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Callbacks
        self._callbacks: List[Callable] = []
    
    def process_tick(self, tick: MarketTick) -> MarketTick:
        """Process incoming tick"""
        exchange = tick.exchange
        symbol = tick.symbol
        
        # Calculate spread if bid/ask available
        if tick.bid > 0 and tick.ask > 0:
            tick.spread = tick.ask - tick.bid
        
        # Store latest
        self._latest[exchange][symbol] = tick
        
        # Add to history
        self._tick_history[exchange][symbol].append(tick)
        
        # Notify callbacks
        self._notify(tick)
        
        return tick
    
    def get_latest_tick(self, exchange: str, symbol: str) -> Optional[MarketTick]:
        """Get latest tick for symbol"""
        return self._latest.get(exchange, {}).get(symbol)
    
    def get_latest_price(self, exchange: str, symbol: str) -> float:
        """Get latest price for symbol"""
        tick = self.get_latest_tick(exchange, symbol)
        return tick.price if tick else 0.0
    
    def get_spread(self, exchange: str, symbol: str) -> Dict[str, float]:
        """Get current spread info"""
        tick = self.get_latest_tick(exchange, symbol)
        if not tick:
            return {"spread": 0, "spread_bps": 0}
        
        spread = tick.spread
        spread_bps = (spread / tick.bid * 10000) if tick.bid > 0 else 0
        
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": spread,
            "spread_bps": round(spread_bps, 2)
        }
    
    def get_price_change(self, exchange: str, symbol: str) -> Dict[str, float]:
        """Calculate price change from history"""
        history = list(self._tick_history.get(exchange, {}).get(symbol, []))
        if not history:
            return {"change": 0, "change_pct": 0}
        
        current = history[-1].price
        
        # Find tick from ~24h ago or oldest
        target_time = datetime.utcnow() - timedelta(hours=24)
        old_price = history[0].price
        
        for tick in history:
            if tick.timestamp >= target_time:
                break
            old_price = tick.price
        
        if old_price <= 0:
            return {"change": 0, "change_pct": 0}
        
        change = current - old_price
        change_pct = (change / old_price) * 100
        
        return {
            "change": round(change, 2),
            "change_pct": round(change_pct, 4)
        }
    
    def add_callback(self, callback: Callable) -> None:
        """Add tick callback"""
        self._callbacks.append(callback)
    
    def _notify(self, tick: MarketTick) -> None:
        """Notify callbacks"""
        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(tick))
                else:
                    cb(tick)
            except Exception as e:
                print(f"Ticker callback error: {e}")
    
    def get_status(self) -> Dict:
        """Get processor status"""
        total_symbols = sum(len(syms) for syms in self._latest.values())
        total_ticks = sum(
            len(q) for ex in self._tick_history.values() for q in ex.values()
        )
        
        return {
            "tracked_symbols": total_symbols,
            "total_ticks_stored": total_ticks,
            "exchanges": list(self._latest.keys())
        }


class OrderbookStreamProcessor:
    """
    Processes orderbook stream updates.
    
    Maintains:
    - Top of book
    - Spread monitoring
    - Depth analysis
    - Imbalance tracking
    """
    
    def __init__(self, depth: int = 20):
        # Latest orderbook per exchange/symbol
        self._orderbooks: Dict[str, Dict[str, MarketOrderbook]] = defaultdict(dict)
        
        # Configuration
        self._depth = depth
        
        # Spread history for analysis
        self._spread_history: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=100))
        )
        
        # Callbacks
        self._callbacks: List[Callable] = []
    
    def process_orderbook(self, orderbook: MarketOrderbook) -> MarketOrderbook:
        """Process orderbook update"""
        exchange = orderbook.exchange
        symbol = orderbook.symbol
        
        # Calculate metrics
        orderbook.calculate_metrics()
        
        # Store
        self._orderbooks[exchange][symbol] = orderbook
        
        # Track spread history
        if orderbook.spread > 0:
            self._spread_history[exchange][symbol].append({
                "spread": orderbook.spread,
                "spread_bps": orderbook.spread_bps,
                "timestamp": orderbook.timestamp
            })
        
        # Notify
        self._notify(orderbook)
        
        return orderbook
    
    def get_orderbook(self, exchange: str, symbol: str) -> Optional[MarketOrderbook]:
        """Get latest orderbook"""
        return self._orderbooks.get(exchange, {}).get(symbol)
    
    def get_best_bid_ask(self, exchange: str, symbol: str) -> Dict[str, float]:
        """Get best bid/ask"""
        ob = self.get_orderbook(exchange, symbol)
        if not ob:
            return {"bid": 0, "ask": 0, "mid": 0, "spread": 0}
        
        return {
            "bid": ob.best_bid,
            "ask": ob.best_ask,
            "mid": ob.mid_price,
            "spread": ob.spread,
            "spread_bps": ob.spread_bps
        }
    
    def get_depth(self, exchange: str, symbol: str) -> Dict[str, float]:
        """Get orderbook depth info"""
        ob = self.get_orderbook(exchange, symbol)
        if not ob:
            return {"bid_depth": 0, "ask_depth": 0, "imbalance": 0}
        
        return {
            "bid_depth": ob.bid_depth,
            "ask_depth": ob.ask_depth,
            "total_depth": ob.bid_depth + ob.ask_depth,
            "imbalance": ob.imbalance,
            "levels": len(ob.bids)
        }
    
    def get_avg_spread(self, exchange: str, symbol: str) -> float:
        """Get average spread from history"""
        history = list(self._spread_history.get(exchange, {}).get(symbol, []))
        if not history:
            return 0.0
        
        spreads = [h["spread_bps"] for h in history]
        return statistics.mean(spreads)
    
    def add_callback(self, callback: Callable) -> None:
        """Add orderbook callback"""
        self._callbacks.append(callback)
    
    def _notify(self, orderbook: MarketOrderbook) -> None:
        """Notify callbacks"""
        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(orderbook))
                else:
                    cb(orderbook)
            except Exception as e:
                print(f"Orderbook callback error: {e}")
    
    def get_status(self) -> Dict:
        """Get processor status"""
        total_symbols = sum(len(syms) for syms in self._orderbooks.values())
        
        return {
            "tracked_symbols": total_symbols,
            "depth_levels": self._depth,
            "exchanges": list(self._orderbooks.keys())
        }


class VolumeStreamProcessor:
    """
    Processes volume data from trades/ticks.
    
    Calculates:
    - Rolling volume
    - Buy/Sell breakdown
    - Volume spikes
    - Activity bursts
    """
    
    def __init__(self, window_seconds: int = 3600):
        # Trade history for volume calculation
        self._trades: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=10000))
        )
        
        # Rolling metrics
        self._metrics: Dict[str, Dict[str, VolumeMetrics]] = defaultdict(dict)
        
        # Configuration
        self._window = window_seconds
        
        # Baseline for spike detection
        self._avg_volume: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Callbacks
        self._callbacks: List[Callable] = []
    
    def process_trade(self, tick: MarketTick) -> VolumeMetrics:
        """Process trade for volume tracking"""
        exchange = tick.exchange
        symbol = tick.symbol
        
        # Store trade
        self._trades[exchange][symbol].append({
            "price": tick.price,
            "volume": tick.volume,
            "side": tick.side,
            "timestamp": tick.timestamp
        })
        
        # Calculate metrics
        metrics = self._calculate_metrics(exchange, symbol)
        self._metrics[exchange][symbol] = metrics
        
        # Notify
        self._notify(metrics)
        
        return metrics
    
    def get_volume_metrics(self, exchange: str, symbol: str) -> Optional[VolumeMetrics]:
        """Get volume metrics for symbol"""
        return self._metrics.get(exchange, {}).get(symbol)
    
    def get_rolling_volume(
        self,
        exchange: str,
        symbol: str,
        window_seconds: int = 3600
    ) -> float:
        """Calculate rolling volume for time window"""
        trades = list(self._trades.get(exchange, {}).get(symbol, []))
        if not trades:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        volume = sum(
            t["volume"] for t in trades
            if t["timestamp"] >= cutoff
        )
        
        return volume
    
    def get_buy_sell_ratio(self, exchange: str, symbol: str) -> Dict[str, float]:
        """Get buy/sell volume ratio"""
        trades = list(self._trades.get(exchange, {}).get(symbol, []))
        if not trades:
            return {"buy_volume": 0, "sell_volume": 0, "ratio": 1.0}
        
        cutoff = datetime.utcnow() - timedelta(seconds=self._window)
        recent = [t for t in trades if t["timestamp"] >= cutoff]
        
        buy_vol = sum(t["volume"] for t in recent if t["side"] == "BUY")
        sell_vol = sum(t["volume"] for t in recent if t["side"] == "SELL")
        
        ratio = buy_vol / sell_vol if sell_vol > 0 else float('inf') if buy_vol > 0 else 1.0
        
        return {
            "buy_volume": buy_vol,
            "sell_volume": sell_vol,
            "ratio": round(ratio, 4) if ratio != float('inf') else 999.0
        }
    
    def is_volume_spike(self, exchange: str, symbol: str, threshold: float = 2.0) -> bool:
        """Check if current volume is a spike"""
        metrics = self.get_volume_metrics(exchange, symbol)
        if not metrics:
            return False
        
        return metrics.volume_ratio >= threshold
    
    def _calculate_metrics(self, exchange: str, symbol: str) -> VolumeMetrics:
        """Calculate volume metrics"""
        trades = list(self._trades[exchange][symbol])
        
        now = datetime.utcnow()
        cutoff_1h = now - timedelta(hours=1)
        cutoff_24h = now - timedelta(hours=24)
        
        # Rolling volumes
        vol_1h = sum(t["volume"] for t in trades if t["timestamp"] >= cutoff_1h)
        vol_24h = sum(t["volume"] for t in trades if t["timestamp"] >= cutoff_24h)
        
        # Buy/Sell breakdown
        recent = [t for t in trades if t["timestamp"] >= cutoff_1h]
        buy_vol = sum(t["volume"] for t in recent if t["side"] == "BUY")
        sell_vol = sum(t["volume"] for t in recent if t["side"] == "SELL")
        
        # Average volume (for spike detection)
        avg_vol = self._avg_volume.get(exchange, {}).get(symbol, vol_1h)
        if avg_vol == 0:
            avg_vol = vol_1h
        
        # Update average (EMA)
        self._avg_volume[exchange][symbol] = avg_vol * 0.9 + vol_1h * 0.1
        
        # Volume ratio
        vol_ratio = vol_1h / avg_vol if avg_vol > 0 else 1.0
        
        # Spike detection
        is_spike = vol_ratio >= 2.0
        
        return VolumeMetrics(
            symbol=symbol,
            exchange=exchange,
            timeframe="1h",
            current_volume=vol_1h,
            avg_volume=avg_vol,
            volume_ratio=round(vol_ratio, 4),
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            buy_sell_ratio=round(buy_vol / sell_vol, 4) if sell_vol > 0 else 0,
            is_volume_spike=is_spike,
            spike_magnitude=vol_ratio if is_spike else 0,
            rolling_volume_1h=vol_1h,
            rolling_volume_24h=vol_24h,
            timestamp=now
        )
    
    def add_callback(self, callback: Callable) -> None:
        """Add volume callback"""
        self._callbacks.append(callback)
    
    def _notify(self, metrics: VolumeMetrics) -> None:
        """Notify callbacks"""
        for cb in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(metrics))
                else:
                    cb(metrics)
            except Exception as e:
                print(f"Volume callback error: {e}")
    
    def get_status(self) -> Dict:
        """Get processor status"""
        total_symbols = sum(len(syms) for syms in self._trades.values())
        total_trades = sum(
            len(q) for ex in self._trades.values() for q in ex.values()
        )
        
        return {
            "tracked_symbols": total_symbols,
            "total_trades_stored": total_trades,
            "window_seconds": self._window
        }


# Global instances
_ticker_processor: Optional[TickerStreamProcessor] = None
_orderbook_processor: Optional[OrderbookStreamProcessor] = None
_volume_processor: Optional[VolumeStreamProcessor] = None


def get_ticker_processor() -> TickerStreamProcessor:
    global _ticker_processor
    if _ticker_processor is None:
        _ticker_processor = TickerStreamProcessor()
    return _ticker_processor


def get_orderbook_processor() -> OrderbookStreamProcessor:
    global _orderbook_processor
    if _orderbook_processor is None:
        _orderbook_processor = OrderbookStreamProcessor()
    return _orderbook_processor


def get_volume_processor() -> VolumeStreamProcessor:
    global _volume_processor
    if _volume_processor is None:
        _volume_processor = VolumeStreamProcessor()
    return _volume_processor
