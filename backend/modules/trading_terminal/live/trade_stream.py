"""
Trade Stream Processor
Processes aggregated trades from Binance WebSocket for microstructure analysis.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Single aggregated trade"""
    agg_trade_id: int
    price: float
    quantity: float
    first_trade_id: int
    last_trade_id: int
    timestamp: datetime
    is_buyer_maker: bool  # True = sell (maker was buyer), False = buy
    
    @property
    def side(self) -> str:
        return "SELL" if self.is_buyer_maker else "BUY"
    
    @property
    def value_usd(self) -> float:
        return self.price * self.quantity


@dataclass 
class TradeStream:
    """
    Manages trade stream with rolling window analysis.
    Detects large trades, buy/sell pressure, sweep patterns.
    """
    
    symbol: str = ""
    trades: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    # Aggregated stats (rolling window)
    window_seconds: int = 60  # 1 minute window
    
    # Stats
    total_trades: int = 0
    total_buy_volume: float = 0.0
    total_sell_volume: float = 0.0
    last_trade_time: Optional[datetime] = None
    
    # Large trade detection
    large_trade_threshold_btc: float = 1.0  # 1 BTC
    large_trades: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def process_trade(self, data: Dict) -> Optional[Trade]:
        """
        Process aggregated trade from WebSocket.
        
        data format:
        {
            "e": "aggTrade",
            "E": 123456789,    # Event time
            "s": "BTCUSDT",    # Symbol
            "a": 12345,        # Aggregate trade ID
            "p": "0.001",      # Price
            "q": "100",        # Quantity
            "f": 100,          # First trade ID
            "l": 105,          # Last trade ID
            "T": 123456785,    # Trade time
            "m": true          # Is buyer maker
        }
        """
        try:
            trade = Trade(
                agg_trade_id=data.get("a", 0),
                price=float(data.get("p", 0)),
                quantity=float(data.get("q", 0)),
                first_trade_id=data.get("f", 0),
                last_trade_id=data.get("l", 0),
                timestamp=datetime.fromtimestamp(data.get("T", 0) / 1000, tz=timezone.utc),
                is_buyer_maker=data.get("m", False)
            )
            
            self.trades.append(trade)
            self.total_trades += 1
            self.last_trade_time = trade.timestamp
            
            # Update volume stats
            if trade.is_buyer_maker:
                self.total_sell_volume += trade.quantity
            else:
                self.total_buy_volume += trade.quantity
            
            # Detect large trades
            if trade.quantity >= self.large_trade_threshold_btc:
                self.large_trades.append(trade)
                logger.info(f"[TradeStream] Large trade: {trade.side} {trade.quantity:.4f} @ {trade.price:.2f}")
            
            return trade
            
        except Exception as e:
            logger.error(f"[TradeStream] Trade processing error: {e}")
            return None
    
    def get_recent_trades(self, seconds: int = 60) -> List[Trade]:
        """Get trades from last N seconds"""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - seconds
        
        return [t for t in self.trades if t.timestamp.timestamp() >= cutoff]
    
    def get_buy_sell_ratio(self, seconds: int = 60) -> Dict:
        """Calculate buy/sell volume ratio for recent trades"""
        recent = self.get_recent_trades(seconds)
        
        buy_vol = sum(t.quantity for t in recent if not t.is_buyer_maker)
        sell_vol = sum(t.quantity for t in recent if t.is_buyer_maker)
        total = buy_vol + sell_vol
        
        if total == 0:
            return {"buy_ratio": 0.5, "sell_ratio": 0.5, "delta": 0, "pressure": "neutral"}
        
        buy_ratio = buy_vol / total
        sell_ratio = sell_vol / total
        delta = buy_vol - sell_vol
        
        if buy_ratio > 0.6:
            pressure = "strong_buy"
        elif buy_ratio > 0.55:
            pressure = "buy"
        elif sell_ratio > 0.6:
            pressure = "strong_sell"
        elif sell_ratio > 0.55:
            pressure = "sell"
        else:
            pressure = "neutral"
        
        return {
            "buy_volume": round(buy_vol, 4),
            "sell_volume": round(sell_vol, 4),
            "buy_ratio": round(buy_ratio, 3),
            "sell_ratio": round(sell_ratio, 3),
            "delta": round(delta, 4),
            "pressure": pressure,
            "trade_count": len(recent)
        }
    
    def get_vwap(self, seconds: int = 60) -> float:
        """Calculate VWAP for recent trades"""
        recent = self.get_recent_trades(seconds)
        
        if not recent:
            return 0.0
        
        total_value = sum(t.price * t.quantity for t in recent)
        total_qty = sum(t.quantity for t in recent)
        
        return total_value / total_qty if total_qty > 0 else 0.0
    
    def detect_sweep(self, seconds: int = 5, min_trades: int = 3, min_volume: float = 2.0) -> Optional[Dict]:
        """
        Detect potential sweep pattern (rapid large trades in one direction).
        """
        recent = self.get_recent_trades(seconds)
        
        if len(recent) < min_trades:
            return None
        
        # Check if mostly one direction
        buy_trades = [t for t in recent if not t.is_buyer_maker]
        sell_trades = [t for t in recent if t.is_buyer_maker]
        
        buy_vol = sum(t.quantity for t in buy_trades)
        sell_vol = sum(t.quantity for t in sell_trades)
        
        # Buy sweep
        if buy_vol >= min_volume and buy_vol > sell_vol * 3:
            return {
                "type": "buy_sweep",
                "volume": round(buy_vol, 4),
                "trade_count": len(buy_trades),
                "avg_price": self.get_vwap(seconds),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Sell sweep
        if sell_vol >= min_volume and sell_vol > buy_vol * 3:
            return {
                "type": "sell_sweep",
                "volume": round(sell_vol, 4),
                "trade_count": len(sell_trades),
                "avg_price": self.get_vwap(seconds),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return None
    
    def get_summary(self) -> Dict:
        """Get trade stream summary"""
        bs_ratio = self.get_buy_sell_ratio(60)
        sweep = self.detect_sweep()
        
        return {
            "symbol": self.symbol,
            "total_trades": self.total_trades,
            "recent_trades": len(self.get_recent_trades(60)),
            "vwap_1m": round(self.get_vwap(60), 2),
            "buy_sell": bs_ratio,
            "sweep_detected": sweep,
            "large_trades_count": len(self.large_trades),
            "last_trade": self.last_trade_time.isoformat() if self.last_trade_time else None
        }
