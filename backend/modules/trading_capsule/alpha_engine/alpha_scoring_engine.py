"""
Alpha Scoring Engine
====================

Engine для агрегации и нормализации alpha-факторов.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .alpha_types import (
    AlphaResult, 
    AlphaSummary, 
    AlphaDirection, 
    AlphaConfig
)
from .alpha_registry import AlphaRegistry, get_alpha_registry


class AlphaScoringEngine:
    """
    Engine для scoring и агрегации alpha-факторов.
    
    Функции:
    - Запуск всех alpha
    - Нормализация значений
    - Взвешенная агрегация
    - Формирование summary
    """
    
    def __init__(self, config: Optional[AlphaConfig] = None):
        self.config = config or AlphaConfig()
        self.registry = get_alpha_registry()
    
    def compute_all_alphas(self, market_data: Dict[str, Any]) -> List[AlphaResult]:
        """Вычисление всех alpha-факторов"""
        return self.registry.compute_all(market_data)
    
    def normalize_results(self, results: List[AlphaResult]) -> List[AlphaResult]:
        """
        Нормализация результатов alpha.
        Приводит strength и confidence к единой шкале.
        """
        if not results:
            return results
        
        # Find max values for normalization
        max_strength = max(r.strength for r in results) or 1.0
        
        normalized = []
        for r in results:
            # Normalize strength to 0-1 range
            norm_strength = r.strength / max_strength if max_strength > 0 else 0
            
            normalized.append(AlphaResult(
                alpha_id=r.alpha_id,
                alpha_name=r.alpha_name,
                direction=r.direction,
                strength=round(norm_strength, 4),
                confidence=r.confidence,
                regime_relevance=r.regime_relevance,
                raw_value=r.raw_value,
                normalized_value=r.normalized_value,
                metadata=r.metadata,
                computed_at=r.computed_at
            ))
        
        return normalized
    
    def aggregate_direction(self, results: List[AlphaResult]) -> AlphaDirection:
        """
        Агрегация направления из всех alpha.
        Взвешенное голосование.
        """
        if not results:
            return AlphaDirection.NEUTRAL
        
        weights = self.config.weights
        
        long_score = 0.0
        short_score = 0.0
        
        for r in results:
            weight = weights.get(r.alpha_id, 1.0)
            vote_strength = r.strength * r.confidence * weight
            
            if r.direction == AlphaDirection.LONG:
                long_score += vote_strength
            elif r.direction == AlphaDirection.SHORT:
                short_score += vote_strength
        
        # Determine winner
        if long_score > short_score * 1.2:  # 20% margin for LONG
            return AlphaDirection.LONG
        elif short_score > long_score * 1.2:  # 20% margin for SHORT
            return AlphaDirection.SHORT
        else:
            return AlphaDirection.NEUTRAL
    
    def calculate_aggregate_confidence(self, results: List[AlphaResult], direction: AlphaDirection) -> float:
        """
        Вычисление агрегированной уверенности.
        """
        if not results:
            return 0.0
        
        weights = self.config.weights
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for r in results:
            weight = weights.get(r.alpha_id, 1.0)
            
            # Only count alphas that agree with the direction
            if r.direction == direction or r.direction == AlphaDirection.NEUTRAL:
                alignment_factor = 1.0 if r.direction == direction else 0.5
                weighted_confidence += r.confidence * weight * alignment_factor
                total_weight += weight
            else:
                # Disagreeing alpha reduces confidence
                weighted_confidence -= r.confidence * weight * 0.3
        
        if total_weight == 0:
            return 0.0
        
        return max(0.0, min(1.0, weighted_confidence / total_weight))
    
    def calculate_aggregate_strength(self, results: List[AlphaResult], direction: AlphaDirection) -> float:
        """
        Вычисление агрегированной силы сигнала.
        """
        if not results:
            return 0.0
        
        weights = self.config.weights
        total_weight = 0.0
        weighted_strength = 0.0
        
        for r in results:
            weight = weights.get(r.alpha_id, 1.0)
            
            if r.direction == direction:
                weighted_strength += r.strength * weight
                total_weight += weight
            elif r.direction == AlphaDirection.NEUTRAL:
                weighted_strength += r.strength * weight * 0.5
                total_weight += weight * 0.5
        
        if total_weight == 0:
            return 0.0
        
        return min(1.0, weighted_strength / total_weight)
    
    def build_summary(
        self, 
        symbol: str, 
        timeframe: str,
        results: List[AlphaResult]
    ) -> AlphaSummary:
        """
        Построение полного summary из результатов alpha.
        """
        # Aggregate metrics
        direction = self.aggregate_direction(results)
        confidence = self.calculate_aggregate_confidence(results, direction)
        strength = self.calculate_aggregate_strength(results, direction)
        
        # Count signals
        long_signals = sum(1 for r in results if r.direction == AlphaDirection.LONG)
        short_signals = sum(1 for r in results if r.direction == AlphaDirection.SHORT)
        neutral_signals = sum(1 for r in results if r.direction == AlphaDirection.NEUTRAL)
        
        # Extract individual alpha strengths
        alpha_values = {r.alpha_id: r.strength for r in results}
        
        # Generate notes
        notes = self._generate_notes(results, direction, confidence)
        
        return AlphaSummary(
            symbol=symbol,
            timeframe=timeframe,
            alpha_bias=direction,
            alpha_confidence=round(confidence, 4),
            alpha_strength=round(strength, 4),
            trend_strength=alpha_values.get("trend_strength_alpha", 0.0),
            trend_acceleration=alpha_values.get("trend_acceleration_alpha", 0.0),
            trend_exhaustion=alpha_values.get("trend_exhaustion_alpha", 0.0),
            breakout_pressure=alpha_values.get("breakout_pressure_alpha", 0.0),
            volatility_compression=alpha_values.get("volatility_compression_alpha", 0.0),
            volatility_expansion=alpha_values.get("volatility_expansion_alpha", 0.0),
            reversal_pressure=alpha_values.get("reversal_pressure_alpha", 0.0),
            volume_confirmation=alpha_values.get("volume_confirmation_alpha", 0.0),
            volume_anomaly=alpha_values.get("volume_anomaly_alpha", 0.0),
            liquidity_sweep=alpha_values.get("liquidity_sweep_alpha", 0.0),
            alphas_count=len(results),
            long_signals=long_signals,
            short_signals=short_signals,
            neutral_signals=neutral_signals,
            alpha_results=results,
            notes=notes,
            computed_at=datetime.utcnow()
        )
    
    def _generate_notes(
        self, 
        results: List[AlphaResult], 
        direction: AlphaDirection,
        confidence: float
    ) -> List[str]:
        """Генерация комментариев для summary"""
        notes = []
        
        # Direction note
        if direction == AlphaDirection.LONG:
            notes.append(f"Alpha bias: LONG with {confidence:.0%} confidence")
        elif direction == AlphaDirection.SHORT:
            notes.append(f"Alpha bias: SHORT with {confidence:.0%} confidence")
        else:
            notes.append("Alpha bias: NEUTRAL - mixed signals")
        
        # Strong signals
        strong_alphas = [r for r in results if r.strength > 0.7]
        if strong_alphas:
            strong_names = [a.alpha_name for a in strong_alphas[:3]]
            notes.append(f"Strong signals: {', '.join(strong_names)}")
        
        # Conflicting signals
        long_count = sum(1 for r in results if r.direction == AlphaDirection.LONG)
        short_count = sum(1 for r in results if r.direction == AlphaDirection.SHORT)
        
        if long_count > 0 and short_count > 0:
            notes.append(f"Signal conflict: {long_count} LONG vs {short_count} SHORT")
        
        # Volatility notes
        vol_comp = next((r for r in results if r.alpha_id == "volatility_compression_alpha"), None)
        vol_exp = next((r for r in results if r.alpha_id == "volatility_expansion_alpha"), None)
        
        if vol_comp and vol_comp.strength > 0.6:
            notes.append("High volatility compression - breakout potential")
        elif vol_exp and vol_exp.strength > 0.6:
            notes.append("Volatility expansion detected - trend continuation likely")
        
        return notes
    
    def score(
        self, 
        symbol: str, 
        timeframe: str,
        market_data: Dict[str, Any]
    ) -> AlphaSummary:
        """
        Полный scoring pipeline.
        
        1. Compute all alphas
        2. Normalize results
        3. Build summary
        """
        # Step 1: Compute
        results = self.compute_all_alphas(market_data)
        
        # Step 2: Normalize
        normalized = self.normalize_results(results)
        
        # Step 3: Build summary
        summary = self.build_summary(symbol, timeframe, normalized)
        
        return summary
