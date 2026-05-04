"""
PHASE 8 - Orderbook Depth Engine
==================================
Analyzes orderbook depth for liquidity intelligence.

Provides:
- Top of book analysis
- Cumulative depth profiles
- Bid/ask wall detection
- Thin zone identification
- Depth asymmetry measurement
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .liquidity_types import (
    DepthProfile, OrderbookLevel, LiquidityQuality,
    DepthZoneType, DEFAULT_CONFIG
)


class OrderbookDepthEngine:
    """
    Analyzes orderbook depth structure for liquidity assessment.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG
        self.depth_levels = self.config.get("depth_levels", 50)
        self.wall_threshold = self.config.get("wall_threshold", 2.0)
        self.thin_threshold = self.config.get("thin_zone_threshold", 0.2)
    
    def analyze_depth(
        self,
        bids: List[Tuple[float, float]],  # [(price, size), ...]
        asks: List[Tuple[float, float]],
        symbol: str = "BTCUSDT"
    ) -> DepthProfile:
        """
        Analyze orderbook depth and structure.
        
        Args:
            bids: List of (price, size) tuples, sorted by price descending
            asks: List of (price, size) tuples, sorted by price ascending
            symbol: Trading symbol
        
        Returns:
            DepthProfile with complete depth analysis
        """
        now = datetime.now(timezone.utc)
        
        if not bids or not asks:
            return self._empty_profile(symbol, now)
        
        # Calculate cumulative depths
        bid_levels = self._process_levels(bids, cumulative=True)
        ask_levels = self._process_levels(asks, cumulative=True)
        
        # Total depths
        bid_depth = sum(level.size for level in bid_levels)
        ask_depth = sum(level.size for level in ask_levels)
        
        # Depth ratio and imbalance
        total_depth = bid_depth + ask_depth
        depth_ratio = bid_depth / ask_depth if ask_depth > 0 else 1.0
        depth_imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0.0
        
        # Spread calculation
        best_bid = bid_levels[0].price if bid_levels else 0
        best_ask = ask_levels[0].price if ask_levels else 0
        spread = best_ask - best_bid
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0
        
        # Detect walls
        bid_walls = self._detect_walls(bid_levels, "bid")
        ask_walls = self._detect_walls(ask_levels, "ask")
        
        # Detect thin zones
        thin_zones = self._detect_thin_zones(bid_levels, ask_levels, mid_price)
        
        # Assess quality
        quality = self._assess_quality(
            bid_depth, ask_depth, spread_bps, thin_zones, bid_walls, ask_walls
        )
        
        # Calculate asymmetry
        asymmetry = self._calculate_asymmetry(bid_levels, ask_levels)
        
        return DepthProfile(
            symbol=symbol,
            timestamp=now,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            depth_ratio=depth_ratio,
            depth_imbalance=depth_imbalance,
            bid_levels=len(bid_levels),
            ask_levels=len(ask_levels),
            spread=spread,
            spread_bps=spread_bps,
            bid_walls=bid_walls,
            ask_walls=ask_walls,
            thin_zones=thin_zones,
            liquidity_quality=quality,
            depth_asymmetry=asymmetry
        )
    
    def _process_levels(
        self,
        levels: List[Tuple[float, float]],
        cumulative: bool = True
    ) -> List[OrderbookLevel]:
        """Process raw levels into OrderbookLevel objects."""
        processed = []
        cum_size = 0.0
        
        for price, size in levels[:self.depth_levels]:
            cum_size += size
            processed.append(OrderbookLevel(
                price=price,
                size=size,
                cumulative_size=cum_size if cumulative else 0.0
            ))
        
        return processed
    
    def _detect_walls(
        self,
        levels: List[OrderbookLevel],
        side: str
    ) -> List[OrderbookLevel]:
        """Detect large order walls."""
        if not levels:
            return []
        
        avg_size = sum(l.size for l in levels) / len(levels)
        threshold = avg_size * self.wall_threshold
        
        walls = [l for l in levels if l.size >= threshold]
        
        # Return top 5 walls
        walls.sort(key=lambda x: x.size, reverse=True)
        return walls[:5]
    
    def _detect_thin_zones(
        self,
        bids: List[OrderbookLevel],
        asks: List[OrderbookLevel],
        mid_price: float
    ) -> List[Dict]:
        """Detect thin liquidity zones (gaps)."""
        thin_zones = []
        
        if not bids or not asks:
            return thin_zones
        
        all_levels = bids + asks
        avg_size = sum(l.size for l in all_levels) / len(all_levels)
        threshold = avg_size * self.thin_threshold
        
        # Check bids for thin zones
        for i in range(len(bids) - 1):
            if bids[i].size < threshold and bids[i+1].size < threshold:
                price_gap = abs(bids[i].price - bids[i+1].price)
                if price_gap > mid_price * 0.001:  # > 0.1% gap
                    thin_zones.append({
                        "side": "bid",
                        "price_low": min(bids[i].price, bids[i+1].price),
                        "price_high": max(bids[i].price, bids[i+1].price),
                        "gap_size": price_gap,
                        "avg_liquidity": (bids[i].size + bids[i+1].size) / 2
                    })
        
        # Check asks for thin zones
        for i in range(len(asks) - 1):
            if asks[i].size < threshold and asks[i+1].size < threshold:
                price_gap = abs(asks[i].price - asks[i+1].price)
                if price_gap > mid_price * 0.001:
                    thin_zones.append({
                        "side": "ask",
                        "price_low": min(asks[i].price, asks[i+1].price),
                        "price_high": max(asks[i].price, asks[i+1].price),
                        "gap_size": price_gap,
                        "avg_liquidity": (asks[i].size + asks[i+1].size) / 2
                    })
        
        return thin_zones[:10]  # Top 10 thin zones
    
    def _assess_quality(
        self,
        bid_depth: float,
        ask_depth: float,
        spread_bps: float,
        thin_zones: List[Dict],
        bid_walls: List[OrderbookLevel],
        ask_walls: List[OrderbookLevel]
    ) -> LiquidityQuality:
        """Assess overall liquidity quality."""
        score = 100
        
        # Penalize wide spread
        if spread_bps > 50:
            score -= 30
        elif spread_bps > 20:
            score -= 15
        elif spread_bps > 10:
            score -= 5
        
        # Penalize thin zones
        score -= len(thin_zones) * 5
        
        # Penalize depth imbalance
        if bid_depth > 0 and ask_depth > 0:
            imbalance = abs(bid_depth - ask_depth) / (bid_depth + ask_depth)
            if imbalance > 0.5:
                score -= 20
            elif imbalance > 0.3:
                score -= 10
        
        # Reward walls (indicates depth)
        score += min(10, len(bid_walls) * 2 + len(ask_walls) * 2)
        
        # Classify
        if score >= 85:
            return LiquidityQuality.EXCELLENT
        elif score >= 70:
            return LiquidityQuality.GOOD
        elif score >= 50:
            return LiquidityQuality.MEDIUM
        elif score >= 30:
            return LiquidityQuality.POOR
        else:
            return LiquidityQuality.CRITICAL
    
    def _calculate_asymmetry(
        self,
        bids: List[OrderbookLevel],
        asks: List[OrderbookLevel]
    ) -> float:
        """Calculate depth asymmetry across price levels."""
        if not bids or not asks:
            return 0.0
        
        # Compare cumulative depth at different distances
        max_levels = min(len(bids), len(asks), 20)
        
        asymmetries = []
        for i in range(max_levels):
            bid_cum = bids[i].cumulative_size
            ask_cum = asks[i].cumulative_size
            total = bid_cum + ask_cum
            
            if total > 0:
                asym = (bid_cum - ask_cum) / total
                asymmetries.append(asym)
        
        return sum(asymmetries) / len(asymmetries) if asymmetries else 0.0
    
    def _empty_profile(self, symbol: str, timestamp: datetime) -> DepthProfile:
        """Return empty profile when no data."""
        return DepthProfile(
            symbol=symbol,
            timestamp=timestamp,
            bid_depth=0,
            ask_depth=0,
            depth_ratio=1.0,
            depth_imbalance=0.0,
            bid_levels=0,
            ask_levels=0,
            spread=0,
            spread_bps=0,
            liquidity_quality=LiquidityQuality.CRITICAL
        )
    
    def get_depth_at_price(
        self,
        levels: List[OrderbookLevel],
        target_price: float
    ) -> float:
        """Get cumulative depth at a target price."""
        for level in levels:
            if level.price <= target_price:
                return level.cumulative_size
        return 0.0
    
    def estimate_slippage(
        self,
        profile: DepthProfile,
        order_size: float,
        side: str  # "buy" or "sell"
    ) -> Dict:
        """Estimate slippage for a given order size."""
        if side == "buy":
            # Need to consume asks
            depth = profile.ask_depth
        else:
            # Need to consume bids
            depth = profile.bid_depth
        
        if depth == 0:
            return {"slippage_pct": float('inf'), "executable": False}
        
        # Simple linear model
        fill_ratio = order_size / depth
        
        if fill_ratio > 1:
            return {
                "slippage_pct": 999,
                "fill_ratio": fill_ratio,
                "executable": False,
                "reason": "Order exceeds available depth"
            }
        
        # Estimate slippage (increases quadratically with fill ratio)
        base_slippage = profile.spread_bps / 100  # Convert to percentage
        impact_slippage = fill_ratio ** 2 * 0.5  # Market impact
        
        total_slippage = base_slippage + impact_slippage
        
        return {
            "slippage_pct": round(total_slippage, 4),
            "fill_ratio": round(fill_ratio, 4),
            "executable": True,
            "base_slippage": round(base_slippage, 4),
            "impact_slippage": round(impact_slippage, 4)
        }


def generate_mock_orderbook(
    symbol: str = "BTCUSDT",
    mid_price: float = 64000.0,
    depth_levels: int = 50
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """Generate mock orderbook data for testing."""
    bids = []
    asks = []
    
    # Generate bids (below mid price)
    for i in range(depth_levels):
        price = mid_price * (1 - 0.0001 * (i + 1))  # 0.01% per level
        # Size varies with some randomness and occasional walls
        base_size = random.uniform(0.5, 3.0)
        if random.random() < 0.1:  # 10% chance of wall
            base_size *= random.uniform(3, 8)
        bids.append((price, base_size))
    
    # Generate asks (above mid price)
    for i in range(depth_levels):
        price = mid_price * (1 + 0.0001 * (i + 1))
        base_size = random.uniform(0.5, 3.0)
        if random.random() < 0.1:
            base_size *= random.uniform(3, 8)
        asks.append((price, base_size))
    
    return bids, asks
