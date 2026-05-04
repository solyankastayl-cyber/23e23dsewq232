"""
Microstructure Features Calculator
Computes real-time microstructure signals from orderbook and trade data.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class MicroFeatures:
    """Microstructure feature calculations"""
    
    @staticmethod
    def compute_imbalance(bids: list, asks: list) -> float:
        """
        Compute orderbook imbalance: (bid_vol - ask_vol) / (bid_vol + ask_vol)
        Returns value between -1 (strong sell) and +1 (strong buy)
        """
        bid_vol = sum(qty for _, qty in bids) if bids else 0
        ask_vol = sum(qty for _, qty in asks) if asks else 0
        
        total = bid_vol + ask_vol
        if total == 0:
            return 0.0
        
        return (bid_vol - ask_vol) / total
    
    @staticmethod
    def compute_spread(best_bid: float, best_ask: float) -> Dict:
        """Compute spread in absolute and basis points"""
        if best_bid == 0 or best_ask == 0:
            return {"spread": 0.0, "spread_bps": 0.0}
        
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2
        spread_bps = (spread / mid) * 10000 if mid > 0 else 0
        
        return {
            "spread": round(spread, 4),
            "spread_bps": round(spread_bps, 2)
        }
    
    @staticmethod
    def compute_liquidity_score(bid_depth_usd: float, ask_depth_usd: float) -> float:
        """
        Liquidity score 0-1 based on depth.
        Higher = more liquid.
        Normalized to ~$10M typical BTC depth.
        """
        total_depth = bid_depth_usd + ask_depth_usd
        if total_depth == 0:
            return 0.0
        
        # Normalize based on typical depth
        normalized = min(total_depth / 10_000_000, 1.0)
        return round(normalized, 3)
    
    @staticmethod
    def get_liquidity_state(imbalance: float, liquidity_score: float) -> str:
        """Classify current liquidity state"""
        if liquidity_score < 0.1:
            return "thin"
        elif liquidity_score < 0.3:
            return "light"
        elif imbalance > 0.3:
            return "strong_bid"
        elif imbalance < -0.3:
            return "strong_ask"
        elif abs(imbalance) < 0.1:
            return "balanced"
        elif imbalance > 0:
            return "bid_heavy"
        else:
            return "ask_heavy"
    
    @staticmethod
    def compute_micro_state(
        imbalance: float,
        spread_bps: float,
        liquidity_score: float,
        trade_pressure: str = "neutral"
    ) -> Dict:
        """
        Compute overall microstructure state and confidence.
        
        Returns:
        - state: favorable / neutral / caution / hostile
        - confidence: 0.0 - 1.0
        """
        # Base confidence from liquidity
        confidence = 0.3 + liquidity_score * 0.3
        
        # Spread factor
        if spread_bps < 1.0:
            confidence += 0.15
            spread_quality = "tight"
        elif spread_bps < 2.0:
            confidence += 0.05
            spread_quality = "normal"
        elif spread_bps < 4.0:
            spread_quality = "wide"
        else:
            confidence -= 0.15
            spread_quality = "very_wide"
        
        # Imbalance factor
        if abs(imbalance) > 0.4:
            confidence += 0.1
        elif abs(imbalance) > 0.2:
            confidence += 0.05
        
        # Trade pressure factor
        if trade_pressure in ["strong_buy", "strong_sell"]:
            confidence += 0.1
        elif trade_pressure in ["buy", "sell"]:
            confidence += 0.05
        
        # Clamp confidence
        confidence = max(0.1, min(0.95, confidence))
        
        # Determine state
        if liquidity_score < 0.1 or spread_bps > 5.0:
            state = "hostile"
        elif spread_bps > 3.0 or liquidity_score < 0.2:
            state = "caution"
        elif imbalance > 0.2 and liquidity_score > 0.4 and spread_bps < 2.0:
            state = "favorable"
        elif imbalance < -0.2 and liquidity_score > 0.4 and spread_bps < 2.0:
            state = "favorable"  # Also favorable for shorts
        else:
            state = "neutral"
        
        return {
            "state": state,
            "confidence": round(confidence, 2),
            "spread_quality": spread_quality,
            "factors": {
                "imbalance_signal": "bullish" if imbalance > 0.1 else "bearish" if imbalance < -0.1 else "neutral",
                "liquidity_signal": "good" if liquidity_score > 0.4 else "weak" if liquidity_score < 0.2 else "moderate",
                "spread_signal": spread_quality
            }
        }


@dataclass
class MicroSnapshot:
    """Point-in-time microstructure snapshot"""
    timestamp: datetime
    symbol: str
    
    # Orderbook
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_bps: float
    imbalance: float
    bid_depth_usd: float
    ask_depth_usd: float
    liquidity_score: float
    liquidity_state: str
    
    # Trade flow
    buy_volume: float
    sell_volume: float
    trade_pressure: str
    vwap: float
    
    # Computed
    state: str
    confidence: float
    sweep_detected: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "orderbook": {
                "best_bid": self.best_bid,
                "best_ask": self.best_ask,
                "mid_price": self.mid_price,
                "spread": self.spread,
                "spread_bps": self.spread_bps,
                "imbalance": round(self.imbalance, 3),
                "bid_depth_usd": round(self.bid_depth_usd, 2),
                "ask_depth_usd": round(self.ask_depth_usd, 2)
            },
            "liquidity": {
                "score": self.liquidity_score,
                "state": self.liquidity_state
            },
            "trade_flow": {
                "buy_volume": round(self.buy_volume, 4),
                "sell_volume": round(self.sell_volume, 4),
                "pressure": self.trade_pressure,
                "vwap": round(self.vwap, 2)
            },
            "micro": {
                "state": self.state,
                "confidence": self.confidence
            },
            "sweep": self.sweep_detected
        }
