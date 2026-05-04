"""
PHASE 8 - Liquidation Zone Detector
=====================================
Estimates zones where leveraged position liquidations may occur.

Detects:
- Trapped longs (potential long liquidations below)
- Trapped shorts (potential short liquidations above)
- Cascade risk assessment
- Leverage density zones
"""

import random
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .liquidity_types import (
    LiquidationZone, DEFAULT_CONFIG
)


class LiquidationZoneDetector:
    """
    Estimates liquidation zones based on price structure and leverage assumptions.
    
    This is a rule-based approximation since actual liquidation data
    requires exchange-specific feeds.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG
        
        # Common leverage levels to consider
        self.leverage_levels = [5, 10, 20, 25, 50, 100]
        
        # Liquidation buffer (exchange-dependent)
        self.liquidation_buffer = 0.005  # 0.5% buffer before liquidation
    
    def detect_zones(
        self,
        price_history: List[float],
        current_price: float,
        volume_profile: Dict = None,
        symbol: str = "BTCUSDT"
    ) -> List[LiquidationZone]:
        """
        Detect potential liquidation zones.
        
        Args:
            price_history: Recent price history
            current_price: Current market price
            volume_profile: Volume at price levels (optional)
            symbol: Trading symbol
        
        Returns:
            List of estimated liquidation zones
        """
        zones = []
        now = datetime.now(timezone.utc)
        
        if len(price_history) < 20:
            return zones
        
        # Detect trapped longs (entered at higher prices)
        long_zones = self._detect_long_liquidations(
            price_history, current_price, symbol, now
        )
        zones.extend(long_zones)
        
        # Detect trapped shorts (entered at lower prices)
        short_zones = self._detect_short_liquidations(
            price_history, current_price, symbol, now
        )
        zones.extend(short_zones)
        
        # Estimate high leverage zones
        leverage_zones = self._detect_leverage_zones(
            price_history, current_price, symbol, now
        )
        zones.extend(leverage_zones)
        
        # Sort by distance from current price
        zones.sort(key=lambda z: abs(z.price_level - current_price))
        
        return zones
    
    def _detect_long_liquidations(
        self,
        prices: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[LiquidationZone]:
        """
        Detect zones where trapped longs might get liquidated.
        
        Longs that entered at higher prices are underwater and
        will be liquidated if price drops further.
        """
        zones = []
        
        # Find recent local highs (where longs likely entered)
        recent_highs = []
        for i in range(2, min(50, len(prices) - 2)):
            if prices[-(i)] > prices[-(i-1)] and prices[-(i)] > prices[-(i+1)]:
                if prices[-(i)] > current_price:  # Above current = underwater longs
                    recent_highs.append(prices[-(i)])
        
        # For each entry point, calculate liquidation levels
        for entry_price in recent_highs[:5]:  # Top 5 entry points
            if entry_price <= current_price:
                continue
            
            # Calculate liquidation levels for different leverages
            for leverage in [10, 20, 25]:
                # Liquidation price = Entry * (1 - 1/leverage - buffer)
                liq_price = entry_price * (1 - 1/leverage - self.liquidation_buffer)
                
                if liq_price < current_price and liq_price > current_price * 0.9:
                    # Estimate volume based on how recent and how much above current
                    recency_factor = 1.0  # Would be calculated from actual data
                    distance_factor = (entry_price - current_price) / current_price
                    
                    estimated_volume = distance_factor * 100 * recency_factor
                    
                    # Cascade risk higher for high leverage
                    cascade_risk = min(0.9, leverage / 50)
                    
                    zones.append(LiquidationZone(
                        symbol=symbol,
                        price_level=liq_price,
                        price_range_low=liq_price * 0.998,
                        price_range_high=liq_price * 1.002,
                        position_type="LONG",
                        estimated_volume=estimated_volume,
                        cascade_risk=cascade_risk,
                        leverage_density=leverage / 100,
                        distance_from_current=current_price - liq_price,
                        distance_pct=(current_price - liq_price) / current_price,
                        detected_at=timestamp
                    ))
        
        # Deduplicate similar zones
        return self._deduplicate_zones(zones)[:5]
    
    def _detect_short_liquidations(
        self,
        prices: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[LiquidationZone]:
        """
        Detect zones where trapped shorts might get liquidated.
        
        Shorts that entered at lower prices are underwater and
        will be liquidated if price rises further.
        """
        zones = []
        
        # Find recent local lows (where shorts likely entered)
        recent_lows = []
        for i in range(2, min(50, len(prices) - 2)):
            if prices[-(i)] < prices[-(i-1)] and prices[-(i)] < prices[-(i+1)]:
                if prices[-(i)] < current_price:  # Below current = underwater shorts
                    recent_lows.append(prices[-(i)])
        
        for entry_price in recent_lows[:5]:
            if entry_price >= current_price:
                continue
            
            for leverage in [10, 20, 25]:
                # Liquidation price for shorts = Entry * (1 + 1/leverage + buffer)
                liq_price = entry_price * (1 + 1/leverage + self.liquidation_buffer)
                
                if liq_price > current_price and liq_price < current_price * 1.1:
                    recency_factor = 1.0
                    distance_factor = (current_price - entry_price) / current_price
                    
                    estimated_volume = distance_factor * 100 * recency_factor
                    cascade_risk = min(0.9, leverage / 50)
                    
                    zones.append(LiquidationZone(
                        symbol=symbol,
                        price_level=liq_price,
                        price_range_low=liq_price * 0.998,
                        price_range_high=liq_price * 1.002,
                        position_type="SHORT",
                        estimated_volume=estimated_volume,
                        cascade_risk=cascade_risk,
                        leverage_density=leverage / 100,
                        distance_from_current=liq_price - current_price,
                        distance_pct=(liq_price - current_price) / current_price,
                        detected_at=timestamp
                    ))
        
        return self._deduplicate_zones(zones)[:5]
    
    def _detect_leverage_zones(
        self,
        prices: List[float],
        current_price: float,
        symbol: str,
        timestamp: datetime
    ) -> List[LiquidationZone]:
        """
        Detect high leverage density zones.
        
        These are typically at round numbers and psychological levels.
        """
        zones = []
        
        # Round number levels (high leverage concentration)
        round_levels = self._get_round_number_levels(current_price)
        
        for level, is_above in round_levels:
            distance = abs(level - current_price)
            distance_pct = distance / current_price
            
            if distance_pct > 0.1:  # Skip if too far
                continue
            
            if is_above:
                position_type = "SHORT"
            else:
                position_type = "LONG"
            
            # Higher leverage density at closer levels
            leverage_density = max(0.2, 1 - distance_pct * 5)
            
            zones.append(LiquidationZone(
                symbol=symbol,
                price_level=level,
                price_range_low=level * 0.998,
                price_range_high=level * 1.002,
                position_type=position_type,
                estimated_volume=leverage_density * 50,
                cascade_risk=leverage_density * 0.5,
                leverage_density=leverage_density,
                distance_from_current=distance,
                distance_pct=distance_pct,
                detected_at=timestamp
            ))
        
        return zones[:4]
    
    def _get_round_number_levels(
        self,
        current_price: float
    ) -> List[tuple]:
        """Get round number levels near current price."""
        levels = []
        
        # Determine step based on price magnitude
        if current_price > 10000:
            steps = [1000, 500, 250]
        elif current_price > 1000:
            steps = [100, 50, 25]
        else:
            steps = [10, 5, 1]
        
        for step in steps:
            # Nearest round above
            round_above = ((current_price // step) + 1) * step
            levels.append((round_above, True))
            
            # Nearest round below
            round_below = (current_price // step) * step
            levels.append((round_below, False))
        
        # Remove duplicates and sort by distance
        seen = set()
        unique = []
        for level, is_above in levels:
            if level not in seen:
                seen.add(level)
                unique.append((level, is_above))
        
        unique.sort(key=lambda x: abs(x[0] - current_price))
        
        return unique[:6]
    
    def _deduplicate_zones(
        self,
        zones: List[LiquidationZone],
        tolerance_pct: float = 0.005
    ) -> List[LiquidationZone]:
        """Remove zones that are too close to each other."""
        if not zones:
            return zones
        
        # Sort by estimated volume (keep larger)
        zones.sort(key=lambda z: z.estimated_volume, reverse=True)
        
        unique = []
        for zone in zones:
            is_duplicate = False
            for existing in unique:
                if abs(zone.price_level - existing.price_level) / existing.price_level < tolerance_pct:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(zone)
        
        return unique
    
    def get_nearest_liquidation_zones(
        self,
        zones: List[LiquidationZone],
        current_price: float
    ) -> Dict:
        """Get nearest liquidation zones above and below."""
        long_zones = [z for z in zones if z.position_type == "LONG"]
        short_zones = [z for z in zones if z.position_type == "SHORT"]
        
        # Long liquidations are below current price
        long_below = [z for z in long_zones if z.price_level < current_price]
        nearest_long_liq = max(long_below, key=lambda z: z.price_level) if long_below else None
        
        # Short liquidations are above current price
        short_above = [z for z in short_zones if z.price_level > current_price]
        nearest_short_liq = min(short_above, key=lambda z: z.price_level) if short_above else None
        
        return {
            "nearest_long_liquidation": nearest_long_liq.to_dict() if nearest_long_liq else None,
            "nearest_short_liquidation": nearest_short_liq.to_dict() if nearest_short_liq else None,
            "total_long_zones": len(long_zones),
            "total_short_zones": len(short_zones),
            "max_cascade_risk_long": max((z.cascade_risk for z in long_zones), default=0),
            "max_cascade_risk_short": max((z.cascade_risk for z in short_zones), default=0)
        }
    
    def get_zone_summary(
        self,
        zones: List[LiquidationZone],
        current_price: float
    ) -> Dict:
        """Get summary of liquidation zones."""
        if not zones:
            return {"total_zones": 0}
        
        long_zones = [z for z in zones if z.position_type == "LONG"]
        short_zones = [z for z in zones if z.position_type == "SHORT"]
        
        return {
            "total_zones": len(zones),
            "long_liquidation_zones": len(long_zones),
            "short_liquidation_zones": len(short_zones),
            "total_estimated_volume": round(sum(z.estimated_volume for z in zones), 2),
            "avg_cascade_risk": round(sum(z.cascade_risk for z in zones) / len(zones), 3),
            "avg_leverage_density": round(sum(z.leverage_density for z in zones) / len(zones), 3),
            "highest_risk_zone": max(zones, key=lambda z: z.cascade_risk).to_dict()
        }
