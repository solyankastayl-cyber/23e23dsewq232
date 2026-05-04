"""
PHASE 8 - Stop Cluster Detector
=================================
Identifies probable stop-loss cluster zones.

Finds stops:
- Above equal highs (short stops)
- Below equal lows (long stops)
- Above range highs
- Below range lows
- Around swing levels
"""

import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .liquidity_types import (
    StopCluster, StopClusterSide, DEFAULT_CONFIG
)


class StopClusterDetector:
    """
    Detects probable stop-loss cluster locations.
    
    Uses price structure analysis to identify where traders
    likely have their stops placed.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG
        self.cluster_range_pct = self.config.get("stop_cluster_range", 0.005)
    
    def detect_clusters(
        self,
        price_history: List[float],
        current_price: float,
        high_history: List[float] = None,
        low_history: List[float] = None,
        symbol: str = "BTCUSDT"
    ) -> List[StopCluster]:
        """
        Detect stop clusters from price history.
        
        Args:
            price_history: List of close prices
            current_price: Current market price
            high_history: List of high prices (optional)
            low_history: List of low prices (optional)
            symbol: Trading symbol
        
        Returns:
            List of detected stop clusters
        """
        clusters = []
        now = datetime.now(timezone.utc)
        
        if len(price_history) < 20:
            return clusters
        
        # Use highs/lows or derive from prices
        highs = high_history if high_history else [p * 1.002 for p in price_history]
        lows = low_history if low_history else [p * 0.998 for p in price_history]
        
        # Detect equal highs (short stops above)
        equal_high_clusters = self._detect_equal_highs(
            highs, current_price, symbol, now
        )
        clusters.extend(equal_high_clusters)
        
        # Detect equal lows (long stops below)
        equal_low_clusters = self._detect_equal_lows(
            lows, current_price, symbol, now
        )
        clusters.extend(equal_low_clusters)
        
        # Detect range boundaries
        range_clusters = self._detect_range_stops(
            highs, lows, current_price, symbol, now
        )
        clusters.extend(range_clusters)
        
        # Detect swing level stops
        swing_clusters = self._detect_swing_stops(
            price_history, highs, lows, current_price, symbol, now
        )
        clusters.extend(swing_clusters)
        
        # Sort by distance from current price
        clusters.sort(key=lambda c: abs(c.price_level - current_price))
        
        return clusters
    
    def _detect_equal_highs(
        self,
        highs: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[StopCluster]:
        """Detect clusters of equal highs (likely short stops above)."""
        clusters = []
        
        if len(highs) < 10:
            return clusters
        
        # Find recent highs that are close together
        recent_highs = highs[-50:]
        tolerance = current_price * 0.002  # 0.2% tolerance
        
        # Group similar highs
        high_groups = self._group_similar_levels(recent_highs, tolerance)
        
        for group in high_groups:
            if len(group) >= 2:  # At least 2 touches
                avg_level = sum(group) / len(group)
                
                if avg_level > current_price:  # Only above current price
                    # Stop cluster just above the equal highs
                    stop_level = avg_level * 1.001
                    
                    # Calculate cluster strength based on touches
                    strength = min(1.0, len(group) / 5) * 0.8
                    
                    cluster = StopCluster(
                        symbol=symbol,
                        price_level=stop_level,
                        price_range_low=avg_level,
                        price_range_high=stop_level * 1.003,
                        side=StopClusterSide.SHORT_STOPS,
                        cluster_strength=strength,
                        confidence=min(0.9, 0.5 + len(group) * 0.1),
                        trigger_type="equal_highs",
                        distance_from_current=stop_level - current_price,
                        distance_pct=(stop_level - current_price) / current_price,
                        cascade_risk=strength * 0.6,
                        detected_at=timestamp
                    )
                    clusters.append(cluster)
        
        return clusters[:3]  # Top 3
    
    def _detect_equal_lows(
        self,
        lows: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[StopCluster]:
        """Detect clusters of equal lows (likely long stops below)."""
        clusters = []
        
        if len(lows) < 10:
            return clusters
        
        recent_lows = lows[-50:]
        tolerance = current_price * 0.002
        
        low_groups = self._group_similar_levels(recent_lows, tolerance)
        
        for group in low_groups:
            if len(group) >= 2:
                avg_level = sum(group) / len(group)
                
                if avg_level < current_price:  # Only below current price
                    stop_level = avg_level * 0.999
                    
                    strength = min(1.0, len(group) / 5) * 0.8
                    
                    cluster = StopCluster(
                        symbol=symbol,
                        price_level=stop_level,
                        price_range_low=stop_level * 0.997,
                        price_range_high=avg_level,
                        side=StopClusterSide.LONG_STOPS,
                        cluster_strength=strength,
                        confidence=min(0.9, 0.5 + len(group) * 0.1),
                        trigger_type="equal_lows",
                        distance_from_current=current_price - stop_level,
                        distance_pct=(current_price - stop_level) / current_price,
                        cascade_risk=strength * 0.6,
                        detected_at=timestamp
                    )
                    clusters.append(cluster)
        
        return clusters[:3]
    
    def _detect_range_stops(
        self,
        highs: List[float],
        lows: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[StopCluster]:
        """Detect stops at range boundaries."""
        clusters = []
        
        if len(highs) < 20:
            return clusters
        
        # Find recent range
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        
        # Stops above range high (shorts)
        if recent_high > current_price:
            stop_level = recent_high * 1.002
            
            clusters.append(StopCluster(
                symbol=symbol,
                price_level=stop_level,
                price_range_low=recent_high,
                price_range_high=stop_level * 1.003,
                side=StopClusterSide.SHORT_STOPS,
                cluster_strength=0.7,
                confidence=0.7,
                trigger_type="range_high",
                distance_from_current=stop_level - current_price,
                distance_pct=(stop_level - current_price) / current_price,
                cascade_risk=0.5,
                detected_at=timestamp
            ))
        
        # Stops below range low (longs)
        if recent_low < current_price:
            stop_level = recent_low * 0.998
            
            clusters.append(StopCluster(
                symbol=symbol,
                price_level=stop_level,
                price_range_low=stop_level * 0.997,
                price_range_high=recent_low,
                side=StopClusterSide.LONG_STOPS,
                cluster_strength=0.7,
                confidence=0.7,
                trigger_type="range_low",
                distance_from_current=current_price - stop_level,
                distance_pct=(current_price - stop_level) / current_price,
                cascade_risk=0.5,
                detected_at=timestamp
            ))
        
        return clusters
    
    def _detect_swing_stops(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[StopCluster]:
        """Detect stops around swing highs/lows."""
        clusters = []
        
        if len(prices) < 30:
            return clusters
        
        # Find swing highs (local maxima)
        swing_highs = self._find_swing_points(highs, "high")
        
        # Find swing lows (local minima)
        swing_lows = self._find_swing_points(lows, "low")
        
        # Create clusters for significant swings
        for swing_high in swing_highs[:3]:  # Top 3 swing highs
            if swing_high > current_price:
                stop_level = swing_high * 1.002
                
                clusters.append(StopCluster(
                    symbol=symbol,
                    price_level=stop_level,
                    price_range_low=swing_high,
                    price_range_high=stop_level * 1.002,
                    side=StopClusterSide.SHORT_STOPS,
                    cluster_strength=0.6,
                    confidence=0.65,
                    trigger_type="swing_high",
                    distance_from_current=stop_level - current_price,
                    distance_pct=(stop_level - current_price) / current_price,
                    cascade_risk=0.4,
                    detected_at=timestamp
                ))
        
        for swing_low in swing_lows[:3]:
            if swing_low < current_price:
                stop_level = swing_low * 0.998
                
                clusters.append(StopCluster(
                    symbol=symbol,
                    price_level=stop_level,
                    price_range_low=stop_level * 0.998,
                    price_range_high=swing_low,
                    side=StopClusterSide.LONG_STOPS,
                    cluster_strength=0.6,
                    confidence=0.65,
                    trigger_type="swing_low",
                    distance_from_current=current_price - stop_level,
                    distance_pct=(current_price - stop_level) / current_price,
                    cascade_risk=0.4,
                    detected_at=timestamp
                ))
        
        return clusters
    
    def _group_similar_levels(
        self,
        levels: List[float],
        tolerance: float
    ) -> List[List[float]]:
        """Group similar price levels together."""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        groups = []
        current_group = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if level - current_group[-1] <= tolerance:
                current_group.append(level)
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [level]
        
        if len(current_group) >= 2:
            groups.append(current_group)
        
        # Sort by number of touches (most touches first)
        groups.sort(key=lambda g: len(g), reverse=True)
        
        return groups
    
    def _find_swing_points(
        self,
        prices: List[float],
        swing_type: str,  # "high" or "low"
        lookback: int = 5
    ) -> List[float]:
        """Find swing highs or lows."""
        swings = []
        
        for i in range(lookback, len(prices) - lookback):
            if swing_type == "high":
                is_swing = all(prices[i] >= prices[i-j] for j in range(1, lookback + 1))
                is_swing = is_swing and all(prices[i] >= prices[i+j] for j in range(1, lookback + 1))
            else:
                is_swing = all(prices[i] <= prices[i-j] for j in range(1, lookback + 1))
                is_swing = is_swing and all(prices[i] <= prices[i+j] for j in range(1, lookback + 1))
            
            if is_swing:
                swings.append(prices[i])
        
        return swings
    
    def get_nearest_clusters(
        self,
        clusters: List[StopCluster],
        current_price: float,
        side: Optional[StopClusterSide] = None
    ) -> Dict:
        """Get nearest stop clusters."""
        if side:
            filtered = [c for c in clusters if c.side == side]
        else:
            filtered = clusters
        
        above = [c for c in filtered if c.price_level > current_price]
        below = [c for c in filtered if c.price_level < current_price]
        
        nearest_above = min(above, key=lambda c: c.price_level) if above else None
        nearest_below = max(below, key=lambda c: c.price_level) if below else None
        
        return {
            "nearest_above": nearest_above.to_dict() if nearest_above else None,
            "nearest_below": nearest_below.to_dict() if nearest_below else None,
            "total_above": len(above),
            "total_below": len(below),
            "highest_strength_above": max(
                (c.cluster_strength for c in above), default=0
            ),
            "highest_strength_below": max(
                (c.cluster_strength for c in below), default=0
            )
        }
    
    def get_cluster_summary(
        self,
        clusters: List[StopCluster],
        current_price: float
    ) -> Dict:
        """Get summary of detected clusters."""
        if not clusters:
            return {"total_clusters": 0}
        
        long_stops = [c for c in clusters if c.side == StopClusterSide.LONG_STOPS]
        short_stops = [c for c in clusters if c.side == StopClusterSide.SHORT_STOPS]
        
        by_trigger = {}
        for c in clusters:
            by_trigger[c.trigger_type] = by_trigger.get(c.trigger_type, 0) + 1
        
        return {
            "total_clusters": len(clusters),
            "long_stop_clusters": len(long_stops),
            "short_stop_clusters": len(short_stops),
            "by_trigger_type": by_trigger,
            "avg_cluster_strength": round(
                sum(c.cluster_strength for c in clusters) / len(clusters), 3
            ),
            "avg_confidence": round(
                sum(c.confidence for c in clusters) / len(clusters), 3
            ),
            "total_cascade_risk": round(
                sum(c.cascade_risk for c in clusters) / len(clusters), 3
            )
        }
