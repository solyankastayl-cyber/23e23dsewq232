"""
Market Snapshot Builder - PHASE 5.2
====================================

Builds aggregated market snapshots from multiple sources.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from .market_data_types import MarketSnapshot, MarketTick
from .stream_processors import (
    get_ticker_processor,
    get_orderbook_processor,
    get_volume_processor
)


class MarketSnapshotBuilder:
    """
    Builds unified market snapshots from multiple data sources.
    
    Features:
    - Multi-exchange aggregation
    - Primary exchange selection
    - Volatility calculation
    - VWAP calculation
    """
    
    def __init__(self):
        # Snapshots per symbol
        self._snapshots: Dict[str, MarketSnapshot] = {}
        
        # Price history for volatility (symbol -> list of prices)
        self._price_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Trade history for VWAP
        self._trade_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Max history size
        self._max_history = 1000
    
    def build_snapshot(self, symbol: str) -> MarketSnapshot:
        """Build aggregated snapshot for symbol"""
        ticker_proc = get_ticker_processor()
        orderbook_proc = get_orderbook_processor()
        volume_proc = get_volume_processor()
        
        # Collect data from all exchanges
        exchanges = ["BINANCE", "BYBIT", "OKX"]
        active_exchanges = []
        
        prices = []
        bids = []
        asks = []
        volumes = []
        
        primary_exchange = None
        best_price = 0.0
        best_volume = 0.0
        
        for exchange in exchanges:
            tick = ticker_proc.get_latest_tick(exchange, symbol)
            if tick and tick.price > 0:
                active_exchanges.append(exchange)
                prices.append(tick.price)
                
                if tick.bid > 0:
                    bids.append(tick.bid)
                if tick.ask > 0:
                    asks.append(tick.ask)
                
                # Volume from volume processor
                vol_metrics = volume_proc.get_volume_metrics(exchange, symbol)
                if vol_metrics:
                    volumes.append(vol_metrics.rolling_volume_24h)
                    
                    # Primary exchange = highest volume
                    if vol_metrics.rolling_volume_24h > best_volume:
                        best_volume = vol_metrics.rolling_volume_24h
                        primary_exchange = exchange
                        best_price = tick.price
        
        if not active_exchanges:
            # Return cached or empty
            return self._snapshots.get(symbol, MarketSnapshot(
                symbol=symbol,
                last_price=0,
                active_exchanges=[],
                timestamp=datetime.utcnow()
            ))
        
        # Calculate aggregated values
        last_price = best_price if best_price > 0 else statistics.mean(prices)
        avg_bid = statistics.mean(bids) if bids else 0
        avg_ask = statistics.mean(asks) if asks else 0
        total_volume = sum(volumes)
        
        spread = avg_ask - avg_bid if avg_bid > 0 and avg_ask > 0 else 0
        spread_bps = (spread / avg_bid * 10000) if avg_bid > 0 else 0
        
        # Price change from ticker processor
        price_change = ticker_proc.get_price_change(
            primary_exchange or active_exchanges[0],
            symbol
        )
        
        # Calculate volatility
        volatility = self._calculate_volatility(symbol)
        
        # Calculate VWAP
        vwap = self._calculate_vwap(symbol)
        
        # Get 24h high/low from history
        high_24h, low_24h = self._get_24h_range(symbol)
        if high_24h == 0:
            high_24h = last_price * 1.02
            low_24h = last_price * 0.98
        
        snapshot = MarketSnapshot(
            symbol=symbol,
            last_price=round(last_price, 2),
            price_change_24h=price_change.get("change", 0),
            price_change_pct_24h=price_change.get("change_pct", 0),
            bid=round(avg_bid, 2),
            ask=round(avg_ask, 2),
            spread=round(spread, 4),
            spread_bps=round(spread_bps, 2),
            volume_24h=round(total_volume, 2),
            high_24h=round(high_24h, 2),
            low_24h=round(low_24h, 2),
            vwap=round(vwap, 2) if vwap > 0 else round(last_price, 2),
            volatility=round(volatility, 4),
            active_exchanges=active_exchanges,
            primary_exchange=primary_exchange or active_exchanges[0],
            timestamp=datetime.utcnow()
        )
        
        # Store snapshot
        self._snapshots[symbol] = snapshot
        
        # Update price history
        self._update_price_history(symbol, last_price)
        
        return snapshot
    
    def get_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """Get cached snapshot"""
        return self._snapshots.get(symbol)
    
    def get_all_snapshots(self) -> Dict[str, MarketSnapshot]:
        """Get all cached snapshots"""
        return self._snapshots.copy()
    
    def record_trade(self, symbol: str, price: float, volume: float) -> None:
        """Record trade for VWAP calculation"""
        self._trade_history[symbol].append({
            "price": price,
            "volume": volume,
            "timestamp": datetime.utcnow()
        })
        
        # Trim history
        if len(self._trade_history[symbol]) > self._max_history:
            self._trade_history[symbol] = self._trade_history[symbol][-self._max_history:]
    
    def _update_price_history(self, symbol: str, price: float) -> None:
        """Update price history for volatility"""
        self._price_history[symbol].append({
            "price": price,
            "timestamp": datetime.utcnow()
        })
        
        # Trim history
        if len(self._price_history[symbol]) > self._max_history:
            self._price_history[symbol] = self._price_history[symbol][-self._max_history:]
    
    def _calculate_volatility(self, symbol: str, window_hours: int = 24) -> float:
        """Calculate price volatility (standard deviation of returns)"""
        history = self._price_history.get(symbol, [])
        if len(history) < 10:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        recent = [h for h in history if h["timestamp"] >= cutoff]
        
        if len(recent) < 5:
            recent = history[-100:]  # Use last 100 if not enough recent
        
        prices = [h["price"] for h in recent]
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if len(returns) < 5:
            return 0.0
        
        # Annualized volatility
        try:
            std_dev = statistics.stdev(returns)
            # Assuming hourly data, annualize
            annualized = std_dev * (8760 ** 0.5)
            return annualized
        except:
            return 0.0
    
    def _calculate_vwap(self, symbol: str, window_hours: int = 24) -> float:
        """Calculate Volume-Weighted Average Price"""
        trades = self._trade_history.get(symbol, [])
        if not trades:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        recent = [t for t in trades if t["timestamp"] >= cutoff]
        
        if not recent:
            recent = trades[-100:]
        
        total_pv = sum(t["price"] * t["volume"] for t in recent)
        total_v = sum(t["volume"] for t in recent)
        
        if total_v <= 0:
            return 0.0
        
        return total_pv / total_v
    
    def _get_24h_range(self, symbol: str) -> tuple:
        """Get 24h high/low from price history"""
        history = self._price_history.get(symbol, [])
        if not history:
            return (0, 0)
        
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = [h for h in history if h["timestamp"] >= cutoff]
        
        if not recent:
            return (0, 0)
        
        prices = [h["price"] for h in recent]
        return (max(prices), min(prices))
    
    def get_status(self) -> Dict:
        """Get builder status"""
        return {
            "cached_snapshots": len(self._snapshots),
            "symbols": list(self._snapshots.keys()),
            "price_history_size": sum(len(h) for h in self._price_history.values()),
            "trade_history_size": sum(len(h) for h in self._trade_history.values())
        }


# Global instance
_snapshot_builder: Optional[MarketSnapshotBuilder] = None


def get_snapshot_builder() -> MarketSnapshotBuilder:
    """Get or create global snapshot builder"""
    global _snapshot_builder
    if _snapshot_builder is None:
        _snapshot_builder = MarketSnapshotBuilder()
    return _snapshot_builder
