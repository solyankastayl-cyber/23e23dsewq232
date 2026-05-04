"""
Market Data Normalizer - PHASE 5.2
===================================

Normalizes market data from different exchanges to unified format.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from .market_data_types import (
    MarketTick,
    MarketCandle,
    MarketOrderbook,
    OrderbookLevel
)


class MarketDataNormalizer:
    """
    Normalizes raw exchange data to unified internal format.
    
    Supports:
    - Binance
    - Bybit
    - OKX
    """
    
    def __init__(self):
        self._normalizers = {
            "BINANCE": self._normalize_binance,
            "BYBIT": self._normalize_bybit,
            "OKX": self._normalize_okx
        }
    
    # ============================================
    # Public Methods
    # ============================================
    
    def normalize_ticker(self, exchange: str, data: Dict[str, Any]) -> MarketTick:
        """Normalize ticker data to MarketTick"""
        normalizer = self._normalizers.get(exchange.upper())
        if normalizer:
            return normalizer("ticker", data)
        return self._generic_ticker(exchange, data)
    
    def normalize_trade(self, exchange: str, data: Dict[str, Any]) -> MarketTick:
        """Normalize trade data to MarketTick"""
        normalizer = self._normalizers.get(exchange.upper())
        if normalizer:
            return normalizer("trade", data)
        return self._generic_trade(exchange, data)
    
    def normalize_candle(self, exchange: str, data: Dict[str, Any]) -> MarketCandle:
        """Normalize candle/kline data to MarketCandle"""
        normalizer = self._normalizers.get(exchange.upper())
        if normalizer:
            return normalizer("candle", data)
        return self._generic_candle(exchange, data)
    
    def normalize_orderbook(self, exchange: str, data: Dict[str, Any]) -> MarketOrderbook:
        """Normalize orderbook data to MarketOrderbook"""
        normalizer = self._normalizers.get(exchange.upper())
        if normalizer:
            return normalizer("orderbook", data)
        return self._generic_orderbook(exchange, data)
    
    # ============================================
    # Binance Normalizers
    # ============================================
    
    def _normalize_binance(self, data_type: str, data: Dict[str, Any]) -> Any:
        """Normalize Binance data"""
        if data_type == "ticker":
            return self._binance_ticker(data)
        elif data_type == "trade":
            return self._binance_trade(data)
        elif data_type == "candle":
            return self._binance_candle(data)
        elif data_type == "orderbook":
            return self._binance_orderbook(data)
        return None
    
    def _binance_ticker(self, data: Dict[str, Any]) -> MarketTick:
        """Binance ticker format"""
        return MarketTick(
            exchange="BINANCE",
            symbol=data.get("symbol", data.get("s", "")),
            price=float(data.get("lastPrice", data.get("c", data.get("last_price", 0)))),
            bid=float(data.get("bidPrice", data.get("b", data.get("bid_price", 0)))),
            ask=float(data.get("askPrice", data.get("a", data.get("ask_price", 0)))),
            spread=0.0,
            volume=float(data.get("volume", data.get("v", data.get("volume_24h", 0)))),
            timestamp=datetime.utcnow()
        )
    
    def _binance_trade(self, data: Dict[str, Any]) -> MarketTick:
        """Binance trade format"""
        ts = data.get("T", data.get("time", time.time() * 1000))
        return MarketTick(
            exchange="BINANCE",
            symbol=data.get("s", data.get("symbol", "")),
            price=float(data.get("p", data.get("price", 0))),
            volume=float(data.get("q", data.get("qty", 0))),
            side="SELL" if data.get("m", False) else "BUY",
            trade_id=str(data.get("t", data.get("id", ""))),
            timestamp=datetime.fromtimestamp(ts / 1000) if ts > 1e10 else datetime.fromtimestamp(ts)
        )
    
    def _binance_candle(self, data: Dict[str, Any]) -> MarketCandle:
        """Binance kline format"""
        # Handle both REST and WebSocket formats
        if "k" in data:
            k = data["k"]
            return MarketCandle(
                exchange="BINANCE",
                symbol=k.get("s", ""),
                timeframe=k.get("i", "1m"),
                open=float(k.get("o", 0)),
                high=float(k.get("h", 0)),
                low=float(k.get("l", 0)),
                close=float(k.get("c", 0)),
                volume=float(k.get("v", 0)),
                quote_volume=float(k.get("q", 0)),
                trades_count=int(k.get("n", 0)),
                start_time=datetime.fromtimestamp(k.get("t", 0) / 1000),
                end_time=datetime.fromtimestamp(k.get("T", 0) / 1000),
                is_closed=k.get("x", False)
            )
        else:
            # REST format (list)
            if isinstance(data, list):
                return MarketCandle(
                    exchange="BINANCE",
                    symbol=data[11] if len(data) > 11 else "",
                    timeframe="1m",
                    open=float(data[1]),
                    high=float(data[2]),
                    low=float(data[3]),
                    close=float(data[4]),
                    volume=float(data[5]),
                    quote_volume=float(data[7]) if len(data) > 7 else 0,
                    trades_count=int(data[8]) if len(data) > 8 else 0,
                    start_time=datetime.fromtimestamp(data[0] / 1000),
                    end_time=datetime.fromtimestamp(data[6] / 1000) if len(data) > 6 else datetime.utcnow(),
                    is_closed=True
                )
            return self._generic_candle("BINANCE", data)
    
    def _binance_orderbook(self, data: Dict[str, Any]) -> MarketOrderbook:
        """Binance orderbook format"""
        raw_bids = data.get("bids", data.get("b", []))
        raw_asks = data.get("asks", data.get("a", []))
        
        # Ensure bids/asks are lists, not 0 or other invalid values
        if not isinstance(raw_bids, list):
            raw_bids = []
        if not isinstance(raw_asks, list):
            raw_asks = []
        
        bids = [
            OrderbookLevel(price=float(b[0]), size=float(b[1]))
            for b in raw_bids if isinstance(b, (list, tuple)) and len(b) >= 2
        ]
        asks = [
            OrderbookLevel(price=float(a[0]), size=float(a[1]))
            for a in raw_asks if isinstance(a, (list, tuple)) and len(a) >= 2
        ]
        
        ob = MarketOrderbook(
            exchange="BINANCE",
            symbol=data.get("symbol", data.get("s", "")),
            bids=bids,
            asks=asks,
            sequence=data.get("lastUpdateId", data.get("u")),
            timestamp=datetime.utcnow()
        )
        ob.calculate_metrics()
        return ob
    
    # ============================================
    # Bybit Normalizers
    # ============================================
    
    def _normalize_bybit(self, data_type: str, data: Dict[str, Any]) -> Any:
        """Normalize Bybit data"""
        if data_type == "ticker":
            return self._bybit_ticker(data)
        elif data_type == "trade":
            return self._bybit_trade(data)
        elif data_type == "candle":
            return self._bybit_candle(data)
        elif data_type == "orderbook":
            return self._bybit_orderbook(data)
        return None
    
    def _bybit_ticker(self, data: Dict[str, Any]) -> MarketTick:
        """Bybit ticker format"""
        return MarketTick(
            exchange="BYBIT",
            symbol=data.get("symbol", ""),
            price=float(data.get("lastPrice", data.get("last_price", 0))),
            bid=float(data.get("bid1Price", data.get("bid_price", 0))),
            ask=float(data.get("ask1Price", data.get("ask_price", 0))),
            volume=float(data.get("volume24h", data.get("volume_24h", 0))),
            timestamp=datetime.utcnow()
        )
    
    def _bybit_trade(self, data: Dict[str, Any]) -> MarketTick:
        """Bybit trade format"""
        ts = data.get("T", data.get("timestamp", time.time() * 1000))
        return MarketTick(
            exchange="BYBIT",
            symbol=data.get("s", data.get("symbol", "")),
            price=float(data.get("p", data.get("price", 0))),
            volume=float(data.get("v", data.get("size", 0))),
            side=data.get("S", data.get("side", "")).upper(),
            trade_id=str(data.get("i", data.get("id", ""))),
            timestamp=datetime.fromtimestamp(ts / 1000) if ts > 1e10 else datetime.fromtimestamp(ts)
        )
    
    def _bybit_candle(self, data: Dict[str, Any]) -> MarketCandle:
        """Bybit kline format"""
        return MarketCandle(
            exchange="BYBIT",
            symbol=data.get("symbol", ""),
            timeframe=data.get("interval", "1m"),
            open=float(data.get("open", 0)),
            high=float(data.get("high", 0)),
            low=float(data.get("low", 0)),
            close=float(data.get("close", 0)),
            volume=float(data.get("volume", 0)),
            quote_volume=float(data.get("turnover", 0)),
            start_time=datetime.fromtimestamp(int(data.get("start", 0)) / 1000) if data.get("start") else datetime.utcnow(),
            end_time=datetime.fromtimestamp(int(data.get("end", 0)) / 1000) if data.get("end") else datetime.utcnow(),
            is_closed=data.get("confirm", False)
        )
    
    def _bybit_orderbook(self, data: Dict[str, Any]) -> MarketOrderbook:
        """Bybit orderbook format"""
        raw_bids = data.get("b", data.get("bids", []))
        raw_asks = data.get("a", data.get("asks", []))
        
        # Ensure bids/asks are lists, not 0 or other invalid values
        if not isinstance(raw_bids, list):
            raw_bids = []
        if not isinstance(raw_asks, list):
            raw_asks = []
        
        bids = [
            OrderbookLevel(price=float(b[0]), size=float(b[1]))
            for b in raw_bids if isinstance(b, (list, tuple)) and len(b) >= 2
        ]
        asks = [
            OrderbookLevel(price=float(a[0]), size=float(a[1]))
            for a in raw_asks if isinstance(a, (list, tuple)) and len(a) >= 2
        ]
        
        ob = MarketOrderbook(
            exchange="BYBIT",
            symbol=data.get("s", data.get("symbol", "")),
            bids=bids,
            asks=asks,
            sequence=data.get("u", data.get("seq")),
            timestamp=datetime.utcnow()
        )
        ob.calculate_metrics()
        return ob
    
    # ============================================
    # OKX Normalizers
    # ============================================
    
    def _normalize_okx(self, data_type: str, data: Dict[str, Any]) -> Any:
        """Normalize OKX data"""
        if data_type == "ticker":
            return self._okx_ticker(data)
        elif data_type == "trade":
            return self._okx_trade(data)
        elif data_type == "candle":
            return self._okx_candle(data)
        elif data_type == "orderbook":
            return self._okx_orderbook(data)
        return None
    
    def _okx_ticker(self, data: Dict[str, Any]) -> MarketTick:
        """OKX ticker format"""
        symbol = data.get("instId", "").replace("-SWAP", "").replace("-", "")
        return MarketTick(
            exchange="OKX",
            symbol=symbol,
            price=float(data.get("last", data.get("last_price", 0))),
            bid=float(data.get("bidPx", data.get("bid_price", 0))),
            ask=float(data.get("askPx", data.get("ask_price", 0))),
            volume=float(data.get("vol24h", data.get("volume_24h", 0))),
            timestamp=datetime.utcnow()
        )
    
    def _okx_trade(self, data: Dict[str, Any]) -> MarketTick:
        """OKX trade format"""
        symbol = data.get("instId", "").replace("-SWAP", "").replace("-", "")
        ts = data.get("ts", time.time() * 1000)
        return MarketTick(
            exchange="OKX",
            symbol=symbol,
            price=float(data.get("px", data.get("price", 0))),
            volume=float(data.get("sz", data.get("size", 0))),
            side=data.get("side", "").upper(),
            trade_id=str(data.get("tradeId", "")),
            timestamp=datetime.fromtimestamp(int(ts) / 1000) if int(ts) > 1e10 else datetime.fromtimestamp(int(ts))
        )
    
    def _okx_candle(self, data: Dict[str, Any]) -> MarketCandle:
        """OKX candle format"""
        # OKX returns candles as arrays
        if isinstance(data, list):
            return MarketCandle(
                exchange="OKX",
                symbol="",
                timeframe="1m",
                open=float(data[1]),
                high=float(data[2]),
                low=float(data[3]),
                close=float(data[4]),
                volume=float(data[5]),
                quote_volume=float(data[6]) if len(data) > 6 else 0,
                start_time=datetime.fromtimestamp(int(data[0]) / 1000),
                end_time=datetime.utcnow(),
                is_closed=True
            )
        
        return MarketCandle(
            exchange="OKX",
            symbol=data.get("instId", "").replace("-SWAP", "").replace("-", ""),
            timeframe=data.get("bar", "1m"),
            open=float(data.get("o", 0)),
            high=float(data.get("h", 0)),
            low=float(data.get("l", 0)),
            close=float(data.get("c", 0)),
            volume=float(data.get("vol", 0)),
            start_time=datetime.fromtimestamp(int(data.get("ts", 0)) / 1000) if data.get("ts") else datetime.utcnow(),
            end_time=datetime.utcnow(),
            is_closed=data.get("confirm", "0") == "1"
        )
    
    def _okx_orderbook(self, data: Dict[str, Any]) -> MarketOrderbook:
        """OKX orderbook format"""
        symbol = data.get("instId", "").replace("-SWAP", "").replace("-", "")
        
        raw_bids = data.get("bids", [])
        raw_asks = data.get("asks", [])
        
        # Ensure bids/asks are lists, not 0 or other invalid values
        if not isinstance(raw_bids, list):
            raw_bids = []
        if not isinstance(raw_asks, list):
            raw_asks = []
        
        bids = [
            OrderbookLevel(price=float(b[0]), size=float(b[1]), orders_count=int(b[3]) if len(b) > 3 else 0)
            for b in raw_bids if isinstance(b, (list, tuple)) and len(b) >= 2
        ]
        asks = [
            OrderbookLevel(price=float(a[0]), size=float(a[1]), orders_count=int(a[3]) if len(a) > 3 else 0)
            for a in raw_asks if isinstance(a, (list, tuple)) and len(a) >= 2
        ]
        
        ob = MarketOrderbook(
            exchange="OKX",
            symbol=symbol,
            bids=bids,
            asks=asks,
            sequence=data.get("seqId"),
            timestamp=datetime.utcnow()
        )
        ob.calculate_metrics()
        return ob
    
    # ============================================
    # Generic Normalizers
    # ============================================
    
    def _generic_ticker(self, exchange: str, data: Dict[str, Any]) -> MarketTick:
        """Generic ticker normalizer"""
        return MarketTick(
            exchange=exchange,
            symbol=data.get("symbol", ""),
            price=float(data.get("price", data.get("last_price", data.get("lastPrice", 0)))),
            bid=float(data.get("bid", data.get("bid_price", data.get("bidPrice", 0)))),
            ask=float(data.get("ask", data.get("ask_price", data.get("askPrice", 0)))),
            volume=float(data.get("volume", data.get("volume_24h", 0))),
            timestamp=datetime.utcnow()
        )
    
    def _generic_trade(self, exchange: str, data: Dict[str, Any]) -> MarketTick:
        """Generic trade normalizer"""
        return MarketTick(
            exchange=exchange,
            symbol=data.get("symbol", ""),
            price=float(data.get("price", 0)),
            volume=float(data.get("volume", data.get("size", data.get("qty", 0)))),
            side=data.get("side", "").upper(),
            timestamp=datetime.utcnow()
        )
    
    def _generic_candle(self, exchange: str, data: Dict[str, Any]) -> MarketCandle:
        """Generic candle normalizer"""
        return MarketCandle(
            exchange=exchange,
            symbol=data.get("symbol", ""),
            timeframe=data.get("timeframe", data.get("interval", "1m")),
            open=float(data.get("open", data.get("o", 0))),
            high=float(data.get("high", data.get("h", 0))),
            low=float(data.get("low", data.get("l", 0))),
            close=float(data.get("close", data.get("c", 0))),
            volume=float(data.get("volume", data.get("v", 0))),
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            is_closed=data.get("is_closed", False)
        )
    
    def _generic_orderbook(self, exchange: str, data: Dict[str, Any]) -> MarketOrderbook:
        """Generic orderbook normalizer"""
        raw_bids = data.get("bids", [])
        raw_asks = data.get("asks", [])
        
        # Ensure bids/asks are lists, not 0 or other invalid values
        if not isinstance(raw_bids, list):
            raw_bids = []
        if not isinstance(raw_asks, list):
            raw_asks = []
        
        bids = [
            OrderbookLevel(price=float(b[0]), size=float(b[1]))
            for b in raw_bids if isinstance(b, (list, tuple)) and len(b) >= 2
        ]
        asks = [
            OrderbookLevel(price=float(a[0]), size=float(a[1]))
            for a in raw_asks if isinstance(a, (list, tuple)) and len(a) >= 2
        ]
        
        ob = MarketOrderbook(
            exchange=exchange,
            symbol=data.get("symbol", ""),
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow()
        )
        ob.calculate_metrics()
        return ob
