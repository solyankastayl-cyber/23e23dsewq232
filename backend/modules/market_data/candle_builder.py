"""
Candle Builder - PHASE 5.2
==========================

Builds live candles from tick/trade stream.
Supports multiple timeframes with proper close detection.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from .market_data_types import MarketTick, MarketCandle, Timeframe


class CandleBuilder:
    """
    Builds and maintains live candles from market ticks.
    
    Features:
    - Multiple timeframe support (1m, 5m, 15m, 1h, 4h, 1d)
    - Real-time candle updates
    - Proper candle close detection
    - Historical candle storage
    """
    
    # Timeframe durations in seconds
    TIMEFRAME_SECONDS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800
    }
    
    def __init__(self, max_history: int = 500):
        # Current open candles: exchange -> symbol -> timeframe -> candle
        self._current: Dict[str, Dict[str, Dict[str, MarketCandle]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        
        # Historical closed candles: exchange -> symbol -> timeframe -> list
        self._history: Dict[str, Dict[str, Dict[str, List[MarketCandle]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        
        # Max candles to keep in history per symbol/timeframe
        self._max_history = max_history
        
        # Callbacks for candle events
        self._on_candle_update: List[Callable] = []
        self._on_candle_close: List[Callable] = []
        
        # Supported timeframes
        self._timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    # ============================================
    # Public Methods
    # ============================================
    
    def process_tick(self, tick: MarketTick) -> List[MarketCandle]:
        """
        Process a market tick and update candles.
        
        Args:
            tick: Market tick data
            
        Returns:
            List of updated candles
        """
        updated = []
        
        for tf in self._timeframes:
            candle = self._update_candle(tick, tf)
            if candle:
                updated.append(candle)
        
        return updated
    
    def process_candle(self, candle: MarketCandle) -> MarketCandle:
        """
        Process an incoming candle from exchange stream.
        
        Args:
            candle: Candle from exchange
            
        Returns:
            Updated/stored candle
        """
        exchange = candle.exchange
        symbol = candle.symbol
        tf = candle.timeframe
        
        if candle.is_closed:
            # Store in history
            self._add_to_history(candle)
            # Clear current
            if tf in self._current[exchange][symbol]:
                del self._current[exchange][symbol][tf]
            
            # Notify callbacks
            self._notify_close(candle)
        else:
            # Update current
            self._current[exchange][symbol][tf] = candle
            # Notify callbacks
            self._notify_update(candle)
        
        return candle
    
    def get_current_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str
    ) -> Optional[MarketCandle]:
        """Get current open candle"""
        return self._current.get(exchange, {}).get(symbol, {}).get(timeframe)
    
    def get_candle_history(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[MarketCandle]:
        """Get historical closed candles"""
        history = self._history.get(exchange, {}).get(symbol, {}).get(timeframe, [])
        return history[-limit:] if limit else history
    
    def get_latest_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        count: int = 10
    ) -> List[MarketCandle]:
        """Get latest candles including current open one"""
        history = self.get_candle_history(exchange, symbol, timeframe, count - 1)
        current = self.get_current_candle(exchange, symbol, timeframe)
        
        if current:
            return history + [current]
        return history
    
    def set_timeframes(self, timeframes: List[str]) -> None:
        """Set which timeframes to build"""
        self._timeframes = [tf for tf in timeframes if tf in self.TIMEFRAME_SECONDS]
    
    def add_on_update_callback(self, callback: Callable) -> None:
        """Add callback for candle updates"""
        self._on_candle_update.append(callback)
    
    def add_on_close_callback(self, callback: Callable) -> None:
        """Add callback for candle closes"""
        self._on_candle_close.append(callback)
    
    # ============================================
    # Private Methods
    # ============================================
    
    def _update_candle(self, tick: MarketTick, timeframe: str) -> Optional[MarketCandle]:
        """Update or create candle from tick"""
        exchange = tick.exchange
        symbol = tick.symbol
        price = tick.price
        volume = tick.volume
        
        if price <= 0:
            return None
        
        # Get timeframe duration
        tf_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 60)
        
        # Calculate candle boundaries
        ts = tick.timestamp.timestamp()
        candle_start_ts = int(ts // tf_seconds) * tf_seconds
        candle_end_ts = candle_start_ts + tf_seconds
        
        candle_start = datetime.fromtimestamp(candle_start_ts)
        candle_end = datetime.fromtimestamp(candle_end_ts)
        
        # Get or create current candle
        current = self._current[exchange][symbol].get(timeframe)
        
        if current is None or current.start_time.timestamp() != candle_start_ts:
            # Close previous candle if exists
            if current is not None:
                current.is_closed = True
                self._add_to_history(current)
                self._notify_close(current)
            
            # Create new candle
            current = MarketCandle(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                trades_count=1,
                start_time=candle_start,
                end_time=candle_end,
                is_closed=False
            )
            self._current[exchange][symbol][timeframe] = current
        else:
            # Update existing candle
            current.high = max(current.high, price)
            current.low = min(current.low, price)
            current.close = price
            current.volume += volume
            current.trades_count += 1
        
        self._notify_update(current)
        return current
    
    def _add_to_history(self, candle: MarketCandle) -> None:
        """Add candle to history"""
        exchange = candle.exchange
        symbol = candle.symbol
        tf = candle.timeframe
        
        history = self._history[exchange][symbol][tf]
        history.append(candle)
        
        # Trim history if needed
        if len(history) > self._max_history:
            self._history[exchange][symbol][tf] = history[-self._max_history:]
    
    def _notify_update(self, candle: MarketCandle) -> None:
        """Notify update callbacks"""
        for callback in self._on_candle_update:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(candle))
                else:
                    callback(candle)
            except Exception as e:
                print(f"Candle update callback error: {e}")
    
    def _notify_close(self, candle: MarketCandle) -> None:
        """Notify close callbacks"""
        for callback in self._on_candle_close:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(candle))
                else:
                    callback(candle)
            except Exception as e:
                print(f"Candle close callback error: {e}")
    
    def get_status(self) -> Dict:
        """Get builder status"""
        total_current = 0
        total_history = 0
        symbols = set()
        
        for exchange in self._current:
            for symbol in self._current[exchange]:
                symbols.add(f"{exchange}:{symbol}")
                total_current += len(self._current[exchange][symbol])
        
        for exchange in self._history:
            for symbol in self._history[exchange]:
                for tf in self._history[exchange][symbol]:
                    total_history += len(self._history[exchange][symbol][tf])
        
        return {
            "active_symbols": len(symbols),
            "current_candles": total_current,
            "historical_candles": total_history,
            "timeframes": self._timeframes,
            "max_history": self._max_history
        }


# Global instance
_candle_builder: Optional[CandleBuilder] = None


def get_candle_builder() -> CandleBuilder:
    """Get or create global candle builder"""
    global _candle_builder
    if _candle_builder is None:
        _candle_builder = CandleBuilder()
    return _candle_builder
