"""
Liquidity Detector
==================

Детектор зон ликвидности и liquidity sweeps.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .structure_types import (
    LiquidityZone,
    LiquidityZoneType,
    LiquiditySweep
)


class LiquidityDetector:
    """
    Детектор зон ликвидности.
    
    Типы зон:
    - Equal Highs: несколько свингов на одном уровне
    - Equal Lows: несколько свингов на одном уровне
    - Range High: верхняя граница диапазона
    - Range Low: нижняя граница диапазона
    - Stop Hunt High/Low: зоны скопления стопов
    
    Liquidity Sweep:
    - Пробой зоны с возвратом обратно
    """
    
    def __init__(
        self,
        tolerance_pct: float = 0.3,  # Толерантность для equal levels
        min_touches: int = 2,         # Минимум касаний для зоны
        sweep_return_pct: float = 0.5  # % возврата для sweep
    ):
        self.tolerance_pct = tolerance_pct
        self.min_touches = min_touches
        self.sweep_return_pct = sweep_return_pct
    
    def detect(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        swing_highs: List[tuple],  # (idx, price)
        swing_lows: List[tuple],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Детектирование зон ликвидности и sweeps.
        """
        if len(highs) < 20:
            return self._empty_result()
        
        if timestamps is None:
            timestamps = [datetime.utcnow() for _ in range(len(highs))]
        
        # Detect liquidity zones
        liquidity_zones = []
        
        # Equal Highs
        equal_highs = self._find_equal_levels(swing_highs, highs, "HIGH", timestamps)
        liquidity_zones.extend(equal_highs)
        
        # Equal Lows
        equal_lows = self._find_equal_levels(swing_lows, lows, "LOW", timestamps)
        liquidity_zones.extend(equal_lows)
        
        # Range boundaries
        range_zones = self._find_range_boundaries(highs, lows, timestamps)
        liquidity_zones.extend(range_zones)
        
        # Detect sweeps
        sweeps = self._detect_sweeps(highs, lows, closes, liquidity_zones, timestamps)
        
        # Mark swept zones
        for sweep in sweeps:
            for zone in liquidity_zones:
                if abs(zone.price_level - sweep.sweep_price) / zone.price_level * 100 < self.tolerance_pct:
                    zone.swept = True
        
        return {
            "liquidity_zones": liquidity_zones,
            "liquidity_sweeps": sweeps,
            "active_zones": sum(1 for z in liquidity_zones if not z.swept)
        }
    
    def _find_equal_levels(
        self,
        swings: List[tuple],
        prices: List[float],
        level_type: str,
        timestamps: List[datetime]
    ) -> List[LiquidityZone]:
        """Найти equal highs/lows"""
        zones = []
        
        if len(swings) < 2:
            return zones
        
        # Group swings by price level
        used = set()
        
        for i, (idx1, price1) in enumerate(swings):
            if i in used:
                continue
            
            touches = [(idx1, price1)]
            
            for j, (idx2, price2) in enumerate(swings):
                if j <= i or j in used:
                    continue
                
                # Check if prices are within tolerance
                diff_pct = abs(price1 - price2) / price1 * 100
                if diff_pct <= self.tolerance_pct:
                    touches.append((idx2, price2))
                    used.add(j)
            
            if len(touches) >= self.min_touches:
                used.add(i)
                avg_price = sum(p for _, p in touches) / len(touches)
                
                zone_type = LiquidityZoneType.EQUAL_HIGHS if level_type == "HIGH" else LiquidityZoneType.EQUAL_LOWS
                
                # Calculate zone boundaries
                prices_at_touches = [p for _, p in touches]
                
                zones.append(LiquidityZone(
                    zone_type=zone_type,
                    price_level=avg_price,
                    price_low=min(prices_at_touches),
                    price_high=max(prices_at_touches),
                    strength=min(1.0, len(touches) * 0.25),
                    touch_count=len(touches),
                    last_touched=timestamps[touches[-1][0]] if touches[-1][0] < len(timestamps) else None,
                    notes=f"{len(touches)} equal {level_type.lower()}s detected"
                ))
        
        return zones
    
    def _find_range_boundaries(
        self,
        highs: List[float],
        lows: List[float],
        timestamps: List[datetime]
    ) -> List[LiquidityZone]:
        """Найти границы диапазона"""
        zones = []
        
        # Recent range (last 50 candles)
        lookback = min(50, len(highs))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        
        range_high = max(recent_highs)
        range_low = min(recent_lows)
        range_size = range_high - range_low
        
        # Only detect if range is significant
        if range_size / range_low * 100 < 1:
            return zones
        
        # Count touches of range high
        high_touches = sum(1 for h in recent_highs if abs(h - range_high) / range_high * 100 < self.tolerance_pct)
        
        if high_touches >= 2:
            zones.append(LiquidityZone(
                zone_type=LiquidityZoneType.RANGE_HIGH,
                price_level=range_high,
                price_low=range_high * (1 - self.tolerance_pct/100),
                price_high=range_high * (1 + self.tolerance_pct/100),
                strength=min(1.0, high_touches * 0.2),
                touch_count=high_touches,
                last_touched=timestamps[-1] if timestamps else None,
                notes=f"Range high with {high_touches} touches"
            ))
        
        # Count touches of range low
        low_touches = sum(1 for l in recent_lows if abs(l - range_low) / range_low * 100 < self.tolerance_pct)
        
        if low_touches >= 2:
            zones.append(LiquidityZone(
                zone_type=LiquidityZoneType.RANGE_LOW,
                price_level=range_low,
                price_low=range_low * (1 - self.tolerance_pct/100),
                price_high=range_low * (1 + self.tolerance_pct/100),
                strength=min(1.0, low_touches * 0.2),
                touch_count=low_touches,
                last_touched=timestamps[-1] if timestamps else None,
                notes=f"Range low with {low_touches} touches"
            ))
        
        return zones
    
    def _detect_sweeps(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        zones: List[LiquidityZone],
        timestamps: List[datetime]
    ) -> List[LiquiditySweep]:
        """Детектировать liquidity sweeps"""
        sweeps = []
        
        # Check recent candles for sweeps
        lookback = min(20, len(highs))
        
        for i in range(-lookback, -1):
            idx = len(highs) + i
            
            for zone in zones:
                if zone.swept:
                    continue
                
                # Check for sweep above (high zones)
                if zone.zone_type in [LiquidityZoneType.EQUAL_HIGHS, LiquidityZoneType.RANGE_HIGH]:
                    if highs[idx] > zone.price_high and closes[idx] < zone.price_level:
                        # Sweep detected
                        sweep_amount = highs[idx] - zone.price_level
                        return_amount = highs[idx] - closes[idx]
                        
                        if return_amount / sweep_amount >= self.sweep_return_pct:
                            sweeps.append(LiquiditySweep(
                                direction="UP",
                                sweep_price=highs[idx],
                                return_price=closes[idx],
                                zone_swept=zone.zone_type,
                                strength=min(1.0, return_amount / sweep_amount),
                                timestamp=timestamps[idx] if idx < len(timestamps) else datetime.utcnow(),
                                candle_index=idx,
                                reversal_confirmed=closes[idx] < zone.price_low,
                                notes=f"Sweep above {zone.zone_type.value}"
                            ))
                
                # Check for sweep below (low zones)
                elif zone.zone_type in [LiquidityZoneType.EQUAL_LOWS, LiquidityZoneType.RANGE_LOW]:
                    if lows[idx] < zone.price_low and closes[idx] > zone.price_level:
                        sweep_amount = zone.price_level - lows[idx]
                        return_amount = closes[idx] - lows[idx]
                        
                        if return_amount / sweep_amount >= self.sweep_return_pct:
                            sweeps.append(LiquiditySweep(
                                direction="DOWN",
                                sweep_price=lows[idx],
                                return_price=closes[idx],
                                zone_swept=zone.zone_type,
                                strength=min(1.0, return_amount / sweep_amount),
                                timestamp=timestamps[idx] if idx < len(timestamps) else datetime.utcnow(),
                                candle_index=idx,
                                reversal_confirmed=closes[idx] > zone.price_high,
                                notes=f"Sweep below {zone.zone_type.value}"
                            ))
        
        return sweeps
    
    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат"""
        return {
            "liquidity_zones": [],
            "liquidity_sweeps": [],
            "active_zones": 0
        }
