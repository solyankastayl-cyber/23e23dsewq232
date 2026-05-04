"""
Funding Context Engine
======================

Анализ funding rate для определения:
- Funding bias
- Funding extremes
- Long/Short overcrowding
- Confidence adjustments
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import random

from .context_types import FundingState, FundingContext


class FundingContextEngine:
    """
    Engine для анализа funding rate контекста.
    
    Funding rate показывает:
    - Положительный: лонги платят шортам (бычий сентимент)
    - Отрицательный: шорты платят лонгам (медвежий сентимент)
    - Экстремальные значения: перекупленность/перепроданность
    """
    
    def __init__(
        self,
        extreme_threshold: float = 0.05,      # 0.05% = extreme
        high_threshold: float = 0.02,         # 0.02% = high
        mild_threshold: float = 0.005,        # 0.005% = mild
        overcrowding_threshold: float = 0.03  # 0.03% = overcrowded
    ):
        self.extreme_threshold = extreme_threshold
        self.high_threshold = high_threshold
        self.mild_threshold = mild_threshold
        self.overcrowding_threshold = overcrowding_threshold
    
    def analyze(
        self,
        funding_rates: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> FundingContext:
        """
        Анализ funding rate.
        
        Args:
            funding_rates: История funding rates (последний = текущий)
            timestamps: Временные метки
            
        Returns:
            FundingContext с полным анализом
        """
        if not funding_rates:
            return FundingContext()
        
        current_rate = funding_rates[-1]
        
        # Determine state
        state = self._determine_state(current_rate)
        
        # Calculate pressure (-1 to +1)
        pressure = self._calculate_pressure(current_rate)
        
        # Check extreme
        is_extreme = abs(current_rate) >= self.extreme_threshold
        
        # Calculate acceleration (change in funding)
        acceleration = 0.0
        if len(funding_rates) >= 3:
            recent_avg = sum(funding_rates[-3:]) / 3
            older_avg = sum(funding_rates[-6:-3]) / 3 if len(funding_rates) >= 6 else recent_avg
            acceleration = (recent_avg - older_avg) / (abs(older_avg) + 0.0001)
            acceleration = max(-1.0, min(1.0, acceleration * 10))
        
        # Determine overcrowding
        long_overcrowded = current_rate >= self.overcrowding_threshold
        short_overcrowded = current_rate <= -self.overcrowding_threshold
        
        if long_overcrowded:
            directional_bias = "LONG_OVERCROWDED"
        elif short_overcrowded:
            directional_bias = "SHORT_OVERCROWDED"
        else:
            directional_bias = "NEUTRAL"
        
        # Calculate confidence adjustment
        confidence_adj = self._calculate_confidence_adjustment(
            current_rate, is_extreme, long_overcrowded, short_overcrowded
        )
        
        # Generate notes
        notes = self._generate_notes(
            state, is_extreme, long_overcrowded, short_overcrowded, acceleration
        )
        
        return FundingContext(
            funding_state=state,
            funding_rate=current_rate,
            funding_pressure=round(pressure, 4),
            funding_extreme=is_extreme,
            funding_acceleration=round(acceleration, 4),
            directional_bias=directional_bias,
            long_overcrowded=long_overcrowded,
            short_overcrowded=short_overcrowded,
            confidence_adjustment=round(confidence_adj, 4),
            notes=notes
        )
    
    def _determine_state(self, rate: float) -> FundingState:
        """Определить состояние funding"""
        abs_rate = abs(rate)
        
        if abs_rate < self.mild_threshold:
            return FundingState.NEUTRAL
        
        if rate > 0:
            if abs_rate >= self.extreme_threshold:
                return FundingState.POSITIVE_EXTREME
            elif abs_rate >= self.high_threshold:
                return FundingState.POSITIVE_HIGH
            else:
                return FundingState.POSITIVE_MILD
        else:
            if abs_rate >= self.extreme_threshold:
                return FundingState.NEGATIVE_EXTREME
            elif abs_rate >= self.high_threshold:
                return FundingState.NEGATIVE_HIGH
            else:
                return FundingState.NEGATIVE_MILD
    
    def _calculate_pressure(self, rate: float) -> float:
        """Рассчитать давление funding (-1 to +1)"""
        # Normalize to -1 to +1 based on extreme threshold
        normalized = rate / self.extreme_threshold
        return max(-1.0, min(1.0, normalized))
    
    def _calculate_confidence_adjustment(
        self,
        rate: float,
        is_extreme: bool,
        long_overcrowded: bool,
        short_overcrowded: bool
    ) -> float:
        """
        Рассчитать adjustment для confidence.
        
        - Extreme positive funding reduces long confidence
        - Extreme negative funding reduces short confidence
        """
        adj = 0.0
        
        if is_extreme:
            if rate > 0:
                # Reduce long confidence, increase short potential
                adj = -0.2  # For longs
            else:
                adj = 0.2   # For longs (shorts overcrowded = long opportunity)
        elif long_overcrowded:
            adj = -0.1
        elif short_overcrowded:
            adj = 0.1
        
        return adj
    
    def _generate_notes(
        self,
        state: FundingState,
        is_extreme: bool,
        long_overcrowded: bool,
        short_overcrowded: bool,
        acceleration: float
    ) -> List[str]:
        """Генерация заметок"""
        notes = []
        
        if is_extreme:
            notes.append(f"EXTREME funding detected: {state.value}")
        
        if long_overcrowded:
            notes.append("Long side overcrowded - breakout long confidence reduced")
        elif short_overcrowded:
            notes.append("Short side overcrowded - potential short squeeze")
        
        if acceleration > 0.5:
            notes.append("Funding accelerating positive - increasing long pressure")
        elif acceleration < -0.5:
            notes.append("Funding accelerating negative - increasing short pressure")
        
        return notes
    
    def generate_mock_data(self, count: int = 24) -> List[float]:
        """Генерация mock funding rates"""
        base = random.uniform(-0.02, 0.02)
        rates = []
        
        for _ in range(count):
            change = random.uniform(-0.005, 0.005)
            base = max(-0.1, min(0.1, base + change))
            rates.append(round(base, 6))
        
        return rates
