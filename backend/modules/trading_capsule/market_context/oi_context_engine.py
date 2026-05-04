"""
Open Interest Context Engine
============================

Анализ Open Interest для определения:
- OI rising/falling with price
- Squeeze conditions
- Participation quality
- Short covering / Long liquidation
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import random

from .context_types import OIState, OIContext


class OIContextEngine:
    """
    Engine для анализа Open Interest контекста.
    
    OI + Price analysis:
    - Price up + OI up = Strong participation (new longs)
    - Price up + OI down = Weak move (short covering)
    - Price down + OI up = Strong selling (new shorts)
    - Price down + OI down = Long liquidation
    """
    
    def __init__(
        self,
        oi_change_threshold: float = 3.0,   # 3% change = significant
        surge_threshold: float = 10.0,       # 10% = surge
        collapse_threshold: float = -10.0,   # -10% = collapse
        squeeze_oi_threshold: float = 5.0    # 5% OI rise against price
    ):
        self.oi_change_threshold = oi_change_threshold
        self.surge_threshold = surge_threshold
        self.collapse_threshold = collapse_threshold
        self.squeeze_oi_threshold = squeeze_oi_threshold
    
    def analyze(
        self,
        oi_values: List[float],
        prices: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> OIContext:
        """
        Анализ Open Interest.
        
        Args:
            oi_values: История OI (последний = текущий)
            prices: История цен (последний = текущий)
            
        Returns:
            OIContext с полным анализом
        """
        if not oi_values or not prices or len(oi_values) < 5 or len(prices) < 5:
            return OIContext()
        
        # Calculate changes
        oi_change_pct = (oi_values[-1] - oi_values[-5]) / oi_values[-5] * 100
        price_change_pct = (prices[-1] - prices[-5]) / prices[-5] * 100
        
        # Determine state
        state = self._determine_state(oi_change_pct, price_change_pct)
        
        # Calculate pressure
        pressure = self._calculate_pressure(oi_change_pct, price_change_pct)
        
        # Squeeze probability
        squeeze_prob = self._calculate_squeeze_probability(oi_change_pct, price_change_pct, state)
        
        # Participation quality
        participation = self._determine_participation(state, oi_change_pct, price_change_pct)
        
        # Alignment
        price_oi_aligned = self._check_alignment(oi_change_pct, price_change_pct)
        
        # Detect liquidation events
        short_covering = (price_change_pct > 1 and oi_change_pct < -self.oi_change_threshold)
        long_liquidation = (price_change_pct < -1 and oi_change_pct < -self.oi_change_threshold)
        
        # Confidence adjustment
        confidence_adj = self._calculate_confidence_adjustment(
            state, participation, short_covering, long_liquidation
        )
        
        # Notes
        notes = self._generate_notes(
            state, participation, short_covering, long_liquidation, squeeze_prob
        )
        
        return OIContext(
            oi_state=state,
            oi_change_pct=round(oi_change_pct, 4),
            oi_pressure=round(pressure, 4),
            squeeze_probability=round(squeeze_prob, 4),
            participation_quality=participation,
            price_oi_alignment=price_oi_aligned,
            short_covering_detected=short_covering,
            long_liquidation_detected=long_liquidation,
            confidence_adjustment=round(confidence_adj, 4),
            notes=notes
        )
    
    def _determine_state(self, oi_change: float, price_change: float) -> OIState:
        """Определить состояние OI"""
        # Check for extreme moves first
        if oi_change >= self.surge_threshold:
            return OIState.SURGE
        elif oi_change <= self.collapse_threshold:
            return OIState.COLLAPSE
        
        # Normal analysis
        oi_rising = oi_change > self.oi_change_threshold
        oi_falling = oi_change < -self.oi_change_threshold
        price_up = price_change > 0.5
        price_down = price_change < -0.5
        
        if oi_rising and price_up:
            return OIState.RISING_WITH_PRICE
        elif oi_rising and price_down:
            return OIState.RISING_AGAINST_PRICE
        elif oi_falling and price_up:
            return OIState.FALLING_AGAINST_PRICE  # Short covering
        elif oi_falling and price_down:
            return OIState.FALLING_WITH_PRICE  # Long liquidation
        else:
            return OIState.STABLE
    
    def _calculate_pressure(self, oi_change: float, price_change: float) -> float:
        """Рассчитать давление OI"""
        # Positive when OI confirms price, negative when diverges
        if (oi_change > 0 and price_change > 0) or (oi_change < 0 and price_change < 0):
            # Aligned
            pressure = abs(oi_change) / 10
        else:
            # Diverged
            pressure = -abs(oi_change) / 10
        
        return max(-1.0, min(1.0, pressure))
    
    def _calculate_squeeze_probability(
        self,
        oi_change: float,
        price_change: float,
        state: OIState
    ) -> float:
        """Рассчитать вероятность squeeze"""
        prob = 0.2  # Base
        
        # High OI against price = squeeze potential
        if state == OIState.RISING_AGAINST_PRICE:
            prob += 0.4
            if abs(oi_change) > self.squeeze_oi_threshold:
                prob += 0.2
        
        # Surge in OI
        if state == OIState.SURGE:
            prob += 0.3
        
        return min(1.0, prob)
    
    def _determine_participation(
        self,
        state: OIState,
        oi_change: float,
        price_change: float
    ) -> str:
        """Определить качество участия"""
        if state == OIState.RISING_WITH_PRICE:
            return "STRONG"
        elif state in [OIState.FALLING_WITH_PRICE, OIState.FALLING_AGAINST_PRICE]:
            return "WEAK"
        elif state == OIState.RISING_AGAINST_PRICE:
            return "WEAK"  # Against trend
        else:
            return "NEUTRAL"
    
    def _check_alignment(self, oi_change: float, price_change: float) -> bool:
        """Проверить выравнивание OI и цены"""
        # Aligned when both positive or both negative
        return (oi_change > 0 and price_change > 0) or (oi_change < 0 and price_change < 0)
    
    def _calculate_confidence_adjustment(
        self,
        state: OIState,
        participation: str,
        short_covering: bool,
        long_liquidation: bool
    ) -> float:
        """Рассчитать adjustment для confidence"""
        adj = 0.0
        
        if participation == "STRONG":
            adj = 0.15
        elif participation == "WEAK":
            adj = -0.1
        
        if short_covering:
            adj -= 0.1  # Reduces long confidence (fake move)
        
        if long_liquidation:
            adj -= 0.15  # Panic selling
        
        if state == OIState.SURGE:
            adj += 0.1  # High participation
        elif state == OIState.COLLAPSE:
            adj -= 0.2  # Capitulation
        
        return max(-0.5, min(0.5, adj))
    
    def _generate_notes(
        self,
        state: OIState,
        participation: str,
        short_covering: bool,
        long_liquidation: bool,
        squeeze_prob: float
    ) -> List[str]:
        """Генерация заметок"""
        notes = []
        
        notes.append(f"OI State: {state.value}")
        notes.append(f"Participation: {participation}")
        
        if short_covering:
            notes.append("Short covering detected - price move may be weak")
        
        if long_liquidation:
            notes.append("Long liquidation detected - potential capitulation")
        
        if squeeze_prob > 0.6:
            notes.append(f"High squeeze probability: {squeeze_prob:.0%}")
        
        return notes
    
    def generate_mock_data(self, count: int = 50) -> tuple:
        """Генерация mock OI и price data"""
        base_oi = random.uniform(1000000, 5000000)
        base_price = random.uniform(40000, 50000)
        
        oi_values = []
        prices = []
        
        for _ in range(count):
            oi_change = random.uniform(-0.02, 0.02)
            price_change = random.uniform(-0.01, 0.01)
            
            base_oi *= (1 + oi_change)
            base_price *= (1 + price_change)
            
            oi_values.append(base_oi)
            prices.append(base_price)
        
        return oi_values, prices
