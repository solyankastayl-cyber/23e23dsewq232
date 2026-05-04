"""
Volume Profile Engine
=====================

Анализ Volume Profile для определения:
- High/Low Volume Nodes
- Value Area
- Acceptance/Rejection zones
- POC (Point of Control)
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import random
from collections import defaultdict

from .context_types import VolumeProfileBias, VolumeProfileContext


class VolumeProfileEngine:
    """
    Engine для анализа Volume Profile.
    
    Концепции:
    - POC: уровень с наибольшим объёмом
    - Value Area: 70% объёма (VAH/VAL)
    - HVN: High Volume Node - магнит для цены
    - LVN: Low Volume Node - быстрое движение сквозь
    """
    
    def __init__(
        self,
        value_area_pct: float = 0.7,      # 70% VA
        num_price_levels: int = 50,        # Количество уровней для профиля
        hvn_threshold: float = 1.5,        # HVN = 1.5x average
        lvn_threshold: float = 0.5         # LVN = 0.5x average
    ):
        self.value_area_pct = value_area_pct
        self.num_price_levels = num_price_levels
        self.hvn_threshold = hvn_threshold
        self.lvn_threshold = lvn_threshold
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        current_price: float = 0.0,
        timestamps: Optional[List[datetime]] = None
    ) -> VolumeProfileContext:
        """
        Анализ Volume Profile.
        """
        if len(highs) < 20 or not volumes:
            return VolumeProfileContext()
        
        if current_price == 0:
            current_price = closes[-1]
        
        # Build volume profile
        profile = self._build_profile(highs, lows, volumes)
        
        # Find POC
        poc_price = self._find_poc(profile)
        
        # Calculate Value Area
        vah, val = self._calculate_value_area(profile, poc_price)
        
        # Find HVN and LVN
        hvn_levels, lvn_levels = self._find_nodes(profile)
        
        # Determine bias based on current price
        bias = self._determine_bias(current_price, poc_price, vah, val, hvn_levels, lvn_levels)
        
        # Find acceptance/rejection zones
        acceptance_zone, rejection_zone = self._find_zones(profile, hvn_levels, lvn_levels)
        
        # Node proximity
        node_proximity = self._check_node_proximity(current_price, hvn_levels, lvn_levels)
        
        # Price acceptance (is price in value area?)
        price_acceptance = val <= current_price <= vah
        
        # Breakout validation
        breakout_validation = self._calculate_breakout_validation(
            current_price, vah, val, lvn_levels
        )
        
        # Mean reversion quality
        mr_quality = self._calculate_mr_quality(
            current_price, poc_price, vah, val, hvn_levels
        )
        
        # S/R refinement levels
        sr_refinement = self._get_sr_refinement(poc_price, vah, val, hvn_levels)
        
        # Notes
        notes = self._generate_notes(
            bias, node_proximity, price_acceptance, current_price, poc_price, vah, val
        )
        
        return VolumeProfileContext(
            volume_profile_bias=bias,
            poc_price=round(poc_price, 2),
            value_area_high=round(vah, 2),
            value_area_low=round(val, 2),
            acceptance_zone=(round(val, 2), round(vah, 2)) if price_acceptance else None,
            rejection_zone=rejection_zone,
            node_proximity=node_proximity,
            price_acceptance=price_acceptance,
            breakout_validation=round(breakout_validation, 4),
            mean_reversion_quality=round(mr_quality, 4),
            sr_refinement=sr_refinement,
            notes=notes
        )
    
    def _build_profile(
        self,
        highs: List[float],
        lows: List[float],
        volumes: List[float]
    ) -> Dict[float, float]:
        """Построить volume profile"""
        profile = defaultdict(float)
        
        # Determine price range
        price_high = max(highs)
        price_low = min(lows)
        price_step = (price_high - price_low) / self.num_price_levels
        
        if price_step == 0:
            return profile
        
        # Distribute volume across price levels
        for i, (h, l, v) in enumerate(zip(highs, lows, volumes)):
            # Distribute volume proportionally across candle range
            candle_levels = int((h - l) / price_step) + 1
            vol_per_level = v / max(1, candle_levels)
            
            level = l
            while level <= h:
                bucket = round(level / price_step) * price_step
                profile[bucket] += vol_per_level
                level += price_step
        
        return dict(profile)
    
    def _find_poc(self, profile: Dict[float, float]) -> float:
        """Найти Point of Control"""
        if not profile:
            return 0.0
        
        return max(profile, key=profile.get)
    
    def _calculate_value_area(
        self,
        profile: Dict[float, float],
        poc_price: float
    ) -> Tuple[float, float]:
        """Рассчитать Value Area"""
        if not profile:
            return 0.0, 0.0
        
        total_volume = sum(profile.values())
        target_volume = total_volume * self.value_area_pct
        
        # Sort levels by distance from POC
        sorted_levels = sorted(profile.keys(), key=lambda x: abs(x - poc_price))
        
        accumulated_volume = 0.0
        included_levels = []
        
        for level in sorted_levels:
            accumulated_volume += profile[level]
            included_levels.append(level)
            
            if accumulated_volume >= target_volume:
                break
        
        if not included_levels:
            return poc_price, poc_price
        
        return max(included_levels), min(included_levels)
    
    def _find_nodes(
        self,
        profile: Dict[float, float]
    ) -> Tuple[List[float], List[float]]:
        """Найти HVN и LVN"""
        if not profile:
            return [], []
        
        avg_volume = sum(profile.values()) / len(profile)
        
        hvn_levels = [level for level, vol in profile.items() if vol > avg_volume * self.hvn_threshold]
        lvn_levels = [level for level, vol in profile.items() if vol < avg_volume * self.lvn_threshold]
        
        return sorted(hvn_levels), sorted(lvn_levels)
    
    def _determine_bias(
        self,
        current_price: float,
        poc_price: float,
        vah: float,
        val: float,
        hvn_levels: List[float],
        lvn_levels: List[float]
    ) -> VolumeProfileBias:
        """Определить bias по volume profile"""
        # Check position relative to value area
        if current_price > vah:
            return VolumeProfileBias.ABOVE_VALUE_AREA
        elif current_price < val:
            return VolumeProfileBias.BELOW_VALUE_AREA
        
        # Check proximity to nodes
        for hvn in hvn_levels:
            if abs(current_price - hvn) / current_price < 0.005:  # 0.5%
                return VolumeProfileBias.NEAR_HIGH_VOLUME_NODE
        
        for lvn in lvn_levels:
            if abs(current_price - lvn) / current_price < 0.005:
                return VolumeProfileBias.NEAR_LOW_VOLUME_NODE
        
        # Check if in acceptance zone
        if val <= current_price <= vah:
            if abs(current_price - poc_price) / current_price < 0.01:
                return VolumeProfileBias.IN_ACCEPTANCE_ZONE
        
        return VolumeProfileBias.NEUTRAL
    
    def _find_zones(
        self,
        profile: Dict[float, float],
        hvn_levels: List[float],
        lvn_levels: List[float]
    ) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """Найти acceptance и rejection zones"""
        acceptance_zone = None
        rejection_zone = None
        
        # HVN areas are acceptance zones
        if hvn_levels and len(hvn_levels) >= 2:
            acceptance_zone = (round(min(hvn_levels), 2), round(max(hvn_levels), 2))
        
        # LVN areas are rejection zones
        if lvn_levels and len(lvn_levels) >= 2:
            rejection_zone = (round(min(lvn_levels), 2), round(max(lvn_levels), 2))
        
        return acceptance_zone, rejection_zone
    
    def _check_node_proximity(
        self,
        current_price: float,
        hvn_levels: List[float],
        lvn_levels: List[float]
    ) -> str:
        """Проверить близость к нодам"""
        proximity_threshold = 0.01  # 1%
        
        for hvn in hvn_levels:
            if abs(current_price - hvn) / current_price < proximity_threshold:
                return "HVN"
        
        for lvn in lvn_levels:
            if abs(current_price - lvn) / current_price < proximity_threshold:
                return "LVN"
        
        return "NONE"
    
    def _calculate_breakout_validation(
        self,
        current_price: float,
        vah: float,
        val: float,
        lvn_levels: List[float]
    ) -> float:
        """Рассчитать валидацию breakout"""
        validation = 0.5
        
        # Above VAH = breakout bullish potential
        if current_price > vah:
            validation += 0.2
            # Check if above any LVN (fast move zone)
            lvn_above = [l for l in lvn_levels if l > vah and current_price > l]
            if lvn_above:
                validation += 0.2
        
        # Below VAL = breakout bearish potential
        elif current_price < val:
            validation += 0.2
            lvn_below = [l for l in lvn_levels if l < val and current_price < l]
            if lvn_below:
                validation += 0.2
        
        return min(1.0, validation)
    
    def _calculate_mr_quality(
        self,
        current_price: float,
        poc_price: float,
        vah: float,
        val: float,
        hvn_levels: List[float]
    ) -> float:
        """Рассчитать качество mean reversion"""
        quality = 0.5
        
        # Distance from POC
        poc_distance_pct = abs(current_price - poc_price) / poc_price * 100
        
        if poc_distance_pct > 3:
            quality += 0.2  # Far from POC = MR potential
        
        # Near HVN = good MR target
        for hvn in hvn_levels:
            if abs(current_price - hvn) / current_price < 0.02:
                quality += 0.15
                break
        
        # Outside VA = MR potential
        if current_price > vah or current_price < val:
            quality += 0.15
        
        return min(1.0, quality)
    
    def _get_sr_refinement(
        self,
        poc_price: float,
        vah: float,
        val: float,
        hvn_levels: List[float]
    ) -> List[float]:
        """Получить уточнённые S/R уровни"""
        levels = [round(poc_price, 2), round(vah, 2), round(val, 2)]
        levels.extend([round(h, 2) for h in hvn_levels[:3]])
        
        return sorted(set(levels))
    
    def _generate_notes(
        self,
        bias: VolumeProfileBias,
        node_proximity: str,
        price_acceptance: bool,
        current_price: float,
        poc_price: float,
        vah: float,
        val: float
    ) -> List[str]:
        """Генерация заметок"""
        notes = []
        
        notes.append(f"Volume Profile Bias: {bias.value}")
        notes.append(f"POC: {poc_price:.2f}, VA: {val:.2f}-{vah:.2f}")
        
        if node_proximity == "HVN":
            notes.append("Near High Volume Node - price may consolidate")
        elif node_proximity == "LVN":
            notes.append("Near Low Volume Node - expect fast movement")
        
        if not price_acceptance:
            notes.append("Price outside Value Area - potential for mean reversion")
        
        return notes
    
    def generate_mock_data(self, count: int = 100) -> tuple:
        """Генерация mock OHLCV data"""
        base_price = random.uniform(40000, 50000)
        
        highs = []
        lows = []
        closes = []
        volumes = []
        
        for _ in range(count):
            change = random.uniform(-0.02, 0.02)
            close = base_price * (1 + change)
            high = close * (1 + random.uniform(0, 0.01))
            low = close * (1 - random.uniform(0, 0.01))
            volume = random.uniform(100, 1000) * base_price
            
            highs.append(high)
            lows.append(low)
            closes.append(close)
            volumes.append(volume)
            base_price = close
        
        return highs, lows, closes, volumes
