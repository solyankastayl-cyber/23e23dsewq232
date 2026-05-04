"""
Volatility Context Engine
=========================

Анализ волатильности для определения:
- Volatility regime
- Compression/Expansion
- Breakout/Mean reversion conditions
- Risk multipliers
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import math
import random

from .context_types import VolatilityRegime, VolatilityContext


class VolatilityContextEngine:
    """
    Engine для анализа контекста волатильности.
    
    Режимы:
    - COMPRESSED: низкая волатильность, потенциал breakout
    - EXPANDING: растущая волатильность, тренд в развитии
    - UNSTABLE: хаотичная волатильность, опасно
    - EXHAUSTED: затухающая волатильность после движения
    """
    
    def __init__(
        self,
        compression_percentile: float = 20.0,   # < 20% = compressed
        expansion_percentile: float = 80.0,     # > 80% = expanding
        lookback_periods: int = 20,
        atr_periods: int = 14
    ):
        self.compression_percentile = compression_percentile
        self.expansion_percentile = expansion_percentile
        self.lookback_periods = lookback_periods
        self.atr_periods = atr_periods
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> VolatilityContext:
        """
        Анализ контекста волатильности.
        """
        if len(highs) < 30 or len(lows) < 30 or len(closes) < 30:
            return VolatilityContext()
        
        # Calculate ATR
        current_atr = self._calculate_atr(highs, lows, closes, self.atr_periods)
        
        # Calculate historical ATR for percentile
        atr_history = []
        for i in range(self.lookback_periods, len(highs)):
            atr = self._calculate_atr(
                highs[i-self.lookback_periods:i],
                lows[i-self.lookback_periods:i],
                closes[i-self.lookback_periods:i],
                min(self.atr_periods, self.lookback_periods)
            )
            atr_history.append(atr)
        
        # Calculate percentile
        percentile = self._calculate_percentile(current_atr, atr_history)
        
        # Determine regime
        regime = self._determine_regime(percentile, highs, lows, closes)
        
        # Calculate pressure
        pressure = self._calculate_pressure(percentile)
        
        # Determine quality
        quality = self._determine_quality(highs, lows, closes)
        
        # Calculate expansion probability
        expansion_prob = self._calculate_expansion_probability(percentile, regime)
        
        # Determine favorable conditions
        breakout_favorable = (regime == VolatilityRegime.COMPRESSED and percentile < 25)
        mean_reversion_favorable = (regime == VolatilityRegime.EXHAUSTED or percentile > 85)
        
        # Risk multiplier
        risk_mult = self._calculate_risk_multiplier(percentile, regime)
        
        # Notes
        notes = self._generate_notes(regime, percentile, breakout_favorable, mean_reversion_favorable)
        
        return VolatilityContext(
            volatility_regime=regime,
            volatility_percentile=round(percentile, 2),
            volatility_pressure=round(pressure, 4),
            volatility_quality=quality,
            expansion_probability=round(expansion_prob, 4),
            breakout_favorable=breakout_favorable,
            mean_reversion_favorable=mean_reversion_favorable,
            risk_multiplier=round(risk_mult, 4),
            notes=notes
        )
    
    def _calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        periods: int
    ) -> float:
        """Рассчитать ATR"""
        n = min(len(highs), len(lows), len(closes))
        if n < periods + 1:
            return 0.0
        
        tr_values = []
        for i in range(1, min(periods + 1, n)):
            idx = n - periods - 1 + i
            if idx > 0 and idx < n:
                tr = max(
                    highs[idx] - lows[idx],
                    abs(highs[idx] - closes[idx-1]),
                    abs(lows[idx] - closes[idx-1])
                )
                tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values) if tr_values else 0.0
    
    def _calculate_percentile(self, current: float, history: List[float]) -> float:
        """Рассчитать перцентиль текущего значения"""
        if not history:
            return 50.0
        
        below_count = sum(1 for h in history if h < current)
        return (below_count / len(history)) * 100
    
    def _determine_regime(
        self,
        percentile: float,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> VolatilityRegime:
        """Определить режим волатильности"""
        # Check recent volatility trend
        recent_range = sum(highs[-5:]) / 5 - sum(lows[-5:]) / 5
        older_range = sum(highs[-15:-10]) / 5 - sum(lows[-15:-10]) / 5
        
        vol_expanding = recent_range > older_range * 1.2
        vol_contracting = recent_range < older_range * 0.8
        
        if percentile < self.compression_percentile:
            return VolatilityRegime.COMPRESSED
        elif percentile > self.expansion_percentile:
            if vol_contracting:
                return VolatilityRegime.EXHAUSTED
            else:
                return VolatilityRegime.EXPANDING
        else:
            # Check for instability (whipsaw)
            changes = [abs(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(-10, 0)]
            if max(changes) > 3 and min(changes) < 0.5:
                return VolatilityRegime.UNSTABLE
            return VolatilityRegime.NORMAL
    
    def _calculate_pressure(self, percentile: float) -> float:
        """Рассчитать давление волатильности"""
        # -1 = contracting, +1 = expanding
        return (percentile - 50) / 50
    
    def _determine_quality(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> str:
        """Определить качество волатильности"""
        # Check for clean vs choppy movement
        directional_moves = 0
        reversals = 0
        
        for i in range(-10, -1):
            if (closes[i] > closes[i-1] and closes[i+1] > closes[i]) or \
               (closes[i] < closes[i-1] and closes[i+1] < closes[i]):
                directional_moves += 1
            else:
                reversals += 1
        
        ratio = directional_moves / (reversals + 1)
        
        if ratio > 1.5:
            return "CLEAN"
        elif ratio < 0.7:
            return "CHOPPY"
        else:
            return "NORMAL"
    
    def _calculate_expansion_probability(
        self,
        percentile: float,
        regime: VolatilityRegime
    ) -> float:
        """Рассчитать вероятность расширения волатильности"""
        if regime == VolatilityRegime.COMPRESSED:
            return min(1.0, 0.5 + (100 - percentile) / 200)
        elif regime == VolatilityRegime.EXHAUSTED:
            return 0.3
        elif regime == VolatilityRegime.EXPANDING:
            return 0.6
        else:
            return 0.5
    
    def _calculate_risk_multiplier(
        self,
        percentile: float,
        regime: VolatilityRegime
    ) -> float:
        """Рассчитать множитель риска"""
        # High volatility = reduce position size
        if regime == VolatilityRegime.EXPANDING or percentile > 80:
            return 0.7
        elif regime == VolatilityRegime.UNSTABLE:
            return 0.5
        elif regime == VolatilityRegime.COMPRESSED:
            return 1.2  # Can take more risk in low vol
        else:
            return 1.0
    
    def _generate_notes(
        self,
        regime: VolatilityRegime,
        percentile: float,
        breakout_favorable: bool,
        mr_favorable: bool
    ) -> List[str]:
        """Генерация заметок"""
        notes = []
        
        notes.append(f"Volatility regime: {regime.value}")
        notes.append(f"Percentile: {percentile:.1f}%")
        
        if breakout_favorable:
            notes.append("Conditions favorable for breakout strategies")
        
        if mr_favorable:
            notes.append("Conditions favorable for mean reversion")
        
        if regime == VolatilityRegime.UNSTABLE:
            notes.append("WARNING: Unstable volatility - reduce exposure")
        
        return notes
    
    def generate_mock_data(self, count: int = 100) -> tuple:
        """Генерация mock OHLC data"""
        base_price = random.uniform(40000, 50000)
        
        highs = []
        lows = []
        closes = []
        
        for _ in range(count):
            change = random.uniform(-0.02, 0.02)
            close = base_price * (1 + change)
            high = close * (1 + random.uniform(0, 0.01))
            low = close * (1 - random.uniform(0, 0.01))
            
            highs.append(high)
            lows.append(low)
            closes.append(close)
            base_price = close
        
        return highs, lows, closes
