"""
PHASE 9 - Micro-Imbalance Engine
=================================
Detects short-lived orderbook imbalances.

Identifies:
- Short-lived bid/ask dominance
- Sudden liquidity vacuum
- Top-of-book skew
- Local orderbook asymmetry
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from .microstructure_types import (
    MicroImbalance, ImbalanceType, DEFAULT_MICROSTRUCTURE_CONFIG
)


class MicroImbalanceEngine:
    """
    Micro-Imbalance Detection Engine
    
    Detects short-lived imbalances in the orderbook that
    may indicate imminent price movements.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_MICROSTRUCTURE_CONFIG
        self.history: List[MicroImbalance] = []
        self.max_history = 100
        self.imbalance_start_time: Optional[datetime] = None
        self.current_imbalance_type: Optional[ImbalanceType] = None
    
    def detect_imbalance(
        self,
        bid_levels: List[Tuple[float, float]],  # [(price, size), ...]
        ask_levels: List[Tuple[float, float]],
        symbol: str = "BTCUSDT",
        recent_volatility: float = 0.0
    ) -> MicroImbalance:
        """
        Detect micro-imbalances in the orderbook.
        
        Args:
            bid_levels: List of (price, size) tuples for bids
            ask_levels: List of (price, size) tuples for asks
            symbol: Trading symbol
            recent_volatility: Recent price volatility
            
        Returns:
            MicroImbalance analysis
        """
        now = datetime.now(timezone.utc)
        
        if not bid_levels or not ask_levels:
            return self._empty_imbalance(symbol, now)
        
        # Top of book analysis
        top_bid_price, top_bid_size = bid_levels[0]
        top_ask_price, top_ask_size = ask_levels[0]
        
        # Calculate top book skew: (bid - ask) / (bid + ask)
        total_top = top_bid_size + top_ask_size
        top_book_skew = (top_bid_size - top_ask_size) / total_top if total_top > 0 else 0
        
        # Calculate depth imbalances at different levels
        depth_3 = self._calculate_depth_imbalance(bid_levels[:3], ask_levels[:3])
        depth_5 = self._calculate_depth_imbalance(bid_levels[:5], ask_levels[:5])
        depth_10 = self._calculate_depth_imbalance(bid_levels[:10], ask_levels[:10])
        
        # Weighted imbalance score (top levels matter more)
        micro_imbalance_score = depth_3 * 0.5 + depth_5 * 0.3 + depth_10 * 0.2
        
        # Determine dominant side
        if micro_imbalance_score > 0.1:
            dominant_side = "BID"
        elif micro_imbalance_score < -0.1:
            dominant_side = "ASK"
        else:
            dominant_side = "NEUTRAL"
        
        # Detect vacuum (very thin levels on one side)
        vacuum_risk = self._detect_vacuum(bid_levels, ask_levels)
        
        # Determine imbalance type
        imbalance_type = self._determine_imbalance_type(
            micro_imbalance_score, top_book_skew, vacuum_risk
        )
        
        # Calculate imbalance strength
        imbalance_strength = abs(micro_imbalance_score)
        
        # Track imbalance duration
        imbalance_duration_ms = self._track_duration(imbalance_type, now)
        
        imbalance = MicroImbalance(
            symbol=symbol,
            timestamp=now,
            micro_imbalance_score=micro_imbalance_score,
            imbalance_type=imbalance_type,
            dominant_micro_side=dominant_side,
            vacuum_risk=vacuum_risk,
            imbalance_duration_ms=imbalance_duration_ms,
            imbalance_strength=imbalance_strength,
            top_bid_size=top_bid_size,
            top_ask_size=top_ask_size,
            top_book_skew=top_book_skew,
            short_term_volatility=recent_volatility
        )
        
        # Save to history
        self._add_to_history(imbalance)
        
        return imbalance
    
    def _calculate_depth_imbalance(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]]
    ) -> float:
        """Calculate imbalance for given depth levels."""
        bid_total = sum(size for _, size in bids) if bids else 0
        ask_total = sum(size for _, size in asks) if asks else 0
        total = bid_total + ask_total
        
        if total == 0:
            return 0
        
        return (bid_total - ask_total) / total
    
    def _detect_vacuum(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]]
    ) -> float:
        """Detect liquidity vacuum (thin levels on one side)."""
        threshold = self.config["vacuum_threshold"]
        
        # Check top 5 levels
        bid_sizes = [size for _, size in bids[:5]]
        ask_sizes = [size for _, size in asks[:5]]
        
        avg_bid = sum(bid_sizes) / len(bid_sizes) if bid_sizes else 0
        avg_ask = sum(ask_sizes) / len(ask_sizes) if ask_sizes else 0
        
        # Find minimum relative sizes
        min_bid_ratio = min(bid_sizes) / avg_bid if avg_bid > 0 else 1
        min_ask_ratio = min(ask_sizes) / avg_ask if avg_ask > 0 else 1
        
        # Vacuum risk is higher when either side has very thin levels
        min_ratio = min(min_bid_ratio, min_ask_ratio)
        
        if min_ratio < threshold:
            return 1 - (min_ratio / threshold)
        
        return 0
    
    def _determine_imbalance_type(
        self,
        score: float,
        skew: float,
        vacuum: float
    ) -> ImbalanceType:
        """Determine the type of imbalance."""
        threshold = self.config["imbalance_threshold"]
        
        # Vacuum takes priority
        if vacuum > 0.6:
            return ImbalanceType.VACUUM
        
        # Check for skew
        if abs(skew) > 0.4:
            return ImbalanceType.SKEW
        
        # Check for dominance
        if score > threshold:
            return ImbalanceType.BID_DOMINANT
        elif score < -threshold:
            return ImbalanceType.ASK_DOMINANT
        
        return ImbalanceType.BALANCED
    
    def _track_duration(self, imbalance_type: ImbalanceType, now: datetime) -> int:
        """Track how long current imbalance has lasted."""
        if imbalance_type == ImbalanceType.BALANCED:
            self.imbalance_start_time = None
            self.current_imbalance_type = None
            return 0
        
        if self.current_imbalance_type != imbalance_type:
            self.imbalance_start_time = now
            self.current_imbalance_type = imbalance_type
            return 0
        
        if self.imbalance_start_time:
            duration = now - self.imbalance_start_time
            return int(duration.total_seconds() * 1000)
        
        return 0
    
    def _empty_imbalance(self, symbol: str, timestamp: datetime) -> MicroImbalance:
        """Return empty imbalance when no data."""
        return MicroImbalance(
            symbol=symbol,
            timestamp=timestamp,
            micro_imbalance_score=0,
            imbalance_type=ImbalanceType.BALANCED,
            dominant_micro_side="NEUTRAL",
            vacuum_risk=0,
            imbalance_duration_ms=0,
            imbalance_strength=0,
            top_bid_size=0,
            top_ask_size=0,
            top_book_skew=0,
            short_term_volatility=0
        )
    
    def _add_to_history(self, imbalance: MicroImbalance):
        """Add imbalance to history."""
        self.history.append(imbalance)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_imbalance_summary(self, periods: int = 10) -> Dict:
        """Get summary of recent imbalances."""
        if len(self.history) < periods:
            return {"summary": "INSUFFICIENT_DATA", "periods": len(self.history)}
        
        recent = self.history[-periods:]
        
        # Calculate averages
        avg_score = sum(i.micro_imbalance_score for i in recent) / len(recent)
        avg_vacuum = sum(i.vacuum_risk for i in recent) / len(recent)
        
        # Count types
        type_counts = {}
        for imb in recent:
            t = imb.imbalance_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        dominant_type = max(type_counts, key=type_counts.get) if type_counts else "BALANCED"
        
        return {
            "avg_imbalance_score": round(avg_score, 4),
            "avg_vacuum_risk": round(avg_vacuum, 3),
            "dominant_type": dominant_type,
            "type_distribution": type_counts,
            "current_imbalance": recent[-1].imbalance_type.value,
            "periods": periods
        }


def generate_mock_orderbook_levels(
    current_price: float = 64000.0,
    levels: int = 20,
    bias: str = "NEUTRAL"
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Generate mock orderbook levels for testing.
    
    Returns:
        Tuple of (bid_levels, ask_levels)
    """
    import random
    
    spread = current_price * 0.0001  # 1 bps spread
    bid_price = current_price - spread / 2
    ask_price = current_price + spread / 2
    
    # Size multipliers for bias
    bid_mult = 1.0
    ask_mult = 1.0
    if bias == "BUY":
        bid_mult = 1.5
    elif bias == "SELL":
        ask_mult = 1.5
    
    bids = []
    asks = []
    
    tick = current_price * 0.0001  # Price increment
    
    for i in range(levels):
        bid_p = bid_price - i * tick
        ask_p = ask_price + i * tick
        
        # Base size with some randomness
        base_size = abs(random.gauss(1.0, 0.3))
        
        # Occasional large orders
        if random.random() < 0.1:
            base_size *= random.uniform(3, 8)
        
        bids.append((bid_p, base_size * bid_mult))
        asks.append((ask_p, base_size * ask_mult))
    
    return bids, asks
