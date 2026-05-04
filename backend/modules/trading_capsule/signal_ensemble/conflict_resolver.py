"""
Conflict Resolver
=================

Обнаружение и разрешение конфликтов между alpha-сигналами.
"""

from typing import Dict, List, Any, Tuple
from .ensemble_types import (
    SignalDirection,
    ConflictReport,
    AlphaContribution,
    EnsembleSignal,
    SignalQuality
)


class ConflictResolver:
    """
    Resolver конфликтов между alpha-сигналами.
    
    Типы конфликтов:
    1. Directional conflict: LONG vs SHORT alphas
    2. Regime conflict: signal vs current regime
    3. Strength conflict: strong opposing signals
    
    Действия:
    - NONE: нет конфликта
    - REDUCE_CONFIDENCE: уменьшить уверенность
    - NEUTRAL: перевести в нейтральный
    - SPLIT: разделить сигнал (partial)
    """
    
    def __init__(self, conflict_threshold: float = 0.4):
        self.conflict_threshold = conflict_threshold
    
    def analyze_conflicts(
        self,
        contributions: List[AlphaContribution],
        signal: EnsembleSignal,
        regime: str = "UNKNOWN"
    ) -> ConflictReport:
        """
        Анализ конфликтов в сигналах.
        
        Args:
            contributions: Вклады alpha-факторов
            signal: Предварительный ensemble сигнал
            regime: Текущий режим
            
        Returns:
            ConflictReport с детализацией конфликтов
        """
        if not contributions:
            return ConflictReport()
        
        # Collect signals by direction
        long_alphas = [c for c in contributions if c.direction == "LONG"]
        short_alphas = [c for c in contributions if c.direction == "SHORT"]
        
        # Calculate directional conflict
        long_power = sum(c.weighted_score for c in long_alphas)
        short_power = sum(c.weighted_score for c in short_alphas)
        
        total_power = long_power + short_power
        if total_power == 0:
            return ConflictReport()
        
        # Conflict ratio
        conflict_ratio = min(long_power, short_power) / total_power
        
        # Detect conflicts
        conflicts = []
        notes = []
        
        # 1. Directional conflict
        if conflict_ratio > self.conflict_threshold:
            # Find specific conflicting pairs
            conflicting_pairs = self._find_conflicting_pairs(long_alphas, short_alphas)
            for pair in conflicting_pairs:
                conflicts.append({
                    "type": "DIRECTIONAL",
                    "alpha_1": pair[0].alpha_id,
                    "alpha_2": pair[1].alpha_id,
                    "severity": conflict_ratio
                })
            notes.append(f"Directional conflict: {len(long_alphas)} LONG vs {len(short_alphas)} SHORT")
        
        # 2. Strong opposing signals
        strong_opposing = self._detect_strong_opposing(contributions, signal.direction)
        if strong_opposing:
            for alpha in strong_opposing:
                conflicts.append({
                    "type": "STRONG_OPPOSING",
                    "alpha": alpha.alpha_id,
                    "strength": alpha.raw_strength,
                    "direction": alpha.direction
                })
            notes.append(f"Strong opposing: {[a.alpha_id for a in strong_opposing]}")
        
        # 3. Regime conflict
        regime_conflict = self._detect_regime_conflict(signal.direction, regime, contributions)
        if regime_conflict:
            conflicts.append({
                "type": "REGIME",
                "signal_direction": signal.direction.value,
                "regime": regime,
                "severity": regime_conflict["severity"]
            })
            notes.append(f"Regime conflict: {signal.direction.value} signal in {regime} regime")
        
        # Calculate overall severity
        has_conflict = len(conflicts) > 0
        severity = self._calculate_severity(conflicts, conflict_ratio)
        
        # Determine resolution action
        action, penalty = self._determine_action(severity, conflict_ratio, has_conflict)
        
        # Mark conflicting alphas
        for c in contributions:
            c.in_conflict = any(
                conf.get("alpha_1") == c.alpha_id or 
                conf.get("alpha_2") == c.alpha_id or
                conf.get("alpha") == c.alpha_id
                for conf in conflicts
            )
        
        return ConflictReport(
            has_conflict=has_conflict,
            conflict_severity=round(severity, 4),
            conflicting_alphas=conflicts,
            resolution_action=action,
            confidence_penalty=round(penalty, 4),
            notes=notes
        )
    
    def resolve(
        self,
        signal: EnsembleSignal,
        conflict_report: ConflictReport
    ) -> EnsembleSignal:
        """
        Применить разрешение конфликтов к сигналу.
        
        Args:
            signal: Исходный сигнал
            conflict_report: Отчёт о конфликтах
            
        Returns:
            Скорректированный сигнал
        """
        if not conflict_report.has_conflict:
            return signal
        
        # Copy signal
        resolved = EnsembleSignal(
            direction=signal.direction,
            strength=signal.strength,
            confidence=signal.confidence,
            quality=signal.quality,
            long_score=signal.long_score,
            short_score=signal.short_score,
            neutral_score=signal.neutral_score,
            dominant_alpha=signal.dominant_alpha,
            supporting_alphas=signal.supporting_alphas,
            opposing_alphas=signal.opposing_alphas
        )
        
        action = conflict_report.resolution_action
        penalty = conflict_report.confidence_penalty
        
        if action == "REDUCE_CONFIDENCE":
            # Reduce confidence by penalty
            resolved.confidence = max(0.1, signal.confidence - penalty)
            resolved.strength = max(0.1, signal.strength * (1 - penalty * 0.5))
            
        elif action == "NEUTRAL":
            # Convert to neutral
            resolved.direction = SignalDirection.NEUTRAL
            resolved.confidence = 0.3
            resolved.strength = 0.3
            
        elif action == "SPLIT":
            # Reduce confidence significantly
            resolved.confidence = max(0.2, signal.confidence * 0.5)
            resolved.strength = max(0.2, signal.strength * 0.7)
        
        # Recalculate quality
        resolved.quality = self._recalculate_quality(resolved)
        
        return resolved
    
    def _find_conflicting_pairs(
        self,
        long_alphas: List[AlphaContribution],
        short_alphas: List[AlphaContribution]
    ) -> List[Tuple[AlphaContribution, AlphaContribution]]:
        """Найти конфликтующие пары alpha"""
        pairs = []
        
        # Sort by weighted score
        long_sorted = sorted(long_alphas, key=lambda x: x.weighted_score, reverse=True)
        short_sorted = sorted(short_alphas, key=lambda x: x.weighted_score, reverse=True)
        
        # Pair strongest from each side
        for i, long_alpha in enumerate(long_sorted[:3]):
            if i < len(short_sorted):
                pairs.append((long_alpha, short_sorted[i]))
        
        return pairs
    
    def _detect_strong_opposing(
        self,
        contributions: List[AlphaContribution],
        direction: SignalDirection
    ) -> List[AlphaContribution]:
        """Найти сильные противоположные сигналы"""
        strong_opposing = []
        
        opposing_dir = "SHORT" if direction == SignalDirection.LONG else "LONG"
        
        for c in contributions:
            if c.direction == opposing_dir and c.raw_strength > 0.6 and c.raw_confidence > 0.5:
                strong_opposing.append(c)
        
        return strong_opposing
    
    def _detect_regime_conflict(
        self,
        direction: SignalDirection,
        regime: str,
        contributions: List[AlphaContribution]
    ) -> Dict[str, Any]:
        """Обнаружить конфликт с режимом"""
        # Define regime expectations
        regime_expects = {
            "TREND_UP": SignalDirection.LONG,
            "TRENDING": SignalDirection.LONG,
            "TREND_DOWN": SignalDirection.SHORT,
            "RANGING": SignalDirection.NEUTRAL,
            "RANGE": SignalDirection.NEUTRAL
        }
        
        expected = regime_expects.get(regime)
        
        if expected and direction != expected and direction != SignalDirection.NEUTRAL:
            # Calculate severity based on how many alphas are regime-aligned
            regime_aligned = sum(1 for c in contributions if c.regime_aligned)
            alignment_ratio = regime_aligned / len(contributions) if contributions else 1
            
            severity = 1 - alignment_ratio
            
            if severity > 0.3:
                return {"severity": severity, "expected": expected.value}
        
        return None
    
    def _calculate_severity(
        self,
        conflicts: List[Dict[str, Any]],
        conflict_ratio: float
    ) -> float:
        """Рассчитать общую серьёзность конфликтов"""
        if not conflicts:
            return 0.0
        
        # Base severity from conflict ratio
        base = conflict_ratio
        
        # Add for each conflict type
        for conf in conflicts:
            if conf["type"] == "DIRECTIONAL":
                base += 0.15
            elif conf["type"] == "STRONG_OPPOSING":
                base += 0.2
            elif conf["type"] == "REGIME":
                base += conf.get("severity", 0.1)
        
        return min(1.0, base)
    
    def _determine_action(
        self,
        severity: float,
        conflict_ratio: float,
        has_conflict: bool
    ) -> Tuple[str, float]:
        """Определить действие по разрешению"""
        if not has_conflict:
            return "NONE", 0.0
        
        if severity > 0.7:
            return "NEUTRAL", 0.5
        elif severity > 0.5:
            return "SPLIT", 0.35
        elif severity > 0.3:
            return "REDUCE_CONFIDENCE", 0.2
        else:
            return "REDUCE_CONFIDENCE", 0.1
    
    def _recalculate_quality(self, signal: EnsembleSignal) -> SignalQuality:
        """Пересчитать качество после разрешения"""
        combined = (signal.strength + signal.confidence) / 2
        
        if combined >= 0.7:
            return SignalQuality.PREMIUM
        elif combined >= 0.55:
            return SignalQuality.HIGH
        elif combined >= 0.35:
            return SignalQuality.MEDIUM
        else:
            return SignalQuality.LOW
