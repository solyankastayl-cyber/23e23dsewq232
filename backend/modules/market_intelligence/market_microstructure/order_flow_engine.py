"""
PHASE 9 - Order Flow Engine
============================
Analyzes trade flow and orderbook updates.

Calculates:
- Buy flow vs sell flow
- Aggressive flow detection
- Burst activity
- Flow persistence
- Short-term absorption
"""

import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .microstructure_types import (
    FlowState, OrderFlowSnapshot, DEFAULT_MICROSTRUCTURE_CONFIG
)


@dataclass
class Trade:
    """Single trade for analysis"""
    price: float
    size: float
    side: str  # BUY or SELL
    timestamp: int  # ms
    is_aggressive: bool = False


class OrderFlowEngine:
    """
    Order Flow Analysis Engine
    
    Analyzes the flow of trades to understand:
    - Who is buying/selling
    - How aggressive is the flow
    - Is there burst activity
    - Is flow persistent or choppy
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_MICROSTRUCTURE_CONFIG
        self.flow_history: List[OrderFlowSnapshot] = []
        self.max_history = 100
    
    def analyze_flow(
        self,
        trades: List[Trade],
        bid_price: float,
        ask_price: float,
        symbol: str = "BTCUSDT"
    ) -> OrderFlowSnapshot:
        """
        Analyze order flow from recent trades.
        
        Args:
            trades: List of recent trades
            bid_price: Current best bid
            ask_price: Current best ask
            symbol: Trading symbol
            
        Returns:
            OrderFlowSnapshot with flow analysis
        """
        now = datetime.now(timezone.utc)
        
        if not trades:
            return self._empty_snapshot(symbol, now)
        
        # Calculate flow metrics
        buy_flow = sum(t.size for t in trades if t.side == "BUY")
        sell_flow = sum(t.size for t in trades if t.side == "SELL")
        total_flow = buy_flow + sell_flow
        
        net_flow = buy_flow - sell_flow
        flow_ratio = buy_flow / total_flow if total_flow > 0 else 0.5
        
        # Calculate aggressive flow (trades at or through bid/ask)
        mid_price = (bid_price + ask_price) / 2
        aggressive_buy = sum(t.size for t in trades if t.side == "BUY" and t.price >= ask_price - 0.01)
        aggressive_sell = sum(t.size for t in trades if t.side == "SELL" and t.price <= bid_price + 0.01)
        
        total_aggressive = aggressive_buy + aggressive_sell
        aggression_score = 0.0
        if total_aggressive > 0:
            aggression_score = (aggressive_buy - aggressive_sell) / total_aggressive
        
        # Detect bursts
        avg_size = total_flow / len(trades) if trades else 0
        burst_threshold = avg_size * self.config["burst_threshold"]
        burst_trades = [t for t in trades if t.size > burst_threshold]
        burst_detected = len(burst_trades) > 0
        burst_direction = None
        if burst_detected:
            burst_buys = sum(1 for t in burst_trades if t.side == "BUY")
            burst_sells = len(burst_trades) - burst_buys
            burst_direction = "BUY" if burst_buys > burst_sells else "SELL" if burst_sells > burst_buys else "MIXED"
        
        # Flow persistence (consistency of direction)
        flow_persistence = self._calculate_persistence(trades)
        
        # Absorption detection (high volume with low price movement)
        absorption_detected = self._detect_absorption(trades, mid_price)
        
        # Calculate pressures
        buy_pressure = flow_ratio
        sell_pressure = 1 - flow_ratio
        
        # Determine flow state
        flow_state = self._determine_flow_state(
            flow_ratio, aggression_score, burst_detected, burst_direction, flow_persistence
        )
        
        snapshot = OrderFlowSnapshot(
            symbol=symbol,
            timestamp=now,
            flow_state=flow_state,
            buy_flow=buy_flow,
            sell_flow=sell_flow,
            net_flow=net_flow,
            flow_ratio=flow_ratio,
            aggressive_buy=aggressive_buy,
            aggressive_sell=aggressive_sell,
            aggression_score=aggression_score,
            burst_detected=burst_detected,
            burst_direction=burst_direction,
            flow_persistence=flow_persistence,
            absorption_detected=absorption_detected,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure
        )
        
        # Save to history
        self._add_to_history(snapshot)
        
        return snapshot
    
    def _determine_flow_state(
        self,
        flow_ratio: float,
        aggression_score: float,
        burst_detected: bool,
        burst_direction: Optional[str],
        persistence: float
    ) -> FlowState:
        """Determine overall flow state."""
        
        # Burst states take priority
        if burst_detected:
            if burst_direction == "BUY":
                return FlowState.BURST_BUY
            elif burst_direction == "SELL":
                return FlowState.BURST_SELL
        
        # Check for dominance
        threshold = self.config["aggressor_threshold"]
        
        if flow_ratio > threshold and aggression_score > 0.2:
            return FlowState.BUYER_DOMINANT
        elif flow_ratio < (1 - threshold) and aggression_score < -0.2:
            return FlowState.SELLER_DOMINANT
        
        # Check for choppy vs balanced
        if persistence < 0.3:
            return FlowState.CHOPPY
        
        return FlowState.BALANCED
    
    def _calculate_persistence(self, trades: List[Trade]) -> float:
        """Calculate flow persistence (consistency of direction)."""
        if len(trades) < 2:
            return 0.5
        
        # Count consecutive same-direction trades
        consecutive_runs = []
        current_run = 1
        current_side = trades[0].side
        
        for i in range(1, len(trades)):
            if trades[i].side == current_side:
                current_run += 1
            else:
                consecutive_runs.append(current_run)
                current_run = 1
                current_side = trades[i].side
        consecutive_runs.append(current_run)
        
        # Higher average run length = higher persistence
        avg_run = sum(consecutive_runs) / len(consecutive_runs) if consecutive_runs else 1
        max_possible_run = len(trades)
        
        return min(1.0, avg_run / (max_possible_run * 0.3))  # Normalize
    
    def _detect_absorption(self, trades: List[Trade], mid_price: float) -> bool:
        """Detect absorption (high volume, low price change)."""
        if len(trades) < 5:
            return False
        
        # Calculate price range
        prices = [t.price for t in trades]
        price_range = max(prices) - min(prices)
        price_range_pct = price_range / mid_price if mid_price > 0 else 0
        
        # High volume with low price movement indicates absorption
        total_volume = sum(t.size for t in trades)
        avg_volume = total_volume / len(trades)
        
        # Threshold: large volume but price moved less than 0.1%
        return avg_volume > 0 and price_range_pct < 0.001
    
    def _empty_snapshot(self, symbol: str, timestamp: datetime) -> OrderFlowSnapshot:
        """Return empty snapshot when no data."""
        return OrderFlowSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            flow_state=FlowState.BALANCED,
            buy_flow=0,
            sell_flow=0,
            net_flow=0,
            flow_ratio=0.5,
            aggressive_buy=0,
            aggressive_sell=0,
            aggression_score=0,
            burst_detected=False,
            burst_direction=None,
            flow_persistence=0,
            absorption_detected=False,
            buy_pressure=0.5,
            sell_pressure=0.5
        )
    
    def _add_to_history(self, snapshot: OrderFlowSnapshot):
        """Add snapshot to history, maintaining max size."""
        self.flow_history.append(snapshot)
        if len(self.flow_history) > self.max_history:
            self.flow_history = self.flow_history[-self.max_history:]
    
    def get_flow_trend(self, periods: int = 5) -> Dict:
        """Get trend of flow over recent periods."""
        if len(self.flow_history) < periods:
            return {"trend": "INSUFFICIENT_DATA", "periods": len(self.flow_history)}
        
        recent = self.flow_history[-periods:]
        
        # Calculate trend
        ratios = [s.flow_ratio for s in recent]
        trend_direction = "UP" if ratios[-1] > ratios[0] else "DOWN" if ratios[-1] < ratios[0] else "FLAT"
        
        avg_ratio = sum(ratios) / len(ratios)
        avg_aggression = sum(s.aggression_score for s in recent) / len(recent)
        
        return {
            "trend": trend_direction,
            "avg_flow_ratio": round(avg_ratio, 4),
            "avg_aggression": round(avg_aggression, 4),
            "periods": periods,
            "dominant_state": recent[-1].flow_state.value
        }


def generate_mock_trades(
    current_price: float = 64000.0,
    count: int = 50,
    bias: str = "NEUTRAL"
) -> Tuple[List[Trade], float, float]:
    """
    Generate mock trades for testing.
    
    Args:
        current_price: Current market price
        count: Number of trades to generate
        bias: BUY, SELL, or NEUTRAL
        
    Returns:
        Tuple of (trades, bid_price, ask_price)
    """
    trades = []
    spread = current_price * 0.0001  # 1 bps spread
    bid_price = current_price - spread / 2
    ask_price = current_price + spread / 2
    
    # Bias probability
    buy_prob = 0.5
    if bias == "BUY":
        buy_prob = 0.65
    elif bias == "SELL":
        buy_prob = 0.35
    
    base_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    for i in range(count):
        side = "BUY" if random.random() < buy_prob else "SELL"
        
        # Price slightly varies
        if side == "BUY":
            price = ask_price + random.gauss(0, spread * 0.5)
        else:
            price = bid_price + random.gauss(0, spread * 0.5)
        
        # Size varies with occasional large trades
        size = abs(random.gauss(0.5, 0.3))
        if random.random() < 0.1:  # 10% chance of larger trade
            size *= random.uniform(2, 5)
        
        # Is aggressive (near or through spread)
        is_aggressive = (side == "BUY" and price >= ask_price - 0.01) or \
                       (side == "SELL" and price <= bid_price + 0.01)
        
        trades.append(Trade(
            price=price,
            size=size,
            side=side,
            timestamp=base_time + i * 100,  # 100ms apart
            is_aggressive=is_aggressive
        ))
    
    return trades, bid_price, ask_price
