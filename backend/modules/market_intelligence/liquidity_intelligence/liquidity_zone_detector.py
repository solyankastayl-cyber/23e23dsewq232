"""
PHASE 8 - Liquidity Zone Detector
====================================
Identifies zones of high/low liquidity and price magnets.

Finds:
- High liquidity zones (attract price)
- Thin liquidity zones (easy breakouts)
- Sweep-prone levels
- Magnet zones (strong attraction)
"""

import random
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .liquidity_types import (
    LiquidityZone, LiquidityZoneType, SweepDirection,
    DepthProfile, OrderbookLevel, DEFAULT_CONFIG
)


class LiquidityZoneDetector:
    """
    Detects and classifies liquidity zones in the orderbook.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG
        self.min_zone_size = 0.002  # 0.2% minimum zone range
        self.max_zone_size = 0.02   # 2% maximum zone range
    
    def detect_zones(
        self,
        depth_profile: DepthProfile,
        price_history: List[float] = None,
        current_price: float = None
    ) -> List[LiquidityZone]:
        """
        Detect all liquidity zones from orderbook depth.
        
        Args:
            depth_profile: Current orderbook depth profile
            price_history: Recent price history for context
            current_price: Current market price
        
        Returns:
            List of detected liquidity zones
        """
        zones = []
        now = datetime.now(timezone.utc)
        
        if current_price is None and price_history:
            current_price = price_history[-1]
        elif current_price is None:
            current_price = 64000.0  # Default for testing
        
        # Detect high liquidity zones from walls
        wall_zones = self._detect_wall_zones(depth_profile, current_price, now)
        zones.extend(wall_zones)
        
        # Detect thin liquidity zones
        thin_zones = self._detect_thin_zones(depth_profile, current_price, now)
        zones.extend(thin_zones)
        
        # Detect magnet zones (where price tends to go)
        if price_history:
            magnet_zones = self._detect_magnet_zones(price_history, current_price, now)
            zones.extend(magnet_zones)
        
        # Detect sweep-prone zones
        sweep_zones = self._detect_sweep_prone_zones(depth_profile, current_price, now)
        zones.extend(sweep_zones)
        
        # Sort by distance from current price
        zones.sort(key=lambda z: abs(z.mid_price - current_price))
        
        return zones
    
    def _detect_wall_zones(
        self,
        profile: DepthProfile,
        current_price: float,
        timestamp: datetime
    ) -> List[LiquidityZone]:
        """Detect high liquidity zones around order walls."""
        zones = []
        
        # Process bid walls
        for wall in profile.bid_walls:
            zone_range = current_price * 0.003  # 0.3% zone
            zones.append(LiquidityZone(
                symbol=profile.symbol,
                zone_type=LiquidityZoneType.HIGH_LIQUIDITY,
                price_low=wall.price - zone_range / 2,
                price_high=wall.price + zone_range / 2,
                mid_price=wall.price,
                liquidity_score=min(1.0, wall.size / 10),  # Normalize
                attraction_strength=min(0.9, wall.size / 15),
                volume_concentration=wall.size,
                detected_at=timestamp
            ))
        
        # Process ask walls
        for wall in profile.ask_walls:
            zone_range = current_price * 0.003
            zones.append(LiquidityZone(
                symbol=profile.symbol,
                zone_type=LiquidityZoneType.HIGH_LIQUIDITY,
                price_low=wall.price - zone_range / 2,
                price_high=wall.price + zone_range / 2,
                mid_price=wall.price,
                liquidity_score=min(1.0, wall.size / 10),
                attraction_strength=min(0.9, wall.size / 15),
                volume_concentration=wall.size,
                detected_at=timestamp
            ))
        
        return zones
    
    def _detect_thin_zones(
        self,
        profile: DepthProfile,
        current_price: float,
        timestamp: datetime
    ) -> List[LiquidityZone]:
        """Detect low liquidity zones from orderbook gaps."""
        zones = []
        
        for thin_zone in profile.thin_zones:
            # Thin zones are easy to break through
            mid_price = (thin_zone["price_low"] + thin_zone["price_high"]) / 2
            
            # Determine sweep direction
            if mid_price > current_price:
                sweep_dir = SweepDirection.UPSIDE
            else:
                sweep_dir = SweepDirection.DOWNSIDE
            
            zones.append(LiquidityZone(
                symbol=profile.symbol,
                zone_type=LiquidityZoneType.LOW_LIQUIDITY,
                price_low=thin_zone["price_low"],
                price_high=thin_zone["price_high"],
                mid_price=mid_price,
                liquidity_score=0.2,  # Low by definition
                attraction_strength=0.3,  # Weak attraction
                volume_concentration=thin_zone.get("avg_liquidity", 0.5),
                sweep_probability=0.7,  # High probability of breaking through
                sweep_direction=sweep_dir,
                detected_at=timestamp
            ))
        
        return zones
    
    def _detect_magnet_zones(
        self,
        price_history: List[float],
        current_price: float,
        timestamp: datetime
    ) -> List[LiquidityZone]:
        """Detect zones that attract price (based on historical levels)."""
        zones = []
        
        if len(price_history) < 20:
            return zones
        
        # Find recent highs and lows as potential magnets
        recent_high = max(price_history[-20:])
        recent_low = min(price_history[-20:])
        
        # Previous session highs/lows
        if len(price_history) >= 50:
            prev_session_high = max(price_history[-50:-20])
            prev_session_low = min(price_history[-50:-20])
        else:
            prev_session_high = recent_high
            prev_session_low = recent_low
        
        # Create magnet zones at key levels
        key_levels = [
            (recent_high, "recent_high", 0.8),
            (recent_low, "recent_low", 0.8),
            (prev_session_high, "prev_high", 0.6),
            (prev_session_low, "prev_low", 0.6),
        ]
        
        for level, level_type, strength in key_levels:
            zone_range = current_price * 0.002
            
            if level > current_price:
                sweep_dir = SweepDirection.UPSIDE
            else:
                sweep_dir = SweepDirection.DOWNSIDE
            
            zones.append(LiquidityZone(
                symbol="BTCUSDT",  # Will be set by caller
                zone_type=LiquidityZoneType.MAGNET_ZONE,
                price_low=level - zone_range / 2,
                price_high=level + zone_range / 2,
                mid_price=level,
                liquidity_score=0.7,
                attraction_strength=strength,
                volume_concentration=1.0,
                sweep_probability=0.5,
                sweep_direction=sweep_dir,
                detected_at=timestamp
            ))
        
        return zones
    
    def _detect_sweep_prone_zones(
        self,
        profile: DepthProfile,
        current_price: float,
        timestamp: datetime
    ) -> List[LiquidityZone]:
        """Detect zones likely to be swept for liquidity."""
        zones = []
        
        # Zones with thin liquidity beyond walls are sweep-prone
        # Check if there's thin liquidity above ask walls
        if profile.ask_walls and profile.thin_zones:
            for wall in profile.ask_walls[:2]:  # Top 2 walls
                for thin in profile.thin_zones:
                    if thin["side"] == "ask" and thin["price_low"] > wall.price:
                        # Sweep zone: go through wall, then thin area
                        zones.append(LiquidityZone(
                            symbol=profile.symbol,
                            zone_type=LiquidityZoneType.SWEEP_PRONE,
                            price_low=wall.price,
                            price_high=thin["price_high"],
                            mid_price=(wall.price + thin["price_high"]) / 2,
                            liquidity_score=0.4,
                            attraction_strength=0.6,
                            volume_concentration=wall.size / 2,
                            sweep_probability=0.65,
                            sweep_direction=SweepDirection.UPSIDE,
                            detected_at=timestamp
                        ))
                        break
        
        # Same for bid side
        if profile.bid_walls and profile.thin_zones:
            for wall in profile.bid_walls[:2]:
                for thin in profile.thin_zones:
                    if thin["side"] == "bid" and thin["price_high"] < wall.price:
                        zones.append(LiquidityZone(
                            symbol=profile.symbol,
                            zone_type=LiquidityZoneType.SWEEP_PRONE,
                            price_low=thin["price_low"],
                            price_high=wall.price,
                            mid_price=(thin["price_low"] + wall.price) / 2,
                            liquidity_score=0.4,
                            attraction_strength=0.6,
                            volume_concentration=wall.size / 2,
                            sweep_probability=0.65,
                            sweep_direction=SweepDirection.DOWNSIDE,
                            detected_at=timestamp
                        ))
                        break
        
        return zones
    
    def get_nearest_zones(
        self,
        zones: List[LiquidityZone],
        current_price: float,
        direction: str = "both",  # "above", "below", "both"
        limit: int = 3
    ) -> List[LiquidityZone]:
        """Get nearest liquidity zones in specified direction."""
        if direction == "above":
            filtered = [z for z in zones if z.mid_price > current_price]
        elif direction == "below":
            filtered = [z for z in zones if z.mid_price < current_price]
        else:
            filtered = zones
        
        # Sort by distance
        filtered.sort(key=lambda z: abs(z.mid_price - current_price))
        
        return filtered[:limit]
    
    def get_zone_summary(
        self,
        zones: List[LiquidityZone],
        current_price: float
    ) -> Dict:
        """Get summary of detected zones."""
        if not zones:
            return {"total_zones": 0}
        
        zone_counts = {}
        for zone in zones:
            zone_type = zone.zone_type.value
            zone_counts[zone_type] = zone_counts.get(zone_type, 0) + 1
        
        above = [z for z in zones if z.mid_price > current_price]
        below = [z for z in zones if z.mid_price < current_price]
        
        nearest_above = min(above, key=lambda z: z.mid_price) if above else None
        nearest_below = max(below, key=lambda z: z.mid_price) if below else None
        
        return {
            "total_zones": len(zones),
            "zones_above": len(above),
            "zones_below": len(below),
            "by_type": zone_counts,
            "nearest_above": nearest_above.to_dict() if nearest_above else None,
            "nearest_below": nearest_below.to_dict() if nearest_below else None,
            "avg_liquidity_score": round(
                sum(z.liquidity_score for z in zones) / len(zones), 3
            ),
            "avg_sweep_probability": round(
                sum(z.sweep_probability for z in zones if z.sweep_probability > 0) / 
                max(1, len([z for z in zones if z.sweep_probability > 0])), 3
            )
        }
