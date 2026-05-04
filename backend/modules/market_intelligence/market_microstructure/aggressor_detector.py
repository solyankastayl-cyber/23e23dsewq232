"""
PHASE 9 - Aggressor Detector
=============================
Determines who initiated trades (buyer or seller aggressor).

Logic:
- Trade near ask -> buyer aggressor
- Trade near bid -> seller aggressor
- Tracks aggressor shifts over time
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from .microstructure_types import (
    AggressorSide, AggressorAnalysis, DEFAULT_MICROSTRUCTURE_CONFIG
)
from .order_flow_engine import Trade


class AggressorDetector:
    """
    Aggressor Side Detection Engine
    
    Determines whether buyers or sellers are initiating trades,
    which indicates who is more aggressive/motivated.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_MICROSTRUCTURE_CONFIG
        self.history: List[AggressorAnalysis] = []
        self.max_history = 100
    
    def detect_aggressor(
        self,
        trades: List[Trade],
        bid_price: float,
        ask_price: float,
        symbol: str = "BTCUSDT"
    ) -> AggressorAnalysis:
        """
        Detect which side is the aggressor in recent trades.
        
        Args:
            trades: List of recent trades
            bid_price: Current best bid
            ask_price: Current best ask
            symbol: Trading symbol
            
        Returns:
            AggressorAnalysis with detection results
        """
        now = datetime.now(timezone.utc)
        
        if not trades:
            return self._empty_analysis(symbol, now)
        
        mid_price = (bid_price + ask_price) / 2
        spread = ask_price - bid_price
        
        # Classify each trade
        buy_initiated = 0
        sell_initiated = 0
        unclear = 0
        
        for trade in trades:
            classification = self._classify_trade(trade, bid_price, ask_price, spread)
            if classification == "BUY":
                buy_initiated += 1
            elif classification == "SELL":
                sell_initiated += 1
            else:
                unclear += 1
        
        total_classified = buy_initiated + sell_initiated
        total_trades = len(trades)
        
        # Calculate ratios
        buy_initiated_pct = buy_initiated / total_trades if total_trades > 0 else 0
        sell_initiated_pct = sell_initiated / total_trades if total_trades > 0 else 0
        
        aggressor_ratio = buy_initiated / total_classified if total_classified > 0 else 0.5
        
        # Determine aggressor side
        threshold = self.config["aggressor_threshold"]
        
        if aggressor_ratio > threshold:
            aggressor_side = AggressorSide.BUYER
            confidence = (aggressor_ratio - 0.5) * 2  # Scale to 0-1
        elif aggressor_ratio < (1 - threshold):
            aggressor_side = AggressorSide.SELLER
            confidence = ((1 - aggressor_ratio) - 0.5) * 2
        elif unclear > total_classified * 0.3:
            aggressor_side = AggressorSide.UNCLEAR
            confidence = 0.3
        else:
            aggressor_side = AggressorSide.NEUTRAL
            confidence = 0.5
        
        confidence = min(1.0, max(0.0, confidence))
        
        # Check for shift
        aggressor_shift = False
        previous_aggressor = None
        shift_timestamp = None
        
        if self.history:
            last = self.history[-1]
            if last.aggressor_side != aggressor_side and \
               last.aggressor_side not in [AggressorSide.NEUTRAL, AggressorSide.UNCLEAR]:
                aggressor_shift = True
                previous_aggressor = last.aggressor_side
                shift_timestamp = now
        
        # Calculate analysis window
        if trades:
            window_ms = trades[-1].timestamp - trades[0].timestamp
        else:
            window_ms = 0
        
        analysis = AggressorAnalysis(
            symbol=symbol,
            timestamp=now,
            aggressor_side=aggressor_side,
            aggressor_confidence=confidence,
            aggressor_ratio=aggressor_ratio,
            buy_initiated_pct=buy_initiated_pct,
            sell_initiated_pct=sell_initiated_pct,
            aggressor_shift=aggressor_shift,
            previous_aggressor=previous_aggressor,
            shift_timestamp=shift_timestamp,
            trade_count=total_trades,
            analysis_window_ms=window_ms
        )
        
        # Save to history
        self._add_to_history(analysis)
        
        return analysis
    
    def _classify_trade(
        self,
        trade: Trade,
        bid_price: float,
        ask_price: float,
        spread: float
    ) -> str:
        """
        Classify a single trade as buyer/seller initiated.
        
        Returns: "BUY", "SELL", or "UNCLEAR"
        """
        # Distance from bid and ask
        dist_from_bid = abs(trade.price - bid_price)
        dist_from_ask = abs(trade.price - ask_price)
        
        # Threshold for classification (within 30% of spread)
        threshold = spread * 0.3
        
        # At or above ask = buyer aggressor
        if trade.price >= ask_price or dist_from_ask < threshold:
            return "BUY"
        
        # At or below bid = seller aggressor
        if trade.price <= bid_price or dist_from_bid < threshold:
            return "SELL"
        
        # Middle of spread = unclear, use trade side as hint
        if trade.side:
            return trade.side
        
        return "UNCLEAR"
    
    def _empty_analysis(self, symbol: str, timestamp: datetime) -> AggressorAnalysis:
        """Return empty analysis when no data."""
        return AggressorAnalysis(
            symbol=symbol,
            timestamp=timestamp,
            aggressor_side=AggressorSide.NEUTRAL,
            aggressor_confidence=0,
            aggressor_ratio=0.5,
            buy_initiated_pct=0,
            sell_initiated_pct=0,
            aggressor_shift=False,
            previous_aggressor=None,
            shift_timestamp=None,
            trade_count=0,
            analysis_window_ms=0
        )
    
    def _add_to_history(self, analysis: AggressorAnalysis):
        """Add analysis to history, maintaining max size."""
        self.history.append(analysis)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_aggressor_trend(self, periods: int = 5) -> Dict:
        """Get trend of aggressor over recent periods."""
        if len(self.history) < periods:
            return {"trend": "INSUFFICIENT_DATA", "periods": len(self.history)}
        
        recent = self.history[-periods:]
        
        # Count aggressor types
        buyer_count = sum(1 for a in recent if a.aggressor_side == AggressorSide.BUYER)
        seller_count = sum(1 for a in recent if a.aggressor_side == AggressorSide.SELLER)
        
        # Determine trend
        if buyer_count > seller_count * 1.5:
            trend = "BUYER_DOMINATED"
        elif seller_count > buyer_count * 1.5:
            trend = "SELLER_DOMINATED"
        else:
            trend = "MIXED"
        
        # Shift count
        shifts = sum(1 for a in recent if a.aggressor_shift)
        
        return {
            "trend": trend,
            "buyer_periods": buyer_count,
            "seller_periods": seller_count,
            "shift_count": shifts,
            "current_aggressor": recent[-1].aggressor_side.value,
            "periods": periods
        }
    
    def get_shift_signals(self) -> List[Dict]:
        """Get recent aggressor shift signals."""
        shifts = [a for a in self.history if a.aggressor_shift][-5:]
        
        return [
            {
                "timestamp": a.shift_timestamp.isoformat() if a.shift_timestamp else None,
                "from": a.previous_aggressor.value if a.previous_aggressor else None,
                "to": a.aggressor_side.value,
                "confidence": round(a.aggressor_confidence, 3)
            }
            for a in shifts
        ]
