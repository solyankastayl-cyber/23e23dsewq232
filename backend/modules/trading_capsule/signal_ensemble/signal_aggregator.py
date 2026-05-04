"""
Signal Aggregator
=================

Агрегация alpha-сигналов с учётом весов.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .ensemble_types import (
    SignalDirection,
    AlphaContribution,
    EnsembleSignal,
    SignalQuality
)
from .ensemble_weights import EnsembleWeights, get_default_weights


class SignalAggregator:
    """
    Агрегатор alpha-сигналов.
    
    Объединяет alpha-сигналы в единый ensemble с учётом:
    - Весов каждого alpha
    - Направления сигнала
    - Силы и уверенности
    - Текущего режима рынка
    """
    
    def __init__(self, weights: Optional[EnsembleWeights] = None):
        self.weights = weights or get_default_weights()
    
    def aggregate(
        self,
        alpha_results: List[Dict[str, Any]],
        regime: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """
        Агрегация alpha-сигналов.
        
        Args:
            alpha_results: Список результатов от Alpha Engine
            regime: Текущий режим рынка
            
        Returns:
            Dict с агрегированными данными
        """
        if not alpha_results:
            return self._empty_result()
        
        # Adjust weights for regime
        adjusted_weights = self.weights.adjust_for_regime(regime)
        
        # Calculate contributions
        contributions = []
        long_score = 0.0
        short_score = 0.0
        neutral_score = 0.0
        total_weight = 0.0
        
        for alpha in alpha_results:
            alpha_id = alpha.get("alpha_id", "")
            direction = alpha.get("direction", "NEUTRAL")
            strength = float(alpha.get("strength", 0))
            confidence = float(alpha.get("confidence", 0))
            
            # Get weight
            weight = adjusted_weights.get_weight(alpha_id)
            
            # Calculate weighted score
            weighted_score = strength * confidence * weight
            total_weight += weight
            
            # Accumulate by direction
            if direction == "LONG":
                long_score += weighted_score
            elif direction == "SHORT":
                short_score += weighted_score
            else:
                neutral_score += weighted_score * 0.5
            
            contributions.append(AlphaContribution(
                alpha_id=alpha_id,
                alpha_name=alpha.get("alpha_name", alpha_id),
                direction=direction,
                raw_strength=strength,
                raw_confidence=confidence,
                weight=weight,
                weighted_score=round(weighted_score, 4),
                contribution_pct=0,  # Will calculate later
                regime_aligned=self._is_regime_aligned(direction, regime),
                in_conflict=False  # Will be set by ConflictResolver
            ))
        
        # Normalize scores
        max_possible = total_weight if total_weight > 0 else 1.0
        long_score = long_score / max_possible
        short_score = short_score / max_possible
        neutral_score = neutral_score / max_possible
        
        # Calculate contribution percentages
        total_contribution = long_score + short_score + neutral_score
        if total_contribution > 0:
            for c in contributions:
                if c.direction == "LONG":
                    c.contribution_pct = round(c.weighted_score / max_possible / total_contribution * 100, 2)
                elif c.direction == "SHORT":
                    c.contribution_pct = round(c.weighted_score / max_possible / total_contribution * 100, 2)
                else:
                    c.contribution_pct = round(c.weighted_score * 0.5 / max_possible / total_contribution * 100, 2)
        
        # Determine final direction
        scores = {"LONG": long_score, "SHORT": short_score, "NEUTRAL": neutral_score}
        max_direction = max(scores, key=scores.get)
        max_score = scores[max_direction]
        
        # Calculate margin (clarity of signal)
        sorted_scores = sorted(scores.values(), reverse=True)
        margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
        
        # Determine direction with thresholds
        if margin < 0.1 or max_score < 0.2:
            direction = SignalDirection.NEUTRAL
        else:
            direction = SignalDirection(max_direction)
        
        # Calculate strength and confidence
        strength = min(1.0, max_score * 1.2)  # Boost slightly
        confidence = min(1.0, margin * 2 + 0.3)  # Based on margin
        
        # Determine quality
        quality = self._determine_quality(strength, confidence, margin)
        
        # Find dominant and supporting alphas
        sorted_contribs = sorted(contributions, key=lambda x: x.weighted_score, reverse=True)
        dominant_alpha = sorted_contribs[0].alpha_id if sorted_contribs else ""
        
        supporting = [c.alpha_id for c in sorted_contribs[1:4] if c.direction == direction.value]
        opposing = [c.alpha_id for c in contributions if c.direction != direction.value and c.direction != "NEUTRAL"]
        
        return {
            "signal": EnsembleSignal(
                direction=direction,
                strength=round(strength, 4),
                confidence=round(confidence, 4),
                quality=quality,
                long_score=round(long_score, 4),
                short_score=round(short_score, 4),
                neutral_score=round(neutral_score, 4),
                dominant_alpha=dominant_alpha,
                supporting_alphas=supporting,
                opposing_alphas=opposing
            ),
            "contributions": contributions,
            "scores": {
                "long": round(long_score, 4),
                "short": round(short_score, 4),
                "neutral": round(neutral_score, 4),
                "margin": round(margin, 4)
            },
            "stats": {
                "total_alphas": len(alpha_results),
                "aligned_alphas": sum(1 for c in contributions if c.direction == direction.value),
                "opposing_alphas": len(opposing),
                "neutral_alphas": sum(1 for c in contributions if c.direction == "NEUTRAL")
            }
        }
    
    def _is_regime_aligned(self, direction: str, regime: str) -> bool:
        """Проверка соответствия направления режиму"""
        if regime in ["TRENDING", "TREND_UP"]:
            return direction == "LONG"
        elif regime == "TREND_DOWN":
            return direction == "SHORT"
        elif regime in ["RANGING", "RANGE"]:
            return direction in ["SHORT", "NEUTRAL"]  # Mean reversion
        return True  # Unknown regime - always aligned
    
    def _determine_quality(self, strength: float, confidence: float, margin: float) -> SignalQuality:
        """Определение качества сигнала"""
        combined = (strength + confidence + margin) / 3
        
        if combined >= 0.7:
            return SignalQuality.PREMIUM
        elif combined >= 0.55:
            return SignalQuality.HIGH
        elif combined >= 0.35:
            return SignalQuality.MEDIUM
        else:
            return SignalQuality.LOW
    
    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат при отсутствии данных"""
        return {
            "signal": EnsembleSignal(
                direction=SignalDirection.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                quality=SignalQuality.LOW,
                long_score=0.0,
                short_score=0.0,
                neutral_score=0.0
            ),
            "contributions": [],
            "scores": {"long": 0, "short": 0, "neutral": 0, "margin": 0},
            "stats": {"total_alphas": 0, "aligned_alphas": 0, "opposing_alphas": 0, "neutral_alphas": 0}
        }
