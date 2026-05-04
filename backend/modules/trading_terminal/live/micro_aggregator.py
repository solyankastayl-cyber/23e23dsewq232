"""
Microstructure Aggregator for Trading Terminal
Aggregates real-time orderbook and trade data into actionable signals
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import random


@dataclass
class MicroSnapshot:
    """Single microstructure measurement"""
    timestamp: datetime
    imbalance: float  # -1 to +1 (negative = sell pressure)
    spread: float     # in price units
    spread_bps: float # in basis points
    liquidity_score: float  # 0 to 1
    bid_volume: float
    ask_volume: float
    

@dataclass
class MicroAggregator:
    """Aggregates microstructure snapshots over time window"""
    
    window: List[MicroSnapshot] = field(default_factory=list)
    max_window_size: int = 100
    
    def add(self, snapshot: MicroSnapshot):
        """Add new snapshot to window"""
        self.window.append(snapshot)
        if len(self.window) > self.max_window_size:
            self.window.pop(0)
    
    def summary(self) -> Dict:
        """Get aggregated summary of current window"""
        if not self.window:
            return {
                "imbalance": 0.0,
                "spread_avg": 0.0,
                "liquidity_score": 0.5,
                "samples": 0
            }
        
        n = len(self.window)
        return {
            "imbalance": sum(x.imbalance for x in self.window) / n,
            "spread_avg": sum(x.spread for x in self.window) / n,
            "spread_bps_avg": sum(x.spread_bps for x in self.window) / n,
            "liquidity_score": sum(x.liquidity_score for x in self.window) / n,
            "bid_volume_avg": sum(x.bid_volume for x in self.window) / n,
            "ask_volume_avg": sum(x.ask_volume for x in self.window) / n,
            "samples": n
        }


class MicroFeatures:
    """Computes microstructure features from orderbook data"""
    
    @staticmethod
    def compute_imbalance(bids: List[tuple], asks: List[tuple]) -> float:
        """
        Compute orderbook imbalance: (bid_vol - ask_vol) / (bid_vol + ask_vol)
        Returns value between -1 (strong sell) and +1 (strong buy)
        """
        bid_vol = sum(v for _, v in bids) if bids else 0
        ask_vol = sum(v for _, v in asks) if asks else 0
        
        total = bid_vol + ask_vol
        if total == 0:
            return 0.0
        
        return (bid_vol - ask_vol) / total
    
    @staticmethod
    def compute_spread(best_bid: float, best_ask: float, mid_price: float) -> Dict:
        """Compute spread in absolute and basis points"""
        spread = best_ask - best_bid
        spread_bps = (spread / mid_price) * 10000 if mid_price > 0 else 0
        
        return {
            "spread": spread,
            "spread_bps": spread_bps
        }
    
    @staticmethod
    def compute_liquidity_score(bid_depth: float, ask_depth: float) -> float:
        """
        Liquidity score 0-1 based on depth
        Higher = more liquid
        """
        total_depth = bid_depth + ask_depth
        if total_depth == 0:
            return 0.0
        
        # Normalize based on typical BTC depth (~$5M each side)
        normalized = min(total_depth / 10_000_000, 1.0)
        return normalized
    
    @staticmethod
    def get_liquidity_state(imbalance: float, liquidity_score: float) -> str:
        """Classify current liquidity state"""
        if liquidity_score < 0.2:
            return "thin"
        elif liquidity_score < 0.4:
            return "light"
        elif imbalance > 0.3:
            return "strong_bid"
        elif imbalance < -0.3:
            return "strong_ask"
        else:
            return "balanced"


# Global aggregator instance per symbol
_aggregators: Dict[str, MicroAggregator] = {}


def get_aggregator(symbol: str) -> MicroAggregator:
    """Get or create aggregator for symbol"""
    if symbol not in _aggregators:
        _aggregators[symbol] = MicroAggregator()
    return _aggregators[symbol]


def get_mock_micro_data(symbol: str = "BTCUSDT") -> Dict:
    """
    Generate mock microstructure data for development.
    In production, this would be replaced with real WebSocket data.
    """
    # Simulate some randomness but with realistic ranges
    base_imbalance = random.uniform(-0.4, 0.4)
    imbalance_noise = random.uniform(-0.1, 0.1)
    imbalance = max(-1, min(1, base_imbalance + imbalance_noise))
    
    spread = random.uniform(0.3, 1.2)  # BTCUSDT typical spread
    spread_bps = random.uniform(0.5, 2.0)
    
    liquidity_score = random.uniform(0.5, 0.95)
    
    features = MicroFeatures()
    liquidity_state = features.get_liquidity_state(imbalance, liquidity_score)
    
    # Determine overall micro state
    if imbalance > 0.2 and liquidity_score > 0.6 and spread_bps < 1.5:
        state = "favorable"
        confidence = min(0.95, 0.7 + abs(imbalance) * 0.3 + liquidity_score * 0.2)
    elif abs(imbalance) < 0.1 and liquidity_score > 0.5:
        state = "neutral"
        confidence = 0.5 + liquidity_score * 0.2
    elif spread_bps > 2.0 or liquidity_score < 0.3:
        state = "hostile"
        confidence = 0.3 - (spread_bps - 2.0) * 0.05
    else:
        state = "caution"
        confidence = 0.5
    
    # Sweep detection (mock)
    sweep_detected = random.random() < 0.1
    sweep_status = "completed" if sweep_detected else "none"
    
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "imbalance": round(imbalance, 3),
        "spread": round(spread, 2),
        "spread_bps": round(spread_bps, 2),
        "liquidity_score": round(liquidity_score, 2),
        "liquidity_state": liquidity_state,
        "state": state,
        "confidence": round(confidence, 2),
        "sweep_status": sweep_status,
        "bid_volume": round(random.uniform(100, 500), 2),
        "ask_volume": round(random.uniform(100, 500), 2)
    }
