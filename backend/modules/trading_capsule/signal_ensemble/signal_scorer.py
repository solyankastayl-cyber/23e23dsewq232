"""
Signal Scorer
=============

Финальный расчёт score для ensemble сигнала.
Объединяет агрегацию, разрешение конфликтов и контекст.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .ensemble_types import (
    SignalDirection,
    SignalQuality,
    EnsembleSignal,
    EnsembleResult,
    ConflictReport,
    AlphaContribution,
    EnsembleConfig
)
from .ensemble_weights import EnsembleWeights, get_default_weights
from .signal_aggregator import SignalAggregator
from .conflict_resolver import ConflictResolver


class SignalScorer:
    """
    Финальный scorer для ensemble сигналов.
    
    Pipeline:
    1. Агрегация alpha-сигналов
    2. Анализ конфликтов
    3. Разрешение конфликтов
    4. Расчёт финального score
    5. Генерация рекомендаций
    """
    
    def __init__(
        self,
        weights: Optional[EnsembleWeights] = None,
        config: Optional[EnsembleConfig] = None
    ):
        self.weights = weights or get_default_weights()
        self.config = config or EnsembleConfig()
        self.aggregator = SignalAggregator(self.weights)
        self.resolver = ConflictResolver(self.config.conflict_threshold)
    
    def score(
        self,
        symbol: str,
        timeframe: str,
        alpha_results: List[Dict[str, Any]],
        regime: str = "UNKNOWN",
        market_context: Optional[Dict[str, Any]] = None
    ) -> EnsembleResult:
        """
        Полный scoring pipeline.
        
        Args:
            symbol: Торговый символ
            timeframe: Таймфрейм
            alpha_results: Результаты от Alpha Engine
            regime: Текущий режим рынка
            market_context: Дополнительный контекст
            
        Returns:
            EnsembleResult с финальным сигналом
        """
        market_context = market_context or {}
        
        # Step 1: Aggregate
        aggregated = self.aggregator.aggregate(alpha_results, regime)
        signal = aggregated["signal"]
        contributions = aggregated["contributions"]
        stats = aggregated["stats"]
        
        # Step 2: Analyze conflicts
        conflict_report = self.resolver.analyze_conflicts(
            contributions, signal, regime
        )
        
        # Step 3: Resolve conflicts
        resolved_signal = self.resolver.resolve(signal, conflict_report)
        
        # Step 4: Apply regime boost
        resolved_signal = self._apply_regime_boost(resolved_signal, regime)
        
        # Step 5: Calculate action score
        action_score = self._calculate_action_score(resolved_signal, conflict_report)
        
        # Step 6: Generate recommendation
        recommendation, notes, warnings = self._generate_recommendation(
            resolved_signal, conflict_report, regime, stats
        )
        
        return EnsembleResult(
            symbol=symbol,
            timeframe=timeframe,
            signal=resolved_signal,
            alpha_contributions=contributions,
            conflict_report=conflict_report,
            regime=regime,
            market_context=market_context,
            recommendation=recommendation,
            action_score=round(action_score, 4),
            total_alphas=stats["total_alphas"],
            aligned_alphas=stats["aligned_alphas"],
            opposing_alphas=stats["opposing_alphas"],
            neutral_alphas=stats["neutral_alphas"],
            notes=notes,
            warnings=warnings,
            computed_at=datetime.utcnow()
        )
    
    def _apply_regime_boost(
        self,
        signal: EnsembleSignal,
        regime: str
    ) -> EnsembleSignal:
        """Применить boost/penalty на основе режима"""
        boost = self.config.regime_boost.get(regime, 1.0)
        
        # Only boost if direction aligns with regime
        should_boost = self._direction_aligns_with_regime(signal.direction, regime)
        
        if should_boost:
            boosted_confidence = min(1.0, signal.confidence * boost)
            boosted_strength = min(1.0, signal.strength * (boost * 0.8 + 0.2))
        else:
            # Slight penalty for misalignment
            boosted_confidence = signal.confidence * 0.9
            boosted_strength = signal.strength * 0.95
        
        return EnsembleSignal(
            direction=signal.direction,
            strength=round(boosted_strength, 4),
            confidence=round(boosted_confidence, 4),
            quality=self._recalculate_quality(boosted_strength, boosted_confidence),
            long_score=signal.long_score,
            short_score=signal.short_score,
            neutral_score=signal.neutral_score,
            dominant_alpha=signal.dominant_alpha,
            supporting_alphas=signal.supporting_alphas,
            opposing_alphas=signal.opposing_alphas
        )
    
    def _direction_aligns_with_regime(
        self,
        direction: SignalDirection,
        regime: str
    ) -> bool:
        """Проверить соответствие направления режиму"""
        alignments = {
            "TRENDING": [SignalDirection.LONG, SignalDirection.SHORT],
            "TREND_UP": [SignalDirection.LONG],
            "TREND_DOWN": [SignalDirection.SHORT],
            "RANGING": [SignalDirection.NEUTRAL],
            "RANGE": [SignalDirection.NEUTRAL],
            "COMPRESSION": [SignalDirection.NEUTRAL],
            "EXPANSION": [SignalDirection.LONG, SignalDirection.SHORT],
            "VOLATILE": [SignalDirection.NEUTRAL]
        }
        
        expected = alignments.get(regime, [SignalDirection.LONG, SignalDirection.SHORT, SignalDirection.NEUTRAL])
        return direction in expected
    
    def _calculate_action_score(
        self,
        signal: EnsembleSignal,
        conflict_report: ConflictReport
    ) -> float:
        """
        Рассчитать score действия (рекомендуемый размер позиции).
        
        0.0 = не торговать
        0.5 = половина размера
        1.0 = полный размер
        """
        if signal.direction == SignalDirection.NEUTRAL:
            return 0.0
        
        # Base from strength and confidence
        base = (signal.strength + signal.confidence) / 2
        
        # Adjust for quality
        quality_mult = {
            SignalQuality.PREMIUM: 1.0,
            SignalQuality.HIGH: 0.85,
            SignalQuality.MEDIUM: 0.65,
            SignalQuality.LOW: 0.4
        }
        base *= quality_mult.get(signal.quality, 0.5)
        
        # Adjust for conflicts
        if conflict_report.has_conflict:
            base *= (1 - conflict_report.confidence_penalty * 0.5)
        
        # Clamp to range
        return max(0.0, min(1.0, base))
    
    def _generate_recommendation(
        self,
        signal: EnsembleSignal,
        conflict_report: ConflictReport,
        regime: str,
        stats: Dict[str, int]
    ) -> tuple:
        """Генерация текстовой рекомендации"""
        notes = []
        warnings = []
        
        # Direction recommendation
        if signal.direction == SignalDirection.NEUTRAL:
            recommendation = "WAIT - No clear signal"
            notes.append("Insufficient directional clarity")
        elif signal.quality == SignalQuality.PREMIUM:
            recommendation = f"STRONG {signal.direction.value} - Premium signal quality"
            notes.append(f"High conviction {signal.direction.value} setup")
        elif signal.quality == SignalQuality.HIGH:
            recommendation = f"{signal.direction.value} - High quality signal"
            notes.append(f"Good {signal.direction.value} opportunity")
        elif signal.quality == SignalQuality.MEDIUM:
            recommendation = f"CONSIDER {signal.direction.value} - Medium quality"
            notes.append("Signal present but moderate conviction")
        else:
            recommendation = f"WEAK {signal.direction.value} - Low quality signal"
            warnings.append("Low conviction - consider smaller size")
        
        # Conflict warnings
        if conflict_report.has_conflict:
            warnings.append(f"Signal conflict detected: {conflict_report.resolution_action}")
            if conflict_report.conflict_severity > 0.5:
                warnings.append("High conflict severity - exercise caution")
        
        # Stats notes
        if stats["opposing_alphas"] > stats["aligned_alphas"]:
            warnings.append(f"More opposing ({stats['opposing_alphas']}) than aligned ({stats['aligned_alphas']}) alphas")
        
        if stats["aligned_alphas"] >= 5:
            notes.append(f"Strong alpha alignment: {stats['aligned_alphas']} supporting")
        
        # Regime notes
        if regime != "UNKNOWN":
            notes.append(f"Current regime: {regime}")
            if not self._direction_aligns_with_regime(signal.direction, regime):
                warnings.append(f"Signal direction may conflict with {regime} regime")
        
        # Dominant alpha
        if signal.dominant_alpha:
            notes.append(f"Primary driver: {signal.dominant_alpha}")
        
        return recommendation, notes, warnings
    
    def _recalculate_quality(self, strength: float, confidence: float) -> SignalQuality:
        """Пересчитать качество"""
        combined = (strength + confidence) / 2
        
        thresholds = self.config.quality_thresholds
        
        if combined >= thresholds.get("PREMIUM", 0.8):
            return SignalQuality.PREMIUM
        elif combined >= thresholds.get("HIGH", 0.65):
            return SignalQuality.HIGH
        elif combined >= thresholds.get("MEDIUM", 0.45):
            return SignalQuality.MEDIUM
        else:
            return SignalQuality.LOW
    
    def score_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[EnsembleResult]:
        """
        Batch scoring для нескольких символов.
        
        Args:
            requests: Список запросов с symbol, timeframe, alpha_results, regime
            
        Returns:
            Список EnsembleResult
        """
        results = []
        
        for req in requests:
            result = self.score(
                symbol=req.get("symbol", "UNKNOWN"),
                timeframe=req.get("timeframe", "1h"),
                alpha_results=req.get("alpha_results", []),
                regime=req.get("regime", "UNKNOWN"),
                market_context=req.get("market_context")
            )
            results.append(result)
        
        return results
