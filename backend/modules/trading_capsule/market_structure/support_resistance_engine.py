"""
Support Resistance Engine
=========================

Определение кластерных зон поддержки и сопротивления.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from .structure_types import (
    SRCluster,
    SRType,
    LiquidityZone,
    Imbalance
)


class SupportResistanceEngine:
    """
    Engine для определения кластерных зон S/R.
    
    Источники:
    - Swing points
    - Fibonacci levels
    - Round numbers
    - Volume profile (approximated)
    - Imbalance zones
    - Liquidity zones
    
    Кластеризация:
    - Объединяет близкие уровни в зоны
    - Рассчитывает силу зоны
    """
    
    def __init__(
        self,
        cluster_tolerance_pct: float = 0.5,  # % для кластеризации
        min_sources: int = 2,                 # Минимум источников для кластера
        fib_levels: List[float] = None        # Fib levels
    ):
        self.cluster_tolerance_pct = cluster_tolerance_pct
        self.min_sources = min_sources
        self.fib_levels = fib_levels or [0.236, 0.382, 0.5, 0.618, 0.786]
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float,
        swing_highs: List[Tuple[int, float]],
        swing_lows: List[Tuple[int, float]],
        liquidity_zones: List[LiquidityZone] = None,
        imbalances: List[Imbalance] = None,
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Анализ S/R уровней.
        """
        if len(highs) < 20:
            return self._empty_result()
        
        # Collect all potential S/R levels
        levels = []
        
        # 1. Swing points
        swing_levels = self._from_swings(swing_highs, swing_lows, current_price)
        levels.extend(swing_levels)
        
        # 2. Fibonacci levels
        fib_levels = self._from_fibonacci(highs, lows, current_price)
        levels.extend(fib_levels)
        
        # 3. Round numbers
        round_levels = self._from_round_numbers(current_price)
        levels.extend(round_levels)
        
        # 4. Liquidity zones
        if liquidity_zones:
            liq_levels = self._from_liquidity(liquidity_zones, current_price)
            levels.extend(liq_levels)
        
        # 5. Imbalance zones
        if imbalances:
            imb_levels = self._from_imbalances(imbalances, current_price)
            levels.extend(imb_levels)
        
        # Cluster levels
        support_clusters, resistance_clusters = self._cluster_levels(levels, current_price)
        
        # Find nearest
        nearest_support = None
        nearest_resistance = None
        
        if support_clusters:
            nearest_support = max(c.price_center for c in support_clusters)
        
        if resistance_clusters:
            nearest_resistance = min(c.price_center for c in resistance_clusters)
        
        # Key levels
        key_levels = []
        for c in sorted(support_clusters + resistance_clusters, key=lambda x: x.strength, reverse=True)[:5]:
            key_levels.append(c.price_center)
        
        return {
            "support_clusters": support_clusters,
            "resistance_clusters": resistance_clusters,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "key_levels": sorted(key_levels)
        }
    
    def _from_swings(
        self,
        swing_highs: List[Tuple[int, float]],
        swing_lows: List[Tuple[int, float]],
        current_price: float
    ) -> List[Dict[str, Any]]:
        """Уровни из свинг-точек"""
        levels = []
        
        for idx, price in swing_highs:
            sr_type = SRType.RESISTANCE if price > current_price else SRType.SUPPORT
            levels.append({
                "price": price,
                "type": sr_type,
                "source": "swing",
                "strength": 0.6
            })
        
        for idx, price in swing_lows:
            sr_type = SRType.SUPPORT if price < current_price else SRType.RESISTANCE
            levels.append({
                "price": price,
                "type": sr_type,
                "source": "swing",
                "strength": 0.6
            })
        
        return levels
    
    def _from_fibonacci(
        self,
        highs: List[float],
        lows: List[float],
        current_price: float
    ) -> List[Dict[str, Any]]:
        """Уровни из Fibonacci"""
        levels = []
        
        # Recent range for Fib
        lookback = min(50, len(highs))
        range_high = max(highs[-lookback:])
        range_low = min(lows[-lookback:])
        range_size = range_high - range_low
        
        for fib in self.fib_levels:
            # Fib from low to high (retracement in uptrend)
            fib_price = range_high - range_size * fib
            sr_type = SRType.SUPPORT if fib_price < current_price else SRType.RESISTANCE
            
            levels.append({
                "price": fib_price,
                "type": sr_type,
                "source": "fib",
                "strength": 0.5 if fib in [0.5, 0.618] else 0.4
            })
            
            # Fib from high to low (retracement in downtrend)
            fib_price = range_low + range_size * fib
            sr_type = SRType.SUPPORT if fib_price < current_price else SRType.RESISTANCE
            
            levels.append({
                "price": fib_price,
                "type": sr_type,
                "source": "fib",
                "strength": 0.5 if fib in [0.5, 0.618] else 0.4
            })
        
        return levels
    
    def _from_round_numbers(self, current_price: float) -> List[Dict[str, Any]]:
        """Уровни из круглых чисел"""
        levels = []
        
        # Determine round number interval based on price
        if current_price > 10000:
            interval = 1000
        elif current_price > 1000:
            interval = 100
        elif current_price > 100:
            interval = 10
        else:
            interval = 1
        
        # Find nearest round numbers
        base = int(current_price / interval) * interval
        
        for i in range(-3, 4):
            round_price = base + i * interval
            if round_price <= 0:
                continue
            
            sr_type = SRType.SUPPORT if round_price < current_price else SRType.RESISTANCE
            
            # Strength based on "roundness"
            strength = 0.3
            if round_price % (interval * 10) == 0:
                strength = 0.5
            if round_price % (interval * 100) == 0:
                strength = 0.6
            
            levels.append({
                "price": float(round_price),
                "type": sr_type,
                "source": "round",
                "strength": strength
            })
        
        return levels
    
    def _from_liquidity(
        self,
        liquidity_zones: List[LiquidityZone],
        current_price: float
    ) -> List[Dict[str, Any]]:
        """Уровни из зон ликвидности"""
        levels = []
        
        for zone in liquidity_zones:
            sr_type = SRType.SUPPORT if zone.price_level < current_price else SRType.RESISTANCE
            
            levels.append({
                "price": zone.price_level,
                "type": sr_type,
                "source": "liquidity",
                "strength": zone.strength
            })
        
        return levels
    
    def _from_imbalances(
        self,
        imbalances: List[Imbalance],
        current_price: float
    ) -> List[Dict[str, Any]]:
        """Уровни из зон дисбаланса"""
        levels = []
        
        for imb in imbalances:
            if not imb.active:
                continue
            
            sr_type = SRType.SUPPORT if imb.midpoint < current_price else SRType.RESISTANCE
            
            levels.append({
                "price": imb.midpoint,
                "type": sr_type,
                "source": "imbalance",
                "strength": imb.strength * 0.8
            })
        
        return levels
    
    def _cluster_levels(
        self,
        levels: List[Dict[str, Any]],
        current_price: float
    ) -> Tuple[List[SRCluster], List[SRCluster]]:
        """Кластеризация уровней"""
        support_clusters = []
        resistance_clusters = []
        
        # Separate by type
        support_levels = [l for l in levels if l["type"] == SRType.SUPPORT]
        resistance_levels = [l for l in levels if l["type"] == SRType.RESISTANCE]
        
        # Cluster support
        support_clusters = self._create_clusters(support_levels, SRType.SUPPORT)
        
        # Cluster resistance
        resistance_clusters = self._create_clusters(resistance_levels, SRType.RESISTANCE)
        
        return support_clusters, resistance_clusters
    
    def _create_clusters(
        self,
        levels: List[Dict[str, Any]],
        sr_type: SRType
    ) -> List[SRCluster]:
        """Создать кластеры из уровней"""
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x["price"])
        
        clusters = []
        used = set()
        
        for i, level in enumerate(sorted_levels):
            if i in used:
                continue
            
            cluster_levels = [level]
            sources = {level["source"]}
            
            # Find nearby levels
            for j, other in enumerate(sorted_levels):
                if j <= i or j in used:
                    continue
                
                diff_pct = abs(level["price"] - other["price"]) / level["price"] * 100
                
                if diff_pct <= self.cluster_tolerance_pct:
                    cluster_levels.append(other)
                    sources.add(other["source"])
                    used.add(j)
            
            if len(sources) >= self.min_sources or len(cluster_levels) >= 3:
                used.add(i)
                
                prices = [l["price"] for l in cluster_levels]
                strengths = [l["strength"] for l in cluster_levels]
                
                cluster = SRCluster(
                    sr_type=sr_type,
                    price_center=sum(prices) / len(prices),
                    price_low=min(prices),
                    price_high=max(prices),
                    strength=min(1.0, sum(strengths) / len(strengths) + len(sources) * 0.1),
                    touch_count=len(cluster_levels),
                    source_count=len(sources),
                    sources=list(sources),
                    notes=f"Cluster from {len(sources)} sources: {', '.join(sources)}"
                )
                clusters.append(cluster)
        
        return sorted(clusters, key=lambda x: x.strength, reverse=True)
    
    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат"""
        return {
            "support_clusters": [],
            "resistance_clusters": [],
            "nearest_support": None,
            "nearest_resistance": None,
            "key_levels": []
        }
